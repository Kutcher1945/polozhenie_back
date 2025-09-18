from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConsultationViewSet, csrf_token_view
from .views_timeslots import (
    process_ai_consultation_request,
    book_scheduled_consultation,
    get_available_timeslots,
    get_patient_consultations,
    cancel_consultation,
    reschedule_consultation,
    get_doctor_consultations,
    generate_doctor_timeslots
)
from .views_dynamic_slots import (
    get_doctor_booked_slots,
    book_dynamic_slot,
    get_doctor_availability_rules
)

router = DefaultRouter()
router.register(r'consultations', ConsultationViewSet, basename='consultations')

urlpatterns = [
    # Timeslot-based consultation booking endpoints (before router to avoid conflicts)
    path('consultations/ai-process/', process_ai_consultation_request, name='ai_consultation_process'),
    path('consultations/book-scheduled/', book_scheduled_consultation, name='book_scheduled_consultation'),
    path('consultations/timeslots/available/', get_available_timeslots, name='available_timeslots'),
    path('consultations/my-consultations/', get_patient_consultations, name='patient_consultations'),
    path('consultations/<int:consultation_id>/cancel/', cancel_consultation, name='cancel_consultation'),
    path('consultations/<int:consultation_id>/reschedule/', reschedule_consultation, name='reschedule_consultation'),

    # Doctor-specific endpoints
    path('consultations/doctor-consultations/', get_doctor_consultations, name='doctor_consultations'),
    path('consultations/generate-timeslots/', generate_doctor_timeslots, name='generate_timeslots'),

    # Dynamic timeslot system endpoints
    path('consultations/doctor/<int:doctor_id>/booked-slots/', get_doctor_booked_slots, name='doctor_booked_slots'),
    path('consultations/book-dynamic-slot/', book_dynamic_slot, name='book_dynamic_slot'),
    path('consultations/doctor/<int:doctor_id>/availability/', get_doctor_availability_rules, name='doctor_availability'),

    # CSRF endpoint
    path("csrf/", csrf_token_view, name="csrf_token_view"),

    # Router URLs (put last to avoid conflicts)
    path('', include(router.urls)),
]
