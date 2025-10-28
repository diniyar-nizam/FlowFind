from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)


aftstart = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='🎯 Главное меню')],
    [KeyboardButton(text='👥 Поддержка')]
], resize_keyboard=True)


M_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🎨 Профиль', callback_data='profile')],
    [InlineKeyboardButton(text='💾 Коллекция', callback_data='collection')],
    [InlineKeyboardButton(text='🎟 Подписка', callback_data='subscription')],
    [InlineKeyboardButton(text='🗣️ Отзывы', url='https://t.me/flowfindofficial/23')]
])


adm_start = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🎟️ Выдать подписку', callback_data='sub')],
    [InlineKeyboardButton(text='🪪 Проверить подписку', callback_data='gsub')],
    [InlineKeyboardButton(text='💾 Проверить паки', callback_data='gpack')],
    [InlineKeyboardButton(text='🎫 Промокоды', callback_data='promo')],
    [InlineKeyboardButton(text='📪 Рассылка', callback_data='mail')],
    [InlineKeyboardButton(text='💻 FlowFind', callback_data='ffind')]
])
free_discount = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='⏳ Бесплатные Дни', callback_data='promo_type_freedays')],
    [InlineKeyboardButton(text='💸 Скидка', callback_data='promo_type_discount')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='promo')]
])
promo_basic_gold = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='BASIC', callback_data='promo_sub1_basic')],
    [InlineKeyboardButton(text='GOLD', callback_data='promo_sub1_gold')],
    [InlineKeyboardButton(text='BASIC+GOLD', callback_data='promo_sub1_goldbasic')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='promo')]
])
promo_basic_gold_without_basicgold = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='BASIC', callback_data='promo_sub1_basic')],
    [InlineKeyboardButton(text='GOLD', callback_data='promo_sub1_gold')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='promo')]
])

spot_artists_for_users = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='SPOT', callback_data='promo_sub_choice_spot')],
    [InlineKeyboardButton(text='ARTISTS', callback_data='promo_sub_choice_artists')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='promo')]
])

mail = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📪 Рассылка', callback_data='mail_choice')],
    [InlineKeyboardButton(text='🤖 Авторассылка', callback_data='automail')],
    [InlineKeyboardButton(text='⚙️ ADMIN PANEL', callback_data='adm_back')]
])

fast_mail = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📪 Общая рассылка', callback_data='mailing')],
    [InlineKeyboardButton(text='💰 Для любых платных подписчиков', callback_data='for_sub')],
    [InlineKeyboardButton(text='🆓 Кто брал бесплатную', callback_data='who_free')],
    [InlineKeyboardButton(text='🆓 Кто не брал бесплатную', callback_data='who_no_free')],
    [InlineKeyboardButton(text='💰 Кто брал любую платную', callback_data='who_paid')],
    [InlineKeyboardButton(text='🆓 Для бесплатных подписчиков', callback_data='who_in_free_sub')],
    [InlineKeyboardButton(text='GOLD', callback_data='gold_mail'),
     InlineKeyboardButton(text='SPOT', callback_data='spot_mail'),
     InlineKeyboardButton(text='ARTIST', callback_data='artists_mail')],
    [InlineKeyboardButton(text='⚙️ ADMIN PANEL', callback_data='adm_back')]
])
backtosub = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='↩️ Назад', callback_data='subscription')]
])

group_mail = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='❌ free sub = 0', callback_data='no_sub')],
    [InlineKeyboardButton(text='✅ free sub = 1', callback_data='end_sub')],
    [InlineKeyboardButton(text='⚙️ ADMIN PANEL', callback_data='adm_back')]
])


ff = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📲 ADD', callback_data='add'),
     InlineKeyboardButton(text='📁 DATABASE', callback_data='database')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='ffback')]
])


confirmation_buttons = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Подтвердить', callback_data='confirm'),
     InlineKeyboardButton(text='🔧 Изменить', callback_data='edit')],
    [InlineKeyboardButton(text='🗑 Отклонить', callback_data='decline')]
])


subscription2 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🎟 Подписка', callback_data='subscription_p')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='back')]
])

subscription3 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🎟 Подписка', callback_data='subscription_c')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='back')]
])

subscription = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🎟 Подписка', callback_data='subscription')]
])

subscription4 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🎟 Подписка', callback_data='subscription_m')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='back')]
])

adm_back = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='⚙️ ADMIN PANEL', callback_data='adm_back')]
])

adm_add = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Выдать подписку на 30 дней', callback_data='adm_give')],
    [InlineKeyboardButton(text='⚙️ ADMIN PANEL', callback_data='adm_back')]

])


backtomenu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🎯 В главное меню', callback_data='m_back')]
])


