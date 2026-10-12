from aiogram.types import User as TgUser
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Movie, User, UserFavorite, UserWatched


async def touch_user(session: AsyncSession, tg: TgUser) -> User:
    """Регистрирует пользователя при первом обращении и обновляет профиль."""
    user = await session.get(User, tg.id)
    if user is None:
        user = User(id=tg.id)
        session.add(user)
    user.username, user.first_name = tg.username, tg.first_name
    user.last_seen_at, user.is_blocked = func.now(), False
    await session.flush()
    return user


async def flags(session: AsyncSession, uid: int, movie_id: int) -> tuple[bool, bool, int | None]:
    fav = await session.get(UserFavorite, (uid, movie_id)) is not None
    seen = await session.get(UserWatched, (uid, movie_id))
    return fav, seen is not None, seen.rating if seen else None


async def toggle_favorite(session: AsyncSession, uid: int, movie_id: int) -> bool:
    row = await session.get(UserFavorite, (uid, movie_id))
    if row:
        await session.delete(row)
        return False
    session.add(UserFavorite(user_id=uid, movie_id=movie_id))
    return True


async def toggle_watched(session: AsyncSession, uid: int, movie_id: int) -> bool:
    row = await session.get(UserWatched, (uid, movie_id))
    if row:
        await session.delete(row)
        return False
    session.add(UserWatched(user_id=uid, movie_id=movie_id))
    return True


async def set_rating(session: AsyncSession, uid: int, movie_id: int, rating: int) -> None:
    row = await session.get(UserWatched, (uid, movie_id))
    if row is None:
        session.add(UserWatched(user_id=uid, movie_id=movie_id, rating=rating))
    else:
        row.rating = rating


async def list_favorites(session: AsyncSession, uid: int, page: int, per_page: int):
    total = (await session.execute(
        select(func.count()).select_from(UserFavorite).where(UserFavorite.user_id == uid))).scalar_one()
    stmt = (select(Movie).join(UserFavorite, UserFavorite.movie_id == Movie.id)
            .where(UserFavorite.user_id == uid).order_by(UserFavorite.created_at.desc())
            .limit(per_page).offset((page - 1) * per_page))
    return [(m, None) for m in (await session.execute(stmt)).scalars().all()], total


async def list_watched(session: AsyncSession, uid: int, page: int, per_page: int):
    total = (await session.execute(
        select(func.count()).select_from(UserWatched).where(UserWatched.user_id == uid))).scalar_one()
    stmt = (select(Movie, UserWatched.rating).join(UserWatched, UserWatched.movie_id == Movie.id)
            .where(UserWatched.user_id == uid).order_by(UserWatched.watched_at.desc())
            .limit(per_page).offset((page - 1) * per_page))
    return [(r[0], r[1]) for r in (await session.execute(stmt)).all()], total


async def all_user_ids(session: AsyncSession) -> list[int]:
    return list((await session.execute(select(User.id).where(User.is_blocked.is_(False)))).scalars().all())


async def mark_blocked(session: AsyncSession, ids: list[int]) -> None:
    if ids:
        await session.execute(update(User).where(User.id.in_(ids)).values(is_blocked=True))
