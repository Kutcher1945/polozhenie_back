"""
User Profile Views

This module handles user profile operations for all roles.
Users can view and update their own profile information.
"""

import logging
from drf_yasg import openapi
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authtoken.models import Token

from ..models import User
from ..serializers import UserProfileSerializer, refresh_jwt_tokens

logger = logging.getLogger(__name__)


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

        # Get profile based on role
        profile = None
        if user_role == 'doctor' and hasattr(user, 'doctor_profile'):
            profile = user.doctor_profile
        elif user_role == 'nurse' and hasattr(user, 'nurse_profile'):
            profile = user.nurse_profile

        if not profile:
            return Response(
                {"error": "Profile not found for user"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Store old status for change detection
        old_status = profile.availability_status

        # Update availability on profile
        profile.availability_status = availability_status
        profile.availability_note = availability_note
        profile.save()
        print(f"[DEBUG] Updated {user.email} availability from {old_status} -> {availability_status}")

        # Broadcast availability change via WebSocket with FULL doctor/nurse data
        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                # Prepare full data based on role
                if user_role == 'doctor':
                    event_type = 'doctor_availability_changed'
                    user_id_key = 'doctor_id'

                    # Get clinic information from doctor profile
                    clinic_data = None
                    if hasattr(user, 'doctor_profile') and user.doctor_profile and user.doctor_profile.clinic:
                        clinic = user.doctor_profile.clinic
                        clinic_data = {
                            "id": clinic.id,
                            "name": clinic.name,
                            "address": clinic.address or None,
                            "phone": clinic.phones if hasattr(clinic, 'phones') else None,
                            "city": clinic.city.name_ru if clinic.city else None,
                        }

                    # Get specialization
                    doctor_specialization = None
                    if hasattr(user, 'doctor_profile') and user.doctor_profile and user.doctor_profile.specialization:
                        doctor_specialization = user.doctor_profile.specialization
                        specialization = doctor_specialization.name_ru
                    else:
                        specialization = "Специальность не указана"

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
                            "id": doctor_specialization.id if doctor_specialization else None,
                            "name_ru": doctor_specialization.name_ru if doctor_specialization else None,
                            "name_kz": doctor_specialization.name_kz if doctor_specialization else None,
                            "name_en": doctor_specialization.name_en if doctor_specialization else None,
                        } if doctor_specialization else None
                    }
                else:  # nurse
                    event_type = 'nurse_availability_changed'
                    user_id_key = 'nurse_id'

                    # Get clinic information from nurse profile
                    clinic_data = None
                    if hasattr(user, 'nurse_profile') and user.nurse_profile and user.nurse_profile.clinic:
                        clinic = user.nurse_profile.clinic
                        clinic_data = {
                            "id": clinic.id,
                            "name": clinic.name,
                            "address": clinic.address or None,
                            "phone": clinic.phones if hasattr(clinic, 'phones') else None,
                            "city": clinic.city.name_ru if clinic.city else None,
                        }

                    # Get specialization
                    nurse_specialization = None
                    if hasattr(user, 'nurse_profile') and user.nurse_profile and user.nurse_profile.specialization:
                        nurse_specialization = user.nurse_profile.specialization
                        specialization = nurse_specialization.name_ru
                    else:
                        specialization = "Специальность не указана"

                    full_data = {
                        "id": user.id,
                        "name": f"{user.first_name} {user.last_name}",
                        "email": user.email,
                        "nurse_type": specialization,
                        "availability_status": availability_status,
                        "availability_note": availability_note,
                        "clinic": clinic_data,
                        "specialization": {
                            "id": nurse_specialization.id if nurse_specialization else None,
                            "name_ru": nurse_specialization.name_ru if nurse_specialization else None,
                            "name_kz": nurse_specialization.name_kz if nurse_specialization else None,
                            "name_en": nurse_specialization.name_en if nurse_specialization else None,
                        } if nurse_specialization else None
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
