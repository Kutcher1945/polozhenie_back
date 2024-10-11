from django.urls import path
from .views import CustomTokenObtainPairView, logout

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('logout/', logout, name='logout'),
]
