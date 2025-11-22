from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.conf import settings
import requests
import json
import logging

logger = logging.getLogger(__name__)


class ClinicsPagination(PageNumberPagination):
    """Пагинация для клиник - 12 на страницу"""
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50

from .models import Clinics, Country, Region, City, District
from .serializers import (
    ClinicsListSerializer,
    ClinicsDetailSerializer,
    CountrySerializer,
    RegionSerializer,
    CitySerializer,
    DistrictSerializer,
)


class ClinicsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для получения списка клиник

    GET /api/v1/clinics/ - список клиник (с пагинацией)
    GET /api/v1/clinics/{id}/ - детали клиники
    GET /api/v1/clinics/cities/ - список городов с клиниками
    GET /api/v1/clinics/categories/ - список категорий клиник
    """
    queryset = Clinics.objects.all()
    permission_classes = [AllowAny]
    pagination_class = ClinicsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['city', 'district', 'region', 'country']
    search_fields = ['name', 'address', 'description']
    ordering_fields = ['rating', 'review_count', 'name']
    ordering = ['-rating']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ClinicsDetailSerializer
        return ClinicsListSerializer

    def get_queryset(self):
        queryset = Clinics.objects.select_related(
            'city', 'district', 'region', 'country', 'microdistrict'
        )

        # Фильтр по городу (по имени)
        city_name = self.request.query_params.get('city_name')
        if city_name:
            queryset = queryset.filter(city__name_ru__icontains=city_name)

        # Фильтр по категории
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(categories__contains=[category])

        # Фильтр по рейтингу (минимальный)
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(rating__gte=float(min_rating))

        # Сортировка по расстоянию от пользователя
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        if lat and lng:
            try:
                user_location = Point(float(lng), float(lat), srid=4326)
                # Максимальный радиус поиска - 50 км (можно изменить через параметр)
                max_radius_km = float(self.request.query_params.get('radius', 50))
                max_radius_m = max_radius_km * 1000

                queryset = queryset.filter(location__isnull=False).annotate(
                    distance=Distance('location', user_location)
                ).filter(
                    distance__lte=max_radius_m
                ).order_by('distance')
            except (ValueError, TypeError):
                pass  # Ignore invalid coordinates

        return queryset

    @action(detail=False, methods=['get'], url_path='cities')
    def cities_with_clinics(self, request):
        """Получить список городов, в которых есть клиники"""
        cities = City.objects.filter(
            clinics__isnull=False,
            is_deleted=False
        ).distinct().order_by('name_ru')

        serializer = CitySerializer(cities, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='categories')
    def categories(self, request):
        """Получить все уникальные категории клиник"""
        clinics = Clinics.objects.exclude(categories__isnull=True)

        all_categories = set()
        for clinic in clinics:
            if clinic.categories:
                if isinstance(clinic.categories, list):
                    all_categories.update(clinic.categories)
                elif isinstance(clinic.categories, dict):
                    all_categories.update(clinic.categories.keys())

        return Response(sorted(list(all_categories)))

    @action(detail=False, methods=['get'], url_path='search')
    def search_clinics(self, request):
        """Поиск клиник по названию, адресу или категории"""
        query = request.query_params.get('q', '')

        if not query:
            return Response([])

        clinics = Clinics.objects.filter(
            Q(name__icontains=query) |
            Q(address__icontains=query) |
            Q(description__icontains=query)
        ).select_related('city', 'district')[:20]

        serializer = ClinicsListSerializer(clinics, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='ai-search')
    def ai_search(self, request):
        """
        AI-поиск клиник по естественному языку.
        Принимает текстовый запрос и возвращает подходящие клиники с объяснением.
        """
        query = request.data.get('query', '').strip()
        city_name = request.data.get('city_name', '')
        lat = request.data.get('lat')
        lng = request.data.get('lng')

        if not query:
            return Response(
                {'error': 'Пожалуйста, опишите что вы ищете'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Получаем все уникальные категории клиник
        all_categories = set()
        for clinic in Clinics.objects.exclude(categories__isnull=True):
            if clinic.categories and isinstance(clinic.categories, list):
                all_categories.update(clinic.categories)

        categories_list = sorted(list(all_categories))

        # Формируем промпт для AI
        system_prompt = f"""Ты - умный помощник для поиска медицинских клиник в Казахстане.

