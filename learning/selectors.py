"""Read queries for learning — public preview vs student attempts vs staff."""

from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from students.models import Student

from .models import (
    Attempt,
    PracticePaper,
    PracticePaperQuestion,
    PublishStatus,
    Question,
    StudyDocument,
    Topic,
)


def topics_all() -> QuerySet[Topic]:
    return Topic.objects.all().order_by("sort_order", "name")


def topic_by_slug(*, slug: str) -> Topic | None:
    return Topic.objects.filter(slug=slug).first()


def questions_staff(*, status: str | None = None) -> QuerySet[Question]:
    qs = Question.objects.select_related("topic", "created_by").all()
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("topic__sort_order", "id")


def question_by_id(*, question_id: int) -> Question | None:
    return (
        Question.objects.select_related("topic", "created_by")
        .filter(pk=question_id)
        .first()
    )


def papers_public_preview() -> QuerySet[PracticePaper]:
    return PracticePaper.objects.filter(
        status=PublishStatus.APPROVED,
        available_to_public_preview=True,
    ).order_by("title")


def papers_for_students() -> QuerySet[PracticePaper]:
    return (
        PracticePaper.objects.filter(status=PublishStatus.APPROVED)
        .prefetch_related(
            Prefetch(
                "paper_questions",
                queryset=PracticePaperQuestion.objects.select_related(
                    "question", "question__topic"
                ).order_by("sort_order"),
            )
        )
        .order_by("title")
    )


def papers_staff(*, status: str | None = None) -> QuerySet[PracticePaper]:
    qs = PracticePaper.objects.prefetch_related("paper_questions__question").all()
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("title")


def paper_by_slug(*, slug: str) -> PracticePaper | None:
    return (
        PracticePaper.objects.prefetch_related(
            Prefetch(
                "paper_questions",
                queryset=PracticePaperQuestion.objects.select_related(
                    "question", "question__topic"
                ).order_by("sort_order"),
            )
        )
        .filter(slug=slug)
        .first()
    )


def study_documents_public() -> QuerySet[StudyDocument]:
    return (
        StudyDocument.objects.select_related("topic")
        .filter(status=PublishStatus.APPROVED, is_rights_cleared=True)
        .order_by("title")
    )


def study_documents_staff() -> QuerySet[StudyDocument]:
    return StudyDocument.objects.select_related("topic").all().order_by("title")


def study_document_by_slug(*, slug: str) -> StudyDocument | None:
    return StudyDocument.objects.select_related("topic").filter(slug=slug).first()


def attempts_for_student(*, student: Student) -> QuerySet[Attempt]:
    return (
        Attempt.objects.select_related("paper", "student")
        .filter(student=student)
        .order_by("-started_at")
    )


def attempt_by_id(*, attempt_id: int) -> Attempt | None:
    return (
        Attempt.objects.select_related("paper", "student")
        .prefetch_related("answers__question__topic")
        .filter(pk=attempt_id)
        .first()
    )
