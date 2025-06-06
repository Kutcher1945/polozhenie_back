import logging
import requests
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from common.models import User
from .models import Consultation
from .serializers import ConsultationSerializer
import uuid
from django.utils import timezone
import jwt
import time
from django.conf import settings
import re


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
        logger.info("🔍 Получен запрос на AI-рекомендацию врача")
    
        symptoms = request.data.get("symptoms")
        language = request.data.get("language", "ru")
        logger.debug(f"📨 Симптомы: {symptoms}")
        logger.debug(f"🌐 Язык: {language}")
    
        if not symptoms:
            logger.warning("⚠️ Не указаны симптомы")
            return Response({"error": "Symptoms are required."}, status=status.HTTP_400_BAD_REQUEST)
    
        available_doctors = User.objects.filter(role="doctor", is_active=True)
        if not available_doctors.exists():
            logger.warning("❌ Нет доступных врачей")
            return Response({"error": "No doctors available at the moment."}, status=status.HTTP_404_NOT_FOUND)
    
        doctor_list = [
            f"{doc.first_name} {doc.last_name} ({doc.doctor_type})"
            for doc in available_doctors
        ]
        logger.info(f"👨‍⚕️ Найдено {len(doctor_list)} врачей")
    
        prompt = {
            "ru": f"""
    Ты — опытный медицинский помощник. Пациент описывает симптомы: "{symptoms}".
    Вот список доступных врачей: {doctor_list}.
    
    Выбери наиболее подходящего врача на основе симптомов. Ответь строго в формате:
    
    Имя Фамилия (Специализация). Причина: [Развернуто объясни, почему именно этот врач подходит. Свяжи симптомы с областью его специализации. Не упоминай ID].
    
    Пример:
    Сергей Сердечный (Кардиолог). Причина: У пациента имеются жалобы на тахикардию, боли в груди и головокружение. Эти симптомы могут свидетельствовать о нарушении сердечного ритма, с чем работает кардиолог. Также наблюдается снижение энергии и тревожность, что может быть связано с сердечной недостаточностью.
    """,
            "kz": f"""
    Сіз тәжірибелі медициналық көмекшісіз. Пациент мынадай белгілерді сипаттайды: "{symptoms}".
    Міне қолжетімді дәрігерлердің тізімі: {doctor_list}.
    
    Симптомдарға сәйкес ең қолайлы дәрігерді таңдаңыз. Жауап форматы:
    
    Аты Жөні (Мамандығы). Себебі: [Мүмкіндігінше толық негіздеңіз. Симптомдарды дәрігердің мамандығымен байланыстырыңыз. ID көрсетпеңіз].
    
    Мысал:
    Айдос Төлегенов (Кардиолог). Себебі: Пациент жүрек қағуы, кеудедегі ауырсыну және әлсіздікке шағымданады. Бұл белгілер жүрек жеткіліксіздігінің белгісі болуы мүмкін, және оны кардиолог емдейді.
    """
        }.get(language, "")
    
        if not prompt:
            logger.error("❌ Некорректный язык. Поддерживаются только 'ru' и 'kz'")
            return Response({"error": "Unsupported language."}, status=status.HTTP_400_BAD_REQUEST)
    
        try:
            payload = {
                "model": "open-mistral-nemo",
                "temperature": 0.4,
                "top_p": 1,
                "max_tokens": 600,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": symptoms}
                ],
            }
    
            headers = {
                "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            }
    
            logger.info("📡 Отправка запроса в Mistral API")
            response = requests.post("https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            ai_reply = response.json()["choices"][0]["message"]["content"].strip()
            logger.debug(f"🤖 Ответ AI: {ai_reply}")
    
            # 📌 Извлекаем "Имя Фамилия (Специализация). Причина: ..."
            match = re.match(r"(.+?)\s+\((.+?)\)\.?\s+Причина:\s*(.+)", ai_reply)
            if not match:
                logger.error("⚠️ Невозможно извлечь врача и причину из ответа AI")
                return Response({"error": "AI returned unrecognized format."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
            full_name = match.group(1).strip()
            doctor_type = match.group(2).strip()
            reason = match.group(3).strip()
    
            name_parts = full_name.split()
            if len(name_parts) < 2:
                logger.error("❌ Недостаточно данных для поиска врача")
                return Response({"error": "Could not determine doctor name."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
            first_name = name_parts[0]
            last_name = name_parts[-1]
    
            matched_doctor = User.objects.filter(
                role="doctor",
                is_active=True,
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                doctor_type__iexact=doctor_type
            ).first()
    
            if not matched_doctor:
                logger.error(f"❌ Врач '{full_name} ({doctor_type})' не найден")
                return Response({"error": "AI suggested doctor not found."}, status=status.HTTP_404_NOT_FOUND)
    
            logger.info(f"🎯 Рекомендованный врач: {matched_doctor.first_name} {matched_doctor.last_name}")
            return Response({
                "recommended_doctor": {
                    "id": matched_doctor.id,
                    "name": f"{matched_doctor.first_name} {matched_doctor.last_name}",
                    "doctor_type": matched_doctor.doctor_type,
                    "email": matched_doctor.email,
                    "reason": reason
                }
            })
    
        except requests.exceptions.RequestException:
            logger.exception("📡 Ошибка при обращении к Mistral API")
            return Response({"error": "Failed to connect to AI API."}, status=status.HTTP_502_BAD_GATEWAY)
    
        except Exception:
            logger.exception("🔥 Непредвиденная ошибка")
            return Response({"error": "AI error or failed to parse result."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
