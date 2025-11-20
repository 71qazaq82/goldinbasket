from aiogram import Bot, Dispatcher, executor, types

TOKEN = "8187938139:AAFnnRe4PzH9l6Vke4uuRG1oaLtRhereXug"

bot = Bot(TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer(f"Ваш Telegram ID: {msg.from_user.id}")

executor.start_polling(dp)