Доступные категории клиник: {', '.join(categories_list[:50])}

Проанализируй запрос пользователя и определи:
1. Какие категории клиник ему подойдут (из списка выше)
2. Ключевые слова для поиска по названию/описанию
3. Краткое объяснение почему эти клиники подходят

Ответь ТОЛЬКО в формате JSON:
{{
    "categories": ["категория1", "категория2"],
    "keywords": ["ключевое слово1", "ключевое слово2"],
    "explanation": "Краткое объяснение на русском языке почему рекомендуются эти клиники",
    "min_rating": null или число от 1 до 5 если пользователь хочет хорошие клиники
}}

Не добавляй никакого текста кроме JSON."""

        user_prompt = f"Запрос пользователя: {query}"

        try:
            # Вызов Mistral AI API
            headers = {
                "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "open-mistral-nemo",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }

            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Mistral API error: {response.status_code} - {response.text}")
                return Response(
                    {'error': 'Ошибка AI сервиса', 'details': response.text},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            ai_response = response.json()
            ai_content = ai_response['choices'][0]['message']['content']

            # Парсим JSON из ответа AI
            # Убираем возможные markdown-обёртки
            ai_content = ai_content.strip()
            if ai_content.startswith('```json'):
                ai_content = ai_content[7:]
            if ai_content.startswith('```'):
                ai_content = ai_content[3:]
            if ai_content.endswith('```'):
                ai_content = ai_content[:-3]
            ai_content = ai_content.strip()

            try:
                ai_data = json.loads(ai_content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response: {ai_content}")
                ai_data = {
                    "categories": [],
                    "keywords": [query],
                    "explanation": "Ищем клиники по вашему запросу",
                    "min_rating": None
                }

            # Строим запрос к БД
            queryset = Clinics.objects.select_related(
                'city', 'district', 'region', 'country'
            )

            # Фильтр по городу
            if city_name:
                queryset = queryset.filter(city__name_ru__icontains=city_name)

            # Фильтр по категориям
            categories = ai_data.get('categories', [])
            keywords = ai_data.get('keywords', [])
            min_rating = ai_data.get('min_rating')

            q_filter = Q()

            # Поиск по категориям
            for cat in categories:
                q_filter |= Q(categories__contains=[cat])

            # Поиск по ключевым словам
            for keyword in keywords:
                q_filter |= Q(name__icontains=keyword)
                q_filter |= Q(description__icontains=keyword)
                q_filter |= Q(address__icontains=keyword)

            if q_filter:
                queryset = queryset.filter(q_filter)

            # Фильтр по рейтингу
            if min_rating:
                queryset = queryset.filter(rating__gte=float(min_rating))

            # Сортировка по расстоянию если есть координаты
            if lat and lng:
                try:
                    user_location = Point(float(lng), float(lat), srid=4326)
                    queryset = queryset.filter(location__isnull=False).annotate(
                        distance=Distance('location', user_location)
                    ).order_by('distance')
                except (ValueError, TypeError):
                    queryset = queryset.order_by('-rating')
            else:
                queryset = queryset.order_by('-rating')

            # Лимит результатов
            clinics = queryset.distinct()[:12]

            serializer = ClinicsListSerializer(clinics, many=True)

            return Response({
                'success': True,
                'explanation': ai_data.get('explanation', ''),
                'matched_categories': categories,
                'keywords': keywords,
                'clinics': serializer.data,
                'total_found': len(serializer.data)
            })

        except requests.Timeout:
            return Response(
                {'error': 'Превышено время ожидания AI сервиса'},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except Exception as e:
            logger.exception("AI search error")
            return Response(
                {'error': 'Произошла ошибка при обработке запроса', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    """API для получения списка стран"""
    queryset = Country.objects.filter(is_deleted=False)
    serializer_class = CountrySerializer
    permission_classes = [AllowAny]


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    """API для получения списка регионов"""
    queryset = Region.objects.filter(is_deleted=False).select_related('country')
    serializer_class = RegionSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['country']


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    """API для получения списка городов"""
    queryset = City.objects.filter(is_deleted=False).select_related('region', 'region__country')
    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    filterset_fields = ['region']


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    """API для получения списка районов"""
    queryset = District.objects.filter(is_deleted=False).select_related('city')
    serializer_class = DistrictSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['city']
