"""
Session Management Views

This module handles user session management.
Users can view and revoke their active sessions across devices.
"""

import logging
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import UserSession
from ..serializers import UserSessionSerializer

logger = logging.getLogger(__name__)


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
