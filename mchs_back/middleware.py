"""
Custom middleware for handling Private Network Access (CORS-RFC1918)
"""

class PrivateNetworkAccessMiddleware:
    """
    Middleware to handle Chrome's Private Network Access preflight requests.
    This fixes the "Permission was denied to access unknown address space" error.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get('HTTP_ORIGIN', '')

        # List of allowed origins
        allowed_origins = [
            'http://localhost:3000',
            'https://www.zhan.care',
            'https://www.zhancare.app',
            'https://zhan.care',
            'https://zhancare.app',
        ]

        # Check if origin is allowed
        origin_allowed = origin in allowed_origins

        # Handle preflight requests (OPTIONS)
        if request.method == 'OPTIONS':
            from django.http import HttpResponse
            response = HttpResponse()

            # Set CORS headers
            if origin_allowed:
                response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = request.META.get(
                'HTTP_ACCESS_CONTROL_REQUEST_HEADERS',
                'accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with'
            )
            response['Access-Control-Allow-Credentials'] = 'true'

            # Handle Private Network Access
            if 'HTTP_ACCESS_CONTROL_REQUEST_PRIVATE_NETWORK' in request.META:
                response['Access-Control-Allow-Private-Network'] = 'true'

            response['Access-Control-Max-Age'] = '86400'  # Cache preflight for 24 hours
            return response

        # Process the request normally
        response = self.get_response(request)

        # Add CORS headers to all responses
        if origin_allowed:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Private-Network'] = 'true'
            response['Access-Control-Expose-Headers'] = 'content-type, x-csrftoken'

        return response
