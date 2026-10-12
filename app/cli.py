"""Команды импорта:

    python -m app.cli seed                       # стартовая база (~60 фильмов), ключи не нужны
    python -m app.cli tmdb --pages 25            # топ-500 по числу голосов
    python -m app.cli tmdb --year-from 1960 --year-to 2025 --pages 3
    python -m app.cli tmdb-id 238 278 424        # конкретные фильмы по TMDB id
    python -m app.cli imdb-ratings               # свежие рейтинги IMDb из официальных датасетов
"""
import argparse
import asyncio
import logging
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.integrations.imdb_datasets import update_imdb_ratings
from app.integrations.tmdb import TMDB
from app.services.importer import import_from_tmdb, save_movies
from app.services.seed import load_seed

log = logging.getLogger("cli")


async def cmd_seed(_a) -> None:
    added, updated = await save_movies(SessionLocal, load_seed())
    print(f"Seed: добавлено {added}, обновлено {updated}")


async def cmd_tmdb(a) -> None:
    years = range(a.year_from, a.year_to + 1) if a.year_from else [None]
    total = [0, 0, 0]
    async with TMDB(get_settings().tmdb_api_key) as tmdb:
        for year in years:
            for page in range(a.start_page, a.start_page + a.pages):
                params = {"sort_by": a.sort, "vote_count.gte": a.min_votes}
                if year:
                    params["primary_release_year"] = year
                ids = await tmdb.discover(page, **params)
                if not ids:
                    break
                res = await import_from_tmdb(SessionLocal, tmdb, ids, refresh=a.refresh)
                total = [t + r for t, r in zip(total, res)]
                print(f"[{year or 'all'} p{page}] +{res[0]} ~{res[1]} skip {res[2]}  | итого +{total[0]} ~{total[1]}")
    print(f"Готово: добавлено {total[0]}, обновлено {total[1]}, пропущено {total[2]}")


async def cmd_tmdb_id(a) -> None:
    async with TMDB(get_settings().tmdb_api_key) as tmdb:
        added, updated, _ = await import_from_tmdb(SessionLocal, tmdb, a.ids, refresh=True)
    print(f"Добавлено {added}, обновлено {updated}")


async def cmd_imdb(a) -> None:
    n = await update_imdb_ratings(engine, Path(a.file) if a.file else None)
    print(f"Обновлено рейтингов IMDb: {n}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed").set_defaults(fn=cmd_seed)

    t = sub.add_parser("tmdb")
    t.add_argument("--pages", type=int, default=5, help="страниц по 20 фильмов (TMDB отдаёт максимум 500)")
    t.add_argument("--start-page", type=int, default=1)
    t.add_argument("--sort", default="vote_count.desc")
    t.add_argument("--min-votes", type=int, default=300)
    t.add_argument("--year-from", type=int)
    t.add_argument("--year-to", type=int, default=2026)
    t.add_argument("--refresh", action="store_true", help="обновить и уже имеющиеся фильмы")
    t.set_defaults(fn=cmd_tmdb)

    i = sub.add_parser("tmdb-id")
    i.add_argument("ids", type=int, nargs="+")
    i.set_defaults(fn=cmd_tmdb_id)

    r = sub.add_parser("imdb-ratings")
    r.add_argument("--file", help="локальный title.ratings.tsv.gz (иначе скачается)")
    r.set_defaults(fn=cmd_imdb)

    a = p.parse_args()
    asyncio.run(a.fn(a))


if __name__ == "__main__":
    main()
