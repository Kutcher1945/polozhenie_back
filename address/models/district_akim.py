from __future__ import unicode_literals
from django.db import models
from django.contrib.gis.db import models


class CityDistrictAkim(models.Model):
    id = models.IntegerField(primary_key=True)
    name_ru = models.CharField(max_length=255, verbose_name='Фото акима')
    name_kz = models.CharField(max_length=255, verbose_name='Фото акима')
    akim_img = models.CharField(max_length=255, verbose_name='Фото акима')
    date_of_appointment = models.DateField(verbose_name='Фото акима')
    date_of_dismissal = models.DateField(verbose_name='Фото акима')
    created_at = models.DateTimeField(verbose_name="Created At", auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(verbose_name="Updated At", auto_now=True, editable=False)

    def __str__(self):
        return self.name_ru

    class Meta:
        db_table = 'address_city_district_akims'
        verbose_name = "Аким города или района города"
        verbose_name_plural = "Акимы городов или районов городов"