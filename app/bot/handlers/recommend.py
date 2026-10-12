from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import Nav, Rec
from app.bot.keyboards import back_row, btn, grid, kb, movies_list
from app.bot.ui import show
from app.core.config import get_settings
from app.core.constants import MOODS, RUNTIME_BUCKETS
from app.db import repo_movies as movies
from app.db.filters import MovieFilter
from app.db.models import Movie, User

router = Router()

PERIODS = [("Любой", "any"), ("2020-е", "2020"), ("2010-е", "2010"), ("2000-е", "2000"),
           ("1990-е", "1990"), ("1980-е", "1980"), ("1970-е", "1970"), ("До 1970", "old")]
DURATIONS = [("Любая", "any")] + [(label, key) for key, (label, _a, _b) in RUNTIME_BUCKETS.items()]


def build_filter(answers: dict, user_id: int) -> MovieFilter:
    _label, genres, min_rating = MOODS[answers.get("mood", "good")]
    period, dur = answers.get("period", "any"), answers.get("dur", "any")
    year_from = year_to = None
    if period == "old":
        year_to = 1969
    elif period != "any":
        year_from, year_to = int(period), int(period) + 9
    bucket = RUNTIME_BUCKETS.get(dur)
    return MovieFilter(genre_ids=genres, year_from=year_from, year_to=year_to, min_rating=min_rating,
                       runtime_min=bucket[1] if bucket else None, runtime_max=bucket[2] if bucket else None,
                       exclude_watched_by=user_id, min_votes=get_settings().min_votes)


@router.callback_query(Nav.filter(F.to == "mood"))
async def ask_mood(cb: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(rec={}, origin="home")
    buttons = [btn(label, Rec(step="mood", v=key)) for key, (label, _g, _r) in MOODS.items()]
    await show(cb, "🎯 <b>Подбор фильма</b>\n\nКакое настроение?", kb(grid(buttons) + [back_row()]))
    await cb.answer()


async def _save(state: FSMContext, **kw) -> dict:
    rec = {**(await state.get_data()).get("rec", {}), **kw}
    await state.update_data(rec=rec)
    return rec


@router.callback_query(Rec.filter(F.step == "mood"))
async def ask_period(cb: CallbackQuery, callback_data: Rec, state: FSMContext) -> None:
    await _save(state, mood=callback_data.v)
    buttons = [btn(label, Rec(step="period", v=v)) for label, v in PERIODS]
    await show(cb, "🎯 Какой период?", kb(grid(buttons, 3) + [back_row("mood")]))
    await cb.answer()


@router.callback_query(Rec.filter(F.step == "period"))
async def ask_duration(cb: CallbackQuery, callback_data: Rec, state: FSMContext) -> None:
    await _save(state, period=callback_data.v)
    buttons = [btn(label, Rec(step="dur", v=v)) for label, v in DURATIONS]
    await show(cb, "🎯 Продолжительность?", kb(grid(buttons, 3) + [back_row("mood")]))
    await cb.answer()


async def _results(cb: CallbackQuery, session: AsyncSession, user: User, state: FSMContext, rec: dict) -> None:
    found: list[Movie] = await movies.pick(session, build_filter(rec, user.id), n=5)
    await state.update_data(back="recres", rec_ids=[m.id for m in found])
    await show_results(cb, found)
    await cb.answer()


async def show_results(event, found: list[Movie]) -> None:
    if not found:
        await show(event, "😕 Под такие условия ничего не нашлось. Попробуйте смягчить период или длительность.",
                   kb([[btn("🔁 Заново", Nav(to="mood"))], back_row()]))
        return
    rows = movies_list([(m, None) for m in found])
    rows.append([btn("🔄 Другие варианты", Rec(step="again")), btn("🔁 Заново", Nav(to="mood"))])
    rows.append(back_row())
    await show(event, "🎯 <b>Подобрал для вас:</b>\nУже просмотренные в подборку не попадают.", kb(rows))


@router.callback_query(Rec.filter(F.step == "dur"))
async def finish(cb: CallbackQuery, callback_data: Rec, session: AsyncSession, user: User, state: FSMContext) -> None:
    rec = await _save(state, dur=callback_data.v)
    await _results(cb, session, user, state, rec)


@router.callback_query(Rec.filter(F.step == "again"))
async def again(cb: CallbackQuery, session: AsyncSession, user: User, state: FSMContext) -> None:
    await _results(cb, session, user, state, (await state.get_data()).get("rec", {}))
