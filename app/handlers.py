from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import CallbackQuery
from sqlalchemy.future import select
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from datetime import datetime, timedelta
import pytz
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)
import logging

from sqlalchemy.orm.base import state_class_str

from app.database.models import ArtistPack, MailingSchedule, SpotPack
from app.database.flowfind_func import rt as flowfind_rt
import app.keyboards as kb
import app.database.requests as rq
from config import ADMIN_ID
from app.database.models import async_session, User

rt = Router()
rt.include_router(flowfind_rt)

def get_total_pages(total_items: int, items_per_page: int):
    return (total_items + items_per_page - 1) // items_per_page
def is_admin(user_id):
    return user_id in ADMIN_ID

class AdminAction(StatesGroup):
    waiting_for_user_username_subscription = State()
    waiting_for_subscription_days = State()
    waiting_for_user_username_check = State()
    waiting_for_message = State()
    waiting_for_user_username_check_packs = State()
    waiting_for_group_no_sub_message = State()
    waiting_for_group_end_sub_message = State()
    waiting_for_time_no_sub = State()
    waiting_for_time_end_sub = State()
    waiting_for_sub_message = State()
    waiting_for_who_free_message = State()
    waiting_for_who_no_free_message = State()
    waiting_for_who_paid_message = State()
    waiting_for_who_in_free_message = State()
    waiting_for_who_gold_mail = State()
    waiting_for_who_spot_mail = State()
    waiting_for_who_artists_mail = State()
    waiting_for_promo_name = State()
    waiting_for_duration = State()
    waiting_for_promo_info = State()
    waiting_for_max_uses = State()
    waiting_for_search_username = State()
class UserState(StatesGroup):
    enter_page_number_artists = State()
    enter_page_number_spot = State()
    waiting_for_promo_code = State()

@rt.message(CommandStart())
async def cmd_start(message: Message):
    await rq.set_user(message.from_user.id, message.from_user.username)
    await message.answer(f'<strong>FlowFind</strong> '
                        f'ваш помощник в поиске артистов и расширении аудитории с минимальными усилиями.\n\n'
                        f'С нами вы экономите время и повышаете свою эффективность! 🚀',
                        parse_mode="HTML",
                        reply_markup=kb.aftstart)


@rt.message(Command('apanel'))
async def apanel(message: Message):
    if is_admin(message.from_user.id):
        await message.answer('<strong>Возможные команды:</strong>', reply_markup=kb.adm_start, parse_mode='HTML')


# промо
@rt.callback_query(F.data == 'promo')
async def promo(callback: CallbackQuery, page: int = 1):
    async with async_session() as session:
        total_promos = await rq.get_promo_count(session)
        await callback.answer('🎫 Промокоды')
        if total_promos == 0:
            await callback.message.edit_text(
                "❗️ Промокодов пока нет.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="➕ Добавить", callback_data="add_promo")],
                        [InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")]
                    ]
                )
            )
            return

        total_pages = (total_promos + 4) // 5
        page = (page - 1) % total_pages + 1
        offset = (page - 1) * 5
        promo_codes = await rq.get_promo_codes(session, offset=offset)

        await callback.message.edit_text(
            "📋 Вот список промокодов:",
            reply_markup=get_promo_buttons(page, total_pages, promo_codes),
        )
async def promo_message(message: Message):
    async with async_session() as session:
        total_promos = await rq.get_promo_count(session)

        if total_promos == 0:
            await message.answer(
                "❗️ Промокодов пока нет.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="➕ Добавить", callback_data="add_promo")],
                        [InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")]
                    ]
                )
            )
            return

        total_pages = (total_promos + 4) // 5
        promo_codes = await rq.get_promo_codes(session, offset=0)

        await message.answer(
            "📋 Вот список промокодов:",
            reply_markup=get_promo_buttons(1, total_pages, promo_codes),
        )
def get_promo_buttons(page, total_pages, promo_codes, empty=False):
    buttons = []
    if not empty:
        for promo in promo_codes:
            buttons.append(
                [InlineKeyboardButton(text=promo.promo_name, callback_data=f"promo_info_{promo.promo_name}")])

    buttons.append([
        InlineKeyboardButton(text="❮", callback_data=f"promo_page_{page - 1}"),
        InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="null"),
        InlineKeyboardButton(text="❯", callback_data=f"promo_page_{page + 1}")
    ])
    buttons.append([InlineKeyboardButton(text="➕ Добавить", callback_data="add_promo"),
                    InlineKeyboardButton(text="❌ Удалить", callback_data="delete_promo")])
    buttons.append([InlineKeyboardButton(text="🔎 Найти по юзеру", callback_data="search_promo_user")])
    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@rt.callback_query(F.data.startswith('promo_page_'))
async def promo_pagination(callback: CallbackQuery):
    page = int(callback.data.split('_')[-1])

    async with async_session() as session:
        total_promos = await rq.get_promo_count(session)

        if total_promos == 0:
            await callback.message.edit_text(
                "❗️ Промокодов пока нет.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="➕ Добавить", callback_data="add_promo")],
                        [InlineKeyboardButton(text="↩️ Назад", callback_data="adm_back")]
                    ]
                )
            )
            return

        total_pages = (total_promos + 4) // 5
        page = (page - 1) % total_pages + 1
        offset = (page - 1) * 5
        promo_codes = await rq.get_promo_codes(session, offset=offset)

        await callback.message.edit_text(
            "📋 Вот список промокодов:",
            reply_markup=get_promo_buttons(page, total_pages, promo_codes),
        )

@rt.callback_query(F.data.startswith('promo_info_'))
async def promo_info(callback: CallbackQuery):
    promo_name = callback.data.split('_')[2]
    async with async_session() as session:
        promo = await rq.get_promo_info(session, promo_name)
        if promo:
            user_list = []
            for user_id in promo.users_used:
                user = await rq.get_user(session, user_id)
                user_list.append(f"@{user.username}" if user.username else f"ID: {user_id}")

            users_used_text = '\n'.join(user_list) if user_list else "Никто еще не использовал."

            text = (
                f"🎁 <strong>Промокод:</strong> {promo.promo_name}\n"
                f"⏳ <strong>Срок действия:</strong> {promo.duration} дней\n"
                f"ℹ️ <strong>Вид промокода:</strong> {'Бесплатные дни' if promo.promo_type == 'freedays' else 'Скидка'}\n"
                f"💸 <strong>{'Бесплатных дней:' if promo.promo_type == 'freedays' else 'Скидка'}</strong> {promo.promo_info_discount if promo.promo_info_discount else promo.promo_info_freedays}{'%' if promo.promo_info_discount else ''}\n"
                f"🎟 <strong>Вид подписки:</strong> {promo.subscription_type}\n"
                f"👥 <strong>Лимит пользователей:</strong> {len(promo.users_used)}/{promo.max_uses}\n"
                f"📋 <strong>Кто использовал:</strong>\n{users_used_text}\n"
            )
            await callback.message.edit_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="↩️ Назад", callback_data="promo")]]))
        else:
            await callback.answer("Промокод не найден!")
@rt.callback_query(F.data == 'add_promo')
async def add_promo(callback: CallbackQuery, state: FSMContext):
    await callback.answer('➕ Добавить')
    await state.set_state(AdminAction.waiting_for_promo_name)
    await callback.message.edit_text("Выберите вид промокода:", reply_markup=kb.free_discount)
@rt.callback_query(F.data.startswith('promo_type_'))
async def promo_type_selected(callback: CallbackQuery, state: FSMContext):
    promo_type = callback.data.split('_')[2]
    await state.update_data(promo_type=promo_type)
    if promo_type == "freedays":
        await callback.answer('⏳ Бесплатные Дни')
        await state.set_state(AdminAction.waiting_for_promo_info)
        await callback.message.edit_text("⏳ Введите количество бесплатных дней:")
    elif promo_type == "discount":
        await callback.answer('💸 Скидка')
        await state.set_state(AdminAction.waiting_for_promo_info)
        await callback.message.edit_text("💸 Введите размер скидки (в %):")
@rt.message(F.text, AdminAction.waiting_for_promo_info)
async def promo_value_entered(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        promo_value = int(message.text.strip())
        promo_type = data.get("promo_type")
        await state.update_data(promo_value=promo_value)
        if promo_type == 'discount':
            await message.answer("📚 Выберите подписку, на которую будет действовать промокод:", reply_markup=kb.promo_basic_gold)
        else:
            await message.answer("📚 Выберите подписку, на которую будет действовать промокод:",
                                 reply_markup=kb.promo_basic_gold_without_basicgold)
    except ValueError:
        await message.answer("⚠️ Введите корректное число!")
@rt.callback_query(F.data.startswith('promo_sub1_'))
async def promo_sub_selected(callback: CallbackQuery, state: FSMContext):
    if "goldbasic" in callback.data:
        subscription_type = "basic+gold"
    elif "basic" in callback.data:
        subscription_type = "basic"
    else:
        subscription_type = "gold"
    await state.update_data(subscription_type=subscription_type)
    await state.set_state(AdminAction.waiting_for_promo_name)
    await callback.message.edit_text("✏️ Введите промокод:")
@rt.message(F.text, AdminAction.waiting_for_promo_name)
async def promo_name_entered(message: Message, state: FSMContext):
    await state.update_data(promo_name=message.text.strip())
    data = await state.get_data()
    promo_type = data.get("promo_type")
    if promo_type == "discount":
        await state.set_state(AdminAction.waiting_for_duration)
        await message.answer("⏳ Введите количество дней действия промокода:")
    else:
        duration = 0
        await state.update_data(duration=duration)
        await state.set_state(AdminAction.waiting_for_max_uses)
        await message.answer("👥️ Введите ограничение людей на промокод:")
@rt.message(F.text, AdminAction.waiting_for_duration)
async def promo_duration_entered(message: Message, state: FSMContext):
    try:
        duration = int(message.text.strip())
        await state.update_data(duration=duration)
        await state.set_state(AdminAction.waiting_for_max_uses)
        await message.answer("👥️ Введите ограничение людей на промокод:")
    except ValueError:
        await message.answer("⚠️ Введите корректное число для дней!")
@rt.message(F.text, AdminAction.waiting_for_max_uses)
async def promo_max_uses_entered(message: Message, state: FSMContext):
    try:
        max_uses = int(message.text.strip())
        data = await state.get_data()

        promo_name = data.get("promo_name")
        duration = data.get("duration")
        promo_type = data.get("promo_type")
        promo_value = data.get("promo_value")
        subscription_type = data.get("subscription_type")

        async with async_session() as session:
            await rq.add_promo_code(session, promo_name, duration, promo_type, promo_value, subscription_type, max_uses)

        await message.answer(
            f"✅ Промокод <strong>{promo_name}</strong> успешно добавлен!\n"
            f"🎁 Тип: {promo_type}\n"
            f"📚 Подписка: {subscription_type}\n"
            f"👥 Лимит: {max_uses} пользователей.", parse_mode='HTML'
        )
        await state.clear()

        await promo_message(message)
    except ValueError:
        await message.answer("⚠️ Введите корректное число для лимита пользователей!")


@rt.callback_query(F.data == 'search_promo_user')
async def search_promo_user(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminAction.waiting_for_search_username)
    await callback.answer('🔎 Найти по юзеру')
    await callback.message.edit_text("🔎 Введите @юзернейм или ID для поиска активированных промокодов:", reply_markup=kb.adm_back)
@rt.message(F.text, AdminAction.waiting_for_search_username)
async def search_promo_result(message: Message, state: FSMContext):
    search_input = message.text.strip()
    async with async_session() as session:
        user = await rq.get_user_by_username_or_id(session, search_input)

        if not user:
            await message.answer("❗️ Пользователь не найден!")
            await state.clear()
            return

        promos_used = await rq.get_promos_by_user(session, user.user_id)

        if not promos_used:
            await message.answer(f"❗️ У пользователя @{user.username or user.user_id} нет активированных промокодов.")
            await state.clear()
            return

        promo_list = []
        for promo in promos_used:
            promo_type = "⏳ Бесплатные дни" if promo.promo_type == "freedays" else "💸 Скидка"
            promo_value = f"{promo.promo_info_freedays} дней" if promo.promo_type == "freedays" else f"{promo.promo_info_discount}% скидка"
            promo_list.append(
                f"🎁 {'✅✅✅' if user.active_promo_code == promo.promo_name else '❌❌❌'}<strong>{promo.promo_name}</strong>{'✅✅✅' if user.active_promo_code == promo.promo_name else '❌❌❌'}\n"
                f"🔖 <strong>Тип:</strong> {promo_type}\n"
                f"🎁 <strong>Размер:</strong> {promo_value}\n"
                f"🕓 <strong>Срок действия:</strong> {promo.duration} дней\n"
                f"📚 <strong>Подписка:</strong> {promo.subscription_type}\n"
                f"👥 <strong>Лимит:</strong> {len(promo.users_used)}/{promo.max_uses}\n"
                "———————————"
            )

        promo_text = '\n\n'.join(promo_list)
        username_or_id = f"@{user.username}" if user.username else f"ID: {user.user_id}"

        await message.answer(
            f"🔎 <strong>Активированные промокоды пользователя {username_or_id}:</strong>\n\n{promo_text}",
            parse_mode='HTML'
        )
    await promo_message(message)
    await state.clear()


@rt.callback_query(F.data == 'delete_promo')
async def delete_promo(callback: CallbackQuery, page: int = 1):
    async with async_session() as session:
        total_promos = await rq.get_promo_count(session)
        await callback.answer('❌ Удалить')
        if total_promos == 0:
            await callback.message.edit_text("❗️ Промокодов для удаления нет.", reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="↩️ Назад", callback_data="promo")]]))
            return

        total_pages = (total_promos + 4) // 5
        page = (page - 1) % total_pages + 1
        offset = (page - 1) * 5
        promo_codes = await rq.get_promo_codes(session, offset=offset)

        await callback.message.edit_text(
            "🗑️ Выберите промокод для удаления:",
            reply_markup=get_delete_promo_buttons(page, total_pages, promo_codes)
        )
