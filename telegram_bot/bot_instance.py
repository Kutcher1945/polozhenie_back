import os
from aiogram import Bot, Dispatcher
import logging

# Import handlers
from telegram_bot.handlers import (
    register_command_handlers,
    register_callback_handlers,
    register_message_handlers
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get token from environment variable (production-safe)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# BOT_TOKEN = "8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw" # Production token
# BOT_TOKEN  = "8283662927:AAEV_Q6T-NZbKPvxG4MIJsTOt03rfgxxFCc" # Development token
# Fallback to development token if not in production
if not BOT_TOKEN:
    BOT_TOKEN = "8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw"  # DEVELOPMENT FALLBACK
    logger.warning("⚠️ Using fallback DEVELOPMENT token. Set TELEGRAM_BOT_TOKEN env variable for production!")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not set and no fallback available")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Register all handlers
register_command_handlers(dp)
register_callback_handlers(dp)
register_message_handlers(dp)  # Must be last - catches all unhandled messages

# === Run polling safely ===
async def run_polling():
    """Start bot polling (safe for threads)."""
    try:
        logger.info("🚀 Starting Aiogram polling (handle_signals=False)...")
        await dp.start_polling(bot, handle_signals=False)
    except Exception as e:
        logger.error(f"❌ Bot polling error: {e}")
        raise
