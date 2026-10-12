import html

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import M, Nav
from app.bot.formatters import search_label
from app.bot.keyboards import back_row, btn, kb
from app.bot.ui import show
from app.db import repo_movies as movies

router = Router()


class SearchSt(StatesGroup):
    query = State()


async def render_search(event, session: AsyncSession, state: FSMContext, query: str) -> None:
    found = await movies.search(session, query)
    await state.update_data(last_query=query, back="sr", origin="home")
    if not found:
        text = (f"По запросу «{html.escape(query)}» ничего не найдено.\n"
                "Попробуйте другое название — русское или оригинальное.")
        await show(event, text, kb([back_row()]))
        return
    rows = [[btn(search_label(m), M(id=m.id))] for m in found]
    rows.append(back_row())
    await show(event, f"🔎 Результаты по запросу «{html.escape(query)}»:", kb(rows))


@router.callback_query(Nav.filter(F.to == "search"))
async def search_prompt(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchSt.query)
    await show(cb, "🔎 Введите название фильма\nНапример: <code>The Godfather</code> или <code>крёстный отец</code>",
               kb([back_row()]))
    await cb.answer()


# Любой обычный текст (не команда) — тоже поиск: пользователю не нужно жать кнопку.
@router.message(SearchSt.query, F.text, ~F.text.startswith("/"))
@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def search_text(m: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.set_state(SearchSt.query)
    await render_search(m, session, state, m.text.strip()[:100])
