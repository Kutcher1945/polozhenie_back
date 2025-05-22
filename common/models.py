from django.db import models
from rest_framework.authtoken.models import Token
from django.contrib.auth.hashers import check_password, make_password


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_deleted = models.BooleanField(default=False, verbose_name="Удалено")

    class Meta:
        abstract = True


class DoctorSpecialization(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Специализация")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Специализация врача"
        verbose_name_plural = "Специализации врачей"


class User(BaseModel):
    ROLE_CHOICES = [
        ('patient', 'Пациент'),
        ('doctor', 'Доктор'),
        ('admin', 'Администратор'),
    ]

    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="Телефон")
    password = models.CharField(max_length=255, verbose_name="Пароль")  # ✅ Must store hashed passwords!
    first_name = models.CharField(max_length=150, null=True, blank=True, verbose_name="Имя")
    last_name = models.CharField(max_length=150, null=True, blank=True, verbose_name="Фамилия")
    is_active = models.BooleanField(default=True, verbose_name="Активен")\
    # 🔧 Добавь вот это:
    is_staff = models.BooleanField(default=False, verbose_name="Сотрудник")
    is_superuser = models.BooleanField(default=False, verbose_name="Суперпользователь")
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='patient', verbose_name="Роль")

    def set_password(self, raw_password):
        """Hashes and saves the password"""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Verifies the password"""
        return check_password(raw_password, self.password)

    @property
    def is_authenticated(self):
        """Custom property to check authentication status"""
        return True 

    def __str__(self):
        return f"{self.email} - {self.get_role_display()}"

    class Meta:
        db_table = "common_users"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class Clinic(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Название клиники")
    address = models.TextField(null=True, blank=True, verbose_name="Адрес")
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Телефон")
    website = models.URLField(null=True, blank=True, verbose_name="Вебсайт")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Клиника"
        verbose_name_plural = "Клиники"


class DoctorProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.ForeignKey(DoctorSpecialization, on_delete=models.SET_NULL, null=True, blank=True)
    years_of_experience = models.PositiveIntegerField(null=True, blank=True, verbose_name="Опыт работы (лет)")
    clinics = models.ManyToManyField(Clinic, blank=True, related_name='doctors', verbose_name="Клиники")

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.specialization.name if self.specialization else 'Без специализации'}"

    class Meta:
        verbose_name = "Профиль доктора"
        verbose_name_plural = "Профили докторов"


class CustomToken(BaseModel):
    key = models.CharField(max_length=40, primary_key=True, default=Token.generate_key, editable=False)
    user = models.OneToOneField(
        User, 
        related_name='auth_token', 
        on_delete=models.CASCADE, 
        verbose_name="User"
    )

    class Meta:
        db_table = "common_authtoken"
        verbose_name = "Токен"
        verbose_name_plural = "Токены"

    def __str__(self):
        return self.key