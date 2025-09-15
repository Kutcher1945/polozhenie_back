import logging
from drf_yasg import openapi
from django.conf import settings
from django.utils import timezone
import random
import string
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from .models import User, CustomToken
from .serializers import UserSerializer, UserProfileSerializer
from .permissions import IsDoctor, IsAdmin
from .utils.email_utils import send_password_reset_email
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def csrf_cookie_view(request):
    return JsonResponse({"message": "CSRF cookie set"})

class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    
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

        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password")

        print("🔹 Login attempt for email:", email)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Неправильный E-mail или пароль."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({"error": "Неправильный E-mail или пароль."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "Account is inactive. Please contact support."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ Remove existing tokens and generate a new one
        CustomToken.objects.filter(user=user).delete()
        token = CustomToken.objects.create(user=user)

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
        email = request.data.get("email", "").strip().lower()

        try:
            user = User.objects.get(email=email)
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
        email = request.data.get("email", "").strip().lower()
        reset_code = request.data.get("reset_code", "").strip().upper()
    
        if not email or not reset_code:
            return Response({"error": "Email и код обязательны."}, status=status.HTTP_400_BAD_REQUEST)
    
        try:
            user = User.objects.get(email=email, reset_code__iexact=reset_code)
    
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
        email = request.data.get("email", "").strip().lower()
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
            # ✅ Use case-insensitive matching for reset_code
            user = User.objects.get(email=email, reset_code__iexact=reset_code)
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

    # ✅ New endpoint to fetch available doctors
    @swagger_auto_schema(
        operation_description="Get available doctors",
        responses={200: "List of available doctors"},
    )
    @action(detail=False, methods=["get"], url_path="doctor/available")
    def get_available_doctors(self, request):
        """Fetch a list of available doctors."""
        doctors = User.objects.filter(role="doctor", is_active=True)

        if not doctors.exists():
            return Response({"error": "No available doctors found."}, status=status.HTTP_404_NOT_FOUND)

        doctor_list = [
            {
                "id": doctor.id,
                "name": f"{doctor.first_name} {doctor.last_name}",
                "email": doctor.email,
                "doctor_type": doctor.doctor_type,  # 🆕 Add doctor_type field
            }
            for doctor in doctors
        ]
        return Response({"doctors": doctor_list}, status=status.HTTP_200_OK)

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
                from common.models import CustomToken
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header.startswith('Token '):
                    token_key = auth_header.split(' ')[1]
                    token = CustomToken.objects.select_related('user').get(key=token_key)
                    user = token.user
                else:
                    return Response({'error': 'Authentication token required'}, status=status.HTTP_401_UNAUTHORIZED)
        except CustomToken.DoesNotExist:
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
            token_obj = CustomToken.objects.get(key=refresh_token)
        except CustomToken.DoesNotExist:
            return Response({"error": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

        # Удаляем старый токен и создаем новый
        token_obj.delete()
        new_token = CustomToken.objects.create(user=token_obj.user)

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