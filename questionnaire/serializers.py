from rest_framework import serializers
from .models import HealthQuestionnaire


class QuestionnaireSubmitSerializer(serializers.Serializer):
    """Serializer for questionnaire submission with account creation"""

    email = serializers.EmailField()
    sugar_level = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=50)
    systolic_pressure = serializers.IntegerField(min_value=60, max_value=250)
    diastolic_pressure = serializers.IntegerField(min_value=40, max_value=150)


class HealthQuestionnaireSerializer(serializers.ModelSerializer):
    """Serializer for HealthQuestionnaire model"""

    sugar_status = serializers.ReadOnlyField()
    pressure_status = serializers.ReadOnlyField()

    class Meta:
        model = HealthQuestionnaire
        fields = [
            'id',
            'sugar_level',
            'systolic_pressure',
            'diastolic_pressure',
            'sugar_status',
            'pressure_status',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
