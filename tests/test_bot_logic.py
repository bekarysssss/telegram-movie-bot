from app.bot.callbacks import L, Lib, Rec, Rnd
from app.bot.handlers.randomizer import rf_to_filter
from app.bot.handlers.recommend import build_filter
from app.bot.helpers import describe, l_to_filter


def test_callback_roundtrip_and_size():
    worst = L(g=10749, a=2020, b=2029, r=90, w=1, s="p", p=1000)
    packed = worst.pack()
    assert len(packed.encode()) <= 64
    assert L.unpack(packed) == worst
    assert Lib.unpack(Lib(kind="seen", p=3).pack()).p == 3
    assert len(Rnd(a="set", d="dec", v="2020").pack()) < 64 and len(Rec(step="dur", v="xl").pack()) < 64


def test_list_filter():
    f = l_to_filter(L(g=27, a=1970, b=1979, r=70, s="r"))
    assert f.genre_ids == (27,) and (f.year_from, f.year_to) == (1970, 1979) and f.min_rating == 7.0
    assert l_to_filter(L(w=1)).exclude_language == "en"
    assert l_to_filter(L(s="p")).min_votes == 0 and l_to_filter(L(s="r")).min_votes > 0


def test_describe():
    assert describe(L()) == "🎬 Все фильмы"
    assert "Ужасы" in describe(L(g=27)) and "1994" in describe(L(a=1994, b=1994))


def test_random_filter_example_from_spec():
    # Horror + 1970–1979 + IMDb 7+
    f = rf_to_filter({"g": "27", "dec": "1970", "r": "7.0"}, user_id=5)
    assert f.genre_ids == (27,) and (f.year_from, f.year_to) == (1970, 1979)
    assert f.min_rating == 7.0 and f.exclude_watched_by == 5


def test_recommend_filter():
    f = build_filter({"mood": "scary", "period": "old", "dur": "m"}, 1)
    assert f.genre_ids == (27,) and f.year_to == 1969 and (f.runtime_min, f.runtime_max) == (90, 120)
    assert build_filter({"mood": "good"}, 1).min_rating == 8.0
