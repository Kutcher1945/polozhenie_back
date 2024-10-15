from django.db import models
from .operation_card import OperationCard
from .fire_rank import FireRank


class Card101(models.Model):
    """Main model for Card 101 form."""
    # Адресная информация
    address = models.CharField(max_length=255, verbose_name="Адрес")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Долгота", blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="Широта", blank=True, null=True)

    # Информация об объекте
    object_name = models.CharField(max_length=255, verbose_name="Наименование объекта")
    operation_plan = models.CharField(max_length=255, verbose_name="Оперативный план", blank=True, null=True)
    constructive_features = models.TextField(verbose_name="Конструктивные особенности", blank=True, null=True)
    operation_card = models.ForeignKey(OperationCard, on_delete=models.SET_NULL, verbose_name="Оперативная карточка", null=True, blank=True)
    year_of_construction = models.IntegerField(verbose_name="Год постройки", blank=True, null=True)
    object_area = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Площадь объекта", blank=True, null=True)

    # Foreign key to district
    district = models.ForeignKey('address.CityDistrict', on_delete=models.SET_NULL, verbose_name="Район города", null=True, blank=True)

    # Foreign key to fire rank
    fire_rank = models.ForeignKey(FireRank, on_delete=models.SET_NULL, verbose_name="Ранг пожара", null=True, blank=True)

    # Дополнительная информация
    floors = models.IntegerField(verbose_name="Этажность", blank=True, null=True)
    fire_floor = models.IntegerField(verbose_name="На каком этаже пожар", blank=True, null=True)
    applicant_name = models.CharField(max_length=255, verbose_name="ФИО Заявителя", blank=True, null=True)
    applicant_phone = models.CharField(max_length=20, verbose_name="Телефон заявителя", blank=True, null=True)
    danger_to_people = models.CharField(max_length=20, choices=[
        ('yes', 'Да'),
        ('no', 'Нет'),
        ('unknown', 'Неизвестно')
    ], verbose_name="Опасность для людей", blank=True, null=True)
    additional_info = models.TextField(verbose_name="Дополнительная информация", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Card101 - {self.object_name}"

    class Meta:
        db_table = 'card101'
        verbose_name = "Карточка 101"
        verbose_name_plural = "Карточки 101"