import asyncio
import random
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import pytz
from sqlalchemy.future import select
from sqlalchemy import extract
from sqlalchemy import or_

from app.database.models import ArtistPack, async_session, User, async_main, MailingSchedule, SpotPack
from config import TOKEN
from app.handlers import rt
import app.keyboards as kb

bot = Bot(token=TOKEN)
dp = Dispatcher()

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def plus_to_number():
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.paid_sub != 1))
        users = result.scalars().all()

        moscow_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(moscow_tz)
        for user in users:
            if user.registered_at.tzinfo is None:
                user.registered_at = moscow_tz.localize(user.registered_at)

            user_registered_at = user.registered_at.astimezone(moscow_tz)

            time_diff = now - user_registered_at

            if time_diff >= timedelta(days=1):
                user.next_message_number += 1
                user.registered_at = now
        await session.commit()


async def send_mailing_to_no_sub(mailing: MailingSchedule):
    async with async_session() as session:
        result = await session.execute(
            select(User).filter(User.subscription == 0, User.free_subscription_used == 0, User.paid_sub == 0))
        users = result.scalars().all()

        for user in users:
            try:
                if user.next_message_number == mailing.send_date:
                    if user.last_message_sent_date and user.last_message_sent_date.date() == datetime.now(
                            pytz.timezone('Europe/Moscow')).date():
                        continue
                    if mailing.message_text:
                        await bot.send_message(user.user_id, mailing.message_text, parse_mode='HTML',
                                               disable_web_page_preview=True)
                        print(f"Сообщение отправлено пользователю {user.user_id} (без подписки).")

                    user.last_message_sent_date = datetime.now(
                        pytz.timezone('Europe/Moscow')) 
                else:
                    print(
                        f"Для пользователя {user.user_id} не пришло сообщение (message_number не совпадает с send_date).")
            except Exception as e:
                print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

        await session.commit()


async def send_mailing_to_end_sub(mailing: MailingSchedule):
    async with async_session() as session:
        result = await session.execute(
            select(User).filter(User.subscription == 0, User.free_subscription_used == 1, User.paid_sub == 0))
        users = result.scalars().all()

        for user in users:
            try:
                
                if user.next_message_number == mailing.send_date:
                    if user.last_message_sent_date and user.last_message_sent_date.date() == datetime.now(
                            pytz.timezone('Europe/Moscow')).date():
                        continue

                    if mailing.message_text:
                        await bot.send_message(user.user_id, mailing.message_text, parse_mode='HTML',
                                               disable_web_page_preview=True)
                        print(f"Сообщение отправлено пользователю {user.user_id} (с завершенной подпиской).")

                    user.last_message_sent_date = datetime.now(
                        pytz.timezone('Europe/Moscow'))  
                else:
                    print(
                        f"Для пользователя {user.user_id} не пришло сообщение (message_number не совпадает с send_date).")
            except Exception as e:
                print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

        await session.commit()


async def send_scheduled_mailings():
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    current_time = now.time()  

    async with async_session() as session:
        result = await session.execute(
            select(MailingSchedule).filter(
                MailingSchedule.group_type == 'no_sub',
                extract('hour', MailingSchedule.send_time) == current_time.hour,
                extract('minute', MailingSchedule.send_time) == current_time.minute
            )
        )
        mailings_no_sub = result.scalars().all()

        for mailing in mailings_no_sub:
            await send_mailing_to_no_sub(mailing)
            session.add(mailing)

        result = await session.execute(
            select(MailingSchedule).filter(
                MailingSchedule.group_type == 'end_sub',
                extract('hour', MailingSchedule.send_time) == current_time.hour,
                extract('minute', MailingSchedule.send_time) == current_time.minute
            )
        )
        mailings_end_sub = result.scalars().all()

        for mailing in mailings_end_sub:
            await send_mailing_to_end_sub(mailing)
            session.add(mailing)

        await session.commit()

    print("Рассылки отправлены по расписанию.")


##
async def deduct_subscription_for_all_users():
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.subscription > 0))
        users = result.scalars().all()

        moscow_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(moscow_tz)

        for user in users:
            if user.subscription > 0:
                if user.subscription_start.tzinfo is None:
                    user.subscription_start = moscow_tz.localize(user.subscription_start)

                user_subscription_start = user.subscription_start.astimezone(moscow_tz)

                time_diff = now - user_subscription_start

                if time_diff >= timedelta(days=1):
                    user.subscription -= 1
                    user.subscription_start = now
                    if user.subscription == 0:
                        user.next_message_number = 0
                        user.registered_at = now
                        user.subscription_type = 'неактивна'
                        try:
                            await bot.send_message(
                                user.user_id,
                                '<strong>🪫 Ваша подписка завершилась!</strong>\n\n'
                                'Чтобы продолжить пользоваться сервисом, перейдите в раздел'
                                ' <strong>«Подписка»</strong> и продлите доступ',
                                reply_markup=kb.subscription, parse_mode='HTML'
                            )
                            print(f"Уведомление о завершении подписки отправлено пользователю {user.user_id}")
                        except Exception as e:
                            print(f"Ошибка при отправке уведомления пользователю {user.user_id}: {e}")

                    session.add(user)
        await session.commit()


