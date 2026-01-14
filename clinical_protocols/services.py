"""
RAG Service for Clinical Protocols
Retrieval-Augmented Generation using Mistral AI
"""
import os
import requests
import json
from typing import List, Dict, Any
from django.conf import settings
from django.db.models import Q, Count
from .models import ClinicalProtocol, ClinicalProtocolContent


class ClinicalProtocolRAG:
    """RAG service for answering questions about clinical protocols using Mistral AI"""

    def __init__(self):
        self.api_key = os.getenv("MISTRAL_API_KEY", getattr(settings, "MISTRAL_API_KEY", ""))
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        self.model = "open-mistral-nemo"

    def preprocess_query(self, query: str) -> str:
        """
        Preprocess user query to handle common variations and typos
        """
        query_lower = query.lower().strip()

        # Common medical term variations and typos
        replacements = {
            'help': 'hellp',  # Common typo for HELLP syndrome
            'хелп': 'hellp',  # Cyrillic typo
            'хэлп': 'hellp',  # Another Cyrillic variation
        }

        # Replace known variations
        for typo, correct in replacements.items():
            if typo in query_lower:
                query_lower = query_lower.replace(typo, correct)

        return query_lower

    def search_relevant_content(
        self,
        query: str,
        protocol_id: int = None,
        content_types: List[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant content sections based on user query
        Uses simple text matching - can be upgraded to vector embeddings later
        """
        # Preprocess query to handle typos and variations
        processed_query = self.preprocess_query(query)

        # Build base query
        queryset = ClinicalProtocolContent.objects.all()

        # Filter by protocol if specified
        if protocol_id:
            queryset = queryset.filter(protocol_id=protocol_id)

        # Filter by content types if specified
        if content_types:
            queryset = queryset.filter(content_type__in=content_types)

        # Search in title and content using processed query
        query_words = processed_query.split()
        q_objects = Q()

        for word in query_words:
            q_objects |= Q(title__icontains=word) | Q(content__icontains=word) | Q(protocol__name__icontains=word)

        queryset = queryset.filter(q_objects)

        # Order by confidence and limit results
        results = queryset.select_related('protocol').order_by('-confidence', 'order')[:limit]

        # Convert to dict format
        return [
            {
                'protocol_id': item.protocol_id,
                'protocol_name': item.protocol.name,
                'protocol_url': item.protocol.url if hasattr(item.protocol, 'url') else None,
                'content_type': item.content_type,
                'content_type_display': item.get_content_type_display(),
                'title': item.title,
                'content': item.content,
                'page_from': item.page_from,
                'page_to': item.page_to,
                'confidence': item.confidence,
            }
            for item in results
        ]

    def get_available_protocols(self) -> List[Dict[str, Any]]:
        """Get list of protocols that have content available"""
        from django.db.models import Count
        from .models import ClinicalProtocol

        protocols = ClinicalProtocol.objects.annotate(
            content_count=Count('contents')
        ).filter(content_count__gt=0).values('id', 'name', 'content_count')

        return list(protocols)

    def get_protocol_availability_message(self, language: str = "ru") -> str:
        """
        Generate a message about which protocols are available and which have full data
        """
        protocols = ClinicalProtocol.objects.annotate(
            content_count=Count('contents')
        ).all()

        protocols_with_content = []
        protocols_without_content = []

        for protocol in protocols:
            if protocol.content_count > 0:
                protocols_with_content.append({
                    'name': protocol.name,
                    'count': protocol.content_count
                })
            else:
                protocols_without_content.append(protocol.name)

        if language == "ru":
            msg_parts = []

            if protocols_with_content:
                msg_parts.append("📚 **Протоколы с полными данными:**")
                for p in protocols_with_content:
                    msg_parts.append(f"- **{p['name']}** ({p['count']} секций)")

            if protocols_without_content:
                msg_parts.append("\n📋 **Протоколы в базе (данные в процессе загрузки):**")
                for name in protocols_without_content:
                    msg_parts.append(f"- {name}")

            return "\n".join(msg_parts)

        return ""

    def build_context(self, relevant_sections: List[Dict[str, Any]]) -> str:
        """Build context string from relevant sections for AI"""
        if not relevant_sections:
            return "Нет релевантной информации в базе данных."

        context_parts = []
        for i, section in enumerate(relevant_sections, 1):
            context_parts.append(
                f"[Секция {i}] Протокол: {section['protocol_name']}\n"
                f"Тип: {section['content_type_display']}\n"
                f"Заголовок: {section['title']}\n"
                f"Содержание: {section['content']}\n"
                f"Страницы: {section['page_from']}-{section['page_to']}\n"
            )

        return "\n---\n".join(context_parts)

    def ask_mistral(
        self,
        user_question: str,
        context: str,
        language: str = "ru"
    ) -> Dict[str, Any]:
        """
        Ask Mistral AI to answer the question based on the context
        """
        system_prompt = """Вы - медицинский ассистент, специализирующийся на клинических протоколах.

ЗАДАЧА:
Ответьте на вопрос пользователя, используя ТОЛЬКО информацию из предоставленного контекста клинических протоколов.

ПРАВИЛА:
1. Отвечайте точно и профессионально
2. Используйте ТОЛЬКО информацию из контекста
3. Если информации недостаточно - скажите об этом честно
4. Указывайте источник (название протокола, страницы)
5. Отвечайте на русском языке
6. Не додумывайте и не галлюцинируйте информацию
7. Если вопрос не связан с медициной - вежливо откажитесь отвечать

ФОРМАТ ОТВЕТА:
- Прямой ответ на вопрос
- Ссылка на источник (протокол, страницы)
- Дополнительные детали если релевантны
"""

        if language == "kk":
            system_prompt = system_prompt.replace("русском", "казахском")

        user_message = f"""КОНТЕКСТ ИЗ КЛИНИЧЕСКИХ ПРОТОКОЛОВ:
{context}

---

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{user_question}

Ответьте на вопрос, используя информацию из контекста выше."""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.1,  # Low temperature for factual responses
            "max_tokens": 2000,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            answer = result["choices"][0]["message"]["content"]

            return {
                "success": True,
                "answer": answer,
                "model": self.model,
                "usage": result.get("usage", {}),
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"API request failed: {str(e)}",
                "answer": None,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "answer": None,
            }

    def answer_question(
        self,
        question: str,
        protocol_id: int = None,
        content_types: List[str] = None,
        language: str = "ru",
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Main method: Answer user question using RAG approach

        Args:
            question: User's question
            protocol_id: Optional - filter by specific protocol
            content_types: Optional - filter by content types
            language: Response language (ru/kk)
            include_sources: Whether to include source sections in response

        Returns:
            Dict with answer, sources, and metadata
        """
        # Step 1: Retrieve relevant content
        relevant_sections = self.search_relevant_content(
            query=question,
            protocol_id=protocol_id,
            content_types=content_types,
            limit=10
        )

        # Step 2: Check if we found any content
        if not relevant_sections:
            # No content found - provide helpful information about available protocols
            availability_msg = self.get_protocol_availability_message(language)

            if language == "ru":
                answer = f"""К сожалению, в предоставленном контексте нет информации, которая могла бы помочь ответить на ваш вопрос.

{availability_msg}

Пожалуйста, попробуйте задать вопрос по протоколу HELLP-СИНДРОМ, или дождитесь загрузки данных по другим протоколам."""
            else:
                answer = "No relevant information found in the database."

            return {
                "question": question,
                "answer": answer,
                "success": True,
                "error": None,
                "metadata": {
                    "model": None,
                    "usage": None,
                    "num_sources": 0,
                    "language": language,
                },
                "sources": []
            }

        # Step 3: Build context
        context = self.build_context(relevant_sections)

        # Step 4: Generate answer using AI
        ai_response = self.ask_mistral(
            user_question=question,
            context=context,
            language=language
        )

        # Step 5: Build final response
        response = {
            "question": question,
            "answer": ai_response.get("answer"),
            "success": ai_response.get("success", False),
            "error": ai_response.get("error"),
            "metadata": {
                "model": ai_response.get("model"),
                "usage": ai_response.get("usage"),
                "num_sources": len(relevant_sections),
                "language": language,
            }
        }

        if include_sources:
            response["sources"] = relevant_sections

        return response


# Singleton instance
rag_service = ClinicalProtocolRAG()
