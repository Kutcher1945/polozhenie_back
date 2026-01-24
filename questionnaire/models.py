from django.db import models
from django.conf import settings


class HealthQuestionnaire(models.Model):
    """Model to store health questionnaire responses"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='health_questionnaires',
        verbose_name="Пользователь"
    )
    sugar_level = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Уровень сахара (ммоль/л)"
    )
    systolic_pressure = models.PositiveIntegerField(
        verbose_name="Систолическое давление (мм рт. ст.)"
    )
    diastolic_pressure = models.PositiveIntegerField(
        verbose_name="Диастолическое давление (мм рт. ст.)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        db_table = "questionnaire_health"
        verbose_name = "Анкета здоровья"
        verbose_name_plural = "Анкеты здоровья"
        ordering = ['-created_at']

    def __str__(self):
        return f"Анкета {self.user.email} от {self.created_at.strftime('%d.%m.%Y')}"

    @property
    def sugar_status(self):
        """Evaluate sugar level status"""
        level = float(self.sugar_level)
        if level < 3.9:
            return "low"  # Гипогликемия
        elif level <= 5.5:
            return "normal"  # Норма
        elif level <= 6.9:
            return "elevated"  # Повышенный (преддиабет)
        else:
            return "high"  # Высокий (диабет)

    @property
    def pressure_status(self):
        """Evaluate blood pressure status"""
        systolic = self.systolic_pressure
        diastolic = self.diastolic_pressure

        if systolic < 90 or diastolic < 60:
            return "low"  # Гипотония
        elif systolic <= 120 and diastolic <= 80:
            return "normal"  # Норма
        elif systolic <= 139 or diastolic <= 89:
            return "elevated"  # Повышенное
        else:
            return "high"  # Гипертония
