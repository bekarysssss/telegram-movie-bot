from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import L, Lib, Nav
from app.bot.handlers.browse import render_list
from app.bot.handlers.library import render_lib
from app.bot.handlers.randomizer import show_builder
from app.bot.handlers.recommend import show_results
from app.bot.handlers.search import render_search
from app.bot.keyboards import main_menu
from app.bot.ui import show
from app.db import repo_movies as movies
from app.db.models import User

router = Router()


@router.callback_query(Nav.filter(F.to == "back"))
async def go_back(cb: CallbackQuery, session: AsyncSession, user: User, state: FSMContext) -> None:
    """Возврат из карточки туда, откуда пришли (список, поиск, рандом, подборка...)."""
    data = await state.get_data()
    back = data.get("back") or ""
    if back.startswith("l:"):
        await render_list(cb, session, state, L.unpack(back))
    elif back.startswith("lib:"):
        await render_lib(cb, session, state, user, Lib.unpack(back))
    elif back == "sr" and data.get("last_query"):
        await render_search(cb, session, state, data["last_query"])
    elif back == "rnd":
        await show_builder(cb, state)
    elif back == "recres":
        await show_results(cb, await movies.get_many(session, data.get("rec_ids", [])))
    else:
        await show(cb, "🎬 <b>Что хотите сделать?</b>", main_menu())
    await cb.answer()
