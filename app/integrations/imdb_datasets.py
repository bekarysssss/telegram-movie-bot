"""Обновление рейтингов IMDb из официальных датасетов (https://datasets.imdbws.com/).

Лицензия IMDb: только личное и некоммерческое использование — см. README.
"""
import asyncio
import gzip
import logging
import urllib.request
from collections.abc import Iterator
from pathlib import Path

log = logging.getLogger(__name__)
RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"


def iter_ratings(path: Path) -> Iterator[tuple[str, float, int]]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        next(f, None)  # заголовок: tconst averageRating numVotes
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 3:
                yield parts[0], float(parts[1]), int(parts[2])


async def update_imdb_ratings(engine, file: Path | None = None, batch: int = 5000) -> int:
    from sqlalchemy import bindparam, select, update

    from app.db.models import Movie

    if file is None:
        file = Path("data/downloads/title.ratings.tsv.gz")
        file.parent.mkdir(parents=True, exist_ok=True)
        log.info("Скачиваю %s …", RATINGS_URL)
        await asyncio.to_thread(urllib.request.urlretrieve, RATINGS_URL, file)

    async with engine.connect() as conn:
        ours = set((await conn.execute(select(Movie.imdb_id).where(Movie.imdb_id.is_not(None)))).scalars().all())
    stmt = (update(Movie.__table__).where(Movie.__table__.c.imdb_id == bindparam("b_imdb"))
            .values(imdb_rating=bindparam("b_rating"), imdb_votes=bindparam("b_votes"),
                    rating=bindparam("b_rating"), votes=bindparam("b_votes")))
    total, buf = 0, []

    async def flush(conn):
        nonlocal total, buf
        if buf:
            await conn.execute(stmt, buf)
            total += len(buf)
            buf = []

    async with engine.begin() as conn:
        for imdb_id, rating, votes in iter_ratings(file):
            if imdb_id in ours:
                buf.append({"b_imdb": imdb_id, "b_rating": rating, "b_votes": votes})
                if len(buf) >= batch:
                    await flush(conn)
        await flush(conn)
    return total
