"""Django admin for scheduler bookings and completions."""

from django.contrib import admin

from .models import LessonBooking, LessonCompletion


class LessonCompletionInline(admin.StackedInline):
    model = LessonCompletion
    extra = 0
    readonly_fields = ("created_at", "credits_deducted")


@admin.register(LessonBooking)
class LessonBookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "instructor",
        "vehicle",
        "starts_at",
        "ends_at",
        "status",
        "duration_minutes",
    )
    list_filter = ("status", "branch")
    search_fields = (
        "student__full_name",
        "student__email",
        "instructor__display_name",
        "vehicle__registration_number",
    )
    raw_id_fields = (
        "student",
        "course",
        "entitlement_account",
        "instructor",
        "vehicle",
        "branch",
        "pickup_zone",
        "created_by",
        "confirmed_by",
    )
    readonly_fields = ("created_at", "updated_at", "confirmed_at", "cancelled_at")
    inlines = [LessonCompletionInline]


@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "attended",
        "no_show",
        "credits_to_deduct",
        "credits_deducted",
        "vehicle_defect_flag",
        "created_at",
    )
    list_filter = ("attended", "no_show", "credits_deducted", "vehicle_defect_flag")
    raw_id_fields = ("booking", "completed_by")
    readonly_fields = ("created_at",)
