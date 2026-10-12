"""Интеграционные тесты на реальном PostgreSQL. Запуск:

    TEST_DATABASE_URL=postgresql+asyncpg://movies:movies@localhost:5432/movies_test pytest

Без переменной окружения тесты пропускаются. ВНИМАНИЕ: схема в тестовой БД пересоздаётся!
"""
import asyncio
import os

import pytest

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL не задан")


def run(coro_fn):
    async def wrapper():
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from app.db import models  # noqa: F401
        from app.db.base import Base
        from app.services.importer import save_movies
        from app.services.seed import load_seed

        engine = create_async_engine(URL)
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        sm = async_sessionmaker(engine, expire_on_commit=False)
        result = await save_movies(sm, load_seed())
        try:
            return await coro_fn(sm, result)
        finally:
            await engine.dispose()
    return asyncio.run(wrapper())


def test_seed_import_is_idempotent():
    async def body(sm, first):
        from app.services.importer import save_movies
        from app.services.seed import load_seed
        assert first[0] == len(load_seed())
        assert await save_movies(sm, load_seed()) == (0, len(load_seed()))
    run(body)


def test_search_ru_en_and_typo():
    async def body(sm, _):
        from app.db import repo_movies as r
        async with sm() as s:
            for q in ("крёстный отец", "крестный отец", "godfather", "the godfater"):
                found = await r.search(s, q)
                assert found and "Godfather" in (found[0].original_title or ""), q
    run(body)


def test_browse_filters_and_pagination():
    async def body(sm, _):
        from app.db import repo_movies as r
        from app.db.filters import MovieFilter
        async with sm() as s:
            items, total = await r.paginate(s, MovieFilter(genre_ids=(80,)), 1, 3)
            assert total > 3 and len(items) == 3 and items[0].original_title == "The Godfather"
            horror70, _t = await r.paginate(s, MovieFilter(genre_ids=(27,), year_from=1970, year_to=1979, min_rating=7), 1, 50)
            assert horror70 and all(1970 <= m.year <= 1979 for m in horror70)
            assert await r.random_movie(s, MovieFilter(genre_ids=(27,), year_from=1970, year_to=1979, min_rating=7))
            assert await r.random_movie(s, MovieFilter(year_from=1800, year_to=1801)) is None
    run(body)


def test_similar_and_user_flows():
    async def body(sm, _):
        from sqlalchemy import select
        from app.db import repo_movies as r, repo_users as u
        from app.db.models import Movie, User
        from app.db.repo_stats import user_stats
        async with sm() as s:
            gf = (await s.execute(select(Movie).where(Movie.imdb_id == "tt0068646"))).scalar_one()
            titles = [m.title for m in await r.similar(s, gf.id)]
            assert "Крёстный отец 2" in titles and gf.title not in titles
            s.add(User(id=1))
            await s.flush()
            assert await u.toggle_favorite(s, 1, gf.id) is True
            assert await u.toggle_watched(s, 1, gf.id) is True
            await u.set_rating(s, 1, gf.id, 10)
            await s.flush()
            assert await u.flags(s, 1, gf.id) == (True, True, 10)
            st = await user_stats(s, 1)
            assert st["total"] == 1 and float(st["avg_rating"]) == 10 and st["top_genre"]
            assert gf.id not in [m.id for m in await r.similar(s, gf.id, user_id=1)]
    run(body)
