from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .models import User, UserSession, PatientMedicalProfile


class UserSerializer(serializers.ModelSerializer):
    """
    Basic user serializer with core authentication and profile fields.
    Role-specific fields have been moved to dedicated profile models.
    """
    role_display = serializers.SerializerMethodField()
    gender_display = serializers.SerializerMethodField()
    language_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "first_name", "last_name", "phone", "email", "password", "role", "role_display",
            "birth_date", "gender", "gender_display", "address", "city", "language", "language_display"
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
    """
    Comprehensive user profile serializer that pulls data from profile models based on role.
    Dynamically includes role-specific fields from DoctorProfile, NurseProfile, PatientProfile, AdminProfile.
    """
    role_display = serializers.SerializerMethodField()
    gender_display = serializers.SerializerMethodField()
    language_display = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(source='created_at', read_only=True)

    # Role-specific fields
    profile_data = serializers.SerializerMethodField()
    clinic = serializers.SerializerMethodField()  # For backward compatibility with frontend

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'phone', 'email', 'role', 'role_display',
            'birth_date', 'gender', 'gender_display', 'address', 'city',
            'language', 'language_display', 'last_seen', 'date_joined',
            'clinic', 'profile_data'
        ]
        read_only_fields = ['email', 'role', 'date_joined', 'clinic']

    def get_clinic(self, obj):
        """
        Return clinic information from the user's profile (doctor, nurse, or admin).
        For backward compatibility with frontend expecting user.clinic.
        """
        try:
            if obj.role == 'doctor' and hasattr(obj, 'doctor_profile'):
                clinic = obj.doctor_profile.clinic
            elif obj.role == 'nurse' and hasattr(obj, 'nurse_profile'):
                clinic = obj.nurse_profile.clinic
            elif obj.role == 'admin' and hasattr(obj, 'admin_profile'):
                clinic = obj.admin_profile.clinic
            else:
                return None

            if clinic:
                return {
                    'id': clinic.id,
                    'name': clinic.name,
                    'address': getattr(clinic, 'address', None),
                    'city': getattr(clinic.city, 'name_ru', None) if hasattr(clinic, 'city') else None,
                }
            return None
        except:
            return None

    def get_profile_data(self, obj):
        """
        Return role-specific profile data from the appropriate profile model.
        """
        if obj.role == 'doctor':
            try:
                profile = obj.doctor_profile
                return {
                    'doctor_type': profile.doctor_type,
                    'clinic': {
                        'id': profile.clinic.id,
                        'name': profile.clinic.name,
                    } if profile.clinic else None,
                    'availability_status': profile.availability_status,
                    'availability_note': profile.availability_note,
                    'specialization': profile.specialization.name_ru if profile.specialization else None,
                }
            except:
                return None
        elif obj.role == 'nurse':
            try:
                profile = obj.nurse_profile
                return {
                    'nurse_type': profile.nurse_type,
                    'clinic': {
                        'id': profile.clinic.id,
                        'name': profile.clinic.name,
                    } if profile.clinic else None,
                    'availability_status': profile.availability_status,
                    'availability_note': profile.availability_note,
                    'specialization': profile.specialization.name_ru if profile.specialization else None,
                }
            except:
                return None
        elif obj.role == 'patient':
            try:
                profile = obj.patient_profile
                return {
                    'citizenship': profile.citizenship,
                    'marital_status': profile.marital_status,
                    'profession': profile.profession,
                }
            except:
                return None
        elif obj.role == 'admin':
            try:
                profile = obj.admin_profile
                return {
                    'admin_type': profile.admin_type,
                    'clinic': {
                        'id': profile.clinic.id,
                        'name': profile.clinic.name,
                    } if profile.clinic else None,
                    'is_super_admin': profile.is_super_admin,
                    'can_manage_staff': profile.can_manage_staff,
                    'can_manage_patients': profile.can_manage_patients,
                    'can_view_reports': profile.can_view_reports,
                    'can_manage_settings': profile.can_manage_settings,
                    'department': profile.department,
                }
            except:
                return None
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


class PatientMedicalProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for patient medical information.
    Includes display fields for better frontend presentation.
    """
    
    blood_type_display = serializers.SerializerMethodField()
    rhesus_factor_display = serializers.SerializerMethodField()
    fluorography_status_display = serializers.SerializerMethodField()
    immunization_status_display = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    last_modified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PatientMedicalProfile
        fields = [
            'id',
            'user',
            'patient_name',
            'blood_type',
            'blood_type_display',
            'rhesus_factor',
            'rhesus_factor_display',
            'fluorography_status',
            'fluorography_status_display',
            'fluorography_date',
            'immunization_status',
            'immunization_status_display',
            'immunization_date',
            'last_modified_by',
            'last_modified_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_modified_by']

    def get_blood_type_display(self, obj):
        return dict(User.BLOOD_TYPE_CHOICES).get(obj.blood_type, "Не указано") if obj.blood_type else "Не указано"

    def get_rhesus_factor_display(self, obj):
        return dict(User.RHESUS_FACTOR_CHOICES).get(obj.rhesus_factor, "Не указан") if obj.rhesus_factor else "Не указан"

    def get_fluorography_status_display(self, obj):
        return dict(User.FLUOROGRAPHY_STATUS_CHOICES).get(obj.fluorography_status, "Не указано") if obj.fluorography_status else "Не указано"

    def get_immunization_status_display(self, obj):
        return dict(User.IMMUNIZATION_STATUS_CHOICES).get(obj.immunization_status, "Не указано") if obj.immunization_status else "Не указано"

    def get_patient_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email

    def get_last_modified_by_name(self, obj):
        if obj.last_modified_by:
            return f"{obj.last_modified_by.first_name} {obj.last_modified_by.last_name}".strip() or obj.last_modified_by.email
        return None
