from django.contrib.gis.db import models
from colorful.fields import RGBColorField

class Microsectors(models.Model):
    name_ru = models.CharField(max_length=100, verbose_name="Название на русском")
    name_kz = models.CharField(max_length=100, verbose_name="Название на казахском")
    line_color = RGBColorField(verbose_name="Цвет линии", help_text="Выберите цвет линии")
    fill_color = RGBColorField(verbose_name="Цвет заливки", help_text="Выберите цвет заливки")
    opacity = models.FloatField(verbose_name="Прозрачность", help_text="Прозрачность от 0 до 1")
    boundary = models.MultiPolygonField(verbose_name="Границы на карте", srid=4326)
    is_deleted = models.BooleanField(editable=False, default=False)
    created_at = models.DateTimeField(editable=False, auto_now=True)
    updated_at = models.DateTimeField(editable=False, auto_now=True)

    def __str__(self):
        return self.name_ru

    class Meta:
        db_table = 'address_microsectors'
        verbose_name = "Граница микроучастка"
        verbose_name_plural = "Границы микроучастков"