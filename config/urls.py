"""
Root URL map for Roadstar.

Plain English:
- Incoming web addresses land here first.
- We keep the public API under /api/v1/ so the frontend has one stable base path.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as static_serve
from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    project = serializers.CharField()
    api = serializers.CharField()


@extend_schema(responses=HealthSerializer, tags=["meta"])
@api_view(["GET"])
@permission_classes([AllowAny])
def health(_request):
    """Tiny public check that the API process is running."""
    return Response(
        {
            "status": "ok",
            "project": "Roadstar Driving School Zambia",
            "api": "v1",
        }
    )


@extend_schema_view(
    post=extend_schema(
        tags=["auth"],
        summary="Login — obtain JWT access + refresh tokens",
        description="Body uses **email** and **password** (not username).",
    )
)
class EmailTokenObtainPairView(TokenObtainPairView):
    pass


@extend_schema_view(
    post=extend_schema(tags=["auth"], summary="Refresh JWT access token")
)
class EmailTokenRefreshView(TokenRefreshView):
    pass


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="api-health"),
    # Auth token endpoints (login/refresh). Login body uses email + password.
    path(
        "api/v1/auth/token/",
        EmailTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/v1/auth/token/refresh/",
        EmailTokenRefreshView.as_view(),
        name="token_refresh",
    ),
    # Domain apps register routes under /api/v1/.
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("catalogue.urls")),
    path("api/v1/", include("content.urls")),
    path("api/v1/", include("leads.urls")),
    path("api/v1/", include("students.urls")),
    path("api/v1/", include("commerce.urls")),
    path("api/v1/", include("fleet.urls")),
    path("api/v1/", include("scheduler.urls")),
    path("api/v1/", include("learning.urls")),
]

# Swagger / ReDoc only while DEBUG is on.
if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "api/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
        path(
            "api/v1/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui-v1",
        ),
        path(
            "api/v1/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc-v1",
        ),
        path(
            "api/v1/schema/",
            SpectacularAPIView.as_view(),
            name="schema-v1",
        ),
    ]

# Serve media + static even when DEBUG is False (Nginx proxies these to Django).
# django.conf.urls.static.static() is a no-op when DEBUG is False.
urlpatterns += [
    re_path(
        r"^media/(?P<path>.*)$",
        static_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
    re_path(
        r"^static/(?P<path>.*)$",
        static_serve,
        {"document_root": settings.STATIC_ROOT},
    ),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
