from django.db import models


class OperationCard(models.Model):
    """Dropdown for the 'Оперативная карточка' field."""
    name_ru = models.CharField(max_length=255, null=True, blank=True)
    name_kz = models.CharField(max_length=255, null=True, blank=True)
    is_deleted = models.BooleanField(editable=False, default=False)
    created_at = models.DateTimeField(editable=False, auto_now=True)
    updated_at = models.DateTimeField(editable=False, auto_now=True)

    def __str__(self):
        return self.name_ru

    class Meta:
        db_table = 'card101_operation_card'
        verbose_name = "Оперативная карточка"
        verbose_name_plural = "Оперативные карточки"