def database_navigation(current_page, total_pages):
    page_info = InlineKeyboardButton(
        text=f"{current_page}/{total_pages}", callback_data="page_info"
    )

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❮", callback_data="page_prev"),
         page_info,
         InlineKeyboardButton(text="❯", callback_data="page_next")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data="delete_pack"),
         InlineKeyboardButton(text="🔧 Изменить", callback_data="edit_pack")],
        [InlineKeyboardButton(text='📃 Выбор страницы', callback_data='go_to_page')],
        [InlineKeyboardButton(text='↩️ Назад', callback_data='db_back')]
    ])
    return buttons

def database_navigation_sec(current_page, total_pages):
    page_inf = InlineKeyboardButton(
        text=f"{current_page}/{total_pages}", callback_data="page_inf"
    )

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❮", callback_data=f"pag_pre"),
         page_inf,
         InlineKeyboardButton(text="❯", callback_data=f"pag_nex")],
        [InlineKeyboardButton(text='📃 Выбор страницы', callback_data='go_to_page_art_col')],
        [InlineKeyboardButton(text='↩️ Назад', callback_data='col_back')]
    ])
    return buttons


back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='↩️ Назад', callback_data='back')]])


sure = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Да', callback_data='yes')]])


def get_free_subscription_button():
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Бесплатная подписка", callback_data="free_subscription")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
    ])
    return buttons
def get_free_subscription_button_p():
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Бесплатная подписка", callback_data="free_subscription_p")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_p")]
    ])
    return buttons
def get_free_subscription_button_c():
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Бесплатная подписка", callback_data="free_subscription_c")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_c")]
    ])
    return buttons
def get_free_subscription_button_completed():
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Активировать", callback_data="free_subscription_completed")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_")]
    ])
    return buttons
def get_free_subscription_button_completed_p():
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Активировать", callback_data="free_subscription_completed_pr")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_pr")]
    ])
    return buttons
def get_free_subscription_button_completed_c():
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Активировать", callback_data="free_subscription_completed_co")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_co")]
    ])
    return buttons
spot_artists = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='artists', callback_data='artists'), InlineKeyboardButton(text='spot', callback_data='spot')],
    [InlineKeyboardButton(text='⚙️ ADMIN PANEL', callback_data='adm_back')]
])

spot = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='📲 ADD', callback_data='add_spot'),
     InlineKeyboardButton(text='📁 DATABASE', callback_data='database_spot')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='ffback')]
])

def database_navigation_spot(current_page, total_pages):
    page_info = InlineKeyboardButton(
        text=f"{current_page}/{total_pages}", callback_data="page_info"
    )

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❮", callback_data="pagespot_prev"),
         page_info,
         InlineKeyboardButton(text="❯", callback_data="pagespot_next")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data="delete_pack_spot"),
         InlineKeyboardButton(text="🔧 Изменить", callback_data="edit_pack_spot")],
        [InlineKeyboardButton(text='📃 Выбор страницы', callback_data='go_to_page_spot')],
        [InlineKeyboardButton(text='↩️ Назад', callback_data='db_back_spot')]
    ])
    return buttons

confirmation_buttons_spot = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Подтвердить', callback_data='confirm_spot'),
     InlineKeyboardButton(text='🔧 Изменить', callback_data='edit_spot')],
    [InlineKeyboardButton(text='🗑 Отклонить', callback_data='decline_spot')]
])

spot_artists_col = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='ARTISTS', callback_data='artists_col'), InlineKeyboardButton(text='SPOT', callback_data='spot_col')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='back')]
])

def database_navigation_sec_spot(current_page, total_pages):
    page_inf = InlineKeyboardButton(
        text=f"{current_page}/{total_pages}", callback_data="page_inf"
    )

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❮", callback_data=f"spotpag_pre"),
         page_inf,
         InlineKeyboardButton(text="❯", callback_data=f"spotpag_nex")],
        [InlineKeyboardButton(text='📃 Выбор страницы', callback_data='go_to_page_spot_col')],
        [InlineKeyboardButton(text='↩️ Назад', callback_data='col_back')]
    ])
    return buttons

gold_spot_artists = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='GOLD', callback_data='give_gold')],
    [InlineKeyboardButton(text='SPOT', callback_data='give_spot')],
    [InlineKeyboardButton(text='ARTISTS', callback_data='give_artists')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='adm_back')]
])

back_to_col_spot = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_spot')]
])
back_to_col_artists = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_art')]
])

col_swap = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🕹 Сменить подписку', callback_data='swap_sub')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='back')]
])

are_you_sure = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='✅ Сменить', callback_data='user_yes')],
    [InlineKeyboardButton(text='↩️ Назад', callback_data='back_to_profile')]
])
back_to_profile = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🎨 В профиль', callback_data='back_to_profile')]
])

confirm_subscription = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='✅ Подтвердить', callback_data='confirm_sub')],
        [InlineKeyboardButton(text='❌ Отменить', callback_data='adm_back')]
    ]
)