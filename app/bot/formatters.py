import html

from app.core.constants import GENRE_BY_ID, country_ru, flag
from app.db.models import Movie

MAX_DESC = 480


def _short(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def card_text(m: Movie) -> str:
    e = html.escape
    lines = [f"🎬 <b>{e(m.title)}</b>"]
    if m.original_title and m.original_title != m.title:
        lines.append(f"<i>{e(m.original_title)}</i>")
    meta = " · ".join(x for x in (str(m.year) if m.year else "", f"{m.runtime} мин" if m.runtime else "", m.age_rating or "") if x)
    if meta:
        lines += ["", f"<b>{e(meta)}</b>"]
    if m.countries:
        lines.append(" · ".join(f"{flag(c.code)} {e(country_ru(c.code, c.name))}" for c in m.countries[:3]))
    if m.genres:
        lines.append("🎭 " + " · ".join(e(g.name_ru) for g in m.genres))
    ratings = []
    if m.imdb_rating:
        ratings.append(f"⭐ IMDb: {m.imdb_rating:.1f}")
    if m.tmdb_rating:
        ratings.append(f"⭐ TMDB: {m.tmdb_rating:.1f}")
    if ratings:
        lines += ["", "   ".join(ratings)]
    directors, cast = m.people("director", 3), m.people("actor", 5)
    if directors:
        lines += ["", f"🎬 Режиссёр: {e(', '.join(directors))}"]
    if cast:
        lines += ["", "👥 В ролях:", e(", ".join(cast)) + "..."]
    lines += ["", f"📝 {e(_short(m.description, MAX_DESC))}" if m.description else
              "📝 <i>Описание появится после импорта из TMDB.</i>"]
    return "\n".join(lines)


def movie_label(m: Movie, idx: int | None = None, my: int | None = None) -> str:
    s = f"{idx}. " if idx else ""
    s += f"{m.title} ({m.year})" if m.year else m.title
    if m.rating:
        s += f" · ⭐{m.rating:.1f}"
    if my:
        s += f" · моя {my}"
    return s


def search_label(m: Movie) -> str:
    parts = [f"🎬 {m.title} ({m.year})" if m.year else f"🎬 {m.title}"]
    if m.countries:
        parts.append(flag(m.countries[0].code))
    if m.rating:
        parts.append(f"⭐{m.rating:.1f}")
    return " · ".join(parts)


def genre_label(gid: int) -> str:
    _, _, ru, emoji = GENRE_BY_ID[gid]
    return f"{emoji} {ru}"


def stats_text(s: dict) -> str:
    if not s["total"]:
        return "📊 <b>Моя статистика</b>\n\nПока пусто. Отмечайте фильмы кнопкой «✅ Я смотрел», и здесь появится статистика."
    avg = f"{float(s['avg_rating']):.1f}" if s["avg_rating"] is not None else "—"
    country = s["top_country"]
    country_line = f"{flag(country[0])} {country_ru(country[0], country[1])}" if country else "—"
    return "\n".join([
        "📊 <b>Моя статистика</b>", "",
        f"🎬 Просмотрено: <b>{s['total']}</b>",
        f"⭐ Средняя оценка: <b>{avg}</b>",
        f"🎭 Любимый жанр: {html.escape(s['top_genre'] or '—')}",
        f"📅 Любимое десятилетие: {html.escape(s['top_decade'] or '—')}",
        f"🎬 Любимый режиссёр: {html.escape(s['top_director'] or '—')}",
        f"🌍 Самая частая страна: {country_line}", "",
        f"За этот месяц: {s['month_cnt']} · за этот год: {s['year_cnt']}",
        f"Стран: {s['countries']} · режиссёров: {s['directors']} · жанров: {s['genres']}",
    ])
