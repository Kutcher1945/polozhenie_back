from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/consultations/', consumers.ConsultationConsumer.as_asgi()),
]