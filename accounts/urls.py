"""
URL routes for `accounts`.

Engineering design auth surface:
- GET  /api/v1/auth/me/
- GET  /api/v1/auth/staff/
- POST /api/v1/auth/change-password/
- POST /api/v1/auth/password-reset/
- POST /api/v1/auth/password-reset/confirm/
"""

from django.urls import path

from .viewsets import (
    ChangePasswordView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PublicStaffListView,
)

urlpatterns = [
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/staff/", PublicStaffListView.as_view(), name="auth-staff"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]
