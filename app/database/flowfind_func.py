from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.future import select
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import re
import logging

from config import ADMIN_ID
import app.keyboards as kb
from app.database.models import ArtistPack, User, SpotPack
from app.database.requests import async_session

rt = Router()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_admin(user_id):
    return user_id in ADMIN_ID

class FlowFindStates(StatesGroup):
    waiting_for_usernames = State()
    confirm_submission = State()
    editing_page = State()
    enter_page_number = State()
class SpotStates(StatesGroup):
    waiting_for_usernames = State()
    confirm_submission = State()
    editing_page = State()
    enter_page_number = State()


@rt.callback_query(F.data == "add")
async def start_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FlowFindStates.waiting_for_usernames)
    await callback.answer('📲 ADD')
    await callback.message.edit_text(
        "<strong>Введите 20 username-ов артистов, каждый с новой строки:</strong>",
        reply_markup=kb.adm_back, parse_mode='HTML'
    )

valid_username_pattern = re.compile(r'^[a-zA-Z0-9._-]+$')

@rt.message(FlowFindStates.waiting_for_usernames)
async def process_usernames(message: Message, state: FSMContext):
    usernames = message.text.strip().split("\n")

    if len(usernames) != 20:
        error_buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='↩️ Назад', callback_data='adm_back')]
        ])
        await message.answer(
            f"<strong>⚠️ Количество строк — {len(usernames)}</strong>",
            reply_markup=error_buttons, parse_mode='HTML'
        )
        return

    invalid_usernames = [username for username in usernames if not valid_username_pattern.match(username.strip())]

    if invalid_usernames:
        await message.answer(
            f"<strong>⚠️ Невалидные username-ы: {', '.join(invalid_usernames)}</strong>\n"
            "Пожалуйста, убедитесь, что каждый username состоит только из букв, цифр, точек и подчеркиваний",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    duplicate_usernames = [username for username in usernames if usernames.count(username) > 1]
    if duplicate_usernames:
        await message.answer(
            f"<strong>⚠️ В паке повторяются юзернеймы: {', '.join(set(duplicate_usernames))}</strong>\n"
            "Пожалуйста, удалите повторяющиеся юзернеймы и попробуйте снова.",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    async with async_session() as session:
        result = await session.execute(select(ArtistPack.usernames))
        existing_usernames = result.scalars().all()

    existing_usernames = [username.strip() for usernames in existing_usernames for username in usernames.split(",")]

    duplicate_usernames_in_db = [username for username in usernames if username.strip() in existing_usernames]

    if duplicate_usernames_in_db:
        await message.answer(
            f"<strong>⚠️ Артист с юзернеймом(ами) {', '.join(duplicate_usernames_in_db)} уже есть в базе данных, повторите попытку</strong>",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    formatted_usernames = [
        f"**{i + 1}.** {username.strip().replace('_', '\\_')} ([ссылка](https://www.instagram.com/{username.strip()}/))"
        for i, username in enumerate(usernames)
    ]

    formatted_message = "\n".join(formatted_usernames)
    await state.update_data(usernames=usernames)

    await state.set_state(FlowFindStates.confirm_submission)
    await message.answer(
        f"**Подтвердите размещение!**\n\n{formatted_message}",
        parse_mode="Markdown",
        reply_markup=kb.confirmation_buttons, disable_web_page_preview=True
    )

@rt.callback_query(F.data == "confirm")
async def confirm_submission(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    usernames = data.get("usernames", [])

    async with async_session() as session:
        pack = ArtistPack(usernames=",".join(usernames))
        session.add(pack)
        await session.commit()
    await callback.answer('✅ Подтвердить')
    await callback.message.edit_text(
        "<strong>✅ Пак успешно добавлен в рассылку</strong>",
        reply_markup=kb.adm_start, parse_mode='HTML'
    )
    await state.clear()

@rt.callback_query(F.data == "edit")
async def edit_submission(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FlowFindStates.waiting_for_usernames)
    await callback.answer('🔧 Изменить')
    await callback.message.edit_text(
        "<strong>Введите 20 username-ов артистов, каждый с новой строки:</strong>",
        reply_markup=kb.adm_back, parse_mode='HTML'
    )

@rt.callback_query(F.data == "decline")
async def decline_submission(callback: CallbackQuery, state: FSMContext):
    await callback.answer('🗑 Отклонить')
    await callback.message.edit_text(
        "<strong>🗑 Размещение отклонено.</strong>",
        reply_markup=kb.adm_start, parse_mode='HTML'
    )
    await state.clear()



@rt.callback_query(F.data == "database")
async def show_database(callback: CallbackQuery, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(select(ArtistPack).order_by(ArtistPack.id))
        packs = result.scalars().all()
    await callback.answer('📁 DATABASE')
    if not packs:
        await callback.message.edit_text(
            "<strong>База данных пуста</strong>",
            reply_markup=kb.adm_back,
            parse_mode='HTML'
        )
        return

    await state.update_data(current_page=1)
    await send_pack_page(callback.message, packs, 1)

async def send_pack_page(message: Message, packs: list, page: int):
    pack = packs[page - 1]
    usernames = pack.usernames.split(",")

    formatted_usernames = [
        f"**{i + 1}.** {username.strip().replace('_', '\\_')} ([ссылка](https://www.instagram.com/{username.strip()}/))"
        for i, username in enumerate(usernames)
    ]

    formatted_message = "\n".join(formatted_usernames)
    total_pages = len(packs)

    try:
        await message.edit_text(
            f"{formatted_message}",
            parse_mode="Markdown",
            reply_markup=kb.database_navigation(page, total_pages), disable_web_page_preview=True
        )
    except Exception:
        await message.answer(
            f"{formatted_message}",
            parse_mode="Markdown",
            reply_markup=kb.database_navigation(page, total_pages), disable_web_page_preview=True
        )

@rt.callback_query(F.data.startswith("page_"))
async def change_page(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_page = data.get("current_page", 1)

    direction = callback.data.split("_")[1]
    async with async_session() as session:
        result = await session.execute(select(ArtistPack).order_by(ArtistPack.id))
        packs = result.scalars().all()

    if direction == "next" and current_page < len(packs):
        current_page += 1
        await callback.answer('❯')
    elif direction == "prev" and current_page > 1:
        await callback.answer('❮')
        current_page -= 1
    else:
        await callback.answer('Не выходи за рамки')
        return

    await state.update_data(current_page=current_page)
    await send_pack_page(callback.message, packs, current_page)

@rt.callback_query(F.data == "go_to_page")
async def request_page_number(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "<strong>Введите номер страницы или юзернейм, на которую хотите перейти:</strong>",
        reply_markup=kb.adm_back,
        parse_mode='HTML'
    )
    await state.set_state(FlowFindStates.enter_page_number)

@rt.message(FlowFindStates.enter_page_number)
async def go_to_page(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    async with async_session() as session:
        if message.text.isdigit():
            page_number = int(message.text)
            result = await session.execute(select(ArtistPack).order_by(ArtistPack.id))
            packs = result.scalars().all()
            total_pages = len(packs)

            if 1 <= page_number <= total_pages:
                await state.update_data(current_page=page_number)
                await send_pack_page(message, packs, page_number)
            else:
                await message.answer(f"<strong>⚠️ Введите число от 1 до {total_pages}</strong>",
                                     reply_markup=kb.adm_back,
                                     parse_mode="HTML")
        else:
            result = await session.execute(select(ArtistPack).order_by(ArtistPack.id))
            packs = result.scalars().all()

            pack = next((p for p in packs if message.text.lower() in p.usernames.lower()), None)

            if pack:
                page_number = packs.index(pack) + 1  
                await state.update_data(current_page=page_number)
                await send_pack_page(message, packs, page_number)
            else:
                await message.answer("⚠️ Пак с таким юзернеймом не найден.",
                                     reply_markup=kb.adm_back,
                                     parse_mode="HTML")

@rt.callback_query(F.data == "delete_pack")
async def delete_pack(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_page = data.get("current_page", 1)
    await callback.answer('🗑 Удалить')
    async with async_session() as session:
        result = await session.execute(select(ArtistPack).order_by(ArtistPack.id))
        packs = result.scalars().all()

        if not packs:
            await callback.message.edit_text(
                "<strong>База данных пуста</strong>",
                reply_markup=kb.adm_back, parse_mode='HTML'
            )
            return

        pack_to_delete = packs[current_page - 1]
        pack_id = pack_to_delete.id

        users = await session.execute(select(User))
        users = users.scalars().all()
        for user in users:
            if pack_id in user.received_packs:
                user.received_packs.remove(pack_id)

        await session.delete(pack_to_delete)
        await session.commit()

    await callback.message.edit_text(
        f"<strong>🗑 Пак №{pack_to_delete.id} успешно удалён</strong>",
        reply_markup=kb.adm_back, parse_mode='HTML'
    )

@rt.callback_query(F.data == "edit_pack")
async def edit_pack(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_page = data.get("current_page", 1)
    async with async_session() as session:
        result = await session.execute(select(ArtistPack).order_by(ArtistPack.id))
        packs = result.scalars().all()

        if current_page > len(packs):
            await callback.message.edit_text(
                "<strong>Ошибка: Пак не найден. Попробуйте снова</strong>",
                reply_markup=kb.adm_back, parse_mode='HTML'
            )
            return

        pack_to_edit = packs[current_page - 1]

        await state.update_data(pack_to_edit_id=pack_to_edit.id)

    await state.set_state(FlowFindStates.editing_page)
    await callback.answer('🔧 Изменить')
    await callback.message.edit_text(
        "<strong>Введите новый список username-ов для текущего пака (20 строк):</strong>",
        reply_markup=kb.adm_back, parse_mode='HTML'
    )

@rt.message(FlowFindStates.editing_page)
async def process_edit_pack(message: Message, state: FSMContext):
    usernames = [u.strip().lower() for u in message.text.strip().splitlines()]

    if len(usernames) != 20:
        await message.answer(
            f"<strong>⚠️ Количество строк — {len(usernames)}. Требуется ровно 20. Попробуйте снова:</strong>",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    invalid_usernames = [u for u in usernames if not valid_username_pattern.match(u)]
    if invalid_usernames:
        await message.answer(
            f"<strong>⚠️ Невалидные username-ы: {', '.join(invalid_usernames)}</strong>\n"
            "Пожалуйста, убедитесь, что каждый username состоит только из букв, цифр, точек и подчеркиваний",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    duplicate_usernames = [u for u in usernames if usernames.count(u) > 1]
    if duplicate_usernames:
        await message.answer(
            f"<strong>⚠️ В паке повторяются юзернеймы: {', '.join(set(duplicate_usernames))}</strong>\n"
            "Пожалуйста, удалите повторяющиеся юзернеймы и попробуйте снова.",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    data = await state.get_data()
    current_page = data.get("current_page", 1)

    async with async_session() as session:
        result = await session.execute(select(ArtistPack).order_by(ArtistPack.id))
        packs = result.scalars().all()

        if current_page > len(packs):
            await message.answer(
                "<strong>Ошибка: Пак не найден. Попробуйте снова</strong>",
                reply_markup=kb.adm_back, parse_mode='HTML'
            )
            return

        pack_to_edit = packs[current_page - 1]

        result = await session.execute(
            select(ArtistPack.usernames).where(ArtistPack.id != pack_to_edit.id)
        )
        other_usernames_raw = result.scalars().all()
        existing_usernames = {
            u.strip().lower()
            for usernames in other_usernames_raw
            for u in usernames.split(",")
        }

        duplicate_usernames_in_db = [u for u in usernames if u in existing_usernames]
        if duplicate_usernames_in_db:
            await message.answer(
                f"<strong>⚠️ Артист с юзернеймом(ами) {', '.join(duplicate_usernames_in_db)} уже есть в других паках. Повторите попытку</strong>",
                reply_markup=kb.adm_back, parse_mode='HTML'
            )
            return

        try:
            pack_to_edit.usernames = ",".join(usernames)

            session.add(pack_to_edit)

            await message.answer(
                f"<strong>✅ Пак №{pack_to_edit.id} успешно обновлён</strong>",
                reply_markup=kb.adm_start, parse_mode='HTML'
            )
            await state.clear()

        except Exception as e:
            logger.error(f"Ошибка при обновлении пака: {e}")
            await message.answer(
                "❌ Произошла ошибка при обновлении пака. Попробуйте снова",
                reply_markup=kb.adm_back
            )

        await session.commit()


@rt.callback_query(F.data == "add_spot")
async def start_add_spot(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SpotStates.waiting_for_usernames)
    await callback.answer('📲 ADD')
    await callback.message.edit_text(
        "<strong>Введите 5 username-ов спотов, каждый с новой строки:</strong>",
        reply_markup=kb.adm_back, parse_mode='HTML'
    )

@rt.message(SpotStates.waiting_for_usernames)
async def process_usernames_spot(message: Message, state: FSMContext):
    usernames = message.text.strip().split("\n")

    if len(usernames) != 5:
        error_buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='↩️ Назад', callback_data='adm_back')]
        ])
        await message.answer(
            f"<strong>⚠️ Количество строк — {len(usernames)}</strong>",
            reply_markup=error_buttons, parse_mode='HTML'
        )
        return

    invalid_usernames = [username for username in usernames if not valid_username_pattern.match(username.strip())]

    if invalid_usernames:
        await message.answer(
            f"<strong>⚠️ Невалидные username-ы: {', '.join(invalid_usernames)}</strong>\n"
            "Пожалуйста, убедитесь, что каждый username состоит только из букв, цифр, точек и подчеркиваний",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    duplicate_usernames = [username for username in usernames if usernames.count(username) > 1]
    if duplicate_usernames:
        await message.answer(
            f"<strong>⚠️ В паке повторяются юзернеймы: {', '.join(set(duplicate_usernames))}</strong>\n"
            "Пожалуйста, удалите повторяющиеся юзернеймы и попробуйте снова.",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    async with async_session() as session:
        result = await session.execute(select(SpotPack.usernames))
        existing_usernames = result.scalars().all()

    existing_usernames = [username.strip() for usernames in existing_usernames for username in usernames.split(",")]

    duplicate_usernames_in_db = [username for username in usernames if username.strip() in existing_usernames]

    if duplicate_usernames_in_db:
        await message.answer(
            f"<strong>⚠️ Спот с юзернеймом(ами) {', '.join(duplicate_usernames_in_db)} уже есть в базе данных, повторите попытку</strong>",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    formatted_usernames = [
        f"**{i + 1}.** {username.strip().replace('_', '\\_')} ([ссылка](https://www.instagram.com/{username.strip()}/))"
        for i, username in enumerate(usernames)
    ]

    formatted_message = "\n".join(formatted_usernames)
    await state.update_data(usernames=usernames)

    await state.set_state(SpotStates.confirm_submission)
    await message.answer(
        f"**Подтвердите размещение!**\n\n{formatted_message}",
        parse_mode="Markdown",
        reply_markup=kb.confirmation_buttons_spot, disable_web_page_preview=True
    )

@rt.callback_query(F.data == "confirm_spot")
async def confirm_submission_spot(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    usernames = data.get("usernames", [])

    async with async_session() as session:
        pack = SpotPack(usernames=",".join(usernames))
        session.add(pack)
        await session.commit()
    await callback.answer('✅ Подтвердить')
    await callback.message.edit_text(
        "<strong>✅ Пак успешно добавлен в рассылку</strong>",
        reply_markup=kb.adm_start, parse_mode='HTML'
    )
    await state.clear()

@rt.callback_query(F.data == "edit_spot")
async def edit_submission_spot(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SpotStates.waiting_for_usernames)
    await callback.answer('🔧 Изменить')
    await callback.message.edit_text(
        "<strong>Введите 5 username-ов Спотов, каждый с новой строки:</strong>",
        reply_markup=kb.adm_back, parse_mode='HTML'
    )

@rt.callback_query(F.data == "decline_spot")
async def decline_submission_spot(callback: CallbackQuery, state: FSMContext):
    await callback.answer('🗑 Отклонить')
    await callback.message.edit_text(
        "<strong>🗑 Размещение отклонено.</strong>",
        reply_markup=kb.adm_start, parse_mode='HTML'
    )
    await state.clear()



@rt.callback_query(F.data == "database_spot")
async def show_database_spot(callback: CallbackQuery, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(select(SpotPack).order_by(SpotPack.id))
        packs = result.scalars().all()
    await callback.answer('📁 DATABASE')
    if not packs:
        await callback.message.edit_text(
            "<strong>База данных пуста</strong>",
            reply_markup=kb.adm_back,
            parse_mode='HTML'
        )
        return

    await state.update_data(current_page=1)
    await send_pack_page_spot(callback.message, packs, 1)

async def send_pack_page_spot(message: Message, packs: list, page: int):
    pack = packs[page - 1]
    usernames = pack.usernames.split(",")

    formatted_usernames = [
        f"**{i + 1}.** {username.strip().replace('_', '\\_')} ([ссылка](https://www.instagram.com/{username.strip()}/))"
        for i, username in enumerate(usernames)
    ]

    formatted_message = "\n".join(formatted_usernames)
    total_pages = len(packs)

    try:
        await message.edit_text(
            f"{formatted_message}",
            parse_mode="Markdown",
            reply_markup=kb.database_navigation_spot(page, total_pages), disable_web_page_preview=True
        )
    except Exception:
        await message.answer(
            f"{formatted_message}",
            parse_mode="Markdown",
            reply_markup=kb.database_navigation_spot(page, total_pages), disable_web_page_preview=True
        )

@rt.callback_query(F.data.startswith("pagespot_"))
async def change_page_spot(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_page = data.get("current_page", 1)

    direction = callback.data.split("_")[1]
    async with async_session() as session:
        result = await session.execute(select(SpotPack).order_by(SpotPack.id))
        packs = result.scalars().all()

    if direction == "next" and current_page < len(packs):
        current_page += 1
        await callback.answer('❯')
    elif direction == "prev" and current_page > 1:
        await callback.answer('❮')
        current_page -= 1
    else:
        await callback.answer('Не выходи за рамки')
        return

    await state.update_data(current_page=current_page)
    await send_pack_page_spot(callback.message, packs, current_page)

@rt.callback_query(F.data == "go_to_page_spot")
async def request_page_number_spot(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "<strong>Введите номер страницы или юзернейм, на которую хотите перейти:</strong>",
        reply_markup=kb.adm_back,
        parse_mode='HTML'
    )
    await state.set_state(SpotStates.enter_page_number)

@rt.message(SpotStates.enter_page_number)
async def go_to_page_spot(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    async with async_session() as session:
        if message.text.isdigit():
            page_number = int(message.text)
            result = await session.execute(select(SpotPack).order_by(SpotPack.id))
            packs = result.scalars().all()
            total_pages = len(packs)

            if 1 <= page_number <= total_pages:
                await state.update_data(current_page=page_number)
                await send_pack_page_spot(message, packs, page_number)
            else:
                await message.answer(f"<strong>⚠️ Введите число от 1 до {total_pages}</strong>",
                                     reply_markup=kb.adm_back,
                                     parse_mode="HTML")
        else:
            result = await session.execute(select(SpotPack).order_by(SpotPack.id))
            packs = result.scalars().all()

            pack = next((p for p in packs if message.text.lower() in p.usernames.lower()), None)

            if pack:
                page_number = packs.index(pack) + 1  
                await state.update_data(current_page=page_number)
                await send_pack_page_spot(message, packs, page_number)
            else:
                await message.answer("⚠️ Пак с таким юзернеймом не найден.",
                                     reply_markup=kb.adm_back,
                                     parse_mode="HTML")


@rt.callback_query(F.data == "delete_pack_spot")
async def delete_pack_spot(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_page = data.get("current_page", 1)
    await callback.answer('🗑 Удалить')
    async with async_session() as session:
        result = await session.execute(select(SpotPack).order_by(SpotPack.id))
        packs = result.scalars().all()

        if not packs:
            await callback.message.edit_text(
                "<strong>База данных пуста</strong>",
                reply_markup=kb.adm_back, parse_mode='HTML'
            )
            return

        pack_to_delete = packs[current_page - 1]
        pack_id = pack_to_delete.id

        users = await session.execute(select(User))
        users = users.scalars().all()
        for user in users:
            if pack_id in user.received_packs_spot:
                user.received_packs_spot.remove(pack_id)

        await session.delete(pack_to_delete)
        await session.commit()

    await callback.message.edit_text(
        f"<strong>🗑 Пак №{pack_to_delete.id} успешно удалён</strong>",
        reply_markup=kb.adm_back, parse_mode='HTML'
    )

@rt.callback_query(F.data == "edit_pack_spot")
async def edit_pack_spot(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_page = data.get("current_page", 1)
    async with async_session() as session:
        result = await session.execute(select(SpotPack).order_by(SpotPack.id))
        packs = result.scalars().all()

        if current_page > len(packs):
            await callback.message.edit_text(
                "<strong>Ошибка: Пак не найден. Попробуйте снова</strong>",
                reply_markup=kb.adm_back, parse_mode='HTML'
            )
            return

        pack_to_edit = packs[current_page - 1]

        await state.update_data(pack_to_edit_id=pack_to_edit.id)

    await state.set_state(SpotStates.editing_page)
    await callback.answer('🔧 Изменить')
    await callback.message.edit_text(
        "<strong>Введите новый список username-ов для текущего пака (5 строк):</strong>",
        reply_markup=kb.adm_back, parse_mode='HTML'
    )

@rt.message(SpotStates.editing_page)
async def process_edit_pack_spot(message: Message, state: FSMContext):
    usernames = message.text.strip().splitlines()

    if len(usernames) != 5:
        await message.answer(
            f"<strong>⚠️ Количество строк — {len(usernames)}. Требуется ровно 5. Попробуйте снова:</strong>",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    invalid_usernames = [username for username in usernames if not valid_username_pattern.match(username.strip())]
    if invalid_usernames:
        await message.answer(
            f"<strong>⚠️ Невалидные username-ы: {', '.join(invalid_usernames)}</strong>\n"
            "Пожалуйста, убедитесь, что каждый username состоит только из букв, цифр, точек и подчеркиваний",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    duplicate_usernames = [username for username in usernames if usernames.count(username) > 1]
    if duplicate_usernames:
        await message.answer(
            f"<strong>⚠️ В паке повторяются юзернеймы: {', '.join(set(duplicate_usernames))}</strong>\n"
            "Пожалуйста, удалите повторяющиеся юзернеймы и попробуйте снова.",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    data = await state.get_data()
    current_page = data.get("current_page", 1)

    async with async_session() as session:
        result = await session.execute(select(SpotPack).order_by(SpotPack.id))
        packs = result.scalars().all()

        if current_page > len(packs):
            await message.answer(
                "<strong>Ошибка: Пак не найден. Попробуйте снова</strong>",
                reply_markup=kb.adm_back, parse_mode='HTML'
            )
            return

        pack_to_edit = packs[current_page - 1]

        result = await session.execute(select(SpotPack.usernames))
        existing_usernames = result.scalars().all()

    existing_usernames = [username.strip() for usernames in existing_usernames for username in usernames.split(",")]

    current_pack_usernames = set(pack_to_edit.usernames.split(","))
    filtered_usernames = [username for username in usernames if username.strip() not in current_pack_usernames]

    duplicate_usernames_in_db = [username for username in filtered_usernames if username.strip() in existing_usernames]

    if duplicate_usernames_in_db:
        await message.answer(
            f"<strong>⚠️ Спот с юзернеймом(ами) {', '.join(duplicate_usernames_in_db)} уже есть в базе данных, повторите попытку</strong>",
            reply_markup=kb.adm_back, parse_mode='HTML'
        )
        return

    try:
        pack_to_edit.usernames = ",".join(usernames)

        async with async_session() as session:
            await session.merge(pack_to_edit)  

            await session.commit()

        if pack_to_edit.usernames != ",".join(usernames):
            logger.error("Ошибка: изменения не были сохранены.")
            await message.answer(
                "❌ Произошла ошибка при сохранении изменений. Попробуйте снова.",
                reply_markup=kb.adm_back
            )
            return

        await message.answer(
            f"<strong>✅ Пак №{pack_to_edit.id} успешно обновлён</strong>",
            reply_markup=kb.adm_start, parse_mode='HTML'
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при обновлении пака: {e}")
        await message.answer("❌ Произошла ошибка при обновлении пака. Попробуйте снова", reply_markup=kb.adm_back)



