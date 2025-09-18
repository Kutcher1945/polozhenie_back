import logging
import requests
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from common.models import User
from .models import Consultation, AIRecommendationLog
from .serializers import ConsultationSerializer
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

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
def csrf_token_view(request):
    return JsonResponse({"message": "CSRF cookie set"})

# Create your views here.
class ConsultationViewSet(ModelViewSet):
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "meeting_id"  # ✅ Tell DRF to use meeting_id in URLs

    def get_queryset(self):
        user = self.request.user

        print("🔍 DEBUG: User Object ->", user)  # ✅ Print the user object
        print("🔍 DEBUG: User Authenticated? ->", user.is_authenticated)

        if not user.is_authenticated:
            return Consultation.objects.none()

        print("🔍 DEBUG: User Role ->", getattr(user, "role", "No role found"))

        if hasattr(user, "role") and user.role == "doctor":
            return Consultation.objects.filter(doctor=user)

        return Consultation.objects.filter(patient=user)

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
    
        # 🚫 No longer preventing duplicate consultations
        # existing_consultation = Consultation.objects.filter(patient=user, doctor=doctor, status="pending").first()
        # if existing_consultation:
        #     return Response(
        #         {"error": "You already have a pending consultation with this doctor.", "meeting_id": existing_consultation.meeting_id},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )
    
        meeting_id = str(uuid.uuid4())
    
        consultation = Consultation.objects.create(
            patient=user,
            doctor=doctor,
            meeting_id=meeting_id,
            status="pending",
        )
    
        print(f"🔔 Doctor {doctor.email} received a consultation request from {user.email}")
    
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


    @action(detail=False, methods=["post"], url_path="ai-recommend")
    def ai_recommend_doctor(self, request):
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
    
        # Prompt for the reason (in the user's language) with possible urgency check
        reason_prompt = f"""
        You are a medical assistant. The patient described the symptoms: "{symptoms}". 
        Please provide a detailed explanation of the possible causes, symptoms, and recommendations for treatment or referral to a doctor.
    
        1. Provide the **reason** (explanation) in the language the question was asked.
        2. The explanation should include:
           - Possible causes for the symptoms.
           - Additional symptoms or related signs.
           - Recommendations for treatment or referral.
        3. Your answer should strictly follow this JSON structure:
    
        {{
          "reason": "<detailed_explanation_in_user_language>"
        }}
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
                # Parse the JSON responses with better error handling
                try:
                    specialty_data = json.loads(specialty_reply)
                    specialty = specialty_data["specialty"].strip().lower()
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse specialty JSON: {e}")
                    logger.warning(f"Specialty response: {specialty_reply}")
                    raise

                try:
                    reason_data = json.loads(reason_reply)
                    reason = reason_data["reason"].strip()
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse reason JSON: {e}")
                    logger.warning(f"Reason response: {reason_reply}")
                    raise

                try:
                    urgency_data = json.loads(urgency_reply)
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
    
            # Query doctors based on the specialty (in Russian)
            doctors = list(User.objects.filter(
                role="doctor",
                is_active=True,
                doctor_specialization__name_ru__icontains=specialty
            )[:10])
    
            if not doctors:
                logger.warning(f"❌ Не найден врач по специализации '{specialty}'")
                logger.warning(f"📨 Ответ от AI (specialty): {specialty_reply}")
                logger.warning(f"📨 Ответ от AI (reason): {reason_reply}")
                logger.warning(f"📨 Ответ от AI (urgency): {urgency_reply}")
    
                AIRecommendationLog.objects.create(
                    symptoms=symptoms,
                    ai_raw_response={"specialty": specialty_reply, "reason": reason_reply, "urgency": urgency_reply},
                    recommended_specialty=specialty,
                    reason=reason,
                    matched_doctor=None,
                    fallback_used=False,
                    specialty_not_found=specialty,
                    urgency=urgency  # Store urgency level in the log
                )
    
                return Response({
                    "success": False,
                    "error": f"No doctor found for '{specialty}'",
                    "fallback_used": False,
                    "ai_data": {
                        "specialty": specialty,
                        "reason": reason,
                        "urgency": urgency,  # Include urgency in the response
                        "raw_specialty": specialty_reply,
                        "raw_reason": reason_reply,
                        "raw_urgency": urgency_reply
                    }
                }, status=200)
    
            # Select a random doctor
            doctor = random.choice(doctors)
            logger.info(f"👨‍⚕️ Назначен врач: {doctor.first_name} {doctor.last_name} ({doctor.doctor_specialization.name_ru})")
    
            AIRecommendationLog.objects.create(
                symptoms=symptoms,
                ai_raw_response={"specialty": specialty_reply, "reason": reason_reply, "urgency": urgency_reply},
                recommended_specialty=specialty,
                reason=reason,
                matched_doctor=doctor,
                fallback_used=False,
                urgency=urgency  # Store urgency level in the log
            )
    
            return Response({
                "success": True,
                "recommended_doctor": {
                    "id": doctor.id,
                    "name": f"{doctor.first_name} {doctor.last_name}",
                    "doctor_type": doctor.doctor_specialization.name_ru,  # Use doctor_type to match frontend expectation
                    "email": doctor.email,
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