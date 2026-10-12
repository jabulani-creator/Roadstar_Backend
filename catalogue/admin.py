"""
Django admin for catalogue records.
"""

from django.contrib import admin

from .models import Branch, Course, Promotion


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "primary_phone", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "address", "landmark", "primary_phone")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "licence_class",
        "transmission",
        "level",
        "price_amount",
        "status",
        "show_price",
    )
    list_filter = ("status", "licence_class", "transmission", "level", "show_price")
    search_fields = ("name", "summary", "slug")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("branches",)
    readonly_fields = ("approved_at", "created_at", "updated_at")


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("title", "starts_at", "ends_at", "status", "discount_label")
    list_filter = ("status",)
    search_fields = ("title", "summary", "slug")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("courses",)
