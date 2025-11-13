from aiogram import types, Dispatcher
from aiogram.filters import Command
from telegram_bot.keyboards import get_main_menu_keyboard


async def start_cmd(message: types.Message):
    """Welcome message with beautiful design"""
    user_name = message.from_user.first_name or "друг"

    # Get the main menu keyboard
    keyboard = get_main_menu_keyboard()

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


def register_command_handlers(dp: Dispatcher):
    """Register all command handlers"""
    dp.message.register(start_cmd, Command("start"))
