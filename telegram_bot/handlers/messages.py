import logging
from aiogram import types, Dispatcher
from telegram_bot.keyboards import get_app_button_keyboard
from telegram_bot.utils import get_conversational_ai_response

logger = logging.getLogger(__name__)


async def handle_message(message: types.Message):
    """Handle all other messages with conversational AI"""
    user_message = message.text

    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, "typing")

    # Try to get AI response
    ai_response = await get_conversational_ai_response(user_message)

    # Create keyboard with app button (always shown)
    keyboard = get_app_button_keyboard()

    if ai_response:
        # AI response available
        await message.answer(
            ai_response,
            reply_markup=keyboard
        )
        logger.info(f"✅ AI response sent to user {message.from_user.id}")
    else:
        # AI unavailable - show friendly fallback
        await message.answer(
            f"Спасибо за сообщение! 💬\n\n"
            f"Я медицинский ассистент ZhanCare. К сожалению, сейчас я не могу обработать ваш запрос.\n\n"
            f"Для консультации с врачом откройте приложение ZhanCare.",
            reply_markup=keyboard
        )
        logger.info(f"ℹ️ Fallback response sent to user {message.from_user.id} (AI unavailable)")


def register_message_handlers(dp: Dispatcher):
    """Register all message handlers"""
    # This should be registered last as it catches all messages
    dp.message.register(handle_message)
