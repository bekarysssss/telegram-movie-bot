from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_TOP = {
    "genre": "SELECT g.name_ru FROM user_watched uw JOIN movie_genres mg ON mg.movie_id = uw.movie_id "
             "JOIN genres g ON g.id = mg.genre_id WHERE uw.user_id = :u GROUP BY g.name_ru ORDER BY count(*) DESC LIMIT 1",
    "decade": "SELECT (m.year / 10 * 10)::text || '-е' FROM user_watched uw JOIN movies m ON m.id = uw.movie_id "
              "WHERE uw.user_id = :u AND m.year IS NOT NULL GROUP BY 1 ORDER BY count(*) DESC LIMIT 1",
    "director": "SELECT p.name FROM user_watched uw JOIN movie_people mp ON mp.movie_id = uw.movie_id AND mp.role = 'director' "
                "JOIN people p ON p.id = mp.person_id WHERE uw.user_id = :u GROUP BY p.name ORDER BY count(*) DESC, p.name LIMIT 1",
    "country": "SELECT c.code, c.name FROM user_watched uw JOIN movie_countries mc ON mc.movie_id = uw.movie_id "
               "JOIN countries c ON c.code = mc.country_code WHERE uw.user_id = :u GROUP BY c.code, c.name ORDER BY count(*) DESC LIMIT 1",
}

_SUMMARY = text("""
SELECT count(*) AS total,
       avg(uw.rating) AS avg_rating,
       count(*) FILTER (WHERE uw.watched_at >= date_trunc('month', now())) AS month_cnt,
       count(*) FILTER (WHERE uw.watched_at >= date_trunc('year', now())) AS year_cnt,
       (SELECT count(DISTINCT mc.country_code) FROM user_watched x JOIN movie_countries mc ON mc.movie_id = x.movie_id WHERE x.user_id = :u) AS countries,
       (SELECT count(DISTINCT mp.person_id) FROM user_watched x JOIN movie_people mp ON mp.movie_id = x.movie_id AND mp.role = 'director' WHERE x.user_id = :u) AS directors,
       (SELECT count(DISTINCT mg.genre_id) FROM user_watched x JOIN movie_genres mg ON mg.movie_id = x.movie_id WHERE x.user_id = :u) AS genres
FROM user_watched uw WHERE uw.user_id = :u
""")


async def user_stats(session: AsyncSession, uid: int) -> dict:
    row = (await session.execute(_SUMMARY, {"u": uid})).mappings().one()
    data = dict(row)
    for key, sql in _TOP.items():
        r = (await session.execute(text(sql), {"u": uid})).first()
        data[f"top_{key}"] = tuple(r) if r and len(r) > 1 else (r[0] if r else None)
    return data


async def bot_stats(session: AsyncSession) -> dict:
    one = lambda sql: session.scalar(text(sql))  # noqa: E731
    top = (await session.execute(text(
        "SELECT m.title, m.year, count(*) c FROM user_watched uw JOIN movies m ON m.id = uw.movie_id "
        "GROUP BY m.id ORDER BY c DESC LIMIT 5"))).all()
    return {
        "users": await one("SELECT count(*) FROM users"),
        "users_24h": await one("SELECT count(*) FROM users WHERE created_at > now() - interval '1 day'"),
        "users_7d": await one("SELECT count(*) FROM users WHERE created_at > now() - interval '7 days'"),
        "active_7d": await one("SELECT count(*) FROM users WHERE last_seen_at > now() - interval '7 days'"),
        "movies": await one("SELECT count(*) FROM movies"),
        "favorites": await one("SELECT count(*) FROM user_favorites"),
        "watched": await one("SELECT count(*) FROM user_watched"),
        "top_movies": [{"title": t, "year": y, "watched_by": c} for t, y, c in top],
    }
