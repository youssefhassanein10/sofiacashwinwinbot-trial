from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ===== ОСНОВНЫЕ КЛАВИАТУРЫ =====
def get_main_menu():
    """Главное меню для пользователей"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("💰 Мой баланс"),
        KeyboardButton("📥 Пополнить"),
        KeyboardButton("📤 Вывести"),
        KeyboardButton("📊 История операций"),
        KeyboardButton("👤 Мой профиль"),
        KeyboardButton("🆘 Поддержка"),
        KeyboardButton("📈 Курсы"),
        KeyboardButton("🎁 Реферальная программа")
    )
    return keyboard

def get_admin_menu():
    """Меню администратора"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📊 Статистика бота"),
        KeyboardButton("👥 Управление пользователями"),
        KeyboardButton("💼 Управление заявками"),
        KeyboardButton("⚙️ Настройки"),
        KeyboardButton("📢 Рассылка"),
        KeyboardButton("🔙 В главное меню")
    )
    return keyboard

# ===== ИНЛАЙН КЛАВИАТУРЫ =====
def get_payment_methods():
    """Выбор способа оплаты"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Т-Банк", callback_data="deposit_qiwi"),
        InlineKeyboardButton("💳 СБП", callback_data="deposit_yoomoney"),
        InlineKeyboardButton("💳 Банк. карта", callback_data="deposit_card"),
        InlineKeyboardButton("₿ USDT", callback_data="deposit_crypto")
    )
    return keyboard

def get_deposit_amounts():
    """Быстрый выбор суммы пополнения"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("50₽", callback_data="amount_50"),
        InlineKeyboardButton("100₽", callback_data="amount_100"),
        InlineKeyboardButton("500₽", callback_data="amount_500"),
        InlineKeyboardButton("1000₽", callback_data="amount_1000"),
        InlineKeyboardButton("5000₽", callback_data="amount_5000"),
        InlineKeyboardButton("Другая", callback_data="amount_custom")
    )
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    return keyboard

def get_withdraw_methods():
    """Выбор способа вывода"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Т-Банк", callback_data="withdraw_qiwi"),
        InlineKeyboardButton("💳 На карту", callback_data="withdraw_card"),
        InlineKeyboardButton("₿ На крипто", callback_data="withdraw_crypto")
    )
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    return keyboard

def get_confirmation_keyboard(action, data_id):
    """Клавиатура подтверждения для админа"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{action}_{data_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{action}_{data_id}")
    )
    return keyboard

# ===== КЛАВИАТУРЫ ДЛЯ АДМИНА =====
def get_user_management_keyboard(user_id):
    """Управление конкретным пользователем"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Начислить", callback_data=f"admin_add_{user_id}"),
        InlineKeyboardButton("➖ Списать", callback_data=f"admin_sub_{user_id}"),
        InlineKeyboardButton("🔒 Заблокировать", callback_data=f"admin_ban_{user_id}"),
        InlineKeyboardButton("🔓 Разблокировать", callback_data=f"admin_unban_{user_id}"),
        InlineKeyboardButton("📊 Статистика", callback_data=f"admin_stats_{user_id}"),
        InlineKeyboardButton("💬 Написать", callback_data=f"admin_msg_{user_id}")
    )
    return keyboard

def get_transaction_actions(transaction_id):
    """Действия с транзакцией"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Выполнено", callback_data=f"trans_complete_{transaction_id}"),
        InlineKeyboardButton("❌ Отменить", callback_data=f"trans_cancel_{transaction_id}"),
        InlineKeyboardButton("🕐 Отложить", callback_data=f"trans_pending_{transaction_id}")
    )
    return keyboard
