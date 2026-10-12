from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import Act, M, Rate
from app.bot.formatters import card_text
from app.bot.keyboards import back_row, btn, card_keyboard, kb, movies_list, rating_keyboard
from app.bot.ui import show
from app.db import repo_movies as movies
from app.db import repo_users as users
from app.db.models import User

router = Router()


async def _keyboard(session, user_id, movie, state):
    fav, seen, my = await users.flags(session, user_id, movie.id)
    back = (await state.get_data()).get("back")
    return card_keyboard(movie, fav, seen, my, back)


async def render_card(event, session: AsyncSession, user_id: int, movie_id: int, state: FSMContext) -> bool:
    movie = await movies.get_movie(session, movie_id)
    if movie is None:
        return False
    await show(event, card_text(movie), await _keyboard(session, user_id, movie, state), photo=movie.poster_url)
    return True


async def _refresh(cb: CallbackQuery, session, user: User, movie_id: int, state: FSMContext) -> None:
    movie = await movies.get_movie(session, movie_id)
    await cb.message.edit_reply_markup(reply_markup=await _keyboard(session, user.id, movie, state))


@router.callback_query(M.filter())
async def open_card(cb: CallbackQuery, callback_data: M, session: AsyncSession, user: User, state: FSMContext) -> None:
    if not await render_card(cb, session, user.id, callback_data.id, state):
        await cb.answer("Фильм не найден", show_alert=True)
        return
    await cb.answer()


@router.callback_query(Act.filter(F.act == "fav"))
async def act_fav(cb: CallbackQuery, callback_data: Act, session: AsyncSession, user: User, state: FSMContext) -> None:
    added = await users.toggle_favorite(session, user.id, callback_data.id)
    await session.flush()
    await cb.answer("Добавлено в избранное ❤️" if added else "Убрано из избранного")
    await _refresh(cb, session, user, callback_data.id, state)


@router.callback_query(Act.filter(F.act == "seen"))
async def act_seen(cb: CallbackQuery, callback_data: Act, session: AsyncSession, user: User, state: FSMContext) -> None:
    seen = await users.toggle_watched(session, user.id, callback_data.id)
    await session.flush()
    await cb.answer("Отмечено как просмотренное ✅ Теперь можно поставить оценку" if seen else "Убрано из просмотренных")
    await _refresh(cb, session, user, callback_data.id, state)


@router.callback_query(Act.filter(F.act == "rate"))
async def act_rate(cb: CallbackQuery, callback_data: Act) -> None:
    await cb.message.edit_reply_markup(reply_markup=rating_keyboard(callback_data.id))
    await cb.answer("Ваша оценка от 1 до 10")


@router.callback_query(Act.filter(F.act == "mk"))
async def act_markup(cb: CallbackQuery, callback_data: Act, session: AsyncSession, user: User, state: FSMContext) -> None:
    await _refresh(cb, session, user, callback_data.id, state)
    await cb.answer()


@router.callback_query(Rate.filter())
async def set_rating(cb: CallbackQuery, callback_data: Rate, session: AsyncSession, user: User, state: FSMContext) -> None:
    await users.set_rating(session, user.id, callback_data.id, callback_data.v)
    await session.flush()
    await cb.answer(f"Оценка {callback_data.v}/10 сохранена ⭐")
    await _refresh(cb, session, user, callback_data.id, state)


@router.callback_query(Act.filter(F.act == "sim"))
async def act_similar(cb: CallbackQuery, callback_data: Act, session: AsyncSession, user: User) -> None:
    found = await movies.similar(session, callback_data.id, user.id)
    if not found:
        await cb.answer("Похожих фильмов пока нет — база ещё растёт", show_alert=True)
        return
    rows = movies_list([(m, None) for m in found])
    rows.append([btn("🔙 К фильму", M(id=callback_data.id))])
    rows.append(back_row())
    await show(cb, "🎲 <b>Похожие фильмы</b>\nПо жанрам, режиссёру, актёрам и эпохе.", kb(rows))
    await cb.answer()
