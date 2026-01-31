"""
Custom JWT Authentication with session validation.
Validates that the session associated with the token is still active.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.utils import timezone


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that validates session status.
    Ensures tokens from revoked sessions are rejected.
    """

    def get_validated_token(self, raw_token):
        """
        Validate token and check if session is revoked.
        """
        validated_token = super().get_validated_token(raw_token)

        # Check if this is an access token (has session_jti claim)
        session_jti = validated_token.get('session_jti')

        if session_jti:
            # Import here to avoid circular imports
            from .models import UserSession

            # Check if the session is still valid
            try:
                session = UserSession.objects.get(
                    refresh_token_jti=session_jti,
                    is_revoked=False,
                    is_deleted=False
                )
                # Update last activity timestamp
                session.last_activity = timezone.now()
                session.save(update_fields=['last_activity', 'updated_at'])

            except UserSession.DoesNotExist:
                raise InvalidToken('Session has been revoked or expired')

        return validated_token

    def authenticate(self, request):
        """
        Authenticate the request and return a tuple of (user, token).
        Falls back to None if JWT auth fails, allowing other authenticators to try.
        """
        try:
            return super().authenticate(request)
        except (InvalidToken, AuthenticationFailed):
            # Return None to allow other authentication classes to try
            # This enables backward compatibility with Token authentication
            return None
