import os
import logging
import sys
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Простая конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ ERROR: BOT_TOKEN not found!")
    logger.error("Add BOT_TOKEN to Environment Variables on Render")
    sys.exit(1)

ADMINS = []
admins_str = os.getenv('ADMINS', '')
if admins_str:
    try:
        ADMINS = [int(admin_id.strip()) for admin_id in admins_str.split(',') if admin_id.strip()]
    except:
        ADMINS = []

SUPPORT_USERNAME = os.getenv('SUPPORT_USERNAME', '@WinWinSupport')

def is_admin(user_id):
    return user_id in ADMINS

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    
    if is_admin(user.id):
        text = f"👋 Администратор {user.first_name}!\nПанель управления готова."
        keyboard = ReplyKeyboardMarkup([
            ["📊 Статистика", "⏳ Депозиты"],
            ["📢 Рассылка", "🆘 Поддержка"]
        ], resize_keyboard=True)
    else:
        text = f"🎰 Добро пожаловать, {user.first_name}!\nWinWin бот к вашим услугам."
        keyboard = ReplyKeyboardMarkup([
            ["💰 Пополнить счет", "💸 Вывести средства"],
            ["📊 Мой баланс", "🆘 Поддержка"]
        ], resize_keyboard=True)
    
    update.message.reply_text(text, reply_markup=keyboard)

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    
    if text == "💰 Пополнить счет":
        update.message.reply_text(
            "💵 Введите сумму для пополнения (мин. 100 ₽):\n\n"
            "⚠️ Система в разработке. Реальные платежи скоро будут доступны!"
        )
    elif text == "🆘 Поддержка":
        update.message.reply_text(
            f"📞 Служба поддержки: {SUPPORT_USERNAME}\n"
            f"🕒 Работаем 24/7\n\n"
            f"Нажмите на username выше, чтобы написать нам."
        )
    elif text == "📊 Мой баланс":
        update.message.reply_text("💰 Ваш баланс: 0 ₽\nДля пополнения нажмите '💰 Пополнить счет'")
    elif text == "💸 Вывести средства":
        update.message.reply_text("Вывод средств временно недоступен. Обратитесь в поддержку.")
    elif text == "📊 Статистика" and is_admin(update.effective_user.id):
        update.message.reply_text(
            "📊 Система в тестовом режиме\n"
            "👥 Пользователи: тестирование\n"
            "💰 Депозиты: 0\n"
            "⏳ В ожидании: 0"
        )
    else:
        update.message.reply_text("Используйте кнопки меню для навигации.")

def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Ошибка: {context.error}")

def main():
    logger.info(f"🚀 Starting bot with token: {BOT_TOKEN[:10]}...")
    
    try:
        # Создаем Updater (старый API для версии 13.15)
        updater = Updater(token=BOT_TOKEN, use_context=True)
        
        # Получаем диспетчер
        dp = updater.dispatcher
        
        # Добавляем обработчики
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        
        # Обработчик ошибок
        dp.add_error_handler(error_handler)
        
        # Запускаем бота
        logger.info("🤖 Bot started and ready!")
        logger.info(f"📞 Support: {SUPPORT_USERNAME}")
        
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
