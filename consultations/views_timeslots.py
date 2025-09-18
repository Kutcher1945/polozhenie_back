"""
API views for timeslot-based consultation booking
"""
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction

from .models import Consultation, TimeSlot, AIRecommendationLog
from .services import ConsultationBookingService, TimeslotManagementService
from .serializers import ConsultationSerializer, TimeSlotSerializer
from common.models import User


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def process_ai_consultation_request(request):
    """
    Process AI recommendation and determine consultation flow

    POST /api/consultations/ai-process/
    {
        "ai_recommendation_id": 123,
        "preferred_doctor_id": 456  // optional
    }

    Returns:
    - If urgent: Creates consultation immediately
    - If non-urgent: Returns available timeslots
    """
    try:
        ai_recommendation_id = request.data.get('ai_recommendation_id')
        preferred_doctor_id = request.data.get('preferred_doctor_id')

        if not ai_recommendation_id:
            return Response(
                {'error': 'ai_recommendation_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ai_recommendation = get_object_or_404(AIRecommendationLog, id=ai_recommendation_id)
        preferred_doctor = None

        if preferred_doctor_id:
            preferred_doctor = get_object_or_404(User, id=preferred_doctor_id, role='doctor')

        # Process the AI recommendation
        result = ConsultationBookingService.process_ai_recommendation(
            patient=request.user,
            ai_recommendation=ai_recommendation,
            preferred_doctor=preferred_doctor
        )

        response_data = {
            'is_urgent': result['is_urgent'],
            'ai_recommendation': {
                'id': ai_recommendation.id,
                'urgency': ai_recommendation.urgency,
                'recommended_specialty': ai_recommendation.recommended_specialty,
                'reason': ai_recommendation.reason
            },
            'recommended_doctor': {
                'id': result['recommended_doctor'].id,
                'first_name': result['recommended_doctor'].first_name,
                'last_name': result['recommended_doctor'].last_name,
                'email': result['recommended_doctor'].email
            } if result['recommended_doctor'] else None
        }

        if result['is_urgent']:
            # Urgent consultation created
            response_data['consultation'] = ConsultationSerializer(result['consultation']).data
            response_data['message'] = 'Экстренная консультация создана. Врач свяжется с вами в ближайшее время.'
        else:
            # Return available timeslots
            timeslots_data = []
            for timeslot in result['available_timeslots'][:20]:  # Limit to 20 slots
                timeslots_data.append({
                    'id': timeslot.id,
                    'start_time': timeslot.start_time,
                    'end_time': timeslot.end_time,
                    'available_spots': timeslot.max_consultations - timeslot.booked_consultations
                })

            response_data['available_timeslots'] = timeslots_data
            response_data['message'] = 'Выберите удобное время для консультации.'

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def book_scheduled_consultation(request):
    """
    Book a scheduled consultation with timeslot

    POST /api/consultations/book-scheduled/
    {
        "timeslot_id": 123,
        "ai_recommendation_id": 456,  // optional
        "scheduled_time": "2024-01-15T10:30:00Z"  // optional, defaults to timeslot start
    }
    """
    try:
        timeslot_id = request.data.get('timeslot_id')
        ai_recommendation_id = request.data.get('ai_recommendation_id')
        scheduled_time_str = request.data.get('scheduled_time')

        if not timeslot_id:
            return Response(
                {'error': 'timeslot_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        timeslot = get_object_or_404(TimeSlot, id=timeslot_id)

        # Validate timeslot availability
        if not timeslot.can_book():
            return Response(
                {'error': 'Выбранный временной слот недоступен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ai_recommendation = None
        if ai_recommendation_id:
            ai_recommendation = get_object_or_404(AIRecommendationLog, id=ai_recommendation_id)

        scheduled_time = None
        if scheduled_time_str:
            try:
                scheduled_time = datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))
            except ValueError:
                return Response(
                    {'error': 'Invalid scheduled_time format. Use ISO format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Book the consultation
        with transaction.atomic():
            consultation = ConsultationBookingService.book_scheduled_consultation(
                patient=request.user,
                timeslot=timeslot,
                ai_recommendation=ai_recommendation,
                scheduled_time=scheduled_time
            )

        return Response({
            'consultation': ConsultationSerializer(consultation).data,
            'message': f'Консультация запланирована на {consultation.scheduled_at.strftime("%Y-%m-%d %H:%M")}'
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_available_timeslots(request):
    """
    Get available timeslots with filtering

    GET /api/consultations/timeslots/available/
    ?doctor_id=123&start_date=2024-01-15&end_date=2024-01-20&limit=50
    """
    try:
        doctor_id = request.GET.get('doctor_id')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        limit = int(request.GET.get('limit', 50))

        doctor = None
        if doctor_id:
            doctor = get_object_or_404(User, id=doctor_id, role='doctor')

        start_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Get available timeslots
        timeslots = TimeSlot.get_available_slots(
            doctor=doctor,
            start_date=start_date,
            end_date=end_date
        )[:limit]

        timeslots_data = []
        for timeslot in timeslots:
            timeslots_data.append({
                'id': timeslot.id,
                'doctor': {
                    'id': timeslot.doctor.id,
                    'first_name': timeslot.doctor.first_name,
                    'last_name': timeslot.doctor.last_name
                },
                'start_time': timeslot.start_time,
                'end_time': timeslot.end_time,
                'available_spots': timeslot.max_consultations - timeslot.booked_consultations,
                'max_consultations': timeslot.max_consultations
            })

        return Response({
            'timeslots': timeslots_data,
            'count': len(timeslots_data)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_patient_consultations(request):
    """
    Get patient's consultations

    GET /api/consultations/my-consultations/
    ?status=scheduled&include_past=false
    """
    try:
        status_filter = request.GET.get('status')
        include_past = request.GET.get('include_past', 'true').lower() == 'true'

        consultations = ConsultationBookingService.get_patient_consultations(
            patient=request.user,
            status_filter=status_filter,
            include_past=include_past
        )

        return Response({
            'consultations': ConsultationSerializer(consultations, many=True).data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_consultation(request, consultation_id):
    """
    Cancel a consultation

    POST /api/consultations/{consultation_id}/cancel/
    {
        "reason": "Optional cancellation reason"
    }
    """
    try:
        consultation = get_object_or_404(
            Consultation,
            id=consultation_id,
            patient=request.user
        )

        reason = request.data.get('reason', '')

        ConsultationBookingService.cancel_consultation(consultation, reason)

        return Response({
            'message': 'Консультация отменена',
            'consultation': ConsultationSerializer(consultation).data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reschedule_consultation(request, consultation_id):
    """
    Reschedule a consultation

    POST /api/consultations/{consultation_id}/reschedule/
    {
        "new_timeslot_id": 123,
        "new_scheduled_time": "2024-01-15T10:30:00Z"  // optional
    }
    """
    try:
        consultation = get_object_or_404(
            Consultation,
            id=consultation_id,
            patient=request.user
        )

        new_timeslot_id = request.data.get('new_timeslot_id')
        new_scheduled_time_str = request.data.get('new_scheduled_time')

        if not new_timeslot_id:
            return Response(
                {'error': 'new_timeslot_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        new_timeslot = get_object_or_404(TimeSlot, id=new_timeslot_id)

        new_scheduled_time = None
        if new_scheduled_time_str:
            try:
                new_scheduled_time = datetime.fromisoformat(new_scheduled_time_str.replace('Z', '+00:00'))
            except ValueError:
                return Response(
                    {'error': 'Invalid new_scheduled_time format. Use ISO format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        with transaction.atomic():
            consultation = ConsultationBookingService.reschedule_consultation(
                consultation=consultation,
                new_timeslot=new_timeslot,
                new_scheduled_time=new_scheduled_time
            )

        return Response({
            'message': f'Консультация перенесена на {consultation.scheduled_at.strftime("%Y-%m-%d %H:%M")}',
            'consultation': ConsultationSerializer(consultation).data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Doctor-specific views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_doctor_consultations(request):
    """
    Get doctor's consultations (only for doctors)

    GET /api/consultations/doctor-consultations/
    ?date=2024-01-15&status=scheduled
    """
    if request.user.role != 'doctor':
        return Response(
            {'error': 'Only doctors can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        date_str = request.GET.get('date')
        status_filter = request.GET.get('status')

        date_filter = None
        if date_str:
            try:
                date_filter = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        consultations = ConsultationBookingService.get_doctor_consultations(
            doctor=request.user,
            date_filter=date_filter,
            status_filter=status_filter
        )

        return Response({
            'consultations': ConsultationSerializer(consultations, many=True).data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_doctor_timeslots(request):
    """
    Generate timeslots for a doctor (only for doctors)

    POST /api/consultations/generate-timeslots/
    {
        "start_date": "2024-01-15",
        "end_date": "2024-01-30",
        "start_hour": 9,
        "end_hour": 18,
        "slot_duration_minutes": 30,
        "max_consultations": 1,
        "weekdays_only": true,
        "excluded_dates": ["2024-01-20", "2024-01-25"]
    }
    """
    if request.user.role != 'doctor':
        return Response(
            {'error': 'Only doctors can generate timeslots'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        data = request.data

        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        start_hour = data.get('start_hour', 9)
        end_hour = data.get('end_hour', 18)
        slot_duration_minutes = data.get('slot_duration_minutes', 30)
        max_consultations = data.get('max_consultations', 1)
        weekdays_only = data.get('weekdays_only', True)
        excluded_dates = data.get('excluded_dates', [])

        # Convert excluded dates
        excluded_date_objects = []
        for date_str in excluded_dates:
            excluded_date_objects.append(datetime.strptime(date_str, '%Y-%m-%d').date())

        slots_created = TimeslotManagementService.bulk_create_timeslots(
            doctor=request.user,
            start_date=start_date,
            end_date=end_date,
            start_hour=start_hour,
            end_hour=end_hour,
            slot_duration_minutes=slot_duration_minutes,
            max_consultations=max_consultations,
            weekdays_only=weekdays_only,
            excluded_dates=excluded_date_objects
        )

        return Response({
            'message': f'Successfully created {slots_created} timeslots',
            'slots_created': slots_created
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )