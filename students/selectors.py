"""Read queries for students — portal sees self; staff see inbox of learners."""

from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from accounts.models import User
from students.models import ConsentRecord, Student


def students_staff(
    *,
    status: str | None = None,
    course_id: int | None = None,
) -> QuerySet[Student]:
    qs = (
        Student.objects.select_related(
            "user",
            "selected_course",
            "preferred_branch",
            "source_lead",
        )
        .prefetch_related(
            Prefetch("consents", queryset=ConsentRecord.objects.order_by("consent_type"))
        )
        .all()
    )
    if status:
        qs = qs.filter(status=status)
    if course_id is not None:
        qs = qs.filter(selected_course_id=course_id)
    return qs.order_by("-registered_at")


def student_by_id(*, student_id: int) -> Student | None:
    return (
        Student.objects.select_related(
            "user",
            "selected_course",
            "preferred_branch",
            "source_lead",
        )
        .prefetch_related("consents")
        .filter(pk=student_id)
        .first()
    )


def student_for_user(*, user: User) -> Student | None:
    if not user or not user.is_authenticated:
        return None
    return (
        Student.objects.select_related(
            "selected_course",
            "preferred_branch",
        )
        .prefetch_related("consents")
        .filter(user=user)
        .first()
    )
