from __future__ import unicode_literals
from django.db import models
from django.contrib.gis.db import models
from .district_akim import CityDistrictAkim


class CityDistrict(models.Model):
    id = models.BigAutoField(primary_key=True)
    name_kz = models.CharField(max_length=255, verbose_name='Название на казахском')
    name_ru = models.CharField(max_length=255, verbose_name='Название на русском')
    response_name_kz = models.CharField(max_length=255, verbose_name='Произношение на казахском')
    response_name_ru = models.CharField(max_length=255, verbose_name='Произношение на русском')
    gerb_img = models.CharField(max_length=255, verbose_name='Герб')
    akim = models.ForeignKey(CityDistrictAkim, models.DO_NOTHING, verbose_name="Аким", blank=True, null=True)
    geometry = models.MultiPolygonField(verbose_name="Геометрия", blank=True, null=True)
    marker = models.PointField(verbose_name="Маркер", blank=True, null=True)
    created_at = models.DateTimeField(verbose_name="Created At", auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(verbose_name="Updated At", auto_now=True, editable=False)

    def __str__(self):
        return self.name_ru

    class Meta:
        db_table = 'address_city_districts'
        verbose_name = "Район города"
        verbose_name_plural = "Районы городов"