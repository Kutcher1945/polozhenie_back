from django.db import models
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: username})

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.password = make_password(None)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_deleted = models.BooleanField(default=False, verbose_name="Удалено")

    class Meta:
        abstract = True


class DoctorSpecialization(BaseModel):
    name_ru = models.CharField(max_length=255, unique=True, verbose_name="Специализация (RU)")
    name_kz = models.CharField(max_length=255, unique=True, verbose_name="Специализация (KZ)")
    name_en = models.CharField(max_length=255, unique=True, verbose_name="Specialization (EN)")

    def __str__(self):
        return self.name_ru  # Default to Russian name

    class Meta:
        db_table = "common_doctors_specialization"
        verbose_name = "Специализация врача"
        verbose_name_plural = "Специализации врачей"


class NurseSpecialization(BaseModel):
    name_ru = models.CharField(max_length=255, unique=True, verbose_name="Специализация (RU)")
    name_kz = models.CharField(max_length=255, unique=True, verbose_name="Специализация (KZ)")
    name_en = models.CharField(max_length=255, unique=True, verbose_name="Specialization (EN)")

    def __str__(self):
        return self.name_ru  # Default to Russian name

    class Meta:
        db_table = "common_nurses_specialization"
        verbose_name = "Специализация медсестры"
        verbose_name_plural = "Специализации медсестёр"


