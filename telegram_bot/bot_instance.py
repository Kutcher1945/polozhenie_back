import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import logging
import requests
import json
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp, ReplyKeyboardMarkup, KeyboardButton


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get token from environment variable (production-safe)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# BOT_TOKEN = "8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw" # Production token
# BOT_TOKEN  = "8586849826:AAG4bdQGrXgTW7LhH5U_s2b1sx3XRug6gJQ" # Development token
# Fallback to development token if not in production
if not BOT_TOKEN:
    BOT_TOKEN = "8364913089:AAG5rK07-jHVgf1Uspgyf1sgXnkrKXH0ngw"  # DEVELOPMENT FALLBACK
    logger.warning("⚠️ Using fallback DEVELOPMENT token. Set TELEGRAM_BOT_TOKEN env variable for production!")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not set and no fallback available")

# Function to get Mistral API key (lazy loading from Django settings)
def get_mistral_api_key():
    """Get Mistral API key from Django settings"""
    try:
        from django.conf import settings
        api_key = getattr(settings, 'MISTRAL_API_KEY', None)
        if api_key:
            logger.info("✅ Mistral API key loaded from Django settings")
        else:
            logger.warning("⚠️ MISTRAL_API_KEY not found in Django settings")
        return api_key
    except Exception as e:
        logger.error(f"❌ Error loading Mistral API key: {e}")
        return None

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Helper Functions ===
async def get_conversational_ai_response(user_message: str):
    """Get conversational AI response for any user message"""
    # Get API key from Django settings
    MISTRAL_API_KEY = get_mistral_api_key()

    if not MISTRAL_API_KEY:
        logger.warning("⚠️ MISTRAL_API_KEY not available, AI response disabled")
        return None

    system_prompt = """
    You are a friendly and helpful medical assistant for ZhanCare, a telemedicine platform in Kazakhstan.

    Your role:
    - Answer medical and health questions in a clear, simple way
    - Be warm, conversational and empathetic
    - Always respond in Russian language
    - Keep responses short and concise (2-3 sentences)
    - Provide general health information only, no specific diagnoses
    - For serious symptoms, suggest consulting a doctor
    - For greetings, respond warmly

    Guidelines:
    - Be natural and friendly
    - Use simple language
    - No emojis unless greeting
    - No HTML formatting
    - Keep it brief and helpful
    """

    try:
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "open-mistral-nemo",
            "temperature": 0.7,
            "top_p": 1,
            "max_tokens": 300,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
        }

        # Send request
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post("https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers)
        )

        response.raise_for_status()
        ai_reply = response.json()["choices"][0]["message"]["content"].strip()

        return ai_reply

    except Exception as e:
        logger.error(f"❌ Conversational AI error: {e}")
        return None

# === Handlers ===
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    """Welcome message with beautiful design"""
    user_name = message.from_user.first_name or "друг"

    # Create beautiful inline keyboard
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏥 Открыть ZhanCare",
                    web_app=WebAppInfo(url="https://www.zhan.care/telegram-auth")
                )
            ],
            [
                InlineKeyboardButton(
                    text="📞 Видео Консультация",
                    web_app=WebAppInfo(url="https://www.zhan.care/telegram-auth")
                ),
                InlineKeyboardButton(
                    text="🏠 Вызов на дом",
                    web_app=WebAppInfo(url="https://www.zhan.care/telegram-auth")
                )
            ],
            [
                InlineKeyboardButton(
                    text="💊 Анализы",
                    web_app=WebAppInfo(url="https://www.zhan.care/telegram-auth")
                ),
                InlineKeyboardButton(
                    text="📋 Медкарта",
                    web_app=WebAppInfo(url="https://www.zhan.care/telegram-auth")
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ О сервисе",
                    callback_data="about"
                ),
                InlineKeyboardButton(
                    text="📞 Поддержка",
                    callback_data="support"
                )
            ]
        ]
    )

    welcome_message = f"""
👋 <b>Здравствуйте, {user_name}!</b>

Добро пожаловать в <b>ZhanCare</b> — вашу современную медицинскую платформу! 🏥

<b>🎯 Наши услуги:</b>

📞 <b>Видео Консультация</b>
Онлайн консультации с врачами

🏠 <b>Вызов врача на дом</b>
Профессиональная помощь у вас дома

💊 <b>Анализы и обследования</b>
Запись и результаты в одном месте

📋 <b>Электронная медкарта</b>
Вся история болезни под рукой

✨ <b>Нажмите "Открыть ZhanCare" для начала работы!</b>
"""

    await message.answer(
        welcome_message,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "about")
async def about_callback(callback: types.CallbackQuery):
    """About service information"""
    about_text = """
<b>🏥 О ZhanCare</b>

ZhanCare — это современная телемедицинская платформа, которая делает медицинскую помощь доступной для каждого.

<b>✨ Почему выбирают нас:</b>

✅ Консультации с квалифицированными врачами
✅ Быстрая запись и удобное расписание
✅ Безопасное хранение медицинских данных
✅ Доступные цены и прозрачность
✅ Поддержка 24/7

<b>🌐 Наш сайт:</b> www.zhan.care
<b>📧 Email:</b> support@zhan.care
"""

    await callback.message.answer(about_text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "support")
async def support_callback(callback: types.CallbackQuery):
    """Support contact information"""
    support_text = """
<b>📞 Служба поддержки</b>

Мы всегда готовы помочь вам!

<b>📱 Контакты:</b>
• WhatsApp: +7 (775) 824-96-86
• Telegram: @zhancare_support
• Email: support@zhan.care

<b>⏰ Часы работы:</b>
Пн-Пт: 9:00 - 20:00
Сб-Вс: 10:00 - 18:00

<b>🚨 Экстренная помощь:</b>
Доступна 24/7 через приложение

Напишите нам, и мы ответим в ближайшее время! 💬
"""

    await callback.message.answer(support_text, parse_mode="HTML")
    await callback.answer()

@dp.message()
async def echo(message: types.Message):
    """Handle all other messages with conversational AI"""
    user_message = message.text

    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, "typing")

    # Try to get AI response
    ai_response = await get_conversational_ai_response(user_message)

    # Create keyboard with app button (always shown)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏥 Открыть ZhanCare",
                    web_app=WebAppInfo(url="https://www.zhan.care/telegram-auth")
                )
            ]
        ]
    )

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

# === Run polling safely ===
async def run_polling():
    """Start bot polling (safe for threads)."""
    try:
        logger.info("🚀 Starting Aiogram polling (handle_signals=False)...")
        await dp.start_polling(bot, handle_signals=False)
    except Exception as e:
        logger.error(f"❌ Bot polling error: {e}")
        raise
