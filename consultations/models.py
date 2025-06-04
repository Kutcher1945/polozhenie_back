from django.db import models
from django.utils import timezone
from common.models import BaseModel

# Create your models here.
class Consultation(BaseModel):
    STATUS_CHOICES = [
        ("pending", "Ожидание"),
        ("ongoing", "В процессе"),
        ("completed", "Завершено"),
        ("cancelled", "Отменено"),
        ("missed", "Пропущено"),  # ✅ Add this line
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
        return f"Видеозвонок {self.patient} с {self.doctor} - {self.get_status_display()}"

    class Meta:
        db_table = "consultations"
        verbose_name = "Консультация"
        verbose_name_plural = "Консультации"