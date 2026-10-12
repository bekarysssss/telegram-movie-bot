"""Стартовая база (data/seed_movies.json): бот работает сразу, без API-ключей."""
import json
from pathlib import Path

from app.core.constants import COUNTRIES, GENRE_ID_BY_NAME
from app.services.types import MovieData

SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "seed_movies.json"


def load_seed(path: Path = SEED_FILE) -> list[MovieData]:
    # строка: [imdb_id, title_ru, title_orig, year, runtime, [countries], [genres], director, [cast], imdb_rating]
    items = []
    for imdb, title, orig, year, runtime, countries, genres, director, cast, rating in json.loads(path.read_text("utf-8")):
        items.append(MovieData(
            title=title, original_title=orig, year=year, runtime=runtime, imdb_id=imdb, imdb_rating=rating,
            genre_ids=[GENRE_ID_BY_NAME[g.lower()] for g in genres],
            countries=[(c, COUNTRIES[c][0]) for c in countries],
            directors=[(director, None)], cast=[(a, None) for a in cast],
        ))
    return items
