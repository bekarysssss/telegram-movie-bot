from aiogram import BaseMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.repo_users import touch_user


class DbSessionMiddleware(BaseMiddleware):
    """Открывает сессию БД на один апдейт, регистрирует пользователя, коммитит по успеху."""

    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker

    async def __call__(self, handler, event, data):
        async with self.session_maker() as session:
            data["session"] = session
            tg_user = data.get("event_from_user")
            if tg_user:
                data["user"] = await touch_user(session, tg_user)
            try:
                result = await handler(event, data)
            except Exception:
                await session.rollback()
                raise
            await session.commit()
            return result
