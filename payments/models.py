from django.db import models
from common.models import BaseModel


class HomeAppointmentKaspiPayment(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачено'),
        ('cancelled', 'Отменено'),
        ('failed', 'Ошибка'),
    ]

    appointment = models.OneToOneField(
        'appointments.HomeAppointment',
        on_delete=models.CASCADE,
        related_name='kaspi_payment',
        verbose_name="Вызов на дом"
    )
    customer = models.ForeignKey(
        'common.User',
        on_delete=models.CASCADE,
        related_name='kaspi_home_payments',
        verbose_name="Клиент (Пациент)"
    )
    payment_id = models.CharField(max_length=64, unique=True, verbose_name="ID платежа Kaspi")
    mpp_payment_id = models.CharField(max_length=64, verbose_name="ID в системе ZhanCare")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма оплаты")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name="Статус оплаты"
    )
    receipt_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на чек (Kaspi)")
    receipt_pdf = models.URLField(blank=True, null=True, verbose_name="PDF чека (Kaspi)")

    class Meta:
        db_table = "payments_kaspi_home_appointments"
        ordering = ['-created_at']
        verbose_name = "Платеж Kaspi"
        verbose_name_plural = "Платежи Kaspi"

    def __str__(self):
        return f"Kaspi | #{self.payment_id} | {self.amount}₸ | {self.get_status_display()}"

    @property
    def is_paid(self) -> bool:
        return self.status == 'paid'
