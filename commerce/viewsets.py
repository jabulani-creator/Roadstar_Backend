"""
HTTP endpoints for `commerce`.

Portal balance/receipts + staff finance + webhook. Rules live in services.py.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from config.api import RoadstarAPIView

from students.models import Student
from students.selectors import student_for_user

from .models import Payment
from .permissions import IsCommerceStaff, IsFinanceStaff
from .selectors import (
    entitlement_by_id,
    entitlements_for_student,
    entitlements_staff,
    payment_by_id,
    payments_for_student,
    payments_staff,
    receipts_for_student,
)
from .serializers import (
    EntitlementAccountSerializer,
    EntitlementAdjustSerializer,
    ExceptionSerializer,
    ManualPaymentSerializer,
    PaymentCreateSerializer,
    PaymentSerializer,
    ReceiptSerializer,
    WebhookSerializer,
)
from .services import (
    CommerceServiceError,
    adjust_entitlement,
    create_payment_intent,
    handle_provider_webhook,
    mark_payment_exception,
    mark_payment_failed,
    mark_payment_succeeded,
    record_manual_payment,
)


def _service_error(exc: CommerceServiceError) -> Response:
    http_status = (
        status.HTTP_403_FORBIDDEN
        if exc.code == "forbidden"
        else status.HTTP_400_BAD_REQUEST
    )
    return Response({"detail": exc.message, "code": exc.code}, status=http_status)


def _require_student(user) -> Student | None:
    return student_for_user(user=user)


# --- Portal ---


class PortalPaymentListCreateView(RoadstarAPIView):
    """GET/POST /api/v1/payments/me/"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        student = _require_student(request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            PaymentSerializer(payments_for_student(student=student), many=True).data
        )

    def post(self, request: Request) -> Response:
        student = _require_student(request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            payment = create_payment_intent(
                student=student,
                course_id=data.get("course") or student.selected_course_id,
                amount=data.get("amount"),
                method=data.get("method") or "online",
                purpose=data.get("purpose") or "",
                credits_purchased=data.get("credits_purchased"),
                provider_reference=data.get("provider_reference") or "",
                actor=request.user,
            )
        except CommerceServiceError as exc:
            return _service_error(exc)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PortalReceiptListView(RoadstarAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        student = _require_student(request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            ReceiptSerializer(receipts_for_student(student=student), many=True).data
        )


class PortalEntitlementListView(RoadstarAPIView):
    """GET /api/v1/entitlements/me/"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        student = _require_student(request.user)
        if student is None:
            return Response(
                {"detail": "No student profile linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            EntitlementAccountSerializer(
                entitlements_for_student(student=student), many=True
            ).data
        )


class PaymentDetailView(RoadstarAPIView):
    """GET /api/v1/payments/{id}/ — own payment or staff."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, payment_id: int) -> Response:
        payment = payment_by_id(payment_id=payment_id)
        if payment is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        student = _require_student(request.user)
        is_owner = student is not None and payment.student_id == student.id
        is_staff = IsCommerceStaff().has_permission(request, self)
        if not is_owner and not is_staff:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentSerializer(payment).data)


class PaymentConfirmView(RoadstarAPIView):
    """
    POST /api/v1/payments/{id}/confirm/

    Dev/self-serve success path (and staff confirm). Real providers should use webhook.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, payment_id: int) -> Response:
        payment = payment_by_id(payment_id=payment_id)
        if payment is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        student = _require_student(request.user)
        is_owner = student is not None and payment.student_id == student.id
        is_staff = IsFinanceStaff().has_permission(request, self)
        if not is_owner and not is_staff:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            payment = mark_payment_succeeded(
                payment_id=payment.id,
                actor=request.user,
                provider_reference=request.data.get("provider_reference") or "",
            )
        except CommerceServiceError as exc:
            return _service_error(exc)
        except Payment.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentSerializer(payment).data)


class PaymentFailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, payment_id: int) -> Response:
        payment = payment_by_id(payment_id=payment_id)
        if payment is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        student = _require_student(request.user)
        is_owner = student is not None and payment.student_id == student.id
        is_staff = IsFinanceStaff().has_permission(request, self)
        if not is_owner and not is_staff:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            payment = mark_payment_failed(
                payment_id=payment.id,
                reason=request.data.get("reason") or "",
                actor=request.user,
            )
        except CommerceServiceError as exc:
            return _service_error(exc)
        return Response(PaymentSerializer(payment).data)


class PaymentWebhookView(RoadstarAPIView):
    """POST /api/v1/payments/webhook/ — provider callback (mock-friendly)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        serializer = WebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            payment = handle_provider_webhook(
                provider_reference=data["provider_reference"],
                event=data["event"],
                payment_id=data.get("payment_id"),
                amount=data.get("amount"),
            )
        except CommerceServiceError as exc:
            return _service_error(exc)
        return Response(PaymentSerializer(payment).data)


# --- Staff ---


class StaffPaymentListView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsCommerceStaff]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status") or None
        student = request.query_params.get("student")
        student_id = int(student) if student and student.isdigit() else None
        qs = payments_staff(status=status_filter, student_id=student_id)
        return Response(PaymentSerializer(qs, many=True).data)


class StaffManualPaymentView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsFinanceStaff]

    def post(self, request: Request) -> Response:
        serializer = ManualPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            payment = record_manual_payment(
                actor=request.user,
                student_id=data["student"],
                course_id=data.get("course"),
                amount=data["amount"],
                method=data.get("method") or "cash",
                credits_purchased=data.get("credits_purchased"),
                provider_reference=data.get("provider_reference") or "",
                purpose=data.get("purpose") or "",
            )
        except CommerceServiceError as exc:
            return _service_error(exc)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class StaffPaymentExceptionView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsFinanceStaff]

    def post(self, request: Request, payment_id: int) -> Response:
        body = ExceptionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            payment = mark_payment_exception(
                actor=request.user,
                payment_id=payment_id,
                note=body.validated_data["note"],
            )
        except CommerceServiceError as exc:
            return _service_error(exc)
        except Payment.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentSerializer(payment).data)


class StaffEntitlementListView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsCommerceStaff]

    def get(self, request: Request) -> Response:
        student = request.query_params.get("student")
        student_id = int(student) if student and student.isdigit() else None
        low = request.query_params.get("low_balance") in {"1", "true", "yes"}
        qs = entitlements_staff(student_id=student_id, low_balance_only=low)
        return Response(EntitlementAccountSerializer(qs, many=True).data)


class StaffEntitlementAdjustView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsFinanceStaff]

    def post(self, request: Request, account_id: int) -> Response:
        account = entitlement_by_id(account_id=account_id)
        if account is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = EntitlementAdjustSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        try:
            adjust_entitlement(
                actor=request.user,
                account_id=account.id,
                credits=data["credits"],
                direction=data["direction"],
                note=data["note"],
            )
        except CommerceServiceError as exc:
            return _service_error(exc)
        account = entitlement_by_id(account_id=account_id)
        return Response(EntitlementAccountSerializer(account).data)
