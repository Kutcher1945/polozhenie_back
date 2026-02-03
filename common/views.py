import logging
from drf_yasg import openapi
from django.conf import settings
from django.utils import timezone
import random
import string
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from .models import User, DoctorSpecialization, NurseSpecialization, DoctorProfile, NurseProfile, UserSession
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    UserSerializer, UserProfileSerializer, UserSessionSerializer,
    create_jwt_tokens_for_user, refresh_jwt_tokens
)
from .permissions import IsDoctor, IsAdmin, IsNurse
from .utils.email_utils import send_password_reset_email
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def csrf_cookie_view(request):
    return JsonResponse({"message": "CSRF cookie set"})

class UserViewSet(ModelViewSet):
    queryset = User.objects.none()  # ✅ No default access to users
    serializer_class = UserSerializer
    permission_classes = []  # ✅ No permissions by default - each action defines its own

    def get_permissions(self):
        """
        Override permissions per action
        """
        if self.action in ['register', 'login', 'logout', 'forgot_password', 'verify_reset_code', 'reset_password', 'get_available_doctors', 'get_profile_choices']:
            # Public endpoints - no authentication required
            return []
        else:
            # All other endpoints require authentication
            return [IsAuthenticated()]

    def list(self):
        """
        Disable listing all users - security risk
        """
        return Response(
            {"error": "Listing users is not allowed"},
            status=status.HTTP_403_FORBIDDEN
        )

    def retrieve(self, request, pk=None):
        """
        Disable retrieving individual users - security risk
        """
        return Response(
            {"error": "Direct user access is not allowed"},
            status=status.HTTP_403_FORBIDDEN
        )

    def update(self, request, pk=None):
        """
        Disable updating users through this endpoint
        """
        return Response(
            {"error": "User updates not allowed through this endpoint"},
            status=status.HTTP_403_FORBIDDEN
        )

    def partial_update(self, request, pk=None):
        """
        Disable partial updating users through this endpoint
        """
        return Response(
            {"error": "User updates not allowed through this endpoint"},
            status=status.HTTP_403_FORBIDDEN
        )

    def destroy(self, request, pk=None):
        """
        Disable deleting users through this endpoint
        """
        return Response(
            {"error": "User deletion not allowed through this endpoint"},
            status=status.HTTP_403_FORBIDDEN
        )

    
    @swagger_auto_schema(
        operation_description="Register a new user",
        request_body=UserSerializer,
        responses={
            201: "User registered successfully!",
            400: "Validation error",
            409: "User with the given email or phone already exists."
        },
    )
    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        """Handles user registration with role support."""

        logger.debug("📥 Incoming registration data: %s", request.data)

        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            logger.debug("✅ Serializer valid: %s", serializer.validated_data)

            email = serializer.validated_data["email"]
            phone = serializer.validated_data["phone"]
            role = serializer.validated_data.get("role", "patient")

            if User.objects.filter(Q(email=email) | Q(phone=phone)).exists():
                logger.warning("⚠️ Duplicate user attempted: %s / %s", email, phone)
                return Response(
                    {"error": "A user with this email or phone already exists."},
                    status=status.HTTP_409_CONFLICT,
                )

            serializer.validated_data["password"] = make_password(serializer.validated_data["password"])
            user = serializer.save()

            logger.info("🆕 User registered: %s", user)

            return Response(
                {"message": "Registration successful!", "user": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        logger.error("❌ Validation error: %s", serializer.errors)
        return Response(
            {"error": "Validation error", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @swagger_auto_schema(
        operation_description="User login with JWT tokens",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="User's email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="User's password"),
                "device_name": openapi.Schema(type=openapi.TYPE_STRING, description="Optional device name"),
            },
            required=["email", "password"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "access_token": openapi.Schema(type=openapi.TYPE_STRING),
                    "refresh_token": openapi.Schema(type=openapi.TYPE_STRING),
                    "user": openapi.Schema(type=openapi.TYPE_OBJECT),
                    "session_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            ),
            401: "Invalid credentials",
            403: "Account is inactive"
        },
    )
    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        """Handles user login using email and password with JWT tokens."""

        email = request.data.get("email", "").strip()
        password = request.data.get("password")
        device_name = request.data.get("device_name", "")

        print("🔹 Login attempt for email:", email)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({"error": "Неправильный E-mail или пароль."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({"error": "Неправильный E-mail или пароль."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "Account is inactive. Please contact support."}, status=status.HTTP_403_FORBIDDEN)

        # Create JWT tokens and session
        tokens = create_jwt_tokens_for_user(user, request, device_name)

        # Use UserProfileSerializer to include all profile fields
        user_serializer = UserProfileSerializer(user)

        return Response(
            {
                "message": "Login successful!",
                "user": user_serializer.data,
                "access_token": tokens['access_token'],
                "refresh_token": tokens['refresh_token'],
                "session_id": tokens['session_id'],
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_description="Logout and revoke current session",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh_token": openapi.Schema(type=openapi.TYPE_STRING, description="Refresh token to revoke"),
            },
        ),
        responses={200: "Logged out successfully"},
    )
    @action(detail=False, methods=["post"], url_path="logout")
    def logout(self, request):
        """Logout and revoke the current session."""
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                jti = str(token['jti'])

                # Revoke the session
                UserSession.objects.filter(
                    refresh_token_jti=jti
                ).update(is_revoked=True, revoked_at=timezone.now())

                # Blacklist the token
                token.blacklist()

            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning(f"Logout error: {e}")
            return Response({"message": "Logged out"}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
    operation_description="Send password reset link or code to user's email",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email"],
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING, description="User's email"),
        },
    ),
    responses={
        200: "Password reset instructions sent",
        404: "User not found",
    },
    )
    @action(detail=False, methods=["post"], url_path="forgot-password")
    def forgot_password(self, request):
        email = request.data.get("email", "").strip()

        try:
            user = User.objects.get(email__iexact=email)
            print(f"Found user for password reset: {user}")

            # Generate a reset code and timestamp
            reset_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            user.reset_code = reset_code
            user.reset_code_created_at = timezone.now()  # you need to add this field in the model
            user.save()

            # 🔥 Use HTML email helper instead of raw send_mail
            send_password_reset_email(email, reset_code)

            return Response(
                {"message": "Password reset instructions sent to your email."},
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

    @swagger_auto_schema(
    operation_description="Verify reset code sent to user's email",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email", "reset_code"],
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING),
            "reset_code": openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
    responses={
        200: "Code is valid",
        400: "Invalid or expired code",
    },
    )
    @action(detail=False, methods=["post"], url_path="verify-reset-code")
    def verify_reset_code(self, request):
        email = request.data.get("email", "").strip()
        reset_code = request.data.get("reset_code", "").strip().upper()

        if not email or not reset_code:
            return Response({"error": "Email и код обязательны."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email, reset_code__iexact=reset_code)
    
            if user.reset_code_created_at and user.reset_code_created_at < timezone.now() - timezone.timedelta(minutes=15):
                return Response({"error": "Код сброса истёк. Запросите новый."}, status=status.HTTP_400_BAD_REQUEST)
    
            return Response({"message": "Код подтверждён."}, status=status.HTTP_200_OK)
    
        except User.DoesNotExist:
            return Response({"error": "Неверный код или email."}, status=status.HTTP_400_BAD_REQUEST)
    

    @swagger_auto_schema(
    operation_description="Reset password using reset code",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email", "reset_code", "new_password"],
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING),
            "reset_code": openapi.Schema(type=openapi.TYPE_STRING),
            "new_password": openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
    responses={200: "Password updated successfully"},
    )
    @action(detail=False, methods=["post"], url_path="reset-password")
    def reset_password(self, request):
        email = request.data.get("email", "").strip()
        reset_code = request.data.get("reset_code", "").strip()
        new_password = request.data.get("new_password", "").strip()

        # 🔍 Debug incoming data
        print("📥 Incoming reset password request:")
        print("Email:", email)
        print("Reset Code:", reset_code)
        print("New Password (len):", len(new_password))

        if not email or not reset_code or not new_password:
            print("❌ Missing fields in request.")
            return Response({"error": "Все поля обязательны."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ✅ Use case-insensitive matching for both email and reset_code
            user = User.objects.get(email__iexact=email, reset_code__iexact=reset_code)
            print("✅ User found:", user.email)

            if user.reset_code_created_at:
                print("🕓 Code created at:", user.reset_code_created_at)
                print("🕓 Now:", timezone.now())

                if user.reset_code_created_at < timezone.now() - timezone.timedelta(minutes=15):
                    print("❌ Reset code expired.")
                    return Response({"error": "Код сброса истёк. Запросите новый."}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.reset_code = None
            user.reset_code_created_at = None
            user.save()

            print("✅ Password reset successfully for", email)
            return Response({"message": "Пароль успешно обновлён."}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            print("❌ No user found with matching email and code.")
            return Response({"error": "Неверный код или email."}, status=status.HTTP_400_BAD_REQUEST)


    @swagger_auto_schema(operation_description="Doctor Dashboard")
    @action(detail=False, methods=["get"], permission_classes=[IsDoctor])
    def doctor_dashboard(self, request):
        return Response({"message": "Welcome, Doctor!"})

    @swagger_auto_schema(operation_description="Admin Panel")
    @action(detail=False, methods=["get"], permission_classes=[IsAdmin])
    def admin_panel(self, request):
        return Response({"message": "Welcome, Admin!"})
    
    @swagger_auto_schema(operation_description="Nurse Dashboard")
    @action(detail=False, methods=["get"], permission_classes=[IsNurse])
    def nurse_dashboard(self, request):
        return Response({"message": "Welcome, Nurse!"})

    # ✅ New endpoint to fetch available doctors
    @swagger_auto_schema(
        operation_description="Get available doctors",
        responses={200: "List of available doctors"},
    )
    @action(detail=False, methods=["get"], url_path="doctor/available")
    def get_available_doctors(self, request):
        """Fetch a list of available doctors."""
        # Optimize query to avoid N+1 problem by prefetching specializations and clinic
        # Show all active doctors (regardless of availability status for real-time updates)
        doctors = User.objects.filter(
            role="doctor",
            is_active=True
        ).select_related('doctor_specialization', 'clinic', 'clinic__city')

        if not doctors.exists():
            return Response({"error": "No available doctors found."}, status=status.HTTP_404_NOT_FOUND)

        # Get language preference from request (default to Russian)
        language = request.GET.get('lang', 'ru')

        doctor_list = []
        for doctor in doctors:
            # Get specialization in requested language
            if doctor.doctor_specialization:
                if language == 'kz':
                    specialization = doctor.doctor_specialization.name_kz
                elif language == 'en':
                    specialization = doctor.doctor_specialization.name_en
                else:
                    specialization = doctor.doctor_specialization.name_ru
            else:
                specialization = doctor.doctor_type or "Специальность не указана"

            # Get clinic information if doctor has clinic
            clinic_data = None
            if doctor.clinic:
                clinic = doctor.clinic
                clinic_data = {
                    "id": clinic.id,
                    "name": clinic.name,
                    "address": clinic.address or None,
                    "phone": clinic.phones if hasattr(clinic, 'phones') else None,
                    "city": clinic.city.name_ru if clinic.city else None,
                }

            doctor_list.append({
                "id": doctor.id,
                "name": f"{doctor.first_name} {doctor.last_name}",
                "email": doctor.email,
                "doctor_type": specialization,
                "availability_status": doctor.availability_status or 'offline',
                "availability_note": doctor.availability_note or '',
                # Include clinic information
                "clinic": clinic_data,
                # Include additional specialization details
                "specialization": {
                    "id": doctor.doctor_specialization.id if doctor.doctor_specialization else None,
                    "name_ru": doctor.doctor_specialization.name_ru if doctor.doctor_specialization else None,
                    "name_kz": doctor.doctor_specialization.name_kz if doctor.doctor_specialization else None,
                    "name_en": doctor.doctor_specialization.name_en if doctor.doctor_specialization else None,
                } if doctor.doctor_specialization else None
            })

        return Response({"doctors": doctor_list}, status=status.HTTP_200_OK)

    # ✅ New endpoint to fetch available nurses
    @swagger_auto_schema(
        operation_description="Get available nurses",
        responses={200: "List of available nurses"},
    )
    @action(detail=False, methods=["get"], url_path="nurse/available")
    def get_available_nurses(self, request):
        """Fetch a list of available nurses."""
        # Optimize query to avoid N+1 problem by prefetching specializations and clinic
        # Show all active nurses (regardless of availability status for real-time updates)
        nurses = User.objects.filter(
            role="nurse",
            is_active=True
        ).select_related('nurse_specialization', 'clinic', 'clinic__city')

        if not nurses.exists():
            return Response({"error": "No available nurses found."}, status=status.HTTP_404_NOT_FOUND)

        # Get language preference from request (default to Russian)
        language = request.GET.get('lang', 'ru')

        nurse_list = []
        for nurse in nurses:
            # Get specialization in requested language
            if nurse.nurse_specialization:
                if language == 'kz':
                    specialization = nurse.nurse_specialization.name_kz
                elif language == 'en':
                    specialization = nurse.nurse_specialization.name_en
                else:
                    specialization = nurse.nurse_specialization.name_ru
            else:
                specialization = nurse.nurse_type or "Специальность не указана"

            # Get clinic information if nurse has clinic
            clinic_data = None
            if nurse.clinic:
                clinic = nurse.clinic
                clinic_data = {
                    "id": clinic.id,
                    "name": clinic.name,
                    "address": clinic.address or None,
                    "phone": clinic.phones if hasattr(clinic, 'phones') else None,
                    "city": clinic.city.name_ru if clinic.city else None,
                }

            nurse_list.append({
                "id": nurse.id,
                "name": f"{nurse.first_name} {nurse.last_name}",
                "email": nurse.email,
                "nurse_type": specialization,
                "availability_status": nurse.availability_status or 'offline',
                "availability_note": nurse.availability_note or '',
                # Include clinic information
                "clinic": clinic_data,
                # Include additional specialization details
                "specialization": {
                    "id": nurse.nurse_specialization.id if nurse.nurse_specialization else None,
                    "name_ru": nurse.nurse_specialization.name_ru if nurse.nurse_specialization else None,
                    "name_kz": nurse.nurse_specialization.name_kz if nurse.nurse_specialization else None,
                    "name_en": nurse.nurse_specialization.name_en if nurse.nurse_specialization else None,
                } if nurse.nurse_specialization else None
            })

        return Response({"nurses": nurse_list}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Get user profile field choices",
        responses={200: "List of field choices for user profile"},
    )
    @action(detail=False, methods=["get"], url_path="profile/choices")
    def get_profile_choices(self, request):
        """Get all available choices for user profile fields."""
        choices = {
            "gender_choices": [{"value": key, "label": value} for key, value in User.GENDER_CHOICES],
            "language_choices": [{"value": key, "label": value} for key, value in User.LANGUAGE_CHOICES],
            "marital_status_choices": [{"value": key, "label": value} for key, value in User.MARITAL_STATUS_CHOICES],
            "blood_type_choices": [{"value": key, "label": value} for key, value in User.BLOOD_TYPE_CHOICES],
            "role_choices": [{"value": key, "label": value} for key, value in User.ROLE_CHOICES],
        }
        return Response(choices, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Update doctor or nurse availability status",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "availability_status": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['available', 'busy', 'offline', 'break'],
                    description="Availability status"
                ),
                "availability_note": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Optional note about availability"
                ),
            },
            required=["availability_status"],
        ),
        responses={
            200: "Availability updated successfully",
            400: "Invalid status",
            403: "Only doctors and nurses can update availability"
        },
    )
    @action(detail=False, methods=["patch"], url_path="update-availability")
    def update_availability(self, request):
        """Update doctor or nurse availability status"""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        # Get the authenticated user
        try:
            if hasattr(request.user, 'role'):
                user = request.user
                print("[DEBUG] Using request.user directly:", user)
                print("[DEBUG] request.user.role:", getattr(user, "role", None))
            else:
                from rest_framework.authtoken.models import Token
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                print("[DEBUG] Auth header:", auth_header)

                if auth_header.startswith('Token '):
                    token_key = auth_header.split(' ')[1]
                    print("[DEBUG] Token key:", token_key)

                    token = Token.objects.select_related('user').get(key=token_key)
                    user = token.user
                    print("[DEBUG] User from token:", user)
                    print("[DEBUG] user.role:", getattr(user, "role", None))
                else:
                    print("[DEBUG] No valid token in header")
                    return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print("[ERROR] Authentication error:", str(e))
            return Response({'error': 'Authentication error'}, status=status.HTTP_401_UNAUTHORIZED)

        # Check if user is a doctor or nurse (case-insensitive)
        user_role = getattr(user, 'role', '').strip().lower()
        print("[DEBUG] Final resolved user:", user)
        print("[DEBUG] user.id:", getattr(user, "id", None))
        print("[DEBUG] user.email:", getattr(user, "email", None))
        print("[DEBUG] user.role:", user_role)

        if user_role not in ['doctor', 'nurse']:
            print("[DEBUG] Role check failed. Expected 'doctor' or 'nurse', got:", user_role)
            return Response(
                {"error": "Only doctors and nurses can update availability status", "debug_role": user_role},
                status=status.HTTP_403_FORBIDDEN
            )

        availability_status = request.data.get('availability_status')
        availability_note = request.data.get('availability_note', '')

        # Validate status
        valid_statuses = ['available', 'busy', 'offline', 'break']
        if availability_status not in valid_statuses:
            print("[DEBUG] Invalid status received:", availability_status)
            return Response(
                {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Store old status for change detection
        old_status = user.availability_status

        # Update availability
        user.availability_status = availability_status
        user.availability_note = availability_note
        user.save()
        print(f"[DEBUG] Updated {user.email} availability from {old_status} -> {availability_status}")

        # Broadcast availability change via WebSocket with FULL doctor data
        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                # Prepare full data based on role
                if user_role == 'doctor':
                    event_type = 'doctor_availability_changed'
                    user_id_key = 'doctor_id'

                    # Get clinic information
                    clinic_data = None
                    if user.clinic:
                        clinic = user.clinic
                        clinic_data = {
                            "id": clinic.id,
                            "name": clinic.name,
                            "address": clinic.address or None,
                            "phone": clinic.phones if hasattr(clinic, 'phones') else None,
                            "city": clinic.city.name_ru if clinic.city else None,
                        }

                    # Get specialization
                    if user.doctor_specialization:
                        specialization = user.doctor_specialization.name_ru
                    else:
                        specialization = user.doctor_type or "Специальность не указана"

                    # Full doctor data
                    full_data = {
                        "id": user.id,
                        "name": f"{user.first_name} {user.last_name}",
                        "email": user.email,
                        "doctor_type": specialization,
                        "availability_status": availability_status,
                        "availability_note": availability_note,
                        "clinic": clinic_data,
                        "specialization": {
                            "id": user.doctor_specialization.id if user.doctor_specialization else None,
                            "name_ru": user.doctor_specialization.name_ru if user.doctor_specialization else None,
                            "name_kz": user.doctor_specialization.name_kz if user.doctor_specialization else None,
                            "name_en": user.doctor_specialization.name_en if user.doctor_specialization else None,
                        } if user.doctor_specialization else None
                    }
                else:  # nurse
                    event_type = 'nurse_availability_changed'
                    user_id_key = 'nurse_id'

                    # Get clinic information
                    clinic_data = None
                    if user.clinic:
                        clinic = user.clinic
                        clinic_data = {
                            "id": clinic.id,
                            "name": clinic.name,
                            "address": clinic.address or None,
                            "phone": clinic.phones if hasattr(clinic, 'phones') else None,
                            "city": clinic.city.name_ru if clinic.city else None,
                        }

                    # Get specialization
                    if user.nurse_specialization:
                        specialization = user.nurse_specialization.name_ru
                    else:
                        specialization = user.nurse_type or "Специальность не указана"

                    full_data = {
                        "id": user.id,
                        "name": f"{user.first_name} {user.last_name}",
                        "email": user.email,
                        "nurse_type": specialization,
                        "availability_status": availability_status,
                        "availability_note": availability_note,
                        "clinic": clinic_data,
                        "specialization": {
                            "id": user.nurse_specialization.id if user.nurse_specialization else None,
                            "name_ru": user.nurse_specialization.name_ru if user.nurse_specialization else None,
                            "name_kz": user.nurse_specialization.name_kz if user.nurse_specialization else None,
                            "name_en": user.nurse_specialization.name_en if user.nurse_specialization else None,
                        } if user.nurse_specialization else None
                    }

                payload = {
                    'type': event_type,
                    user_id_key: user.id,
                    'availability_status': availability_status,
                    'availability_note': availability_note,
                    'old_status': old_status,
                    'data': full_data  # Full doctor/nurse data
                }

                # Send to all Socket.IO clients (no need to send to both groups to avoid duplicates)
                async_to_sync(channel_layer.group_send)("socketio_clients", payload)

                logger.info(f"{user_role.capitalize()} {user.email} availability changed from {old_status} to {availability_status}")
            except Exception as e:
                print("[ERROR] Failed to broadcast availability change:", str(e))
                logger.error(f"Failed to broadcast availability change: {str(e)}")

        return Response({
            "message": "Availability updated successfully",
            "availability_status": availability_status,
            "availability_note": availability_note
        }, status=status.HTTP_200_OK)

class UserProfileViewSet(ViewSet):
    """
    A ViewSet for handling user profile operations.
    """

    @swagger_auto_schema(
        method='get',
        operation_description="Fetch the authenticated user's profile",
        responses={200: UserProfileSerializer},
    )
    @swagger_auto_schema(
        method='patch',
        operation_description="Update the authenticated user's profile",
        request_body=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: "Validation error"
        },
    )
    @action(detail=False, methods=["get", "patch"], url_path="profile")
    def myprofile(self, request):
        # Get the custom User instance using the authenticated token
        try:
            # If using CustomTokenAuthentication, the request.user should be the custom User
            # But if it's AnonymousUser, we need to get the custom User from the token
            if hasattr(request.user, 'role'):
                # Already have custom User instance
                user = request.user
            else:
                # Get custom User from token
                from rest_framework.authtoken.models import Token
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header.startswith('Token '):
                    token_key = auth_header.split(' ')[1]
                    token = Token.objects.select_related('user').get(key=token_key)
                    user = token.user
                else:
                    return Response({'error': 'Authentication token required'}, status=status.HTTP_401_UNAUTHORIZED)
        except Token.DoesNotExist:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'error': f'Authentication error: {str(e)}'}, status=status.HTTP_401_UNAUTHORIZED)

        if request.method == "GET":
            serializer = UserProfileSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == "PATCH":
            serializer = UserProfileSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Fetch a specific user's profile by user_id",
        responses={200: UserProfileSerializer},
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_PATH,
                description="The ID of the user to fetch the profile for.",
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
    )
    @action(detail=False, methods=["get"], url_path="profile/(?P<user_id>[^/.]+)")
    def profile_by_id(self, request, user_id):
        """
        Retrieve a specific user's profile by user_id.
        """
        try:
            user = User.objects.get(id=user_id)
            serializer = UserProfileSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_description="Update the authenticated user's profile",
        request_body=UserProfileSerializer,
        responses={
            200: "Profile updated successfully!",
            400: "Validation error",
        },
    )
    @action(detail=False, methods=["put"], url_path="profile")
    def update_profile(self, request):
        """
        Update the authenticated user's profile.
        """
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Update a specific user's profile by user_id",
        request_body=UserProfileSerializer,
        responses={
            200: "Profile updated successfully!",
            400: "Validation error",
        },
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_PATH,
                description="The ID of the user to update the profile for.",
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
    )
    @action(detail=False, methods=["put"], url_path="profile/(?P<user_id>[^/.]+)")
    def update_profile_by_id(self, request, user_id):
        """
        Update a specific user's profile by user_id.
        """
        try:
            user = User.objects.get(id=user_id)
            serializer = UserProfileSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
        
    @swagger_auto_schema(
        method="post",
        operation_description="Refresh JWT access token",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh_token": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["refresh_token"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "access_token": openapi.Schema(type=openapi.TYPE_STRING),
                    "refresh_token": openapi.Schema(type=openapi.TYPE_STRING),
                }
            ),
            401: "Invalid refresh token"
        },
    )
    @action(detail=False, methods=["post"], url_path="auth/refresh", url_name="refresh")
    def refresh_token(self, request):
        """Refresh JWT tokens using refresh token."""
        refresh_token_str = request.data.get("refresh_token")

        if not refresh_token_str:
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Use the JWT refresh function
            tokens = refresh_jwt_tokens(refresh_token_str)
            return Response(tokens, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")
            return Response({"error": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)


    @swagger_auto_schema(
        operation_description="Partially update the authenticated user's profile (PATCH).",
        request_body=UserProfileSerializer,
        responses={200: "Profile updated successfully!", 400: "Validation error"},
    )
    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /user-profile/profile/
        Authenticated user updates their own profile.
        """
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Partially update a specific user's profile by user_id (PATCH).",
        request_body=UserProfileSerializer,
        responses={200: "Profile updated successfully!", 400: "Validation error", 404: "User not found."},
        manual_parameters=[
            openapi.Parameter(
                "user_id",
                openapi.IN_PATH,
                description="The ID of the user to partially update the profile for.",
                type=openapi.TYPE_INTEGER,
                required=True,
            )
        ],
    )
    @action(detail=False, methods=["patch"], url_path="profile/(?P<user_id>[^/.]+)")
    def partial_update_profile_by_id(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            serializer = UserProfileSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Update doctor or nurse availability status",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "availability_status": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['available', 'busy', 'offline', 'break'],
                    description="Availability status"
                ),
                "availability_note": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Optional note about availability"
                ),
            },
            required=["availability_status"],
        ),
        responses={
            200: "Availability updated successfully",
            400: "Invalid status",
            403: "Only doctors and nurses can update availability"
        },
    )
    @action(detail=False, methods=["patch"], url_path="update-availability")
    def update_availability(self, request):
        """Update doctor or nurse availability status"""
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        # Get the authenticated user
        try:
            if hasattr(request.user, 'role'):
                user = request.user
                print("[DEBUG] Using request.user directly:", user)
                print("[DEBUG] request.user.role:", getattr(user, "role", None))
            else:
                from rest_framework.authtoken.models import Token
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                print("[DEBUG] Auth header:", auth_header)

                if auth_header.startswith('Token '):
                    token_key = auth_header.split(' ')[1]
                    print("[DEBUG] Token key:", token_key)

                    token = Token.objects.select_related('user').get(key=token_key)
                    user = token.user
                    print("[DEBUG] User from token:", user)
                    print("[DEBUG] user.role:", getattr(user, "role", None))
                else:
                    print("[DEBUG] No valid token in header")
                    return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print("[ERROR] Authentication error:", str(e))
            return Response({'error': 'Authentication error'}, status=status.HTTP_401_UNAUTHORIZED)

        # Check if user is a doctor or nurse (case-insensitive)
        user_role = getattr(user, 'role', '').strip().lower()
        print("[DEBUG] Final resolved user:", user)
        print("[DEBUG] user.id:", getattr(user, "id", None))
        print("[DEBUG] user.email:", getattr(user, "email", None))
        print("[DEBUG] user.role:", user_role)

        if user_role not in ['doctor', 'nurse']:
            print("[DEBUG] Role check failed. Expected 'doctor' or 'nurse', got:", user_role)
            return Response(
                {"error": "Only doctors and nurses can update availability status", "debug_role": user_role},
                status=status.HTTP_403_FORBIDDEN
            )
    
        availability_status = request.data.get('availability_status')
        availability_note = request.data.get('availability_note', '')
    
        # Validate status
        valid_statuses = ['available', 'busy', 'offline', 'break']
        if availability_status not in valid_statuses:
            print("[DEBUG] Invalid status received:", availability_status)
            return Response(
                {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        # Store old status for change detection
        old_status = user.availability_status
    
        # Update availability
        user.availability_status = availability_status
        user.availability_note = availability_note
        user.save()
        print(f"[DEBUG] Updated {user.email} availability from {old_status} -> {availability_status}")
    
        # Broadcast availability change via WebSocket with FULL doctor/nurse data
        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                # Prepare full data based on role
                if user_role == 'doctor':
                    event_type = 'doctor_availability_changed'
                    user_id_key = 'doctor_id'

                    # Get clinic information
                    clinic_data = None
                    if user.clinic:
                        clinic = user.clinic
                        clinic_data = {
                            "id": clinic.id,
                            "name": clinic.name,
                            "address": clinic.address or None,
                            "phone": clinic.phones if hasattr(clinic, 'phones') else None,
                            "city": clinic.city.name_ru if clinic.city else None,
                        }

                    # Get specialization
                    if user.doctor_specialization:
                        specialization = user.doctor_specialization.name_ru
                    else:
                        specialization = user.doctor_type or "Специальность не указана"

                    # Full doctor data
                    full_data = {
                        "id": user.id,
                        "name": f"{user.first_name} {user.last_name}",
                        "email": user.email,
                        "doctor_type": specialization,
                        "availability_status": availability_status,
                        "availability_note": availability_note,
                        "clinic": clinic_data,
                        "specialization": {
                            "id": user.doctor_specialization.id if user.doctor_specialization else None,
                            "name_ru": user.doctor_specialization.name_ru if user.doctor_specialization else None,
                            "name_kz": user.doctor_specialization.name_kz if user.doctor_specialization else None,
                            "name_en": user.doctor_specialization.name_en if user.doctor_specialization else None,
                        } if user.doctor_specialization else None
                    }
                else:  # nurse
                    event_type = 'nurse_availability_changed'
                    user_id_key = 'nurse_id'

                    # Get clinic information
                    clinic_data = None
                    if user.clinic:
                        clinic = user.clinic
                        clinic_data = {
                            "id": clinic.id,
                            "name": clinic.name,
                            "address": clinic.address or None,
                            "phone": clinic.phones if hasattr(clinic, 'phones') else None,
                            "city": clinic.city.name_ru if clinic.city else None,
                        }

                    # Get specialization
                    if user.nurse_specialization:
                        specialization = user.nurse_specialization.name_ru
                    else:
                        specialization = user.nurse_type or "Специальность не указана"

                    full_data = {
                        "id": user.id,
                        "name": f"{user.first_name} {user.last_name}",
                        "email": user.email,
                        "nurse_type": specialization,
                        "availability_status": availability_status,
                        "availability_note": availability_note,
                        "clinic": clinic_data,
                        "specialization": {
                            "id": user.nurse_specialization.id if user.nurse_specialization else None,
                            "name_ru": user.nurse_specialization.name_ru if user.nurse_specialization else None,
                            "name_kz": user.nurse_specialization.name_kz if user.nurse_specialization else None,
                            "name_en": user.nurse_specialization.name_en if user.nurse_specialization else None,
                        } if user.nurse_specialization else None
                    }

                payload = {
                    'type': event_type,
                    user_id_key: user.id,
                    'availability_status': availability_status,
                    'availability_note': availability_note,
                    'old_status': old_status,
                    'data': full_data  # Full doctor/nurse data
                }

                # Send to all Socket.IO clients (no need to send to both groups to avoid duplicates)
                async_to_sync(channel_layer.group_send)("socketio_clients", payload)

                logger.info(f"{user_role.capitalize()} {user.email} availability changed from {old_status} to {availability_status}")
            except Exception as e:
                print("[ERROR] Failed to broadcast availability change:", str(e))
                logger.error(f"Failed to broadcast availability change: {str(e)}")
    
        return Response({
            "message": "Availability updated successfully",
            "availability_status": availability_status,
            "availability_note": availability_note
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="test-action")
    def test_action(self, request):
        """Test action to see if actions work"""
        return Response({"message": "Test action works!"}, status=status.HTTP_200_OK)


class StaffViewSet(ViewSet):
    """
    ViewSet for managing staff (doctors and nurses)
    Only accessible by admins
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        GET /api/v1/staff/
        List all staff members (doctors and nurses)
        """
        # Check if user is admin
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get clinic_id if admin is clinic-specific
        clinic_id = request.user.clinic_id if hasattr(request.user, 'clinic_id') else None

        # show_deleted=true returns only soft-deleted staff, otherwise only active
        show_deleted = request.query_params.get('show_deleted', 'false').lower() == 'true'

        # Build query
        base_filters = {
            'role__in': ['doctor', 'nurse'],
            'is_deleted': show_deleted,
        }
        if clinic_id:
            base_filters['clinic_id'] = clinic_id

        staff = User.objects.filter(**base_filters)

        # Serialize staff data
        staff_data = []
        for member in staff:
            # Get all specializations as comma-separated string
            specialization = None
            if member.role == 'doctor':
                specs = list(member.doctor_specializations.values_list('name_ru', flat=True))
                if specs:
                    specialization = ', '.join(specs)
                elif member.doctor_specialization:
                    specialization = member.doctor_specialization.name_ru
            elif member.role == 'nurse':
                specs = list(member.nurse_specializations.values_list('name_ru', flat=True))
                if specs:
                    specialization = ', '.join(specs)
                elif member.nurse_specialization:
                    specialization = member.nurse_specialization.name_ru

            # Get profile fields
            profile = None
            if member.role == 'doctor' and hasattr(member, 'doctor_profile'):
                profile = member.doctor_profile
            elif member.role == 'nurse' and hasattr(member, 'nurse_profile'):
                profile = member.nurse_profile

            staff_data.append({
                'id': member.id,
                'first_name': member.first_name,
                'last_name': member.last_name,
                'email': member.email,
                'phone': member.phone,
                'role': member.role,
                'specialization': specialization,
                'gender': member.gender,
                'birth_date': member.birth_date.isoformat() if member.birth_date else None,
                'address': member.address,
                'city': member.city,
                'language': member.language,
                'years_of_experience': profile.years_of_experience if profile else None,
                'offline_consultation_price': str(profile.offline_consultation_price) if profile and profile.offline_consultation_price is not None else None,
                'online_consultation_price': str(profile.online_consultation_price) if profile and profile.online_consultation_price is not None else None,
                'preferred_consultation_duration': profile.preferred_consultation_duration if profile else None,
                'work_schedule': profile.work_schedule if profile else None,
                'is_active': member.is_active,
                'is_deleted': member.is_deleted,
                'availability_status': member.availability_status,
                'created_at': member.created_at.isoformat() if member.created_at else None,
                'clinic': {
                    'id': member.clinic.id,
                    'name': member.clinic.name
                } if member.clinic else None
            })

        return Response(staff_data, status=status.HTTP_200_OK)

    def create(self, request):
        """
        POST /api/v1/staff/
        Create a new staff member (doctor or nurse)
        """
        # Check if user is admin
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get data from request
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        if phone:
            phone = '+' + ''.join(c for c in phone if c.isdigit())
        password = request.data.get('password')
        role = request.data.get('role')  # 'doctor' or 'nurse'
        specialization = request.data.get('specialization', '')

        # Additional optional fields
        gender = request.data.get('gender')
        birth_date = request.data.get('birth_date')
        address = request.data.get('address')
        city = request.data.get('city')
        language = request.data.get('language')
        years_of_experience = request.data.get('years_of_experience')
        offline_consultation_price = request.data.get('offline_consultation_price')
        online_consultation_price = request.data.get('online_consultation_price')
        preferred_consultation_duration = request.data.get('preferred_consultation_duration')
        work_schedule = request.data.get('work_schedule')

        # Validate required fields
        if not all([first_name, last_name, email, phone, password, role]):
            return Response(
                {'error': 'Все обязательные поля должны быть заполнены'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate role
        if role not in ['doctor', 'nurse']:
            return Response(
                {'error': 'Роль должна быть doctor или nurse'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate password length
        if len(password) < 8:
            return Response(
                {'error': 'Пароль должен содержать минимум 8 символов'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Collect all validation errors
        validation_errors = []

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            validation_errors.append('Пользователь с таким email уже существует')

        # Check if phone already exists
        if phone and User.objects.filter(phone=phone).exists():
            validation_errors.append('Пользователь с таким телефоном уже существует')

        # Return all validation errors together
        if validation_errors:
            return Response(
                {'error': '. '.join(validation_errors)},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Determine clinic assignment
            # Global admins (no clinic_id) can select clinic from request
            # Clinic admins (have clinic_id) automatically assign to their clinic
            admin_clinic_id = request.user.clinic_id if hasattr(request.user, 'clinic_id') else None

            if admin_clinic_id:
                # Clinic admin: use their clinic
                clinic_id = admin_clinic_id
            else:
                # Global admin: use clinic from request (optional)
                clinic_id = request.data.get('clinic_id')

            clinic = None
            if clinic_id:
                from clinics.models import Clinics
                try:
                    clinic = Clinics.objects.get(id=clinic_id)
                except Clinics.DoesNotExist:
                    return Response(
                        {'error': 'Клиника не найдена'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Create new staff member
            new_staff = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                role=role,
                gender=gender if gender else None,
                birth_date=birth_date if birth_date else None,
                address=address if address else None,
                city=city if city else None,
                language=language if language else 'ru',
                is_active=True,
                is_deleted=False,
                clinic=clinic
            )

            # Set password (will be hashed automatically by set_password)
            new_staff.set_password(password)
            new_staff.save()

            # Handle specializations (supports comma-separated multiple specializations)
            if specialization:
                # Split by comma and strip whitespace
                spec_names = [s.strip() for s in specialization.split(',') if s.strip()]

                if role == 'doctor':
                    specs = []
                    for spec_name in spec_names:
                        # Try to find existing specialization by name_ru
                        spec = DoctorSpecialization.objects.filter(name_ru=spec_name).first()
                        if not spec:
                            # Create new specialization with unique names
                            try:
                                spec = DoctorSpecialization.objects.create(
                                    name_ru=spec_name,
                                    name_kz=f"{spec_name} (KZ)",
                                    name_en=f"{spec_name} (EN)"
                                )
                            except Exception:
                                # If creation fails, try to find by any name field
                                spec = DoctorSpecialization.objects.filter(
                                    models.Q(name_ru=spec_name) |
                                    models.Q(name_kz=spec_name) |
                                    models.Q(name_en=spec_name)
                                ).first()
                        if spec:
                            specs.append(spec)

                    # Set primary specialization (first one) for backwards compatibility
                    new_staff.doctor_specialization = specs[0] if specs else None
                    new_staff.save()
                    # Set all specializations in ManyToMany field
                    new_staff.doctor_specializations.set(specs)

                elif role == 'nurse':
                    specs = []
                    for spec_name in spec_names:
                        # Try to find existing specialization by name_ru
                        spec = NurseSpecialization.objects.filter(name_ru=spec_name).first()
                        if not spec:
                            # Create new specialization with unique names
                            try:
                                spec = NurseSpecialization.objects.create(
                                    name_ru=spec_name,
                                    name_kz=f"{spec_name} (KZ)",
                                    name_en=f"{spec_name} (EN)"
                                )
                            except Exception:
                                # If creation fails, try to find by any name field
                                spec = NurseSpecialization.objects.filter(
                                    models.Q(name_ru=spec_name) |
                                    models.Q(name_kz=spec_name) |
                                    models.Q(name_en=spec_name)
                                ).first()
                        if spec:
                            specs.append(spec)

                    # Set primary specialization (first one) for backwards compatibility
                    new_staff.nurse_specialization = specs[0] if specs else None
                    new_staff.save()
                    # Set all specializations in ManyToMany field
                    new_staff.nurse_specializations.set(specs)

            # Create doctor/nurse profile
            profile_defaults = {
                'years_of_experience': int(years_of_experience) if years_of_experience else None,
                'offline_consultation_price': offline_consultation_price if offline_consultation_price else None,
                'online_consultation_price': online_consultation_price if online_consultation_price else None,
                'preferred_consultation_duration': int(preferred_consultation_duration) if preferred_consultation_duration else None,
                'work_schedule': work_schedule if work_schedule else None,
            }
            if role == 'doctor':
                DoctorProfile.objects.update_or_create(user=new_staff, defaults=profile_defaults)
            elif role == 'nurse':
                NurseProfile.objects.update_or_create(user=new_staff, defaults=profile_defaults)

            # Get profile
            profile = None
            if role == 'doctor' and hasattr(new_staff, 'doctor_profile'):
                profile = new_staff.doctor_profile
            elif role == 'nurse' and hasattr(new_staff, 'nurse_profile'):
                profile = new_staff.nurse_profile

            # Return created staff member data
            return Response({
                'id': new_staff.id,
                'first_name': new_staff.first_name,
                'last_name': new_staff.last_name,
                'email': new_staff.email,
                'phone': new_staff.phone,
                'role': new_staff.role,
                'specialization': specialization,
                'gender': new_staff.gender,
                'birth_date': str(new_staff.birth_date) if new_staff.birth_date else None,
                'address': new_staff.address,
                'city': new_staff.city,
                'language': new_staff.language,
                'years_of_experience': profile.years_of_experience if profile else None,
                'offline_consultation_price': str(profile.offline_consultation_price) if profile and profile.offline_consultation_price is not None else None,
                'online_consultation_price': str(profile.online_consultation_price) if profile and profile.online_consultation_price is not None else None,
                'preferred_consultation_duration': profile.preferred_consultation_duration if profile else None,
                'work_schedule': profile.work_schedule if profile else None,
                'is_active': new_staff.is_active,
                'created_at': new_staff.created_at.isoformat() if new_staff.created_at else None,
                'clinic': {
                    'id': clinic.id,
                    'name': clinic.name
                } if clinic else None
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception("Error creating staff member")
            return Response(
                {'error': 'Не удалось создать сотрудника', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def partial_update(self, request, pk=None):
        """
        PATCH /api/v1/staff/{id}/
        Update staff member details
        """
        # Check if user is admin
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Get the staff member
            staff_member = User.objects.get(id=pk, role__in=['doctor', 'nurse'])

            # Check if admin has permission to update this staff member
            admin_clinic_id = request.user.clinic_id if hasattr(request.user, 'clinic_id') else None
            if admin_clinic_id and staff_member.clinic_id != admin_clinic_id:
                return Response(
                    {'error': 'У вас нет прав для изменения этого сотрудника'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Validate email uniqueness if email is being changed
            new_email = request.data.get('email')
            if new_email and new_email != staff_member.email:
                if User.objects.filter(email=new_email).exclude(id=pk).exists():
                    return Response(
                        {'error': 'Пользователь с таким email уже существует'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Validate phone uniqueness if phone is being changed
            new_phone = request.data.get('phone')
            if new_phone:
                new_phone = '+' + ''.join(c for c in new_phone if c.isdigit())
            if new_phone and new_phone != staff_member.phone:
                if User.objects.filter(phone=new_phone).exclude(id=pk).exists():
                    return Response(
                        {'error': 'Пользователь с таким телефоном уже существует'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Update basic fields if provided
            if 'first_name' in request.data:
                staff_member.first_name = request.data['first_name']
            if 'last_name' in request.data:
                staff_member.last_name = request.data['last_name']
            if 'email' in request.data:
                staff_member.email = request.data['email']
            if 'phone' in request.data:
                staff_member.phone = new_phone

            # Update additional fields if provided
            if 'gender' in request.data:
                staff_member.gender = request.data['gender'] if request.data['gender'] else None
            if 'birth_date' in request.data:
                staff_member.birth_date = request.data['birth_date'] if request.data['birth_date'] else None
            if 'address' in request.data:
                staff_member.address = request.data['address'] if request.data['address'] else None
            if 'city' in request.data:
                staff_member.city = request.data['city'] if request.data['city'] else None
            if 'language' in request.data:
                staff_member.language = request.data['language'] if request.data['language'] else 'ru'

            # Update role if provided (doctor/nurse)
            if 'role' in request.data and request.data['role'] in ['doctor', 'nurse']:
                staff_member.role = request.data['role']

            # Update password if provided
            if 'password' in request.data and request.data['password']:
                password = request.data['password']
                if len(password) < 8:
                    return Response(
                        {'error': 'Пароль должен содержать минимум 8 символов'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                staff_member.set_password(password)

            # Update specializations if provided (supports comma-separated multiple specializations)
            if 'specialization' in request.data:
                specialization_input = request.data['specialization']
                if specialization_input:
                    # Split by comma and strip whitespace
                    spec_names = [s.strip() for s in specialization_input.split(',') if s.strip()]

                    if staff_member.role == 'doctor':
                        specs = []
                        for spec_name in spec_names:
                            # Try to find existing specialization by name_ru
                            spec = DoctorSpecialization.objects.filter(name_ru=spec_name).first()
                            if not spec:
                                # Create new specialization with unique names
                                try:
                                    spec = DoctorSpecialization.objects.create(
                                        name_ru=spec_name,
                                        name_kz=f"{spec_name} (KZ)",
                                        name_en=f"{spec_name} (EN)"
                                    )
                                except Exception:
                                    # If creation fails, try to find by any name field
                                    spec = DoctorSpecialization.objects.filter(
                                        models.Q(name_ru=spec_name) |
                                        models.Q(name_kz=spec_name) |
                                        models.Q(name_en=spec_name)
                                    ).first()
                            if spec:
                                specs.append(spec)

                        # Set primary specialization (first one) for backwards compatibility
                        staff_member.doctor_specialization = specs[0] if specs else None
                        staff_member.nurse_specialization = None
                        # Save first to get ID for ManyToMany
                        staff_member.save()
                        # Set all specializations in ManyToMany field
                        staff_member.doctor_specializations.set(specs)
                        staff_member.nurse_specializations.clear()

                    elif staff_member.role == 'nurse':
                        specs = []
                        for spec_name in spec_names:
                            # Try to find existing specialization by name_ru
                            spec = NurseSpecialization.objects.filter(name_ru=spec_name).first()
                            if not spec:
                                # Create new specialization with unique names
                                try:
                                    spec = NurseSpecialization.objects.create(
                                        name_ru=spec_name,
                                        name_kz=f"{spec_name} (KZ)",
                                        name_en=f"{spec_name} (EN)"
                                    )
                                except Exception:
                                    # If creation fails, try to find by any name field
                                    spec = NurseSpecialization.objects.filter(
                                        models.Q(name_ru=spec_name) |
                                        models.Q(name_kz=spec_name) |
                                        models.Q(name_en=spec_name)
                                    ).first()
                            if spec:
                                specs.append(spec)

                        # Set primary specialization (first one) for backwards compatibility
                        staff_member.nurse_specialization = specs[0] if specs else None
                        staff_member.doctor_specialization = None
                        # Save first to get ID for ManyToMany
                        staff_member.save()
                        # Set all specializations in ManyToMany field
                        staff_member.nurse_specializations.set(specs)
                        staff_member.doctor_specializations.clear()

            # Update availability_status if provided
            if 'availability_status' in request.data:
                staff_member.availability_status = request.data['availability_status']

            # Update is_active if provided (for backward compatibility)
            if 'is_active' in request.data:
                staff_member.is_active = request.data['is_active']

            # Soft delete if requested
            if 'is_deleted' in request.data:
                staff_member.is_deleted = bool(request.data['is_deleted'])

            # Update clinic if provided (only for global admins)
            if 'clinic_id' in request.data and not admin_clinic_id:
                clinic_id = request.data['clinic_id']
                if clinic_id:
                    from clinics.models import Clinics
                    try:
                        clinic = Clinics.objects.get(id=clinic_id)
                        staff_member.clinic = clinic
                    except Clinics.DoesNotExist:
                        return Response(
                            {'error': 'Клиника не найдена'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            staff_member.save()

            # Update profile fields if any are provided
            profile_fields = ['years_of_experience', 'offline_consultation_price', 'online_consultation_price', 'preferred_consultation_duration', 'work_schedule']
            if any(f in request.data for f in profile_fields):
                profile_defaults = {}
                if 'years_of_experience' in request.data:
                    val = request.data['years_of_experience']
                    profile_defaults['years_of_experience'] = int(val) if val else None
                if 'offline_consultation_price' in request.data:
                    val = request.data['offline_consultation_price']
                    profile_defaults['offline_consultation_price'] = val if val else None
                if 'online_consultation_price' in request.data:
                    val = request.data['online_consultation_price']
                    profile_defaults['online_consultation_price'] = val if val else None
                if 'preferred_consultation_duration' in request.data:
                    val = request.data['preferred_consultation_duration']
                    profile_defaults['preferred_consultation_duration'] = int(val) if val else None
                if 'work_schedule' in request.data:
                    val = request.data['work_schedule']
                    profile_defaults['work_schedule'] = val if val else None

                if staff_member.role == 'doctor':
                    DoctorProfile.objects.update_or_create(user=staff_member, defaults=profile_defaults)
                elif staff_member.role == 'nurse':
                    NurseProfile.objects.update_or_create(user=staff_member, defaults=profile_defaults)

            # Get updated specializations for response (as comma-separated string)
            specialization = None
            if staff_member.role == 'doctor':
                specs = list(staff_member.doctor_specializations.values_list('name_ru', flat=True))
                if specs:
                    specialization = ', '.join(specs)
                elif staff_member.doctor_specialization:
                    specialization = staff_member.doctor_specialization.name_ru
            elif staff_member.role == 'nurse':
                specs = list(staff_member.nurse_specializations.values_list('name_ru', flat=True))
                if specs:
                    specialization = ', '.join(specs)
                elif staff_member.nurse_specialization:
                    specialization = staff_member.nurse_specialization.name_ru

            # Get profile (refresh to pick up updates)
            staff_member.refresh_from_db()
            profile = None
            if staff_member.role == 'doctor' and hasattr(staff_member, 'doctor_profile'):
                profile = staff_member.doctor_profile
            elif staff_member.role == 'nurse' and hasattr(staff_member, 'nurse_profile'):
                profile = staff_member.nurse_profile

            # Return updated staff member data
            return Response({
                'id': staff_member.id,
                'first_name': staff_member.first_name,
                'last_name': staff_member.last_name,
                'email': staff_member.email,
                'phone': staff_member.phone,
                'role': staff_member.role,
                'specialization': specialization,
                'gender': staff_member.gender,
                'birth_date': str(staff_member.birth_date) if staff_member.birth_date else None,
                'address': staff_member.address,
                'city': staff_member.city,
                'language': staff_member.language,
                'years_of_experience': profile.years_of_experience if profile else None,
                'offline_consultation_price': str(profile.offline_consultation_price) if profile and profile.offline_consultation_price is not None else None,
                'online_consultation_price': str(profile.online_consultation_price) if profile and profile.online_consultation_price is not None else None,
                'preferred_consultation_duration': profile.preferred_consultation_duration if profile else None,
                'work_schedule': profile.work_schedule if profile else None,
                'is_active': staff_member.is_active,
                'availability_status': staff_member.availability_status,
                'created_at': staff_member.created_at.isoformat() if staff_member.created_at else None,
                'clinic': {
                    'id': staff_member.clinic.id,
                    'name': staff_member.clinic.name
                } if staff_member.clinic else None
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response(
                {'error': 'Сотрудник не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception("Error updating staff member")
            return Response(
                {'error': 'Не удалось обновить сотрудника', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClinicsViewSet(ViewSet):
    """
    ViewSet for managing clinics.
    Only accessible by authenticated admins.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Get list of all clinics (for global admins to select from)
        """
        try:
            from clinics.models import Clinics

            # Check if user is admin
            if not hasattr(request.user, 'role') or request.user.role != 'admin':
                return Response(
                    {'error': 'У вас нет прав доступа'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get all clinics
            clinics = Clinics.objects.filter(is_deleted=False).order_by('name')

            clinics_data = []
            for clinic in clinics:
                clinics_data.append({
                    'id': clinic.id,
                    'name': clinic.name,
                    'address': clinic.address if hasattr(clinic, 'address') else None,
                    'phone': clinic.phone if hasattr(clinic, 'phone') else None,
                })

            return Response(clinics_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error fetching clinics")
            return Response(
                {'error': 'Не удалось загрузить список клиник', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PatientsViewSet(ViewSet):
    """
    ViewSet for managing patients.
    Only accessible by authenticated admins.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Get list of patients.
        - Global admins: see all patients
        - Clinic admins: see only their clinic's patients
        """
        try:
            # Check if user is admin
            if not hasattr(request.user, 'role') or request.user.role != 'admin':
                return Response(
                    {'error': 'У вас нет прав доступа'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Filter patients based on admin's clinic
            clinic_id = request.user.clinic_id if hasattr(request.user, 'clinic_id') else None

            if clinic_id:
                # Clinic admin: filter by their clinic
                patients = User.objects.filter(
                    role='patient',
                    clinic_id=clinic_id,
                    is_deleted=False
                ).order_by('-created_at')
            else:
                # Global admin: get all patients
                patients = User.objects.filter(
                    role='patient',
                    is_deleted=False
                ).order_by('-created_at')

            patients_data = []
            for patient in patients:
                patients_data.append({
                    'id': patient.id,
                    'first_name': patient.first_name,
                    'last_name': patient.last_name,
                    'email': patient.email,
                    'phone': patient.phone,
                    'birth_date': patient.birth_date.isoformat() if patient.birth_date else None,
                    'gender': patient.gender,
                    'address': patient.address,
                    'city': patient.city,
                    'is_active': patient.is_active,
                    'created_at': patient.created_at.isoformat() if patient.created_at else None,
                    'clinic': {
                        'id': patient.clinic.id,
                        'name': patient.clinic.name
                    } if patient.clinic else None
                })

            return Response(patients_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error fetching patients")
            return Response(
                {'error': 'Не удалось загрузить список пациентов', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request):
        """
        Create a new patient.
        - Global admins can assign to any clinic (or null)
        - Clinic admins automatically assign to their clinic
        """
        try:
            # Check if user is admin
            if not hasattr(request.user, 'role') or request.user.role != 'admin':
                return Response(
                    {'error': 'У вас нет прав доступа'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Extract data from request
            first_name = request.data.get('first_name')
            last_name = request.data.get('last_name')
            email = request.data.get('email')
            phone = request.data.get('phone')
            if phone:
                phone = '+' + ''.join(c for c in phone if c.isdigit())
            password = request.data.get('password')
            birth_date = request.data.get('birth_date')
            gender = request.data.get('gender')
            address = request.data.get('address')
            city = request.data.get('city')

            # Validate required fields
            if not all([first_name, last_name, email, phone, password]):
                return Response(
                    {'error': 'Пожалуйста, заполните все обязательные поля'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if email already exists
            if User.objects.filter(email=email).exists():
                return Response(
                    {'error': 'Пользователь с таким email уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if phone already exists
            if phone and User.objects.filter(phone=phone).exists():
                return Response(
                    {'error': 'Пользователь с таким телефоном уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Determine clinic assignment
            admin_clinic_id = request.user.clinic_id if hasattr(request.user, 'clinic_id') else None

            if admin_clinic_id:
                # Clinic admin: use their clinic
                clinic_id = admin_clinic_id
            else:
                # Global admin: use clinic from request (optional)
                clinic_id = request.data.get('clinic_id')

            clinic = None
            if clinic_id:
                from clinics.models import Clinics
                try:
                    clinic = Clinics.objects.get(id=clinic_id)
                except Clinics.DoesNotExist:
                    return Response(
                        {'error': 'Клиника не найдена'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Create new patient
            new_patient = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                role='patient',
                birth_date=birth_date if birth_date else None,
                gender=gender,
                address=address,
                city=city,
                is_active=True,
                is_deleted=False,
                clinic=clinic
            )

            # Set password (will be hashed automatically)
            new_patient.set_password(password)
            new_patient.save()

            # Return created patient data
            return Response({
                'id': new_patient.id,
                'first_name': new_patient.first_name,
                'last_name': new_patient.last_name,
                'email': new_patient.email,
                'phone': new_patient.phone,
                'birth_date': new_patient.birth_date.isoformat() if new_patient.birth_date else None,
                'gender': new_patient.gender,
                'address': new_patient.address,
                'city': new_patient.city,
                'is_active': new_patient.is_active,
                'created_at': new_patient.created_at.isoformat() if new_patient.created_at else None,
                'clinic': {
                    'id': clinic.id,
                    'name': clinic.name
                } if clinic else None
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception("Error creating patient")
            return Response(
                {'error': 'Не удалось создать пациента', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SessionViewSet(ViewSet):
    """
    ViewSet for managing user sessions.
    Allows users to view and revoke their active sessions across devices.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get all active sessions for the current user",
        responses={200: UserSessionSerializer(many=True)},
    )
    def list(self, request):
        """List all active sessions for the current user."""
        sessions = UserSession.objects.filter(
            user=request.user,
            is_revoked=False,
            is_deleted=False
        ).order_by('-last_activity')

        # Get current session JTI from access token
        current_session_jti = self._get_current_session_jti(request)

        session_data = []
        for session in sessions:
            data = UserSessionSerializer(session).data
            data['is_current'] = session.refresh_token_jti == current_session_jti
            session_data.append(data)

        return Response(session_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Revoke a specific session",
        responses={
            200: "Session revoked successfully",
            403: "Cannot revoke current session through this endpoint",
            404: "Session not found",
        },
    )
    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        """Revoke a specific session."""
        try:
            session = UserSession.objects.get(
                id=pk,
                user=request.user,
                is_revoked=False,
                is_deleted=False
            )

            # Prevent revoking current session
            current_session_jti = self._get_current_session_jti(request)
            if session.refresh_token_jti == current_session_jti:
                return Response(
                    {"error": "Cannot revoke current session. Use logout instead."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Revoke the session
            session.revoke()

            # Try to blacklist the token
            try:
                token = RefreshToken(session.refresh_token_jti)
                token.blacklist()
            except Exception:
                pass  # Token may already be blacklisted or invalid

            return Response({"message": "Session revoked successfully"}, status=status.HTTP_200_OK)

        except UserSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Revoke all sessions except current",
        responses={200: "All other sessions revoked"},
    )
    @action(detail=False, methods=["post"], url_path="revoke-all-others")
    def revoke_all_others(self, request):
        """Revoke all sessions except the current one."""
        current_session_jti = self._get_current_session_jti(request)

        # Get all other sessions
        other_sessions = UserSession.objects.filter(
            user=request.user,
            is_revoked=False,
            is_deleted=False
        ).exclude(
            refresh_token_jti=current_session_jti
        )

        revoked_count = other_sessions.count()

        # Revoke all other sessions
        other_sessions.update(
            is_revoked=True,
            revoked_at=timezone.now()
        )

        return Response({
            "message": f"Revoked {revoked_count} sessions",
            "revoked_count": revoked_count
        }, status=status.HTTP_200_OK)

    def _get_current_session_jti(self, request):
        """Extract session JTI from current access token."""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                token = AccessToken(auth_header.split(' ')[1])
                return token.get('session_jti')
            except Exception:
                pass
        return None


class ReportsViewSet(ViewSet):
    """
    ViewSet for generating admin reports and analytics.
    Only accessible by authenticated admins.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        GET /api/v1/reports/
        Get comprehensive reports with optional date filtering.
        Query params: start (date), end (date)
        """
        from django.db.models import Count, Sum
        from django.db.models.functions import TruncMonth, ExtractYear
        from consultations.models import Consultation
        from appointments.models import HomeAppointment
        from payments.models import HomeAppointmentKaspiPayment
        from datetime import datetime

        # Check if user is admin
        if not hasattr(request.user, 'role') or request.user.role != 'admin':
            return Response(
                {'error': 'У вас нет прав доступа'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Parse date range from query params
        start_date_str = request.GET.get('start')
        end_date_str = request.GET.get('end')

        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            else:
                # Default: beginning of current year
                start_date = datetime(datetime.now().year, 1, 1).date()

            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            else:
                # Default: today
                end_date = datetime.now().date()
        except ValueError:
            return Response(
                {'error': 'Неверный формат даты. Используйте YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get clinic filter if admin is clinic-specific
        clinic_id = request.user.clinic_id if hasattr(request.user, 'clinic_id') and request.user.clinic_id else None

        # ==================== REVENUE REPORT ====================
        # Get payments for home appointments
        payments_query = HomeAppointmentKaspiPayment.objects.filter(
            status='paid',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        if clinic_id:
            payments_query = payments_query.filter(appointment__patient__clinic_id=clinic_id)

        total_revenue = payments_query.aggregate(total=Sum('amount'))['total'] or 0

        # Monthly revenue
        monthly_revenue_qs = payments_query.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            revenue=Sum('amount')
        ).order_by('month')

        month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
        monthly_revenue = [
            {
                'month': month_names[item['month'].month - 1],
                'revenue': float(item['revenue'] or 0)
            }
            for item in monthly_revenue_qs
        ]

        # Revenue by service type (home appointments for now)
        revenue_by_service = [
            {
                'service': 'Записи на дом',
                'revenue': float(total_revenue),
                'count': payments_query.count()
            }
        ]

        # ==================== CONSULTATION REPORT ====================
        consultations_query = Consultation.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_deleted=False
        )
        if clinic_id:
            consultations_query = consultations_query.filter(
                Q(patient__clinic_id=clinic_id) | Q(doctor__clinic_id=clinic_id)
            )

        total_consultations = consultations_query.count()

        # Consultations by status
        status_mapping = {
            'pending': 'Ожидание',
            'ongoing': 'В процессе',
            'completed': 'Завершено',
            'cancelled': 'Отменено',
            'missed': 'Пропущено',
            'scheduled': 'Запланировано',
        }
        consultations_by_status = consultations_query.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        by_status = [
            {
                'status': status_mapping.get(item['status'], item['status']),
                'count': item['count']
            }
            for item in consultations_by_status
        ]

        # Consultations by doctor (top 10)
        consultations_by_doctor = consultations_query.values(
            'doctor__first_name', 'doctor__last_name', 'doctor_id'
        ).annotate(
            consultations=Count('id')
        ).order_by('-consultations')[:10]

        by_doctor = [
            {
                'doctor_name': f"Доктор {item['doctor__first_name'] or ''} {item['doctor__last_name'] or ''}".strip(),
                'consultations': item['consultations'],
                'revenue': 0  # TODO: Add consultation pricing when available
            }
            for item in consultations_by_doctor
        ]

        # Consultations by specialization
        consultations_by_spec = consultations_query.values(
            'doctor__doctor_specialization__name_ru'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        by_specialization = [
            {
                'specialization': item['doctor__doctor_specialization__name_ru'] or 'Без специализации',
                'count': item['count']
            }
            for item in consultations_by_spec
        ]

        # ==================== APPOINTMENT REPORT ====================
        appointments_query = HomeAppointment.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_deleted=False
        )
        if clinic_id:
            appointments_query = appointments_query.filter(
                Q(patient__clinic_id=clinic_id) | Q(nurse__clinic_id=clinic_id)
            )

        total_appointments = appointments_query.count()

        # Appointments by status
        appt_status_mapping = {
            'scheduled': 'Запланировано',
            'assigned': 'Назначено',
            'in_progress': 'В процессе',
            'completed': 'Завершено',
            'cancelled': 'Отменено',
        }
        appointments_by_status = appointments_query.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        appt_by_status = [
            {
                'status': appt_status_mapping.get(item['status'], item['status']),
                'count': item['count']
            }
            for item in appointments_by_status
        ]

        # Appointments by nurse (top 10)
        appointments_by_nurse = appointments_query.filter(
            nurse__isnull=False
        ).values(
            'nurse__first_name', 'nurse__last_name'
        ).annotate(
            appointments=Count('id')
        ).order_by('-appointments')[:10]

        by_nurse = [
            {
                'nurse_name': f"Медсестра {item['nurse__first_name'] or ''} {item['nurse__last_name'] or ''}".strip(),
                'appointments': item['appointments']
            }
            for item in appointments_by_nurse
        ]

        # ==================== PATIENT REPORT ====================
        patients_query = User.objects.filter(
            role='patient',
            is_deleted=False
        )
        if clinic_id:
            patients_query = patients_query.filter(clinic_id=clinic_id)

        total_patients = patients_query.count()

        # New patients by month (within date range)
        new_patients_monthly_qs = patients_query.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        new_patients_monthly = [
            {
                'month': month_names[item['month'].month - 1],
                'count': item['count']
            }
            for item in new_patients_monthly_qs
        ]

        # Patients by age group
        from datetime import date
        today = date.today()

        def calculate_age(birth_date):
            if not birth_date:
                return None
            return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        # Get patients with birth dates
        patients_with_age = patients_query.filter(birth_date__isnull=False)

        age_groups = {
            '0-17': 0,
            '18-30': 0,
            '31-50': 0,
            '51-70': 0,
            '70+': 0
        }

        for patient in patients_with_age:
            age = calculate_age(patient.birth_date)
            if age is not None:
                if age <= 17:
                    age_groups['0-17'] += 1
                elif age <= 30:
                    age_groups['18-30'] += 1
                elif age <= 50:
                    age_groups['31-50'] += 1
                elif age <= 70:
                    age_groups['51-70'] += 1
                else:
                    age_groups['70+'] += 1

        by_age_group = [
            {'age_group': group, 'count': count}
            for group, count in age_groups.items()
        ]

        # ==================== COMPILE RESPONSE ====================
        report_data = {
            'revenue_report': {
                'total_revenue': float(total_revenue),
                'monthly_revenue': monthly_revenue,
                'revenue_by_service': revenue_by_service
            },
            'consultation_report': {
                'total_consultations': total_consultations,
                'by_status': by_status,
                'by_doctor': by_doctor,
                'by_specialization': by_specialization
            },
            'appointment_report': {
                'total_appointments': total_appointments,
                'by_status': appt_by_status,
                'by_nurse': by_nurse
            },
            'patient_report': {
                'total_patients': total_patients,
                'new_patients_monthly': new_patients_monthly,
                'by_age_group': by_age_group
            }
        }

        return Response(report_data, status=status.HTTP_200_OK)
