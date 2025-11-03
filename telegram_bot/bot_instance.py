import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import logging
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


logging.basicConfig(level=logging.INFO)

# ⚠️ You can keep the token hardcoded for testing, but in production use environment variables
BOT_TOKEN = "8586849826:AAG4bdQGrXgTW7LhH5U_s2b1sx3XRug6gJQ" # DEVELOPMENT
# BOT_TOKEN = "8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw" # PRODUCTION

if not BOT_TOKEN:
    raise ValueError("⚠️ BOT_TOKEN not set")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Handlers ===
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 Open Web App",
                    web_app=WebAppInfo(url="https://www.zhan.care/telegram-auth")  # Replace with your real URL
                )
            ]
        ]
    )

    await message.answer(
        "🤖 Bot is running with Django server!\n\nClick below to open the web app 👇",
        reply_markup=keyboard
    )

@dp.message()
async def echo(message: types.Message):
    await message.answer(f"You said: {message.text}")

# === Run polling safely ===
async def run_polling():
    """Start bot polling (safe for threads)."""
    print("🚀 Starting Aiogram polling (handle_signals=False)...")
    await dp.start_polling(bot, handle_signals=False)
