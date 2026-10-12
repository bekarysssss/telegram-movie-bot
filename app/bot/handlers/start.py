from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import Nav
from app.bot.keyboards import main_menu
from app.bot.ui import show
from app.core.config import get_settings

router = Router()

WELCOME = ("Добро пожаловать в <b>{name}</b> 🎬\n\n"
           "Здесь можно найти фильм практически под любое настроение.\n\n"
           "Что будем смотреть?")
ABOUT = ("🎬 <b>{name}</b>\n\n"
         "Каталог и подбор фильмов в Telegram.\n\n"
         "Данные о фильмах: This product uses the TMDB API but is not endorsed or certified by TMDB.\n"
         "Рейтинги IMDb: информация предоставлена IMDb (imdb.com), только для некоммерческого использования.")


@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext) -> None:
    await state.clear()
    await m.answer(WELCOME.format(name=get_settings().bot_name), reply_markup=main_menu())


@router.message(Command("menu"))
async def cmd_menu(m: Message, state: FSMContext) -> None:
    await state.clear()
    await m.answer("🎬 <b>Что хотите сделать?</b>", reply_markup=main_menu())


@router.message(Command("about"))
async def cmd_about(m: Message) -> None:
    await m.answer(ABOUT.format(name=get_settings().bot_name))


@router.callback_query(Nav.filter(F.to == "home"))
async def cb_home(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show(cb, "🎬 <b>Что хотите сделать?</b>", main_menu())
    await cb.answer()


@router.callback_query(Nav.filter(F.to == "noop"))
async def cb_noop(cb: CallbackQuery) -> None:
    await cb.answer()
