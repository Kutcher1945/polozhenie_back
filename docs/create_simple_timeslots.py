#!/usr/bin/env python3
"""
Simple script to create timeslots without Django management commands
"""
import requests
import json
from datetime import datetime, timedelta

def create_timeslots_via_api():
    """Create timeslots using the API endpoint directly"""

    # API base URL (adjust if needed)
    base_url = "http://localhost:8000"  # Adjust port if different

    # First, let's check if we can access the API
    try:
        # Try to get available timeslots to test API connectivity
        response = requests.get(f"{base_url}/api/consultations/timeslots/available/")
        if response.status_code == 200:
            print("✅ API is accessible")
            data = response.json()
            print(f"Current timeslots count: {data.get('count', 0)}")

            if data.get('count', 0) > 0:
                print("✅ Timeslots already exist in database")
                # Print some examples
                for slot in data.get('timeslots', [])[:5]:
                    print(f"  - {slot['start_time']} ({slot['doctor']['first_name']} {slot['doctor']['last_name']})")
            else:
                print("❌ No timeslots found in database")
                print("This explains why you see 'На эту дату нет свободных слотов' for all dates")
                print("\nTo fix this, doctors need to create their availability using the API:")
                print("POST /api/consultations/generate-timeslots/")

        else:
            print(f"❌ API not accessible. Status: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Make sure Django server is running on localhost:8000")
        print("Run: python3 manage.py runserver 8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    create_timeslots_via_api()