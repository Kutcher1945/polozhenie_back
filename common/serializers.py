from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .models import User, UserSession


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.SerializerMethodField()
    gender_display = serializers.SerializerMethodField()
    language_display = serializers.SerializerMethodField()
    marital_status_display = serializers.SerializerMethodField()
    blood_type_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "first_name", "last_name", "phone", "email", "password", "role", "role_display",
            "birth_date", "gender", "gender_display", "address", "city", "language", "language_display",
            "citizenship", "marital_status", "marital_status_display", "profession", "blood_type", "blood_type_display"
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def get_role_display(self, obj):
        return dict(User.ROLE_CHOICES).get(obj.role, "Неизвестно")

    def get_gender_display(self, obj):
        return dict(User.GENDER_CHOICES).get(obj.gender, "Не указано") if obj.gender else "Не указано"

    def get_language_display(self, obj):
        if not obj.language:
            return "Не указано"
        # Handle both list (JSONField) and string formats
        if isinstance(obj.language, list):
            choices_dict = dict(User.LANGUAGE_CHOICES)
            return ", ".join([choices_dict.get(lang, lang) for lang in obj.language])
        # Fallback for single string value
        return dict(User.LANGUAGE_CHOICES).get(obj.language, "Не указано")

    def get_marital_status_display(self, obj):
        return dict(User.MARITAL_STATUS_CHOICES).get(obj.marital_status, "Не указано") if obj.marital_status else "Не указано"

    def get_blood_type_display(self, obj):
        return dict(User.BLOOD_TYPE_CHOICES).get(obj.blood_type, "Не указано") if obj.blood_type else "Не указано"


    def validate_email(self, value):
        # Check if updating existing user - exclude current user from uniqueness check
        user_id = self.instance.id if self.instance else None
        if User.objects.filter(email=value).exclude(id=user_id).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone(self, value):
        if value:  # Only validate if phone is provided
            # Check if updating existing user - exclude current user from uniqueness check
            user_id = self.instance.id if self.instance else None
            if User.objects.filter(phone=value).exclude(id=user_id).exists():
                raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def create(self, validated_data):
        return User.objects.create(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile details."""
    role_display = serializers.SerializerMethodField()
    gender_display = serializers.SerializerMethodField()
    language_display = serializers.SerializerMethodField()
    marital_status_display = serializers.SerializerMethodField()
    blood_type_display = serializers.SerializerMethodField()
    rhesus_factor_display = serializers.SerializerMethodField()
    fluorography_status_display = serializers.SerializerMethodField()
    immunization_status_display = serializers.SerializerMethodField()
    availability_status_display = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(source='created_at', read_only=True)
    clinic = serializers.SerializerMethodField()
    clinic_id = serializers.IntegerField(source='clinic.id', read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'phone', 'email', 'role', 'role_display',
            'birth_date', 'gender', 'gender_display', 'address', 'city',
            'language', 'language_display', 'citizenship', 'marital_status',
            'marital_status_display', 'profession', 'blood_type', 'blood_type_display',
            'rhesus_factor', 'rhesus_factor_display', 'fluorography_status', 'fluorography_status_display',
            'fluorography_date', 'immunization_status', 'immunization_status_display', 'immunization_date',
            'availability_status', 'availability_status_display', 'availability_note', 'last_seen',
            'date_joined', 'clinic', 'clinic_id'
        ]
        read_only_fields = ['email', 'role', 'date_joined', 'clinic', 'clinic_id']

    def get_clinic(self, obj):
        """Return clinic information if user has a clinic assigned."""
        if obj.clinic:
            return {
                'id': obj.clinic.id,
                'name': obj.clinic.name,
                'address': obj.clinic.address if hasattr(obj.clinic, 'address') else None,
            }
        return None

    def get_role_display(self, obj):
        return dict(User.ROLE_CHOICES).get(obj.role, "Неизвестно")

    def get_gender_display(self, obj):
        return dict(User.GENDER_CHOICES).get(obj.gender, "Не указано") if obj.gender else "Не указано"

    def get_language_display(self, obj):
        if not obj.language:
            return "Не указано"
        # Handle both list (JSONField) and string formats
        if isinstance(obj.language, list):
            choices_dict = dict(User.LANGUAGE_CHOICES)
            return ", ".join([choices_dict.get(lang, lang) for lang in obj.language])
        # Fallback for single string value
        return dict(User.LANGUAGE_CHOICES).get(obj.language, "Не указано")

    def get_marital_status_display(self, obj):
        return dict(User.MARITAL_STATUS_CHOICES).get(obj.marital_status, "Не указано") if obj.marital_status else "Не указано"

    def get_blood_type_display(self, obj):
        return dict(User.BLOOD_TYPE_CHOICES).get(obj.blood_type, "Не указано") if obj.blood_type else "Не указано"

    def get_rhesus_factor_display(self, obj):
        return dict(User.RHESUS_FACTOR_CHOICES).get(obj.rhesus_factor, "Не указан") if obj.rhesus_factor else "Не указан"

    def get_fluorography_status_display(self, obj):
        return dict(User.FLUOROGRAPHY_STATUS_CHOICES).get(obj.fluorography_status, "Не указана") if obj.fluorography_status else "Не указана"

    def get_immunization_status_display(self, obj):
        return dict(User.IMMUNIZATION_STATUS_CHOICES).get(obj.immunization_status, "Не указано") if obj.immunization_status else "Не указано"

    def get_availability_status_display(self, obj):
        return dict(User.AVAILABILITY_CHOICES).get(obj.availability_status, "Не указано") if obj.availability_status else "Не указано"

    def validate_birth_date(self, value):
        """Validate that birth date is not in the future and user is at least 1 year old."""
        if value:
            from datetime import date, timedelta
            today = date.today()
            if value > today:
                raise serializers.ValidationError("Дата рождения не может быть в будущем.")
            if value > today - timedelta(days=365):
                raise serializers.ValidationError("Возраст должен быть не менее 1 года.")
        return value

    def validate_phone(self, value):
        """Validate phone number format and uniqueness."""
        if value:
            import re
            # Remove all non-digit characters for validation
            cleaned_phone = re.sub(r'\D', '', value)
            if not cleaned_phone.startswith('7') or len(cleaned_phone) != 11:
                raise serializers.ValidationError("Введите корректный номер телефона в формате +7XXXXXXXXXX")

            # Check uniqueness, excluding current user
            user_id = self.instance.id if self.instance else None
            if User.objects.filter(phone=value).exclude(id=user_id).exists():
                raise serializers.ValidationError("Пользователь с таким номером телефона уже существует.")
        return value

    def validate_first_name(self, value):
        """Validate first name."""
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Имя должно содержать минимум 2 символа.")
        return value.strip() if value else value

    def validate_last_name(self, value):
        """Validate last name."""
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Фамилия должна содержать минимум 2 символа.")
        return value.strip() if value else value

    def validate_address(self, value):
        """Validate address."""
        if value and len(value.strip()) < 5:
            raise serializers.ValidationError("Адрес должен содержать минимум 5 символов.")
        return value.strip() if value else value

    def validate_city(self, value):
        """Validate city name."""
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Название города должно содержать минимум 2 символа.")
        return value.strip() if value else value

    def validate_profession(self, value):
        """Validate profession."""
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Профессия должна содержать минимум 2 символа.")
        return value.strip() if value else value

    def validate_citizenship(self, value):
        """Validate citizenship."""
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Гражданство должно содержать минимум 2 символа.")
        return value.strip() if value else value


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for user sessions."""

    class Meta:
        model = UserSession
        fields = [
            'id',
            'device_name',
            'device_type',
            'ip_address',
            'last_activity',
            'created_at',
        ]
        read_only_fields = fields


def get_client_ip(request):
    """Extract client IP from request."""
    if request is None:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def parse_device_info(user_agent_string):
    """Parse user agent string to determine device type and name."""
    try:
        from user_agents import parse
        user_agent = parse(user_agent_string)

        # Determine device type
        if user_agent.is_mobile:
            device_type = 'mobile'
        elif user_agent.is_tablet:
            device_type = 'tablet'
        elif user_agent.is_pc:
            device_type = 'desktop'
        else:
            device_type = 'unknown'

        # Generate device name
        device_name = f"{user_agent.browser.family} on {user_agent.os.family}"

        return device_type, device_name
    except Exception:
        return 'unknown', 'Unknown Device'


def create_jwt_tokens_for_user(user, request=None, device_name=None):
    """
    Create JWT tokens for a user and register the session.
    Returns dict with access_token, refresh_token, and session_id.
    """
    # Parse device information
    user_agent_string = ''
    if request:
        user_agent_string = request.META.get('HTTP_USER_AGENT', '')

    device_type, auto_device_name = parse_device_info(user_agent_string)

    # Use provided device name or auto-detected one
    final_device_name = device_name if device_name else auto_device_name

    # Get IP address
    ip_address = get_client_ip(request)

    # Generate refresh token
    refresh = RefreshToken.for_user(user)
    refresh_jti = str(refresh['jti'])

    # Create session record
    session = UserSession.objects.create(
        user=user,
        refresh_token_jti=refresh_jti,
        device_name=final_device_name,
        device_type=device_type,
        user_agent=user_agent_string,
        ip_address=ip_address,
    )

    # Add session JTI to access token for validation
    access = refresh.access_token
    access['session_jti'] = refresh_jti

    return {
        'access_token': str(access),
        'refresh_token': str(refresh),
        'session_id': session.id,
    }


def refresh_jwt_tokens(refresh_token_string):
    """
    Refresh JWT tokens using a refresh token.
    Validates session and rotates tokens.
    Returns dict with access_token and refresh_token.
    """
    # Decode the refresh token
    old_refresh = RefreshToken(refresh_token_string)
    old_jti = str(old_refresh['jti'])

    # Validate session exists and is not revoked
    try:
        session = UserSession.objects.get(
            refresh_token_jti=old_jti,
            is_revoked=False,
            is_deleted=False
        )
    except UserSession.DoesNotExist:
        raise serializers.ValidationError('Session not found or has been revoked')

    # Blacklist old refresh token
    old_refresh.blacklist()

    # Create new tokens
    new_refresh = RefreshToken.for_user(session.user)
    new_jti = str(new_refresh['jti'])

    # Update session with new JTI
    session.refresh_token_jti = new_jti
    session.last_activity = timezone.now()
    session.save(update_fields=['refresh_token_jti', 'last_activity', 'updated_at'])

    # Add session JTI to access token
    new_access = new_refresh.access_token
    new_access['session_jti'] = new_jti

    return {
        'access_token': str(new_access),
        'refresh_token': str(new_refresh),
    }
