from dataclasses import dataclass


@dataclass(frozen=True)
class MovieFilter:
    """Единое описание условий выборки — используется списками, случайным выбором и подбором."""
    genre_ids: tuple[int, ...] = ()          # любой из перечисленных
    year_from: int | None = None
    year_to: int | None = None
    min_rating: float | None = None
    runtime_min: int | None = None
    runtime_max: int | None = None
    country: str | None = None               # ISO-код
    exclude_language: str | None = None      # напр. "en" → «мировое кино»
    exclude_watched_by: int | None = None    # Telegram ID
    min_votes: int = 0
    sort: str = "r"                          # r — рейтинг, p — популярность, n — новизна
