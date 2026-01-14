from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static
from common.swagger_permissions import SwaggerAccessPermission, swagger_basic_auth_required

# Configure Swagger schema with authentication
schema_view = get_schema_view(
    openapi.Info(
        title="ZhanCare API",
        default_version="v1",
        description="ZhanCare Medical Platform API Documentation",
        terms_of_service="https://www.zhan.care/terms/",
        contact=openapi.Contact(email="support@zhancare.ai"),
        license=openapi.License(name="BSD License"),
    ),
    public=False,  # ✅ Not public - requires authentication
    permission_classes=(SwaggerAccessPermission,),  # ✅ Custom permission class
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("common.urls")),
    path("api/v1/", include("consultations.urls")),
    path("api/v1/", include("appointments.urls")),
    path("api/v1/", include("ai_game.urls")),
    path("api/v1/", include("clinics.urls")),
    path("api/v1/", include("clinical_protocols.urls")),
    path('accounts/', include('django.contrib.auth.urls')),

    # Swagger/ReDoc endpoints with multiple auth methods
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        swagger_basic_auth_required(schema_view.without_ui(cache_timeout=0)),
        name="schema-json"
    ),
    path(
        "swagger/",
        swagger_basic_auth_required(schema_view.with_ui("swagger", cache_timeout=0)),
        name="schema-swagger-ui"
    ),
    path(
        "redoc/",
        swagger_basic_auth_required(schema_view.with_ui("redoc", cache_timeout=0)),
        name="schema-redoc"
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
