from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = ""
    bot_name: str = "Movie Finder"
    admin_ids: str = ""

    database_url: str = "postgresql+asyncpg://movies:movies@localhost:5432/movies"
    redis_url: str = ""

    tmdb_api_key: str = ""

    admin_username: str = "admin"
    admin_password: str = "change-me"
    admin_secret_key: str = "change-me-too"

    per_page: int = 8
    min_votes: int = 1000

    @property
    def admin_id_set(self) -> set[int]:
        return {int(x) for x in self.admin_ids.replace(" ", "").split(",") if x.isdigit()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
