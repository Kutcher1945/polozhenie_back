from rest_framework import viewsets, permissions
from .models import Appointment
from .serializers import AppointmentSerializer
from drf_yasg.utils import swagger_auto_schema



class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff or user.is_superuser:
                return Appointment.objects.all()
            return Appointment.objects.filter(patient=user)
        # When AnonymousUser (for example during schema generation), return empty queryset
        return Appointment.objects.none()

