from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from consultations.models import TimeSlot
from common.models import User


class Command(BaseCommand):
    help = 'Generate timeslots for doctors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--doctor-id',
            type=int,
            help='Specific doctor ID to generate slots for'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days ahead to generate slots (default: 30)'
        )
        parser.add_argument(
            '--start-hour',
            type=int,
            default=9,
            help='Start hour for daily slots (default: 9)'
        )
        parser.add_argument(
            '--end-hour',
            type=int,
            default=18,
            help='End hour for daily slots (default: 18)'
        )
        parser.add_argument(
            '--slot-duration',
            type=int,
            default=30,
            help='Duration of each slot in minutes (default: 30)'
        )
        parser.add_argument(
            '--max-consultations',
            type=int,
            default=1,
            help='Maximum consultations per slot (default: 1)'
        )
        parser.add_argument(
            '--weekdays-only',
            action='store_true',
            help='Generate slots only for weekdays (Monday-Friday)'
        )

    def handle(self, *args, **options):
        # Get doctors to generate slots for
        doctors = User.objects.filter(role='doctor')
        if options['doctor_id']:
            doctors = doctors.filter(id=options['doctor_id'])

        if not doctors.exists():
            self.stdout.write(
                self.style.ERROR('No doctors found with the specified criteria')
            )
            return

        # Calculate date range
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=options['days'])

        slot_duration = timedelta(minutes=options['slot_duration'])
        slots_created = 0

        for doctor in doctors:
            doctor_name = f"{doctor.first_name} {doctor.last_name}".strip() if doctor.first_name or doctor.last_name else doctor.email
            self.stdout.write(f"Generating slots for {doctor_name}...")

            current_date = start_date
            while current_date <= end_date:
                # Skip weekends if weekdays_only is True
                if options['weekdays_only'] and current_date.weekday() > 4:  # 0=Monday, 6=Sunday
                    current_date += timedelta(days=1)
                    continue

                # Generate slots for this day
                current_time = datetime.combine(
                    current_date,
                    datetime.min.time().replace(hour=options['start_hour'])
                )
                current_time = timezone.make_aware(current_time)

                end_time_for_day = datetime.combine(
                    current_date,
                    datetime.min.time().replace(hour=options['end_hour'])
                )
                end_time_for_day = timezone.make_aware(end_time_for_day)

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
                            max_consultations=options['max_consultations'],
                            is_available=True
                        )
                        slots_created += 1

                    current_time = slot_end_time

                current_date += timedelta(days=1)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {slots_created} timeslots for {doctors.count()} doctor(s)'
            )
        )

        # Show some statistics
        total_slots = TimeSlot.objects.filter(doctor__in=doctors).count()
        available_slots = TimeSlot.objects.filter(
            doctor__in=doctors,
            is_available=True,
            start_time__gt=timezone.now()
        ).count()

        self.stdout.write(f"Total slots for these doctors: {total_slots}")
        self.stdout.write(f"Available future slots: {available_slots}")