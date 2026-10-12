from dataclasses import dataclass, field


@dataclass
class MovieData:
    """Нормализованный фильм: единый формат для любого источника (TMDB, seed, ...)."""
    title: str
    original_title: str | None = None
    year: int | None = None
    runtime: int | None = None
    description: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    trailer_url: str | None = None
    age_rating: str | None = None
    original_language: str | None = None
    studio: str | None = None
    budget: int | None = None
    revenue: int | None = None
    tmdb_id: int | None = None
    imdb_id: str | None = None
    tmdb_rating: float | None = None
    tmdb_votes: int | None = None
    imdb_rating: float | None = None
    imdb_votes: int | None = None
    popularity: float | None = None
    genre_ids: list[int] = field(default_factory=list)
    countries: list[tuple[str, str]] = field(default_factory=list)       # (ISO, name)
    directors: list[tuple[str, int | None]] = field(default_factory=list)  # (name, tmdb person id)
    writers: list[tuple[str, int | None]] = field(default_factory=list)
    cast: list[tuple[str, int | None]] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


SCALAR_FIELDS = (
    "title", "original_title", "year", "runtime", "description", "poster_url", "backdrop_url", "trailer_url",
    "age_rating", "original_language", "studio", "budget", "revenue", "tmdb_id", "imdb_id", "tmdb_rating",
    "tmdb_votes", "imdb_rating", "imdb_votes", "popularity",
)
