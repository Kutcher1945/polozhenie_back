from django.db import models
from common.models import BaseModel

class HomeAppointment(BaseModel):
    STATUS_CHOICES = [
        ('scheduled', 'Запланировано'),
        ('assigned', 'Назначено медсестре'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
    ]

    patient = models.ForeignKey(
        'common.User', on_delete=models.CASCADE, related_name='home_appointments', verbose_name="Пациент"
    )
    doctor = models.ForeignKey(
        'common.User', on_delete=models.SET_NULL, related_name='home_doctor_appointments',
        null=True, blank=True, verbose_name="Врач"
    )
    nurse = models.ForeignKey(
        'common.User', on_delete=models.SET_NULL, related_name='home_nurse_appointments',
        null=True, blank=True, verbose_name="Медсестра"
    )
    appointment_time = models.DateTimeField(verbose_name="Дата и время вызова")
    address = models.CharField(max_length=255, verbose_name="Адрес вызова")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Широта")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Долгота")
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

    def __str__(self):
        if self.doctor:
            return f"{self.patient} вызов к {self.doctor} ({self.appointment_time.strftime('%d.%m.%Y %H:%M')})"
        elif self.nurse:
            return f"{self.patient} вызов медсестре {self.nurse} ({self.appointment_time.strftime('%d.%m.%Y %H:%M')})"
        else:
            return f"{self.patient} вызов на дом ({self.appointment_time.strftime('%d.%m.%Y %H:%M')})"