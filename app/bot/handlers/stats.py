from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import Nav
from app.bot.formatters import stats_text
from app.bot.keyboards import back_row, kb
from app.bot.ui import show
from app.db.models import User
from app.db.repo_stats import user_stats

router = Router()


@router.callback_query(Nav.filter(F.to == "stats"))
async def my_stats(cb: CallbackQuery, session: AsyncSession, user: User) -> None:
    await show(cb, stats_text(await user_stats(session, user.id)), kb([back_row()]))
    await cb.answer()
