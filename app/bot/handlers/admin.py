import asyncio
import html

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import repo_users as users
from app.db.repo_stats import bot_stats

router = Router()
router.message.filter(F.from_user.id.in_(get_settings().admin_id_set))


@router.message(Command("admin_stats"))
async def admin_stats(m: Message, session: AsyncSession) -> None:
    s = await bot_stats(session)
    top = "\n".join(f"  {i}. {html.escape(t['title'])} ({t['year']}) — {t['watched_by']}"
                    for i, t in enumerate(s["top_movies"], 1)) or "  —"
    await m.answer(
        "📈 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: <b>{s['users']}</b> (за сутки +{s['users_24h']}, за неделю +{s['users_7d']})\n"
        f"🔥 Активных за 7 дней: {s['active_7d']}\n"
        f"🎬 Фильмов в базе: {s['movies']}\n"
        f"❤️ В избранном: {s['favorites']} · ✅ Просмотров: {s['watched']}\n\n"
        f"🏆 Самые просматриваемые:\n{top}")


@router.message(Command("broadcast"))
async def broadcast(m: Message, command: CommandObject, session: AsyncSession, bot: Bot) -> None:
    if not command.args:
        await m.answer("Использование: <code>/broadcast текст сообщения</code> (HTML-разметка поддерживается)")
        return
    ids, sent, blocked = await users.all_user_ids(session), 0, []
    await m.answer(f"Рассылка на {len(ids)} пользователей…")
    for uid in ids:
        try:
            await bot.send_message(uid, command.args)
            sent += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await bot.send_message(uid, command.args)
            sent += 1
        except TelegramForbiddenError:
            blocked.append(uid)
        except TelegramAPIError:
            pass
        await asyncio.sleep(0.05)  # ~20 сообщений/с, лимит Telegram — 30
    await users.mark_blocked(session, blocked)
    await m.answer(f"Готово: доставлено {sent}, заблокировали бота {len(blocked)}.")
