import threading
import asyncio
import os

def start_bot():
    from telegram_bot.bot_instance import run_polling
    asyncio.run(run_polling())

if os.environ.get("RUN_MAIN") == "true":
    print("🤖 Starting Aiogram bot in background thread...")
    threading.Thread(target=start_bot, daemon=True).start()
