import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

import config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Состояния для FSM
class UserStates(StatesGroup):
    waiting_for_deposit_amount = State()
    waiting_for_withdraw_amount = State()
    waiting_for_admin_amount = State()

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            total_deposited REAL DEFAULT 0,
            total_withdrawn REAL DEFAULT 0,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица транзакций
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Функции для работы с БД
def get_user(user_id):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(user_id, username):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def update_balance(user_id, amount, operation='deposit'):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    if operation == 'deposit':
        cursor.execute("UPDATE users SET balance = balance + ?, total_deposited = total_deposited + ? WHERE user_id = ?", 
                      (amount, amount, user_id))
    elif operation == 'withdraw':
        cursor.execute("UPDATE users SET balance = balance - ?, total_withdrawn = total_withdrawn + ? WHERE user_id = ?", 
                      (amount, amount, user_id))
    
    conn.commit()
    conn.close()

def add_transaction(user_id, trans_type, amount):
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transactions (user_id, type, amount) VALUES (?, ?, ?)", 
                  (user_id, trans_type, amount))
    conn.commit()
    conn.close()

# Основные клавиатуры
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💰 Баланс"))
    keyboard.row(KeyboardButton("📥 Пополнить"), KeyboardButton("📤 Вывести"))
    keyboard.add(KeyboardButton("📊 Статистика"), KeyboardButton("ℹ️ Помощь"))
    return keyboard

def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📊 Общая статистика"))
    keyboard.add(KeyboardButton("👥 Все пользователи"))
    keyboard.add(KeyboardButton("➕ Начислить баланс"))
    keyboard.add(KeyboardButton("🔙 Главное меню"))
    return keyboard

# Команда /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or f"User_{user_id}"
    
    create_user(user_id, username)
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"Добро пожаловать в бота для управления балансом!\n\n"
        f"Используйте кнопки ниже для навигации:",
        reply_markup=get_main_keyboard()
    )

