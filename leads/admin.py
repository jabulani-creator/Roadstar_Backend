"""Django admin for lead inbox records."""

from django.contrib import admin

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "phone",
        "status",
        "channel",
        "referral_source",
        "preferred_branch",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "channel", "referral_source", "licence_class", "transmission")
    search_fields = ("full_name", "phone", "email", "message", "whatsapp_summary")
    raw_id_fields = (
        "preferred_branch",
        "interested_course",
        "recommended_course",
        "assigned_to",
    )
    readonly_fields = ("created_at", "updated_at", "converted_at")
