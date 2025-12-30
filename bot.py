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
        f"• QIWI: 1₽ = 1₽\n"
        f"• ЮMoney: 1₽ = 1₽\n"
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
    
    # Генерируем детали опла
