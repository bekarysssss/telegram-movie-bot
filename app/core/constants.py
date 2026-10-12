# (tmdb_id, english, russian, emoji)
GENRES: list[tuple[int, str, str, str]] = [
    (28, "Action", "Боевик", "⚔️"),
    (12, "Adventure", "Приключения", "🧭"),
    (16, "Animation", "Мультфильм", "🎨"),
    (35, "Comedy", "Комедия", "😂"),
    (80, "Crime", "Криминал", "🔪"),
    (99, "Documentary", "Документальный", "🎞"),
    (18, "Drama", "Драма", "🎭"),
    (10751, "Family", "Семейный", "👨‍👩‍👧"),
    (14, "Fantasy", "Фэнтези", "🧙"),
    (36, "History", "История", "🏛"),
    (27, "Horror", "Ужасы", "👻"),
    (10402, "Music", "Музыка", "🎵"),
    (9648, "Mystery", "Детектив", "🕵️"),
    (10749, "Romance", "Мелодрама", "❤️"),
    (878, "Science Fiction", "Фантастика", "🚀"),
    (10770, "TV Movie", "ТВ-фильм", "📺"),
    (53, "Thriller", "Триллер", "😰"),
    (10752, "War", "Военный", "🪖"),
    (37, "Western", "Вестерн", "🤠"),
]
GENRE_BY_ID = {g[0]: g for g in GENRES}
GENRE_ID_BY_NAME = {g[1].lower(): g[0] for g in GENRES} | {"sci-fi": 878}

# ISO 3166-1 -> (english, russian)
COUNTRIES: dict[str, tuple[str, str]] = {
    "US": ("United States of America", "США"), "GB": ("United Kingdom", "Великобритания"),
    "FR": ("France", "Франция"), "DE": ("Germany", "Германия"), "IT": ("Italy", "Италия"),
    "JP": ("Japan", "Япония"), "KR": ("South Korea", "Южная Корея"), "RU": ("Russia", "Россия"),
    "SU": ("Soviet Union", "СССР"), "CA": ("Canada", "Канада"), "AU": ("Australia", "Австралия"),
    "NZ": ("New Zealand", "Новая Зеландия"), "ES": ("Spain", "Испания"), "MX": ("Mexico", "Мексика"),
    "BR": ("Brazil", "Бразилия"), "IN": ("India", "Индия"), "CN": ("China", "Китай"),
    "HK": ("Hong Kong", "Гонконг"), "PL": ("Poland", "Польша"), "SE": ("Sweden", "Швеция"),
    "DK": ("Denmark", "Дания"), "IE": ("Ireland", "Ирландия"), "AR": ("Argentina", "Аргентина"),
    "KZ": ("Kazakhstan", "Казахстан"), "UA": ("Ukraine", "Украина"), "TR": ("Turkey", "Турция"),
}

DECADES = [2020, 2010, 2000, 1990, 1980, 1970, 1960, 1950, 1940, 1930, 1920]
RATING_STEPS = [9.0, 8.5, 8.0, 7.5, 7.0]

# key -> (label, min, max) в минутах
RUNTIME_BUCKETS = {
    "s": ("< 90 мин", 0, 89),
    "m": ("90–120 мин", 90, 120),
    "l": ("120–150 мин", 121, 150),
    "xl": ("150+ мин", 151, 999),
}

# key -> (label, genre ids (любой из), min rating)
MOODS = {
    "fun": ("😄 Весёлое", (35,), 6.5),
    "scary": ("😨 Страшное", (27,), 6.0),
    "sad": ("😢 Грустное", (18,), 7.5),
    "smart": ("🧠 Умное / сложное", (9648, 878), 7.5),
    "love": ("❤️ Романтическое", (10749,), 6.5),
    "tense": ("🔥 Напряжённое", (53,), 6.5),
    "good": ("🎬 Просто хороший фильм", (), 8.0),
}


def flag(code: str) -> str:
    code = (code or "").upper()
    if len(code) != 2 or not code.isalpha():
        return "🏳️"
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in code)


def country_ru(code: str, fallback: str | None = None) -> str:
    return COUNTRIES.get(code, (None, fallback or code))[1]
