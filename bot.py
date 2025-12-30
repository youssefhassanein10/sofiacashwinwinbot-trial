import logging
from aiogram import Bot, Dispatcher, executor, types
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("✅ Бот работает! (aiogram 2)")

if __name__ == "__main__":
    print("BOT STARTED")
    executor.start_polling(dp, skip_updates=True)
