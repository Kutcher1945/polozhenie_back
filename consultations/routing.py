from django.urls import path
from . import consumers
from .consumers_optimized import OptimizedConsultationConsumer

websocket_urlpatterns = [
    # Use optimized consumer for better performance and reliability
    path('ws/consultations/', OptimizedConsultationConsumer.as_asgi()),

    # Keep old consumer as fallback if needed
    path('ws/consultations/legacy/', consumers.ConsultationConsumer.as_asgi()),
]