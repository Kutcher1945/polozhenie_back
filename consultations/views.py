import logging
import requests
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from common.models import User
from .models import Consultation, AIRecommendationLog
from .serializers import ConsultationSerializer
from .permissions import IsAuthenticatedOrAIRecommendation
from .throttles import AIRecommendationAnonThrottle, AIRecommendationUserThrottle
import uuid
from django.utils import timezone
import jwt
import time
from django.core.cache import cache
from django.conf import settings
import re
import json
import random
from livekit.api import AccessToken, VideoGrants
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from common.utils.email_utils import send_consultation_created_email

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
def csrf_token_view(request):
    return JsonResponse({"message": "CSRF cookie set"})

# Create your views here.
class ConsultationViewSet(ModelViewSet):
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [IsAuthenticatedOrAIRecommendation]
    lookup_field = "meeting_id"  # ✅ Tell DRF to use meeting_id in URLs

    def get_queryset(self):
        user = self.request.user

        print("🔍 DEBUG: User Object ->", user)  # ✅ Print the user object
        print("🔍 DEBUG: User Authenticated? ->", user.is_authenticated)

        if not user.is_authenticated:
            return Consultation.objects.none()

        print("🔍 DEBUG: User Role ->", getattr(user, "role", "No role found"))

        # Start with base queryset filtered by user role
        if hasattr(user, "role") and user.role == "doctor":
            queryset = Consultation.objects.filter(doctor=user)
        else:
            queryset = Consultation.objects.filter(patient=user)

        # ✅ Filter by meeting_id if provided in query params
        meeting_id = self.request.query_params.get('meeting_id')
        if meeting_id:
            print(f"🔍 DEBUG: Filtering by meeting_id -> {meeting_id}")
            queryset = queryset.filter(meeting_id=meeting_id)

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Override list to add time-based access control for consultations
        """
        queryset = self.filter_queryset(self.get_queryset())

        # ⏰ Time-based access control for patients
        meeting_id = request.query_params.get('meeting_id')
        if meeting_id and hasattr(request.user, 'role') and request.user.role == 'patient':
            # Check if consultation is being accessed too early
            consultation = queryset.first()

            if consultation and consultation.scheduled_at:
                from django.utils import timezone
                from datetime import timedelta

                scheduled_time = consultation.scheduled_at
                now = timezone.now()
                time_diff = scheduled_time - now

                # Allow access 5 minutes before scheduled time (grace period)
                grace_period = timedelta(minutes=5)

                if time_diff > grace_period:
                    # Format date in Russian
                    months_ru = {
                        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
                        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
                        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
                    }

                    scheduled_str = f"{scheduled_time.day} {months_ru[scheduled_time.month]} {scheduled_time.year}, {scheduled_time.strftime('%H:%M')}"

                    return Response({
                        'error': f'Консультация запланирована на {scheduled_str}.'
                    }, status=status.HTTP_403_FORBIDDEN)

        # Return normal list response
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # @action(detail=False, methods=["post"], url_path="start")
    # def start_consultation(self, request):
    #     """
    #     Patients start a video consultation with an available doctor.
    #     """
    #     user = request.user

    #     # ✅ Debug: Check user authentication
    #     if not user.is_authenticated:
    #         return Response({"error": "User is not authenticated."}, status=status.HTTP_403_FORBIDDEN)

    #     # ✅ Debug: Ensure only patients can start a call
    #     if user.role != "patient":
    #         return Response({"error": "Only patients can start consultations."}, status=status.HTTP_403_FORBIDDEN)

    #     # ✅ Check if `doctor_id` is provided
    #     doctor_id = request.data.get("doctor_id")
    #     if not doctor_id:
    #         return Response({"error": "Missing doctor_id."}, status=status.HTTP_400_BAD_REQUEST)

    #     doctor = User.objects.filter(id=doctor_id, role="doctor", is_active=True).first()
    #     if not doctor:
    #         return Response({"error": "Selected doctor is not available."}, status=status.HTTP_404_NOT_FOUND)

    #     # ✅ Prevent duplicate pending consultations
    #     existing_consultation = Consultation.objects.filter(patient=user, doctor=doctor, status="pending").first()
    #     if existing_consultation:
    #         return Response(
    #             {"error": "You already have a pending consultation with this doctor.", "meeting_id": existing_consultation.meeting_id},
    #             status=status.HTTP_400_BAD_REQUEST,
    #         )

    #     # ✅ Generate a unique meeting ID
    #     meeting_id = str(uuid.uuid4())

    #     # ✅ Create a new consultation
    #     consultation = Consultation.objects.create(
    #         patient=user,
    #         doctor=doctor,
    #         meeting_id=meeting_id,
    #         status="pending",
    #     )

    #     print(f"🔔 Doctor {doctor.email} received a consultation request from {user.email}")

    #     return Response(
    #         {
    #             "message": "Consultation request sent!",
    #             "doctor": {"id": doctor.id, "name": f"{doctor.first_name} {doctor.last_name}", "email": doctor.email},
    #             "meeting_id": meeting_id,
    #             "consultation_id": consultation.id,
    #         },
    #         status=status.HTTP_200_OK,
    #     )
    @action(detail=False, methods=["post"], url_path="start")
    def start_consultation(self, request):
        """
        Patients start a video consultation with an available doctor.
        """
        user = request.user

        if not user.is_authenticated:
            return Response({"error": "User is not authenticated."}, status=status.HTTP_403_FORBIDDEN)

        if user.role != "patient":
            return Response({"error": "Only patients can start consultations."}, status=status.HTTP_403_FORBIDDEN)

        doctor_id = request.data.get("doctor_id")
        if not doctor_id:
            return Response({"error": "Missing doctor_id."}, status=status.HTTP_400_BAD_REQUEST)

        doctor = User.objects.filter(id=doctor_id, role="doctor", is_active=True).first()
        if not doctor:
            return Response({"error": "Selected doctor is not available."}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Extract urgency from request data
        is_urgent = request.data.get("is_urgent", False)
        symptoms = request.data.get("symptoms", "")

        # 🚫 No longer preventing duplicate consultations
        # existing_consultation = Consultation.objects.filter(patient=user, doctor=doctor, status="pending").first()
        # if existing_consultation:
        #     return Response(
        #         {"error": "You already have a pending consultation with this doctor.", "meeting_id": existing_consultation.meeting_id},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )

        meeting_id = str(uuid.uuid4())

        # ✅ Create consultation with urgency information
        consultation = Consultation.objects.create(
            patient=user,
            doctor=doctor,
            meeting_id=meeting_id,
            status="pending",
            is_urgent=is_urgent,
        )

        urgency_text = "URGENT" if is_urgent else "non-urgent"
        print(f"🔔 Doctor {doctor.email} received a {urgency_text} consultation request from {user.email}")

        # 📧 Send email notification to patient with access code and magic link
        try:
            patient_name = f"{user.first_name} {user.last_name}".strip() or user.email.split("@")[0]
            doctor_name = f"{doctor.first_name} {doctor.last_name}".strip() or "Врач"

            # Build consultation link (adjust URL based on your frontend)
            consultation_link = f"{settings.FRONTEND_URL}/video-call/patient?meetingId={meeting_id}"

            send_consultation_created_email(
                patient_email=user.email,
                patient_name=patient_name,
                doctor_name=doctor_name,
                access_code=consultation.access_code,
                consultation_link=consultation_link,
                scheduled_at=consultation.scheduled_at,
                consultation=consultation  # ✅ Pass consultation object for magic link token
            )
            logger.info(f"✅ Email sent to {user.email} with access code {consultation.access_code} and magic link token")
        except Exception as email_error:
            # Log error but don't fail the consultation creation
            logger.error(f"❌ Failed to send email notification: {str(email_error)}")

        return Response(
            {
                "message": "Consultation request sent!",
                "doctor": {
                    "id": doctor.id,
                    "name": f"{doctor.first_name} {doctor.last_name}",
                    "email": doctor.email,
                },
                "meeting_id": meeting_id,
                "consultation_id": consultation.id,
                "access_code": consultation.access_code,
            },
            status=status.HTTP_200_OK,
        )


    @action(detail=True, methods=["post"], url_path="accept")
    def accept_consultation(self, request, meeting_id=None):
        user = request.user
        consultation = self.get_object()

        if user.role != "doctor" or consultation.doctor != user:
            return Response({"error": "You are not authorized to accept this consultation."}, status=status.HTTP_403_FORBIDDEN)

        consultation.status = "ongoing"
        consultation.started_at = timezone.now()
        consultation.save()

        return Response({
            "message": "Consultation started!",
            "meeting_id": consultation.meeting_id,
            "status": consultation.status
        }, status=status.HTTP_200_OK)


    @action(detail=True, methods=["post"], url_path="reject")
    def reject_consultation(self, request, meeting_id=None):
        user = request.user
        consultation = self.get_object()

        if user.role != "doctor" or consultation.doctor != user:
            return Response({"error": "You are not authorized to reject this consultation."}, status=status.HTTP_403_FORBIDDEN)

        consultation.status = "cancelled"
        consultation.save()

        return Response({"message": "Consultation rejected.", "status": consultation.status}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="mark-missed")
    def mark_missed(self, request, meeting_id=None):
        """
        Automatically mark a consultation as 'missed' if doctor didn't respond.
        Triggered by a frontend timeout or background task.
        """
        consultation = self.get_object()
    
        if consultation.status != "pending":
            return Response({"error": "Only pending consultations can be marked as missed."}, status=status.HTTP_400_BAD_REQUEST)
    
        consultation.status = "missed"
        consultation.ended_at = timezone.now()
        consultation.save()
    
        return Response({
            "message": "Consultation marked as missed.",
            "status": consultation.status
        }, status=status.HTTP_200_OK)

    # ✅ Notify the patient when doctor accepts the call
    @action(detail=True, methods=["post"], url_path="notify-patient")
    def notify_patient(self, request, meeting_id=None):
        consultation = self.get_object()

        if request.user.role != "doctor":
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        consultation.status = "ongoing"
        consultation.save()

        return Response({
            "message": "Patient notified",
            "meeting_id": consultation.meeting_id
        }, status=status.HTTP_200_OK)

    # ✅ API to check consultation status
    @action(detail=False, methods=["get"], url_path="status")
    def consultation_status(self, request):
        """
        Checks the status of a consultation based on meeting_id.
        Used to notify the patient when the doctor has accepted or rejected the call.
        """
        meeting_id = request.query_params.get("meeting_id")
        if not meeting_id:
            return Response({"error": "Missing meeting_id"}, status=status.HTTP_400_BAD_REQUEST)

        consultation = get_object_or_404(Consultation, meeting_id=meeting_id)

        # ✅ Stop polling if the consultation is cancelled
        if consultation.status == "cancelled":
            return Response({"status": "cancelled", "message": "Doctor rejected the call."}, status=status.HTTP_200_OK)

        return Response({"status": consultation.status}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="status")
    def update_consultation_status(self, request, meeting_id=None):
        """
        Update consultation status (for doctors)

        POST /api/consultations/{meeting_id}/status/
        {
            "status": "completed"
        }
        """
        user = request.user
        consultation = self.get_object()

        # Only doctors can change consultation status
        if user.role != "doctor" or consultation.doctor != user:
            return Response(
                {"error": "You are not authorized to change this consultation status."},
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get("status")
        if not new_status:
            return Response(
                {"error": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate status
        valid_statuses = ["pending", "ongoing", "completed", "cancelled", "missed", "scheduled", "planned"]
        if new_status not in valid_statuses:
            return Response(
                {"error": f"Invalid status. Valid options: {', '.join(valid_statuses)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update consultation status
        consultation.status = new_status
        if new_status == "ongoing" and not consultation.started_at:
            consultation.started_at = timezone.now()
        elif new_status == "completed" and not consultation.ended_at:
            consultation.ended_at = timezone.now()

        consultation.save()

        return Response({
            "message": "Consultation status updated successfully",
            "status": consultation.status
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="start-call")
    def start_call(self, request, meeting_id=None):
        consultation = self.get_object()

        if consultation.status != "pending":
            return Response({"error": "Consultation is not in a valid state to start."}, status=status.HTTP_400_BAD_REQUEST)

        consultation.status = "ongoing"
        consultation.started_at = timezone.now()
        consultation.save()

        return Response({"message": "Call started!", "status": consultation.status}, status=status.HTTP_200_OK)


    @action(detail=True, methods=["post"], url_path="end-call")
    def end_call(self, request, meeting_id=None):
        consultation = self.get_object()

        if consultation.status != "ongoing":
            return Response({"error": "Consultation is not active or has already ended."}, status=status.HTTP_400_BAD_REQUEST)

        consultation.status = "completed"
        consultation.ended_at = timezone.now()
        consultation.save()

        return Response({"message": "Call ended successfully!", "status": consultation.status}, status=status.HTTP_200_OK)


    @action(detail=True, methods=["get"], url_path="video-token")
    def get_livekit_video_token(self, request, meeting_id=None):
        consultation = self.get_object()
        user = request.user
        if user not in (consultation.patient, consultation.doctor):
            return Response({"error": "Not allowed"}, status=403)
    
        room = consultation.meeting_id
        identity = request.query_params.get(
            "identity",
            f"{user.role}-{user.id}-{uuid.uuid4().hex[:6]}"
        )
    
        token = (AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
                 .with_identity(identity)
                 .with_grants(VideoGrants(room_join=True, room=room, can_publish=True, can_subscribe=True))
                 .to_jwt())
    
        return Response({"token": token, "url": settings.LIVEKIT_URL, "identity": identity})


    @action(
        detail=False,
        methods=["post"],
        url_path="ai-recommend",
        throttle_classes=[AIRecommendationAnonThrottle, AIRecommendationUserThrottle]
    )
    def ai_recommend_doctor(self, request):
        """
        AI Doctor Recommendation endpoint - allows unauthenticated access
        Rate limited:
        - Anonymous users: 10 requests per hour per IP
        - Authenticated users: 30 requests per hour
        Origin checking enabled in production
        """
        # Get client IP for logging
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        user_id = request.user.id if request.user.is_authenticated else "anonymous"
        logger.info(f"AI recommendation request from IP: {ip}, User: {user_id}")

        symptoms = request.data.get("symptoms")
        language = request.data.get("language", "ru")

        if not symptoms:
            return Response({"success": False, "error": "Symptoms are required."}, status=400)

        # Debugging: Print the symptoms
        print(f"Symptoms received: {symptoms}")
        
        # Prompt for the specialty (always in Russian)
        specialty_prompt = f"""
        You are a medical assistant. The patient described the symptoms: "{symptoms}". 
        Please suggest an appropriate doctor based on these symptoms, without limiting to a specific specialization. 
    
        1. Always provide the **specialty** in **Russian** in the JSON response.
        2. The **specialty** should include the medical field in which the doctor specializes.
        3. The explanation should strictly follow this JSON structure:
    
        {{
          "specialty": "<specialization_in_russian>"
        }}
        """
    
        # Detect input language first
        import re
        has_english = bool(re.search(r'[a-zA-Z]', symptoms))
        has_cyrillic = bool(re.search(r'[а-яА-ЯёЁ]', symptoms))
        has_kazakh = bool(re.search(r'[әғқңөұүһіӘҒҚҢӨҰҮҺІ]', symptoms))

        # Determine language
        if has_english and not has_cyrillic:
            detected_lang = "English"
            lang_instruction = "YOU MUST RESPOND IN ENGLISH ONLY. Use English language for your entire response."
        elif has_kazakh:
            detected_lang = "Kazakh"
            lang_instruction = "YOU MUST RESPOND IN KAZAKH ONLY. Use Kazakh language for your entire response."
        else:
            detected_lang = "Russian"
            lang_instruction = "YOU MUST RESPOND IN RUSSIAN ONLY. Use Russian language for your entire response."

        # Prompt for the reason (in the same language as user's input)
        reason_prompt = f"""
        You are a medical assistant. The patient described symptoms in {detected_lang}: "{symptoms}".

        🚨 CRITICAL LANGUAGE REQUIREMENT 🚨
        {lang_instruction}
        DO NOT translate to any other language. DO NOT use Russian if input is English.

        Provide a detailed medical explanation including:
           - Possible causes for the symptoms
           - Additional symptoms or related signs
           - Recommendations for treatment or referral

        Return ONLY a JSON object with this structure:
        {{
          "reason": "<detailed_explanation_in_{detected_lang}>"
        }}

        EXAMPLES:
        - Input in English "i have a headache" → Response: {{"reason": "Headaches can be caused by various factors such as stress, tension, dehydration, or lack of sleep..."}} (in English)
        - Input in Russian "болит голова" → Response: {{"reason": "Боли в голове могут быть вызваны различными факторами..."}} (in Russian)
        - Input in Kazakh "бас ауырады" → Response: {{"reason": "Бас ауруы әртүрлі себептерден болуы мүмкін..."}} (in Kazakh)
        """
    
        # Third prompt for urgency, separate from the reason
        urgency_prompt = f"""
        You are a medical assistant. The patient described the symptoms: "{symptoms}".
        Please evaluate the urgency of the condition based on medical triage principles.

        URGENT conditions require immediate medical attention (examples):
        - High fever (>39°C/102°F) with severe symptoms
        - Chest pain, difficulty breathing, or heart palpitations
        - Severe headache with neurological symptoms
        - Severe abdominal pain or persistent vomiting
        - Signs of severe infection or sepsis
        - Mental health crisis or suicidal thoughts
        - Severe allergic reactions
        - Trauma or severe injury

        NON-URGENT conditions can be scheduled for regular appointments (examples):
        - Mild cold or flu symptoms
        - Minor aches and pains
        - Routine check-ups or follow-ups
        - Mild headaches without other symptoms
        - Minor digestive issues
        - Skin issues (non-severe)
        - General wellness concerns

        Your answer must be EXACTLY one of these two values: "urgent" or "non_urgent"

        Return ONLY the JSON object, no markdown formatting, no code blocks, no explanations:
        {{
          "urgency": "urgent"
        }}
        OR
        {{
          "urgency": "non_urgent"
        }}
        """
    
        try:
            # Get response for specialty
            specialty_payload = {
                "model": "open-mistral-nemo",
                "temperature": 0.3,
                "top_p": 1,
                "max_tokens": 400,
                "messages": [
                    {"role": "system", "content": specialty_prompt},
                    {"role": "user", "content": symptoms}
                ],
            }
    
            # Get response for reason
            reason_payload = {
                "model": "open-mistral-nemo",
                "temperature": 0.3,
                "top_p": 1,
                "max_tokens": 800,  # Increase tokens for reason to avoid truncation
                "messages": [
                    {"role": "system", "content": reason_prompt},
                    {"role": "user", "content": symptoms}
                ],
            }
    
            # Get response for urgency
            urgency_payload = {
                "model": "open-mistral-nemo",
                "temperature": 0.1,  # Lower temperature for more consistent urgency classification
                "top_p": 1,
                "max_tokens": 100,  # Shorter response needed for urgency
                "messages": [
                    {"role": "system", "content": urgency_prompt},
                    {"role": "user", "content": symptoms}
                ],
            }
    
            headers = {
                "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            }
    
            logger.info("📡 Отправка в LLM")
    
            # Send requests for specialty, reason, and urgency
            specialty_response = requests.post("https://api.mistral.ai/v1/chat/completions", json=specialty_payload, headers=headers)
            reason_response = requests.post("https://api.mistral.ai/v1/chat/completions", json=reason_payload, headers=headers)
            urgency_response = requests.post("https://api.mistral.ai/v1/chat/completions", json=urgency_payload, headers=headers)
    
            specialty_response.raise_for_status()
            reason_response.raise_for_status()
            urgency_response.raise_for_status()
    
            def extract_json_from_response(response_text):
                """Extract JSON from AI response, handling markdown code blocks"""
                text = response_text.strip()

                # Check if response is wrapped in markdown code blocks
                if '```json' in text:
                    # Extract content between ```json and ```
                    start = text.find('```json') + 7
                    end = text.find('```', start)
                    if end != -1:
                        text = text[start:end].strip()
                elif '```' in text:
                    # Extract content between ``` and ```
                    start = text.find('```') + 3
                    end = text.find('```', start)
                    if end != -1:
                        text = text[start:end].strip()

                return text

            specialty_reply = extract_json_from_response(specialty_response.json()["choices"][0]["message"]["content"])
            reason_reply = extract_json_from_response(reason_response.json()["choices"][0]["message"]["content"])
            urgency_reply = extract_json_from_response(urgency_response.json()["choices"][0]["message"]["content"])
    
            # Debugging: Print the raw responses
            print("Specialty Response:", specialty_reply)
            print("Reason Response:", reason_reply)
            print("Urgency Response:", urgency_reply)
    
            logger.debug(f"🧠 Ответ AI для специализации:\n{specialty_reply}")
            logger.debug(f"🧠 Ответ AI для пояснения:\n{reason_reply}")
            logger.debug(f"🧠 Ответ AI для экстренности:\n{urgency_reply}")
    
            try:
                # Helper function to clean and parse JSON
                def clean_and_parse_json(json_str):
                    """Clean JSON string by removing markdown code blocks and extra whitespace"""
                    # Remove markdown code blocks if present
                    json_str = re.sub(r'^```json\s*', '', json_str.strip())
                    json_str = re.sub(r'\s*```$', '', json_str.strip())
                    # Parse JSON (Python's json.loads handles newlines within strings correctly)
                    return json.loads(json_str)

                # Parse the JSON responses with better error handling
                try:
                    specialty_data = clean_and_parse_json(specialty_reply)
                    specialty = specialty_data["specialty"].strip().lower()
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse specialty JSON: {e}")
                    logger.warning(f"Specialty response: {specialty_reply}")
                    raise

                try:
                    reason_data = clean_and_parse_json(reason_reply)
                    reason = reason_data["reason"].strip()
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse reason JSON: {e}")
                    logger.warning(f"Reason response: {reason_reply}")
                    raise

                try:
                    urgency_data = clean_and_parse_json(urgency_reply)
                    urgency_raw = urgency_data["urgency"].strip()
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse urgency JSON: {e}")
                    logger.warning(f"Urgency response: {urgency_reply}")
                    # Default to non_urgent if urgency parsing fails
                    urgency_raw = "non_urgent"

                # Validate and normalize urgency value
                if urgency_raw.lower() in ["urgent", "emergency", "immediate", "critical"]:
                    urgency = "urgent"
                elif urgency_raw.lower() in ["non_urgent", "non-urgent", "routine", "planned", "regular"]:
                    urgency = "non_urgent"
                else:
                    # Default to non_urgent if unclear
                    urgency = "non_urgent"
                    logger.warning(f"⚠️ Unexpected urgency value from AI: '{urgency_raw}', defaulting to 'non_urgent'")

                # Debugging: Print urgency value
                print(f"Urgency value extracted from AI: {urgency_raw} -> normalized to: {urgency}")

            except (json.JSONDecodeError, KeyError) as e:
                logger.error("⚠️ Ошибка парсинга JSON")
                logger.warning(f"📥 Сырой ответ от AI (specialty):\n{specialty_reply}")
                logger.warning(f"📥 Сырой ответ от AI (reason):\n{reason_reply}")
                logger.warning(f"📥 Сырой ответ от AI (urgency):\n{urgency_reply}")
                return Response({"success": False, "error": "Invalid AI response format", "raw_specialty": specialty_reply, "raw_reason": reason_reply, "raw_urgency": urgency_reply}, status=200)
    
            # Query doctors based on the specialty (in Russian) - only available doctors
            doctors = list(User.objects.filter(
                role="doctor",
                is_active=True,
                availability_status='available',  # Only recommend available doctors
                doctor_specialization__name_ru__icontains=specialty
            )[:10])
    
            if not doctors:
                logger.warning(f"❌ Не найден врач по специализации '{specialty}'")
                logger.warning(f"📨 Ответ от AI (specialty): {specialty_reply}")
                logger.warning(f"📨 Ответ от AI (reason): {reason_reply}")
                logger.warning(f"📨 Ответ от AI (urgency): {urgency_reply}")

                # Try to find a fallback doctor (general practitioner/терапевт)
                fallback_doctors = list(User.objects.filter(
                    role="doctor",
                    is_active=True,
                    availability_status='available',
                    doctor_specialization__name_ru__icontains='терапевт'
                )[:10])

                # If no терапевт found, get any available doctor
                if not fallback_doctors:
                    fallback_doctors = list(User.objects.filter(
                        role="doctor",
                        is_active=True,
                        availability_status='available'
                    )[:10])

                if fallback_doctors:
                    # Select a random fallback doctor
                    fallback_doctor = random.choice(fallback_doctors)
                    logger.info(f"🔄 Using fallback doctor: {fallback_doctor.first_name} {fallback_doctor.last_name}")

                    ai_recommendation = AIRecommendationLog.objects.create(
                        symptoms=symptoms,
                        ai_raw_response={"specialty": specialty_reply, "reason": reason_reply, "urgency": urgency_reply},
                        recommended_specialty=specialty,
                        reason=reason,
                        matched_doctor=fallback_doctor,
                        fallback_used=True,
                        specialty_not_found=specialty,
                        urgency=urgency
                    )

                    # Get comprehensive doctor information for fallback
                    years_of_experience = None
                    try:
                        if hasattr(fallback_doctor, 'doctor_profile') and fallback_doctor.doctor_profile:
                            years_of_experience = fallback_doctor.doctor_profile.years_of_experience
                    except Exception:
                        pass

                    # Build multilingual specialization
                    specialization = {
                        "ru": fallback_doctor.doctor_specialization.name_ru if fallback_doctor.doctor_specialization else "Терапевт",
                        "en": fallback_doctor.doctor_specialization.name_en if fallback_doctor.doctor_specialization else "General Practitioner",
                        "kz": fallback_doctor.doctor_specialization.name_kz if fallback_doctor.doctor_specialization else "Терапевт"
                    }

                    # Clinic information
                    clinic_info = None
                    if fallback_doctor.clinic:
                        clinic_info = {
                            "name": fallback_doctor.clinic.name,
                            "address": fallback_doctor.clinic.address,
                            "city": fallback_doctor.clinic.city.name_ru if fallback_doctor.clinic.city else None,
                            "rating": fallback_doctor.clinic.rating
                        }

                    return Response({
                        "success": True,
                        "fallback_used": True,
                        "requested_specialty": specialty,
                        "ai_recommendation_id": ai_recommendation.id,
                        "recommended_doctor": {
                            "id": fallback_doctor.id,
                            "name": f"{fallback_doctor.first_name} {fallback_doctor.last_name}",
                            "specialization": specialization,
                            "email": fallback_doctor.email,
                            "phone": fallback_doctor.phone,
                            "years_of_experience": years_of_experience,
                            "clinic": clinic_info,
                            "language": fallback_doctor.language,
                            "reason": reason,
                            "urgency": urgency,
                        }
                    }, status=200)

                # No doctors available at all
                ai_recommendation = AIRecommendationLog.objects.create(
                    symptoms=symptoms,
                    ai_raw_response={"specialty": specialty_reply, "reason": reason_reply, "urgency": urgency_reply},
                    recommended_specialty=specialty,
                    reason=reason,
                    matched_doctor=None,
                    fallback_used=False,
                    specialty_not_found=specialty,
                    urgency=urgency
                )

                return Response({
                    "success": False,
                    "error": f"No doctor found for '{specialty}'",
                    "fallback_used": False,
                    "ai_recommendation_id": ai_recommendation.id,
                    "ai_data": {
                        "specialty": specialty,
                        "reason": reason,
                        "urgency": urgency,
                        "raw_specialty": specialty_reply,
                        "raw_reason": reason_reply,
                        "raw_urgency": urgency_reply
                    }
                }, status=200)
    
            # Select a random doctor
            doctor = random.choice(doctors)
            logger.info(f"👨‍⚕️ Назначен врач: {doctor.first_name} {doctor.last_name} ({doctor.doctor_specialization.name_ru})")

            ai_recommendation = AIRecommendationLog.objects.create(
                symptoms=symptoms,
                ai_raw_response={"specialty": specialty_reply, "reason": reason_reply, "urgency": urgency_reply},
                recommended_specialty=specialty,
                reason=reason,
                matched_doctor=doctor,
                fallback_used=False,
                urgency=urgency  # Store urgency level in the log
            )

            # Get comprehensive doctor information
            years_of_experience = None
            try:
                if hasattr(doctor, 'doctor_profile') and doctor.doctor_profile:
                    years_of_experience = doctor.doctor_profile.years_of_experience
            except Exception:
                pass

            # Build multilingual specialization
            specialization = {
                "ru": doctor.doctor_specialization.name_ru if doctor.doctor_specialization else "Врач",
                "en": doctor.doctor_specialization.name_en if doctor.doctor_specialization else "Doctor",
                "kz": doctor.doctor_specialization.name_kz if doctor.doctor_specialization else "Дәрігер"
            }

            # Clinic information
            clinic_info = None
            if doctor.clinic:
                clinic_info = {
                    "name": doctor.clinic.name,
                    "address": doctor.clinic.address,
                    "city": doctor.clinic.city.name_ru if doctor.clinic.city else None,
                    "rating": doctor.clinic.rating
                }

            return Response({
                "success": True,
                "ai_recommendation_id": ai_recommendation.id,  # Include the AI recommendation ID
                "recommended_doctor": {
                    "id": doctor.id,
                    "name": f"{doctor.first_name} {doctor.last_name}",
                    "specialization": specialization,
                    "email": doctor.email,
                    "phone": doctor.phone,
                    "years_of_experience": years_of_experience,
                    "clinic": clinic_info,
                    "language": doctor.language,
                    "reason": reason,
                    "urgency": urgency  # Include urgency in the response
                }
            })
    
        except requests.exceptions.RequestException:
            logger.exception("❌ Ошибка запроса к AI")
            return Response({"success": False, "error": "LLM API unavailable"}, status=502)
    
        except Exception as e:
            logger.exception("🔥 Непредвиденная ошибка")
            return Response({"success": False, "error": str(e)}, status=500)
    
    @action(detail=False, methods=["get"], url_path="my-consultations")
    def my_consultations(self, request):
        user = request.user

        # ✅ Restrict to patients only
        if user.role != "patient":
            return Response(
                {"error": "Only patients can view their consultations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ✅ Optional filtering by status
        status_filter = request.query_params.get("status")
        consultations = Consultation.objects.filter(patient=user)
        if status_filter:
            consultations = consultations.filter(status=status_filter)

        consultations = consultations.order_by("-created_at")

        serializer = self.get_serializer(consultations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="patient-latest")
    def patient_latest_consultation(self, request):
        """
        Get patient's aggregated consultation history
        Used by nurses to view patient's medical history

        GET /api/v1/consultations/patient-latest/?patient_id=123

        Returns an aggregated view with the latest non-null value for each field
        across all completed consultations
        """
        patient_id = request.query_params.get("patient_id")

        if not patient_id:
            return Response(
                {"error": "patient_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.db.models import Q

        # Get all consultations for this patient (any status), ordered by most recent first
        # We include all statuses to ensure we capture data from ongoing/completed consultations
        consultations = Consultation.objects.filter(
            patient_id=patient_id
        ).exclude(
            status__in=["cancelled", "missed"]  # Exclude cancelled/missed consultations
        ).order_by("-created_at")

        if not consultations.exists():
            return Response(
                {"message": "No consultation history found for this patient"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Helper function to check if a value is valid (not null, not empty, not "<null>")
        def is_valid_value(value):
            return value and value != '' and value != '<null>'

        # Aggregate data: find the latest non-null value for each field
        aggregated_data = {
            'complaints': None,
            'anamnesis': None,
            'diagnostics': None,
            'treatment': None,
            'diagnosis': None,
            'session_notes': None,
            'prescription': None,
            'recommendations': None,
            'transcription': None,
        }

        # Track metadata from the most recent consultation
        most_recent = consultations.first()

        # Iterate through consultations to find latest valid value for each field
        for consultation in consultations:
            for field in aggregated_data.keys():
                # If we haven't found a value for this field yet
                if aggregated_data[field] is None:
                    value = getattr(consultation, field, None)
                    if is_valid_value(value):
                        aggregated_data[field] = value

        # Build response with aggregated data + metadata from most recent consultation
        response_data = {
            'id': most_recent.id,
            'patient_first_name': most_recent.patient.first_name,
            'patient_last_name': most_recent.patient.last_name,
            'doctor_first_name': most_recent.doctor.first_name,
            'doctor_last_name': most_recent.doctor.last_name,
            'ended_at': most_recent.ended_at,
            'scheduled_at': most_recent.scheduled_at,
            'created_at': most_recent.created_at,
            **aggregated_data  # Add all the aggregated consultation data
        }

        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="save-consultation-form")
    def save_consultation_form(self, request, meeting_id=None):
        """
        Save consultation form data (filled by doctor during video call)

        PATCH /api/v1/consultations/{meeting_id}/save-consultation-form/
        {
            "complaints": "Patient complaints...",
            "anamnesis": "Medical history...",
            "diagnostics": "Diagnostic results...",
            "treatment": "Treatment plan...",
            "diagnosis": "Final diagnosis..."
        }
        """
        user = request.user
        consultation = self.get_object()

        # Only doctors can save consultation forms
        if user.role != "doctor" or consultation.doctor != user:
            return Response(
                {"error": "Only the assigned doctor can save consultation form data."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Update consultation form fields
        consultation.complaints = request.data.get("complaints", consultation.complaints)
        consultation.anamnesis = request.data.get("anamnesis", consultation.anamnesis)
        consultation.diagnostics = request.data.get("diagnostics", consultation.diagnostics)
        consultation.treatment = request.data.get("treatment", consultation.treatment)
        consultation.diagnosis = request.data.get("diagnosis", consultation.diagnosis)

        # Update additional consultation data
        consultation.session_notes = request.data.get("session_notes", consultation.session_notes)
        consultation.prescription = request.data.get("prescription", consultation.prescription)
        consultation.recommendations = request.data.get("recommendations", consultation.recommendations)
        consultation.transcription = request.data.get("transcription", consultation.transcription)

        consultation.save()

        serializer = self.get_serializer(consultation)
        return Response({
            "message": "Consultation form saved successfully",
            "consultation": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="get-random-doctors", permission_classes=[AllowAny])
    def get_random_doctors(self, request):
        """
        Get 5 random available doctors for alternative selection
        No authentication required - public endpoint
        """
        try:
            # Get all available doctors with related data
            available_doctors = User.objects.filter(
                role="doctor",
                is_active=True,
                availability_status='available'
            ).select_related('doctor_specialization', 'clinic', 'doctor_profile')

            # Get 5 random doctors (or less if not enough available)
            doctor_count = min(available_doctors.count(), 5)
            random_doctors = random.sample(list(available_doctors), doctor_count)

            logger.info(f"📋 Fetched {doctor_count} random doctors for alternative selection")

            # Format doctor data with comprehensive information
            doctors_data = []
            for doctor in random_doctors:
                # Get years of experience from doctor_profile if exists
                years_of_experience = None
                try:
                    if hasattr(doctor, 'doctor_profile') and doctor.doctor_profile:
                        years_of_experience = doctor.doctor_profile.years_of_experience
                except Exception:
                    pass

                # Build multilingual specialization
                specialization = {
                    "ru": doctor.doctor_specialization.name_ru if doctor.doctor_specialization else "Врач общей практики",
                    "en": doctor.doctor_specialization.name_en if doctor.doctor_specialization else "General Practitioner",
                    "kz": doctor.doctor_specialization.name_kz if doctor.doctor_specialization else "Жалпы тәжірибелі дәрігер"
                }

                # Clinic information
                clinic_info = None
                if doctor.clinic:
                    clinic_info = {
                        "name": doctor.clinic.name,
                        "address": doctor.clinic.address,
                        "city": doctor.clinic.city.name_ru if doctor.clinic.city else None,
                        "rating": doctor.clinic.rating
                    }

                doctors_data.append({
                    "id": doctor.id,
                    "name": f"{doctor.first_name} {doctor.last_name}",
                    "specialization": specialization,
                    "email": doctor.email,
                    "phone": doctor.phone,
                    "years_of_experience": years_of_experience,
                    "clinic": clinic_info,
                    "language": doctor.language,
                    "urgency": "non_urgent"  # Alternative doctors are for non-urgent consultations
                })

            return Response({
                "success": True,
                "doctors": doctors_data,
                "count": doctor_count
            }, status=200)

        except Exception as e:
            logger.error(f"❌ Error fetching random doctors: {str(e)}")
            return Response({
                "success": False,
                "error": "Failed to fetch alternative doctors"
            }, status=500)

    @action(detail=False, methods=["get"], url_path="get-doctor-time-slots/(?P<doctor_id>[^/.]+)", permission_classes=[AllowAny])
    def get_doctor_time_slots(self, request, doctor_id=None):
        """
        Get available time slots for a specific doctor for the next 7 days
        Uses existing TimeSlot model to get real availability
        No authentication required - public endpoint
        """
        try:
            from datetime import datetime, timedelta
            from .models import TimeSlot

            # Verify doctor exists and is active
            doctor = User.objects.get(id=doctor_id, role="doctor", is_active=True)

            logger.info(f"📅 Fetching time slots for doctor: {doctor.first_name} {doctor.last_name} (ID: {doctor_id})")

            # Get available time slots from database for next 7 days
            today = timezone.now().date()
            end_date = today + timedelta(days=7)

            # Fetch existing time slots
            existing_slots = TimeSlot.get_available_slots(
                doctor=doctor,
                start_date=today,
                end_date=end_date
            )

            time_slots = []
            for slot in existing_slots:
                time_slots.append({
                    "id": f"{slot.start_time.date()}_{slot.start_time.strftime('%H:%M')}",
                    "date": slot.start_time.date().isoformat(),
                    "time": slot.start_time.strftime('%H:%M'),
                    "available": slot.can_book(),
                    "datetime": slot.start_time.isoformat()
                })

            # If no time slots exist in database, generate default slots for demo
            if not time_slots:
                logger.warning(f"⚠️ No time slots in database for doctor {doctor_id}, generating default slots")

                for day_offset in range(7):
                    slot_date = today + timedelta(days=day_offset)

                    # Skip weekends (Saturday=5, Sunday=6)
                    if slot_date.weekday() >= 5:
                        continue

                    # Generate slots from 9:00 to 18:00 (15-minute intervals)
                    for hour in range(9, 18):
                        for minute in [0, 15, 30, 45]:
                            slot_time = f"{hour:02d}:{minute:02d}"
                            slot_datetime = datetime.combine(slot_date, datetime.strptime(slot_time, "%H:%M").time())

                            # Make it timezone-aware
                            slot_datetime = timezone.make_aware(slot_datetime)

                            time_slots.append({
                                "id": f"{slot_date}_{slot_time}",
                                "date": slot_date.isoformat(),
                                "time": slot_time,
                                "available": True,  # All generated slots are available
                                "datetime": slot_datetime.isoformat()
                            })

            # Filter to only available slots and limit to 20
            available_slots = [slot for slot in time_slots if slot['available']][:20]

            logger.info(f"✅ Found {len(available_slots)} available slots for doctor ID {doctor_id}")

            return Response({
                "success": True,
                "timeSlots": available_slots,
                "doctorId": doctor_id,
                "doctorName": f"{doctor.first_name} {doctor.last_name}"
            }, status=200)

        except User.DoesNotExist:
            logger.error(f"❌ Doctor not found: ID {doctor_id}")
            return Response({
                "success": False,
                "error": "Doctor not found"
            }, status=404)
        except Exception as e:
            logger.error(f"❌ Error fetching time slots for doctor {doctor_id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                "success": False,
                "error": "Failed to fetch available time slots"
            }, status=500)

    @action(detail=False, methods=["post"], url_path="verify-access-code", permission_classes=[AllowAny])
    def verify_access_code(self, request):
        """
        Verify consultation access code and authenticate the patient
        Allows unauthenticated access - public endpoint

        POST /api/v1/consultations/verify-access-code/
        {
            "access_code": "ABC123"
        }

        Returns JWT tokens and consultation details for authentication
        """
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            from datetime import timedelta

            access_code = request.data.get("access_code", "").strip().upper()

            if not access_code:
                return Response({
                    "success": False,
                    "error": "Access code is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate code length
            if len(access_code) != 6:
                return Response({
                    "success": False,
                    "error": "Access code must be 6 characters"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Find consultation with this access code
            try:
                consultation = Consultation.objects.select_related(
                    'patient', 'doctor', 'doctor__doctor_profile', 'doctor__doctor_profile__specialization'
                ).get(access_code=access_code)
            except Consultation.DoesNotExist:
                logger.warning(f"⚠️ Invalid access code attempted: {access_code}")
                return Response({
                    "success": False,
                    "error": "Invalid access code"
                }, status=status.HTTP_404_NOT_FOUND)

            # Check if consultation is cancelled or missed
            active_statuses = ['pending', 'scheduled', 'ongoing', 'planned']
            if consultation.status not in active_statuses:
                return Response({
                    "success": False,
                    "error": f"This consultation is no longer active (status: {consultation.status})",
                    "status": consultation.status
                }, status=status.HTTP_400_BAD_REQUEST)

            # 🔐 Generate JWT tokens for the patient (authenticate them)
            patient = consultation.patient
            refresh = RefreshToken.for_user(patient)

            # Set shorter token lifetime for consultation-specific use
            refresh.access_token.set_exp(lifetime=timedelta(hours=3))

            # Build response with consultation details
            specialization = None
            if hasattr(consultation.doctor, 'doctor_profile') and consultation.doctor.doctor_profile:
                if consultation.doctor.doctor_profile.specialization:
                    specialization = {
                        "ru": consultation.doctor.doctor_profile.specialization.name_ru,
                        "en": consultation.doctor.doctor_profile.specialization.name_en,
                        "kz": consultation.doctor.doctor_profile.specialization.name_kz
                    }

            # Get client IP for audit logging
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(',')[0]
            else:
                client_ip = request.META.get('REMOTE_ADDR', 'unknown')

            logger.info(
                f"✅ Access code verified and patient authenticated | "
                f"access_code={access_code} | consultation_id={consultation.id} | "
                f"patient_id={patient.id} | patient_email={patient.email} | "
                f"meeting_id={consultation.meeting_id} | ip={client_ip}"
            )

            return Response({
                "success": True,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "user": {
                    "id": patient.id,
                    "email": patient.email,
                    "first_name": patient.first_name,
                    "last_name": patient.last_name,
                    "role": patient.role
                },
                "consultation": {
                    "id": consultation.id,
                    "meeting_id": consultation.meeting_id,
                    "access_code": consultation.access_code,
                    "status": consultation.status,
                    "is_urgent": consultation.is_urgent,
                    "scheduled_at": consultation.scheduled_at.isoformat() if consultation.scheduled_at else None,
                    "doctor": {
                        "id": consultation.doctor.id,
                        "first_name": consultation.doctor.first_name,
                        "last_name": consultation.doctor.last_name,
                        "email": consultation.doctor.email,
                        "specialization": specialization
                    }
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"❌ Error verifying access code: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                "success": False,
                "error": "An error occurred while verifying the access code"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"], url_path="auto-login", permission_classes=[AllowAny])
    def auto_login(self, request):
        """
        Secure auto-login endpoint using signed JWT magic link tokens
        Allows unauthenticated patients to automatically authenticate via email link

        POST /api/v1/consultations/auto-login/
        {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
        }

        Returns JWT access_token and refresh_token for the patient

        Security features:
        - Cryptographically signed JWT tokens (impossible to forge)
        - Short-lived expiration (2 hours - safe & user-friendly)
        - Minimal token claims (no PII like email addresses)
        - No DB storage needed (stateless)
        - Validates consultation exists and is in active state
        - POST only (not GET) to prevent token leakage in logs
        - Atomic transaction with row locking (prevents race conditions)
        - Single-use enforcement (prevents forwarding attacks)
        """
        try:
            from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
            from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
            from django.db import transaction
            from datetime import timedelta

            token_string = request.data.get("token", "").strip()

            if not token_string:
                logger.warning("⚠️ Auto-login attempted without token")
                return Response({
                    "success": False,
                    "error": "Token is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate the signed JWT magic link token
            try:
                magic_token = AccessToken(token_string)
            except (TokenError, InvalidToken) as e:
                logger.warning(f"⚠️ Invalid or expired magic link token: {str(e)}")
                return Response({
                    "success": False,
                    "error": "Invalid or expired magic link token"
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Verify this is a magic link token (not a regular access token)
            access_type = magic_token.get('access_type')
            if access_type != 'magic_link':
                logger.warning(f"⚠️ Token is not a magic link token: access_type={access_type}")
                return Response({
                    "success": False,
                    "error": "Invalid token type"
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Extract consultation details from token (minimal claims)
            consultation_id = magic_token.get('consultation_id')
            patient_id = magic_token.get('patient_id')

            if not all([consultation_id, patient_id]):
                logger.error("⚠️ Magic link token missing required claims")
                return Response({
                    "success": False,
                    "error": "Invalid token claims"
                }, status=status.HTTP_401_UNAUTHORIZED)

            # 🔒 CRITICAL: Use atomic transaction with row-level locking to prevent race conditions
            # This ensures only ONE request can authenticate, even if multiple hit simultaneously
            with transaction.atomic():
                try:
                    # select_for_update() locks only the Consultation row
                    # Can't use select_related with nullable joins (doctor_profile might not exist)
                    consultation = Consultation.objects.select_for_update().get(
                        id=consultation_id,
                        patient_id=patient_id
                    )
                except Consultation.DoesNotExist:
                    logger.warning(f"⚠️ Consultation not found for magic link: consultation_id={consultation_id}")
                    return Response({
                        "success": False,
                        "error": "Consultation not found or has been deleted"
                    }, status=status.HTTP_404_NOT_FOUND)

                # Validate consultation is in an active state (not cancelled/missed/completed)
                # Allow: pending, scheduled, ongoing, planned
                active_statuses = ['pending', 'scheduled', 'ongoing', 'planned']
                if consultation.status not in active_statuses:
                    logger.info(f"⚠️ Auto-login attempted for inactive consultation: status={consultation.status}, id={consultation_id}")
                    return Response({
                        "success": False,
                        "error": f"This consultation is no longer active (status: {consultation.status})",
                        "status": consultation.status
                    }, status=status.HTTP_403_FORBIDDEN)

                # 🔐 SECURITY: Check if magic link has already been used (prevent forwarded link reuse)
                # Row is locked, so this check is race-condition safe
                if consultation.magic_link_used_at is not None:
                    logger.warning(f"⚠️ Magic link reuse attempt for consultation {consultation_id} (originally used at {consultation.magic_link_used_at})")
                    return Response({
                        "success": False,
                        "error": "This magic link has already been used. Please log in manually or request a new link.",
                        "used_at": consultation.magic_link_used_at.isoformat()
                    }, status=status.HTTP_403_FORBIDDEN)

                # Mark magic link as used (single-use security)
                # This is atomic and race-condition proof due to select_for_update()
                consultation.magic_link_used_at = timezone.now()
                consultation.save(update_fields=['magic_link_used_at'])

                # Store patient reference before transaction commits
                patient = consultation.patient
                patient_email = patient.email
                meeting_id = consultation.meeting_id

            # Generate regular session JWT tokens for the patient (outside transaction)
            refresh = RefreshToken.for_user(patient)

            # Shorten access token lifetime for consultation-specific use
            refresh.access_token.set_exp(lifetime=timedelta(hours=3))

            # Get client IP for audit logging
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(',')[0]
            else:
                client_ip = request.META.get('REMOTE_ADDR', 'unknown')

            logger.info(
                f"✅ Magic link used | consultation_id={consultation_id} | "
                f"patient_id={patient.id} | patient_email={patient_email} | "
                f"meeting_id={meeting_id} | ip={client_ip}"
            )

            # Fetch consultation again for response (transaction is committed, row is unlocked)
            consultation_response = Consultation.objects.select_related(
                'patient', 'doctor', 'doctor__doctor_profile', 'doctor__doctor_profile__specialization'
            ).get(id=consultation_id)

            # Build response with consultation details and JWT tokens
            specialization = None
            if hasattr(consultation_response.doctor, 'doctor_profile') and consultation_response.doctor.doctor_profile:
                if consultation_response.doctor.doctor_profile.specialization:
                    specialization = {
                        "ru": consultation_response.doctor.doctor_profile.specialization.name_ru,
                        "en": consultation_response.doctor.doctor_profile.specialization.name_en,
                        "kz": consultation_response.doctor.doctor_profile.specialization.name_kz
                    }

            return Response({
                "success": True,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "user": {
                    "id": patient.id,
                    "email": patient.email,
                    "first_name": patient.first_name,
                    "last_name": patient.last_name,
                    "role": patient.role
                },
                "consultation": {
                    "id": consultation_response.id,
                    "meeting_id": consultation_response.meeting_id,
                    "access_code": consultation_response.access_code,
                    "status": consultation_response.status,
                    "is_urgent": consultation_response.is_urgent,
                    "scheduled_at": consultation_response.scheduled_at.isoformat() if consultation_response.scheduled_at else None,
                    "doctor": {
                        "id": consultation_response.doctor.id,
                        "first_name": consultation_response.doctor.first_name,
                        "last_name": consultation_response.doctor.last_name,
                        "email": consultation_response.doctor.email,
                        "specialization": specialization
                    }
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"❌ Error during auto-login: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                "success": False,
                "error": "An error occurred during auto-login"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)