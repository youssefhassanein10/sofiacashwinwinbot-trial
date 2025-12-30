from aiohttp import web
import asyncio
from bot import dp, bot
import threading

# Простой HTTP сервер для проверки здоровья
async def health_check(request):
    return web.Response(text="Bot is running")

def run_http_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    
    async def start_server():
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 10000)
        await site.start()
        print("HTTP сервер запущен на порту 10000")
        await asyncio.Future()  # Бесконечный цикл
    
    asyncio.run(start_server())

# Запуск в отдельном потоке
def start_http_in_thread():
    thread = threading.Thread(target=run_http_server, daemon=True)
    thread.start()

if __name__ == '__main__':
    start_http_in_thread()
    
    # Запуск бота
    from aiogram import executor
    import bot
    
    executor.start_polling(bot.dp, skip_updates=True)
