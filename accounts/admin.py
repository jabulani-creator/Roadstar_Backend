"""
Django admin registration for accounts.

Plain English: this lets you create/edit users and role badges in /admin/
while we build the real dashboard later.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import StaffRoleAssignment, User


class StaffRoleAssignmentInline(admin.TabularInline):
    model = StaffRoleAssignment
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "phone",
        "show_on_public_staff_list",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_active", "show_on_public_staff_list")
    search_fields = ("email", "first_name", "last_name", "phone")
    inlines = [StaffRoleAssignmentInline]

    # Django's default UserAdmin forms expect a username field. Remap to email.
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone")}),
        (
            "Public trust page",
            {
                "fields": (
                    "show_on_public_staff_list",
                    "public_title",
                    "public_bio",
                    "public_list_order",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")


@admin.register(StaffRoleAssignment)
class StaffRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("user__email",)
