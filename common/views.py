import logging
from drf_yasg import openapi
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

logger = logging.getLogger(__name__)

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
            return Response({"error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({"error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "Account is inactive. Please contact support."}, status=status.HTTP_403_FORBIDDEN)

        # ✅ Remove existing tokens and generate a new one
        CustomToken.objects.filter(user=user).delete()
        token = CustomToken.objects.create(user=user)

        return Response(
            {
                "message": "Login successful!",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                },
                "access_token": token.key,   # ✅ renamed for frontend
                "refresh_token": token.key,  # ❗ you can later change this to separate value
            },
            status=status.HTTP_200_OK,
        )


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

class UserProfileViewSet(ViewSet):
    """
    A ViewSet for handling user profile operations.
    """

    @swagger_auto_schema(
        operation_description="Fetch the authenticated user's profile",
        responses={200: UserProfileSerializer},
    )
    @action(detail=False, methods=["get"], url_path="profile")
    def myprofile(self, request):
        """
        Retrieve the authenticated user's profile.
        """
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
