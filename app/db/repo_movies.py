import random

from sqlalchemy import Text, case, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.text import normalize_text
from app.db.filters import MovieFilter
from app.db.models import Country, Movie, UserWatched, movie_countries, movie_genres

ORDER = {
    "r": (Movie.rating.desc().nulls_last(), Movie.votes.desc().nulls_last()),
    "p": (Movie.popularity.desc().nulls_last(),),
    "n": (Movie.year.desc().nulls_last(), Movie.rating.desc().nulls_last()),
}


def _conditions(f: MovieFilter) -> list:
    c = []
    if f.genre_ids:
        c.append(Movie.id.in_(select(movie_genres.c.movie_id).where(movie_genres.c.genre_id.in_(f.genre_ids))))
    if f.year_from is not None:
        c.append(Movie.year >= f.year_from)
    if f.year_to is not None:
        c.append(Movie.year <= f.year_to)
    if f.min_rating is not None:
        c.append(Movie.rating >= f.min_rating)
    if f.runtime_min is not None:
        c.append(Movie.runtime >= f.runtime_min)
    if f.runtime_max is not None:
        c.append(Movie.runtime <= f.runtime_max)
    if f.country:
        c.append(Movie.id.in_(select(movie_countries.c.movie_id).where(movie_countries.c.country_code == f.country)))
    if f.exclude_language:
        c.append(or_(Movie.original_language.is_(None), Movie.original_language != f.exclude_language))
    if f.exclude_watched_by:
        c.append(Movie.id.notin_(select(UserWatched.movie_id).where(UserWatched.user_id == f.exclude_watched_by)))
    if f.min_votes:
        c.append(or_(Movie.votes.is_(None), Movie.votes >= f.min_votes))
    return c


async def get_movie(session: AsyncSession, movie_id: int) -> Movie | None:
    stmt = select(Movie).where(Movie.id == movie_id).options(selectinload(Movie.people_links))
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_many(session: AsyncSession, ids: list[int]) -> list[Movie]:
    if not ids:
        return []
    rows = (await session.execute(select(Movie).where(Movie.id.in_(ids)))).scalars().all()
    by_id = {m.id: m for m in rows}
    return [by_id[i] for i in ids if i in by_id]


async def paginate(session: AsyncSession, f: MovieFilter, page: int, per_page: int) -> tuple[list[Movie], int]:
    where = _conditions(f)
    total = (await session.execute(select(func.count(Movie.id)).where(*where))).scalar_one()
    stmt = (select(Movie).where(*where).order_by(*ORDER.get(f.sort, ORDER["r"]), Movie.id)
            .limit(per_page).offset(max(page - 1, 0) * per_page))
    return list((await session.execute(stmt)).scalars().all()), total


async def random_movie(session: AsyncSession, f: MovieFilter) -> Movie | None:
    """Случайный фильм без ORDER BY random(): count + случайный OFFSET по индексам."""
    where = _conditions(f)
    total = (await session.execute(select(func.count(Movie.id)).where(*where))).scalar_one()
    if not total:
        return None
    stmt = select(Movie.id).where(*where).order_by(Movie.id).offset(random.randrange(total)).limit(1)
    movie_id = (await session.execute(stmt)).scalar_one()
    return await get_movie(session, movie_id)


async def pick(session: AsyncSession, f: MovieFilter, n: int = 5, pool: int = 40) -> list[Movie]:
    """n случайных фильмов из топ-`pool` по рейтингу среди подходящих."""
    stmt = select(Movie).where(*_conditions(f)).order_by(*ORDER["r"], Movie.id).limit(pool)
    rows = list((await session.execute(stmt)).scalars().all())
    return random.sample(rows, min(n, len(rows)))


async def search(session: AsyncSession, query: str, limit: int = 8) -> list[Movie]:
    """Поиск по русскому/оригинальному названию: подстрока + триграммы (pg_trgm), опечатки прощаются."""
    q = normalize_text(query)
    if not q:
        return []
    await session.execute(text("SET LOCAL pg_trgm.word_similarity_threshold = 0.45"))
    qt = cast(q, Text)
    stmt = (
        select(Movie)
        .where(or_(Movie.search_text.contains(q, autoescape=True), qt.op("<%")(Movie.search_text)))
        .order_by(
            case((Movie.search_text.startswith(q, autoescape=True), 0), else_=1),
            func.word_similarity(qt, Movie.search_text).desc(),
            Movie.votes.desc().nulls_last(),
        )
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


SIMILAR_SQL = text("""
WITH g AS (
  SELECT mg.movie_id, count(*) * 2 AS s FROM movie_genres mg
  WHERE mg.genre_id IN (SELECT genre_id FROM movie_genres WHERE movie_id = :mid) AND mg.movie_id <> :mid
  GROUP BY mg.movie_id
), p AS (
  SELECT mp.movie_id, sum(CASE WHEN mp.role = 'director' THEN 4 ELSE 1 END) AS s FROM movie_people mp
  WHERE mp.person_id IN (SELECT person_id FROM movie_people WHERE movie_id = :mid
                         AND (role = 'director' OR (role = 'actor' AND position < 5)))
    AND (mp.role = 'director' OR (mp.role = 'actor' AND mp.position < 5)) AND mp.movie_id <> :mid
  GROUP BY mp.movie_id
), k AS (
  SELECT mk.movie_id, count(*) AS s FROM movie_keywords mk
  WHERE mk.keyword_id IN (SELECT keyword_id FROM movie_keywords WHERE movie_id = :mid) AND mk.movie_id <> :mid
  GROUP BY mk.movie_id
)
SELECT m.id FROM movies m
LEFT JOIN g ON g.movie_id = m.id LEFT JOIN p ON p.movie_id = m.id LEFT JOIN k ON k.movie_id = m.id
WHERE (g.s IS NOT NULL OR p.s IS NOT NULL OR k.s IS NOT NULL)
  AND (m.votes IS NULL OR m.votes >= 200)
  AND (CAST(:uid AS BIGINT) IS NULL OR m.id NOT IN (SELECT movie_id FROM user_watched WHERE user_id = :uid))
ORDER BY (coalesce(g.s, 0) + coalesce(p.s, 0) + coalesce(k.s, 0)
          + CASE WHEN abs(m.year - (SELECT year FROM movies WHERE id = :mid)) <= 10 THEN 1 ELSE 0 END) DESC,
         m.rating DESC NULLS LAST, m.votes DESC NULLS LAST
LIMIT :lim
""")


async def similar(session: AsyncSession, movie_id: int, user_id: int | None = None, limit: int = 5) -> list[Movie]:
    """Похожесть: общие жанры (×2), режиссёр (×4), топ-актёры (×1), keywords (×1), близкое десятилетие (+1)."""
    ids = (await session.execute(SIMILAR_SQL, {"mid": movie_id, "uid": user_id, "lim": limit})).scalars().all()
    return await get_many(session, list(ids))


async def top_countries(session: AsyncSession, limit: int = 12) -> list[tuple[str, str]]:
    stmt = (select(Country.code, Country.name).join(movie_countries, movie_countries.c.country_code == Country.code)
            .group_by(Country.code, Country.name).order_by(func.count().desc()).limit(limit))
    return [(r[0], r[1]) for r in (await session.execute(stmt)).all()]
