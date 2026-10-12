from app.integrations.tmdb import parse_tmdb

SAMPLE = {
    "id": 238, "imdb_id": "tt0068646", "title": "Крёстный отец", "original_title": "The Godfather",
    "release_date": "1972-03-14", "runtime": 175, "overview": " Описание. ", "poster_path": "/p.jpg",
    "backdrop_path": None, "original_language": "en", "vote_average": 8.69, "vote_count": 20000,
    "popularity": 99.5, "budget": 6000000, "revenue": 245000000,
    "genres": [{"id": 18, "name": "Драма"}, {"id": 80, "name": "Криминал"}],
    "production_countries": [{"iso_3166_1": "US", "name": "United States of America"}],
    "production_companies": [{"name": "Paramount Pictures"}],
    "credits": {
        "cast": [{"id": 3084, "name": "Marlon Brando"}, {"id": 1158, "name": "Al Pacino"}],
        "crew": [{"id": 1776, "name": "Francis Ford Coppola", "job": "Director"},
                 {"id": 1, "name": "Mario Puzo", "job": "Screenplay"}, {"id": 2, "name": "X", "job": "Editor"}],
    },
    "keywords": {"keywords": [{"name": "mafia"}, {"name": "italy"}]},
    "videos": {"results": [
        {"site": "YouTube", "type": "Teaser", "key": "bad"},
        {"site": "YouTube", "type": "Trailer", "key": "en1", "iso_639_1": "en", "official": True},
        {"site": "YouTube", "type": "Trailer", "key": "ru1", "iso_639_1": "ru", "official": False}]},
    "release_dates": {"results": [{"iso_3166_1": "US", "release_dates": [{"certification": "R"}]}]},
}


def test_parse_full():
    d = parse_tmdb(SAMPLE)
    assert (d.tmdb_id, d.imdb_id, d.year, d.runtime) == (238, "tt0068646", 1972, 175)
    assert d.description == "Описание."
    assert d.poster_url == "https://image.tmdb.org/t/p/w500/p.jpg" and d.backdrop_url is None
    assert d.tmdb_rating == 8.7 and d.tmdb_votes == 20000
    assert d.genre_ids == [18, 80] and d.countries == [("US", "United States of America")]
    assert d.directors == [("Francis Ford Coppola", 1776)] and d.writers == [("Mario Puzo", 1)]
    assert [n for n, _ in d.cast] == ["Marlon Brando", "Al Pacino"]
    assert d.keywords == ["mafia", "italy"] and d.studio == "Paramount Pictures" and d.age_rating == "R"
    assert d.trailer_url.endswith("ru1"), "русский трейлер предпочтительнее"


def test_parse_minimal_does_not_crash():
    d = parse_tmdb({"id": 1, "original_title": "X", "vote_average": 0, "vote_count": 0})
    assert d.title == "X" and d.year is None and d.tmdb_rating is None and d.genre_ids == []
