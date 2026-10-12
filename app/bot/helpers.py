from app.bot.callbacks import L
from app.core.config import get_settings
from app.core.constants import GENRE_BY_ID
from app.db.filters import MovieFilter

SORT_NAMES = {"r": "по рейтингу", "p": "по популярности", "n": "по новизне"}


def l_to_filter(cb: L) -> MovieFilter:
    return MovieFilter(
        genre_ids=(cb.g,) if cb.g else (),
        year_from=cb.a or None,
        year_to=cb.b or None,
        min_rating=cb.r / 10 if cb.r else None,
        exclude_language="en" if cb.w else None,
        min_votes=get_settings().min_votes if cb.s == "r" else 0,
        sort=cb.s,
    )


def describe(cb: L) -> str:
    parts = []
    if cb.g:
        _, en, ru, emoji = GENRE_BY_ID[cb.g]
        parts.append(f"{emoji} {ru}")
    if cb.a and cb.b:
        parts.append(str(cb.a) if cb.a == cb.b else f"{cb.a}–{cb.b}")
    elif cb.b:
        parts.append(f"до {cb.b + 1}")
    if cb.r:
        parts.append(f"⭐ {cb.r / 10:.1f}+")
    if cb.w:
        parts.append("🌍 Мировое кино")
    return " · ".join(parts) or "🎬 Все фильмы"