async def send_packs_to_subscribers():
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    print(f"Отправка паков началась в {now}")

    async with async_session() as session:
        result = await session.execute(select(ArtistPack).where(ArtistPack.is_sent == False))
        packs_to_send = result.scalars().all()

    async with async_session() as session:
        result = await session.execute(
            select(User).where(
                User.subscription > 0,
                or_(User.subscription_type == 'artists', User.subscription_type == 'gold')
            )
        )
        active_users = result.scalars().all()

    async with async_session() as session:
        for user in active_users:
            available_packs = [pack for pack in packs_to_send if pack.id not in (user.received_packs or [])]
            if not available_packs:
                print(f"Нет новых паков для пользователя {user.user_id}")
                continue

            pack = random.choice(available_packs)

            usernames = [username.strip() for username in pack.usernames.strip().split(",")]
            formatted_usernames = [
                f"**{i + 1}.** {username.replace('_', '\\_')} ([ссылка](https://www.instagram.com/{username}/))"
                for i, username in enumerate(usernames)
            ]
            message = "**Вам доступен новый пак артистов:**\n\n" + "\n".join(formatted_usernames)

            try:
                await bot.send_message(user.user_id, message, parse_mode="Markdown")
                print(f"Пак {pack.id} отправлен пользователю {user.user_id}")
            except Exception as e:
                print(f"Ошибка отправки пакета пользователю {user.user_id}: {e}")
                continue

            pack.sent_at = now
            session.add(pack)

            if user.received_packs is None:
                user.received_packs = []
            user.received_packs.append(pack.id)
            session.add(user)

        await session.commit()

    print("Все паки успешно отправлены.")


async def send_packs_to_subscribers_spot():
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    print(f"Отправка паков началась в {now}")

    async with async_session() as session:
        result = await session.execute(select(SpotPack).where(SpotPack.is_sent == False))
        packs_to_send = result.scalars().all()

    async with async_session() as session:
        result = await session.execute(
            select(User).where(
                User.subscription > 0,
                or_(User.subscription_type == 'spot', User.subscription_type == 'gold')
            )
        )
        active_users = result.scalars().all()

    async with async_session() as session:
        for user in active_users:
            available_packs = [pack for pack in packs_to_send if pack.id not in (user.received_packs_spot or [])]
            if not available_packs:
                print(f"Нет новых паков для пользователя {user.user_id}")
                continue

            pack = random.choice(available_packs)

            usernames = [username.strip() for username in pack.usernames.strip().split(",")]
            formatted_usernames = [
                f"**{i + 1}.** {username.replace('_', '\\_')} ([ссылка](https://www.instagram.com/{username}/))"
                for i, username in enumerate(usernames)
            ]
            message = "**Вам доступен новый пак спотов:**\n\n" + "\n".join(formatted_usernames)

            try:
                await bot.send_message(user.user_id, message, parse_mode="Markdown")
                print(f"Пак {pack.id} отправлен пользователю {user.user_id}")
            except Exception as e:
                print(f"Ошибка отправки пакета пользователю {user.user_id}: {e}")
                continue

            pack.sent_at = now
            session.add(pack)

            if user.received_packs_spot is None:
                user.received_packs_spot = []
            user.received_packs_spot.append(pack.id)
            session.add(user)

        await session.commit()

    print("Все паки успешно отправлены.")


async def check_promo_expiration():
    async with async_session() as session:
        result = await session.execute(select(User).where(User.active_promo_code != None))
        users_with_promos = result.scalars().all()

        for user in users_with_promos:
            now = datetime.now()

            if user.promo_expiration and 0 < (
                    user.promo_expiration - now).total_seconds() <= 86400 and not user.notified_one_day:
                await bot.send_message(
                    chat_id=user.user_id,
                    text=f"⚠️ <strong>У вас остался 1 день, чтобы использовать промокод.\n\n</strong>"
                         f"<strong>Успей забрать подписку по скидке!</strong>",
                    parse_mode="HTML", reply_markup=kb.subscription
                )
                user.notified_one_day = True
            elif user.promo_expiration and now >= user.promo_expiration:
                user.active_promo_code = None
                user.promo_expiration = None
                user.notified_one_day = False
        await session.commit()


def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    scheduler.add_job(
        deduct_subscription_for_all_users,
        'interval',
        hours=1,
        minutes=0,
        seconds=0,
        start_date=datetime.now(pytz.timezone("Europe/Moscow"))
    )

    scheduler.add_job(
        send_packs_to_subscribers, 'cron',
        hour=18,
        minute=0,
        second=0,
        start_date=datetime.now(pytz.timezone("Europe/Moscow"))
    )

    scheduler.add_job(
        send_packs_to_subscribers_spot, 'cron',
        hour=19,
        minute=0,
        second=0,
        start_date=datetime.now(pytz.timezone("Europe/Moscow"))
    )
    scheduler.add_job(
        check_promo_expiration,
        'interval',
        hours=1,
        minutes=0,
        seconds=0,
        start_date=datetime.now(pytz.timezone("Europe/Moscow"))
    )

    scheduler.start()
    print("Планировщик запущен.")

    print(
        f"текущее время  {datetime.now(pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d %H:%M:%S')} (по Москве)")

    next_run = scheduler.get_job(scheduler.get_jobs()[0].id).next_run_time
    print(f"Следующее время выполнения задачи: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (по Москве)")


##


async def main():
    await async_main()
    dp.include_router(rt)
    setup_scheduler()
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')