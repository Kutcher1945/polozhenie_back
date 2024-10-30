from django.contrib.gis.db import models

class FireStations(models.Model):
    name_ru = models.CharField(max_length=255, null=True, blank=True, verbose_name="Название на русском")
    name_kz = models.CharField(max_length=255, null=True, blank=True, verbose_name="Название на казахском")
    old_name_ru = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название (старое) на русском")
    old_name_kz = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название (старое) на казахском")
    use_in_recommendations = models.BooleanField(default=False, verbose_name="Использовать в рекомендациях")
    use_in_records = models.BooleanField(default=False, verbose_name="Использовать в строевых")
    district = models.ForeignKey('address.CityDistrict', on_delete=models.SET_NULL, verbose_name="Район города", null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=1, verbose_name="Сортировка")
    address = models.CharField(max_length=255, verbose_name="Адрес")
    location = models.PointField(geography=True, verbose_name="Местоположение")  # For map location (coordinates)
    is_deleted = models.BooleanField(editable=False, default=False)
    created_at = models.DateTimeField(editable=False, auto_now=True)
    updated_at = models.DateTimeField(editable=False, auto_now=True)
    
    def __str__(self):
        return self.name_ru

    class Meta:
        verbose_name = "Пожарная часть"
        verbose_name_plural = "Пожарные части"
        db_table = 'card101_fire_stations'

    
