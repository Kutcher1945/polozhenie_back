from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from common.models import BaseModel


class TimeSlot(BaseModel):
    """
    TimeSlot model for scheduling non-urgent consultations
    """
    doctor = models.ForeignKey(
        "common.User", on_delete=models.CASCADE, related_name="available_timeslots",
        verbose_name="Доктор"
    )
    start_time = models.DateTimeField(verbose_name="Время начала")
    end_time = models.DateTimeField(verbose_name="Время окончания")
    is_available = models.BooleanField(default=True, verbose_name="Доступен")
    max_consultations = models.PositiveIntegerField(default=1, verbose_name="Максимум консультаций")
    booked_consultations = models.PositiveIntegerField(default=0, verbose_name="Забронированные консультации")

    # Recurring slot settings
    is_recurring = models.BooleanField(default=False, verbose_name="Повторяющийся слот")
    recurrence_type = models.CharField(
        max_length=10,
        choices=[
            ("daily", "Ежедневно"),
            ("weekly", "Еженедельно"),
            ("monthly", "Ежемесячно")
        ],
        null=True, blank=True, verbose_name="Тип повторения"
    )
    recurrence_end_date = models.DateField(null=True, blank=True, verbose_name="Дата окончания повторения")

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Время начала должно быть раньше времени окончания")

        if self.booked_consultations > self.max_consultations:
            raise ValidationError("Забронированные консультации не могут превышать максимум")

    def is_fully_booked(self):
        """Check if timeslot is fully booked"""
        return self.booked_consultations >= self.max_consultations

    def can_book(self):
        """Check if timeslot can be booked"""
        return self.is_available and not self.is_fully_booked() and self.start_time > timezone.now()

    def book_consultation(self):
        """Book a consultation in this timeslot"""
        if not self.can_book():
            raise ValidationError("Этот временной слот недоступен для бронирования")

        self.booked_consultations += 1
        if self.is_fully_booked():
            self.is_available = False
        self.save()

    def cancel_booking(self):
        """Cancel a booking in this timeslot"""
        if self.booked_consultations > 0:
            self.booked_consultations -= 1
            if not self.is_fully_booked():
                self.is_available = True
            self.save()

    @classmethod
    def get_available_slots(cls, doctor=None, start_date=None, end_date=None):
        """Get available timeslots with filters"""
        queryset = cls.objects.filter(
            is_available=True,
            start_time__gt=timezone.now()
        )

        if doctor:
            queryset = queryset.filter(doctor=doctor)

        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)

        if end_date:
            queryset = queryset.filter(start_time__date__lte=end_date)

        return queryset.order_by('start_time')

    def __str__(self):
        return f"{self.doctor} - {self.start_time.strftime('%Y-%m-%d %H:%M')} ({'Доступен' if self.can_book() else 'Занят'})"

    class Meta:
        db_table = "consultation_timeslots"
        verbose_name = "Временной слот"
        verbose_name_plural = "Временные слоты"
        ordering = ['start_time']
        unique_together = ['doctor', 'start_time', 'end_time']


class Consultation(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Ожидание"),
        ("ongoing", "В процессе"),
        ("completed", "Завершено"),
        ("cancelled", "Отменено"),
        ("missed", "Пропущено"),
        ("scheduled", "Запланировано"),  # New status for scheduled consultations
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

    # Timeslot relationship (only for non-urgent consultations)
    timeslot = models.ForeignKey(
        TimeSlot, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="consultations", verbose_name="Временной слот"
    )

    # AI recommendation relationship
    ai_recommendation = models.ForeignKey(
        "AIRecommendationLog", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="consultations", verbose_name="AI рекомендация"
    )

    # Scheduled time (for timeslot consultations)
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name="Запланированное время")

    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Время начала")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="Время завершения")

    def clean(self):
        """Validate consultation constraints"""
        if self.is_urgent and self.timeslot:
            raise ValidationError("Экстренные консультации не могут иметь временной слот")

        if not self.is_urgent and not self.timeslot and self.status == "scheduled":
            raise ValidationError("Неэкстренные консультации должны иметь временной слот")

        if self.timeslot and self.scheduled_at:
            if not (self.timeslot.start_time <= self.scheduled_at <= self.timeslot.end_time):
                raise ValidationError("Запланированное время должно быть в пределах временного слота")

    def schedule_with_timeslot(self, timeslot, scheduled_time=None):
        """Schedule consultation with a specific timeslot"""
        if self.is_urgent:
            raise ValidationError("Экстренные консультации не могут быть запланированы")

        if not timeslot.can_book():
            raise ValidationError("Временной слот недоступен для бронирования")

        # Use timeslot start time if no specific time provided
        if not scheduled_time:
            scheduled_time = timeslot.start_time

        self.timeslot = timeslot
        self.scheduled_at = scheduled_time
        self.status = "scheduled"

        # Book the timeslot
        timeslot.book_consultation()
        self.save()

    def cancel_schedule(self):
        """Cancel scheduled consultation and free up timeslot"""
        if self.timeslot and self.status == "scheduled":
            self.timeslot.cancel_booking()
            self.timeslot = None
            self.scheduled_at = None
            self.status = "cancelled"
            self.save()

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

    def is_scheduled_soon(self, minutes=15):
        """Check if consultation is scheduled within the next X minutes"""
        if not self.scheduled_at:
            return False

        now = timezone.now()
        return now <= self.scheduled_at <= now + timedelta(minutes=minutes)

    @classmethod
    def create_urgent_consultation(cls, patient, doctor, ai_recommendation=None):
        """Create an urgent consultation (no timeslot needed)"""
        consultation = cls.objects.create(
            patient=patient,
            doctor=doctor,
            is_urgent=True,
            ai_recommendation=ai_recommendation,
            meeting_id=f"urgent-{timezone.now().strftime('%Y%m%d%H%M%S')}-{patient.id}",
            status="pending"
        )
        return consultation

    @classmethod
    def create_scheduled_consultation(cls, patient, doctor, timeslot, ai_recommendation=None, scheduled_time=None):
        """Create a scheduled consultation with timeslot"""
        consultation = cls.objects.create(
            patient=patient,
            doctor=doctor,
            is_urgent=False,
            ai_recommendation=ai_recommendation,
            meeting_id=f"scheduled-{timezone.now().strftime('%Y%m%d%H%M%S')}-{patient.id}"
        )

        consultation.schedule_with_timeslot(timeslot, scheduled_time)
        return consultation

    def __str__(self):
        urgency_text = "Экстренная" if self.is_urgent else "Не экстренная"
        schedule_text = f" | Запланировано на {self.scheduled_at.strftime('%Y-%m-%d %H:%M')}" if self.scheduled_at else ""
        return f"Видеозвонок {self.patient} с {self.doctor} - {self.get_status_display()} - {urgency_text}{schedule_text}"

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

