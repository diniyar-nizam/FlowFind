from sqlalchemy import String, BigInteger, DateTime, Column, Integer, Boolean, PickleType
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.ext.mutable import MutableList
from datetime import datetime
import pytz



from config import DB_URL


engine = create_async_engine(url=DB_URL)

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column(String(255))
    admin_action: Mapped[str] = mapped_column(default='none')
    subscription = Column(Integer, default=0)
    subscription_start = Column(DateTime, default=None)
    received_packs = Column(MutableList.as_mutable(PickleType), default=[])
    received_packs_spot = Column(MutableList.as_mutable(PickleType), default=[])
    free_subscription_used = Column(Boolean, default=False)
    registered_at = Column(DateTime, default=datetime.now(pytz.timezone('Europe/Moscow')))
    paid_sub = Column(Integer, default=0)
    next_message_number = Column(Integer, default=0)
    last_message_sent_date = Column(DateTime, nullable=True)
    subscription_type: Mapped[str] = mapped_column(String, default='неактивна')
    active_promo_code: Mapped[str] = mapped_column(String, nullable=True)
    promo_expiration: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    notified_one_day: Mapped[bool] = mapped_column(Boolean, default=False)

class ArtistPack(Base):
    __tablename__ = 'artist_packs'

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(pytz.timezone('Europe/Moscow')))
    usernames: Mapped[str] = mapped_column(String)
    sent_at = Column(DateTime, default=None)
    is_sent = Column(Boolean, default=False, nullable=False)

class SpotPack(Base):
    __tablename__ = 'spot_packs'

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(pytz.timezone('Europe/Moscow')))
    usernames: Mapped[str] = mapped_column(String)
    sent_at = Column(DateTime, default=None)
    is_sent = Column(Boolean, default=False, nullable=False)

class MailingSchedule(Base):
    __tablename__ = 'mailing_schedule'

    id: Mapped[int] = mapped_column(primary_key=True)
    group_type = mapped_column(String(50))
    message_text = mapped_column(String)
    send_time = mapped_column(DateTime)
    send_date = mapped_column(Integer, default=1)

class PromotionalCode(Base):
    __tablename__ = 'promotional_code'

    id: Mapped[int] = mapped_column(primary_key=True)
    promo_name: Mapped[str] = mapped_column(String, unique=True)
    duration: Mapped[int] = mapped_column(Integer)
    promo_info_freedays: Mapped[int] = mapped_column(Integer, nullable=True)
    promo_info_discount: Mapped[int] = mapped_column(Integer, nullable=True)
    promo_type = Column(String)
    subscription_type: Mapped[str] = mapped_column(String)
    max_uses: Mapped[int] = mapped_column(Integer)
    users_used: Mapped[list] = Column(MutableList.as_mutable(PickleType), default=[])


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)