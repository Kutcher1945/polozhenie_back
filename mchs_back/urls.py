from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger schema view configuration
# Swagger схема для API
schema_view = get_schema_view(
    openapi.Info(
        title="API",
        default_version='v1',
        # description="""
        # Этот API предоставляет доступ к различным сервисам и данным, связанным с управлением чрезвычайными ситуациями и бедствиями.
        # Включает в себя эндпоинты для аутентификации пользователей, управления модулями, а также доступа к данным категорий, 
        # связанных с чрезвычайными ситуациями и общественной безопасностью.

        # Основные функции API:
        # - Аутентификация пользователей и управление JWT-токенами.
        # - Управление модулями, включая список категорий и подкатегорий.
        # - Поддержка фильтрации данных и сортировки.
        # - Безопасный доступ с использованием ролевых разрешений.
        # - Полная документация эндпоинтов с поддержкой OpenAPI для лёгкой интеграции.

        # Для дополнительной информации, пожалуйста, свяжитесь с поддержкой: adilan.akhramovich@gmail.com
        # """,
        description=""" API desc """,
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="adilan.akhramovich@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


# Main URL patterns
urlpatterns = [
    # Admin routes
    path('admin/', admin.site.urls),

    # Authentication routes (from the 'common' app)
    path('api/auth/', include('common.urls')),  

    # Modules routes (from the 'modules' app)
    path('api/', include('modules.urls')),

    #Card101 routes (from the 'card101' app)
    path('api/', include('card101.urls')),

    #Address routes (from the 'address' app)
    path('api/', include('address.urls')),

    # Swagger API documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    
    # Raw schema JSON for OpenAPI
    path('schema/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
