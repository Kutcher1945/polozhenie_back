from django.db import models

class Player(models.Model):
    nickname = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Никнейм",
        help_text="Уникальное имя игрока"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата регистрации"
    )

    class Meta:
        verbose_name = "Игрок"
        verbose_name_plural = "Игроки"
        db_table = "ai_game_player"

    def __str__(self):
        return self.nickname


class Question(models.Model):
    symptoms = models.TextField(
        verbose_name="Симптомы",
        help_text="Описание симптомов для диагноза"
    )
    correct_answer = models.CharField(
        max_length=255,
        verbose_name="Правильный ответ"
    )
    wrong_answers = models.JSONField(
        verbose_name="Неправильные ответы",
        help_text="JSON-массив неправильных вариантов"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
        db_table = "ai_game_question"

    def __str__(self):
        return f"Вопрос: {self.symptoms[:50]}..."


class GameSession(models.Model):
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        verbose_name="Игрок",
        related_name="sessions"
    )
    score = models.IntegerField(
        verbose_name="Очки",
        help_text="Количество правильных ответов"
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время начала"
    )
    ended_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Время окончания"
    )

    class Meta:
        verbose_name = "Игровая сессия"
        verbose_name_plural = "Игровые сессии"
        db_table = "ai_game_session"

    def __str__(self):
        return f"{self.player.nickname} — {self.score} очков"
