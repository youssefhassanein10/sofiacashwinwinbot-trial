from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from config import Config

def get_main_keyboard():
    """Основная клавиатура для пользователей"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("💰 Пополнить счет"), KeyboardButton("💸 Вывести средства")],
        [KeyboardButton("📊 Мой баланс"), KeyboardButton("📋 Мои депозиты")],
        [KeyboardButton("🆘 Поддержка"), KeyboardButton("📞 Связаться с поддержкой")]
    ], resize_keyboard=True, input_field_placeholder="Выберите действие...")

def get_admin_keyboard():
    """Клавиатура для администратора"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("📊 Статистика"), KeyboardButton("⏳ Ожидающие депозиты")],
        [KeyboardButton("🔄 В обработке"), KeyboardButton("📢 Рассылка")],
        [KeyboardButton("💼 Баланс кассы"), KeyboardButton("👤 Поиск игрока")]
    ], resize_keyboard=True, input_field_placeholder="Панель администратора...")

def get_deposit_keyboard(deposit_id):
    """Клавиатура для депозита (админ)"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"accept_{deposit_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{deposit_id}")
        ],
        [
            InlineKeyboardButton("📞 Связаться", callback_data=f"contact_{deposit_id}"),
            InlineKeyboardButton("💳 Реквизиты", callback_data=f"payment_{deposit_id}")
        ]
    ])

def get_user_deposit_keyboard(deposit_id):
    """Клавиатура для пользователя после создания депозита"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Я оплатил", callback_data=f"paid_{deposit_id}"),
            InlineKeyboardButton("❌ Отменить", callback_data=f"user_cancel_{deposit_id}")
        ],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help_deposit")]
    ])

def get_payment_methods_keyboard():
    """Выбор метода оплаты"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Банковская карта", callback_data="method_card"),
            InlineKeyboardButton("📱 ЮMoney", callback_data="method_yoomoney")
        ],
        [
            InlineKeyboardButton("🎯 QIWI", callback_data="method_qiwi"),
            InlineKeyboardButton("🔗 Крипто", callback_data="method_crypto")
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")]
    ])

def get_broadcast_keyboard():
    """Клавиатура для рассылки"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Отправить", callback_data="broadcast_confirm"),
            InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")
        ]
    ])

def get_support_keyboard():
    """Клавиатура поддержки"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Написать в поддержку", url=f"https://t.me/{Config.SUPPORT_USERNAME[1:]}")],
        [InlineKeyboardButton("📋 Частые вопросы", callback_data="faq")]
    ])

def get_cancel_keyboard():
    """Клавиатура отмены"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("❌ Отмена")]
    ], resize_keyboard=True, one_time_keyboard=True)

def get_confirm_keyboard():
    """Клавиатура подтверждения"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Нет", callback_data="confirm_no")
        ]
    ])
