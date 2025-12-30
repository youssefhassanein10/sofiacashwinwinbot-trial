import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode

import config
from database import Database
from keyboards import *
from utils import *

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
db = Database()

# Состояния FSM
class DepositStates(StatesGroup):
    waiting_amount = State()
    waiting_payment = State()

class WithdrawStates(StatesGroup):
    waiting_amount = State()
    waiting_requisites = State()

class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_user_action = State()

# ===== ОСНОВНЫЕ КОМАНДЫ =====
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    # Проверяем реферальную ссылку
    referrer_id = None
    if len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
        if ref_code.startswith('ref'):
            try:
                referrer_id = int(ref_code[3:])
            except:
                pass
    
    db.create_user(user_id, username, first_name, last_name, referrer_id)
    
    # Приветственное сообщение
    welcome_text = (
        f"🎉 Добро пожаловать в *{config.BOT_NAME}*!\n\n"
        f"{config.BOT_DESCRIPTION}\n\n"
        f"💎 *Наши преимущества:*\n"
        f"• Мгновенные переводы\n"
        f"• Низкие комиссии\n"
        f"• Круглосуточная поддержка\n"
        f"• Множество способов оплаты\n\n"
        f"📊 *Быстрый старт:*\n"
        f"1. Пополните баланс\n"
        f"2. Выводите средства\n"
        f"3. Приглашайте друзей\n\n"
        f"💰 *Ваш реферальный код:* `ref{user_id}`\n"
        f"🔗 *Ссылка:* https://t.me/{message.bot.username}?start=ref{user_id}"
    )
    
    await message.answer(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_menu())

