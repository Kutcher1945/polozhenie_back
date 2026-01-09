from rest_framework.permissions import BasePermission
from django.core.cache import cache
from django.conf import settings
import hashlib


class IsAuthenticatedOrAIRecommendation(BasePermission):
    """
    Custom permission that:
    - Allows authenticated users to access all endpoints
    - Allows unauthenticated users to access only the ai-recommend endpoint
    - Implements rate limiting and origin checking for ai-recommend
    """

    def has_permission(self, request, view):
        # If user is authenticated, allow all actions
        if request.user and request.user.is_authenticated:
            return True

        # For unauthenticated users, only allow ai-recommend action
        if view.action == 'ai_recommend_doctor':
            # Check if request is from allowed origins
            origin = request.META.get('HTTP_ORIGIN', '')
            referer = request.META.get('HTTP_REFERER', '')

            # Allow requests from your frontend domains
            allowed_domains = [
                'localhost',
                '127.0.0.1',
                'zhan.care',
                'www.zhan.care',
            ]

            # Check if origin or referer contains allowed domain
            is_allowed_origin = any(domain in origin or domain in referer for domain in allowed_domains)

            if not is_allowed_origin and settings.DEBUG is False:
                # In production, block requests from unknown origins
                return False

            # Implement rate limiting based on IP address
            ip_address = self.get_client_ip(request)
            rate_limit_key = f"ai_recommend_rate_limit_{ip_address}"

            # Check rate limit: max 10 requests per 10 minutes per IP
            request_count = cache.get(rate_limit_key, 0)

            if request_count >= 10:
                return False

            # Increment counter
            cache.set(rate_limit_key, request_count + 1, 600)  # 10 minutes

            return True

        # Block all other actions for unauthenticated users
        return False

    @staticmethod
    def get_client_ip(request):
        """Get the client's IP address from the request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RateLimitPermission(BasePermission):
    """
    Rate limiting permission for AI recommendations
    Limits: 10 requests per 10 minutes per IP
    """

    def has_permission(self, request, view):
        ip_address = self.get_client_ip(request)
        rate_limit_key = f"ai_recommend_rate_limit_{ip_address}"

        # Get current request count
        request_count = cache.get(rate_limit_key, 0)

        # Check if limit exceeded
        if request_count >= 10:
            return False

        # Increment counter (10 minutes = 600 seconds)
        cache.set(rate_limit_key, request_count + 1, 600)

        return True

    @staticmethod
    def get_client_ip(request):
        """Get the client's IP address from the request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
