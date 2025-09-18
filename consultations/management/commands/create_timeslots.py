from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta, time
from common.models import User
from consultations.models import TimeSlot


class Command(BaseCommand):
    help = 'Create test timeslots for doctors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=14,
            help='Number of days to create timeslots for (default: 14)'
        )
        parser.add_argument(
            '--start-hour',
            type=int,
            default=0,
            help='Start hour (default: 0 for 24/7)'
        )
        parser.add_argument(
            '--end-hour',
            type=int,
            default=24,
            help='End hour (default: 24 for 24/7)'
        )

    def handle(self, *args, **options):
        days = options['days']
        start_hour = options['start_hour']
        end_hour = options['end_hour']

        # Get all doctors
        doctors = User.objects.filter(role='doctor')
        if not doctors.exists():
            self.stdout.write(self.style.ERROR('No doctors found in database'))
            return

        self.stdout.write(f'Found {doctors.count()} doctors')
        created_count = 0

        # Create timeslots for specified number of days
        for doctor in doctors:
            self.stdout.write(f'Creating timeslots for {doctor.first_name} {doctor.last_name}')

            for day_offset in range(days):
                date = datetime.now().date() + timedelta(days=day_offset)

                # No weekend restrictions - 24/7 service
                # Create slots from start_hour to end_hour with 1 hour intervals
                for hour in range(start_hour, end_hour):
                    start_datetime = timezone.make_aware(
                        datetime.combine(date, time(hour, 0))
                    )
                    end_datetime = start_datetime + timedelta(hours=1)

                    # Check if timeslot already exists
                    if TimeSlot.objects.filter(
                        doctor=doctor,
                        start_time=start_datetime
                    ).exists():
                        continue

                    # Create the timeslot
                    TimeSlot.objects.create(
                        doctor=doctor,
                        start_time=start_datetime,
                        end_time=end_datetime,
                        is_available=True,
                        max_consultations=1,
                        booked_consultations=0
                    )
                    created_count += 1

        total_slots = TimeSlot.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} new timeslots. '
                f'Total timeslots in database: {total_slots}'
            )
        )

        # Show upcoming slots by date
        self.stdout.write('\nUpcoming timeslots by date:')
        for i in range(7):
            date = datetime.now().date() + timedelta(days=i)
            slots_count = TimeSlot.objects.filter(
                start_time__date=date,
                is_available=True
            ).count()
            self.stdout.write(f'  {date.strftime("%Y-%m-%d")}: {slots_count} available slots')