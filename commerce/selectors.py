"""Read queries for commerce — portal sees own; staff see finance views."""

from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from students.models import Student

from .models import EntitlementAccount, EntitlementEntry, Payment, Receipt


def payments_for_student(*, student: Student) -> QuerySet[Payment]:
    return (
        Payment.objects.select_related("student", "course", "receipt")
        .filter(student=student)
        .order_by("-created_at")
    )


def payments_staff(
    *,
    status: str | None = None,
    student_id: int | None = None,
) -> QuerySet[Payment]:
    qs = Payment.objects.select_related("student", "course", "receipt").all()
    if status:
        qs = qs.filter(status=status)
    if student_id is not None:
        qs = qs.filter(student_id=student_id)
    return qs.order_by("-created_at")


def payment_by_id(*, payment_id: int) -> Payment | None:
    return (
        Payment.objects.select_related("student", "course", "receipt")
        .filter(pk=payment_id)
        .first()
    )


def receipts_for_student(*, student: Student) -> QuerySet[Receipt]:
    return (
        Receipt.objects.select_related("payment", "payment__student", "payment__course")
        .filter(payment__student=student)
        .order_by("-issued_at")
    )


def entitlements_for_student(*, student: Student) -> QuerySet[EntitlementAccount]:
    return (
        EntitlementAccount.objects.select_related("student", "course")
        .prefetch_related(
            Prefetch(
                "entries",
                queryset=EntitlementEntry.objects.order_by("-created_at"),
            )
        )
        .filter(student=student, is_active=True)
        .order_by("-updated_at")
    )


def entitlements_staff(
    *,
    student_id: int | None = None,
    low_balance_only: bool = False,
) -> QuerySet[EntitlementAccount]:
    qs = (
        EntitlementAccount.objects.select_related("student", "course")
        .prefetch_related("entries")
        .all()
    )
    if student_id is not None:
        qs = qs.filter(student_id=student_id)
    if low_balance_only:
        # Evaluated in Python for simplicity; fine at Phase 1 scale.
        ids = [a.id for a in qs if a.is_low_balance]
        qs = qs.filter(id__in=ids)
    return qs.order_by("-updated_at")


def entitlement_by_id(*, account_id: int) -> EntitlementAccount | None:
    return (
        EntitlementAccount.objects.select_related("student", "course")
        .prefetch_related("entries")
        .filter(pk=account_id)
        .first()
    )
