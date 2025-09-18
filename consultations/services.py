"""
Consultation booking services that integrate AI recommendations with timeslot system
"""
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .models import Consultation, TimeSlot, AIRecommendationLog
from common.models import User


class ConsultationBookingService:
    """
    Service class for handling consultation booking logic based on AI urgency recommendations
    """

    @staticmethod
    def process_ai_recommendation(
        patient: User,
        ai_recommendation: AIRecommendationLog,
        preferred_doctor: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Process AI recommendation and determine consultation flow

        Returns:
        - If urgent: Creates immediate consultation
        - If non-urgent: Returns available timeslots for booking
        """

        result = {
            'is_urgent': ai_recommendation.urgency == 'urgent',
            'ai_recommendation': ai_recommendation,
            'consultation': None,
            'available_timeslots': [],
            'recommended_doctor': None
        }

        # Determine the doctor to use
        doctor = preferred_doctor or ai_recommendation.matched_doctor
        if not doctor:
            # Fallback to first available doctor of the recommended specialty
            doctors = User.objects.filter(
                role='doctor',
                doctor_profile__specialty=ai_recommendation.recommended_specialty
            )
            doctor = doctors.first()

        if not doctor:
            raise ValidationError(f"Нет доступных врачей по специальности: {ai_recommendation.recommended_specialty}")

        result['recommended_doctor'] = doctor

        if ai_recommendation.urgency == 'urgent':
            # Create urgent consultation immediately
            consultation = Consultation.create_urgent_consultation(
                patient=patient,
                doctor=doctor,
                ai_recommendation=ai_recommendation
            )
            result['consultation'] = consultation
        else:
            # Get available timeslots for the next 14 days
            end_date = timezone.now().date() + timedelta(days=14)
            available_slots = TimeSlot.get_available_slots(
                doctor=doctor,
                start_date=timezone.now().date(),
                end_date=end_date
            )
            result['available_timeslots'] = list(available_slots)

        return result

    @staticmethod
    def book_scheduled_consultation(
        patient: User,
        timeslot: TimeSlot,
        ai_recommendation: Optional[AIRecommendationLog] = None,
        scheduled_time: Optional[datetime] = None
    ) -> Consultation:
        """
        Book a scheduled consultation with specific timeslot
        """
        if not timeslot.can_book():
            raise ValidationError("Выбранный временной слот недоступен")

        consultation = Consultation.create_scheduled_consultation(
            patient=patient,
            doctor=timeslot.doctor,
            timeslot=timeslot,
            ai_recommendation=ai_recommendation,
            scheduled_time=scheduled_time
        )

        return consultation

    @staticmethod
    def get_patient_consultations(
        patient: User,
        status_filter: Optional[str] = None,
        include_past: bool = True
    ) -> List[Consultation]:
        """
        Get patient's consultations with optional filtering
        """
        queryset = Consultation.objects.filter(patient=patient)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if not include_past:
            from django.db import models as django_models
            queryset = queryset.filter(
                django_models.Q(scheduled_at__gte=timezone.now()) |
                django_models.Q(scheduled_at__isnull=True, status__in=['pending', 'ongoing'])
            )

        return queryset.order_by('-created_at')

    @staticmethod
    def get_doctor_consultations(
        doctor: User,
        date_filter: Optional[datetime.date] = None,
        status_filter: Optional[str] = None
    ) -> List[Consultation]:
        """
        Get doctor's consultations with optional filtering
        """
        queryset = Consultation.objects.filter(doctor=doctor)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if date_filter:
            from django.db import models as django_models
            queryset = queryset.filter(
                django_models.Q(scheduled_at__date=date_filter) |
                django_models.Q(created_at__date=date_filter, scheduled_at__isnull=True)
            )

        return queryset.order_by('scheduled_at', 'created_at')

    @staticmethod
    def get_upcoming_consultations(
        doctor: User,
        hours_ahead: int = 24
    ) -> List[Consultation]:
        """
        Get doctor's upcoming consultations within specified hours
        """
        now = timezone.now()
        future_time = now + timedelta(hours=hours_ahead)

        return Consultation.objects.filter(
            doctor=doctor,
            status__in=['scheduled', 'pending'],
            scheduled_at__range=[now, future_time]
        ).order_by('scheduled_at')

    @staticmethod
    def cancel_consultation(consultation: Consultation, reason: str = "") -> bool:
        """
        Cancel a consultation and free up timeslot if applicable
        """
        if consultation.status in ['completed', 'cancelled']:
            raise ValidationError("Консультация уже завершена или отменена")

        if consultation.status == 'ongoing':
            raise ValidationError("Нельзя отменить консультацию в процессе")

        # Free up timeslot if it's a scheduled consultation
        if consultation.timeslot and consultation.status == 'scheduled':
            consultation.cancel_schedule()
        else:
            consultation.status = 'cancelled'
            consultation.save()

        return True

    @staticmethod
    def reschedule_consultation(
        consultation: Consultation,
        new_timeslot: TimeSlot,
        new_scheduled_time: Optional[datetime] = None
    ) -> Consultation:
        """
        Reschedule a consultation to a new timeslot
        """
        if consultation.status not in ['scheduled', 'pending']:
            raise ValidationError("Можно перенести только запланированные или ожидающие консультации")

        if consultation.is_urgent:
            raise ValidationError("Экстренные консультации нельзя переносить")

        if not new_timeslot.can_book():
            raise ValidationError("Новый временной слот недоступен")

        # Free up old timeslot
        if consultation.timeslot:
            consultation.timeslot.cancel_booking()

        # Book new timeslot
        consultation.schedule_with_timeslot(new_timeslot, new_scheduled_time)

        return consultation

    @staticmethod
    def check_consultation_reminders() -> List[Consultation]:
        """
        Get consultations that need reminders (scheduled within next 15 minutes)
        """
        now = timezone.now()
        reminder_time = now + timedelta(minutes=15)

        return Consultation.objects.filter(
            status='scheduled',
            scheduled_at__range=[now, reminder_time]
        )


class TimeslotManagementService:
    """
    Service for managing doctor timeslots
    """

    @staticmethod
    def bulk_create_timeslots(
        doctor: User,
        start_date: datetime.date,
        end_date: datetime.date,
        start_hour: int = 9,
        end_hour: int = 18,
        slot_duration_minutes: int = 30,
        max_consultations: int = 1,
        weekdays_only: bool = True,
        excluded_dates: Optional[List[datetime.date]] = None
    ) -> int:
        """
        Bulk create timeslots for a doctor
        """
        if excluded_dates is None:
            excluded_dates = []

        slots_created = 0
        current_date = start_date

        while current_date <= end_date:
            # Skip weekends if weekdays_only is True
            if weekdays_only and current_date.weekday() > 4:
                current_date += timedelta(days=1)
                continue

            # Skip excluded dates
            if current_date in excluded_dates:
                current_date += timedelta(days=1)
                continue

            # Generate slots for this day
            current_time = datetime.combine(
                current_date,
                datetime.min.time().replace(hour=start_hour)
            )
            current_time = timezone.make_aware(current_time)

            end_time_for_day = datetime.combine(
                current_date,
                datetime.min.time().replace(hour=end_hour)
            )
            end_time_for_day = timezone.make_aware(end_time_for_day)

            slot_duration = timedelta(minutes=slot_duration_minutes)

            while current_time + slot_duration <= end_time_for_day:
                slot_end_time = current_time + slot_duration

                # Check if slot already exists
                existing_slot = TimeSlot.objects.filter(
                    doctor=doctor,
                    start_time=current_time,
                    end_time=slot_end_time
                ).first()

                if not existing_slot:
                    TimeSlot.objects.create(
                        doctor=doctor,
                        start_time=current_time,
                        end_time=slot_end_time,
                        max_consultations=max_consultations,
                        is_available=True
                    )
                    slots_created += 1

                current_time = slot_end_time

            current_date += timedelta(days=1)

        return slots_created

    @staticmethod
    def block_timeslots(
        doctor: User,
        start_time: datetime,
        end_time: datetime,
        reason: str = "Заблокировано врачом"
    ) -> int:
        """
        Block doctor's timeslots for a specific period
        """
        timeslots = TimeSlot.objects.filter(
            doctor=doctor,
            start_time__gte=start_time,
            end_time__lte=end_time,
            is_available=True,
            booked_consultations=0
        )

        blocked_count = 0
        for timeslot in timeslots:
            timeslot.is_available = False
            timeslot.save()
            blocked_count += 1

        return blocked_count

    @staticmethod
    def get_doctor_availability(
        doctor: User,
        date: datetime.date
    ) -> Dict[str, Any]:
        """
        Get doctor's availability for a specific date
        """
        timeslots = TimeSlot.objects.filter(
            doctor=doctor,
            start_time__date=date
        ).order_by('start_time')

        total_slots = timeslots.count()
        available_slots = timeslots.filter(is_available=True).count()
        booked_slots = timeslots.filter(booked_consultations__gt=0).count()

        return {
            'date': date,
            'total_slots': total_slots,
            'available_slots': available_slots,
            'booked_slots': booked_slots,
            'timeslots': timeslots
        }