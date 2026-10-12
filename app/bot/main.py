import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand

from app.bot.handlers import admin, browse, card, library, nav, randomizer, recommend, search, start, stats
from app.bot.middlewares import DbSessionMiddleware
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.importer import ensure_genres


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN не задан — см. .env.example")

    async with SessionLocal() as session:
        await ensure_genres(session)
        await session.commit()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = RedisStorage.from_url(settings.redis_url) if settings.redis_url else MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.outer_middleware(DbSessionMiddleware(SessionLocal))

    # порядок важен: search с «ловлей любого текста» — последним
    dp.include_routers(start.router, admin.router, browse.router, randomizer.router, recommend.router,
                       library.router, stats.router, card.router, nav.router, search.router)

    await bot.set_my_commands([BotCommand(command="start", description="Главное меню"),
                               BotCommand(command="menu", description="Показать меню"),
                               BotCommand(command="about", description="О боте и источниках данных")])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
