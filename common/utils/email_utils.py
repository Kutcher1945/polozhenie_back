from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
from django.conf import settings
import os

def send_password_reset_email(email, code, reset_link=None):
    subject = "🔐 Восстановление пароля – ZhanCare.Ai"
    text_content = f"""Здравствуйте,

Вы запросили сброс пароля для аккаунта ZhanCare.Ai.
Ваш код: {code}

Если вы не отправляли этот запрос, просто проигнорируйте это письмо.
С уважением, команда ZhanCare.Ai
"""

    html_content = f"""
    <div style="font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; background-color: #f4f6f8; padding: 30px 0;">
      <div style="max-width: 600px; margin: auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.07);">
        
        <div style="background-color: #002762; padding: 32px 24px; text-align: center;">
          <img src="cid:logo" alt="ZhanCare.Ai" style="max-width: 150px; margin-bottom: 16px;" />
          <h1 style="color: #ffffff; font-size: 24px; margin: 0;">Сброс пароля</h1>
        </div>

        <div style="padding: 32px 28px; color: #333;">
          <p style="font-size: 16px; margin-bottom: 12px;">Здравствуйте,</p>
          <p style="font-size: 15px; color: #555; line-height: 1.6;">
            Мы получили запрос на сброс пароля для вашего аккаунта ZhanCare.Ai.
            Пожалуйста, используйте следующий код:
          </p>

          <div style="text-align: center; margin: 30px 0;">
            <span style="display: inline-block; font-size: 28px; font-weight: 600; background-color: #002762; color: #fff; padding: 16px 32px; border-radius: 8px; letter-spacing: 2px;">
              {code}
            </span>
          </div>

          {f'''
          <div style="text-align: center; margin: 24px 0;">
            <a href="{reset_link}" style="display: inline-block; background-color: #002762; color: #ffffff; text-decoration: none; padding: 14px 28px; font-size: 16px; border-radius: 6px;">
              Сбросить пароль
            </a>
          </div>
          <p style="font-size: 14px; color: #555; line-height: 1.5;">
            Если кнопка не работает, скопируйте и вставьте ссылку в адресную строку браузера:
            <br/><a href="{reset_link}" style="color: #002762; word-break: break-all;">{reset_link}</a>
          </p>
          ''' if reset_link else ''}

          <p style="font-size: 14px; color: #666; line-height: 1.5;">
            Срок действия кода: <strong>15 минут</strong>.
          </p>
          <p style="font-size: 14px; color: #666; line-height: 1.5;">
            Если вы не отправляли этот запрос, проигнорируйте это письмо.
          </p>
          <p style="font-size: 14px; color: #666; line-height: 1.5; margin-top: 30px;">
            Нужна помощь? Свяжитесь с нами: <a href="mailto:support@zhancare.ai" style="color: #002762;">marzipan9256@yandex.com</a>
          </p>
        </div>

        <div style="background-color: #f1f1f1; text-align: center; padding: 18px;">
          <a href="https://www.zhancare.ai" style="color: #002762; text-decoration: none; font-weight: bold; font-size: 14px;">
            Перейти на сайт ZhanCare.Ai
          </a>
        </div>

        <div style="background-color: #002762; color: #ffffff; text-align: center; font-size: 12px; padding: 16px;">
          © 2025 ZhanCare.Ai — Все права защищены.
        </div>
      </div>
    </div>
    """

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email]
    )
    msg.attach_alternative(html_content, "text/html")

    # Attach inline logo if it exists
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logosaas.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo = MIMEImage(f.read())
            logo.add_header('Content-ID', '<logo>')
            logo.add_header('Content-Disposition', 'inline', filename='logosaas.png')
            msg.attach(logo)

    msg.send()
