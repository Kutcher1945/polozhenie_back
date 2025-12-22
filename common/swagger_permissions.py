"""
Custom permissions for Swagger/ReDoc documentation
"""
from rest_framework import permissions
from django.contrib.auth import authenticate
from django.http import HttpResponse
import base64


class SwaggerAccessPermission(permissions.BasePermission):
    """
    Custom permission for Swagger/ReDoc access.

    Allows access if:
    1. User is staff/superuser (Django admin)
    2. Valid DRF Token provided
    3. Valid Basic Authentication (for external tools)
    """

    def has_permission(self, request, view):
        # 1. Check if user is authenticated via Django session (admin)
        if request.user and request.user.is_authenticated:
            # Only allow staff or superuser
            if request.user.is_staff or request.user.is_superuser:
                return True

        # 2. Check for DRF Token Authentication
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token '):
            token_key = auth_header.split(' ')[1]
            try:
                from rest_framework.authtoken.models import Token
                token = Token.objects.select_related('user').get(key=token_key)
                if token.user.is_staff or token.user.is_superuser:
                    return True
            except Token.DoesNotExist:
                pass

        # 3. Check for Basic Authentication
        if auth_header.startswith('Basic '):
            try:
                auth_decoded = base64.b64decode(auth_header.split(' ')[1]).decode('utf-8')
                username, password = auth_decoded.split(':', 1)

                # Try to authenticate with email (our custom User model uses email)
                user = authenticate(request=request, email=username, password=password)

                # If that fails, try with username field directly
                if not user:
                    from common.models import User
                    try:
                        user_obj = User.objects.get(email=username)
                        if user_obj.check_password(password):
                            user = user_obj
                    except User.DoesNotExist:
                        pass

                if user and (user.is_staff or user.is_superuser):
                    return True
            except Exception:
                pass

        return False


def swagger_basic_auth_required(view_func):
    """
    Decorator that requires Basic Authentication for Swagger views.
    Returns 401 with WWW-Authenticate header if not authenticated.
    """
    def wrapped_view(request, *args, **kwargs):
        # Check if user is authenticated
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        # Allow Django session auth (for admins)
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return view_func(request, *args, **kwargs)

        # Check for Basic Auth
        if auth_header.startswith('Basic '):
            try:
                auth_decoded = base64.b64decode(auth_header.split(' ')[1]).decode('utf-8')
                username, password = auth_decoded.split(':', 1)

                # Try to authenticate with email (our custom User model uses email)
                user = authenticate(request=request, email=username, password=password)

                # If that fails, try with username field directly
                if not user:
                    from common.models import User
                    try:
                        user_obj = User.objects.get(email=username)
                        if user_obj.check_password(password):
                            user = user_obj
                    except User.DoesNotExist:
                        pass

                if user and (user.is_staff or user.is_superuser):
                    return view_func(request, *args, **kwargs)
            except Exception as e:
                print(f"Basic auth error: {e}")
                pass

        # Check for Token Auth
        if auth_header.startswith('Token '):
            token_key = auth_header.split(' ')[1]
            try:
                from rest_framework.authtoken.models import Token
                token = Token.objects.select_related('user').get(key=token_key)
                if token.user.is_staff or token.user.is_superuser:
                    return view_func(request, *args, **kwargs)
            except Token.DoesNotExist:
                pass

        # Return 401 Unauthorized with WWW-Authenticate header
        response = HttpResponse(
            '<h1>401 Unauthorized</h1>'
            '<p>Access to API documentation requires authentication.</p>'
            '<p>Please login as staff or superuser.</p>',
            status=401
        )
        response['WWW-Authenticate'] = 'Basic realm="Swagger API Documentation"'
        return response

    return wrapped_view


def staff_required(view_func):
    """
    Simple decorator that requires staff or superuser access.
    Redirects to login page if not authenticated.
    """
    from django.contrib.auth.decorators import user_passes_test

    def is_staff(user):
        return user.is_authenticated and (user.is_staff or user.is_superuser)

    return user_passes_test(is_staff, login_url='/admin/login/')(view_func)
