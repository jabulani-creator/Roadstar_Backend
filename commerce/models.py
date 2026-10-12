"""
Durable data for the `commerce` domain.

Owns: payments, receipts, lesson-credit entitlement ledger.

Plain English:
- Payment = money in (online intent or staff cash/manual).
- Receipt = proof issued only after success.
- EntitlementAccount = remaining lesson credits for a learner + course.
- EntitlementEntry = each grant / deduct / adjust (audit trail).

Critical rule: a successful payment creates entitlement exactly once.
Failed payments never create credits.

Does NOT own: full accounting ERP, bank reconciliation, payroll, bookings.
"""

from django.conf import settings
from django.db import models


class PaymentMethod(models.TextChoices):
    ONLINE = "online", "Online (provider)"
    MOBILE_MONEY = "mobile_money", "Mobile money"
    BANK_TRANSFER = "bank_transfer", "Bank transfer"
    CASH = "cash", "Cash (staff-recorded)"
    OTHER = "other", "Other"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    EXCEPTION = "exception", "Needs staff review"


class Payment(models.Model):
    """
    A payment attempt or staff-recorded payment for a learner package.
    """

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="payments",
    )
    course = models.ForeignKey(
        "catalogue.Course",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="ZMW")
    method = models.CharField(
        max_length=32,
        choices=PaymentMethod.choices,
        default=PaymentMethod.ONLINE,
    )
    status = models.CharField(
        max_length=32,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    credits_purchased = models.PositiveIntegerField(
        help_text="Lesson credits this payment should grant on success.",
    )
    provider_reference = models.CharField(
        max_length=120,
        blank=True,
        help_text="External provider / bank / MoMo reference. Used for idempotency.",
    )
    purpose = models.CharField(
        max_length=255,
        blank=True,
        help_text="Human label, e.g. Class B full package.",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_payments",
        help_text="Staff user when cash/manual; null for self-serve online.",
    )
    exception_note = models.TextField(blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    succeeded_at = models.DateTimeField(null=True, blank=True)
    entitlement_granted = models.BooleanField(
        default=False,
        help_text="True after the exactly-once grant has been written.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider_reference"],
                condition=~models.Q(provider_reference=""),
                name="commerce_unique_provider_reference",
            )
        ]

    def __str__(self) -> str:
        return f"Payment #{self.pk} {self.amount} {self.currency} ({self.status})"


class Receipt(models.Model):
    """
    Issued only for succeeded payments. One receipt per payment.
    """

    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name="receipt",
    )
    receipt_number = models.CharField(max_length=32, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issued_receipts",
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return self.receipt_number


class EntitlementAccount(models.Model):
    """
    Remaining lesson-credit balance for a learner on a course pathway.
    """

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="entitlement_accounts",
    )
    course = models.ForeignKey(
        "catalogue.Course",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="entitlement_accounts",
    )
    balance_credits = models.PositiveIntegerField(default=0)
    low_balance_threshold = models.PositiveIntegerField(
        default=2,
        help_text="Portal/staff can highlight when balance is at or below this.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="commerce_unique_student_course_entitlement",
            )
        ]

    def __str__(self) -> str:
        return f"{self.student_id} course={self.course_id} bal={self.balance_credits}"

    @property
    def is_low_balance(self) -> bool:
        return self.balance_credits <= self.low_balance_threshold


class EntitlementEntryType(models.TextChoices):
    GRANT = "grant", "Grant (purchase)"
    DEDUCT = "deduct", "Deduct (lesson / policy)"
    ADJUST = "adjust", "Staff adjustment"


class EntitlementEntry(models.Model):
    """
    Append-only ledger line. Grants tied to a payment are unique.
    """

    account = models.ForeignKey(
        EntitlementAccount,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    entry_type = models.CharField(max_length=16, choices=EntitlementEntryType.choices)
    # Signed amount: grant/adjust-up positive; deduct/adjust-down stored as positive with type.
    credits = models.PositiveIntegerField()
    payment = models.OneToOneField(
        Payment,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="entitlement_grant",
        help_text="Set only for purchase grants — enforces exactly-once.",
    )
    # Future scheduler booking id (no FK yet — avoid coupling before scheduler exists).
    booking_reference = models.CharField(max_length=64, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="entitlement_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "entitlement entries"

    def __str__(self) -> str:
        return f"{self.entry_type} {self.credits} on account {self.account_id}"
