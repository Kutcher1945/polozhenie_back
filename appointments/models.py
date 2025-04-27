from django.db import models
from common.models import BaseModel


class Appointment(BaseModel):
    STATUS_CHOICES = [
        ('scheduled', 'Запланировано'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
    ]

    patient = models.ForeignKey(
        'common.User', on_delete=models.CASCADE, related_name='appointments', verbose_name="Пациент"
    )
    doctor = models.ForeignKey(
        'common.User', on_delete=models.CASCADE, related_name='doctor_appointments', verbose_name="Врач"
    )
    appointment_time = models.DateTimeField(verbose_name="Дата и время приема")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='scheduled', verbose_name="Статус"
    )
    symptoms = models.TextField(blank=True, null=True, verbose_name="Симптомы")
    notes = models.TextField(blank=True, null=True, verbose_name="Заметки")

    class Meta:
        db_table = "appointment"
        verbose_name = "Запись на прием"
        verbose_name_plural = "Записи на прием"
        ordering = ['-appointment_time']
        unique_together = ('doctor', 'appointment_time')

    def __str__(self):
        return f"{self.patient} к {self.doctor} ({self.appointment_time.strftime('%d.%m.%Y %H:%M')})"
