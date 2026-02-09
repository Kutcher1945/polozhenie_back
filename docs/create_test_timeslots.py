#!/usr/bin/env python3
"""
Script to create test timeslots for development
"""
import os
import sys
import django
from datetime import datetime, timedelta, time
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mchs_back.settings')
django.setup()

from common.models import User
from consultations.models import TimeSlot

def create_test_timeslots():
    """Create test timeslots for doctors"""
    print("Creating test timeslots...")

    # Get all doctors
    doctors = User.objects.filter(role='doctor')
    if not doctors.exists():
        print("No doctors found in database")
        return

    print(f"Found {doctors.count()} doctors")

    # Create timeslots for next 14 days
    for doctor in doctors:
        print(f"Creating timeslots for {doctor.first_name} {doctor.last_name}")

        for day_offset in range(14):  # Next 14 days
            date = datetime.now().date() + timedelta(days=day_offset)

            # Skip weekends for this test
            if date.weekday() >= 5:  # Saturday=5, Sunday=6
                continue

            # Create slots from 9 AM to 5 PM with 1 hour intervals
            for hour in range(9, 18):  # 9 AM to 5 PM
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
                timeslot = TimeSlot.objects.create(
                    doctor=doctor,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    is_available=True,
                    max_consultations=1,
                    booked_consultations=0
                )
                print(f"  Created: {start_datetime.strftime('%Y-%m-%d %H:%M')}")

    total_slots = TimeSlot.objects.count()
    print(f"\nTotal timeslots in database: {total_slots}")

    # Show upcoming slots by date
    print("\nUpcoming timeslots by date:")
    for i in range(7):
        date = datetime.now().date() + timedelta(days=i)
        slots_count = TimeSlot.objects.filter(
            start_time__date=date,
            is_available=True
        ).count()
        print(f"  {date.strftime('%Y-%m-%d')}: {slots_count} available slots")

if __name__ == '__main__':
    create_test_timeslots()