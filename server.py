import asyncio
from aiohttp import web
import threading
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальная переменная для хранения состояния
bot_status = "stopped"

async def handle_health(request):
    """Обработчик для health check"""
    global bot_status
    return web.Response(
        text=f"SofiaCash Bot\nStatus: {bot_status}\nHealth: OK",
        content_type='text/plain'
    )

async def handle_root(request):
    """Главная страница"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SofiaCash Bot</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
            .status { padding: 20px; background: #f0f0f0; border-radius: 10px; margin: 20px auto; max-width: 600px; }
            .green { color: green; }
            .blue { color: blue; }
        </style>
    </head>
    <body>
        <h1>🤖 SofiaCash Bot</h1>
        <div class="status">
            <h2 class="green">✅ Бот работает</h2>
            <p>Telegram бот для пополнения и вывода средств</p>
            <p><strong>Статус:</strong> <span id="status">running</span></p>
        </div>
        <p>Этот сервер нужен только для проверки здоровья (health check).</p>
        <p>Основная работа происходит в Telegram: <a href="https://t.me/SofiaCashBot" target="_blank">@SofiaCashBot</a></p>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

async def handle_start_bot(request):
    """Запуск бота (если нужно перезапустить)"""
    global bot_status
    bot_status = "starting"
    
    # Импортируем и запускаем бота в отдельном потоке
    import bot
    thread = threading.Thread(target=lambda: asyncio.run(bot.main()), daemon=True)
    thread.start()
    
    bot_status = "running"
    return web.Response(text="Bot started successfully", content_type='text/plain')

def run_http_server():
    """Запуск HTTP сервера"""
    app = web.Application()
    
    # Добавляем маршруты
    app.router.add_get('/', handle_root)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/start', handle_start_bot)
    
    # Получаем порт из переменной окружения или используем 10000
    port = int(8000)
    
    async def start():
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"HTTP сервер запущен на http://0.0.0.0:{port}")
        logger.info(f"Health check: http://0.0.0.0:{port}/health")
        
        # Бесконечный цикл чтобы сервер не завершался
        while True:
            await asyncio.sleep(3600)
    
    # Запускаем сервер
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start())

if __name__ == '__main__':
    # Запускаем HTTP сервер в отдельном потоке
    import threading
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Запускаем бота в основном потоке
    logger.info("Запуск SofiaCash Bot...")
    import bot
    asyncio.run(bot.main())
