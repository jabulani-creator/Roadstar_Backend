"""
URL routes for `commerce`.

Portal:
- GET/POST /api/v1/payments/me/
- GET /api/v1/receipts/me/
- GET /api/v1/entitlements/me/
- GET /api/v1/payments/{id}/
- POST /api/v1/payments/{id}/confirm/
- POST /api/v1/payments/{id}/fail/

Provider:
- POST /api/v1/payments/webhook/

Staff:
- GET /api/v1/staff/payments/
- POST /api/v1/staff/payments/manual/
- POST /api/v1/staff/payments/{id}/exception/
- GET /api/v1/staff/entitlements/
- POST /api/v1/staff/entitlements/{id}/adjust/
"""

from django.urls import path

from .viewsets import (
    PaymentConfirmView,
    PaymentDetailView,
    PaymentFailView,
    PaymentWebhookView,
    PortalEntitlementListView,
    PortalPaymentListCreateView,
    PortalReceiptListView,
    StaffEntitlementAdjustView,
    StaffEntitlementListView,
    StaffManualPaymentView,
    StaffPaymentExceptionView,
    StaffPaymentListView,
)

urlpatterns = [
    path("payments/me/", PortalPaymentListCreateView.as_view(), name="portal-payment-list"),
    path("receipts/me/", PortalReceiptListView.as_view(), name="portal-receipt-list"),
    path(
        "entitlements/me/",
        PortalEntitlementListView.as_view(),
        name="portal-entitlement-list",
    ),
    path("payments/webhook/", PaymentWebhookView.as_view(), name="payment-webhook"),
    path(
        "payments/<int:payment_id>/",
        PaymentDetailView.as_view(),
        name="payment-detail",
    ),
    path(
        "payments/<int:payment_id>/confirm/",
        PaymentConfirmView.as_view(),
        name="payment-confirm",
    ),
    path(
        "payments/<int:payment_id>/fail/",
        PaymentFailView.as_view(),
        name="payment-fail",
    ),
    path("staff/payments/", StaffPaymentListView.as_view(), name="staff-payment-list"),
    path(
        "staff/payments/manual/",
        StaffManualPaymentView.as_view(),
        name="staff-payment-manual",
    ),
    path(
        "staff/payments/<int:payment_id>/exception/",
        StaffPaymentExceptionView.as_view(),
        name="staff-payment-exception",
    ),
    path(
        "staff/entitlements/",
        StaffEntitlementListView.as_view(),
        name="staff-entitlement-list",
    ),
    path(
        "staff/entitlements/<int:account_id>/adjust/",
        StaffEntitlementAdjustView.as_view(),
        name="staff-entitlement-adjust",
    ),
]
