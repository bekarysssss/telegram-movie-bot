import math

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import Lib, Nav
from app.bot.keyboards import back_row, kb, lib_keyboard
from app.bot.ui import show
from app.core.config import get_settings
from app.db import repo_users as users
from app.db.models import User

router = Router()

TITLES = {"fav": "❤️ <b>Избранное</b>", "seen": "✅ <b>Мои просмотренные</b>"}
EMPTY = {
    "fav": "Здесь пока пусто. Нажимайте «❤️ В избранное» в карточке фильма.",
    "seen": "Здесь пока пусто. Нажимайте «✅ Я смотрел» в карточке фильма.",
}


async def render_lib(event, session: AsyncSession, state: FSMContext, user: User, cb: Lib) -> None:
    per_page = get_settings().per_page
    fetch = users.list_favorites if cb.kind == "fav" else users.list_watched
    items, total = await fetch(session, user.id, cb.p, per_page)
    await state.update_data(back=cb.pack(), origin="home")
    if not total:
        await show(event, f"{TITLES[cb.kind]}\n\n{EMPTY[cb.kind]}", kb([back_row()]))
        return
    pages = max(1, math.ceil(total / per_page))
    await show(event, f"{TITLES[cb.kind]}\nВсего: {total}",
               lib_keyboard(items, cb, pages, (cb.p - 1) * per_page + 1))


@router.callback_query(Nav.filter(F.to.in_({"fav", "seen"})))
async def open_lib(cb: CallbackQuery, callback_data: Nav, session: AsyncSession, user: User, state: FSMContext) -> None:
    await render_lib(cb, session, state, user, Lib(kind=callback_data.to))
    await cb.answer()


@router.callback_query(Lib.filter())
async def lib_page(cb: CallbackQuery, callback_data: Lib, session: AsyncSession, user: User, state: FSMContext) -> None:
    await render_lib(cb, session, state, user, callback_data)
    await cb.answer()
