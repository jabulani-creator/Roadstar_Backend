"""Django admin for fleet records."""

from django.contrib import admin

from .models import InstructorProfile, PickupZone, Vehicle


@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "user",
        "home_branch",
        "licence_classes",
        "transmission",
        "status",
        "show_on_public_page",
        "photo",
    )
    list_filter = ("status", "transmission", "show_on_public_page", "home_branch")
    search_fields = ("display_name", "user__email", "employee_code")
    raw_id_fields = ("user", "home_branch")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "registration_number",
        "make_model",
        "branch",
        "licence_class",
        "transmission",
        "status",
        "show_on_public_page",
        "photo",
    )
    list_filter = (
        "status",
        "licence_class",
        "transmission",
        "vehicle_type",
        "show_on_public_page",
        "branch",
    )
    search_fields = ("name", "registration_number", "make_model", "status_note")
    raw_id_fields = ("branch",)


@admin.register(PickupZone)
class PickupZoneAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "branch",
        "radius_km",
        "travel_buffer_minutes",
        "travel_fee_amount",
        "is_active",
    )
    list_filter = ("is_active", "branch")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("branch",)
