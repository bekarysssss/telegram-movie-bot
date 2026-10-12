"""Веб-админка (SQLAdmin): CRUD фильмов/жанров/пользователей + JSON-статистика.

Запуск: uvicorn app.api.main:app --host 0.0.0.0 --port 8000  →  http://localhost:8000/admin
"""
import secrets

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.core.config import get_settings
from app.db.models import Genre, Movie, User
from app.db.repo_stats import bot_stats
from app.db.session import SessionLocal, engine

settings = get_settings()
app = FastAPI(title="Movie Bot Admin", docs_url=None, redoc_url=None)
basic = HTTPBasic()


def _check(username: str, password: str) -> bool:
    return (secrets.compare_digest(username, settings.admin_username)
            and secrets.compare_digest(password, settings.admin_password))


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        if _check(str(form.get("username", "")), str(form.get("password", ""))):
            request.session.update({"admin": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin"))


class MovieAdmin(ModelView, model=Movie):
    name, name_plural, icon = "Фильм", "Фильмы", "fa-solid fa-film"
    page_size = 50
    column_list = [Movie.id, Movie.title, Movie.original_title, Movie.year, Movie.rating, Movie.votes, Movie.imdb_id]
    column_searchable_list = [Movie.title, Movie.original_title, Movie.imdb_id]
    column_sortable_list = [Movie.id, Movie.title, Movie.year, Movie.rating, Movie.votes, Movie.popularity]
    column_default_sort = [(Movie.votes, True)]
    # «основной» рейтинг и search_text вычисляются автоматически, связи с людьми правятся импортом
    form_columns = [Movie.title, Movie.original_title, Movie.year, Movie.runtime, Movie.description,
                    Movie.poster_url, Movie.backdrop_url, Movie.trailer_url, Movie.age_rating,
                    Movie.original_language, Movie.studio, Movie.imdb_id, Movie.tmdb_id,
                    Movie.imdb_rating, Movie.imdb_votes, Movie.tmdb_rating, Movie.tmdb_votes,
                    Movie.popularity, Movie.genres]
    column_details_exclude_list = [Movie.search_text]


class GenreAdmin(ModelView, model=Genre):
    name, name_plural, icon = "Жанр", "Жанры", "fa-solid fa-masks-theater"
    column_list = [Genre.id, Genre.name, Genre.name_ru]


class UserAdmin(ModelView, model=User):
    name, name_plural, icon = "Пользователь", "Пользователи", "fa-solid fa-users"
    can_create = False
    column_list = [User.id, User.username, User.first_name, User.created_at, User.last_seen_at, User.is_blocked]
    column_default_sort = [(User.created_at, True)]


admin = Admin(app, engine, authentication_backend=AdminAuth(secret_key=settings.admin_secret_key),
              title="Movie Bot — админка")
for view in (MovieAdmin, GenreAdmin, UserAdmin):
    admin.add_view(view)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/stats")
async def stats(creds: HTTPBasicCredentials = Depends(basic)) -> dict:
    if not _check(creds.username, creds.password):
        raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})
    async with SessionLocal() as session:
        return await bot_stats(session)
