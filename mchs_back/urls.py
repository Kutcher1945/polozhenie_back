from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required

schema_view = get_schema_view(
    openapi.Info(
        title="ExperimentalApp",
        default_version="v1",
        description="ExperimentalApp API",
        terms_of_service="https://www.zhan.care/terms/",
        contact=openapi.Contact(email="support@zhancare.ai"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("common.urls")),
    path("api/v1/", include("consultations.urls")),
    path("api/v1/", include("appointments.urls")),
    path('accounts/', include('django.contrib.auth.urls')),

    re_path(r"^swagger(?P<format>\.json|\.yaml)$", login_required(schema_view.without_ui(cache_timeout=0)), name="schema-json"),
    path("swagger/", login_required(schema_view.with_ui("swagger", cache_timeout=0)), name="schema-swagger-ui"),
    path("redoc/", login_required(schema_view.with_ui("redoc", cache_timeout=0)), name="schema-redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
