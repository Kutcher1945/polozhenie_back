from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
from django.conf import settings
import os

def send_password_reset_email(email, code):
    subject = "🔐 Восстановление пароля – ZhanCare.Ai"
    text_content = f"Ваш код для восстановления пароля: {code}"

    html_content = f"""
    <div style="font-family: Arial, sans-serif; background-color: #f5f7fa; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background-color: #ffffff; border-radius: 12px; padding: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="cid:logo" alt="ZhanCare.Ai Logo" style="max-width: 120px; margin-bottom: 20px;" />
                <div style="font-size: 28px; font-weight: bold; color: #002762;">CSTI SAMGAU</div>
                <h2 style="color: #002762; margin-top: 10px;">Восстановление пароля</h2>
            </div>
            <p style="font-size: 16px; color: #333;">Здравствуйте,</p>
            <p style="font-size: 16px; color: #333;">
                Вы запросили восстановление пароля. Пожалуйста, используйте следующий код:
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <span style="display: inline-block; font-size: 24px; font-weight: bold; background: #002762; color: #ffffff; padding: 12px 24px; border-radius: 10px;">
                    {code}
                </span>
            </div>
            <p style="font-size: 14px; color: #666;">
                Этот код действует в течение 15 минут. Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.
            </p>
            <div style="margin-top: 40px; text-align: center; font-size: 12px; color: #aaa;">
                © 2025 ZhanCare.Ai
            </div>
        </div>
    </div>
    """

    # Create the email message
    msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
    msg.attach_alternative(html_content, "text/html")

    # Path to your logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logosaas.png')

    # Attach image if file exists
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo = MIMEImage(f.read())
            logo.add_header('Content-ID', '<logo>')  # matches src="cid:logo"
            logo.add_header('Content-Disposition', 'inline', filename='logosaas.png')
            msg.attach(logo)

    msg.send()
