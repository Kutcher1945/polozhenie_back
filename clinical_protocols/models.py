from django.db import models


class ClinicalProtocol(models.Model):
    name = models.TextField()
    url = models.URLField(max_length=1000, unique=True)

    year = models.PositiveSmallIntegerField()

    medicine = models.CharField(max_length=255, blank=True)
    mkb = models.CharField(max_length=50, blank=True)
    mkb_codes = models.JSONField(default=list, blank=True)

    size = models.PositiveIntegerField(help_text="File size in bytes")
    extension = models.CharField(max_length=10)

    modified = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "clinical_protocols"
        ordering = ["-year", "name"]
        verbose_name = "Клинический протокол"
        verbose_name_plural = "Клинические протоколы"


class ClinicalProtocolContent(models.Model):
    class ContentType(models.TextChoices):
        DEFINITION = "definition", "Определение"
        DIAGNOSIS = "diagnosis", "Диагностика"
        CLASSIFICATION = "classification", "Классификация"
        DIFFERENTIAL = "differential", "Дифференциальный диагноз"
        TREATMENT = "treatment", "Лечение"
        DRUGS = "drugs", "Лекарственные средства"
        ALGORITHM = "algorithm", "Алгоритм ведения"
        COMPLICATIONS = "complications", "Осложнения"
        INDICATIONS = "indications", "Показания"
        CONTRAINDICATIONS = "contraindications", "Противопоказания"

        REFERENCES = "references", "Источники и литература"
        META = "meta", "Организационная информация"

        OTHER = "other", "Другое"

    protocol = models.ForeignKey(
        "ClinicalProtocol",
        on_delete=models.CASCADE,
        related_name="contents"
    )

    content_type = models.CharField(
        max_length=32,
        choices=ContentType.choices,
        db_index=True
    )

    title = models.TextField(
        blank=True,
        help_text="Заголовок раздела (если есть)"
    )

    content = models.TextField(
        help_text="Основной текст раздела"
    )

    page_from = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Страница PDF (начало)"
    )

    page_to = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Страница PDF (конец)"
    )

    source = models.CharField(
        max_length=50,
        default="pdf",
        help_text="Источник данных: pdf / guideline / update / ai"
    )

    confidence = models.FloatField(
        default=1.0,
        help_text="Доверие к источнику (1.0 = оригинал из протокола)"
    )

    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Порядок внутри одного content_type"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.protocol_id} | {self.content_type} | {self.title or '—'}"

    class Meta:
        db_table = "clinical_protocols_content"
        verbose_name = "Контент клинического протокола"
        verbose_name_plural = "Контент клинических протоколов"

        ordering = ["protocol", "content_type", "order"]

        indexes = [
            models.Index(fields=["protocol", "content_type"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["protocol", "content_type", "title"],
                name="uniq_protocol_content_block"
            )
        ]

