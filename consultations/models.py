from django.db import models
from django.utils import timezone
from common.models import BaseModel


class Consultation(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Ожидание"),
        ("ongoing", "В процессе"),
        ("completed", "Завершено"),
        ("cancelled", "Отменено"),
        ("missed", "Пропущено"),
    ]
    
    patient = models.ForeignKey(
        "common.User", on_delete=models.CASCADE, related_name="consultations_as_patient", verbose_name="Пациент"
    )
    doctor = models.ForeignKey(
        "common.User", on_delete=models.CASCADE, related_name="consultations_as_doctor", verbose_name="Доктор"
    )
    meeting_id = models.CharField(max_length=255, unique=True, verbose_name="ID Видеозвонка")
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending", verbose_name="Статус"
    )
    is_urgent = models.BooleanField(default=False, verbose_name="Экстренность консультации")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Время начала")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="Время завершения")

    def start(self):
        """Marks consultation as ongoing and sets start time."""
        self.status = "ongoing"
        self.started_at = timezone.now()
        self.save()

    def end(self):
        """Marks consultation as completed and sets end time."""
        self.status = "completed"
        self.ended_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Видеозвонок {self.patient} с {self.doctor} - {self.get_status_display()} - {'Экстренная' if self.is_urgent else 'Не экстренная'}"

    class Meta:
        db_table = "consultations"
        verbose_name = "Консультация"
        verbose_name_plural = "Консультации"


class AIRecommendationLog(BaseModel):
    symptoms = models.TextField(verbose_name="Симптомы запроса")
    ai_raw_response = models.TextField(verbose_name="Сырой ответ AI")
    recommended_specialty = models.CharField(
        max_length=255, verbose_name="Рекомендованная специализация", null=True, blank=True
    )
    reason = models.TextField(verbose_name="Пояснение AI", null=True, blank=True)
    matched_doctor = models.ForeignKey(
        "common.User", on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Назначенный врач", related_name="ai_matches"
    )
    fallback_used = models.BooleanField(default=False, verbose_name="Использован fallback (терапевт)?")
    specialty_not_found = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Найденная AI специализация, но врач не найден"
    )
    urgency = models.CharField(
        max_length=10, choices=[("urgent", "Экстренная"), ("non_urgent", "Не экстренная")],
        default="non_urgent", verbose_name="Экстренность рекомендации AI"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI рекомендация: {self.recommended_specialty or 'не распознано'} ({self.created_at:%Y-%m-%d %H:%M})"

    class Meta:
        db_table = "consultations_ai_recommendation_logs"
        verbose_name = "Лог AI-рекомендации"
        verbose_name_plural = "Логи AI-рекомендаций"

