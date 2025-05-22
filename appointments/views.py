from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q
from .models import HomeAppointment
from .serializers import HomeAppointmentSerializer
from common.models import User

class HomeAppointmentViewSet(viewsets.ModelViewSet):
    queryset = HomeAppointment.objects.all()
    serializer_class = HomeAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.is_staff or user.is_superuser:
                return HomeAppointment.objects.all()
            elif user.role == 'doctor':
                return HomeAppointment.objects.filter(doctor=user)
            else:
                return HomeAppointment.objects.filter(patient=user)
        return HomeAppointment.objects.none()

    @swagger_auto_schema(
        operation_summary="Get My Home Appointments",
        operation_description="Returns a list of home appointments created by the authenticated patient.",
        responses={200: HomeAppointmentSerializer(many=True)}
    )
    @action(detail=False, methods=["get"], url_path="my-appointments")
    def my_appointments(self, request):
        appointments = HomeAppointment.objects.filter(patient=request.user)
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Get Home Appointments for Doctor",
        operation_description="Returns all home appointments assigned to the authenticated doctor.",
        responses={200: HomeAppointmentSerializer(many=True)}
    )
    @action(detail=False, methods=["get"], url_path="for-doctor")
    def appointments_for_doctor(self, request):
        if request.user.role != 'doctor':
            return Response({"detail": "Access Denied"}, status=status.HTTP_403_FORBIDDEN)

        appointments = HomeAppointment.objects.filter(doctor=request.user)
        serializer = self.get_serializer(appointments, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Cancel a Home Appointment",
        operation_description="Allows a patient or admin to cancel a specific home appointment.",
        responses={200: "Appointment cancelled successfully.", 403: "Permission Denied"}
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_appointment(self, request, pk=None):
        appointment = self.get_object()

        if appointment.patient != request.user and not request.user.is_staff:
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        appointment.status = "cancelled"
        appointment.save()

        return Response({"message": "Appointment cancelled successfully."}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Complete a Home Appointment",
        operation_description="Allows a doctor or admin to mark a home appointment as completed.",
        responses={200: "Appointment completed successfully.", 403: "Permission Denied"}
    )
    @action(detail=True, methods=["post"], url_path="complete")
    def complete_appointment(self, request, pk=None):
        appointment = self.get_object()

        if appointment.doctor != request.user and not request.user.is_staff:
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        appointment.status = "completed"
        appointment.save()

        return Response({"message": "Appointment completed successfully."}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Get Available Doctors for 'Сестринское дело'",
        operation_description="Returns a list of doctors specialized in 'Сестринское дело' for home appointments.",
        responses={200: "List of doctors."}
    )
    @action(detail=False, methods=["get"], url_path="available-doctors-sestrinskoe-delo")
    def available_doctors_sestrinskoe_delo(self, request):
        doctors = User.objects.filter(role="doctor", doctor_type="Сестринское дело", is_active=True)

        doctor_data = [
            {
                "id": doc.id,
                "name": f"{doc.first_name} {doc.last_name}",
                "email": doc.email,
                "doctor_type": doc.doctor_type,
            }
            for doc in doctors
        ]

        return Response({"doctors": doctor_data}, status=status.HTTP_200_OK)