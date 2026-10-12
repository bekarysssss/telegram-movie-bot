import math

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import L, Nav
from app.bot.helpers import describe, l_to_filter
from app.bot.keyboards import back_row, btn, grid, kb, list_keyboard
from app.bot.ui import show
from app.core.config import get_settings
from app.core.constants import DECADES, GENRES, RATING_STEPS
from app.db import repo_movies as movies

router = Router()


class BrowseSt(StatesGroup):
    year = State()


async def render_list(event, session: AsyncSession, state: FSMContext, cb: L) -> None:
    per_page = get_settings().per_page
    items, total = await movies.paginate(session, l_to_filter(cb), cb.p, per_page)
    pages = max(1, math.ceil(total / per_page))
    origin = (await state.get_data()).get("origin", "home")
    await state.update_data(back=cb.pack())
    if not total:
        text = f"<b>{describe(cb)}</b>\n\nПока ничего не нашлось. База растёт — загляните позже."
        await show(event, text, kb([back_row(origin)]))
        return
    text = f"<b>{describe(cb)}</b>\nНайдено: {total}"
    await show(event, text, list_keyboard(items, cb, pages, origin, (cb.p - 1) * per_page + 1))


@router.callback_query(L.filter())
async def cb_list(cb: CallbackQuery, callback_data: L, session: AsyncSession, state: FSMContext) -> None:
    await render_list(cb, session, state, callback_data)
    await cb.answer()


@router.callback_query(Nav.filter(F.to == "genres"))
async def genres_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(origin="genres")
    buttons = [btn(f"{emoji} {ru}", L(g=gid)) for gid, _en, ru, emoji in GENRES if gid != 10770]
    await show(cb, "🎭 <b>Выберите жанр</b>", kb(grid(buttons) + [back_row()]))
    await cb.answer()


@router.callback_query(Nav.filter(F.to == "years"))
async def years_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.update_data(origin="years")
    buttons = [btn(f"{d}–{d + 9}", L(a=d, b=d + 9)) for d in DECADES] + [btn("До 1920", L(b=1919))]
    rows = grid(buttons, 3) + [[btn("✍️ Ввести год", Nav(to="year_input"))], back_row()]
    await show(cb, "📅 <b>Выберите период</b>", kb(rows))
    await cb.answer()


@router.callback_query(Nav.filter(F.to == "year_input"))
async def year_input(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BrowseSt.year)
    await show(cb, "📅 Введите год, например <code>1994</code>", kb([back_row("years")]))
    await cb.answer()


@router.message(BrowseSt.year, F.text)
async def year_entered(m: Message, session: AsyncSession, state: FSMContext) -> None:
    text = m.text.strip()
    if not (text.isdigit() and 1888 <= int(text) <= 2100):
        await m.answer("Введите год числом от 1888, например <code>1994</code>")
        return
    year = int(text)
    await state.set_state(None)
    await state.update_data(origin="years")
    await render_list(m, session, state, L(a=year, b=year))


@router.callback_query(Nav.filter(F.to == "ratings"))
async def ratings_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(origin="ratings")
    buttons = [btn(f"⭐ {r:.1f}+", L(r=int(r * 10))) for r in RATING_STEPS]
    await show(cb, "⭐ <b>Минимальный рейтинг</b>\nСортировку можно менять в самом списке.",
               kb(grid(buttons) + [back_row()]))
    await cb.answer()


@router.callback_query(Nav.filter(F.to == "popular"))
async def popular_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(origin="popular")
    rows = [
        [btn("🔥 Сейчас популярно", L(s="p"))],
        [btn("🏆 Лучшие фильмы", L(r=80, s="r"))],
        [btn("🎬 Классика (до 1980)", L(b=1979, r=75, s="r"))],
        [btn("🌍 Мировое кино", L(w=1, r=70, s="r"))],
        back_row(),
    ]
    await show(cb, "🔥 <b>Популярное</b>", kb(rows))
    await cb.answer()
