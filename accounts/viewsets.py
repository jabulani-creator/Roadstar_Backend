"""
HTTP endpoints for `accounts`.

Plain English:
- Receive the request.
- Call selectors for reads and services for writes.
- Return JSON via serializers.
- Keep this file thin — no heavy business rules.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from config.api import RoadstarAPIView

from .selectors import get_current_user, get_public_staff_queryset
from .serializers import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PublicStaffSerializer,
    UserMeSerializer,
)
from .services import (
    AccountsServiceError,
    change_password,
    confirm_password_reset,
    request_password_reset,
)


class MeView(RoadstarAPIView):
    """
    GET /api/v1/auth/me/

    Returns the logged-in user's profile and role badges.
    Requires a valid access token.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserMeSerializer

    def get(self, request: Request) -> Response:
        user = get_current_user(request.user)
        data = UserMeSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)


class ChangePasswordView(RoadstarAPIView):
    """
    POST /api/v1/auth/change-password/

    Body: current_password, new_password
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            change_password(
                user=request.user,
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["new_password"],
            )
        except AccountsServiceError as exc:
            return Response(
                {"detail": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"detail": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(RoadstarAPIView):
    """
    POST /api/v1/auth/password-reset/

    Body: email
    Always returns the same success message (does not reveal account existence).
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(email=serializer.validated_data["email"])
        return Response(
            {
                "detail": (
                    "If an account exists for that email, "
                    "password reset instructions have been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(RoadstarAPIView):
    """
    POST /api/v1/auth/password-reset/confirm/

    Body: uid, token, new_password
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_password_reset(
                uid=serializer.validated_data["uid"],
                token=serializer.validated_data["token"],
                new_password=serializer.validated_data["new_password"],
            )
        except AccountsServiceError as exc:
            return Response(
                {"detail": exc.message, "code": exc.code},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"detail": "Password has been reset. You can log in now."},
            status=status.HTTP_200_OK,
        )


class PublicStaffListView(RoadstarAPIView):
    """
    GET /api/v1/auth/staff/

    Public list of staff/instructors opted into trust pages.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        staff = get_public_staff_queryset()
        data = PublicStaffSerializer(staff, many=True).data
        return Response(data, status=status.HTTP_200_OK)
