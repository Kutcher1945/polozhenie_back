"""
Dynamic timeslot system - generates slots on demand and tracks only bookings
"""
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
from django.db import transaction
import logging

from .models import Consultation, AIRecommendationLog
from .serializers import ConsultationSerializer
from common.models import User
from common.utils.email_utils import send_consultation_created_email

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_doctor_booked_slots(request, doctor_id):
    """
    Get only the BOOKED consultation slots for a doctor

    GET /api/consultations/doctor/{doctor_id}/booked-slots/
    ?start_date=2024-01-15&end_date=2024-01-30

    Returns only the times that are already booked, not all possible slots
    """
    try:
        print(f"🔍 get_doctor_booked_slots called for doctor_id={doctor_id}")
        print(f"🔍 GET params: {request.GET}")

        doctor = get_object_or_404(User, id=doctor_id, role='doctor')

        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        print(f"🔍 Date range: {start_date_str} to {end_date_str}")

        start_date = None
        end_date = None

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Get only BOOKED consultations (not all possible slots)
        consultations = Consultation.objects.filter(
            doctor=doctor,
            status__in=['scheduled', 'in_progress', 'completed']  # Not cancelled
        )

        if start_date:
            consultations = consultations.filter(scheduled_at__date__gte=start_date)

        if end_date:
            consultations = consultations.filter(scheduled_at__date__lte=end_date)

        # Extract just the datetime strings of booked slots
        booked_slots = [
            consultation.scheduled_at.isoformat()
            for consultation in consultations
            if consultation.scheduled_at
        ]

        print(f"🔍 Found {len(booked_slots)} booked consultations")
        if booked_slots:
            print(f"🔍 Sample booked slots: {booked_slots[:3]}")

        response_data = {
            'booked_slots': booked_slots,
            'count': len(booked_slots)
        }
        print(f"📨 Returning response: {response_data}")

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def book_dynamic_slot(request):
    """
    Book a consultation at a specific time (without pre-created TimeSlot)

    POST /api/consultations/book-dynamic-slot/
    {
        "doctor_id": 123,
        "scheduled_time": "2024-01-15T10:00:00Z",
        "ai_recommendation_id": 456
    }
    """
    try:
        doctor_id = request.data.get('doctor_id')
        scheduled_time_str = request.data.get('scheduled_time')
        ai_recommendation_id = request.data.get('ai_recommendation_id')

        print(f"🔍 book_dynamic_slot called with:")
        print(f"   doctor_id: {doctor_id}")
        print(f"   scheduled_time: {scheduled_time_str}")
        print(f"   ai_recommendation_id: {ai_recommendation_id}")
        print(f"   user: {request.user}")

        if not doctor_id:
            return Response(
                {'error': 'doctor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not scheduled_time_str:
            return Response(
                {'error': 'scheduled_time is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        doctor = get_object_or_404(User, id=doctor_id, role='doctor')

        try:
            scheduled_time = datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))
        except ValueError:
            return Response(
                {'error': 'Invalid scheduled_time format. Use ISO format.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Make sure the time is in the future
        if scheduled_time <= timezone.now():
            return Response(
                {'error': 'Scheduled time must be in the future'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ai_recommendation = None
        if ai_recommendation_id:
            try:
                ai_recommendation = AIRecommendationLog.objects.get(id=ai_recommendation_id)
                print(f"✅ Found AI recommendation: {ai_recommendation.id}")
            except AIRecommendationLog.DoesNotExist:
                print(f"❌ AI recommendation {ai_recommendation_id} not found")
                return Response(
                    {'error': f'AI recommendation {ai_recommendation_id} not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Check if this exact time slot is already booked
        existing_consultation = Consultation.objects.filter(
            doctor=doctor,
            scheduled_at=scheduled_time,
            status__in=['scheduled', 'in_progress']  # Active bookings
        ).first()

        if existing_consultation:
            return Response(
                {'error': 'This time slot is already booked'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the consultation (without consultation_type field)
        print(f"🔄 Creating consultation...")
        print(f"   patient: {request.user}")
        print(f"   doctor: {doctor}")
        print(f"   scheduled_at: {scheduled_time}")
        print(f"   ai_recommendation: {ai_recommendation}")

        try:
            with transaction.atomic():
                consultation = Consultation.objects.create(
                    patient=request.user,
                    doctor=doctor,
                    scheduled_at=scheduled_time,
                    status='scheduled',
                    meeting_id=f"meeting_{request.user.id}_{doctor.id}_{int(scheduled_time.timestamp())}",
                    ai_recommendation=ai_recommendation
                )
                print(f"✅ Consultation created successfully: {consultation.id}")
        except Exception as create_error:
            print(f"❌ Error creating consultation: {create_error}")
            raise

        # 📧 Send email notification to patient
        print(f"📧 Attempting to send email notification...")
        print(f"   Patient email: {request.user.email}")
        print(f"   Access code: {consultation.access_code}")
        print(f"   Scheduled at: {consultation.scheduled_at}")

        try:
            patient_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email.split("@")[0]
            doctor_name = f"{doctor.first_name} {doctor.last_name}".strip() or "Врач"

            # Build consultation link
            consultation_link = f"{settings.FRONTEND_URL}/video-call/patient?meetingId={consultation.meeting_id}"

            print(f"   Patient name: {patient_name}")
            print(f"   Doctor name: {doctor_name}")
            print(f"   Consultation link: {consultation_link}")
            print(f"   Calling send_consultation_created_email()...")

            send_consultation_created_email(
                patient_email=request.user.email,
                patient_name=patient_name,
                doctor_name=doctor_name,
                access_code=consultation.access_code,
                consultation_link=consultation_link,
                scheduled_at=consultation.scheduled_at
            )

            print(f"✅ Email sent successfully to {request.user.email}!")
            logger.info(f"✅ Email sent to {request.user.email} for scheduled consultation {consultation.id}")
        except Exception as email_error:
            # Log error but don't fail the consultation creation
            print(f"❌ EMAIL SENDING FAILED!")
            print(f"   Error: {str(email_error)}")
            print(f"   Error type: {type(email_error).__name__}")

            import traceback
            print(f"   Traceback:")
            traceback.print_exc()

            logger.error(f"❌ Failed to send email notification: {str(email_error)}")
            logger.error(f"   Full traceback:", exc_info=True)

        print(f"🔄 Serializing consultation data...")
        consultation_data = ConsultationSerializer(consultation).data
        print(f"✅ Serialization successful")

        return Response({
            'consultation': consultation_data,
            'message': f'Консультация запланирована на {consultation.scheduled_at.strftime("%Y-%m-%d %H:%M")}'
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        print(f"❌ Unexpected error in book_dynamic_slot: {e}")
        print(f"❌ Error type: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_doctor_availability_rules(request, doctor_id):
    """
    Get doctor's availability rules (working hours, days off, etc.)
    This is much more efficient than storing millions of individual slots

    GET /api/consultations/doctor/{doctor_id}/availability/
    """
    try:
        doctor = get_object_or_404(User, id=doctor_id, role='doctor')

        # 24/7 medical service availability
        availability = {
            'working_days': [0, 1, 2, 3, 4, 5, 6],  # All 7 days (Sunday to Saturday)
            'working_hours': {
                'start': '00:00',
                'end': '23:59'
            },
            'slot_duration_minutes': 15,
            'break_times': [],  # No breaks in emergency medical service
            'days_off': [],  # No days off - 24/7 service
            'max_bookings_per_slot': 1
        }

        return Response({
            'doctor_id': doctor_id,
            'availability': availability
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )