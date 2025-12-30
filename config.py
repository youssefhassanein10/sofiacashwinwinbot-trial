import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Токен бота (обязательно)
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Данные API SofiaCash (получить у менеджера)
    API_HASH = os.getenv('API_HASH', 'fhd.ncbf9hf2ythr')  # пример из документации
    API_CASHIERPASS = os.getenv('API_CASHIERPASS', '123123')
    API_CASHDESKID = os.getenv('API_CASHDESKID', '77')
    API_LOGIN = os.getenv('API_LOGIN', 'cashier_login')
    API_BASE_URL = "https://partners.servcul.com/CashdeskBotAPI/"
    
    # Админы (ID Telegram через запятую)
    ADMINS = [int(admin_id) for admin_id in os.getenv('ADMINS', '123456789').split(',') if admin_id]
    
    # Поддержка
    SUPPORT_USERNAME = os.getenv('SUPPORT_USERNAME', '@WinWinSupport')
    
    # Настройки
    DEPOSIT_TIMEOUT = 600  # 10 минут
    MIN_DEPOSIT = 100      # Минимальный депозит
    
    # Статусы
    STATUS_PENDING = "ожидает оплаты"
    STATUS_PAID = "оплачен"
    STATUS_PROCESSING = "в обработке"
    STATUS_COMPLETED = "завершен"
    STATUS_CANCELLED = "отменен"
