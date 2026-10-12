"""Загрузка фильмов в БД: upsert по tmdb_id / imdb_id, нормализованные связи."""
import asyncio
import logging
from dataclasses import dataclass, field

from sqlalchemy import delete, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import noload

from app.core.constants import GENRES
from app.db.models import (Country, Genre, Keyword, Movie, MoviePerson, Person, movie_countries,
                           movie_genres, movie_keywords)
from app.integrations.tmdb import TMDB, parse_tmdb
from app.services.types import SCALAR_FIELDS, MovieData

log = logging.getLogger(__name__)


@dataclass
class RefCache:
    people: dict = field(default_factory=dict)
    keywords: dict = field(default_factory=dict)
    countries: set = field(default_factory=set)


async def ensure_genres(session: AsyncSession) -> None:
    have = set((await session.execute(select(Genre.id))).scalars().all())
    for gid, en, ru, _emoji in GENRES:
        if gid not in have:
            session.add(Genre(id=gid, name=en, name_ru=ru))
    await session.flush()


async def _person_id(session: AsyncSession, cache: RefCache, name: str, tmdb_id: int | None) -> int:
    key = ("t", tmdb_id) if tmdb_id else ("n", name)
    if key in cache.people:
        return cache.people[key]
    person = None
    if tmdb_id:
        person = (await session.execute(select(Person).where(Person.tmdb_id == tmdb_id))).scalars().first()
        if person is None:  # «усыновляем» запись из seed, у которой ещё нет tmdb_id
            person = (await session.execute(
                select(Person).where(Person.name == name, Person.tmdb_id.is_(None)))).scalars().first()
            if person:
                person.tmdb_id = tmdb_id
    else:
        person = (await session.execute(select(Person).where(Person.name == name))).scalars().first()
    if person is None:
        person = Person(name=name, tmdb_id=tmdb_id)
        session.add(person)
    await session.flush()
    cache.people[key] = person.id
    return person.id


async def _keyword_id(session: AsyncSession, cache: RefCache, name: str) -> int:
    if name not in cache.keywords:
        kid = (await session.execute(select(Keyword.id).where(Keyword.name == name))).scalar_one_or_none()
        if kid is None:
            kw = Keyword(name=name)
            session.add(kw)
            await session.flush()
            kid = kw.id
        cache.keywords[name] = kid
    return cache.keywords[name]


async def upsert_movie(session: AsyncSession, d: MovieData, cache: RefCache | None = None) -> tuple[Movie, bool]:
    """Создаёт или обновляет фильм. Пустые (None) поля источника существующие данные не затирают."""
    cache = cache or RefCache()
    conds = []
    if d.tmdb_id:
        conds.append(Movie.tmdb_id == d.tmdb_id)
    if d.imdb_id:
        conds.append(Movie.imdb_id == d.imdb_id)
    movie = None
    if conds:
        movie = (await session.execute(
            select(Movie).where(or_(*conds)).options(noload(Movie.genres), noload(Movie.countries)))
        ).scalars().first()
    created = movie is None
    if created:
        movie = Movie(title=d.title)
        session.add(movie)
    for f in SCALAR_FIELDS:
        value = getattr(d, f)
        if value not in (None, ""):
            setattr(movie, f, value)
    await session.flush()
    mid = movie.id

    if d.genre_ids:
        await session.execute(delete(movie_genres).where(movie_genres.c.movie_id == mid))
        await session.execute(insert(movie_genres), [{"movie_id": mid, "genre_id": g} for g in set(d.genre_ids)])
    if d.countries:
        for code, name in d.countries:
            if code not in cache.countries:
                if await session.get(Country, code) is None:
                    session.add(Country(code=code, name=name))
                cache.countries.add(code)
        await session.flush()
        await session.execute(delete(movie_countries).where(movie_countries.c.movie_id == mid))
        await session.execute(insert(movie_countries),
                              [{"movie_id": mid, "country_code": c} for c in {c for c, _ in d.countries}])
    if d.keywords:
        ids = {await _keyword_id(session, cache, k) for k in d.keywords}
        await session.execute(delete(movie_keywords).where(movie_keywords.c.movie_id == mid))
        await session.execute(insert(movie_keywords), [{"movie_id": mid, "keyword_id": k} for k in ids])

    if d.directors or d.writers or d.cast:
        await session.execute(delete(MoviePerson).where(MoviePerson.movie_id == mid))
        seen: set[tuple[int, str]] = set()
        for role, people in (("director", d.directors), ("writer", d.writers), ("actor", d.cast)):
            for pos, (name, tid) in enumerate(people):
                pid = await _person_id(session, cache, name, tid)
                if (pid, role) not in seen:
                    seen.add((pid, role))
                    session.add(MoviePerson(movie_id=mid, person_id=pid, role=role, position=pos))
    await session.flush()
    return movie, created


async def save_movies(sm: async_sessionmaker, items: list[MovieData], cache: RefCache | None = None) -> tuple[int, int]:
    """Каждый фильм — в своей транзакции: сбой одного не откатывает остальные."""
    cache, added, updated = cache or RefCache(), 0, 0
    for d in items:
        async with sm() as session:
            try:
                await ensure_genres(session)
                _, created = await upsert_movie(session, d, cache)
                await session.commit()
                added, updated = added + created, updated + (not created)
            except Exception:
                await session.rollback()
                cache.people.clear(), cache.keywords.clear(), cache.countries.clear()
                log.exception("Не удалось сохранить «%s»", d.title)
    return added, updated


async def import_from_tmdb(sm: async_sessionmaker, tmdb: TMDB, ids: list[int], refresh: bool = False,
                           concurrency: int = 8) -> tuple[int, int, int]:
    """Возвращает (добавлено, обновлено, пропущено)."""
    skipped = 0
    if not refresh and ids:
        async with sm() as session:
            have = set((await session.execute(select(Movie.tmdb_id).where(Movie.tmdb_id.in_(ids)))).scalars().all())
        skipped = len(have)
        ids = [i for i in ids if i not in have]
    sem = asyncio.Semaphore(concurrency)

    async def fetch(i: int):
        async with sem:
            return await tmdb.movie(i)

    raw = await asyncio.gather(*(fetch(i) for i in ids), return_exceptions=True)
    items = []
    for i, r in zip(ids, raw):
        if isinstance(r, Exception):
            log.warning("TMDB %s: %s", i, r)
        elif r:
            items.append(parse_tmdb(r))
    added, updated = await save_movies(sm, items)
    return added, updated, skipped
