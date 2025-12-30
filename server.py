import asyncio
import logging
import threading
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Простой HTTP сервер для health check
async def health_handler(request):
    return web.Response(text="SofiaCash Bot is running")

async def index_handler(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SofiaCash Bot</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .status { color: green; font-size: 24px; margin: 20px; }
        </style>
    </head>
    <body>
        <h1>🤖 SofiaCash Bot</h1>
        <div class="status">✅ Бот работает</div>
        <p>Этот сервер нужен только для проверки здоровья.</p>
        <p>Основная работа происходит в Telegram.</p>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def start_http_server():
    """Запуск HTTP сервера"""
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/health', health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Используем порт из переменной окружения или 10000
    port = 10000
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"HTTP сервер запущен на порту {port}")
    logger.info(f"Health check: http://0.0.0.0:{port}/health")
    
    # Бесконечный цикл
    await asyncio.Future()

def run_bot():
    """Запуск бота в отдельном потоке"""
    import bot
    from aiogram import executor
    
    # Запускаем polling
    executor.start_polling(
        bot.dp,
        skip_updates=True,
        on_startup=bot.on_startup,
        on_shutdown=bot.on_shutdown
    )

def main():
    """Основная функция запуска"""
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("Бот запущен в отдельном потоке")
    
    # Запускаем HTTP сервер в основном потоке
    asyncio.run(start_http_server())

if __name__ == '__main__':
    main()