@dp.message_handler(commands=['admin'])
async def cmd_admin(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к админ-панели")
        return
    
    stats = db.get_bot_stats()
    
    stats_text = (
        f"⚙️ *Панель администратора*\n\n"
        f"📊 *Статистика:*\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"🔥 Активных сегодня: {stats['active_today']}\n"
        f"💰 Общий баланс: {format_balance(stats['total_balance'])}\n"
        f"📥 Всего пополнений: {format_balance(stats['total_deposits'])}\n"
        f"📤 Всего выводов: {format_balance(stats['total_withdrawals'])}\n"
        f"⏳ Ожидают обработки: {stats['pending_transactions']}\n\n"
        f"⚡ *Быстрые действия:*"
    )
    
    await message.answer(stats_text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_admin_menu())

# ===== ОСНОВНОЕ МЕНЮ =====
@dp.message_handler(lambda message: message.text == "💰 Мой баланс")
async def show_balance(message: types.Message):
    user = db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("Пользователь не найден. Нажмите /start")
        return
    
    balance_text = (
        f"💼 *Ваш баланс*\n\n"
        f"💎 Основной: *{format_balance(user[4])}*\n"
        f"📥 Всего пополнено: {format_balance(user[5])}\n"
        f"📤 Всего выведено: {format_balance(user[6])}\n\n"
        f"👥 Рефералов: {user[9]}\n"
        f"🆔 Ваш код: `ref{user[0]}`"
    )
    
    await message.answer(balance_text, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(lambda message: message.text == "📥 Пополнить")
async def start_deposit(message: types.Message):
    await message.answer(
        f"💳 *Выберите способ пополнения:*\n\n"
        f"Минимальная сумма: {format_balance(config.MIN_DEPOSIT)}\n"
        f"Максимальная сумма: {format_balance(config.MAX_DEPOSIT)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_payment_methods()
    )

@dp.message_handler(lambda message: message.text == "📤 Вывести")
async def start_withdraw(message: types.Message):
    user = db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("Пользователь не найден")
        return
    
    if user[4] < config.MIN_WITHDRAW:
        await message.answer(
            f"❌ *Недостаточно средств*\n\n"
            f"Минимальная сумма вывода: {format_balance(config.MIN_WITHDRAW)}\n"
            f"Ваш баланс: {format_balance(user[4])}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await message.answer(
        f"💸 *Вывод средств*\n\n"
        f"💰 Доступно: {format_balance(user[4])}\n"
        f"📉 Комиссия: {config.WITHDRAW_FEE}%\n"
        f"🔢 Минимум: {format_balance(config.MIN_WITHDRAW)}\n\n"
        f"*Выберите способ вывода:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_withdraw_methods()
    )

@dp.message_handler(lambda message: message.text == "📊 История операций")
async def show_history(message: types.Message):
    transactions = db.get_user_transactions(message.from_user.id, limit=5)
    
    if not transactions:
        await message.answer("📭 У вас еще нет операций")
        return
    
    history_text = "📊 *Последние операции:*\n\n"
    
    for trans in transactions:
        history_text += f"{format_transaction(trans)}\n\n"
    
    await message.answer(history_text, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(lambda message: message.text == "👤 Мой профиль")
async def show_profile(message: types.Message):
    user = db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("Пользователь не найден")
        return
    
    profile_text = (
        f"👤 *Ваш профиль*\n\n"
        f"🆔 ID: `{user[0]}`\n"
        f"👁‍🗨 Username: @{user[1] or 'не установлен'}\n"
        f"📅 Регистрация: {format_date(user[12])}\n"
        f"💰 Баланс: {format_balance(user[4])}\n\n"
        f"📊 *Статистика:*\n"
        f"📥 Пополнений: {format_balance(user[5])}\n"
        f"📤 Выводов: {format_balance(user[6])}\n"
        f"👥 Рефералов: {user[9]}\n\n"
        f"🔗 *Реферальная ссылка:*\n"
        f"`https://t.me/{message.bot.username}?start=ref{user[0]}`"
    )
    
    await message.answer(profile_text, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(lambda message: message.text == "🆘 Поддержка")
async def show_support(message: types.Message):
    support_text = (
        f"🆘 *Служба поддержки*\n\n"
        f"📞 Техподдержка: {config.SUPPORT_USERNAME}\n"
        f"📢 Новости: {config.CHANNEL_USERNAME}\n"
        f"🌐 Сайт: {config.WEBSITE_URL}\n\n"
        f"⏰ *Режим работы:*\n"
        f"• Поддержка: 24/7\n"
        f"• Выводы: 10:00-22:00 МСК\n\n"
        f"📋 *Правила:*\n"
        f"1. Минимальный вывод: {format_balance(config.MIN_WITHDRAW)}\n"
        f"2. Комиссия на вывод: {config.WITHDRAW_FEE}%\n"
        f"3. Верификация не требуется"
    )
    
    await message.answer(support_text, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(lambda message: message.text == "📈 Курсы")
async def show_rates(message: types.Message):
    rates_text = (
        f"📈 *Курсы обмена*\n\n"
        f"💵 *Пополнение:*\n"
        f"• Т-Банк: 1₽ = 1₽\n"
        f"• СБП: 1₽ = 1₽\n"
        f"• Банк. карта: 1₽ = 1₽\n"
        f"• USDT: 1$ = ~95₽\n\n"
        f"💸 *Вывод:*\n"
        f"• Комиссия: {config.WITHDRAW_FEE}%\n"
        f"• Минимум: {format_balance(config.MIN_WITHDRAW)}\n"
        f"• Максимум: {format_balance(config.MAX_WITHDRAW)}\n\n"
        f"⚡ *Сроки:*\n"
        f"• Пополнение: мгновенно\n"
        f"• Вывод: 5-60 минут"
    )
    
    await message.answer(rates_text, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(lambda message: message.text == "🎁 Реферальная программа")
async def show_referral(message: types.Message):
    user = db.get_user(message.from_user.id)
    
    referral_text = (
        f"🎁 *Реферальная программа*\n\n"
        f"💰 *Зарабатывайте 5%* с каждого пополнения приглашенных друзей!\n\n"
        f"📊 *Ваша статистика:*\n"
        f"👥 Рефералов: {user[9]}\n"
        f"🆔 Ваш код: `ref{user[0]}`\n\n"
        f"🔗 *Ваша ссылка:*\n"
        f"`https://t.me/{message.bot.username}?start=ref{user[0]}`\n\n"
        f"📋 *Как работает:*\n"
        f"1. Друг переходит по вашей ссылке\n"
        f"2. Пополняет баланс\n"
        f"3. Вы получаете 5% от его пополнения\n\n"
        f"💡 *Совет:* Размещайте ссылку в соцсетях!"
    )
    
    await message.answer(referral_text, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(lambda message: message.text == "🔙 В главное меню")
async def back_to_main(message: types.Message):
    await message.answer("Возвращаемся в главное меню:", reply_markup=get_main_menu())

# ===== CALLBACK ОБРАБОТЧИКИ =====
@dp.callback_query_handler(lambda c: c.data.startswith('deposit_'))
async def process_deposit_method(callback_query: types.CallbackQuery, state: FSMContext):
    payment_method = callback_query.data.split('_')[1]
    
    await state.update_data(payment_method=payment_method)
    
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=(
            f"💳 *{config.PAYMENT_SYSTEMS.get(payment_method, payment_method)}*\n\n"
            f"Введите сумму пополнения:\n"
            f"• Минимум: {format_balance(config.MIN_DEPOSIT)}\n"
            f"• Максимум: {format_balance(config.MAX_DEPOSIT)}\n\n"
            f"Пример: `1000` или `500.50`"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_deposit_amounts()
    )
    
    await DepositStates.waiting_amount.set()

@dp.callback_query_handler(lambda c: c.data.startswith('amount_'))
async def process_deposit_amount(callback_query: types.CallbackQuery, state: FSMContext):
    amount_type = callback_query.data.split('_')[1]
    
    if amount_type == 'custom':
        await bot.answer_callback_query(callback_query.id, "Введите сумму вручную")
        return
    
    if amount_type == 'cancel':
        await bot.delete_message(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id
        )
        await state.finish()
        await callback_query.message.answer("Операция отменена", reply_markup=get_main_menu())
        return
    
    # Стандартные суммы
    amounts = {
        '50': 50, '100': 100, '500': 500,
        '1000': 1000, '5000': 5000
    }
    
    amount = amounts.get(amount_type, 0)
    
    user_data = await state.get_data()
    payment_method = user_data.get('payment_method')
    
    # Создаем транзакцию
    trans_id = db.create_transaction(
        callback_query.from_user.id,
        'deposit',
        amount,
        payment_method
    )
    
    # Генерируем детали оплаты
    from utils import generate_payment_details
    details = generate_payment_details(payment_method, amount)
    
    payment_text = (
        f"💳 *Детали оплаты*\n\n"
        f"💵 Сумма: *{format_balance(amount)}*\n"
        f"📋 Способ: {config.PAYMENT_SYSTEMS.get(payment_method, payment_method)}\n"
        f"🆔 Номер: `{trans_id}`\n\n"
    )
    
    if payment_method == 'qiwi':
        payment_text += (
            f"💳 *Т-Банк:*\n"
            f"📱 Номер: `{details['phone']}`\n"
            f"📝 Комментарий: `{details['comment']}`\n\n"
            f"💡 *Инструкция:*\n"
            f"1. Перейдите в Т-Банк\n"
            f"2. Введите номер\n"
            f"3. Укажите сумму\n"
            f"4. Введите комментарий\n"
            f"5. Оплатите"
        )
    elif payment_method == 'yoomoney':
        payment_text += (
            f"💳 *СБП:*\n"
            f"👛 Реквизиты: `{details['wallet']}`\n"
            f"📝 Комментарий: `{details['comment']}`\n\n"
            f"💡 *После оплаты:*\n"
            f"Средства поступят в течение 5 минут"
        )
    elif payment_method == 'bank_card':
        payment_text += (
            f"💳 *Банковская карта:*\n"
            f"🏦 Банк: {details['bank']}\n"
            f"💳 Карта: `{details['card']}`\n\n"
            f"💡 *После перевода:*\n"
            f"Средства поступят в течение 15 минут"
        )
    elif payment_method == 'crypto':
        payment_text += (
            f"₿ *Криптовалюта (USDT):*\n"
            f"👛 Кошелек: `{details['wallet']}`\n"
            f"🌐 Сеть: {details['network']}\n"
            f"💵 Сумма: {amount/95:.2f} USDT\n\n"
            f"⚠️ *Внимание:*\n"
            f"Отправляйте только USDT в сети TRC20!"
        )
    
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=payment_text,
        parse_mode=ParseMode.MARKDOWN
    )
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('withdraw_'))
async def process_withdraw_method(callback_query: types.CallbackQuery, state: FSMContext):
    payment_method = callback_query.data.split('_')[1]
    
    await state.update_data(payment_method=payment_method)
    
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=(
            f"💸 *Вывод на {config.PAYMENT_SYSTEMS.get(payment_method, payment_method)}*\n\n"
            f"Введите сумму для вывода:\n"
            f"• Комиссия: {config.WITHDRAW_FEE}%\n"
            f"• Минимум: {format_balance(config.MIN_WITHDRAW)}\n"
            f"• Максимум: {format_balance(config.MAX_WITHDRAW)}\n\n"
            f"Пример: `1000` или `500.50`"
        ),
        parse_mode=ParseMode.MARKDOWN
    )
    
    await WithdrawStates.waiting_amount.set()

# ===== ОБРАБОТКА СООБЩЕНИЙ ДЛЯ FSM =====
@dp.message_handler(state=DepositStates.waiting_amount)
async def process_deposit_amount_message(message: types.Message, state: FSMContext):
    is_valid, result = validate_amount(
        message.text,
        config.MIN_DEPOSIT,
        config.MAX_DEPOSIT
    )
    
    if not is_valid:
        await message.answer(result)
        return
    
    amount = result
    user_data = await state.get_data()
    payment_method = user_data.get('payment_method')
    
    # Создаем транзакцию
    trans_id = db.create_transaction(
        message.from_user.id,
        'deposit',
        amount,
        payment_method
    )
    
    # Генерируем детали оплаты
    from utils import generate_payment_details
    details = generate_payment_details(payment_method, amount)
    
    payment_text = (
        f"💳 *Детали оплаты*\n\n"
        f"💵 Сумма: *{format_balance(amount)}*\n"
        f"📋 Способ: {config.PAYMENT_SYSTEMS.get(payment_method, payment_method)}\n"
        f"🆔 Номер: `{trans_id}`\n\n"
    )
    
    if payment_method == 'qiwi':
        payment_text += (
            f"💳 *Т-Банк:*\n"
            f"📱 Номер: `{details['phone']}`\n"
            f"📝 Комментарий: `{details['comment']}`"
        )
    elif payment_method == 'yoomoney':
        payment_text += (
            f"💳 *СБП:*\n"
            f"👛 Реквизиты: `{details['wallet']}`\n"
            f"📝 Комментарий: `{details['comment']}`"
        )
    elif payment_method == 'bank_card':
        payment_text += (
            f"💳 *Банковская карта:*\n"
            f"🏦 Банк: {details['bank']}\n"
            f"💳 Карта: `{details['card']}`"
        )
    elif payment_method == 'crypto':
        payment_text += (
            f"₿ *Криптовалюта (USDT):*\n"
            f"👛 Кошелек: `{details['wallet']}`\n"
            f"🌐 Сеть: {details['network']}\n"
            f"💵 Сумма: {amount/95:.2f} USDT"
        )
    
    await message.answer(payment_text, parse_mode=ParseMode.MARKDOWN)
    await state.finish()

@dp.message_handler(state=WithdrawStates.waiting_amount)
async def process_withdraw_amount_message(message: types.Message, state: FSMContext):
    user = db.get_user(message.from_user.id)
    
    is_valid, result = validate_amount(
        message.text,
        config.MIN_WITHDRAW,
        min(config.MAX_WITHDRAW, user[4])
    )
    
    if not is_valid:
        await message.answer(result)
        return
    
    amount = result
    
    # Проверяем достаточно ли средств
    if amount > user[4]:
        await message.answer(f"❌ Недостаточно средств. Доступно: {format_balance(user[4])}")
        return
    
    # Расчет комиссии
    fee, net_amount = calculate_withdraw_fee(amount)
    
    await state.update_data(amount=amount, fee=fee, net_amount=net_amount)
    
    user_data = await state.get_data()
    payment_method = user_data.get('payment_method')
    
    # Запрашиваем реквизиты
    requisites_text = {
        'Т-Банк': "📱 Введите номер QIWI (формат: 79123456789):",
        'card': "💳 Введите номер карты (16-19 цифр):",
        'crypto': "₿ Введите адрес крипто-кошелька (USDT TRC20):"
    }.get(payment_method, "📋 Введите реквизиты для вывода:")
    
    await message.answer(
        f"💸 *Подтверждение вывода*\n\n"
        f"💵 Сумма: {format_balance(amount)}\n"
        f"📉 Комиссия: {format_balance(fee)} ({config.WITHDRAW_FEE}%)\n"
        f"💰 К получению: *{format_balance(net_amount)}*\n\n"
        f"{requisites_text}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await WithdrawStates.waiting_requisites.set()

@dp.message_handler(state=WithdrawStates.waiting_requisites)
async def process_withdraw_requisites(message: types.Message, state: FSMContext):
    requisites = message.text.strip()
    
    user_data = await state.get_data()
    amount = user_data.get('amount')
    fee = user_data.get('fee')
    net_amount = user_data.get('net_amount')
    payment_method = user_data.get('payment_method')
    
    # Создаем транзакцию
    trans_id = db.create_transaction(
        message.from_user.id,
        'withdraw',
        amount,
        payment_method,
        requisites
    )
    
    # Списываем средства
    db.update_balance(message.from_user.id, amount, 'withdraw')
    
    # Уведомляем пользователя
    await message.answer(
        f"✅ *Заявка на вывод создана!*\n\n"
        f"💵 Сумма: {format_balance(amount)}\n"
        f"💰 К получению: {format_balance(net_amount)}\n"
        f"📋 Способ: {config.PAYMENT_SYSTEMS.get(payment_method, payment_method)}\n"
        f"🆔 Номер заявки: `{trans_id}`\n\n"
        f"⏳ *Статус:* Ожидает обработки\n"
        f"Обычно вывод занимает 5-60 минут",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Уведомляем администраторов
    user = db.get_user(message.from_user.id)
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔄 *Новая заявка на вывод #{trans_id}*\n\n"
                f"👤 Пользователь: @{user[1] or 'без username'}\n"
                f"🆔 ID: `{user[0]}`\n"
                f"💵 Сумма: {format_balance(amount)}\n"
                f"💰 К выплате: {format_balance(net_amount)}\n"
                f"📋 Способ: {config.PAYMENT_SYSTEMS.get(payment_method, payment_method)}\n"
                f"📝 Реквизиты: `{requisites}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_confirmation_keyboard('withdraw', trans_id)
            )
        except:
            pass
    
    await state.finish()

# ===== АДМИН ФУНКЦИИ =====
@dp.message_handler(lambda message: message.text == "📊 Статистика бота")
async def admin_bot_stats(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    stats = db.get_bot_stats()
    
    # Получаем последние 5 пользователей
    recent_users = db.get_all_users(limit=5)
    
    stats_text = (
        f"📊 *Статистика бота*\n\n"
        f"👥 *Пользователи:*\n"
        f"• Всего: {stats['total_users']}\n"
        f"• Активных сегодня: {stats['active_today']}\n\n"
        f"💰 *Финансы:*\n"
        f"• Общий баланс: {format_balance(stats['total_balance'])}\n"
        f"• Всего пополнений: {format_balance(stats['total_deposits'])}\n"
        f"• Всего выводов: {format_balance(stats['total_withdrawals'])}\n"
        f"• Ожидают обработки: {stats['pending_transactions']}\n\n"
        f"👤 *Последние пользователи:*\n"
    )
    
    for user in recent_users:
        user_id, username, balance, created_at = user
        stats_text += f"• @{username or 'нет'}: {format_balance(balance)} ({format_date(created_at)})\n"
    
    await message.answer(stats_text, parse_mode=ParseMode.MARKDOWN)

@dp.message_handler(lambda message: message.text == "👥 Управление пользователями")
async def admin_users_management(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    await message.answer(
        "👥 *Управление пользователями*\n\n"
        "Для поиска пользователя отправьте:\n"
        "• Его ID\n"
        "• Username (без @)\n"
        "• Реферальный код\n\n"
        "Пример: `123456789` или `username`",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await AdminStates.waiting_user_action.set()

@dp.message_handler(state=AdminStates.waiting_user_action)
async def admin_search_user(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await state.finish()
        return
    
    query = message.text.strip()
    users = db.search_users(query)
    
    if not users:
        await message.answer("❌ Пользователь не найден")
        await state.finish()
        return
    
    # Показываем первого найденного пользователя
    user = users[0]
    
    user_info = (
        f"👤 *Информация о пользователе*\n\n"
        f"🆔 ID: `{user[0]}`\n"
        f"👁‍🗨 Username: @{user[1] or 'нет'}\n"
        f"👤 Имя: {user[2] or 'нет'} {user[3] or ''}\n"
        f"💰 Баланс: {format_balance(user[4])}\n"
        f"📥 Пополнено: {format_balance(user[5])}\n"
        f"📤 Выведено: {format_balance(user[6])}\n"
        f"👥 Рефералов: {user[9]}\n"
        f"🚫 Заблокирован: {'Да' if user[10] else 'Нет'}\n"
        f"👑 Админ: {'Да' if user[11] else 'Нет'}\n"
        f"📅 Регистрация: {format_date(user[12])}\n"
        f"🔥 Последняя активность: {format_date(user[13])}\n\n"
        f"🔗 Реферальный код: `{user[7]}`"
    )
    
    await message.answer(user_info, parse_mode=ParseMode.MARKDOWN, reply_markup=get_user_management_keyboard(user[0]))
    await state.finish()

@dp.message_handler(lambda message: message.text == "💼 Управление заявками")
async def admin_pending_withdrawals(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    withdrawals = db.get_pending_withdrawals()
    
    if not withdrawals:
        await message.answer("✅ Нет ожидающих заявок на вывод")
        return
    
    for withdraw in withdrawals:
        w_id, trans_id, user_id, amount, fee, net_amount, method, requisites, status, comment, created_at, processed_at = withdraw
        
        withdraw_text = (
            f"🔄 *Заявка на вывод #{w_id}*\n\n"
            f"👤 Пользователь: ID `{user_id}`\n"
            f"💵 Сумма: {format_balance(amount)}\n"
            f"📉 Комиссия: {format_balance(fee)}\n"
            f"💰 К выплате: {format_balance(net_amount)}\n"
            f"📋 Способ: {config.PAYMENT_SYSTEMS.get(method, method)}\n"
            f"📝 Реквизиты: `{requisites}`\n"
            f"📅 Дата: {format_date(created_at)}"
        )
        
        await message.answer(withdraw_text, parse_mode=ParseMode.MARKDOWN, reply_markup=get_transaction_actions(trans_id))

@dp.callback_query_handler(lambda c: c.data.startswith('trans_'))
async def process_transaction_action(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in config.ADMIN_IDS:
        await bot.answer_callback_query(callback_query.id, "Нет доступа")
        return
    
    action_parts = callback_query.data.split('_')
    action = action_parts[1]
    trans_id = int(action_parts[2])
    
    status_map = {
        'complete': 'completed',
        'cancel': 'cancelled',
        'pending': 'pending'
    }
    
    new_status = status_map.get(action, 'pending')
    
    db.update_transaction_status(trans_id, new_status, callback_query.from_user.id)
    
    status_text = {
        'completed': '✅ Выполнено',
        'cancelled': '❌ Отменено',
        'pending': '🕐 Отложено'
    }.get(new_status, new_status)
    
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=f"{callback_query.message.text}\n\n{status_text}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    await bot.answer_callback_query(callback_query.id, f"Статус изменен на: {status_text}")

# ===== ЗАПУСК БОТА =====
async def main():
    logger.info("Starting SofiaCash Bot...")
    
    try:
        await dp.start_polling()
    finally:
        await bot.close()

if __name__ == '__main__':
    asyncio.run(main())
if __name__ == '__main__':
    # Импортируем сервер только если это основной файл
    import server
    server.start_http_in_thread()
    
    # Запускаем бота
    asyncio.run(main())
