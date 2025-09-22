"""
ASGI config for mchs_back project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from consultations.routing import websocket_urlpatterns as consultation_patterns
from common.routing import websocket_urlpatterns as common_patterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mchs_back.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            consultation_patterns + common_patterns
        )
    ),
})