# Команда /admin (только для администратора)
@dp.message_handler(commands=['admin'])
async def cmd_admin(message: types.Message):
    if message.from_user.id == config.ADMIN_ID:
        await message.answer(
            "⚙️ Панель администратора",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("⛔ У вас нет доступа к этой команде.")

# Кнопка "💰 Баланс"
@dp.message_handler(lambda message: message.text == "💰 Баланс")
async def show_balance(message: types.Message):
    user = get_user(message.from_user.id)
    
    if user:
        await message.answer(
            f"📊 Ваш баланс: {user[2]:.2f} руб.\n"
            f"Всего пополнено: {user[3]:.2f} руб.\n"
            f"Всего выведено: {user[4]:.2f} руб."
        )
    else:
        await message.answer("Пользователь не найден. Нажмите /start")

# Кнопка "📥 Пополнить"
@dp.message_handler(lambda message: message.text == "📥 Пополнить")
async def start_deposit(message: types.Message):
    await message.answer(
        f"💳 Введите сумму для пополнения (минимум {config.MIN_DEPOSIT} руб.):\n"
        f"Пример: 500 или 1000.50"
    )
    await UserStates.waiting_for_deposit_amount.set()

# Обработчик суммы пополнения
@dp.message_handler(state=UserStates.waiting_for_deposit_amount)
async def process_deposit(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        
        if amount < config.MIN_DEPOSIT:
            await message.answer(f"❌ Минимальная сумма пополнения: {config.MIN_DEPOSIT} руб.")
            return
        
        user_id = message.from_user.id
        update_balance(user_id, amount, 'deposit')
        add_transaction(user_id, 'deposit', amount)
        
        await message.answer(
            f"✅ Успешно!\n"
            f"Сумма {amount:.2f} руб. зачислена на ваш баланс.\n"
            f"Для вывода доступно {amount:.2f} руб."
        )
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму (только цифры)")
    
    await state.finish()

# Кнопка "📤 Вывести"
@dp.message_handler(lambda message: message.text == "📤 Вывести")
async def start_withdraw(message: types.Message):
    user = get_user(message.from_user.id)
    
    if not user:
        await message.answer("Пользователь не найден. Нажмите /start")
        return
    
    if user[2] < config.MIN_WITHDRAW:
        await message.answer(f"❌ Минимальная сумма для вывода: {config.MIN_WITHDRAW} руб.")
        return
    
    await message.answer(
        f"💸 Введите сумму для вывода (доступно: {user[2]:.2f} руб.):\n"
        f"Минимум: {config.MIN_WITHDRAW} руб.\n"
        f"Укажите реквизиты для вывода после суммы через пробел (например: '500 карта 1234')"
    )
    await UserStates.waiting_for_withdraw_amount.set()

# Обработчик вывода
@dp.message_handler(state=UserStates.waiting_for_withdraw_amount)
async def process_withdraw(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split(' ', 1)
        amount = float(parts[0].replace(',', '.'))
        details = parts[1] if len(parts) > 1 else "Не указаны"
        
        user = get_user(message.from_user.id)
        
        if amount < config.MIN_WITHDRAW:
            await message.answer(f"❌ Минимальная сумма вывода: {config.MIN_WITHDRAW} руб.")
            return
        
        if amount > user[2]:
            await message.answer(f"❌ Недостаточно средств. Доступно: {user[2]:.2f} руб.")
            return
        
        # Обновляем баланс
        update_balance(message.from_user.id, amount, 'withdraw')
        add_transaction(message.from_user.id, 'withdraw', amount)
        
        # Уведомляем администратора
        admin_text = (
            f"🔄 Новая заявка на вывод:\n"
            f"Пользователь: @{message.from_user.username or 'без username'}\n"
            f"ID: {message.from_user.id}\n"
            f"Сумма: {amount:.2f} руб.\n"
            f"Реквизиты: {details}\n"
            f"Баланс после вывода: {user[2] - amount:.2f} руб."
        )
        
        try:
            await bot.send_message(config.ADMIN_ID, admin_text)
        except:
            pass
        
        await message.answer(
            f"✅ Заявка на вывод {amount:.2f} руб. принята!\n"
            f"Реквизиты: {details}\n"
            f"Заявка отправлена администратору. Вы получите уведомление."
        )
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму (например: '500 карта 1234')")
    except Exception as e:
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        logger.error(f"Withdraw error: {e}")
    
    await state.finish()

# Кнопка "📊 Статистика"
@dp.message_handler(lambda message: message.text == "📊 Статистика")
async def show_stats(message: types.Message):
    user = get_user(message.from_user.id)
    
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    # Считаем транзакции пользователя
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (message.from_user.id,))
    total_transactions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ? AND type = 'deposit'", (message.from_user.id,))
    deposits_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ? AND type = 'withdraw'", (message.from_user.id,))
    withdraws_count = cursor.fetchone()[0]
    
    conn.close()
    
    await message.answer(
        f"📈 Ваша статистика:\n"
        f"Баланс: {user[2]:.2f} руб.\n"
        f"Всего пополнений: {deposits_count}\n"
        f"Всего выводов: {withdraws_count}\n"
        f"Всего транзакций: {total_transactions}\n"
        f"Дата регистрации: {user[5]}"
    )

# Кнопка "ℹ️ Помощь"
@dp.message_handler(lambda message: message.text == "ℹ️ Помощь")
async def show_help(message: types.Message):
    await message.answer(
        "❓ Помощь по боту:\n\n"
        "💰 Баланс - посмотреть текущий баланс\n"
        "📥 Пополнить - пополнить баланс\n"
        f"  • Минимум: {config.MIN_DEPOSIT} руб.\n"
        "📤 Вывести - вывести средства\n"
        f"  • Минимум: {config.MIN_WITHDRAW} руб.\n"
        "📊 Статистика - ваша статистика\n\n"
        "Для связи с администратором используйте команду /support"
    )

# Команда /support
@dp.message_handler(commands=['support'])
async def cmd_support(message: types.Message):
    await message.answer(
        "📞 Связь с администратором:\n"
        f"ID администратора: {config.ADMIN_ID}\n"
        "Опишите вашу проблему, и администратор свяжется с вами."
    )

# АДМИН-ФУНКЦИИ

# Кнопка "📊 Общая статистика"
@dp.message_handler(lambda message: message.text == "📊 Общая статистика")
async def admin_stats(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(balance) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(total_deposited) FROM users")
    total_deposited = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(total_withdrawn) FROM users")
    total_withdrawn = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total_transactions = cursor.fetchone()[0]
    
    conn.close()
    
    await message.answer(
        f"📊 Общая статистика бота:\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💰 Общий баланс: {total_balance:.2f} руб.\n"
        f"📥 Всего пополнено: {total_deposited:.2f} руб.\n"
        f"📤 Всего выведено: {total_withdrawn:.2f} руб.\n"
        f"🔄 Всего транзакций: {total_transactions}"
    )

# Кнопка "👥 Все пользователи"
@dp.message_handler(lambda message: message.text == "👥 Все пользователи")
async def admin_all_users(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    conn = sqlite3.connect(config.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, balance FROM users ORDER BY balance DESC LIMIT 20")
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        await message.answer("📭 Пользователей нет")
        return
    
    response = "👥 Топ-20 пользователей:\n\n"
    for i, user in enumerate(users, 1):
        response += f"{i}. @{user[1] or 'без username'} (ID: {user[0]})\n   Баланс: {user[2]:.2f} руб.\n\n"
    
    await message.answer(response[:4000])  # Ограничение Telegram

# Кнопка "➕ Начислить баланс"
@dp.message_handler(lambda message: message.text == "➕ Начислить баланс")
async def admin_add_balance(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    await message.answer(
        "Введите данные в формате:\n"
        "ID_пользователя сумма\n\n"
        "Пример: 123456789 1000"
    )
    await UserStates.waiting_for_admin_amount.set()

# Обработчик начисления баланса
@dp.message_handler(state=UserStates.waiting_for_admin_amount)
async def process_admin_add(message: types.Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        await state.finish()
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Неверный формат. Пример: 123456789 1000")
            return
        
        user_id = int(parts[0])
        amount = float(parts[1])
        
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительной")
            return
        
        # Начисляем баланс
        update_balance(user_id, amount, 'deposit')
        add_transaction(user_id, 'admin_deposit', amount)
        
        # Пытаемся уведомить пользователя
        try:
            await bot.send_message(
                user_id,
                f"🎉 Администратор начислил вам {amount:.2f} руб.\n"
                f"Текущий баланс обновлен."
            )
        except:
            pass
        
        await message.answer(f"✅ Пользователю {user_id} начислено {amount:.2f} руб.")
        
    except ValueError:
        await message.answer("❌ Ошибка в данных. Проверьте ID и сумму")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    
    await state.finish()

# Кнопка "🔙 Главное меню"
@dp.message_handler(lambda message: message.text == "🔙 Главное меню")
async def back_to_main(message: types.Message):
    await message.answer("Возвращаемся в главное меню:", reply_markup=get_main_keyboard())

# Запуск бота
async def main():
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())
