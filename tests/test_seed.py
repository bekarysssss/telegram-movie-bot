from app.core.constants import GENRE_BY_ID
from app.services.seed import load_seed


def test_seed_is_valid():
    items = load_seed()
    assert len(items) >= 50
    imdb = [i.imdb_id for i in items]
    assert len(imdb) == len(set(imdb)), "дубликаты imdb_id"
    for it in items:
        assert it.imdb_id.startswith("tt") and it.title and it.original_title
        assert 1888 < it.year < 2100 and 40 < it.runtime < 400
        assert 1 <= it.imdb_rating <= 10
        assert it.genre_ids and all(g in GENRE_BY_ID for g in it.genre_ids)
        assert it.countries and it.directors and it.cast
