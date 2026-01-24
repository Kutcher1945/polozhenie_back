from django.urls import path
from . import views

urlpatterns = [
    path('questionnaire/submit/', views.submit_questionnaire, name='submit-questionnaire'),
]

