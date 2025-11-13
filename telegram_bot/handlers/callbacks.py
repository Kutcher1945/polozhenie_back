from aiogram import types, Dispatcher


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


def register_callback_handlers(dp: Dispatcher):
    """Register all callback handlers"""
    dp.callback_query.register(about_callback, lambda c: c.data == "about")
    dp.callback_query.register(support_callback, lambda c: c.data == "support")