class User(BaseModel):
    ROLE_CHOICES = [
        ('patient', 'Пациент'),
        ('doctor', 'Доктор'),
        ('nurse', 'Медсестра'),
        ('admin', 'Администратор'),
    ]

    GENDER_CHOICES = [
        ('male', 'Мужской'),
        ('female', 'Женский'),
        ('other', 'Другой'),
    ]

    LANGUAGE_CHOICES = [
        ('kz', 'Казахский'),
        ('ru', 'Русский'),
        ('en', 'Английский'),
        ('other', 'Другой'),
    ]

    MARITAL_STATUS_CHOICES = [
        ('single', 'Не женат/не замужем'),
        ('married', 'Женат/замужем'),
        ('divorced', 'Разведен/разведена'),
        ('widowed', 'Вдовец/вдова'),
    ]

    BLOOD_TYPE_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]

    RHESUS_FACTOR_CHOICES = [
        ('positive', 'Положительный'),
        ('negative', 'Отрицательный'),
    ]

    FLUOROGRAPHY_STATUS_CHOICES = [
        ('normal', 'Норма'),
        ('abnormal', 'Отклонения'),
        ('pending', 'Ожидает результата'),
        ('expired', 'Просрочена'),
    ]

    IMMUNIZATION_STATUS_CHOICES = [
        ('up_to_date', 'Актуальная'),
        ('partial', 'Частичная'),
        ('expired', 'Просрочена'),
        ('none', 'Отсутствует'),
    ]

    # Основные поля
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="Телефон")
    password = models.CharField(max_length=255, verbose_name="Пароль")  # ✅ Must store hashed passwords!
    first_name = models.CharField(max_length=150, null=True, blank=True, verbose_name="Имя")
    last_name = models.CharField(max_length=150, null=True, blank=True, verbose_name="Фамилия")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    reset_code = models.CharField(max_length=10, blank=True, null=True)
    reset_code_created_at = models.DateTimeField(null=True, blank=True)
    is_staff = models.BooleanField(default=False, verbose_name="Сотрудник")
    is_superuser = models.BooleanField(default=False, verbose_name="Суперпользователь")
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='patient', verbose_name="Роль")

    # Персональные данные для профиля
    birth_date = models.DateField(null=True, blank=True, verbose_name="Дата рождения")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True, verbose_name="Пол")
    address = models.TextField(null=True, blank=True, verbose_name="Адрес")
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name="Город")
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='ru', null=True, blank=True, verbose_name="Язык")
    citizenship = models.CharField(max_length=100, default='Казахстан', null=True, blank=True, verbose_name="Гражданство")
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES, null=True, blank=True, verbose_name="Семейное положение")
    profession = models.CharField(max_length=255, null=True, blank=True, verbose_name="Профессия")

    # Медицинские данные
    blood_type = models.CharField(max_length=5, choices=BLOOD_TYPE_CHOICES, null=True, blank=True, verbose_name="Группа крови")
    rhesus_factor = models.CharField(max_length=10, choices=RHESUS_FACTOR_CHOICES, null=True, blank=True, verbose_name="Резус-фактор")
    fluorography_status = models.CharField(max_length=20, choices=FLUOROGRAPHY_STATUS_CHOICES, null=True, blank=True, verbose_name="Статус флюорографии")
    fluorography_date = models.DateField(null=True, blank=True, verbose_name="Дата флюорографии")
    immunization_status = models.CharField(max_length=20, choices=IMMUNIZATION_STATUS_CHOICES, null=True, blank=True, verbose_name="Статус иммунизации")
    immunization_date = models.DateField(null=True, blank=True, verbose_name="Дата последней иммунизации")

    # Врачебные поля
    doctor_type = models.CharField(max_length=150, null=True, blank=True, verbose_name="Тип врача")
    doctor_specialization = models.ForeignKey('DoctorSpecialization', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Специализация врача")

    # Медсестринские поля
    nurse_type = models.CharField(max_length=150, null=True, blank=True, verbose_name="Тип медсестры")
    nurse_specialization = models.ForeignKey('NurseSpecialization', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Специализация медсестры")

    # Клиника (для докторов и медсестер)
    clinic = models.ForeignKey(
        'clinics.Clinics',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members',
        verbose_name="Клиника"
    )

    # Статус доступности для докторов и медсестёр
    AVAILABILITY_CHOICES = [
        ('available', 'Доступен'),
        ('busy', 'Занят'),
        ('offline', 'Не работает'),
        ('break', 'На перерыве'),
    ]

    availability_status = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default='offline',
        null=True,
        blank=True,
        verbose_name="Статус доступности"
    )
    availability_note = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Заметка о доступности"
    )
    last_seen = models.DateTimeField(auto_now=True, verbose_name="Последний раз в сети")

    # Django authentication requirements
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    EMAIL_FIELD = 'email'
    
    objects = UserManager()

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

    @property
    def is_anonymous(self):
        """Always return False for authenticated users"""
        return False

    def get_username(self):
        """Return the username field value"""
        return getattr(self, self.USERNAME_FIELD)

    def has_perm(self, perm, obj=None):
        """Check if user has specific permission"""
        return self.is_superuser

    def has_module_perms(self, app_label):
        """Check if user has permissions for app"""
        return self.is_superuser

    def __str__(self):
        return f"{self.email} - {self.get_role_display()}"

    class Meta:
        db_table = "common_users"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"



class DoctorProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.ForeignKey(DoctorSpecialization, on_delete=models.SET_NULL, null=True, blank=True)
    years_of_experience = models.PositiveIntegerField(null=True, blank=True, verbose_name="Опыт работы (лет)")

    # Primary clinic - main workplace (optional, can work independently)
    clinic = models.ForeignKey(
        'clinics.Clinics',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_doctors',
        verbose_name="Основная клиника"
    )

    # Additional clinics - can work in multiple locations
    additional_clinics = models.ManyToManyField('clinics.Clinics', blank=True, related_name='doctors', verbose_name="Дополнительные клиники")

    @property
    def is_available_for_consultation(self):
        """Check if doctor is available for new consultations"""
        return self.user.availability_status == 'available'

    @property
    def availability_display(self):
        """Get display text for availability status"""
        choices = dict(self.user.AVAILABILITY_CHOICES)
        return choices.get(self.user.availability_status, 'Неизвестно') if self.user.availability_status else 'Неизвестно'

    def __str__(self):
        clinic_info = f" ({self.clinic.name})" if self.clinic else " (Независимый)"
        return f"{self.user.first_name} {self.user.last_name} - {self.specialization.name_ru if self.specialization else 'Без специализации'}{clinic_info}"

    class Meta:
        verbose_name = "Профиль доктора"
        verbose_name_plural = "Профили докторов"


class NurseProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='nurse_profile')
    specialization = models.ForeignKey(NurseSpecialization, on_delete=models.SET_NULL, null=True, blank=True)
    years_of_experience = models.PositiveIntegerField(null=True, blank=True, verbose_name="Опыт работы (лет)")

    # Primary clinic - main workplace (optional, can work independently)
    clinic = models.ForeignKey(
        'clinics.Clinics',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_nurses',
        verbose_name="Основная клиника"
    )

    # Additional clinics - can work in multiple locations
    additional_clinics = models.ManyToManyField('clinics.Clinics', blank=True, related_name='nurses', verbose_name="Дополнительные клиники")

    @property
    def is_available_for_consultation(self):
        """Check if nurse is available for new consultations"""
        return self.user.availability_status == 'available'

    @property
    def availability_display(self):
        """Get display text for availability status"""
        choices = dict(self.user.AVAILABILITY_CHOICES)
        return choices.get(self.user.availability_status, 'Неизвестно') if self.user.availability_status else 'Неизвестно'

    def __str__(self):
        clinic_info = f" ({self.clinic.name})" if self.clinic else " (Независимая)"
        return f"{self.user.first_name} {self.user.last_name} - {self.specialization.name_ru if self.specialization else 'Без специализации'}{clinic_info}"

    class Meta:
        verbose_name = "Профиль медсестры"
        verbose_name_plural = "Профили медсестёр"


class UserSession(BaseModel):
    """
    Tracks individual user sessions across devices.
    Each session has its own refresh token for multi-device support.
    """
    DEVICE_TYPE_CHOICES = [
        ('desktop', 'Desktop'),
        ('mobile', 'Mobile'),
        ('tablet', 'Tablet'),
        ('unknown', 'Unknown'),
    ]

    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name="Пользователь"
    )

    # JWT Token Identifier
    refresh_token_jti = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name="Refresh Token JTI"
    )

    # Device Information
    device_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Название устройства"
    )
    device_type = models.CharField(
        max_length=50,
        choices=DEVICE_TYPE_CHOICES,
        default='unknown',
        verbose_name="Тип устройства"
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name="User Agent"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP адрес"
    )

    # Session Metadata
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name="Последняя активность"
    )

    # Revocation
    is_revoked = models.BooleanField(
        default=False,
        verbose_name="Отозвана"
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата отзыва"
    )

    class Meta:
        db_table = "common_user_sessions"
        verbose_name = "Сессия пользователя"
        verbose_name_plural = "Сессии пользователей"
        ordering = ['-last_activity']

    def __str__(self):
        return f"{self.user.email} - {self.device_name or 'Unknown Device'}"

    def revoke(self):
        """Revoke this session."""
        from django.utils import timezone
        self.is_revoked = True
        self.revoked_at = timezone.now()
        self.save(update_fields=['is_revoked', 'revoked_at'])


# CustomToken has been migrated to standard DRF Token (authtoken_token table)
# Migration completed: 2025-12-05
# - 52 tokens successfully migrated
# - Old table 'common_authtoken' can be dropped manually if needed


# class ClinicalProtocol(models.Model):
#     name = models.TextField()
#     url = models.URLField(max_length=1000, unique=True)

#     year = models.PositiveSmallIntegerField()
#     medicine = models.CharField(max_length=255)

#     mkb = models.CharField(max_length=50)
#     mkb_codes = models.JSONField(default=list)

#     size = models.PositiveIntegerField(help_text="File size in bytes")
#     extension = models.CharField(max_length=10)

#     modified = models.DateTimeField()

#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         db_table = "clinical_protocols"
#         ordering = ["-year", "name"]

#     def __str__(self):
#         return self.name

#     class Meta:
#         db_table = "common_clinical_protocols"
#         verbose_name = "Клинический протокол"
#         verbose_name_plural = "Клинические протоколы"