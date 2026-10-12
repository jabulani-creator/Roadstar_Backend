"""Django admin for learning / practice papers."""

from django.contrib import admin

from .models import (
    Attempt,
    AttemptAnswer,
    PracticePaper,
    PracticePaperQuestion,
    Question,
    StudyDocument,
    Topic,
)


class PracticePaperQuestionInline(admin.TabularInline):
    model = PracticePaperQuestion
    extra = 0
    raw_id_fields = ("question",)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort_order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "topic",
        "difficulty",
        "correct_choice",
        "status",
        "is_rights_cleared",
    )
    list_filter = ("status", "difficulty", "topic", "is_rights_cleared")
    search_fields = ("prompt", "explanation")
    raw_id_fields = ("topic", "created_by")


@admin.register(PracticePaper)
class PracticePaperAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "time_limit_minutes",
        "pass_mark_percent",
        "available_to_public_preview",
    )
    list_filter = ("status", "available_to_public_preview")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [PracticePaperQuestionInline]


@admin.register(StudyDocument)
class StudyDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "is_rights_cleared", "status")
    list_filter = ("status", "is_rights_cleared")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}


class AttemptAnswerInline(admin.TabularInline):
    model = AttemptAnswer
    extra = 0
    readonly_fields = ("question", "selected_choice", "is_correct")


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "paper",
        "status",
        "score_percent",
        "passed",
        "started_at",
        "submitted_at",
    )
    list_filter = ("status", "passed")
    search_fields = ("student__full_name", "student__email", "paper__title")
    raw_id_fields = ("student", "paper")
    inlines = [AttemptAnswerInline]
