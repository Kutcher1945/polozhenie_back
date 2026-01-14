"""
Serializers for Clinical Protocols API
"""
from rest_framework import serializers
from .models import ClinicalProtocol, ClinicalProtocolContent


class ClinicalProtocolContentSerializer(serializers.ModelSerializer):
    """Serializer for protocol content sections"""
    content_type_display = serializers.CharField(source='get_content_type_display', read_only=True)
    protocol_name = serializers.CharField(source='protocol.name', read_only=True)

    class Meta:
        model = ClinicalProtocolContent
        fields = [
            'id',
            'protocol',
            'protocol_name',
            'content_type',
            'content_type_display',
            'title',
            'content',
            'page_from',
            'page_to',
            'source',
            'confidence',
            'order',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ClinicalProtocolListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for protocol list view (no full contents)"""
    content_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClinicalProtocol
        fields = [
            'id',
            'name',
            'url',
            'year',
            'medicine',
            'mkb',
            'mkb_codes',
            'content_count',  # Just the count, not the full data
        ]
        read_only_fields = ['id']


class ClinicalProtocolSerializer(serializers.ModelSerializer):
    """Serializer for clinical protocols (with full contents for detail view)"""
    contents = ClinicalProtocolContentSerializer(many=True, read_only=True)

    class Meta:
        model = ClinicalProtocol
        fields = [
            'id',
            'name',
            'url',
            'year',
            'medicine',
            'mkb',
            'mkb_codes',
            'size',
            'extension',
            'modified',
            'created_at',
            'updated_at',
            'contents',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProtocolQuestionSerializer(serializers.Serializer):
    """Serializer for RAG question input"""
    question = serializers.CharField(
        required=True,
        min_length=3,
        max_length=500,
        help_text="Вопрос пользователя о клиническом протоколе"
    )
    protocol_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID конкретного протокола (опционально)"
    )
    content_types = serializers.ListField(
        child=serializers.ChoiceField(choices=ClinicalProtocolContent.ContentType.choices),
        required=False,
        allow_null=True,
        help_text="Типы контента для поиска (опционально)"
    )
    language = serializers.ChoiceField(
        choices=['ru', 'kk', 'en'],
        default='ru',
        help_text="Язык ответа"
    )
    include_sources = serializers.BooleanField(
        default=True,
        help_text="Включить источники в ответ"
    )


class ProtocolAnswerSourceSerializer(serializers.Serializer):
    """Serializer for source sections in answer"""
    protocol_id = serializers.IntegerField()
    protocol_name = serializers.CharField()
    protocol_url = serializers.URLField(allow_null=True, required=False)
    content_type = serializers.CharField()
    content_type_display = serializers.CharField()
    title = serializers.CharField()
    content = serializers.CharField()
    page_from = serializers.IntegerField(allow_null=True)
    page_to = serializers.IntegerField(allow_null=True)
    confidence = serializers.FloatField()


class ProtocolAnswerMetadataSerializer(serializers.Serializer):
    """Serializer for answer metadata"""
    model = serializers.CharField(allow_null=True)
    usage = serializers.DictField(allow_null=True)
    num_sources = serializers.IntegerField()
    language = serializers.CharField()


class ProtocolAnswerSerializer(serializers.Serializer):
    """Serializer for RAG answer output"""
    question = serializers.CharField()
    answer = serializers.CharField(allow_null=True)
    success = serializers.BooleanField()
    error = serializers.CharField(allow_null=True, required=False)
    metadata = ProtocolAnswerMetadataSerializer()
    sources = ProtocolAnswerSourceSerializer(many=True, required=False)
