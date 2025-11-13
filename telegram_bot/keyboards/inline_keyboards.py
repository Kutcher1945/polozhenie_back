from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard with all service buttons"""
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
    return keyboard


def get_app_button_keyboard() -> InlineKeyboardMarkup:
    """Simple keyboard with just the app button"""
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
    return keyboard
