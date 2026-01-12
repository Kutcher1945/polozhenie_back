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
from .models import User, DoctorSpecialization, NurseSpecialization
from rest_framework.authtoken.models import Token
from .serializers import UserSerializer, UserProfileSerializer
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
        if self.action in ['register', 'login', 'forgot_password', 'verify_reset_code', 'reset_password', 'get_available_doctors', 'get_profile_choices']:
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
        operation_description="User login",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="User's email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="User's password"),
            },
            required=["email", "password"],
        ),
        responses={200: "Login successful!", 401: "Invalid credentials", 403: "Account is inactive"},
    )
    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        """Handles user login using email and password."""

        email = request.data.get("email", "").strip()
        password = request.data.get("password")

        print("🔹 Login attempt for email:", email)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({"error": "Неправильный E-mail или пароль."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({"error": "Неправильный E-mail или пароль."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "Account is inactive. Please contact support."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ Remove existing tokens and generate a new one
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        # Use UserProfileSerializer to include all profile fields
        user_serializer = UserProfileSerializer(user)

        return Response(
            {
                "message": "Login successful!",
                "user": user_serializer.data,
                "access_token": token.key,   # ✅ renamed for frontend
                "refresh_token": token.key,  # ❗ you can later change this to separate value
            },
            status=status.HTTP_200_OK,
        )

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
        operation_description="Refresh access token",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh_token": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["refresh_token"],
        ),
        responses={200: "New token returned", 401: "Invalid refresh token"},
    )
    @action(detail=False, methods=["post"], url_path="auth/refresh", url_name="refresh")
    def refresh_token(self, request):
        refresh_token = request.data.get("refresh_token")

        if not refresh_token:
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_obj = Token.objects.get(key=refresh_token)
        except Token.DoesNotExist:
            return Response({"error": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

        # Удаляем старый токен и создаем новый
        token_obj.delete()
        new_token = Token.objects.create(user=token_obj.user)

        return Response({
            "access_token": new_token.key,
        }, status=status.HTTP_200_OK)


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

        # Build query
        if clinic_id:
            # Clinic admin sees only their clinic's staff (both active and inactive)
            staff = User.objects.filter(
                role__in=['doctor', 'nurse'],
                clinic_id=clinic_id,
                is_deleted=False
            )
        else:
            # Super admin sees all staff (both active and inactive)
            staff = User.objects.filter(
                role__in=['doctor', 'nurse'],
                is_deleted=False
            )

        # Serialize staff data
        staff_data = []
        for member in staff:
            specialization = None
            if member.role == 'doctor' and member.doctor_specialization:
                specialization = member.doctor_specialization.name_ru
            elif member.role == 'nurse' and member.nurse_specialization:
                specialization = member.nurse_specialization.name_ru

            staff_data.append({
                'id': member.id,
                'first_name': member.first_name,
                'last_name': member.last_name,
                'email': member.email,
                'phone': member.phone,
                'role': member.role,
                'specialization': specialization,
                'is_active': member.is_active,
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
        password = request.data.get('password')
        role = request.data.get('role')  # 'doctor' or 'nurse'
        specialization = request.data.get('specialization', '')

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
                is_active=True,
                is_deleted=False,
                clinic=clinic
            )

            # Set password (will be hashed automatically by set_password)
            new_staff.set_password(password)
            new_staff.save()

            # Handle specialization (create as simple text for now)
            if specialization:
                if role == 'doctor':
                    # Try to find or create specialization
                    spec, created = DoctorSpecialization.objects.get_or_create(
                        name_ru=specialization,
                        defaults={
                            'name_kz': specialization,
                            'name_en': specialization
                        }
                    )
                    new_staff.doctor_specialization = spec
                elif role == 'nurse':
                    spec, created = NurseSpecialization.objects.get_or_create(
                        name_ru=specialization,
                        defaults={
                            'name_kz': specialization,
                            'name_en': specialization
                        }
                    )
                    new_staff.nurse_specialization = spec
                new_staff.save()

            # Return created staff member data
            return Response({
                'id': new_staff.id,
                'first_name': new_staff.first_name,
                'last_name': new_staff.last_name,
                'email': new_staff.email,
                'phone': new_staff.phone,
                'role': new_staff.role,
                'specialization': specialization,
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
        Update staff member (e.g., toggle active status)
        """
        # Check if user is admin
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Get the staff member
            staff_member = User.objects.get(id=pk, role__in=['doctor', 'nurse'], is_deleted=False)

            # Check if admin has permission to update this staff member
            clinic_id = request.user.clinic_id if hasattr(request.user, 'clinic_id') else None
            if clinic_id and staff_member.clinic_id != clinic_id:
                return Response(
                    {'error': 'У вас нет прав для изменения этого сотрудника'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Update availability_status field if provided
            if 'availability_status' in request.data:
                staff_member.availability_status = request.data['availability_status']
                staff_member.save()

            # Update is_active field if provided (for backward compatibility)
            if 'is_active' in request.data:
                staff_member.is_active = request.data['is_active']
                staff_member.save()

            # Get updated specialization
            specialization = None
            if staff_member.role == 'doctor' and staff_member.doctor_specialization:
                specialization = staff_member.doctor_specialization.name_ru
            elif staff_member.role == 'nurse' and staff_member.nurse_specialization:
                specialization = staff_member.nurse_specialization.name_ru

            # Return updated staff member data
            return Response({
                'id': staff_member.id,
                'first_name': staff_member.first_name,
                'last_name': staff_member.last_name,
                'email': staff_member.email,
                'phone': staff_member.phone,
                'role': staff_member.role,
                'specialization': specialization,
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
