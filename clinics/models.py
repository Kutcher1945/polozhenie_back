from django.db import models
from django.contrib.gis.db import models as gis_models


class Country(models.Model):
    """Модель страны"""
    name_ru = models.CharField(
        max_length=255,
        verbose_name="Название (рус)"
    )
    name_kz = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name="Название (каз)"
    )
    code = models.CharField(
        max_length=3,
        null=True, blank=True,
        verbose_name="Код страны (ISO)"
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Удалён"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    point = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True, blank=True,
        verbose_name="Точка (центр страны)"
    )
    geometry = gis_models.GeometryField(
        geography=True,
        srid=4326,
        null=True, blank=True,
        verbose_name="Геометрия (границы)"
    )

    class Meta:
        db_table = "countries"
        verbose_name = "Страна"
        verbose_name_plural = "Страны"
        ordering = ["name_ru"]

    def __str__(self):
        return self.name_ru


class Region(models.Model):
    """Модель региона/области"""
    name_ru = models.CharField(
        max_length=255,
        verbose_name="Название (рус)"
    )
    name_kz = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name="Название (каз)"
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="regions",
        null=True, blank=True,
        verbose_name="Страна"
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Удалён"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    point = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True, blank=True,
        verbose_name="Точка (центр региона)"
    )
    geometry = gis_models.GeometryField(
        geography=True,
        srid=4326,
        null=True, blank=True,
        verbose_name="Геометрия (границы)"
    )

    class Meta:
        db_table = "regions"
        verbose_name = "Регион"
        verbose_name_plural = "Регионы"
        ordering = ["name_ru"]

    def __str__(self):
        return f"{self.name_ru}" + (f" ({self.country.name_ru})" if self.country else "")


class City(models.Model):
    """Модель города"""
    name_ru = models.CharField(
        max_length=255,
        verbose_name="Название (рус)"
    )
    name_kz = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name="Название (каз)"
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name="cities",
        null=True, blank=True,
        verbose_name="Регион"
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Удалён"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    point = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True, blank=True,
        verbose_name="Точка (центр города)"
    )
    geometry = gis_models.GeometryField(
        geography=True,
        srid=4326,
        null=True, blank=True,
        verbose_name="Геометрия (границы)"
    )

    class Meta:
        db_table = "cities"
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ["name_ru"]

    def __str__(self):
        return self.name_ru


class District(models.Model):
    """Модель района"""
    name_ru = models.CharField(
        max_length=255,
        verbose_name="Название (рус)"
    )
    name_kz = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name="Название (каз)"
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name="districts",
        null=True, blank=True,
        verbose_name="Город"
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Удалён"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    point = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True, blank=True,
        verbose_name="Точка (центр района)"
    )
    geometry = gis_models.GeometryField(
        geography=True,
        srid=4326,
        null=True, blank=True,
        verbose_name="Геометрия (границы)"
    )

    class Meta:
        db_table = "districts"
        verbose_name = "Район"
        verbose_name_plural = "Районы"
        ordering = ["name_ru"]

    def __str__(self):
        return f"{self.name_ru}" + (f" ({self.city.name_ru})" if self.city else "")


class Microdistrict(models.Model):
    """Модель микрорайона"""
    name_ru = models.CharField(
        max_length=255,
        verbose_name="Название (рус)"
    )
    name_kz = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name="Название (каз)"
    )
    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name="microdistricts",
        null=True, blank=True,
        verbose_name="Район"
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Удалён"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    point = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True, blank=True,
        verbose_name="Точка (центр микрорайона)"
    )
    geometry = gis_models.GeometryField(
        geography=True,
        srid=4326,
        null=True, blank=True,
        verbose_name="Геометрия (границы)"
    )

    class Meta:
        db_table = "microdistricts"
        verbose_name = "Микрорайон"
        verbose_name_plural = "Микрорайоны"
        ordering = ["name_ru"]

    def __str__(self):
        return f"{self.name_ru}" + (f" ({self.district.name_ru})" if self.district else "")


class Clinics(models.Model):
    name = models.CharField(
        max_length=512,
        db_index=True,
        verbose_name="Название"
    )
    description = models.TextField(
        null=True, blank=True,
        verbose_name="Описание"
    )

    address = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="Адрес"
    )
    address_comment = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="Комментарий к адресу"
    )

    postal_code = models.CharField(
        max_length=20, null=True, blank=True,
        verbose_name="Почтовый индекс"
    )

    microdistrict = models.ForeignKey(
        Microdistrict,
        on_delete=models.SET_NULL,
        related_name="clinics",
        null=True, blank=True,
        verbose_name="Микрорайон"
    )


    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        related_name="clinics",
        null=True, blank=True,
        verbose_name="Район"
    )


    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        related_name="clinics",
        null=True, blank=True,
        verbose_name="Город"
    )

    administrative_area = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="Административный округ"
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        related_name="clinics",
        null=True, blank=True,
        verbose_name="Регион"
    )

    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        related_name="clinics",
        null=True, blank=True,
        verbose_name="Страна"
    )

    working_hours = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="Часы работы"
    )
    time_zone = models.CharField(
        max_length=50, null=True, blank=True,
        verbose_name="Часовой пояс"
    )

    rating = models.FloatField(
        null=True, blank=True,
        verbose_name="Рейтинг"
    )
    review_count = models.IntegerField(
        null=True, blank=True,
        verbose_name="Количество отзывов"
    )

    # Соц. сети
    instagram = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="Instagram"
    )
    twitter = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="Twitter"
    )
    facebook = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="Facebook"
    )
    vkontakte = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="ВКонтакте"
    )
    viber = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="Viber"
    )
    youtube = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="YouTube"
    )
    skype = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name="Skype"
    )

    location = gis_models.PointField(
        geography=True,
        srid=4326,
        null=True, blank=True,
        verbose_name="Геолокация (Point, SRID=4326)"
    )

    gis2_url = models.CharField(
        max_length=500, null=True, blank=True,
        verbose_name="Ссылка 2ГИС"
    )

    # JSON поля
    categories = models.JSONField(
        null=True, blank=True,
        verbose_name="Категории"
    )
    phones = models.JSONField(
        null=True, blank=True,
        verbose_name="Телефоны"
    )
    emails = models.JSONField(
        null=True, blank=True,
        verbose_name="Email адреса"
    )
    websites = models.JSONField(
        null=True, blank=True,
        verbose_name="Веб-сайты"
    )
    whatsapp = models.JSONField(
        null=True, blank=True,
        verbose_name="WhatsApp"
    )

    class Meta:
        db_table = "clinics"
        verbose_name = "Клиника"
        verbose_name_plural = "Клиники"

    def __str__(self):
        return self.name
