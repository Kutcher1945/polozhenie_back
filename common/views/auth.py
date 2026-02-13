"""
Authentication views: register, login, logout, password reset
"""
import logging
import random
import string
from django.utils import timezone
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import User, UserSession
from ..serializers import UserSerializer, UserProfileSerializer, create_jwt_tokens_for_user
from ..utils.email_utils import send_password_reset_email
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
def csrf_cookie_view(request):
    return JsonResponse({"message": "CSRF cookie set"})


class AuthViewSet(ModelViewSet):
    """
    Authentication endpoints: register, login, logout, password reset
    All endpoints are public (no authentication required)
    """
    queryset = User.objects.none()
    serializer_class = UserSerializer
    permission_classes = []

    def list(self):
        """Disable listing - security risk"""
        return Response(
            {"error": "Listing users is not allowed"},
            status=status.HTTP_403_FORBIDDEN
        )

    def retrieve(self, request, pk=None):
        """Disable retrieving - security risk"""
        return Response(
            {"error": "Direct user access is not allowed"},
            status=status.HTTP_403_FORBIDDEN
        )

    def update(self, request, pk=None):
        """Disable updating through this endpoint"""
        return Response(
            {"error": "User updates not allowed through this endpoint"},
            status=status.HTTP_403_FORBIDDEN
        )

    def partial_update(self, request, pk=None):
        """Disable partial updating through this endpoint"""
        return Response(
            {"error": "User updates not allowed through this endpoint"},
            status=status.HTTP_403_FORBIDDEN
        )

    def destroy(self, request, pk=None):
        """Disable deleting through this endpoint"""
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
            user.reset_code_created_at = timezone.now()
            user.save()

            # Send email with reset code
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

        # Debug incoming data
        print("📥 Incoming reset password request:")
        print("Email:", email)
        print("Reset Code:", reset_code)
        print("New Password (len):", len(new_password))

        if not email or not reset_code or not new_password:
            print("❌ Missing fields in request.")
            return Response({"error": "Все поля обязательны."}, status=status.HTTP_400_BAD_REQUEST)

        try:
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
