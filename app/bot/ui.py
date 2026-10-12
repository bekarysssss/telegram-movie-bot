from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def _send(msg: Message, text: str, markup: InlineKeyboardMarkup | None, photo: str | None) -> Message:
    if photo:
        try:
            return await msg.answer_photo(photo, caption=text[:1024], reply_markup=markup)
        except TelegramBadRequest:
            pass  # битая ссылка на постер — показываем карточку текстом
    return await msg.answer(text, reply_markup=markup)


async def show(event: CallbackQuery | Message, text: str, markup: InlineKeyboardMarkup | None = None,
               photo: str | None = None) -> None:
    """Показывает экран: редактирует текущее сообщение, а если тип меняется (текст ↔ фото) — заменяет его."""
    if isinstance(event, Message):
        await _send(event, text, markup, photo)
        return
    msg = event.message
    if photo or msg.photo:
        try:
            await msg.delete()
        except TelegramBadRequest:
            pass
        await _send(msg, text, markup, photo)
        return
    try:
        await msg.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            raise
