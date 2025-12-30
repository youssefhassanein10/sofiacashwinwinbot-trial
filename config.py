import os

class Config:
    # Токен бота - обязательно
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    
    # Если BOT_TOKEN пустой, выходим
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN not found!")
        print("Add BOT_TOKEN to Environment Variables on Render")
        exit(1)
    
    # Данные API (можно тестовые)
    API_HASH = os.getenv('API_HASH', 'test_hash')
    API_CASHIERPASS = os.getenv('API_CASHIERPASS', 'test_pass')
    API_CASHDESKID = os.getenv('API_CASHDESKID', '77')
    API_LOGIN = os.getenv('API_LOGIN', 'test_login')
    
    # Админы (ваш ID)
    ADMINS_STR = os.getenv('ADMINS', '')
    ADMINS = []
    if ADMINS_STR:
        try:
            ADMINS = [int(admin_id.strip()) for admin_id in ADMINS_STR.split(',') if admin_id.strip()]
        except:
            ADMINS = []
    
    # Поддержка
    SUPPORT_USERNAME = os.getenv('SUPPORT_USERNAME', '@WinWinSupport')
    
    # Настройки
    MIN_DEPOSIT = 100
    DEPOSIT_TIMEOUT = 600