def get_delete_promo_buttons(page, total_pages, promo_codes):
    buttons = []
    for promo in promo_codes:
        buttons.append(
            [InlineKeyboardButton(text=f"🗑️ {promo.promo_name}", callback_data=f"delete_promo_{promo.promo_name}")])

    buttons.append([
        InlineKeyboardButton(text="❮", callback_data=f"delete_page_{page - 1}"),
        InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="null"),
        InlineKeyboardButton(text="❯", callback_data=f"delete_page_{page + 1}")
    ])
    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="promo")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
@rt.callback_query(F.data.startswith('delete_promo_'))
async def delete_selected_promo(callback: CallbackQuery):
    promo_name = callback.data.split('_')[2]
    async with async_session() as session:
        await rq.delete_promo_code(session, promo_name)

    await callback.answer(f"✅ Промокод {promo_name} удален!", show_alert=True)

    await delete_promo(callback)


@rt.callback_query(F.data == 'promo_for_sub')
async def promo_for_sub(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session() as session:
        user = await rq.get_user(session, user_id)

        if user.active_promo_code:
            remaining_days = (user.promo_expiration - datetime.now()).days
            if remaining_days > 0:
                await callback.answer(
                    f"📅 У вас уже есть активный промокод", show_alert=True
                )
                return


        await callback.message.edit_text("<strong>Введите промокод</strong>", reply_markup=kb.backtosub, parse_mode='HTML')
        await state.set_state(UserState.waiting_for_promo_code)
@rt.message(F.text, UserState.waiting_for_promo_code)
async def promo_code_entered(message: Message, state: FSMContext):
    promo_code = message.text.strip()
    await state.update_data(promo_code=promo_code)
    if promo_code == '🎯 Главное меню':
        await state.clear()
        await main_menu(message, state)
        return
    elif promo_code == '👥 Поддержка':
        await state.clear()
        await main_support(message)
        return
    async with async_session() as session:
        promo = await rq.get_promo_info(session, promo_code)

        if not promo:
            await message.answer("❌")
            return

        if len(promo.users_used) >= promo.max_uses:
            await message.answer("❌")
            return

        user_id = message.from_user.id
        user = await rq.get_user(session, user_id)

        if user_id in promo.users_used:
            await message.answer("❌")
            return

        if user.active_promo_code:
            await message.answer("❌")
            return
        if promo.promo_type == 'discount':
            user.active_promo_code = promo.promo_name
            user.promo_expiration = datetime.now() + timedelta(days=promo.duration)


        promo_value = f"{promo.promo_info_freedays} дней" if promo.promo_type == "freedays" else f"{promo.promo_info_discount}%"
        if promo.promo_type == 'discount':
            expiration_date = user.promo_expiration.strftime('%d.%m %H:%M')

            await message.answer(
                f"<strong>✅ Промокод активен до {expiration_date}</strong>\n\n"
                f"Размер скидки: {promo_value}",
                parse_mode='HTML', reply_markup=kb.backtosub
            )
            promo.users_used.append(user_id)
            await state.clear()
        if promo.promo_type == 'freedays':
            if user.subscription_type == 'gold' and promo.subscription_type == 'gold':
                user.subscription += promo.promo_info_freedays
                await message.answer(
                    f"<strong>✅ Промокод активирован</strong>\n\n"
                    f"Вам начислено {promo_value}",
                    parse_mode='HTML', reply_markup=kb.backtosub
                )
                promo.users_used.append(user_id)
                await state.clear()
            elif user.subscription_type in ['spot', 'artists'] and promo.subscription_type == 'basic':
                user.subscription += promo.promo_info_freedays
                await message.answer(
                    f"<strong>✅ Промокод активирован</strong>\n\n"
                    f"Вам начислено {promo_value}",
                    parse_mode='HTML', reply_markup=kb.backtosub
                )
                promo.users_used.append(user_id)
                await state.clear()
            elif user.subscription_type == 'неактивна':
                if promo.subscription_type == 'gold':
                    user.subscription += promo.promo_info_freedays
                    user.subscription_type = 'gold'
                    await message.answer(
                        f"<strong>✅ Промокод активирован</strong>\n\n"
                        f"Вам начислено {promo_value}",
                        parse_mode='HTML', reply_markup=kb.backtosub
                    )
                else:
                    await message.answer(
                        f"<strong>Выберите вид подписки:</strong>",
                        parse_mode='HTML', reply_markup=kb.spot_artists_for_users
                    )
            else:
                await message.answer("❌")
                return
        await session.commit()
@rt.callback_query(F.data.startswith('promo_sub_choice_'))
async def promo_sub_selected_spot_artists(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    promo_code = data.get("promo_code")
    if "spot" in callback.data:
        subscription_type = "spot"
    else:
        subscription_type = "artists"
    async with async_session() as session:
        promo = await rq.get_promo_info(session, promo_code)
        user_id = callback.from_user.id
        user = await rq.get_user(session, user_id)
        promo_value = f"{promo.promo_info_freedays} дней" if promo.promo_type == "freedays" else f"{promo.promo_info_discount}%"
        user.subscription_type = subscription_type
        user.subscription += promo.promo_info_freedays
        await callback.message.edit_text(
            f"<strong>✅ Промокод активирован</strong>\n\n"
            f"Вам начислено {promo_value}\n"
            f"Ваша подписка: {subscription_type}",

            parse_mode='HTML', reply_markup=kb.backtosub
        )
        await session.commit()


##
@rt.callback_query(F.data == 'ffind')
async def ffind(callback: CallbackQuery):
    if is_admin(callback.from_user.id):
        await callback.answer('💻 FlowFind')
        await callback.message.edit_text('<strong>Выберите группу по кнопкам ниже:</strong>',
                                         reply_markup=kb.spot_artists,
                                         parse_mode='HTML')
@rt.callback_query(F.data == 'artists')
async def artists(callback: CallbackQuery):
    if is_admin(callback.from_user.id):
        await callback.answer('artists')
        await callback.message.edit_text('<strong>Выберите действия по кнопкам ниже:</strong>',
                                         reply_markup=kb.ff,
                                         parse_mode='HTML')
@rt.callback_query(F.data == 'spot')
async def spot(callback: CallbackQuery):
    if is_admin(callback.from_user.id):
        await callback.answer('spot')
        await callback.message.edit_text('<strong>Выберите действия по кнопкам ниже:</strong>',
                                         reply_markup=kb.spot,
                                         parse_mode='HTML')

@rt.callback_query(F.data == 'db_back')
async def db_back(callback: CallbackQuery, state: FSMContext):
    if is_admin(callback.from_user.id):
        await callback.answer('↩️Назад')
        await callback.message.edit_text('<strong>Выберите действия по кнопкам ниже:</strong>',
                                         reply_markup=kb.ff,
                                         parse_mode='HTML')
    await state.clear()
@rt.callback_query(F.data == 'db_back_spot')
async def db_back_spot(callback: CallbackQuery, state: FSMContext):
    if is_admin(callback.from_user.id):
        await callback.answer('↩️Назад')
        await callback.message.edit_text('<strong>Выберите действия по кнопкам ниже:</strong>',
                                         reply_markup=kb.spot,
                                         parse_mode='HTML')
    await state.clear()
##
@rt.callback_query(F.data == 'ffback')
async def ffback(callback: CallbackQuery, state: FSMContext):
    await callback.answer('↩️ Назад')
    await callback.message.edit_text('<strong>Возможные команды:</strong>',
                                     reply_markup=kb.adm_start,
                                     parse_mode='HTML')
    await state.clear()

@rt.callback_query(F.data == 'adm_back')
async def abm_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer('⚙️ ADMIN PANEL')
    await callback.message.edit_text('<strong>Возможные команды:</strong>', reply_markup=kb.adm_start,
                                     parse_mode='HTML')
    await state.clear()

##

@rt.callback_query(F.data == 'sub')
async def start_subscription(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return
    await state.set_state(AdminAction.waiting_for_user_username_subscription)
    await callback.answer('🎟️ Выдать подписку')
    await callback.message.edit_text("Введите username или id пользователя в формате @username, "
                                     "для которого хотите выдать подписку:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_user_username_subscription)
async def get_user_username(message: Message, state: FSMContext):
    user_input = message.text.strip()

    async with async_session() as session:
        try:
            if user_input.isdigit():  
                user_id = int(user_input)
                result = await session.execute(select(User).where(User.user_id == user_id))
            elif user_input.startswith('@') and len(user_input) > 1 and user_input[1:].replace("_", "").replace(".", "").isalnum():
                username = user_input[1:].strip().lower()
                result = await session.execute(select(User).where(User.username.ilike(username)))
            else:
                await message.answer("⚠️ Введите корректный username (@username) или ID (число).",
                                     reply_markup=kb.adm_back)
                return

            user = result.scalar_one_or_none()

            if not user:
                await message.answer(f"Пользователь {user_input} не найден", reply_markup=kb.adm_back)
                return

            await state.update_data(username=user.user_id)

        except Exception as e:
            logging.error(f"Ошибка при поиске пользователя: {e}")
            await message.answer("Произошла ошибка при поиске пользователя.", reply_markup=kb.adm_back)
            return

    await message.answer(f"Выберите вид подписки для пользователя {f'@{user.username}' if user.username != 'Неуказано' else user.user_id}:",
                         reply_markup=kb.gold_spot_artists)
@rt.callback_query(F.data.in_(['give_gold', 'give_spot', 'give_artists']))
async def set_subscription_type(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    username = data['username']

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == username))
        user = result.scalar_one_or_none()

        if not user:
            await callback.message.edit_text(f"Пользователь {f'@{user.username}' if user.username != 'Неуказано' else username} не найден в базе", reply_markup=kb.adm_back)
            return

        new_type = callback.data.replace('give_', '')
        current_type = user.subscription_type

        if new_type == current_type:
            await callback.message.edit_text(f"Введите количество дней подписки:",
                                             reply_markup=kb.adm_add)
            await state.update_data(new_type=new_type, sum_days=True)
        elif (new_type == 'spot' and current_type == 'artists') or (new_type == 'artists' and current_type == 'spot'):
            await callback.message.edit_text(
                f"⚠️ У пользователя уже подписка {current_type}. Подтвердите смену на {new_type}. Дни будут суммированы.",
                reply_markup=kb.confirm_subscription
            )
            await state.update_data(new_type=new_type, sum_days=True)
        elif (new_type == 'gold' and current_type in ['artists', 'spot']) or (current_type == 'gold' and new_type in ['artists', 'spot']):
            await callback.message.edit_text(
                f"⚠️ У пользователя подписка {current_type}. Введите точное количество дней для новой подписки {new_type}:",
                reply_markup=kb.adm_add
            )
            await state.update_data(new_type=new_type, sum_days=False)
        else:
            await callback.message.edit_text(f"Подтвердите смену подписки на {new_type}. Дни будут суммированы.",
                                             reply_markup=kb.confirm_subscription)
            await state.update_data(new_type=new_type, sum_days=True)

    await state.set_state(AdminAction.waiting_for_subscription_days)
@rt.callback_query(F.data == 'confirm_sub')
async def confirm_subscription(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    username = data['username']
    new_type = data['new_type']
    sum_days = data['sum_days']

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == username))
        user = result.scalar_one_or_none()

        if not user:
            await callback.message.edit_text(f"Пользователь {f'@{user.username}' if user.username != 'Неуказано' else username} не найден в базе", reply_markup=kb.adm_back)
            return

        user.subscription_type = new_type
        await session.commit()
        await callback.answer('✅ Успешно')
        await callback.message.edit_text(
            f"✅ Подписка успешно обновлена на {new_type}. Введите количество дней подписки:",
            reply_markup=kb.adm_add
        )
        await state.set_state(AdminAction.waiting_for_subscription_days)
        await state.update_data(sum_days=sum_days)
@rt.message(AdminAction.waiting_for_subscription_days)
async def get_subscription_days(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data['username']
    new_type = data['new_type']
    sum_days = data['sum_days']

    try:
        days = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите корректное количество дней подписки (целое число)",
                             reply_markup=kb.adm_add)
        return

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == username))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(f"Пользователь {f'@{user.username}' if user.username != 'Неуказано' else username} не найден в базе",
                                 reply_markup=kb.adm_back)
            return

        if sum_days:
            user.subscription += days
        else:
            user.subscription = days

        user.paid_sub = 1
        user.subscription_start = datetime.now(pytz.timezone('Europe/Moscow'))
        user.subscription_type = new_type
        if user.active_promo_code:
            promo_info = await rq.get_promo_info(session, user.active_promo_code)

            if promo_info and promo_info.subscription_type in ["basic", "basic+gold"] and new_type in ["artists", "spot"]:
                user.active_promo_code = None
                user.promo_expiration = None
                user.notified_one_day = False

            elif promo_info and promo_info.subscription_type in ["gold", "basic+gold"] and new_type == "gold":
                user.active_promo_code = None
                user.promo_expiration = None
                user.notified_one_day = False
        await message.answer(
            f"✅ Подписка для пользователя {f'@{user.username}' if user.username != 'Неуказано' else username} успешно обновлена на {user.subscription_type} на {days} дней.",
            reply_markup=kb.adm_start
        )
        await session.commit()

    await state.clear()
