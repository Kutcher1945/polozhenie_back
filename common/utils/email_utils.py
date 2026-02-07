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


def send_welcome_email_with_password(email, password, sugar_level=None, systolic=None, diastolic=None):
    """Send welcome email with login credentials and optional health summary"""
    subject = "🎉 Добро пожаловать в ZhanCare.Ai – Ваш аккаунт создан"

    # Build health summary if provided
    health_section = ""
    if sugar_level is not None and systolic is not None and diastolic is not None:
        sugar = float(sugar_level)
        if sugar < 3.9:
            sugar_message = f"Уровень сахара ({sugar} ммоль/л) — ниже нормы"
            sugar_color = "#dc3545"
        elif sugar <= 5.5:
            sugar_message = f"Уровень сахара ({sugar} ммоль/л) — в норме"
            sugar_color = "#28a745"
        elif sugar <= 6.9:
            sugar_message = f"Уровень сахара ({sugar} ммоль/л) — повышен"
            sugar_color = "#ffc107"
        else:
            sugar_message = f"Уровень сахара ({sugar} ммоль/л) — высокий"
            sugar_color = "#dc3545"

        if systolic < 90 or diastolic < 60:
            pressure_message = f"Давление ({systolic}/{diastolic}) — пониженное"
            pressure_color = "#17a2b8"
        elif systolic <= 120 and diastolic <= 80:
            pressure_message = f"Давление ({systolic}/{diastolic}) — в норме"
            pressure_color = "#28a745"
        elif systolic <= 139 or diastolic <= 89:
            pressure_message = f"Давление ({systolic}/{diastolic}) — немного повышено"
            pressure_color = "#ffc107"
        else:
            pressure_message = f"Давление ({systolic}/{diastolic}) — высокое"
            pressure_color = "#dc3545"

        health_section = f"""
          <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 24px 0;">
            <h3 style="color: #333; margin: 0 0 16px 0; font-size: 16px;">📋 Результаты вашей анкеты:</h3>
            <p style="margin: 8px 0; font-size: 14px;">
              <span style="display: inline-block; width: 10px; height: 10px; background-color: {sugar_color}; border-radius: 50%; margin-right: 8px;"></span>
              {sugar_message}
            </p>
            <p style="margin: 8px 0; font-size: 14px;">
              <span style="display: inline-block; width: 10px; height: 10px; background-color: {pressure_color}; border-radius: 50%; margin-right: 8px;"></span>
              {pressure_message}
            </p>
          </div>
        """

    text_content = f"""Здравствуйте!

Добро пожаловать в ZhanCare.Ai!

Ваш аккаунт успешно создан. Данные для входа:
Email: {email}
Пароль: {password}

Войдите в личный кабинет: https://zhan.care/login

С уважением, команда ZhanCare.Ai
"""

    html_content = f"""
    <div style="font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; background-color: #f4f6f8; padding: 30px 0;">
      <div style="max-width: 600px; margin: auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.07);">

        <div style="background-color: #002762; padding: 32px 24px; text-align: center;">
          <img src="cid:logo" alt="ZhanCare.Ai" style="max-width: 150px; margin-bottom: 16px;" />
          <h1 style="color: #ffffff; font-size: 24px; margin: 0;">Добро пожаловать!</h1>
        </div>

        <div style="padding: 32px 28px; color: #333;">
          <p style="font-size: 16px; margin-bottom: 12px;">Здравствуйте,</p>
          <p style="font-size: 15px; color: #555; line-height: 1.6;">
            Ваш аккаунт ZhanCare.Ai успешно создан. Используйте следующие данные для входа:
          </p>

          <div style="background-color: #002762; padding: 20px; border-radius: 8px; margin: 24px 0;">
            <p style="color: #ffffff; margin: 8px 0; font-size: 14px;">
              <strong>Email:</strong> {email}
            </p>
            <p style="color: #ffffff; margin: 8px 0; font-size: 14px;">
              <strong>Пароль:</strong> {password}
            </p>
          </div>

          {health_section}

          <div style="text-align: center; margin: 24px 0;">
            <a href="https://zhan.care/login" style="display: inline-block; background-color: #002762; color: #ffffff; text-decoration: none; padding: 14px 28px; font-size: 16px; border-radius: 6px;">
              Войти в личный кабинет
            </a>
          </div>

          <p style="font-size: 14px; color: #666; line-height: 1.5;">
            Рекомендуем сменить пароль после первого входа в систему.
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


def send_consultation_created_email(patient_email, patient_name, doctor_name, access_code, consultation_link, scheduled_at=None):
    """
    Send email notification when a consultation is created
    Includes access code and direct link to join the consultation
    """
    subject = "📅 Консультация назначена – ZhanCare.Ai"

    # Format scheduled time if provided
    scheduled_info = ""
    if scheduled_at:
        from datetime import datetime
        if isinstance(scheduled_at, str):
            scheduled_dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
        else:
            scheduled_dt = scheduled_at
        scheduled_info = f"""
          <p style="font-size: 15px; color: #555; line-height: 1.6;">
            <strong>Запланированное время:</strong> {scheduled_dt.strftime('%d.%m.%Y в %H:%M')}
          </p>
        """

    text_content = f"""Здравствуйте, {patient_name}!

Ваша консультация с врачом {doctor_name} успешно создана.

Код доступа к консультации: {access_code}

Для подключения к консультации используйте ссылку: {consultation_link}

