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


logger = logging.getLogger(__name__)

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

        if user != consultation.patient and user != consultation.doctor:
            return Response({"error": "You are not part of this consultation."}, status=status.HTTP_403_FORBIDDEN)

        room_name = consultation.meeting_id
        identity = str(user.id)

        payload = {
            "jti": f"{identity}-{int(time.time())}",
            "iss": settings.LIVEKIT_API_KEY,
            "sub": "video",
            "exp": int(time.time()) + 3600,
            "nbf": int(time.time()),
            "video": {
                "roomJoin": True,
                "room": room_name,
            },
        }

        token = jwt.encode(payload, settings.LIVEKIT_API_SECRET, algorithm="HS256")

        return Response({
            "token": token,
            "room": room_name,
            "identity": identity,
            "url": settings.LIVEKIT_URL,
        })

    @action(detail=False, methods=["post"], url_path="ai-recommend")
    def ai_recommend_doctor(self, request):
        symptoms = request.data.get("symptoms")
        language = request.data.get("language", "ru")

        if not symptoms:
            return Response({"error": "Symptoms are required."}, status=400)

        prompt = {
            "ru": f"""Ты — медицинский ассистент. Пациент описал симптомы: "{symptoms}".
    Ответь строго в JSON-формате:
    {{
      "specialty": "<специализация>",
      "reason": "<пояснение>"
    }}""",
            "kz": f"""Сіз медициналық көмекшісіз. Пациент белгілерді сипаттады: "{symptoms}".
    Жауапты тек JSON форматында қайтарыңыз:
    {{
      "specialty": "<мамандық>",
      "reason": "<түсіндіру>"
    }}"""
        }.get(language, "")

        if not prompt:
            return Response({"error": "Unsupported language"}, status=400)

        try:
            payload = {
                "model": "open-mistral-nemo",
                "temperature": 0.3,
                "top_p": 1,
                "max_tokens": 400,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": symptoms}
                ],
            }

            headers = {
                "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            }

            logger.info("📡 Отправка в LLM")
            response = requests.post("https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            reply_text = response.json()["choices"][0]["message"]["content"].strip()

            logger.debug(f"🧠 Ответ AI:\n{reply_text}")

            try:
                ai_data = json.loads(reply_text)
                specialty_raw = ai_data["specialty"].strip().lower()
                reason = ai_data["reason"].strip()
            except (json.JSONDecodeError, KeyError) as e:
                logger.error("⚠️ Ошибка парсинга JSON")
                logger.warning(f"📥 Сырой ответ от AI:\n{reply_text}")
                return Response({"error": "Invalid AI response format", "raw": reply_text}, status=500)

            # ✅ Оставляем только первую специализацию
            specialty = re.split(r" или | и |,|/", specialty_raw)[0].strip()
            logger.info(f"🎯 AI выбрал специализацию: {specialty}")

            doctors = list(User.objects.filter(
                role="doctor",
                is_active=True,
                doctor_type__icontains=specialty
            )[:10])

            if not doctors:
                logger.warning(f"❌ Не найден врач по специализации '{specialty}'")
                logger.warning(f"📨 Ответ от AI: {reply_text}")

                # 🔥 Запись в лог с отсутствием врача
                AIRecommendationLog.objects.create(
                    symptoms=symptoms,
                    ai_raw_response=reply_text,
                    recommended_specialty=specialty,
                    reason=reason,
                    matched_doctor=None,
                    fallback_used=False,
                    specialty_not_found=specialty
                )

                return Response({
                    "error": f"No doctor found for '{specialty}'",
                    "ai_response": reply_text
                }, status=404)

            doctor = random.choice(doctors)
            logger.info(f"👨‍⚕️ Назначен врач: {doctor.first_name} {doctor.last_name} ({doctor.doctor_type})")

            # ✅ Лог успешной рекомендации
            AIRecommendationLog.objects.create(
                symptoms=symptoms,
                ai_raw_response=reply_text,
                recommended_specialty=specialty,
                reason=reason,
                matched_doctor=doctor,
                fallback_used=False
            )

            return Response({
                "recommended_doctor": {
                    "id": doctor.id,
                    "name": f"{doctor.first_name} {doctor.last_name}",
                    "doctor_type": doctor.doctor_type,
                    "email": doctor.email,
                    "reason": reason
                }
            })

        except requests.exceptions.RequestException:
            logger.exception("❌ Ошибка запроса к AI")
            return Response({"error": "LLM API unavailable"}, status=502)
        except Exception as e:
            logger.exception("🔥 Непредвиденная ошибка")
            return Response({"error": str(e)}, status=500)

