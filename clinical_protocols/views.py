"""
API Views for Clinical Protocols
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import ClinicalProtocol, ClinicalProtocolContent
from .serializers import (
    ClinicalProtocolSerializer,
    ClinicalProtocolContentSerializer,
    ProtocolQuestionSerializer,
    ProtocolAnswerSerializer,
)
from .services import rag_service


class ClinicalProtocolViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing clinical protocols

    list: Get all protocols
    retrieve: Get a specific protocol with all its content

    NOTE: Publicly accessible for protocol-ai page
    """
    queryset = ClinicalProtocol.objects.all()
    serializer_class = ClinicalProtocolSerializer
    permission_classes = [AllowAny]  # Public access for protocol-ai page

    @swagger_auto_schema(
        method='post',
        operation_description="Ask a question about clinical protocols using AI (RAG)",
        request_body=ProtocolQuestionSerializer,
        responses={
            200: ProtocolAnswerSerializer,
            400: "Bad Request - Invalid input",
            500: "Internal Server Error - AI service failed"
        },
        tags=['Clinical Protocols AI']
    )
    @action(detail=False, methods=['post'], url_path='ask')
    def ask_question(self, request):
        """
        Ask a question about clinical protocols.
        Uses RAG (Retrieval-Augmented Generation) to answer based on database content.

        Example request:
        ```json
        {
            "question": "Какие диагностические критерии HELLP-синдрома?",
            "protocol_id": 1,
            "language": "ru",
            "include_sources": true
        }
        ```
        """
        # Validate input
        input_serializer = ProtocolQuestionSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(
                {"error": "Invalid input", "details": input_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get validated data
        data = input_serializer.validated_data
        question = data['question']
        protocol_id = data.get('protocol_id')
        content_types = data.get('content_types')
        language = data.get('language', 'ru')
        include_sources = data.get('include_sources', True)

        # Call RAG service
        try:
            result = rag_service.answer_question(
                question=question,
                protocol_id=protocol_id,
                content_types=content_types,
                language=language,
                include_sources=include_sources
            )

            # Serialize response
            output_serializer = ProtocolAnswerSerializer(data=result)
            if output_serializer.is_valid():
                return Response(output_serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": f"Service error: {str(e)}",
                    "question": question,
                    "answer": None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        method='get',
        operation_description="Search protocol content by text query",
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description="Search query",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'content_type',
                openapi.IN_QUERY,
                description="Filter by content type",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Maximum number of results",
                type=openapi.TYPE_INTEGER,
                default=10
            ),
        ],
        responses={200: ClinicalProtocolContentSerializer(many=True)},
        tags=['Clinical Protocols']
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search_content(self, request):
        """
        Search for content sections by text query

        Example: /api/v1/protocols/search/?q=HELLP&content_type=diagnosis&limit=5
        """
        query = request.query_params.get('q', '')
        content_type = request.query_params.get('content_type')
        limit = int(request.query_params.get('limit', 10))

        if not query:
            return Response(
                {"error": "Query parameter 'q' is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Search using RAG service
        content_types = [content_type] if content_type else None
        results = rag_service.search_relevant_content(
            query=query,
            content_types=content_types,
            limit=limit
        )

        return Response(results, status=status.HTTP_200_OK)


class ClinicalProtocolContentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing protocol content sections

    list: Get all content sections
    retrieve: Get a specific content section

    NOTE: Publicly accessible for protocol-ai page
    """
    queryset = ClinicalProtocolContent.objects.select_related('protocol').all()
    serializer_class = ClinicalProtocolContentSerializer
    permission_classes = [AllowAny]  # Public access for protocol-ai page
    filterset_fields = ['protocol', 'content_type', 'source']
    search_fields = ['title', 'content']
    ordering_fields = ['order', 'created_at', 'confidence']
    ordering = ['protocol', 'order']