С уважением, команда ZhanCare.Ai
"""

    html_content = f"""
    <div style="font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; background-color: #f4f6f8; padding: 30px 0;">
      <div style="max-width: 600px; margin: auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.07);">

        <div style="background-color: #002762; padding: 32px 24px; text-align: center;">
          <img src="cid:logo" alt="ZhanCare.Ai" style="max-width: 150px; margin-bottom: 16px;" />
          <h1 style="color: #ffffff; font-size: 24px; margin: 0;">Консультация назначена</h1>
        </div>

        <div style="padding: 32px 28px; color: #333;">
          <p style="font-size: 16px; margin-bottom: 12px;">Здравствуйте, {patient_name}!</p>
          <p style="font-size: 15px; color: #555; line-height: 1.6;">
            Ваша видеоконсультация с <strong>{doctor_name}</strong> успешно создана.
          </p>

          {scheduled_info}

          <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 24px 0; text-align: center;">
            <p style="font-size: 14px; color: #666; margin-bottom: 8px;">Код доступа к консультации:</p>
            <span style="display: inline-block; font-size: 32px; font-weight: 600; background-color: #002762; color: #fff; padding: 16px 32px; border-radius: 8px; letter-spacing: 4px;">
              {access_code}
            </span>
            <p style="font-size: 13px; color: #888; margin-top: 12px;">Сохраните этот код для входа в консультацию</p>
          </div>

          <div style="text-align: center; margin: 24px 0;">
            <a href="{consultation_link}" style="display: inline-block; background-color: #28a745; color: #ffffff; text-decoration: none; padding: 14px 28px; font-size: 16px; border-radius: 6px; font-weight: 600;">
              🎥 Присоединиться к консультации
            </a>
          </div>

          <p style="font-size: 14px; color: #555; line-height: 1.5;">
            Если кнопка не работает, скопируйте и вставьте ссылку в адресную строку браузера:
            <br/><a href="{consultation_link}" style="color: #002762; word-break: break-all;">{consultation_link}</a>
          </p>

          <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px 16px; margin: 24px 0;">
            <p style="font-size: 14px; color: #856404; margin: 0; line-height: 1.5;">
              💡 <strong>Совет:</strong> Подключитесь за 5-10 минут до начала консультации, чтобы проверить камеру и микрофон.
            </p>
          </div>

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
        to=[patient_email]
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


def send_consultation_reminder_email(patient_email, patient_name, doctor_name, access_code, consultation_link, scheduled_at):
    """
    Send reminder email 10 minutes before consultation starts
    """
    from datetime import datetime

    # Format scheduled time
    if isinstance(scheduled_at, str):
        scheduled_dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
    else:
        scheduled_dt = scheduled_at

    subject = "⏰ Напоминание: Консультация через 10 минут – ZhanCare.Ai"

    text_content = f"""Здравствуйте, {patient_name}!

Напоминаем, что через 10 минут начнётся ваша консультация с врачом {doctor_name}.

Время начала: {scheduled_dt.strftime('%d.%m.%Y в %H:%M')}
Код доступа: {access_code}

Подключиться к консультации: {consultation_link}

С уважением, команда ZhanCare.Ai
"""

    html_content = f"""
    <div style="font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; background-color: #f4f6f8; padding: 30px 0;">
      <div style="max-width: 600px; margin: auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.07);">

        <div style="background: linear-gradient(135deg, #002762 0%, #004d9c 100%); padding: 32px 24px; text-align: center;">
          <img src="cid:logo" alt="ZhanCare.Ai" style="max-width: 150px; margin-bottom: 16px;" />
          <div style="display: inline-block; background-color: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 20px; margin-bottom: 12px;">
            <span style="color: #ffffff; font-size: 14px; font-weight: 600;">⏰ Через 10 минут</span>
          </div>
          <h1 style="color: #ffffff; font-size: 24px; margin: 8px 0 0 0;">Напоминание о консультации</h1>
        </div>

        <div style="padding: 32px 28px; color: #333;">
          <p style="font-size: 16px; margin-bottom: 12px;">Здравствуйте, {patient_name}!</p>
          <p style="font-size: 15px; color: #555; line-height: 1.6;">
            Напоминаем, что через <strong style="color: #dc3545;">10 минут</strong> начнётся ваша видеоконсультация с <strong>{doctor_name}</strong>.
          </p>

          <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 24px 0;">
            <p style="font-size: 14px; color: #666; margin: 8px 0;">
              <strong>📅 Время начала:</strong> {scheduled_dt.strftime('%d.%m.%Y в %H:%M')}
            </p>
            <p style="font-size: 14px; color: #666; margin: 8px 0;">
              <strong>👨‍⚕️ Врач:</strong> {doctor_name}
            </p>
          </div>

          <div style="background-color: #002762; padding: 20px; border-radius: 8px; margin: 24px 0; text-align: center;">
            <p style="font-size: 14px; color: #ffffff; margin-bottom: 8px; opacity: 0.9;">Код доступа:</p>
            <span style="display: inline-block; font-size: 28px; font-weight: 600; color: #fff; letter-spacing: 3px;">
              {access_code}
            </span>
          </div>

          <div style="text-align: center; margin: 24px 0;">
            <a href="{consultation_link}" style="display: inline-block; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: #ffffff; text-decoration: none; padding: 16px 32px; font-size: 18px; border-radius: 8px; font-weight: 600; box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);">
              🎥 Присоединиться сейчас
            </a>
          </div>

          <p style="font-size: 14px; color: #555; line-height: 1.5;">
            Если кнопка не работает, скопируйте и вставьте ссылку:
            <br/><a href="{consultation_link}" style="color: #002762; word-break: break-all;">{consultation_link}</a>
          </p>

          <div style="background-color: #d1ecf1; border-left: 4px solid #0c5460; padding: 12px 16px; margin: 24px 0;">
            <p style="font-size: 14px; color: #0c5460; margin: 0; line-height: 1.5;">
              📱 <strong>Убедитесь что:</strong> Камера и микрофон включены, а интернет-соединение стабильное.
            </p>
          </div>

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
        to=[patient_email]
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
