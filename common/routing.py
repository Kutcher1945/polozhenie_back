from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/socketio/', consumers.SocketIOConsumer.as_asgi()),
]