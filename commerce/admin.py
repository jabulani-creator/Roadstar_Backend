"""Django admin for commerce records."""

from django.contrib import admin

from .models import EntitlementAccount, EntitlementEntry, Payment, Receipt


class ReceiptInline(admin.StackedInline):
    model = Receipt
    extra = 0
    readonly_fields = ("receipt_number", "issued_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "amount",
        "currency",
        "method",
        "status",
        "credits_purchased",
        "entitlement_granted",
        "created_at",
    )
    list_filter = ("status", "method", "entitlement_granted")
    search_fields = (
        "provider_reference",
        "purpose",
        "student__full_name",
        "student__email",
    )
    raw_id_fields = ("student", "course", "recorded_by")
    readonly_fields = ("created_at", "updated_at", "succeeded_at", "entitlement_granted")
    inlines = [ReceiptInline]


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "payment", "issued_at", "issued_by")
    search_fields = ("receipt_number", "payment__student__email")
    raw_id_fields = ("payment", "issued_by")
    readonly_fields = ("receipt_number", "issued_at")


class EntitlementEntryInline(admin.TabularInline):
    model = EntitlementEntry
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(EntitlementAccount)
class EntitlementAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "course",
        "balance_credits",
        "low_balance_threshold",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("student__full_name", "student__email")
    raw_id_fields = ("student", "course")
    inlines = [EntitlementEntryInline]


@admin.register(EntitlementEntry)
class EntitlementEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "account",
        "entry_type",
        "credits",
        "payment",
        "created_by",
        "created_at",
    )
    list_filter = ("entry_type",)
    search_fields = ("note", "booking_reference", "account__student__email")
    raw_id_fields = ("account", "payment", "created_by")
    readonly_fields = ("created_at",)
