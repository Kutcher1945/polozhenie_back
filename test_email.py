#!/usr/bin/env python
"""
Test email sending functionality
Run with: python test_email.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mchs_back.settings')
django.setup()

from common.utils.email_utils import send_consultation_created_email
from django.conf import settings

def test_email():
    """Test sending a consultation email"""
    try:
        print("=" * 60)
        print("Testing Email Configuration")
        print("=" * 60)
        print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        print(f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
        print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        print(f"FRONTEND_URL: {settings.FRONTEND_URL}")
        print("=" * 60)

        # Test email details
        test_patient_email = input("\nEnter patient email to test: ").strip()
        if not test_patient_email:
            print("❌ No email provided. Exiting.")
            return

        print(f"\n📧 Sending test email to: {test_patient_email}")

        # Send test email
        send_consultation_created_email(
            patient_email=test_patient_email,
            patient_name="Test Patient",
            doctor_name="Dr. Test Doctor",
            access_code="TEST123",
            consultation_link=f"{settings.FRONTEND_URL}/video-call/patient?meetingId=test-meeting-123",
            scheduled_at="2026-02-15T10:00:00Z"
        )

        print("✅ Email sent successfully!")
        print(f"Check inbox at: {test_patient_email}")
        print("\n💡 If you don't see the email:")
        print("   1. Check your spam/junk folder")
        print("   2. Verify the email address is correct")
        print("   3. Check Django logs for errors")

    except Exception as e:
        print(f"\n❌ Error sending email: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_email()
