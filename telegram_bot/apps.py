from django.apps import AppConfig
import threading
import asyncio
import os
import logging

logger = logging.getLogger(__name__)


class TelegramBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telegram_bot'
    bot_thread = None

    def ready(self):
        """Start bot when Django is ready (production-safe)"""
        # Prevent duplicate startup during development auto-reload
        # RUN_MAIN is set by Django's runserver only after the first reload
        if os.environ.get('RUN_MAIN') == 'false':
            logger.info("⏭️ Skipping bot startup (pre-reload)")
            return

        # --- Telegram bot startup commented out temporarily ---
        # bot_enabled = os.environ.get('TELEGRAM_BOT_ENABLED', 'true').lower() == 'true'

        # if not bot_enabled:
        #     logger.info("⏸️ Telegram bot disabled (TELEGRAM_BOT_ENABLED=false)")
        #     return

        # # Check if already running
        # if TelegramBotConfig.bot_thread and TelegramBotConfig.bot_thread.is_alive():
        #     logger.info("🔄 Bot thread already running, skipping startup")
        #     return

        # logger.info("🤖 Starting Telegram bot...")

        # try:
        #     from telegram_bot.bot_instance import run_polling

        #     def start_bot():
        #         try:
        #             asyncio.run(run_polling())
        #         except Exception as e:
        #             logger.error(f"❌ Bot error: {e}")

        #     TelegramBotConfig.bot_thread = threading.Thread(
        #         target=start_bot,
        #         daemon=True,
        #         name="TelegramBotThread"
        #     )
        #     TelegramBotConfig.bot_thread.start()
        #     logger.info("✅ Telegram bot thread started successfully")

        # except Exception as e:
        #     logger.error(f"❌ Failed to start bot: {e}")
        logger.info("⏸️ Telegram bot startup is commented out")
