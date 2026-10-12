"""Django admin for student profiles and consents."""

from django.contrib import admin

from .models import ConsentRecord, Student


class ConsentRecordInline(admin.TabularInline):
    model = ConsentRecord
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "phone",
        "status",
        "selected_course",
        "preferred_branch",
        "checklist_status",
        "registered_at",
    )
    list_filter = ("status", "checklist_status", "preferred_branch")
    search_fields = ("full_name", "email", "phone", "national_id", "sponsor_name")
    raw_id_fields = ("user", "selected_course", "preferred_branch", "source_lead")
    readonly_fields = ("registered_at", "updated_at")
    inlines = [ConsentRecordInline]


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "consent_type", "accepted", "accepted_at", "created_at")
    list_filter = ("consent_type", "accepted")
    search_fields = ("student__full_name", "student__email")
