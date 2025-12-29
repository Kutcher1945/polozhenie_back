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
        # Handle preflight requests with Access-Control-Request-Private-Network
        if request.method == 'OPTIONS' and 'HTTP_ACCESS_CONTROL_REQUEST_PRIVATE_NETWORK' in request.META:
            from django.http import HttpResponse
            response = HttpResponse()
            response['Access-Control-Allow-Private-Network'] = 'true'
            response['Access-Control-Allow-Origin'] = request.META.get('HTTP_ORIGIN', '*')
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = request.META.get(
                'HTTP_ACCESS_CONTROL_REQUEST_HEADERS',
                'accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with'
            )
            response['Access-Control-Allow-Credentials'] = 'true'
            return response

        # Process the request normally
        response = self.get_response(request)

        # Add Private Network Access header to all responses
        if 'HTTP_ORIGIN' in request.META:
            response['Access-Control-Allow-Private-Network'] = 'true'

        return response
