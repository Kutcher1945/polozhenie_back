from django.conf import settings
import requests
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Max
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Player, Question, GameSession
from .serializers import PlayerSerializer, QuestionSerializer, GameSessionSerializer
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.permissions import AllowAny


class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.order_by("-created_at")
    serializer_class = QuestionSerializer


@method_decorator(csrf_exempt, name='dispatch')
class GameSessionViewSet(viewsets.ModelViewSet):
    queryset = GameSession.objects.select_related("player").order_by("-ended_at")
    serializer_class = GameSessionSerializer

    MISTRAL_API_KEY = settings.MISTRAL_API_KEY
    MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
    
    @action(detail=False, methods=["post"])
    def generate_question(self, request):
        prompt = """
    Сгенерируй медицинский вопрос для викторины. Верни JSON строго в формате:
    {
      "symptoms": "описание симптомов",
      "correct_answer": "правильный диагноз",
      "wrong_answers": ["неправильный1", "неправильный2"]
    }
    ⚠️ Только JSON. Без пояснений.
    """
        try:
            response = requests.post(
                self.MISTRAL_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.MISTRAL_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "open-mistral-nemo",
                    "temperature": 0.8,
                    "top_p": 1,
                    "max_tokens": 400,
                    "messages": [
                        {"role": "system", "content": "Ты создаешь медицинские викторины."},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            content = response.json()["choices"][0]["message"]["content"]
    
            # === Save to DB ===
            import json
            parsed = json.loads(content)
    
            question = Question.objects.create(
                symptoms=parsed["symptoms"].strip(),
                correct_answer=parsed["correct_answer"].strip(),
                wrong_answers=parsed["wrong_answers"],
            )
    
            # Return serialized version (optional)
            serializer = QuestionSerializer(question)
            return Response(serializer.data)
    
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    def generate_nickname(self, request):
        existing_nicks = set(Player.objects.values_list("nickname", flat=True))

        prompt = f"""
    Придумай уникальный никнейм на английском в стиле CyberDoctor, PsychoTiger.
    Ник не должен совпадать с: {', '.join(existing_nicks)}
    ⚠️ Только ник, без кавычек и без пояснений.
    """

        try:
            # 1. Запрос к Mistral
            response = requests.post(
                self.MISTRAL_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.MISTRAL_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "open-mistral-nemo",
                    "temperature": 0.7,
                    "top_p": 1,
                    "messages": [
                        {"role": "system", "content": "Ты генератор никнеймов."},
                        {"role": "user", "content": prompt},
                    ],
                },
            )

            base_nick = response.json()["choices"][0]["message"]["content"].strip().strip('"')

            # 2. Проверка на уникальность и добавление суффикса при необходимости
            final_nick = base_nick
            suffix = 1
            while final_nick in existing_nicks:
                final_nick = f"{base_nick}{suffix:02d}"
                suffix += 1

            return Response({"nickname": final_nick})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=False, methods=["post"])
    def submit(self, request):
        nickname = request.data.get("nickname")
        score = request.data.get("score")

        if not nickname or score is None:
            return Response(
                {"error": "nickname and score are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        player, _ = Player.objects.get_or_create(nickname=nickname)
        session = GameSession.objects.create(player=player, score=score)

        return Response({"message": "Session recorded", "session_id": session.id})

    @swagger_auto_schema(
        operation_summary="Top 10 Leaderboard",
        operation_description="Returns a list of top 10 players with the highest scores.",
        responses={
            200: openapi.Response(
                description="List of top players",
                examples={
                    "application/json": [
                        {"nickname": "NeuroFalcon", "score": 12},
                        {"nickname": "CyberMedic", "score": 10},
                    ]
                },
            )
        },
    )
    @action(detail=False, methods=["get"])
    def leaderboard(self, request):
        top_scores = (
            GameSession.objects
            .values("player__nickname")
            .annotate(score=Max("score"))
            .order_by("-score")[:10]
        )
        result = [
            {"nickname": entry["player__nickname"], "score": entry["score"]}
            for entry in top_scores
        ]
        return Response(result)