@rt.callback_query(F.data == 'adm_give')
async def give_30_days(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    username = data['username']
    new_type = data.get('new_type')
    sum_days = data.get('sum_days', True)
    days = 30

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == username))
        user = result.scalar_one_or_none()

        if not user:
            await callback.answer('❌ Ошибка')
            await callback.message.edit_text(f"❌ Пользователь {f'@{user.username}' if user.username != 'Неуказано' else username} не найден в базе.", reply_markup=kb.adm_back)
            return

        if new_type and user.subscription_type != new_type:
            user.subscription_type = new_type

        if sum_days:
            user.subscription += days
        else:
            user.subscription = days

        user.paid_sub = 1
        user.subscription_start = datetime.now(pytz.timezone('Europe/Moscow'))
        if user.active_promo_code:
            promo_info = await rq.get_promo_info(session, user.active_promo_code)

            if promo_info and promo_info.subscription_type in ["basic", "basic+gold"] and new_type in ["artists", "spot"]:
                user.active_promo_code = None
                user.promo_expiration = None
                user.notified_one_day = False

            elif promo_info and promo_info.subscription_type in ["gold", "basic+gold"] and new_type == "gold":
                user.active_promo_code = None
                user.promo_expiration = None
                user.notified_one_day = False
        await callback.answer('✅ Успешно')
        await callback.message.edit_text(
            f"✅ Подписка для пользователя {f'@{user.username}' if user.username != 'Неуказано' else username} успешно обновлена на {user.subscription_type} на {days} дней.",
            reply_markup=kb.adm_start
        )
        await session.commit()

    await state.clear()


@rt.callback_query(F.data == 'gsub')
async def check_subscription_request(callback: CallbackQuery, state: FSMContext):
    await callback.answer('🪪 Проверить подписку')
    await callback.message.edit_text(
        "Введите username пользователя в формате @username, чью подписку вы хотите проверить:",
        reply_markup=kb.adm_back)

    await state.set_state(AdminAction.waiting_for_user_username_check)

@rt.message(AdminAction.waiting_for_user_username_check)
async def get_user_subscription(message: Message, state: FSMContext):
    username_input = message.text.strip()

    if not username_input.startswith('@') or len(username_input) < 2 or not username_input[1:].replace("_", "").replace(".", "").isalnum():
        await message.answer("Пожалуйста, введите корректный username в формате @username")
        return

    username = username_input[1:]

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(f"Пользователь с username @{username} не найден")
            return

        await message.answer(f"Пользователь @{username} имеет подписку {user.subscription_type} на {user.subscription} дней. "
                             f"Выберите следующее действие:", reply_markup=kb.adm_start)

    await state.clear()



@rt.callback_query(F.data == 'gpack')
async def check_packs(callback: CallbackQuery, state: FSMContext):
    await callback.answer('💾 Проверить паки')

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        excluded_usernames = ['Неуказано', 'chofpiee']

        artist_counts = []
        spot_counts = []

        for user in users:
            username = user.username or 'no_username'
            if username in excluded_usernames:
                continue  
            artist_count = len(user.received_packs or [])
            spot_count = len(user.received_packs_spot or [])

            artist_counts.append((artist_count, user.username))
            spot_counts.append((spot_count, user.username))

        artist_counts.sort(reverse=True)
        spot_counts.sort(reverse=True)

        top_artists = artist_counts[:20]
        top_spots = spot_counts[:20]

        artist_text = "🎤 Топ 20 артистов:\n"
        for idx, (count, username) in enumerate(top_artists, 1):
            artist_text += f"{idx}. {count} – @{username}\n"

        spot_text = "\n🎧 Топ 20 спотеров:\n"
        for idx, (count, username) in enumerate(top_spots, 1):
            spot_text += f"{idx}. {count} – @{username}\n"

        text_spot_artist = artist_text + spot_text

        text = (
            f"{text_spot_artist}\n\n"
            "Введите username пользователя в формате @username, чьи паки вы хотите проверить:"
        )

        await callback.message.edit_text(text, reply_markup=kb.adm_back)
        await state.set_state(AdminAction.waiting_for_user_username_check_packs)


@rt.message(AdminAction.waiting_for_user_username_check_packs)
async def get_user_subscription(message: Message, state: FSMContext):
    username_input = message.text.strip()

    if not username_input.startswith('@') or len(username_input) < 2:
        await message.answer("Пожалуйста, введите корректный username в формате @username")
        return

    username = username_input[1:].lower()

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(f"Пользователь с username @{username} не найден")
            return

        await message.answer(f"Паки пользователя @{username}: {user.received_packs}, {user.received_packs_spot} "
                             f"Выберите следующее действие:", reply_markup=kb.adm_start)

    await state.clear()


@rt.callback_query(F.data == 'mail')
async def mail(callback: CallbackQuery):
    await callback.answer('📪 Рассылка')
    await callback.message.edit_text('<strong>Выберите вид рассылки:</strong>', parse_mode='HTML',
                                     reply_markup=kb.mail)
@rt.callback_query(F.data == 'automail')
async def automail(callback: CallbackQuery):
    await callback.answer('🤖 Авторассылка')
    await callback.message.edit_text('<strong>Выберите группу для рассылки:</strong>', parse_mode='HTML',
                                     reply_markup=kb.group_mail)
@rt.callback_query(F.data == 'mail_choice')
async def mail_choice(callback: CallbackQuery):
    await callback.answer('📪 Рассылка')
    await callback.message.edit_text('<strong>Выберите группу для рассылки:</strong>', parse_mode='HTML',
                                     reply_markup=kb.fast_mail)


