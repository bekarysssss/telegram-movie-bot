"""Клиент TMDB API v3 + превращение ответа в MovieData.

Данные TMDB бесплатны для некоммерческого использования при условии указания атрибуции
(см. README и команду /about в боте).
"""
import asyncio
import logging

import httpx

from app.services.types import MovieData

log = logging.getLogger(__name__)

API = "https://api.themoviedb.org/3"
IMG = "https://image.tmdb.org/t/p"
APPEND = "credits,keywords,videos,release_dates"


class TMDB:
    def __init__(self, api_key: str, language: str = "ru-RU", timeout: float = 20):
        if not api_key:
            raise RuntimeError("TMDB_API_KEY не задан (см. .env.example)")
        headers, self._params = {}, {}
        if api_key.startswith("eyJ"):  # v4 Read Access Token
            headers["Authorization"] = f"Bearer {api_key}"
        else:                          # v3 API key
            self._params["api_key"] = api_key
        self.language = language
        self._client = httpx.AsyncClient(base_url=API, headers=headers, timeout=timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self._client.aclose()

    async def _get(self, path: str, **params) -> dict | None:
        for attempt in range(5):
            try:
                r = await self._client.get(path, params={**self._params, **params})
            except httpx.TransportError as e:
                log.warning("TMDB network error %s (try %d)", e, attempt + 1)
                await asyncio.sleep(2 ** attempt)
                continue
            if r.status_code == 429:
                await asyncio.sleep(int(r.headers.get("Retry-After", 2)) + 1)
                continue
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"TMDB: не удалось получить {path}")

    async def discover(self, page: int = 1, **params) -> list[int]:
        data = await self._get("/discover/movie", page=page, language=self.language, include_adult="false", **params)
        return [m["id"] for m in (data or {}).get("results", [])]

    async def movie(self, tmdb_id: int) -> dict | None:
        return await self._get(f"/movie/{tmdb_id}", language=self.language, append_to_response=APPEND,
                               include_video_language="ru,en,null")


def _img(path: str | None, size: str) -> str | None:
    return f"{IMG}/{size}{path}" if path else None


def _pick_trailer(videos: list[dict]) -> str | None:
    yt = [v for v in videos if v.get("site") == "YouTube" and v.get("type") == "Trailer"]
    yt.sort(key=lambda v: (v.get("iso_639_1") != "ru", not v.get("official"), v.get("published_at") or ""))
    return f"https://www.youtube.com/watch?v={yt[0]['key']}" if yt else None


def _age_rating(release_dates: list[dict]) -> str | None:
    by_country = {r["iso_3166_1"]: r["release_dates"] for r in release_dates}
    for country in ("RU", "US"):
        for rd in by_country.get(country, []):
            if rd.get("certification"):
                return rd["certification"]
    return None


def parse_tmdb(d: dict) -> MovieData:
    """Чистая функция: ответ /movie/{id}?append_to_response=... → MovieData."""
    crew = (d.get("credits") or {}).get("crew", [])
    cast = (d.get("credits") or {}).get("cast", [])
    people = lambda items: [(p["name"], p.get("id")) for p in items]  # noqa: E731
    release = d.get("release_date") or ""
    companies = d.get("production_companies") or []
    votes = d.get("vote_count") or 0
    return MovieData(
        tmdb_id=d["id"],
        imdb_id=d.get("imdb_id") or None,
        title=d.get("title") or d.get("original_title") or "Без названия",
        original_title=d.get("original_title"),
        year=int(release[:4]) if release[:4].isdigit() else None,
        runtime=d.get("runtime") or None,
        description=(d.get("overview") or "").strip() or None,
        poster_url=_img(d.get("poster_path"), "w500"),
        backdrop_url=_img(d.get("backdrop_path"), "w780"),
        trailer_url=_pick_trailer((d.get("videos") or {}).get("results", [])),
        age_rating=_age_rating((d.get("release_dates") or {}).get("results", [])),
        original_language=d.get("original_language"),
        studio=companies[0]["name"] if companies else None,
        budget=d.get("budget") or None,
        revenue=d.get("revenue") or None,
        tmdb_rating=round(d["vote_average"], 1) if votes and d.get("vote_average") else None,
        tmdb_votes=votes or None,
        popularity=d.get("popularity"),
        genre_ids=[g["id"] for g in d.get("genres", [])],
        countries=[(c["iso_3166_1"], c["name"]) for c in d.get("production_countries", [])],
        directors=people([c for c in crew if c.get("job") == "Director"]),
        writers=people([c for c in crew if c.get("job") in ("Writer", "Screenplay", "Story")]),
        cast=people(cast[:12]),
        keywords=[k["name"] for k in (d.get("keywords") or {}).get("keywords", [])][:20],
    )
