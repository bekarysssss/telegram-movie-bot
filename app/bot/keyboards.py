from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import Act, L, Lib, M, Nav, Rate, Rnd
from app.bot.formatters import movie_label
from app.db.models import Movie


def btn(text: str, cb) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=cb.pack())


def kb(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def grid(buttons: list[InlineKeyboardButton], cols: int = 2) -> list[list[InlineKeyboardButton]]:
    return [buttons[i:i + cols] for i in range(0, len(buttons), cols)]


def back_row(to: str = "home") -> list[InlineKeyboardButton]:
    if to == "home":
        return [btn("🏠 Меню", Nav(to="home"))]
    return [btn("🔙 Назад", Nav(to=to)), btn("🏠 Меню", Nav(to="home"))]


def main_menu() -> InlineKeyboardMarkup:
    items = [("🎲 Случайный фильм", "random"), ("🔎 Найти фильм", "search"), ("🎭 По жанру", "genres"),
             ("📅 По году", "years"), ("⭐ По рейтингу", "ratings"), ("🔥 Популярное", "popular"),
             ("❤️ Избранное", "fav"), ("✅ Мои просмотренные", "seen"), ("🎯 Подобрать фильм", "mood"),
             ("📊 Моя статистика", "stats")]
    return kb(grid([btn(t, Nav(to=to)) for t, to in items]))


def pager(cb, page: int, pages: int) -> list[InlineKeyboardButton]:
    """Строка пагинации для любого CallbackData с полем p: ⬅️ | 1/20 | ➡️"""
    row = []
    if page > 1:
        row.append(btn("⬅️ Пред.", cb.model_copy(update={"p": page - 1})))
    row.append(btn(f"{page}/{pages}", Nav(to="noop")))
    if page < pages:
        row.append(btn("След. ➡️", cb.model_copy(update={"p": page + 1})))
    return row


def movies_list(items: list[tuple[Movie, int | None]], start: int = 1) -> list[list[InlineKeyboardButton]]:
    return [[btn(movie_label(m, start + i, my), M(id=m.id))] for i, (m, my) in enumerate(items)]


def sort_row(cb: L) -> list[InlineKeyboardButton]:
    out = []
    for key, label in (("r", "⭐ Рейтинг"), ("p", "🔥 Популярность"), ("n", "🆕 Новизна")):
        out.append(btn(("• " if cb.s == key else "") + label, cb.model_copy(update={"s": key, "p": 1})))
    return out


def card_keyboard(m: Movie, fav: bool, seen: bool, my: int | None, back_token: str | None) -> InlineKeyboardMarkup:
    rows = []
    if m.trailer_url:
        rows.append([InlineKeyboardButton(text="▶️ Трейлер", url=m.trailer_url)])
    rows.append([
        btn("💔 Убрать из избранного" if fav else "❤️ В избранное", Act(act="fav", id=m.id)),
        btn("✔️ Просмотрен (убрать)" if seen else "✅ Я смотрел", Act(act="seen", id=m.id)),
    ])
    if seen:
        rows.append([btn(f"⭐ Моя оценка: {my}" if my else "⭐ Поставить оценку", Act(act="rate", id=m.id))])
    rows.append([btn("🎲 Похожие фильмы", Act(act="sim", id=m.id))])
    if back_token == "rnd":
        rows.append([btn("🎲 Ещё один", Rnd(a="go")), btn("⚙️ Фильтры", Rnd(a="menu"))])
    rows.append([btn("🔙 Назад", Nav(to="back")), btn("🏠 Меню", Nav(to="home"))])
    return kb(rows)


def rating_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    nums = [btn(str(i), Rate(id=movie_id, v=i)) for i in range(1, 11)]
    return kb([nums[:5], nums[5:], [btn("✖️ Отмена", Act(act="mk", id=movie_id))]])


def lib_keyboard(items, cb: Lib, pages: int, start: int) -> InlineKeyboardMarkup:
    rows = movies_list(items, start)
    if pages > 1:
        rows.append(pager(cb, cb.p, pages))
    rows.append(back_row())
    return kb(rows)


def list_keyboard(items, cb: L, pages: int, origin: str, start: int) -> InlineKeyboardMarkup:
    rows = movies_list([(m, None) for m in items], start)
    if pages > 1:
        rows.append(pager(cb, cb.p, pages))
    rows.append(sort_row(cb))
    rows.append(back_row(origin))
    return kb(rows)
