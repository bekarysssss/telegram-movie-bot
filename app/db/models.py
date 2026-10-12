from datetime import datetime

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Index,
                        Integer, SmallInteger, String, Table, Text, event, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.text import normalize_text
from app.db.base import Base


# ───────────── справочники ─────────────
class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)  # id жанра в TMDB
    name: Mapped[str] = mapped_column(String(64), unique=True)
    name_ru: Mapped[str] = mapped_column(String(64))

    def __str__(self) -> str:
        return self.name_ru


class Country(Base):
    __tablename__ = "countries"
    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))

    def __str__(self) -> str:
        return self.name


class Person(Base):
    """Режиссёры, сценаристы и актёры — одна таблица, роль хранится в movie_people."""
    __tablename__ = "people"
    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String(255), index=True)


class Keyword(Base):
    __tablename__ = "keywords"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)


movie_genres = Table(
    "movie_genres", Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_movie_genres_genre_movie", "genre_id", "movie_id"),
)
movie_countries = Table(
    "movie_countries", Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("country_code", ForeignKey("countries.code", ondelete="CASCADE"), primary_key=True),
    Index("ix_movie_countries_code_movie", "country_code", "movie_id"),
)
movie_keywords = Table(
    "movie_keywords", Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("keyword_id", ForeignKey("keywords.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_movie_keywords_keyword_movie", "keyword_id", "movie_id"),
)


class MoviePerson(Base):
    __tablename__ = "movie_people"
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), primary_key=True)  # director | writer | actor
    position: Mapped[int] = mapped_column(SmallInteger, default=0)

    person: Mapped[Person] = relationship(lazy="joined")

    __table_args__ = (Index("ix_movie_people_person_role", "person_id", "role"),)


# ───────────── фильмы ─────────────
class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    imdb_id: Mapped[str | None] = mapped_column(String(16), unique=True)

    title: Mapped[str] = mapped_column(String(512))
    original_title: Mapped[str | None] = mapped_column(String(512))
    search_text: Mapped[str] = mapped_column(Text, default="")  # нормализованные названия для поиска
    year: Mapped[int | None] = mapped_column(SmallInteger, index=True)
    runtime: Mapped[int | None] = mapped_column(SmallInteger)
    description: Mapped[str | None] = mapped_column(Text)
    poster_url: Mapped[str | None] = mapped_column(String(512))
    backdrop_url: Mapped[str | None] = mapped_column(String(512))
    trailer_url: Mapped[str | None] = mapped_column(String(512))
    age_rating: Mapped[str | None] = mapped_column(String(16))
    original_language: Mapped[str | None] = mapped_column(String(8))
    studio: Mapped[str | None] = mapped_column(String(255))
    budget: Mapped[int | None] = mapped_column(BigInteger)
    revenue: Mapped[int | None] = mapped_column(BigInteger)

    imdb_rating: Mapped[float | None] = mapped_column(Float)
    imdb_votes: Mapped[int | None] = mapped_column(Integer)
    tmdb_rating: Mapped[float | None] = mapped_column(Float)
    tmdb_votes: Mapped[int | None] = mapped_column(Integer)
    letterboxd_rating: Mapped[float | None] = mapped_column(Float)  # зарезервировано, не заполняется

    # «основной» рейтинг: IMDb, если есть, иначе TMDB (заполняется автоматически)
    rating: Mapped[float | None] = mapped_column(Float)
    votes: Mapped[int | None] = mapped_column(Integer)
    popularity: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())

    genres: Mapped[list[Genre]] = relationship(secondary=movie_genres, lazy="selectin", order_by=Genre.name)
    countries: Mapped[list[Country]] = relationship(secondary=movie_countries, lazy="selectin")
    keywords: Mapped[list[Keyword]] = relationship(secondary=movie_keywords, lazy="raise")
    people_links: Mapped[list[MoviePerson]] = relationship(lazy="raise", order_by=MoviePerson.position,
                                                           cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_movies_search_trgm", "search_text", postgresql_using="gin",
              postgresql_ops={"search_text": "gin_trgm_ops"}),
        Index("ix_movies_rating_votes", "rating", "votes"),
        Index("ix_movies_popularity", "popularity"),
    )

    def people(self, role: str, limit: int | None = None) -> list[str]:
        names = [l.person.name for l in self.people_links if l.role == role]
        return names[:limit] if limit else names

    def __str__(self) -> str:
        return f"{self.title} ({self.year})"


def _derive(_mapper, _conn, m: Movie) -> None:
    """Поля, которые всегда выводятся из других: поиск и «основной» рейтинг."""
    m.search_text = normalize_text(f"{m.title or ''} {m.original_title or ''}")
    if m.imdb_rating is not None:
        m.rating, m.votes = m.imdb_rating, m.imdb_votes
    else:
        m.rating, m.votes = m.tmdb_rating, m.tmdb_votes


event.listen(Movie, "before_insert", _derive)
event.listen(Movie, "before_update", _derive)


# ───────────── пользователи ─────────────
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)  # Telegram ID
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    def __str__(self) -> str:
        return f"{self.username or self.first_name or self.id}"


class UserFavorite(Base):
    __tablename__ = "user_favorites"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_user_favorites_user_created", "user_id", "created_at"),)


class UserWatched(Base):
    """Просмотренные фильмы + личная оценка 1–10 (rating может быть NULL)."""
    __tablename__ = "user_watched"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    watched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rating: Mapped[int | None] = mapped_column(SmallInteger)

    __table_args__ = (Index("ix_user_watched_user_at", "user_id", "watched_at"),)
