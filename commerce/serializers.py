"""API input/output shapes for `commerce`."""

from rest_framework import serializers

from .models import EntitlementAccount, EntitlementEntry, Payment, Receipt


class PaymentCreateSerializer(serializers.Serializer):
    student = serializers.IntegerField(required=False)
    course = serializers.IntegerField(required=False, allow_null=True)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    method = serializers.CharField(required=False, default="online")
    purpose = serializers.CharField(required=False, allow_blank=True, default="")
    credits_purchased = serializers.IntegerField(required=False, allow_null=True)
    provider_reference = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class ManualPaymentSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    course = serializers.IntegerField(required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    method = serializers.CharField(required=False, default="cash")
    purpose = serializers.CharField(required=False, allow_blank=True, default="")
    credits_purchased = serializers.IntegerField(required=False, allow_null=True)
    provider_reference = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class PaymentSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    method_label = serializers.CharField(source="get_method_display", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    course_name = serializers.CharField(
        source="course.name", read_only=True, allow_null=True
    )
    receipt_number = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id",
            "student",
            "student_name",
            "course",
            "course_name",
            "amount",
            "currency",
            "method",
            "method_label",
            "status",
            "status_label",
            "credits_purchased",
            "provider_reference",
            "purpose",
            "exception_note",
            "failure_reason",
            "succeeded_at",
            "entitlement_granted",
            "receipt_number",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_receipt_number(self, obj: Payment) -> str | None:
        try:
            return obj.receipt.receipt_number
        except Receipt.DoesNotExist:
            return None


class ReceiptSerializer(serializers.ModelSerializer):
    payment_id = serializers.IntegerField(source="payment.id", read_only=True)
    amount = serializers.DecimalField(
        source="payment.amount", max_digits=12, decimal_places=2, read_only=True
    )
    currency = serializers.CharField(source="payment.currency", read_only=True)
    student_name = serializers.CharField(
        source="payment.student.full_name", read_only=True
    )

    class Meta:
        model = Receipt
        fields = (
            "id",
            "receipt_number",
            "payment_id",
            "amount",
            "currency",
            "student_name",
            "issued_at",
            "notes",
        )
        read_only_fields = fields


class EntitlementEntrySerializer(serializers.ModelSerializer):
    entry_type_label = serializers.CharField(
        source="get_entry_type_display", read_only=True
    )

    class Meta:
        model = EntitlementEntry
        fields = (
            "id",
            "entry_type",
            "entry_type_label",
            "credits",
            "payment",
            "booking_reference",
            "note",
            "created_at",
        )
        read_only_fields = fields


class EntitlementAccountSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    course_name = serializers.CharField(
        source="course.name", read_only=True, allow_null=True
    )
    is_low_balance = serializers.BooleanField(read_only=True)
    entries = EntitlementEntrySerializer(many=True, read_only=True)

    class Meta:
        model = EntitlementAccount
        fields = (
            "id",
            "student",
            "student_name",
            "course",
            "course_name",
            "balance_credits",
            "low_balance_threshold",
            "is_low_balance",
            "is_active",
            "entries",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class EntitlementAdjustSerializer(serializers.Serializer):
    credits = serializers.IntegerField(min_value=1)
    direction = serializers.ChoiceField(choices=["credit", "debit"])
    note = serializers.CharField()


class WebhookSerializer(serializers.Serializer):
    provider_reference = serializers.CharField()
    event = serializers.ChoiceField(choices=["succeeded", "failed"])
    payment_id = serializers.IntegerField(required=False, allow_null=True)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )


class ExceptionSerializer(serializers.Serializer):
    note = serializers.CharField()
