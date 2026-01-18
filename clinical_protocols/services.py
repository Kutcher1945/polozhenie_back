"""
RAG Service for Clinical Protocols
Retrieval-Augmented Generation using Mistral AI
"""
import os
import requests
import json
import hashlib
from typing import List, Dict, Any
from django.conf import settings
from django.core.cache import cache
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

    def is_protocol_list_query(self, query: str) -> tuple[bool, bool]:
        """
        Detect if user is asking for a list of available protocols
        Returns: (is_list_query, show_all)
        """
        query_lower = query.lower().strip()

        # Check for "show all" keywords
        show_all_keywords = [
            'все протоколы',
            'покажи все',
            'показать все',
            'полный список',
            'полностью',
        ]
        show_all = any(keyword in query_lower for keyword in show_all_keywords)

        # Russian keywords for protocol listing
        list_keywords = [
            'какие протоколы',
            'какие имеются протоколы',
            'список протоколов',
            'покажи протоколы',
            'доступные протоколы',
            'есть протоколы',
            'все протоколы',
            'протоколы в базе',
        ]

        is_list_query = any(keyword in query_lower for keyword in list_keywords)
        return (is_list_query, show_all)

    def is_greeting(self, query: str) -> bool:
        """
        Detect if user is sending a greeting
        Returns: True if greeting detected
        """
        query_lower = query.lower().strip()

        # Common greetings in Russian, English, and Kazakh
        greeting_keywords = [
            # Russian
            'привет',
            'здравствуй',
            'приветствую',
            'добрый день',
            'доброе утро',
            'добрый вечер',
            'здравия',
            'салам',
            # English
            'hi',
            'hello',
            'hey',
            'good morning',
            'good afternoon',
            'good evening',
            'greetings',
            # Kazakh
            'сәлем',
            'сәлеметсіз',
            'қайырлы таң',
            'қайырлы күн',
            # Short common messages
            'ok',
            'okay',
        ]

        # Exact match for very short greetings or starts with greeting
        return (
            query_lower in greeting_keywords or
            any(query_lower.startswith(keyword) for keyword in greeting_keywords)
        )

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

    def get_protocol_availability_message(self, language: str = "ru", limit: int = 15) -> Dict[str, Any]:
        """
        Generate a message about which protocols are available and which have full data
        Returns a dict with message and metadata for pagination
        """
        protocols = ClinicalProtocol.objects.annotate(
            content_count=Count('contents')
        ).all()

        protocols_with_content = []
        protocols_without_content = []

        for protocol in protocols:
            if protocol.content_count > 0:
                protocols_with_content.append({
                    'id': protocol.id,
                    'name': protocol.name,
                    'count': protocol.content_count
                })
            else:
                protocols_without_content.append({
                    'id': protocol.id,
                    'name': protocol.name
                })

        # Calculate pagination
        total_with_content = len(protocols_with_content)
        total_without_content = len(protocols_without_content)
        showing_with_content = min(limit, total_with_content)
        showing_without_content = min(limit, total_without_content)

        if language == "ru":
            msg_parts = []

            # Summary header
            msg_parts.append(f"📊 **Всего в базе данных: {total_with_content + total_without_content} протоколов**\n")

            if protocols_with_content:
                msg_parts.append(f"📚 **Протоколы с полными данными ({total_with_content}):**")
                for p in protocols_with_content[:limit]:
                    msg_parts.append(f"• **{p['name']}** ({p['count']} секций)")

                if total_with_content > limit:
                    remaining = total_with_content - limit
                    msg_parts.append(f"\n_... и еще {remaining} протоколов с данными_")

            if protocols_without_content:
                msg_parts.append(f"\n📋 **Протоколы в базе без данных ({total_without_content}):**")
                for p in protocols_without_content[:limit]:
                    msg_parts.append(f"• {p['name']}")

                if total_without_content > limit:
                    remaining = total_without_content - limit
                    msg_parts.append(f"\n_... и еще {remaining} протоколов в процессе загрузки_")

            msg_parts.append("\n💡 **Подсказка:** Нажмите на протокол ниже или задайте вопрос!")

            return {
                "message": "\n".join(msg_parts),
                "has_more": (total_with_content > limit) or (total_without_content > limit),
                "total_with_content": total_with_content,
                "total_without_content": total_without_content,
                "showing_with_content": showing_with_content,
                "showing_without_content": showing_without_content,
                "interactive_protocols": protocols_with_content[:limit],  # For interactive UI
            }

        return {
            "message": "",
            "has_more": False,
            "total_with_content": 0,
            "total_without_content": 0,
            "showing_with_content": 0,
            "showing_without_content": 0,
        }

    def build_context(self, relevant_sections: List[Dict[str, Any]]) -> str:
        """Build context string from relevant sections for AI (legacy method)"""
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

    def build_context_smart(self, relevant_sections: List[Dict[str, Any]], max_chars: int = 12000) -> str:
        """
        Build context with smart features:
        - Character limit to avoid token overflow
        - Deduplication to avoid redundant information
        - Confidence-based ranking
        """
        if not relevant_sections:
            return "Нет релевантной информации в базе данных."

        context_parts = []
        total_chars = 0
        seen_content = set()  # Track duplicate content to avoid repetition

        # Sort by confidence (highest first)
        sorted_sections = sorted(
            relevant_sections,
            key=lambda x: x.get('confidence', 0),
            reverse=True
        )

        for i, section in enumerate(sorted_sections, 1):
            # Create a hash of first 100 characters to detect duplicates
            content_preview = section['content'][:100].strip().lower()
            content_hash = hash(content_preview)

            # Skip if we've seen very similar content
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            # Build section text
            section_text = f"""[Секция {i}] Протокол: {section['protocol_name']}
Тип: {section['content_type_display']}
Заголовок: {section['title']}
Содержание: {section['content']}
Страницы: {section['page_from']}-{section['page_to']}
"""

            # Check if adding this section would exceed limit
            if total_chars + len(section_text) > max_chars:
                # Add note about truncation
                context_parts.append(f"\n[Примечание: Контекст ограничен. Показаны наиболее релевантные {i-1} секций из {len(relevant_sections)}]")
                break

            context_parts.append(section_text)
            total_chars += len(section_text)

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
        system_prompt = """Вы - опытный врач-консультант, специализирующийся на клинических протоколах.

ПРОЦЕСС ОТВЕТА:
1. Проанализируйте вопрос пользователя
2. Найдите релевантную информацию в предоставленных клинических протоколах
3. Сформулируйте ясный, структурированный ответ
4. Укажите конкретные источники (протокол, страницы)
5. Если информации недостаточно - честно скажите об этом

ФОРМАТ ОТВЕТА:
✅ Используйте заголовки (**жирный текст** для важных разделов)
✅ Нумерованные списки (1., 2., 3.) для последовательных критериев
✅ Маркированные списки (•) для перечислений
✅ ОБЯЗАТЕЛЬНО добавьте раздел "📚 **Источники:**" в конце с указанием протокола и страниц

ПРАВИЛА:
✅ Отвечайте точно и профессионально, используя медицинскую терминологию
✅ Базируйтесь ТОЛЬКО на информации из предоставленного контекста
✅ Структурируйте ответ для удобства чтения
✅ Всегда указывайте конкретные источники в конце ответа
✅ Если нужной информации нет - укажите, какой именно информации не хватает

❌ НЕ придумывайте факты и данные
❌ НЕ используйте информацию, которой нет в контексте
❌ НЕ отвечайте на вопросы вне медицинской тематики
❌ НЕ давайте персональные медицинские рекомендации конкретным пациентам

ПРИМЕР ХОРОШЕГО ОТВЕТА:
**Диагностические критерии HELLP-синдрома:**

1. **H (Hemolysis)** - гемолиз:
   • Наличие шизоцитов в мазке крови
   • Билирубин > 20 мкмоль/л

2. **EL (Elevated Liver enzymes)** - повышение печеночных ферментов:
   • АСТ > 70 МЕ/л
   • АЛТ > 70 МЕ/л

3. **LP (Low Platelets)** - тромбоцитопения:
   • Тромбоциты < 100×10⁹/л

📚 **Источники:**
- Клинический протокол "HELLP-синдром при беременности", стр. 8-10
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
            "temperature": 0.2,  # Slightly higher for better structure while staying factual
            "max_tokens": 2500,  # Increased for more detailed responses
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

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "AI service timeout",
                "answer": "⏱️ Извините, AI сервис не ответил вовремя. Попробуйте переформулировать вопрос или задать более конкретный вопрос.",
                "model": self.model,
            }

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None

            if status_code == 429:
                return {
                    "success": False,
                    "error": "Rate limit exceeded",
                    "answer": "⏳ Система перегружена запросами. Пожалуйста, подождите минуту и попробуйте снова.",
                    "model": self.model,
                }
            elif status_code == 401:
                return {
                    "success": False,
                    "error": "Invalid API key",
                    "answer": "🔐 Проблема с доступом к AI сервису. Пожалуйста, обратитесь к администратору.",
                    "model": self.model,
                }
            elif status_code == 503:
                return {
                    "success": False,
                    "error": "Service unavailable",
                    "answer": "🔧 AI сервис временно недоступен. Попробуйте через несколько минут.",
                    "model": self.model,
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP error {status_code}",
                    "answer": f"❌ Произошла ошибка при обращении к AI сервису (код: {status_code}). Попробуйте еще раз.",
                    "model": self.model,
                }

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Connection error",
                "answer": "📡 Не удается подключиться к AI сервису. Проверьте подключение к интернету или попробуйте позже.",
                "model": self.model,
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"API request failed: {str(e)}",
                "answer": "❌ Произошла ошибка при запросе к AI. Попробуйте еще раз или обратитесь в поддержку.",
                "model": self.model,
            }

        except KeyError as e:
            return {
                "success": False,
                "error": f"Invalid API response format: {str(e)}",
                "answer": "⚠️ Получен некорректный ответ от AI. Попробуйте переформулировать вопрос.",
                "model": self.model,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "answer": "❌ Произошла непредвиденная ошибка. Пожалуйста, попробуйте еще раз или обратитесь в службу поддержки.",
                "model": self.model,
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
        Main method: Answer user question using RAG approach with caching

        Args:
            question: User's question
            protocol_id: Optional - filter by specific protocol
            content_types: Optional - filter by content types
            language: Response language (ru/kk)
            include_sources: Whether to include source sections in response

        Returns:
            Dict with answer, sources, and metadata
        """
        # Create cache key from normalized question + parameters
        cache_data = {
            'question': question.lower().strip(),
            'protocol_id': protocol_id,
            'content_types': sorted(content_types) if content_types else None,
            'language': language,
            'include_sources': include_sources,
        }
        cache_key_string = json.dumps(cache_data, sort_keys=True)
        cache_key = f"protocol_ai:{hashlib.md5(cache_key_string.encode()).hexdigest()}"

        # Try to get from cache first
        cached_response = cache.get(cache_key)
        if cached_response:
            print(f"✅ Cache HIT for question: {question[:50]}...")
            return cached_response

        print(f"❌ Cache MISS for question: {question[:50]}...")

        # Check if this is a greeting
        is_greeting = self.is_greeting(question)
        if is_greeting:
            availability_data = self.get_protocol_availability_message(language, limit=10)

            if language == "ru":
                greeting_response = f"""Здравствуйте! 👋

Я - AI-ассистент по клиническим протоколам. Я помогу вам найти информацию о диагностике, лечении и медицинских процедурах.

**Что я могу:**
• Отвечать на вопросы по клиническим протоколам
• Находить диагностические критерии заболеваний
• Подсказывать методы лечения и дозировки
• Объяснять медицинские процедуры

**Как задавать вопросы:**
Просто напишите свой вопрос естественным языком! Например:
• "Какие критерии HELLP-синдрома?"
• "Как лечить диабетический кетоацидоз?"
• "Показания к кесареву сечению?"

{availability_data['message']}"""
            else:
                greeting_response = f"""Hello! 👋

I am an AI assistant for clinical protocols. I can help you find information about diagnosis, treatment, and medical procedures.

{availability_data['message']}"""

            response = {
                "question": question,
                "answer": greeting_response,
                "success": True,
                "error": None,
                "metadata": {
                    "model": None,
                    "usage": None,
                    "num_sources": 0,
                    "language": language,
                    "is_greeting": True,
                    "total_protocols": availability_data["total_with_content"] + availability_data["total_without_content"],
                    "interactive_protocols": availability_data.get("interactive_protocols", []),
                },
                "sources": []
            }

            # Cache the greeting response
            cache.set(cache_key, response, 3600)
            return response

        # Check if user is asking for protocol list
        is_list_query, show_all = self.is_protocol_list_query(question)
        if is_list_query:
            # Determine limit based on show_all flag
            limit = 999999 if show_all else 15
            availability_data = self.get_protocol_availability_message(language, limit=limit)

            return {
                "question": question,
                "answer": availability_data["message"],
                "success": True,
                "error": None,
                "metadata": {
                    "model": None,
                    "usage": None,
                    "num_sources": 0,
                    "language": language,
                    "is_protocol_list": True,
                    "has_more": availability_data["has_more"] if not show_all else False,
                    "total_protocols": availability_data["total_with_content"] + availability_data["total_without_content"],
                    "interactive_protocols": availability_data.get("interactive_protocols", []),
                },
                "sources": []
            }

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
            availability_data = self.get_protocol_availability_message(language, limit=10)
            availability_msg = availability_data["message"]

            if language == "ru":
                answer = f"""К сожалению, в предоставленном контексте нет информации, которая могла бы помочь ответить на ваш вопрос.

{availability_msg}"""
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

        # Step 3: Build context (using smart builder)
        context = self.build_context_smart(relevant_sections)

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

        # Cache successful responses for 1 hour (3600 seconds)
        if response.get('success') and response.get('answer'):
            cache.set(cache_key, response, 3600)
            print(f"💾 Cached response for: {question[:50]}...")

        return response


# Singleton instance
rag_service = ClinicalProtocolRAG()
