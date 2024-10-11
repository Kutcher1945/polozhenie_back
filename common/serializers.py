from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from rest_framework import serializers

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims here if needed, e.g., token['email'] = user.email
        return token

    def validate(self, attrs):
        # Modify this if needed to handle email or username for login
        data = super().validate(attrs)

        # Add more data to the response if necessary
        data['username'] = self.user.username
        return data
