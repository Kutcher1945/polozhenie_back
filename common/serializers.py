from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "phone", "email", "password", "role", "role_display"]
        extra_kwargs = {"password": {"write_only": True}}

    def get_role_display(self, obj):
        return dict(User.ROLE_CHOICES).get(obj.role, "Неизвестно")


    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def create(self, validated_data):
        return User.objects.create(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile details."""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'phone', 'email',]
        read_only_fields = ['email']

