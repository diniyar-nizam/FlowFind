from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.database.models import async_session, User, ArtistPack, PromotionalCode


async def set_user(user_id, username = None):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.user_id == user_id))

        if not user:
            session.add(User(user_id=user_id, username = username or "Неуказано"))
        else:
            if username and user.username != username:
                user.username = username
        await session.commit()

async def add_subscription(user_id: int, days: int, session: AsyncSession):
    user = await session.scalar(select(User).where(User.user_id == user_id))
    if user:
        user.subscription += days
        await session.commit()
    else:
        print(f"User with id {user_id} not found")

async def get_promo_codes(session: AsyncSession, offset: int = 0, limit: int = 5):
    result = await session.execute(select(PromotionalCode).offset(offset).limit(limit))
    return result.scalars().all()
async def get_promo_count(session: AsyncSession):
    result = await session.execute(select(PromotionalCode))
    return len(result.scalars().all())
async def add_promo_code(session, promo_name, duration, promo_type, promo_value, subscription_type, max_uses):
    new_promo = PromotionalCode(
        promo_name=promo_name,
        duration=duration,
        promo_type=promo_type,
        promo_info_freedays=promo_value if promo_type == 'freedays' else None,
        promo_info_discount=promo_value if promo_type == 'discount' else None,
        subscription_type=subscription_type,
        max_uses=max_uses
    )
    session.add(new_promo)
    await session.commit()
async def get_user(session: AsyncSession, user_id: int):
    result = await session.execute(select(User).filter(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user:
        promo_result = await session.execute(
            select(PromotionalCode).filter(PromotionalCode.users_used.contains(user.user_id))
        )
        user.promos_used = promo_result.scalars().all()

    return user
async def delete_promo_code(session: AsyncSession, promo_name: str):
    await session.execute(delete(PromotionalCode).where(PromotionalCode.promo_name == promo_name))
    await session.commit()
async def get_promo_info(session: AsyncSession, promo_name: str):
    result = await session.execute(select(PromotionalCode).filter(PromotionalCode.promo_name == promo_name))
    return result.scalar_one_or_none()
async def get_user_by_username_or_id(session, search_input):
    if search_input.isdigit():
        result = await session.execute(select(User).filter(User.user_id == int(search_input)))
    else:
        result = await session.execute(select(User).filter(User.username == search_input.lstrip('@')))

    return result.scalar_one_or_none()
async def get_promos_by_user(session, user_id):
    result = await session.execute(select(PromotionalCode))
    all_promos = result.scalars().all()

    promos_used = [promo for promo in all_promos if user_id in promo.users_used]
    return promos_used


