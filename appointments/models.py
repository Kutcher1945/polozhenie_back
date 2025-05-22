from django.db import models
from common.models import BaseModel

class HomeAppointment(BaseModel):
    STATUS_CHOICES = [
        ('scheduled', 'Запланировано'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
    ]

    patient = models.ForeignKey(
        'common.User', on_delete=models.CASCADE, related_name='home_appointments', verbose_name="Пациент"
    )
    doctor = models.ForeignKey(
        'common.User', on_delete=models.CASCADE, related_name='home_doctor_appointments', verbose_name="Врач"
    )
    appointment_time = models.DateTimeField(verbose_name="Дата и время вызова")
    address = models.CharField(max_length=255, verbose_name="Адрес вызова")
    symptoms = models.TextField(blank=True, null=True, verbose_name="Симптомы")
    notes = models.TextField(blank=True, null=True, verbose_name="Заметки")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='scheduled', verbose_name="Статус"
    )

    class Meta:
        db_table = "appointment_home"
        verbose_name = "Вызов на дом"
        verbose_name_plural = "Вызовы на дом"
        ordering = ['-appointment_time']
        unique_together = ('doctor', 'appointment_time')

    def __str__(self):
        return f"{self.patient} вызов к {self.doctor} ({self.appointment_time.strftime('%d.%m.%Y %H:%M')})"