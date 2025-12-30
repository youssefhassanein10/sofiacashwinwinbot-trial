import os

# Токен бота (в Render добавьте как переменную окружения BOT_TOKEN)
BOT_TOKEN = os.getenv('BOT_TOKEN', '7479880371:AAHemgaC1OO2Ni-8ClbH9aYG4c8_FXoIQik')

# ID администратора (ваш Telegram ID)
ADMIN_ID = int(os.getenv('ADMIN_ID', '7940060404'))

# Настройки базы данных
DB_NAME = "database.db"

# Минимальные суммы
MIN_DEPOSIT = 100  # минимальное пополнение
MIN_WITHDRAW = 200  # минимальный вывод
