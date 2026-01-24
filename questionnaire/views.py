import random
import string
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from common.models import User
from common.utils.email_utils import send_welcome_email_with_password
from .models import HealthQuestionnaire
from .serializers import QuestionnaireSubmitSerializer, HealthQuestionnaireSerializer


def generate_simple_password(length=8):
    """Generate a simple, easy-to-remember password"""
    chars = string.ascii_letters + string.digits
    password = ''.join(random.choice(chars) for _ in range(length))
    return password


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def submit_questionnaire(request):
    """
    Submit health questionnaire and create user account.
    Sends email with generated password.
    """
    serializer = QuestionnaireSubmitSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']
    sugar_level = serializer.validated_data['sugar_level']
    systolic_pressure = serializer.validated_data['systolic_pressure']
    diastolic_pressure = serializer.validated_data['diastolic_pressure']

    # Check if user already exists
    if User.objects.filter(email=email).exists():
        return Response(
            {"error": "Пользователь с таким email уже существует. Пожалуйста, войдите в систему."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generate simple password
    password = generate_simple_password(8)

    try:
        # Create user with default first_name and last_name
        user = User.objects.create_user(
            email=email,
            password=password,
            role='patient',
            is_active=True,
            first_name="Не указано",
            last_name="Не указано"
        )

        # Create questionnaire record
        questionnaire = HealthQuestionnaire.objects.create(
            user=user,
            sugar_level=sugar_level,
            systolic_pressure=systolic_pressure,
            diastolic_pressure=diastolic_pressure
        )

        # Send email with password using common utility
        try:
            send_welcome_email_with_password(
                email=email,
                password=password,
                sugar_level=sugar_level,
                systolic=systolic_pressure,
                diastolic=diastolic_pressure
            )
            email_sent = True
        except Exception as email_error:
            print(f"Failed to send email: {email_error}")
            email_sent = False

        return Response({
            "message": "Аккаунт успешно создан! Проверьте вашу почту.",
            "email": email,
            "email_sent": email_sent,
            "questionnaire": HealthQuestionnaireSerializer(questionnaire).data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        # Rollback user creation if something fails
        User.objects.filter(email=email).delete()
        return Response(
            {"error": f"Ошибка при создании аккаунта: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
