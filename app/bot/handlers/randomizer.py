from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import Nav, Rnd
from app.bot.handlers.card import render_card
from app.bot.keyboards import back_row, btn, grid, kb
from app.bot.ui import show
from app.core.constants import COUNTRIES, DECADES, GENRE_BY_ID, GENRES, RATING_STEPS, RUNTIME_BUCKETS, country_ru, flag
from app.db import repo_movies as movies
from app.db.filters import MovieFilter
from app.db.models import User

router = Router()

DIMS = {"g": "🎭 Жанр", "dec": "📅 Десятилетие", "r": "⭐ Рейтинг", "rt": "🕐 Длительность", "c": "🌍 Страна"}


def value_label(dim: str, v) -> str:
    if dim == "g":
        return f"{GENRE_BY_ID[int(v)][3]} {GENRE_BY_ID[int(v)][2]}"
    if dim == "dec":
        return f"{v}–{int(v) + 9}"
    if dim == "r":
        return f"IMDb {float(v):.1f}+"
    if dim == "rt":
        return RUNTIME_BUCKETS[v][0]
    return f"{flag(v)} {country_ru(v, COUNTRIES.get(v, ('', v))[0])}"


def rf_to_filter(rf: dict, user_id: int) -> MovieFilter:
    dec = rf.get("dec")
    bucket = RUNTIME_BUCKETS.get(rf.get("rt"))
    return MovieFilter(
        genre_ids=(int(rf["g"]),) if rf.get("g") else (),
        year_from=int(dec) if dec else None,
        year_to=int(dec) + 9 if dec else None,
        min_rating=float(rf["r"]) if rf.get("r") else None,
        runtime_min=bucket[1] if bucket else None,
        runtime_max=bucket[2] if bucket else None,
        country=rf.get("c"),
        exclude_watched_by=user_id,
    )


async def show_builder(event, state: FSMContext) -> None:
    rf = (await state.get_data()).get("rf", {})
    await state.update_data(back="rnd", origin="home")
    rows = [[btn(f"{label}: {value_label(d, rf[d])}" if rf.get(d) else label, Rnd(a="dim", d=d))] for d, label in DIMS.items()]
    rows.append([btn("🎲 Выдать фильм", Rnd(a="go"))])
    rows.append([btn("🎲 Любой фильм", Rnd(a="any")), btn("🔄 Сбросить", Rnd(a="reset"))])
    rows.append(back_row())
    chosen = "\n".join(f"• {DIMS[d]}: {value_label(d, v)}" for d, v in rf.items() if v) or "Фильтры не выбраны — выпадет любой."
    await show(event, f"🎲 <b>Случайный фильм</b>\nЗадайте условия или жмите «Выдать фильм».\n\n{chosen}", kb(rows))


async def options(session: AsyncSession, dim: str) -> list[tuple[str, str]]:
    if dim == "g":
        return [(f"{e} {ru}", str(g)) for g, _en, ru, e in GENRES if g != 10770]
    if dim == "dec":
        return [(f"{d}–{d + 9}", str(d)) for d in DECADES]
    if dim == "r":
        return [(f"⭐ {r:.1f}+", str(r)) for r in RATING_STEPS]
    if dim == "rt":
        return [(label, key) for key, (label, _a, _b) in RUNTIME_BUCKETS.items()]
    return [(f"{flag(c)} {country_ru(c, n)}", c) for c, n in await movies.top_countries(session)]


@router.callback_query(Nav.filter(F.to == "random"))
async def open_random(cb: CallbackQuery, state: FSMContext) -> None:
    await show_builder(cb, state)
    await cb.answer()


@router.callback_query(Rnd.filter(F.a == "menu"))
async def rnd_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await show_builder(cb, state)
    await cb.answer()


@router.callback_query(Rnd.filter(F.a == "dim"))
async def rnd_dim(cb: CallbackQuery, callback_data: Rnd, session: AsyncSession) -> None:
    d = callback_data.d
    buttons = [btn(label, Rnd(a="set", d=d, v=value)) for label, value in await options(session, d)]
    rows = grid(buttons, 2) + [[btn("❌ Не важно", Rnd(a="clr", d=d))], [btn("🔙 Назад", Rnd(a="menu"))]]
    await show(cb, f"{DIMS[d]} — выберите значение", kb(rows))
    await cb.answer()


async def _update_rf(state: FSMContext, **changes) -> None:
    rf = dict((await state.get_data()).get("rf", {}))
    for k, v in changes.items():
        rf.pop(k, None) if v is None else rf.__setitem__(k, v)
    await state.update_data(rf=rf)


@router.callback_query(Rnd.filter(F.a == "set"))
async def rnd_set(cb: CallbackQuery, callback_data: Rnd, state: FSMContext) -> None:
    await _update_rf(state, **{callback_data.d: callback_data.v})
    await show_builder(cb, state)
    await cb.answer()


@router.callback_query(Rnd.filter(F.a == "clr"))
async def rnd_clear(cb: CallbackQuery, callback_data: Rnd, state: FSMContext) -> None:
    await _update_rf(state, **{callback_data.d: None})
    await show_builder(cb, state)
    await cb.answer()


@router.callback_query(Rnd.filter(F.a == "reset"))
async def rnd_reset(cb: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(rf={})
    await show_builder(cb, state)
    await cb.answer("Фильтры сброшены")


async def _roll(cb: CallbackQuery, session: AsyncSession, user: User, state: FSMContext, rf: dict) -> None:
    movie = await movies.random_movie(session, rf_to_filter(rf, user.id))
    if movie is None:
        await cb.answer("По таким условиям фильмов не нашлось (или всё уже просмотрено). Смягчите фильтры.", show_alert=True)
        return
    await state.update_data(back="rnd")
    await render_card(cb, session, user.id, movie.id, state)
    await cb.answer()


@router.callback_query(Rnd.filter(F.a == "go"))
async def rnd_go(cb: CallbackQuery, session: AsyncSession, user: User, state: FSMContext) -> None:
    await _roll(cb, session, user, state, (await state.get_data()).get("rf", {}))


@router.callback_query(Rnd.filter(F.a == "any"))
async def rnd_any(cb: CallbackQuery, session: AsyncSession, user: User, state: FSMContext) -> None:
    await state.update_data(rf={})
    await _roll(cb, session, user, state, {})
