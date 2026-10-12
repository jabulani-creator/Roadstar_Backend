"""
Write workflows for `commerce`.

Plain English:
- Pending online payments wait for success/failure.
- Success → one receipt + one entitlement grant (never twice).
- Failure → no credits.
- Staff cash/manual payments go through the same success path.
- Adjustments need a staff actor and an audit note.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import StaffRole, User
from accounts.permissions import user_has_any_role, user_is_staff_operator
from catalogue.models import Course
from students.models import Student, StudentStatus

from .models import (
    EntitlementAccount,
    EntitlementEntry,
    EntitlementEntryType,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Receipt,
)


class CommerceServiceError(Exception):
    """Domain error with a safe API message."""

    def __init__(self, message: str, code: str = "error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _can_finance(user: User) -> bool:
    return user_is_staff_operator(user) and (
        user_has_any_role(
            user,
            [StaffRole.OWNER, StaffRole.FINANCE, StaffRole.RECEPTION],
        )
        or user.is_superuser
        or user.is_staff
    )


def _require_finance(actor: User) -> None:
    if not _can_finance(actor):
        raise CommerceServiceError(
            "Not allowed to manage payments/entitlements.",
            code="forbidden",
        )


def _default_credits_for_course(course: Course | None) -> int:
    if course is None:
        return 1
    if course.lesson_count:
        return int(course.lesson_count)
    return 1


def _next_receipt_number() -> str:
    # Simple sequential-looking number; good enough for Phase 1 local use.
    year = timezone.now().strftime("%Y")
    count = Receipt.objects.count() + 1
    return f"RS-{year}-{count:05d}"


def _get_or_create_account(*, student: Student, course: Course | None) -> EntitlementAccount:
    account, _ = EntitlementAccount.objects.get_or_create(
        student=student,
        course=course,
        defaults={"balance_credits": 0},
    )
    return account


@transaction.atomic
def _grant_entitlement_for_payment(*, payment: Payment, actor: User | None) -> EntitlementEntry:
    """
    Exactly-once grant. Caller must hold a locked Payment row.
    """
    if payment.status != PaymentStatus.SUCCEEDED:
        raise CommerceServiceError(
            "Only succeeded payments can grant entitlement.",
            code="invalid_status",
        )

    existing = EntitlementEntry.objects.filter(payment=payment).first()
    if existing is not None:
        payment.entitlement_granted = True
        payment.save(update_fields=["entitlement_granted", "updated_at"])
        return existing

    if payment.entitlement_granted:
        # Defensive: flag set but entry missing — do not double-grant blindly.
        raise CommerceServiceError(
            "Payment already marked granted but ledger entry is missing.",
            code="ledger_inconsistent",
        )

    account = _get_or_create_account(student=payment.student, course=payment.course)
    # Lock account row for balance update.
    account = EntitlementAccount.objects.select_for_update().get(pk=account.pk)

    entry = EntitlementEntry.objects.create(
        account=account,
        entry_type=EntitlementEntryType.GRANT,
        credits=payment.credits_purchased,
        payment=payment,
        note=payment.purpose or "Package purchase grant",
        created_by=actor,
    )
    EntitlementAccount.objects.filter(pk=account.pk).update(
        balance_credits=F("balance_credits") + payment.credits_purchased,
        updated_at=timezone.now(),
    )

    payment.entitlement_granted = True
    payment.save(update_fields=["entitlement_granted", "updated_at"])

    # Activate learner after first successful purchase if still registered.
    student = payment.student
    if student.status == StudentStatus.REGISTERED:
        student.status = StudentStatus.ACTIVE
        student.has_proof_of_payment = True
        student.save(update_fields=["status", "has_proof_of_payment", "updated_at"])

    return entry


@transaction.atomic
def _issue_receipt(*, payment: Payment, actor: User | None) -> Receipt:
    existing = Receipt.objects.filter(payment=payment).first()
    if existing is not None:
        return existing
    return Receipt.objects.create(
        payment=payment,
        receipt_number=_next_receipt_number(),
        issued_by=actor,
    )

def create_payment_intent(
    *,
    student: Student,
    course_id: int | None,
    amount: Decimal | None = None,
    method: str = PaymentMethod.ONLINE,
    purpose: str = "",
    credits_purchased: int | None = None,
    provider_reference: str = "",
    actor: User | None = None,
) -> Payment:
    """
    Create a pending payment (online) or prepare a record for later confirmation.
    """
    course = None
    if course_id is not None:
        course = Course.objects.filter(pk=course_id).first()
        if course is None:
            raise CommerceServiceError("Course not found.", code="course_not_found")

    if credits_purchased is None:
        credits_purchased = _default_credits_for_course(course)
    if credits_purchased < 1:
        raise CommerceServiceError(
            "Credits purchased must be at least 1.",
            code="invalid_credits",
        )

    if amount is None:
        if course is None or course.price_amount is None:
            raise CommerceServiceError(
                "Amount is required when the course has no published price.",
                code="amount_required",
            )
        amount = course.price_amount

    if amount <= 0:
        raise CommerceServiceError("Amount must be greater than zero.", code="invalid_amount")

    # Block duplicate pending/succeeded for same student+course while investigating.
    blocking = Payment.objects.filter(
        student=student,
        course=course,
        status__in=[PaymentStatus.PENDING, PaymentStatus.EXCEPTION],
    ).exists()
    if blocking:
        raise CommerceServiceError(
            "A pending or under-review payment already exists for this package.",
            code="payment_in_flight",
        )

    return Payment.objects.create(
        student=student,
        course=course,
        amount=amount,
        currency=(course.currency if course else "ZMW"),
        method=method,
        status=PaymentStatus.PENDING,
        credits_purchased=credits_purchased,
        provider_reference=provider_reference or "",
        purpose=purpose or (course.name if course else ""),
        recorded_by=actor,
    )


@transaction.atomic
def record_manual_payment(
    *,
    actor: User,
    student_id: int,
    course_id: int | None,
    amount: Decimal,
    method: str = PaymentMethod.CASH,
    credits_purchased: int | None = None,
    provider_reference: str = "",
    purpose: str = "",
) -> Payment:
    """Staff cash/manual payment — succeeds immediately through the same grant path."""
    _require_finance(actor)
    student = Student.objects.filter(pk=student_id).first()
    if student is None:
        raise CommerceServiceError("Student not found.", code="student_not_found")

    payment = create_payment_intent(
        student=student,
        course_id=course_id,
        amount=amount,
        method=method,
        purpose=purpose,
        credits_purchased=credits_purchased,
        provider_reference=provider_reference,
        actor=actor,
    )
    return mark_payment_succeeded(payment_id=payment.id, actor=actor)


@transaction.atomic
def mark_payment_succeeded(
    *,
    payment_id: int,
    actor: User | None = None,
    provider_reference: str = "",
) -> Payment:
    """
    Idempotent success handler.

    Safe to call twice (webhook retries, double-click): second call returns same result.
    """
    # Postgres rejects FOR UPDATE on the nullable side of an outer join
    # (Payment.course is null=True), so lock Payment only — no select_related here.
    payment = Payment.objects.select_for_update().get(pk=payment_id)

    if payment.status == PaymentStatus.SUCCEEDED:
        # Ensure receipt/grant exist (repair path) without double-granting.
        _issue_receipt(payment=payment, actor=actor)
        _grant_entitlement_for_payment(payment=payment, actor=actor)
        return payment

    if payment.status in {PaymentStatus.FAILED, PaymentStatus.CANCELLED}:
        raise CommerceServiceError(
            f"Cannot succeed a {payment.status} payment.",
            code="invalid_status",
        )

    if provider_reference:
        # Avoid colliding with another payment's unique reference.
        clash = (
            Payment.objects.filter(provider_reference=provider_reference)
            .exclude(pk=payment.pk)
            .exists()
        )
        if clash:
            raise CommerceServiceError(
                "Provider reference already used on another payment.",
                code="duplicate_provider_reference",
            )
        payment.provider_reference = provider_reference

    payment.status = PaymentStatus.SUCCEEDED
    payment.succeeded_at = timezone.now()
    payment.failure_reason = ""
    payment.save(
        update_fields=[
            "status",
            "succeeded_at",
            "failure_reason",
            "provider_reference",
            "updated_at",
        ]
    )

    _issue_receipt(payment=payment, actor=actor)
    _grant_entitlement_for_payment(payment=payment, actor=actor)
    return (
        Payment.objects.select_related("student", "course", "receipt")
        .prefetch_related("entitlement_grant")
        .get(pk=payment.pk)
    )


@transaction.atomic
def mark_payment_failed(
    *,
    payment_id: int,
    reason: str = "",
    actor: User | None = None,
) -> Payment:
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    if payment.status == PaymentStatus.SUCCEEDED:
        raise CommerceServiceError(
            "Cannot fail a succeeded payment. Use exception review if needed.",
            code="invalid_status",
        )
    if payment.status == PaymentStatus.FAILED:
        return payment

    payment.status = PaymentStatus.FAILED
    payment.failure_reason = (reason or "")[:255]
    payment.save(update_fields=["status", "failure_reason", "updated_at"])
    # Explicitly do not create receipt or entitlement.
    _ = actor
    return payment


def _set_payment_exception(*, payment_id: int, note: str) -> Payment:
    if not (note or "").strip():
        raise CommerceServiceError(
            "An exception note is required.",
            code="note_required",
        )
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    if payment.status == PaymentStatus.SUCCEEDED and payment.entitlement_granted:
        raise CommerceServiceError(
            "Succeeded and granted payments are not moved to exception; use adjust if needed.",
            code="invalid_status",
        )
    payment.status = PaymentStatus.EXCEPTION
    payment.exception_note = note.strip()
    payment.save(update_fields=["status", "exception_note", "updated_at"])
    return payment


@transaction.atomic
def mark_payment_exception(
    *,
    actor: User,
    payment_id: int,
    note: str,
) -> Payment:
    _require_finance(actor)
    return _set_payment_exception(payment_id=payment_id, note=note)


@transaction.atomic
def handle_provider_webhook(
    *,
    provider_reference: str,
    event: str,
    payment_id: int | None = None,
    amount: Decimal | None = None,
) -> Payment:
    """
    Mock/provider webhook entrypoint.

    event: succeeded | failed
    Idempotent on provider_reference + payment status.
    """
    if not provider_reference:
        raise CommerceServiceError(
            "provider_reference is required.",
            code="provider_reference_required",
        )

    payment = None
    if payment_id is not None:
        payment = Payment.objects.filter(pk=payment_id).first()
    if payment is None:
        payment = Payment.objects.filter(provider_reference=provider_reference).first()
    if payment is None:
        # Allow first webhook to attach reference via payment_id only.
        raise CommerceServiceError("Payment not found for webhook.", code="payment_not_found")

    if amount is not None and payment.amount != amount:
        # Mismatch → exception, no entitlement.
        return _set_payment_exception(
            payment_id=payment.id,
            note=f"Webhook amount mismatch: expected {payment.amount}, got {amount}",
        )

    if event == "succeeded":
        return mark_payment_succeeded(
            payment_id=payment.id,
            provider_reference=provider_reference,
        )
    if event == "failed":
        return mark_payment_failed(payment_id=payment.id, reason="Provider reported failure")
    raise CommerceServiceError("Unknown webhook event.", code="invalid_event")


@transaction.atomic
def adjust_entitlement(
    *,
    actor: User,
    account_id: int,
    credits: int,
    direction: str,
    note: str,
) -> EntitlementEntry:
    """
    Staff adjustment. direction: credit | debit
    """
    _require_finance(actor)
    if not (note or "").strip():
        raise CommerceServiceError(
            "An audit note is required for entitlement adjustments.",
            code="note_required",
        )
    if credits < 1:
        raise CommerceServiceError("Credits must be at least 1.", code="invalid_credits")
    if direction not in {"credit", "debit"}:
        raise CommerceServiceError(
            "direction must be 'credit' or 'debit'.",
            code="invalid_direction",
        )

    account = EntitlementAccount.objects.select_for_update().get(pk=account_id)
    if direction == "debit" and account.balance_credits < credits:
        raise CommerceServiceError(
            "Insufficient balance for this debit adjustment.",
            code="insufficient_balance",
        )

    if direction == "credit":
        EntitlementAccount.objects.filter(pk=account.pk).update(
            balance_credits=F("balance_credits") + credits,
            updated_at=timezone.now(),
        )
    else:
        EntitlementAccount.objects.filter(pk=account.pk).update(
            balance_credits=F("balance_credits") - credits,
            updated_at=timezone.now(),
        )

    return EntitlementEntry.objects.create(
        account=account,
        entry_type=EntitlementEntryType.ADJUST,
        credits=credits,
        note=f"{direction}: {note.strip()}",
        created_by=actor,
    )


@transaction.atomic
def deduct_entitlement(
    *,
    account_id: int,
    credits: int = 1,
    booking_reference: str = "",
    note: str = "",
    actor: User | None = None,
) -> EntitlementEntry:
    """
    Used later by scheduler lesson completion. Exported now so the rule lives in commerce.
    """
    if credits < 1:
        raise CommerceServiceError("Credits must be at least 1.", code="invalid_credits")

    account = EntitlementAccount.objects.select_for_update().get(pk=account_id)
    if account.balance_credits < credits:
        raise CommerceServiceError(
            "Insufficient entitlement credits.",
            code="insufficient_balance",
        )

    EntitlementAccount.objects.filter(pk=account.pk).update(
        balance_credits=F("balance_credits") - credits,
        updated_at=timezone.now(),
    )
    return EntitlementEntry.objects.create(
        account=account,
        entry_type=EntitlementEntryType.DEDUCT,
        credits=credits,
        booking_reference=booking_reference,
        note=note or "Lesson credit deduction",
        created_by=actor,
    )