@rt.callback_query(F.data == 'no_sub')
async def no_sub(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return

    await state.set_state(AdminAction.waiting_for_group_no_sub_message)
    await callback.answer('❌ Без бесплатной подписки')
    await callback.message.edit_text("Введите текст сообщения для рассылки:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_group_no_sub_message)
async def get_mailing_no_sub_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    mailing_text = message.caption if message.caption else message.text
    photo = message.photo[-1] if message.photo else None

    await state.set_state(AdminAction.waiting_for_time_no_sub)
    await message.answer("Введите время в формате HH:MM для рассылки:", reply_markup=kb.adm_back)
    await state.update_data(mailing_text=mailing_text, photo=photo)
@rt.message(AdminAction.waiting_for_time_no_sub)
async def get_time_for_no_sub(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    time_text = message.text
    try:
        hour, minute = map(int, time_text.split(':'))
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("Неверный формат времени.")
    except ValueError:
        await message.answer("Неверный формат времени. Пожалуйста, введите время в формате HH:MM.", reply_markup=kb.adm_back)
        return

    user_data = await state.get_data()
    mailing_text = user_data.get('mailing_text')
    photo = user_data.get('photo')

    async with async_session() as session:
        result = await session.execute(
            select(MailingSchedule.send_time)
            .filter(MailingSchedule.group_type == 'no_sub')
            .order_by(MailingSchedule.send_time.desc())
        )

        mailings_no_sub = result.scalars().all()

        send_date = len(mailings_no_sub) + 1

        if not mailings_no_sub:
            send_time = datetime.now(pytz.timezone('Europe/Moscow')).replace(hour=hour, minute=minute, second=0,
                                                                             microsecond=0)
        else:
            send_time = datetime.now(pytz.timezone('Europe/Moscow')).replace(hour=hour, minute=minute, second=0,
                                                                             microsecond=0)

        new_schedule = MailingSchedule(
            group_type='no_sub',
            message_text=mailing_text,
            send_time=send_time,
            send_date=send_date
        )

        async with async_session() as session:
            session.add(new_schedule)
            await session.commit()

    await message.answer(f"Сообщение будет отправлено в {send_time.strftime('%H:%M')} для группы без подписки.",
                         reply_markup=kb.adm_back)
    await state.clear()

@rt.callback_query(F.data == 'end_sub')
async def end_sub(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return

    await state.set_state(AdminAction.waiting_for_group_end_sub_message)
    await callback.answer('✅ Подписка окончена')
    await callback.message.edit_text("Введите текст сообщения для рассылки:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_group_end_sub_message)
async def get_mailing_end_sub_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    mailing_text = message.caption if message.caption else message.text
    photo = message.photo[-1] if message.photo else None

    await state.set_state(AdminAction.waiting_for_time_end_sub)
    await message.answer("Введите время в формате HH:MM для рассылки:", reply_markup=kb.adm_back)
    await state.update_data(mailing_text=mailing_text, photo=photo)
@rt.message(AdminAction.waiting_for_time_end_sub)
async def get_time_for_end_sub(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    time_text = message.text
    try:
        hour, minute = map(int, time_text.split(':'))
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("Неверный формат времени.")
    except ValueError:
        await message.answer("Неверный формат времени. Пожалуйста, введите время в формате HH:MM.", reply_markup=kb.adm_back)
        return

    user_data = await state.get_data()
    mailing_text = user_data.get('mailing_text')
    photo = user_data.get('photo')

    async with async_session() as session:
        result = await session.execute(
            select(MailingSchedule.send_time)
            .filter(MailingSchedule.group_type == 'end_sub')
            .order_by(MailingSchedule.send_time.desc())
        )

        mailings_end_sub = result.scalars().all()

        send_date = len(mailings_end_sub) + 1

        if not mailings_end_sub:
            send_time = datetime.now(pytz.timezone('Europe/Moscow')).replace(hour=hour, minute=minute, second=0,
                                                                             microsecond=0)
        else:
            send_time = datetime.now(pytz.timezone('Europe/Moscow')).replace(hour=hour, minute=minute, second=0,
                                                                             microsecond=0)

        new_schedule = MailingSchedule(
            group_type='end_sub',
            message_text=mailing_text,
            send_time=send_time,
            send_date=send_date
        )

        async with async_session() as session:
            session.add(new_schedule)
            await session.commit()

    await message.answer(
        f"Сообщение будет отправлено в {send_time.strftime('%H:%M')} для группы с завершенной подпиской.",
        reply_markup=kb.adm_back)
    await state.clear()


@rt.callback_query(F.data == 'mailing')
async def start_mailing(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return

    await state.set_state(AdminAction.waiting_for_message)
    await callback.answer('📪 Общая рассылка')
    await callback.message.edit_text("Введите текст сообщения для рассылки:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_message)
async def get_mailing_message(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    mailing_text = message.caption if message.caption else message.text
    photo = message.photo[-1] if message.photo else None
    video = message.video if message.video else None
    document = message.document if message.document else None
    audio = message.audio if message.audio else None

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id.isnot(None)))
        users = result.scalars().all()

        if not users:
            await message.answer("Нет пользователей для рассылки", reply_markup=kb.adm_back)
            return

        print(f"Найдено пользователей: {[user.user_id for user in users]}")
        for user in users:
            try:
                print(f"Отправка сообщения пользователю с ID: {user.user_id}")

                if photo:
                    photo_file = photo.file_id
                    if mailing_text:
                        await message.bot.send_photo(user.user_id, photo_file, caption=mailing_text, parse_mode='HTML')
                    else:
                        await message.bot.send_photo(user.user_id, photo_file)

                elif video:
                    video_file = video.file_id
                    if mailing_text:
                        await message.bot.send_video(user.user_id, video_file, caption=mailing_text)
                    else:
                        await message.bot.send_video(user.user_id, video_file)

                elif document:
                    document_file = document.file_id
                    if mailing_text:
                        await message.bot.send_document(user.user_id, document_file, caption=mailing_text)
                    else:
                        await message.bot.send_document(user.user_id, document_file)

                elif audio:
                    audio_file = audio.file_id
                    if mailing_text:
                        await message.bot.send_audio(user.user_id, audio_file, caption=mailing_text)
                    else:
                        await message.bot.send_audio(user.user_id, audio_file)

                elif mailing_text:
                    await message.bot.send_message(user.user_id, mailing_text, parse_mode='HTML',
                                                   disable_web_page_preview=True)

            except Exception as e:
                print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

        await message.answer("Сообщение успешно отправлено всем пользователям", reply_markup=kb.adm_back)
        await state.clear()

@rt.callback_query(F.data == 'for_sub')
async def for_sub(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return

    await state.set_state(AdminAction.waiting_for_sub_message)
    await callback.answer('💰 Для платных подписчиков')
    await callback.message.edit_text("Введите текст сообщения для рассылки подписчикам:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_sub_message)
async def get_mailing_for_sub(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    mailing_text = message.caption if message.caption else message.text
    photo = message.photo[-1] if message.photo else None
    video = message.video if message.video else None
    document = message.document if message.document else None
    audio = message.audio if message.audio else None

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.subscription > 0, User.paid_sub == 1))
        users = result.scalars().all()

        if not users:
            await message.answer("Нет подписчиков для рассылки", reply_markup=kb.adm_back)
            return

        for user in users:
            try:
                print(f"Отправка сообщения пользователю с ID: {user.user_id}")

                if photo:
                    photo_file = photo.file_id
                    if mailing_text:
                        await message.bot.send_photo(user.user_id, photo_file, caption=mailing_text, parse_mode='HTML')
                    else:
                        await message.bot.send_photo(user.user_id, photo_file)

                elif video:
                    video_file = video.file_id
                    if mailing_text:
                        await message.bot.send_video(user.user_id, video_file, caption=mailing_text)
                    else:
                        await message.bot.send_video(user.user_id, video_file)

                elif document:
                    document_file = document.file_id
                    if mailing_text:
                        await message.bot.send_document(user.user_id, document_file, caption=mailing_text)
                    else:
                        await message.bot.send_document(user.user_id, document_file)

                elif audio:
                    audio_file = audio.file_id
                    if mailing_text:
                        await message.bot.send_audio(user.user_id, audio_file, caption=mailing_text)
                    else:
                        await message.bot.send_audio(user.user_id, audio_file)

                elif mailing_text:
                    await message.bot.send_message(user.user_id, mailing_text, parse_mode='HTML',
                                                   disable_web_page_preview=True)

            except Exception as e:
                print(f"Ошибка при отправке сообщения подписчику {user.user_id}: {e}")

    await message.answer("Сообщение успешно отправлено подписчикам", reply_markup=kb.adm_back)
    await state.clear()

@rt.callback_query(F.data == 'who_free')
async def who_free(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return

    await state.set_state(AdminAction.waiting_for_who_free_message)
    await callback.answer('🆓 Кто брал бесплатную')
    await callback.message.edit_text("Введите текст сообщения для рассылки тем, кто брал бесплатную подписку:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_who_free_message)
async def get_mailing_who_free(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    photo = message.photo[-1] if message.photo else None
    video = message.video if message.video else None
    document = message.document if message.document else None
    audio = message.audio if message.audio else None
    mailing_text = message.caption if message.caption else message.text

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.free_subscription_used == True, User.paid_sub == 0, User.subscription == 0))
        users = result.scalars().all()

        if not users:
            await message.answer("Нет пользователей, кто брал бесплатную подписку", reply_markup=kb.adm_back)
            return

        for user in users:
            try:
                print(f"Отправка сообщения пользователю с ID: {user.user_id}")

                if photo:
                    photo_file = photo.file_id
                    if mailing_text:
                        await message.bot.send_photo(user.user_id, photo_file, caption=mailing_text, parse_mode='HTML')
                    else:
                        await message.bot.send_photo(user.user_id, photo_file)

                elif video:
                    video_file = video.file_id
                    if mailing_text:
                        await message.bot.send_video(user.user_id, video_file, caption=mailing_text)
                    else:
                        await message.bot.send_video(user.user_id, video_file)

                elif document:
                    document_file = document.file_id
                    if mailing_text:
                        await message.bot.send_document(user.user_id, document_file, caption=mailing_text)
                    else:
                        await message.bot.send_document(user.user_id, document_file)

                elif audio:
                    audio_file = audio.file_id
                    if mailing_text:
                        await message.bot.send_audio(user.user_id, audio_file, caption=mailing_text)
                    else:
                        await message.bot.send_audio(user.user_id, audio_file)

                elif mailing_text:
                    await message.bot.send_message(user.user_id, mailing_text, parse_mode='HTML',
                                                   disable_web_page_preview=True)

            except Exception as e:
                print(f"Ошибка при отправке сообщения {user.user_id}: {e}")

    await message.answer("Сообщение успешно отправлено тем, кто брал бесплатную подписку", reply_markup=kb.adm_back)
    await state.clear()

@rt.callback_query(F.data == 'who_no_free')
async def who_no_free(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return

    await state.set_state(AdminAction.waiting_for_who_no_free_message)
    await callback.answer('🆓 Кто не брал бесплатную')
    await callback.message.edit_text("Введите текст сообщения для рассылки тем, кто не брал бесплатную подписку:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_who_no_free_message)
async def get_mailing_who_no_free(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    mailing_text = message.caption if message.caption else message.text
    photo = message.photo[-1] if message.photo else None
    video = message.video if message.video else None
    document = message.document if message.document else None
    audio = message.audio if message.audio else None
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.free_subscription_used == False, User.paid_sub == 0, User.subscription == 0))
        users = result.scalars().all()

        if not users:
            await message.answer("Нет пользователей, кто не брал бесплатную подписку", reply_markup=kb.adm_back)
            return

        for user in users:
            try:
                print(f"Отправка сообщения пользователю с ID: {user.user_id}")

                if photo:
                    photo_file = photo.file_id
                    if mailing_text:
                        await message.bot.send_photo(user.user_id, photo_file, caption=mailing_text, parse_mode='HTML')
                    else:
                        await message.bot.send_photo(user.user_id, photo_file)

                elif video:
                    video_file = video.file_id
                    if mailing_text:
                        await message.bot.send_video(user.user_id, video_file, caption=mailing_text)
                    else:
                        await message.bot.send_video(user.user_id, video_file)

                elif document:
                    document_file = document.file_id
                    if mailing_text:
                        await message.bot.send_document(user.user_id, document_file, caption=mailing_text)
                    else:
                        await message.bot.send_document(user.user_id, document_file)

                elif audio:
                    audio_file = audio.file_id
                    if mailing_text:
                        await message.bot.send_audio(user.user_id, audio_file, caption=mailing_text)
                    else:
                        await message.bot.send_audio(user.user_id, audio_file)

                elif mailing_text:
                    await message.bot.send_message(user.user_id, mailing_text, parse_mode='HTML',
                                                   disable_web_page_preview=True)

            except Exception as e:
                print(f"Ошибка при отправке сообщения {user.user_id}: {e}")

    await message.answer("Сообщение успешно отправлено тем, кто не брал бесплатную подписку", reply_markup=kb.adm_back)
    await state.clear()

@rt.callback_query(F.data == 'who_paid')
async def for_sub(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return

    await state.set_state(AdminAction.waiting_for_who_paid_message)
    await callback.answer('💰 Кто брал платную')
    await callback.message.edit_text("Введите текст сообщения для рассылки бывшим подписчикам:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_who_paid_message)
async def get_mailing_for_paid_sub(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    mailing_text = message.caption if message.caption else message.text
    photo = message.photo[-1] if message.photo else None
    video = message.video if message.video else None
    document = message.document if message.document else None
    audio = message.audio if message.audio else None
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.subscription == 0, User.paid_sub == 1))
        users = result.scalars().all()

        if not users:
            await message.answer("Нет юзеров для рассылки", reply_markup=kb.adm_back)
            return

        for user in users:
            try:
                print(f"Отправка сообщения пользователю с ID: {user.user_id}")

                if photo:
                    photo_file = photo.file_id
                    if mailing_text:
                        await message.bot.send_photo(user.user_id, photo_file, caption=mailing_text, parse_mode='HTML')
                    else:
                        await message.bot.send_photo(user.user_id, photo_file)

                elif video:
                    video_file = video.file_id
                    if mailing_text:
                        await message.bot.send_video(user.user_id, video_file, caption=mailing_text)
                    else:
                        await message.bot.send_video(user.user_id, video_file)

                elif document:
                    document_file = document.file_id
                    if mailing_text:
                        await message.bot.send_document(user.user_id, document_file, caption=mailing_text)
                    else:
                        await message.bot.send_document(user.user_id, document_file)

                elif audio:
                    audio_file = audio.file_id
                    if mailing_text:
                        await message.bot.send_audio(user.user_id, audio_file, caption=mailing_text)
                    else:
                        await message.bot.send_audio(user.user_id, audio_file)

                elif mailing_text:
                    await message.bot.send_message(user.user_id, mailing_text, parse_mode='HTML',
                                                   disable_web_page_preview=True)

            except Exception as e:
                print(f"Ошибка при отправке сообщения юзеру {user.user_id}: {e}")

    await message.answer("Сообщение успешно отправлено юзерам", reply_markup=kb.adm_back)
    await state.clear()

@rt.callback_query(F.data == 'who_in_free_sub')
async def for_sub(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return

    await state.set_state(AdminAction.waiting_for_who_in_free_message)
    await callback.answer('🆓 Для бесплатных подписчиков')
    await callback.message.edit_text("Введите текст сообщения для рассылки бесплатным подписчикам:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_who_in_free_message)
async def get_mailing_for_paid_sub(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    mailing_text = message.caption if message.caption else message.text
    photo = message.photo[-1] if message.photo else None
    video = message.video if message.video else None
    document = message.document if message.document else None
    audio = message.audio if message.audio else None
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.subscription > 0, User.paid_sub == 0, User.free_subscription_used == True))
        users = result.scalars().all()

        if not users:
            await message.answer("Нет подписчиков для рассылки", reply_markup=kb.adm_back)
            return

        for user in users:
            try:
                print(f"Отправка сообщения пользователю с ID: {user.user_id}")

                if photo:
                    photo_file = photo.file_id
                    if mailing_text:
                        await message.bot.send_photo(user.user_id, photo_file, caption=mailing_text, parse_mode='HTML')
                    else:
                        await message.bot.send_photo(user.user_id, photo_file)

                elif video:
                    video_file = video.file_id
                    if mailing_text:
                        await message.bot.send_video(user.user_id, video_file, caption=mailing_text)
                    else:
                        await message.bot.send_video(user.user_id, video_file)

                elif document:
                    document_file = document.file_id
                    if mailing_text:
                        await message.bot.send_document(user.user_id, document_file, caption=mailing_text)
                    else:
                        await message.bot.send_document(user.user_id, document_file)

                elif audio:
                    audio_file = audio.file_id
                    if mailing_text:
                        await message.bot.send_audio(user.user_id, audio_file, caption=mailing_text)
                    else:
                        await message.bot.send_audio(user.user_id, audio_file)

                elif mailing_text:
                    await message.bot.send_message(user.user_id, mailing_text, parse_mode='HTML',
                                                   disable_web_page_preview=True)

            except Exception as e:
                print(f"Ошибка при отправке сообщения юзеру {user.user_id}: {e}")

    await message.answer("Сообщение успешно отправлено бесплатным подписчикам", reply_markup=kb.adm_back)
    await state.clear()

@rt.callback_query(F.data == 'gold_mail')
async def gold_mail(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return

    await state.set_state(AdminAction.waiting_for_who_gold_mail)
    await callback.answer('GOLD')
    await callback.message.edit_text("Введите текст сообщения для рассылки GOLD подписчикам:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_who_gold_mail)
async def get_mailing_for_gold_mail(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    mailing_text = message.caption if message.caption else message.text
    photo = message.photo[-1] if message.photo else None
    video = message.video if message.video else None
    document = message.document if message.document else None
    audio = message.audio if message.audio else None

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.subscription > 0, User.paid_sub == 1, User.subscription_type == 'gold'))
        users = result.scalars().all()

        if not users:
            await message.answer("Нет подписчиков для рассылки", reply_markup=kb.adm_back)
            return

        for user in users:
            try:
                print(f"Отправка сообщения пользователю с ID: {user.user_id}")

                if photo:
                    photo_file = photo.file_id
                    if mailing_text:
                        await message.bot.send_photo(user.user_id, photo_file, caption=mailing_text, parse_mode='HTML')
                    else:
                        await message.bot.send_photo(user.user_id, photo_file)

                elif video:
                    video_file = video.file_id
                    if mailing_text:
                        await message.bot.send_video(user.user_id, video_file, caption=mailing_text)
                    else:
                        await message.bot.send_video(user.user_id, video_file)

                elif document:
                    document_file = document.file_id
                    if mailing_text:
                        await message.bot.send_document(user.user_id, document_file, caption=mailing_text)
                    else:
                        await message.bot.send_document(user.user_id, document_file)

                elif audio:
                    audio_file = audio.file_id
                    if mailing_text:
                        await message.bot.send_audio(user.user_id, audio_file, caption=mailing_text)
                    else:
                        await message.bot.send_audio(user.user_id, audio_file)

                elif mailing_text:
                    await message.bot.send_message(user.user_id, mailing_text, parse_mode='HTML',
                                                   disable_web_page_preview=True)

            except Exception as e:
                print(f"Ошибка при отправке сообщения подписчику {user.user_id}: {e}")

    await message.answer("Сообщение успешно отправлено подписчикам", reply_markup=kb.adm_back)
    await state.clear()

@rt.callback_query(F.data == 'spot_mail')
async def spot_mail(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return

    await state.set_state(AdminAction.waiting_for_who_spot_mail)
    await callback.answer('SPOT')
    await callback.message.edit_text("Введите текст сообщения для рассылки SPOT подписчикам:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_who_spot_mail)
async def get_mailing_spot_mail(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    mailing_text = message.caption if message.caption else message.text
    photo = message.photo[-1] if message.photo else None
    video = message.video if message.video else None
    document = message.document if message.document else None
    audio = message.audio if message.audio else None

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.subscription > 0, User.paid_sub == 1, User.subscription_type == 'spot'))
        users = result.scalars().all()

        if not users:
            await message.answer("Нет подписчиков для рассылки", reply_markup=kb.adm_back)
            return

        for user in users:
            try:
                print(f"Отправка сообщения пользователю с ID: {user.user_id}")

                if photo:
                    photo_file = photo.file_id
                    if mailing_text:
                        await message.bot.send_photo(user.user_id, photo_file, caption=mailing_text, parse_mode='HTML')
                    else:
                        await message.bot.send_photo(user.user_id, photo_file)

                elif video:
                    video_file = video.file_id
                    if mailing_text:
                        await message.bot.send_video(user.user_id, video_file, caption=mailing_text)
                    else:
                        await message.bot.send_video(user.user_id, video_file)

                elif document:
                    document_file = document.file_id
                    if mailing_text:
                        await message.bot.send_document(user.user_id, document_file, caption=mailing_text)
                    else:
                        await message.bot.send_document(user.user_id, document_file)

                elif audio:
                    audio_file = audio.file_id
                    if mailing_text:
                        await message.bot.send_audio(user.user_id, audio_file, caption=mailing_text)
                    else:
                        await message.bot.send_audio(user.user_id, audio_file)

                elif mailing_text:
                    await message.bot.send_message(user.user_id, mailing_text, parse_mode='HTML',
                                                   disable_web_page_preview=True)

            except Exception as e:
                print(f"Ошибка при отправке сообщения подписчику {user.user_id}: {e}")

    await message.answer("Сообщение успешно отправлено подписчикам", reply_markup=kb.adm_back)
    await state.clear()

@rt.callback_query(F.data == 'artists_mail')
async def artists_mail(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    if not is_admin(user_id):
        await callback.answer("Вы не являетесь администратором!", reply_markup=kb.adm_back)
        return

    await state.set_state(AdminAction.waiting_for_who_artists_mail)
    await callback.answer('ARTISTS')
    await callback.message.edit_text("Введите текст сообщения для рассылки ARTISTS подписчикам:", reply_markup=kb.adm_back)
@rt.message(AdminAction.waiting_for_who_artists_mail)
async def get_mailing_artists_mail(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять рассылки", reply_markup=kb.adm_back)
        return

    mailing_text = message.caption if message.caption else message.text
    photo = message.photo[-1] if message.photo else None
    video = message.video if message.video else None
    document = message.document if message.document else None
    audio = message.audio if message.audio else None

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.subscription > 0, User.paid_sub == 1, User.subscription_type == 'artists'))
        users = result.scalars().all()

        if not users:
            await message.answer("Нет подписчиков для рассылки", reply_markup=kb.adm_back)
            return

        for user in users:
            try:
                print(f"Отправка сообщения пользователю с ID: {user.user_id}")

                if photo:
                    photo_file = photo.file_id
                    if mailing_text:
                        await message.bot.send_photo(user.user_id, photo_file, caption=mailing_text, parse_mode='HTML')
                    else:
                        await message.bot.send_photo(user.user_id, photo_file)

                elif video:
                    video_file = video.file_id
                    if mailing_text:
                        await message.bot.send_video(user.user_id, video_file, caption=mailing_text)
                    else:
                        await message.bot.send_video(user.user_id, video_file)

                elif document:
                    document_file = document.file_id
                    if mailing_text:
                        await message.bot.send_document(user.user_id, document_file, caption=mailing_text)
                    else:
                        await message.bot.send_document(user.user_id, document_file)

                elif audio:
                    audio_file = audio.file_id
                    if mailing_text:
                        await message.bot.send_audio(user.user_id, audio_file, caption=mailing_text)
                    else:
                        await message.bot.send_audio(user.user_id, audio_file)

                elif mailing_text:
                    await message.bot.send_message(user.user_id, mailing_text, parse_mode='HTML',
                                                   disable_web_page_preview=True)

            except Exception as e:
                print(f"Ошибка при отправке сообщения подписчику {user.user_id}: {e}")

    await message.answer("Сообщение успешно отправлено подписчикам", reply_markup=kb.adm_back)
    await state.clear()


@rt.message(F.text == '🎯 Главное меню')
async def main_menu(message: Message, state: FSMContext):
    await rq.set_user(message.from_user.id, message.from_user.username)
    await message.answer('<strong>Выберите действия по кнопкам ниже:</strong>',
                         parse_mode="HTML",
                         reply_markup=kb.M_menu)
    await state.clear()

##
@rt.callback_query(F.data == 'profile')
async def profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if user:
            remaining_days = user.subscription

            await callback.answer('🎨 Профиль')
            if remaining_days > 0 and user.subscription_type == 'gold':
                await callback.message.edit_text(
                    f"🎨 Профиль {callback.from_user.first_name}\n\n"
                    f"<strong>Подписка:</strong> ARTISTS + SPOT | GOLD 🟡 \n\n"
                    f"<strong>До окончания подписки:</strong> {remaining_days} дней\n",
                    parse_mode="HTML", reply_markup=kb.back)
            elif remaining_days > 0 and user.subscription_type == 'spot':
                await callback.message.edit_text(
                    f"🎨 Профиль {callback.from_user.first_name}\n\n"
                    f"<strong>Подписка:</strong> SPOT | BASIC ⚪️ \n\n"
                    f"<strong>До окончания подписки:</strong> {remaining_days} дней\n",
                    parse_mode="HTML", reply_markup=kb.col_swap)
            elif remaining_days > 0 and user.subscription_type == 'artists':
                await callback.message.edit_text(
                    f"🎨 Профиль {callback.from_user.first_name}\n\n"
                    f"<strong>Подписка:</strong> ARTISTS | BASIC ⚪️ \n\n"
                    f"<strong>До окончания подписки:</strong> {remaining_days} дней\n",
                    parse_mode="HTML", reply_markup=kb.col_swap)
            else:
                await callback.message.edit_text(
                    f'🎨 Профиль {callback.from_user.first_name}\n\n'
                    f'<strong>Подписка:</strong> неактивна\n\n',
                    parse_mode="HTML", reply_markup=kb.subscription2)
        else:
            await callback.answer(f"Пользователь с ID {user_id} не найден в базе данных. Введите команду /get_profile")

def is_time_allowed():
    moscow_tz = pytz.timezone('Europe/Moscow')
    now_moscow = datetime.now(moscow_tz).time()
    return now_moscow < datetime.strptime('18:00', '%H:%M').time() or now_moscow > datetime.strptime('19:00', '%H:%M').time()
@rt.callback_query(F.data == 'swap_sub')
async def swap_sub(callback: CallbackQuery):
    if not is_time_allowed():
        await callback.answer('❗️Не доступно с 18:00 до 19:00 МСК', show_alert=True)
        return

    await callback.answer('🕹 Сменить подписку')
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user.subscription_type == 'spot':
            await callback.message.edit_text('<strong>Вы уверены, что хотите сменить подписку с </strong>'
                                             '<strong><a href="https://telegra.ph/Podpiska-SPOT-03-16">SPOT</a> на </strong>'
                                             '<strong><a href="https://telegra.ph/Podpiska-ARTISTS-03-16">ARTISTS</a>?</strong>\n\n'
                                             '<strong>⚠ При смене подписки вы начнете получать 20 артистов вместо 5 SPOT-аккаунтов</strong>',
                                             reply_markup=kb.are_you_sure, parse_mode='HTML', disable_web_page_preview=True)
        elif user.subscription_type == 'artists':
            await callback.message.edit_text('<strong>Вы уверены, что хотите сменить подписку с </strong>'
                                             '<strong><a href="https://telegra.ph/Podpiska-ARTISTS-03-16">ARTISTS</a> на </strong>'
                                             '<strong><a href="https://telegra.ph/Podpiska-SPOT-03-16">SPOT</a>?</strong>\n\n'
                                             '<strong>⚠ При смене подписки вы начнете получать 5 SPOT-аккаунтов вместо 20 артистов</strong>',
                                             reply_markup=kb.are_you_sure, parse_mode='HTML', disable_web_page_preview=True)
        else:
            await callback.message.edit_text('Вы не можете сменить подписку', parse_mode='HTML', reply_markup=kb.back)
@rt.callback_query(F.data == 'user_yes')
async def user_yes(callback: CallbackQuery):
    if not is_time_allowed():
        await callback.answer('❗️Не доступно с 18:00 до 19:00 МСК', show_alert=True)
        return

    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user.subscription_type == 'spot':
            user.subscription_type = 'artists'
            await callback.answer('✅ Успешно')
            await callback.message.edit_text('<strong>✅ Вы успешно сменили подписку на ARTISTS</strong>',
                                             reply_markup=kb.back_to_profile, parse_mode='HTML', disable_web_page_preview=True)
        elif user.subscription_type == 'artists':
            user.subscription_type = 'spot'
            await callback.answer('✅ Успешно')
            await callback.message.edit_text('<strong>✅ Вы успешно сменили подписку на SPOT</strong>',
                                             reply_markup=kb.back_to_profile, parse_mode='HTML', disable_web_page_preview=True)
        else:
            await callback.answer('error')
            await callback.message.edit_text('Вы не можете сменить подписку', reply_markup=kb.back_to_profile)
        await session.commit()
@rt.callback_query(F.data == 'back_to_profile')
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    await callback.answer('🎨 В профиль')
    await state.clear()
    await profile(callback)
##

@rt.callback_query(F.data == 'm_back')
async def m_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer('🎯 главное меню')
    await state.clear()
    await callback.message.edit_text('<strong>Выберите действия по кнопкам ниже:</strong>',
                                     parse_mode="HTML",
                                     reply_markup=kb.M_menu)
@rt.callback_query(F.data == 'back')
async def back(callback: CallbackQuery, state: FSMContext):
    await callback.answer('↩️ Назад')
    await state.clear()
    await callback.message.edit_text('<strong>Выберите действия по кнопкам ниже:</strong>',
                                     parse_mode="HTML",
                                     reply_markup=kb.M_menu)
@rt.callback_query(F.data == 'back_p')
async def back_p(callback: CallbackQuery):
    await callback.answer('↩️ Назад')
    user_id = callback.from_user.id
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if user:
            remaining_days = user.subscription

            await callback.answer('🎨 Профиль')
            if remaining_days > 0 and user.subscription_type == 'gold':
                await callback.message.edit_text(
                    f"🎨 Профиль {callback.from_user.first_name}\n\n"
                    f"<strong>Подписка:</strong>  ARTISTS + SPOT | GOLD 🟡\n\n"
                    f"<strong>До окончания подписки:</strong> {remaining_days} дней\n",
                    parse_mode="HTML", reply_markup=kb.back)
            elif remaining_days > 0 and user.subscription_type == 'spot':
                await callback.message.edit_text(
                    f"🎨 Профиль {callback.from_user.first_name}\n\n"
                    f"<strong>Подписка:</strong> SPOT | BASIC ⚪️ \n\n"
                    f"<strong>До окончания подписки:</strong> {remaining_days} дней\n",
                    parse_mode="HTML", reply_markup=kb.col_swap)
            elif remaining_days > 0 and user.subscription_type == 'artists':
                await callback.message.edit_text(
                    f"🎨 Профиль {callback.from_user.first_name}\n\n"
                    f"<strong>Подписка:</strong> ARTISTS | BASIC ⚪️ \n\n"
                    f"<strong>До окончания подписки:</strong> {remaining_days} дней\n",
                    parse_mode="HTML", reply_markup=kb.col_swap)
            else:
                await callback.message.edit_text(
                    f'🎨 Профиль {callback.from_user.first_name}\n\n'
                    f'<strong>Состояние подписки:</strong> неактивна\n\n',
                    parse_mode="HTML", reply_markup=kb.subscription2)
        else:
            await callback.answer(f"Пользователь с ID {user_id} не найден в базе данных. Введите команду /get_profile")
@rt.callback_query(F.data == 'back_c')
async def back_c(callback: CallbackQuery, state: FSMContext):
    await callback.answer('↩️ Назад')
    user_id = callback.from_user.id
    await show_collection(callback, state)
@rt.callback_query(F.data == 'col_back')
async def col_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer('↩️ Назад')
    user_id = callback.from_user.id
    await state.clear()
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if not user.received_packs_spot or not user.received_packs:
            await callback.message.edit_text('<strong>Выберите действия по кнопкам ниже:</strong>',reply_markup=kb.M_menu,
                                            parse_mode='HTML')
        else:
            await show_collection(callback, state)
@rt.callback_query(F.data == 'back_')
async def back_(callback: CallbackQuery):
    await callback.answer('↩️ Назад')
    await user_get_sub(callback)
@rt.callback_query(F.data == 'back_pr')
async def back_pr(callback: CallbackQuery):
    await callback.answer('↩️ Назад')
    await profile_p(callback)
@rt.callback_query(F.data == 'back_co')
async def back_co(callback: CallbackQuery):
    await callback.answer('↩️ Назад')
    await profile_c(callback)
@rt.callback_query(F.data == 'back_to_spot')
async def back_to_spot(callback: CallbackQuery, state: FSMContext):
    await callback.answer('↩️ Назад')
    await state.clear()
    await show_spot(callback, state)
@rt.callback_query(F.data == 'back_to_art')
async def back_to_art(callback: CallbackQuery, state: FSMContext):
    await callback.answer('↩️ Назад')
    await state.clear()
    await show_artists(callback, state)

##
@rt.callback_query(F.data =='collection')
async def show_collection(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await callback.answer('💾 Коллекция')
    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if not user.received_packs_spot and user.received_packs:
            await show_artists(callback, state)
        if not user.received_packs and user.received_packs_spot:
            await show_spot(callback, state)
        if user.received_packs and user.received_packs_spot:
            await callback.message.edit_text('<strong>Выберите категорию по кнопкам ниже:</strong>', parse_mode='HTML', reply_markup=kb.spot_artists_col)
        if user.subscription <= 0:
            if not user.received_packs and not user.received_packs_spot:
                await callback.message.edit_text("<strong>Ваша подписка неактивна!</strong>\n\n"
                                                 "Оформите подписку, чтобы получить доступ к функционалу бота",
                                                 parse_mode='HTML', reply_markup=kb.subscription3)
        if user.subscription > 0:
            if not user.received_packs and not user.received_packs_spot:
                await callback.message.edit_text("<strong>Нет доступных паков для просмотра</strong>", parse_mode='HTML',reply_markup=kb.back)

@rt.callback_query(F.data == 'spot_col')
async def show_spot(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    print(f"Requesting user with user_id: {user_id}")

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == user_id))
        user = result.scalar_one_or_none()

    if user is None:
        await callback.message.edit_text("Пользователь не найден", reply_markup=kb.back)
        return

    print(f"User ID: {user_id}, Subscription: {user.subscription}, Subscription Start: {user.subscription_start}")

    if user.subscription <= 0:
        if not user.received_packs_spot:
            await callback.message.edit_text("<strong>Ваша подписка неактивна!</strong>\n\n"
                                             "Оформите подписку, чтобы получить доступ к функционалу бота",
                                             parse_mode='HTML',
                                             reply_markup=kb.subscription3)
            return

    if not user.subscription_start:
        await callback.message.edit_text("Ошибка подписки: время начала подписки отсутствует", reply_markup=kb.back)
        return

    print(f"Received packs for user: {user.received_packs_spot}")


    if not user.received_packs_spot:
        await callback.message.edit_text("<strong>Нет доступных паков для просмотра</strong>", parse_mode='HTML',reply_markup=kb.back)
        return

    async with async_session() as session:
        result = await session.execute(
            select(SpotPack).filter(SpotPack.id.in_(user.received_packs_spot))
        )
        packs = result.scalars().all()

    if not packs:
        await callback.message.edit_text("Нет доступных паков для просмотра", reply_markup=kb.back)
        return

    await state.update_data(current_page=1)

    await send_pack_page_spot(callback.message, user, 1, state)
async def send_pack_page_spot(message: Message, user: User, page: int, state: FSMContext):
    items_per_page = 1
    total_items = len(user.received_packs_spot)
    total_pages = get_total_pages(total_items, items_per_page)


    if total_pages == 0:
        await message.edit_text("Нет доступных паков для просмотра", reply_markup=kb.back)
        return

    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    page_packs = user.received_packs_spot[start_index:end_index]

    formatted_usernames = []

    for i, pack_id in enumerate(page_packs):
        async with async_session() as session:
            result = await session.execute(select(SpotPack).filter(SpotPack.id == pack_id))
            pack = result.scalar_one_or_none()
            if pack:
                usernames = pack.usernames.split(",")
                formatted_usernames.extend([
                    f"**{i + 1}.** {username.strip().replace('_', '\\_')} ([ссылка](https://www.instagram.com/{username.strip()}/))"
                    for i, username in enumerate(usernames)
                ])

    formatted_message = "\n".join(formatted_usernames)

    if formatted_message:
        await message.edit_text(
            f"{formatted_message}",
            parse_mode="Markdown",
            reply_markup=kb.database_navigation_sec_spot(page, total_pages)
        )


    await state.update_data(current_page=page)
async def send_pack_page_spot_2(message: Message, user: User, page: int, state: FSMContext):
    items_per_page = 1
    total_items = len(user.received_packs_spot)
    total_pages = get_total_pages(total_items, items_per_page)


    if total_pages == 0:
        await message.edit_text("Нет доступных паков для просмотра", reply_markup=kb.back)
        return

    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    page_packs = user.received_packs_spot[start_index:end_index]

    formatted_usernames = []

    for i, pack_id in enumerate(page_packs):
        async with async_session() as session:
            result = await session.execute(select(SpotPack).filter(SpotPack.id == pack_id))
            pack = result.scalar_one_or_none()
            if pack:
                usernames = pack.usernames.split(",")
                formatted_usernames.extend([
                    f"**{i + 1}.** {username.strip().replace('_', '\\_')} ([ссылка](https://www.instagram.com/{username.strip()}/))"
                    for i, username in enumerate(usernames)
                ])

    formatted_message = "\n".join(formatted_usernames)

    if formatted_message:
        await message.answer(
            f"{formatted_message}",
            parse_mode="Markdown",
            reply_markup=kb.database_navigation_sec_spot(page, total_pages)
        )

    await state.update_data(current_page=page)
@rt.callback_query(F.data.startswith("spotpag_"))
async def page_navigation_spot(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_page = data.get("current_page", 1)
    direction = callback.data.split("_")[1]

    async with async_session() as session:
        result = await session.execute(
            select(User).filter(User.user_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

    if not user:
        await callback.answer('Пользователь не найден')
        return

    total_items = len(user.received_packs_spot)
    total_pages = get_total_pages(total_items, 1)

    if direction == "nex":
        current_page = current_page + 1 if current_page < total_pages else 1
        await callback.answer('❯')
    elif direction == "pre":
        current_page = current_page - 1 if current_page > 1 else total_pages
        await callback.answer('❮')

    await send_pack_page_spot(callback.message, user, current_page, state)
@rt.callback_query(F.data == "go_to_page_spot_col")
async def request_page_number_spot_col(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "<strong>Введите номер страницы, на которую хотите перейти:</strong>",
        reply_markup=kb.back_to_col_spot,
        parse_mode='HTML'
    )
    await state.set_state(UserState.enter_page_number_spot)
@rt.message(UserState.enter_page_number_spot)
async def go_to_page_spot(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text.isdigit():
        page_number = int(message.text)

        async with async_session() as session:
            result = await session.execute(
                select(User).filter(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()

        if not user:
            await message.answer("Пользователь не найден.", reply_markup=kb.back_to_col_spot)
            return

        total_items = len(user.received_packs_spot)
        total_pages = get_total_pages(total_items, 1)

        if 1 <= page_number <= total_pages:
            await state.update_data(current_page=page_number)
            await send_pack_page_spot_2(message, user, page_number, state)
        else:
            await message.answer(f"<strong>⚠️ Введите число от 1 до {total_pages}.</strong>",
                                 reply_markup=kb.back_to_col_spot,
                                 parse_mode="HTML")
    else:
        await message.answer("<strong>⚠️ Неизвестная команда. Введите номер страницы.</strong>",
                             reply_markup=kb.back_to_col_spot,
                             parse_mode="HTML")


@rt.callback_query(F.data == "artists_col")
async def show_artists(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    print(f"Requesting user with user_id: {user_id}")

    async with async_session() as session:
        result = await session.execute(select(User).filter(User.user_id == user_id))
        user = result.scalar_one_or_none()

    if user is None:
        await callback.message.edit_text("Пользователь не найден", reply_markup=kb.back)
        return

    print(f"User ID: {user_id}, Subscription: {user.subscription}, Subscription Start: {user.subscription_start}")

    if user.subscription <= 0:
        if not user.received_packs:
            await callback.message.edit_text("<strong>Ваша подписка неактивна!</strong>\n\n"
                                             "Оформите подписку, чтобы получить доступ к функционалу бота",
                                             parse_mode='HTML',
                                             reply_markup=kb.subscription3)
            return
    if not user.subscription_start:
        await callback.message.edit_text("Ошибка подписки: время начала подписки отсутствует", reply_markup=kb.back)
        return

    print(f"Received packs for user: {user.received_packs}")


    if not user.received_packs:
        await callback.message.edit_text("<strong>Нет доступных паков для просмотра</strong>", parse_mode='HTML',reply_markup=kb.back)
        return

    async with async_session() as session:
        result = await session.execute(
            select(ArtistPack).filter(ArtistPack.id.in_(user.received_packs))
        )
        packs = result.scalars().all()

    if not packs:
        await callback.message.edit_text("Нет доступных паков для просмотра", reply_markup=kb.back)
        return

    await state.update_data(current_page=1)

    await send_pack_page_artists(callback.message, user, 1, state)
async def send_pack_page_artists(message: Message, user: User, page: int, state: FSMContext):
    items_per_page = 1
    total_items = len(user.received_packs)
    total_pages = get_total_pages(total_items, items_per_page)


    if total_pages == 0:
        await message.edit_text("Нет доступных паков для просмотра", reply_markup=kb.back)
        return

    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    page_packs = user.received_packs[start_index:end_index]

    formatted_usernames = []

    for i, pack_id in enumerate(page_packs):
        async with async_session() as session:
            result = await session.execute(select(ArtistPack).filter(ArtistPack.id == pack_id))
            pack = result.scalar_one_or_none()
            if pack:
                usernames = pack.usernames.split(",")
                formatted_usernames.extend([
                    f"**{i + 1}.** {username.strip().replace('_', '\\_')} ([ссылка](https://www.instagram.com/{username.strip()}/))"
                    for i, username in enumerate(usernames)
                ])

    formatted_message = "\n".join(formatted_usernames)

    if formatted_message:
        await message.edit_text(
            f"{formatted_message}",
            parse_mode="Markdown",
            reply_markup=kb.database_navigation_sec(page, total_pages)
        )


    await state.update_data(current_page=page)
async def send_pack_page_artists_2(message: Message, user: User, page: int, state: FSMContext):
    items_per_page = 1
    total_items = len(user.received_packs)
    total_pages = get_total_pages(total_items, items_per_page)


    if total_pages == 0:
        await message.edit_text("Нет доступных паков для просмотра", reply_markup=kb.back)
        return

    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    page_packs = user.received_packs[start_index:end_index]

    formatted_usernames = []

    for i, pack_id in enumerate(page_packs):
        async with async_session() as session:
            result = await session.execute(select(ArtistPack).filter(ArtistPack.id == pack_id))
            pack = result.scalar_one_or_none()
            if pack:
                usernames = pack.usernames.split(",")
                formatted_usernames.extend([
                    f"**{i + 1}.** {username.strip().replace('_', '\\_')} ([ссылка](https://www.instagram.com/{username.strip()}/))"
                    for i, username in enumerate(usernames)
                ])

    formatted_message = "\n".join(formatted_usernames)

    if formatted_message:
        await message.answer(
            f"{formatted_message}",
            parse_mode="Markdown",
            reply_markup=kb.database_navigation_sec(page, total_pages)
        )


    await state.update_data(current_page=page)
@rt.callback_query(F.data.startswith("pag_"))
async def page_navigation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_page = data.get("current_page", 1)
    direction = callback.data.split("_")[1]

    async with async_session() as session:
        result = await session.execute(
            select(User).filter(User.user_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

    if not user:
        await callback.answer('Пользователь не найден')
        return

    total_items = len(user.received_packs)
    total_pages = get_total_pages(total_items, 1)

    if direction == "nex":
        current_page = current_page + 1 if current_page < total_pages else 1
        await callback.answer('❯')
    elif direction == "pre":
        current_page = current_page - 1 if current_page > 1 else total_pages
        await callback.answer('❮')

    await send_pack_page_artists(callback.message, user, current_page, state)
@rt.callback_query(F.data == "go_to_page_art_col")
async def request_page_number_art_col(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "<strong>Введите номер страницы, на которую хотите перейти:</strong>",
        reply_markup=kb.back_to_col_artists,
        parse_mode='HTML'
    )
    await state.set_state(UserState.enter_page_number_artists)
@rt.message(UserState.enter_page_number_artists)
async def go_to_page_art(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text.isdigit():
        page_number = int(message.text)

        async with async_session() as session:
            result = await session.execute(
                select(User).filter(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()

        if not user:
            await message.answer("Пользователь не найден.", reply_markup=kb.back_to_col_art)
            return

        total_items = len(user.received_packs)
        total_pages = get_total_pages(total_items, 1)

        if 1 <= page_number <= total_pages:
            await state.update_data(current_page=page_number)
            await send_pack_page_artists_2(message, user, page_number, state)
        else:
            await message.answer(f"<strong>⚠️ Введите число от 1 до {total_pages}.</strong>",
                                 reply_markup=kb.back_to_col_artists,
                                 parse_mode="HTML")
    else:
        await message.answer("<strong>⚠️ Неизвестная команда. Введите номер страницы.</strong>",
                             reply_markup=kb.back_to_col_artists,
                             parse_mode="HTML")


@rt.callback_query(F.data == 'subscription')
async def user_get_sub(callback: CallbackQuery, page: int = 1, state: FSMContext = None):
    user_id = callback.from_user.id
    await callback.answer('🎟 Подписка')
    if state:
        await state.clear()
    async with async_session() as session:
        user = await session.execute(select(User).where(User.user_id == user_id))
        user = user.scalars().first()

        discount_percentage = 0
        discount_gold = 0
        if user.active_promo_code:
            promo_info = await rq.get_promo_info(session, user.active_promo_code)

            if promo_info and promo_info.promo_type == "discount":
                if promo_info.subscription_type == 'basic':
                    discount_percentage = promo_info.promo_info_discount
                    discount_gold = 0
                elif promo_info.subscription_type == "gold":
                    discount_gold = promo_info.promo_info_discount
                    discount_percentage = 0
                elif promo_info.subscription_type == "basic+gold":
                    discount_gold = promo_info.promo_info_discount
                    discount_percentage = promo_info.promo_info_discount


    basic_premium_list = ['ARTISTS', 'SPOT', 'GOLD']
    total_pages = len(basic_premium_list)

    page = (page - 1) % total_pages + 1

    current_subscription = basic_premium_list[page - 1]
    if current_subscription == 'ARTISTS':
        base_price = 2000
        discounted_price = int(base_price * (1 - discount_percentage / 100))

        discount_expiration_info = (
            f" (промокод действует по {user.promo_expiration.strftime('%d.%m %H:%M')})"
            if user.active_promo_code and discount_percentage > 0 else ""
        )

        subscription_message = (
            f'Оформи подписку, чтобы получить доступ к функционалу бота.\n\n'
            f'<strong>Подписка: ARTISTS</strong>\n'
            f'<strong>Уровень подписки: BASIC ⚪️</strong>\n\n'
            f'<strong>Стоимость: {f"<s>{base_price}</s> " if discounted_price != base_price else ""}{discounted_price} руб./мес.</strong>'
            f'{discount_expiration_info}\n\n'  
            f'<strong>Методы оплаты:</strong>\n'
            f'<strong>Сбербанк:</strong> 2202208415908988\n'
            f'<strong>Telegram Wallet:</strong> @xxx\n\n'
            'ℹ️ Для оплаты переведите средства любым из указанных выше способов. '
            'Затем ОБЯЗАТЕЛЬНО отправьте чек об оплате '
            '<a href="https://t.me/flowfind_support">нам (кликабельно)</a> '
        )

        pagination_buttons = [
            InlineKeyboardButton(text="❮", callback_data=f"sub_page_c_{(page - 2) % total_pages + 1}"),
            InlineKeyboardButton(text=f"{current_subscription}", url='https://telegra.ph/Podpiska-ARTISTS-03-16'),
            InlineKeyboardButton(text="❯", callback_data=f"sub_page_c_{page % total_pages + 1}")
        ]
    elif current_subscription == 'SPOT':
        base_price = 2000
        discounted_price = int(base_price * (1 - discount_percentage / 100))

        discount_expiration_info = (
            f" (промокод действует по {user.promo_expiration.strftime('%d.%m %H:%M')})"
            if user.active_promo_code and discount_percentage > 0 else ""
        )

        subscription_message = (
            f'Оформи подписку, чтобы получить доступ к функционалу бота.\n\n'
            f'<strong>Подписка: SPOT</strong>\n'
            f'<strong>Уровень подписки: BASIC ⚪️</strong>\n\n'
            f'<strong>Стоимость: {f"<s>{base_price}</s> " if discounted_price != base_price else ""}{discounted_price} руб./мес.</strong>'
            f'{discount_expiration_info}\n\n'
            f'<strong>Методы оплаты:</strong>\n'
            f'<strong>Сбербанк:</strong> 2202208415908988\n'
            f'<strong>Telegram Wallet:</strong> @xxx\n\n'
            'ℹ️ Для оплаты переведите средства любым из указанных выше способов. '
            'Затем ОБЯЗАТЕЛЬНО отправьте чек об оплате '
            '<a href="https://t.me/flowfind_support">нам (кликабельно)</a> '
        )

        pagination_buttons = [
            InlineKeyboardButton(text="❮", callback_data=f"sub_page_c_{(page - 2) % total_pages + 1}"),
            InlineKeyboardButton(text=f"{current_subscription}", url='https://telegra.ph/Podpiska-SPOT-03-16'),
            InlineKeyboardButton(text="❯", callback_data=f"sub_page_c_{page % total_pages + 1}")
        ]
    else:
        base_price = 3000
        discounted_price = int(base_price * (1 - discount_gold / 100))

        discount_expiration_info = (
            f" (промокод действует по {user.promo_expiration.strftime('%d.%m %H:%M')})"
            if user.active_promo_code and discount_gold > 0 else ""
        )

        subscription_message = (
            f'Оформи подписку, чтобы получить доступ к функционалу бота.\n\n'
            f'<strong>Подписка: ARTISTS + SPOT</strong>\n'
            f'<strong>Уровень подписки: GOLD 🟡</strong>\n\n'
            f'<strong>Стоимость: {f"<s>{base_price}</s> " if discounted_price != base_price else ""}{discounted_price} руб./мес.</strong>'
            f'{discount_expiration_info}\n\n'
            f'<strong>Методы оплаты:</strong>\n'
            f'<strong>Сбербанк:</strong> 2202208415908988\n'
            f'<strong>Telegram Wallet:</strong> @xxx\n\n'
            'ℹ️ Для оплаты переведите средства любым из указанных выше способов. '
            'Затем ОБЯЗАТЕЛЬНО отправьте чек об оплате '
            '<a href="https://t.me/flowfind_support">нам (кликабельно)</a> '
        )

        pagination_buttons = [
            InlineKeyboardButton(text="❮", callback_data=f"sub_page_c_{(page - 2) % total_pages + 1}"),
            InlineKeyboardButton(text=f"{current_subscription}", url='https://telegra.ph/Podpiska-ARTISTS--SPOT-03-16'),
            InlineKeyboardButton(text="❯", callback_data=f"sub_page_c_{page % total_pages + 1}")
        ]
    async with async_session() as session:
        user = await session.execute(select(User).where(User.user_id == user_id))
        user = user.scalars().first()
        if user.free_subscription_used == 0:
            buttons = [
                pagination_buttons,
                [InlineKeyboardButton(text="🆓 Бесплатная", callback_data="free_subscription"),
                InlineKeyboardButton(text="🎟 О подписках", url='https://telegra.ph/Podpiski--FlowFind-03-16')],
                [InlineKeyboardButton(text='🔍 Ввести промокод', callback_data='promo_for_sub')],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
            ]
        else:
            buttons = [
                pagination_buttons,
                [InlineKeyboardButton(text="🎟 О подписках", url='https://telegra.ph/Podpiski--FlowFind-03-16')],
                [InlineKeyboardButton(text='🔍 Ввести промокод', callback_data='promo_for_sub')],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
            ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        f"{subscription_message}",
        parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True
    )
@rt.callback_query(F.data.startswith("sub_page_"))
async def change_subscription_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await user_get_sub(callback, page)


@rt.callback_query(F.data == 'subscription_p')
async def profile_p(callback: CallbackQuery, page: int = 1):
    user_id = callback.from_user.id
    await callback.answer('🎟 Подписка')
    async with async_session() as session:
        user = await session.execute(select(User).where(User.user_id == user_id))
        user = user.scalars().first()

        discount_percentage = 0
        discount_gold = 0
        if user.active_promo_code:
            promo_info = await rq.get_promo_info(session, user.active_promo_code)

            if promo_info and promo_info.promo_type == "discount":
                if promo_info.subscription_type == 'basic':
                    discount_percentage = promo_info.promo_info_discount
                    discount_gold = 0
                elif promo_info.subscription_type == "gold":
                    discount_gold = promo_info.promo_info_discount
                    discount_percentage = 0
                elif promo_info.subscription_type == "basic+gold":
                    discount_gold = promo_info.promo_info_discount
                    discount_percentage = promo_info.promo_info_discount

    basic_premium_list = ['ARTISTS', 'SPOT', 'GOLD']
    total_pages = len(basic_premium_list)

    page = (page - 1) % total_pages + 1

    current_subscription = basic_premium_list[page - 1]
    if current_subscription == 'ARTISTS':
        base_price = 2000
        discounted_price = int(base_price * (1 - discount_percentage / 100))

        discount_expiration_info = (
            f" (промокод действует по {user.promo_expiration.strftime('%d.%m %H:%M')})"
            if user.active_promo_code and discount_percentage > 0 else ""
        )

        subscription_message = (
            f'Оформи подписку, чтобы получить доступ к функционалу бота.\n\n'
            f'<strong>Подписка: ARTISTS</strong>\n'
            f'<strong>Уровень подписки: BASIC ⚪️</strong>\n\n'
            f'<strong>Стоимость: {f"<s>{base_price}</s> " if discounted_price != base_price else ""}{discounted_price} руб./мес.</strong>'
            f'{discount_expiration_info}\n\n'  
            f'<strong>Методы оплаты:</strong>\n'
            f'<strong>Сбербанк:</strong> 2202208415908988\n'
            f'<strong>Telegram Wallet:</strong> @xxx\n\n'
            'ℹ️ Для оплаты переведите средства любым из указанных выше способов. '
            'Затем ОБЯЗАТЕЛЬНО отправьте чек об оплате '
            '<a href="https://t.me/flowfind_support">нам (кликабельно)</a> '
        )

        pagination_buttons = [
            InlineKeyboardButton(text="❮", callback_data=f"sub_page_c_{(page - 2) % total_pages + 1}"),
            InlineKeyboardButton(text=f"{current_subscription}", url='https://telegra.ph/Podpiska-ARTISTS-03-16'),
            InlineKeyboardButton(text="❯", callback_data=f"sub_page_c_{page % total_pages + 1}")
        ]
    elif current_subscription == 'SPOT':
        base_price = 2000
        discounted_price = int(base_price * (1 - discount_percentage / 100))

        discount_expiration_info = (
            f" (промокод действует по {user.promo_expiration.strftime('%d.%m %H:%M')})"
            if user.active_promo_code and discount_percentage > 0 else ""
        )

        subscription_message = (
            f'Оформи подписку, чтобы получить доступ к функционалу бота.\n\n'
            f'<strong>Подписка: SPOT</strong>\n'
            f'<strong>Уровень подписки: BASIC ⚪️</strong>\n\n'
            f'<strong>Стоимость: {f"<s>{base_price}</s> " if discounted_price != base_price else ""}{discounted_price} руб./мес.</strong>'
            f'{discount_expiration_info}\n\n'
            f'<strong>Методы оплаты:</strong>\n'
            f'<strong>Сбербанк:</strong> 2202208415908988\n'
            f'<strong>Telegram Wallet:</strong> @xxx\n\n'
            'ℹ️ Для оплаты переведите средства любым из указанных выше способов. '
            'Затем ОБЯЗАТЕЛЬНО отправьте чек об оплате '
            '<a href="https://t.me/flowfind_support">нам (кликабельно)</a> '
        )

        pagination_buttons = [
            InlineKeyboardButton(text="❮", callback_data=f"sub_page_c_{(page - 2) % total_pages + 1}"),
            InlineKeyboardButton(text=f"{current_subscription}", url='https://telegra.ph/Podpiska-SPOT-03-16'),
            InlineKeyboardButton(text="❯", callback_data=f"sub_page_c_{page % total_pages + 1}")
        ]
    else:
        base_price = 3000
        discounted_price = int(base_price * (1 - discount_gold / 100))

        discount_expiration_info = (
            f" (промокод действует по {user.promo_expiration.strftime('%d.%m %H:%M')})"
            if user.active_promo_code and discount_gold > 0 else ""
        )

        subscription_message = (
            f'Оформи подписку, чтобы получить доступ к функционалу бота.\n\n'
            f'<strong>Подписка: ARTISTS + SPOT</strong>\n'
            f'<strong>Уровень подписки: GOLD 🟡</strong>\n\n'
            f'<strong>Стоимость: {f"<s>{base_price}</s> " if discounted_price != base_price else ""}{discounted_price} руб./мес.</strong>'
            f'{discount_expiration_info}\n\n'
            f'<strong>Методы оплаты:</strong>\n'
            f'<strong>Сбербанк:</strong> 2202208415908988\n'
            f'<strong>Telegram Wallet:</strong> @xxx\n\n'
            'ℹ️ Для оплаты переведите средства любым из указанных выше способов. '
            'Затем ОБЯЗАТЕЛЬНО отправьте чек об оплате '
            '<a href="https://t.me/flowfind_support">нам (кликабельно)</a> '
        )

        pagination_buttons = [
            InlineKeyboardButton(text="❮", callback_data=f"sub_page_c_{(page - 2) % total_pages + 1}"),
            InlineKeyboardButton(text=f"{current_subscription}", url='https://telegra.ph/Podpiska-ARTISTS--SPOT-03-16'),
            InlineKeyboardButton(text="❯", callback_data=f"sub_page_c_{page % total_pages + 1}")
        ]
    async with async_session() as session:
        user = await session.execute(select(User).where(User.user_id == user_id))
        user = user.scalars().first()
        if user.free_subscription_used == 0:
            buttons = [
                pagination_buttons,
                [InlineKeyboardButton(text="🆓 Бесплатная", callback_data="free_subscription"),
                 InlineKeyboardButton(text="🎟 О подписках", url='https://telegra.ph/Podpiski--FlowFind-03-16')],
                [InlineKeyboardButton(text='🔍 Ввести промокод', callback_data='promo_for_sub')],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back_p")]
            ]
        else:
            buttons = [
                pagination_buttons,
                [InlineKeyboardButton(text="🎟 О подписках", url='https://telegra.ph/Podpiski--FlowFind-03-16')],
                [InlineKeyboardButton(text='🔍 Ввести промокод', callback_data='promo_for_sub')],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back_p")]
            ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        f"{subscription_message}",
        parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True
    )
@rt.callback_query(F.data.startswith("sub_page_p_"))
async def change_subscription_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await profile_p(callback, page)

@rt.callback_query(F.data == 'subscription_c')
async def profile_c(callback: CallbackQuery, page: int = 1):
    user_id = callback.from_user.id
    await callback.answer('🎟 Подписка')
    async with async_session() as session:
        user = await session.execute(select(User).where(User.user_id == user_id))
        user = user.scalars().first()

        discount_percentage = 0
        discount_gold = 0
        if user.active_promo_code:
            promo_info = await rq.get_promo_info(session, user.active_promo_code)

            if promo_info and promo_info.promo_type == "discount":
                if promo_info.subscription_type == 'basic':
                    discount_percentage = promo_info.promo_info_discount
                    discount_gold = 0
                elif promo_info.subscription_type == "gold":
                    discount_gold = promo_info.promo_info_discount
                    discount_percentage = 0
                elif promo_info.subscription_type == "basic+gold":
                    discount_gold = promo_info.promo_info_discount
                    discount_percentage = promo_info.promo_info_discount

    basic_premium_list = ['ARTISTS', 'SPOT', 'GOLD']
    total_pages = len(basic_premium_list)

    page = (page - 1) % total_pages + 1

    current_subscription = basic_premium_list[page - 1]
    if current_subscription == 'ARTISTS':
        base_price = 2000
        discounted_price = int(base_price * (1 - discount_percentage / 100))

        discount_expiration_info = (
            f" (промокод действует по {user.promo_expiration.strftime('%d.%m %H:%M')})"
            if user.active_promo_code and discount_percentage > 0 else ""
        )

        subscription_message = (
            f'Оформи подписку, чтобы получить доступ к функционалу бота.\n\n'
            f'<strong>Подписка: ARTISTS</strong>\n'
            f'<strong>Уровень подписки: BASIC ⚪️</strong>\n\n'
            f'<strong>Стоимость: {f"<s>{base_price}</s> " if discounted_price != base_price else ""}{discounted_price} руб./мес.</strong>'
            f'{discount_expiration_info}\n\n'  
            f'<strong>Методы оплаты:</strong>\n'
            f'<strong>Сбербанк:</strong> 2202208415908988\n'
            f'<strong>Telegram Wallet:</strong> @xxx\n\n'
            'ℹ️ Для оплаты переведите средства любым из указанных выше способов. '
            'Затем ОБЯЗАТЕЛЬНО отправьте чек об оплате '
            '<a href="https://t.me/flowfind_support">нам (кликабельно)</a> '
        )

        pagination_buttons = [
            InlineKeyboardButton(text="❮", callback_data=f"sub_page_c_{(page - 2) % total_pages + 1}"),
            InlineKeyboardButton(text=f"{current_subscription}", url='https://telegra.ph/Podpiska-ARTISTS-03-16'),
            InlineKeyboardButton(text="❯", callback_data=f"sub_page_c_{page % total_pages + 1}")
        ]
    elif current_subscription == 'SPOT':
        base_price = 2000
        discounted_price = int(base_price * (1 - discount_percentage / 100))

        discount_expiration_info = (
            f" (промокод действует по {user.promo_expiration.strftime('%d.%m %H:%M')})"
            if user.active_promo_code and discount_percentage > 0 else ""
        )

        subscription_message = (
            f'Оформи подписку, чтобы получить доступ к функционалу бота.\n\n'
            f'<strong>Подписка: SPOT</strong>\n'
            f'<strong>Уровень подписки: BASIC ⚪️</strong>\n\n'
            f'<strong>Стоимость: {f"<s>{base_price}</s> " if discounted_price != base_price else ""}{discounted_price} руб./мес.</strong>'
            f'{discount_expiration_info}\n\n'
            f'<strong>Методы оплаты:</strong>\n'
            f'<strong>Сбербанк:</strong> 2202208415908988\n'
            f'<strong>Telegram Wallet:</strong> @xxx\n\n'
            'ℹ️ Для оплаты переведите средства любым из указанных выше способов. '
            'Затем ОБЯЗАТЕЛЬНО отправьте чек об оплате '
            '<a href="https://t.me/flowfind_support">нам (кликабельно)</a> '
        )

        pagination_buttons = [
            InlineKeyboardButton(text="❮", callback_data=f"sub_page_c_{(page - 2) % total_pages + 1}"),
            InlineKeyboardButton(text=f"{current_subscription}", url='https://telegra.ph/Podpiska-SPOT-03-16'),
            InlineKeyboardButton(text="❯", callback_data=f"sub_page_c_{page % total_pages + 1}")
        ]
    else:
        base_price = 3000
        discounted_price = int(base_price * (1 - discount_gold / 100))

        discount_expiration_info = (
            f" (промокод действует по {user.promo_expiration.strftime('%d.%m %H:%M')})"
            if user.active_promo_code and discount_gold > 0 else ""
        )

        subscription_message = (
            f'Оформи подписку, чтобы получить доступ к функционалу бота.\n\n'
            f'<strong>Подписка: ARTISTS + SPOT</strong>\n'
            f'<strong>Уровень подписки: GOLD 🟡</strong>\n\n'
            f'<strong>Стоимость: {f"<s>{base_price}</s> " if discounted_price != base_price else ""}{discounted_price} руб./мес.</strong>'
            f'{discount_expiration_info}\n\n'
            f'<strong>Методы оплаты:</strong>\n'
            f'<strong>Сбербанк:</strong> 2202208415908988\n'
            f'<strong>Telegram Wallet:</strong> @xxx\n\n'
            'ℹ️ Для оплаты переведите средства любым из указанных выше способов. '
            'Затем ОБЯЗАТЕЛЬНО отправьте чек об оплате '
            '<a href="https://t.me/flowfind_support">нам (кликабельно)</a> '
        )

        pagination_buttons = [
            InlineKeyboardButton(text="❮", callback_data=f"sub_page_c_{(page - 2) % total_pages + 1}"),
            InlineKeyboardButton(text=f"{current_subscription}", url='https://telegra.ph/Podpiska-ARTISTS--SPOT-03-16'),
            InlineKeyboardButton(text="❯", callback_data=f"sub_page_c_{page % total_pages + 1}")
        ]

    async with async_session() as session:
        user = await session.execute(select(User).where(User.user_id == user_id))
        user = user.scalars().first()
        if user.free_subscription_used == 0:
            buttons = [
                pagination_buttons,
                [InlineKeyboardButton(text="🆓 Бесплатная", callback_data="free_subscription"),
                 InlineKeyboardButton(text="🎟 О подписках", url='https://telegra.ph/Podpiski--FlowFind-03-16')],
                [InlineKeyboardButton(text='🔍 Ввести промокод', callback_data='promo_for_sub')],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back_c")]
            ]
        else:
            buttons = [
                pagination_buttons,
                [InlineKeyboardButton(text="🎟 О подписках", url='https://telegra.ph/Podpiski--FlowFind-03-16')],
                [InlineKeyboardButton(text='🔍 Ввести промокод', callback_data='promo_for_sub')],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back_c")]
            ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        f"{subscription_message}",
        parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True
    )
@rt.callback_query(F.data.startswith("sub_page_c_"))
async def change_subscription_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await profile_c(callback, page)
##

@rt.message(F.text == '👥 Поддержка')
async def main_support(message: Message):
    await message.answer('<strong>🫂 По любым вопросам ждем вас: @flowfind_support</strong>',
                         parse_mode="HTML",
                         reply_markup=kb.backtomenu)


@rt.message(Command("restart"))
async def restart(message: Message):
    await cmd_start(message)

@rt.message(Command("get_profile"))
async def restart(message: Message):
    await cmd_start(message)


async def is_subscribed_to_channels(user_id: int, channel_1: str, bot: Bot) -> bool:
    try:
        chat_member_1 = await bot.get_chat_member(channel_1, user_id)

        print(f"User {user_id} status in {channel_1}: {chat_member_1.status}")

        statuses = ["member", "administrator", "creator"]
        return chat_member_1.status in statuses
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

@rt.callback_query(F.data=='free_subscription')
async def process_free_subscription(callback: CallbackQuery):
    await callback.answer('🆓 Бесплатная подписка')
    await callback.message.edit_text('<strong>🫷🏻Бесплатную подписку <a href="https://telegra.ph/Podpiska-ARTISTS--SPOT-03-16">GOLD</a> можно активировать только 1 раз! </strong>\n'
                                     'Она действует 3 дня и не подлежит приостановке.\n\n'
                                     '<strong>Условия получения:</strong>\n'
                                     '1. Подписаться на канал @formantsales\n'
                                     '2. Нажать кнопку <strong>«Активировать»</strong>\n\n'
                                     'После завершения пробного периода доступ будет заблокирован.',
                                     parse_mode="HTML",reply_markup=kb.get_free_subscription_button_completed(), disable_web_page_preview=True)
@rt.callback_query(F.data=='free_subscription_p')
async def process_free_subscription_p(callback: CallbackQuery):
    await callback.answer('🆓 Бесплатная подписка')
    await callback.message.edit_text('<strong>🫷🏻Бесплатную подписку <a href="https://telegra.ph/Podpiska-ARTISTS--SPOT-03-16">GOLD</a> можно активировать только 1 раз! </strong>\n'
                                     'Она действует 3 дня и не подлежит приостановке.\n\n'
                                     '<strong>Условия получения:</strong>\n'
                                     '1. Подписаться на канал @formantsales\n'
                                     '2. Нажать кнопку <strong>«Активировать»</strong>\n\n'
                                     'После завершения пробного периода доступ будет заблокирован.',
                                     parse_mode="HTML", reply_markup=kb.get_free_subscription_button_completed_p(), disable_web_page_preview=True)
@rt.callback_query(F.data=='free_subscription_c')
async def process_free_subscription(callback: CallbackQuery):
    await callback.message.edit_text('<strong>🫷🏻Бесплатную подписку <a href="https://telegra.ph/Podpiska-ARTISTS--SPOT-03-16">GOLD</a> можно активировать только 1 раз! </strong>\n'
                                     'Она действует 3 дня и не подлежит приостановке.\n\n'
                                     '<strong>Условия получения:</strong>\n'
                                     '1. Подписаться на канал @formantsales\n'
                                     '2. Нажать кнопку <strong>«Активировать»</strong>\n\n'
                                     'После завершения пробного периода доступ будет заблокирован.',
                                     parse_mode="HTML", reply_markup=kb.get_free_subscription_button_completed_c(), disable_web_page_preview=True)
@rt.callback_query(F.data=='free_subscription_completed')
async def process_free_subscription(callback: CallbackQuery):
    if callback.data == "free_subscription_completed":
        user_id = callback.from_user.id
        channel_1 = "@formantsales"

    if await is_subscribed_to_channels(user_id, channel_1, callback.message.bot):
        async with async_session() as session:
            user = await session.execute(select(User).where(User.user_id == user_id))
            user = user.scalars().first()
            if user.paid_sub == 1 and user.subscription > 0:
                await callback.answer("Недоступно при активной подписке", show_alert=True)
                return
            if user and not user.free_subscription_used and user.subscription == 0:
                now = datetime.now(pytz.timezone('Europe/Moscow'))
                user.subscription += 3
                user.subscription_start = now
                user.free_subscription_used = True
                user.subscription_type = 'gold'

                session.add(user)
                await session.commit()

                await callback.answer("Поздравляем! Вы получили бесплатную подписку на 3 дня!")

                user_id = callback.from_user.id
                async with async_session() as session:
                    result = await session.execute(select(User).filter(User.user_id == user_id))
                    user = result.scalar_one_or_none()

                    if user:
                        remaining_days = user.subscription

                        await profile(callback)
                    else:
                        await callback.answer(
                            f"Пользователь с ID {user_id} не найден в базе данных. Введите команду /get_profile")
            else:
                await callback.answer("Вы уже активировали бесплатную подписку", show_alert=True)
    else:
        await callback.answer(
            'Сначала выполните условия', show_alert=True)
@rt.callback_query(F.data=='free_subscription_completed_pr')
async def process_free_subscription_pr(callback: CallbackQuery):
    if callback.data == "free_subscription_completed_pr":
        user_id = callback.from_user.id
        channel_1 = "@formantsales"

    if await is_subscribed_to_channels(user_id, channel_1, callback.message.bot):
        async with async_session() as session:
            user = await session.execute(select(User).where(User.user_id == user_id))
            user = user.scalars().first()
            if user.paid_sub == 1 and user.subscription > 0:
                await callback.answer("Недоступно при активной подписке", show_alert=True)
                return
            if user and not user.free_subscription_used and user.subscription == 0:
                now = datetime.now(pytz.timezone('Europe/Moscow'))
                user.subscription += 3
                user.subscription_start = now
                user.free_subscription_used = True
                user.subscription_type = 'gold'

                session.add(user)
                await session.commit()

                await callback.answer("Поздравляем! Вы получили бесплатную подписку на 3 дня!")

                user_id = callback.from_user.id
                async with async_session() as session:
                    result = await session.execute(select(User).filter(User.user_id == user_id))
                    user = result.scalar_one_or_none()

                    if user:
                        remaining_days = user.subscription


                        await profile(callback)
                    else:
                        await callback.answer(
                            f"Пользователь с ID {user_id} не найден в базе данных. Введите команду /get_profile")
            else:
                await callback.answer("Вы уже активировали бесплатную подписку", show_alert=True)
    else:
        await callback.answer(
            'Сначала выполните условия', show_alert=True)
@rt.callback_query(F.data=='free_subscription_completed_co')
async def process_free_subscription_co(callback: CallbackQuery):
    if callback.data == "free_subscription_completed_co":
        user_id = callback.from_user.id
        channel_1 = "@formantsales"

        if await is_subscribed_to_channels(user_id, channel_1, callback.message.bot):
            async with async_session() as session:
                user = await session.execute(select(User).where(User.user_id == user_id))
                user = user.scalars().first()
                if user.paid_sub == 1 and user.subscription > 0:
                    await callback.answer("Недоступно при активной подписке", show_alert=True)
                    return
                if user and not user.free_subscription_used and user.subscription == 0:
                    now = datetime.now(pytz.timezone('Europe/Moscow'))
                    user.subscription += 3
                    user.subscription_start = now
                    user.free_subscription_used = True
                    user.subscription_type = 'gold'

                    session.add(user)
                    await session.commit()

                    await callback.answer("Поздравляем! Вы получили бесплатную подписку на 3 дня!")

                    user_id = callback.from_user.id
                    async with async_session() as session:
                        result = await session.execute(select(User).filter(User.user_id == user_id))
                        user = result.scalar_one_or_none()

                        if user:
                            remaining_days = user.subscription

                            await profile(callback)
                        else:
                            await callback.answer(
                                f"Пользователь с ID {user_id} не найден в базе данных. Введите команду /get_profile")
                else:
                    await callback.answer("<strong>🫷🏻Бесплатную подписку «GOLD» можно активировать только 1 раз!</strong> Она действует 3 дня и не подлежит приостановке.",show_alert=True)
        else:
            await callback.answer(
                'Сначала выполните условия', show_alert=True)

