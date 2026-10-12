from aiogram.filters.callback_data import CallbackData


class Nav(CallbackData, prefix="nav"):
    to: str  # home, back, search, genres, years, ratings, popular, random, mood, fav, seen, stats, noop, year_input


class L(CallbackData, prefix="l"):
    """Список фильмов по фильтру (жанр / годы / рейтинг / сортировка / страница)."""
    g: int = 0        # id жанра
    a: int = 0        # год от
    b: int = 0        # год до
    r: int = 0        # мин. рейтинг × 10
    w: int = 0        # 1 = не-англоязычное («мировое») кино
    s: str = "r"      # сортировка: r — рейтинг, p — популярность, n — новизна
    p: int = 1        # страница


class M(CallbackData, prefix="m"):
    id: int


class Act(CallbackData, prefix="a"):
    act: str          # fav | seen | rate | mk | sim
    id: int


class Rate(CallbackData, prefix="rt"):
    id: int
    v: int


class Lib(CallbackData, prefix="lib"):
    kind: str         # fav | seen
    p: int = 1


class Rnd(CallbackData, prefix="rnd"):
    a: str            # menu | dim | set | clr | go | any | reset
    d: str = ""       # измерение: g, dec, r, rt, c
    v: str = ""


class Rec(CallbackData, prefix="rec"):
    step: str         # mood | period | dur | again
    v: str = ""
