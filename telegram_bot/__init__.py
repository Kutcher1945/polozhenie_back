# Bot startup is now handled by apps.py (TelegramBotConfig.ready())
# This ensures proper initialization in both development and production

default_app_config = 'telegram_bot.apps.TelegramBotConfig'
