from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlayerViewSet, QuestionViewSet, GameSessionViewSet

router = DefaultRouter()
router.register(r'players', PlayerViewSet, basename='players')
router.register(r'questions', QuestionViewSet, basename='questions')
router.register(r'sessions', GameSessionViewSet, basename='sessions')  # 👈 включает /sessions/generate_nickname/

urlpatterns = [
    path('', include(router.urls)),
]
