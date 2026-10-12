"""
Write workflows for `learning`.

Plain English:
- Staff author questions/papers and approve them for students.
- Students start an attempt, answer, and submit for auto-scoring.
- Correct answers / explanations are only revealed after submit.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import StaffRole, User
from accounts.permissions import user_has_any_role, user_is_staff_operator
from students.models import Student

from .models import (
    Attempt,
    AttemptAnswer,
    AttemptStatus,
    PracticePaper,
    PracticePaperQuestion,
    PublishStatus,
    Question,
    StudyDocument,
    Topic,
)


class LearningServiceError(Exception):
    def __init__(self, message: str, code: str = "error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _can_manage(user: User) -> bool:
    return user_is_staff_operator(user) and (
        user_has_any_role(user, [StaffRole.OWNER, StaffRole.CONTENT])
        or user.is_superuser
        or user.is_staff
    )


def _require_manager(actor: User) -> None:
    if not _can_manage(actor):
        raise LearningServiceError(
            "Not allowed to manage learning content.",
            code="forbidden",
        )


def _unique_slug(model, base: str, *, exclude_pk=None) -> str:
    base = slugify(base) or model.__name__.lower()
    slug = base
    n = 2
    while True:
        qs = model.objects.filter(slug=slug)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        if not qs.exists():
            return slug
        slug = f"{base}-{n}"
        n += 1


# --- Topics ---


def create_topic(*, actor: User, data: dict) -> Topic:
    _require_manager(actor)
    payload = dict(data)
    name = (payload.get("name") or "").strip()
    if not name:
        raise LearningServiceError("Topic name is required.", code="invalid_name")
    payload["name"] = name
    payload.setdefault("slug", _unique_slug(Topic, name))
    return Topic.objects.create(**payload)


def update_topic(*, actor: User, topic: Topic, data: dict) -> Topic:
    _require_manager(actor)
    for field, value in data.items():
        if field == "slug":
            continue
        setattr(topic, field, value)
    topic.save()
    return topic


# --- Questions ---


def create_question(*, actor: User, data: dict) -> Question:
    _require_manager(actor)
    payload = dict(data)
    payload.pop("status", None)
    if not payload.get("is_rights_cleared", True):
        raise LearningServiceError(
            "Questions must be rights-cleared or Roadstar-authored.",
            code="rights_required",
        )
    choice = payload.get("correct_choice")
    if choice == "C" and not (payload.get("choice_c") or "").strip():
        raise LearningServiceError(
            "choice_c is required when correct_choice is C.",
            code="invalid_choice",
        )
    if choice == "D" and not (payload.get("choice_d") or "").strip():
        raise LearningServiceError(
            "choice_d is required when correct_choice is D.",
            code="invalid_choice",
        )
    payload.setdefault("status", PublishStatus.DRAFT)
    payload["created_by"] = actor
    return Question.objects.create(**payload)


def update_question(*, actor: User, question: Question, data: dict) -> Question:
    _require_manager(actor)
    payload = dict(data)
    payload.pop("status", None)
    payload.pop("created_by", None)
    for field, value in payload.items():
        setattr(question, field, value)
    question.save()
    return question


def approve_question(*, actor: User, question: Question) -> Question:
    _require_manager(actor)
    if not question.is_rights_cleared:
        raise LearningServiceError(
            "Cannot approve a question that is not rights-cleared.",
            code="rights_required",
        )
    question.status = PublishStatus.APPROVED
    question.save(update_fields=["status", "updated_at"])
    return question


# --- Practice papers ---


@transaction.atomic
def create_practice_paper(*, actor: User, data: dict) -> PracticePaper:
    _require_manager(actor)
    payload = dict(data)
    question_ids = payload.pop("question_ids", None) or []
    payload.pop("status", None)
    title = (payload.get("title") or "").strip()
    if not title:
        raise LearningServiceError("Title is required.", code="invalid_title")
    payload["title"] = title
    payload.setdefault("slug", _unique_slug(PracticePaper, title))
    payload.setdefault("status", PublishStatus.DRAFT)
    paper = PracticePaper.objects.create(**payload)
    _set_paper_questions(paper, question_ids)
    return paper


@transaction.atomic
def update_practice_paper(
    *, actor: User, paper: PracticePaper, data: dict
) -> PracticePaper:
    _require_manager(actor)
    payload = dict(data)
    question_ids = payload.pop("question_ids", None)
    for field in ("status", "slug", "approved_by", "approved_at"):
        payload.pop(field, None)
    for field, value in payload.items():
        setattr(paper, field, value)
    paper.save()
    if question_ids is not None:
        _set_paper_questions(paper, question_ids)
    return paper


def _set_paper_questions(paper: PracticePaper, question_ids: list[int]) -> None:
    PracticePaperQuestion.objects.filter(paper=paper).delete()
    for order, qid in enumerate(question_ids):
        question = Question.objects.filter(pk=qid).first()
        if question is None:
            raise LearningServiceError(
                f"Question {qid} not found.",
                code="question_not_found",
            )
        if not question.is_rights_cleared:
            raise LearningServiceError(
                f"Question {qid} is not rights-cleared.",
                code="rights_required",
            )
        PracticePaperQuestion.objects.create(
            paper=paper, question=question, sort_order=order
        )


def approve_practice_paper(*, actor: User, paper: PracticePaper) -> PracticePaper:
    _require_manager(actor)
    links = paper.paper_questions.select_related("question")
    if not links.exists():
        raise LearningServiceError(
            "Cannot approve a paper with no questions.",
            code="empty_paper",
        )
    for link in links:
        if link.question.status != PublishStatus.APPROVED:
            raise LearningServiceError(
                "All questions on the paper must be approved first.",
                code="questions_not_approved",
            )
        if not link.question.is_rights_cleared:
            raise LearningServiceError(
                "All questions must be rights-cleared.",
                code="rights_required",
            )
    paper.status = PublishStatus.APPROVED
    paper.approved_by = actor
    paper.approved_at = timezone.now()
    paper.save(
        update_fields=["status", "approved_by", "approved_at", "updated_at"]
    )
    return paper


def deactivate_practice_paper(*, actor: User, paper: PracticePaper) -> PracticePaper:
    _require_manager(actor)
    paper.status = PublishStatus.INACTIVE
    paper.save(update_fields=["status", "updated_at"])
    return paper


# --- Study documents ---


def create_study_document(*, actor: User, data: dict) -> StudyDocument:
    _require_manager(actor)
    payload = dict(data)
    payload.pop("status", None)
    title = (payload.get("title") or "").strip()
    if not title:
        raise LearningServiceError("Title is required.", code="invalid_title")
    payload["title"] = title
    payload.setdefault("slug", _unique_slug(StudyDocument, title))
    payload.setdefault("status", PublishStatus.DRAFT)
    return StudyDocument.objects.create(**payload)


def approve_study_document(*, actor: User, doc: StudyDocument) -> StudyDocument:
    _require_manager(actor)
    if not doc.is_rights_cleared:
        raise LearningServiceError(
            "Cannot approve a study document that is not rights-cleared.",
            code="rights_required",
        )
    doc.status = PublishStatus.APPROVED
    doc.save(update_fields=["status", "updated_at"])
    return doc


# --- Attempts ---


def refresh_attempt(attempt: Attempt) -> Attempt:
    """Expire in-progress attempts past their timer, otherwise return as-is."""
    return _auto_expire_if_needed(attempt)


def _auto_expire_if_needed(attempt: Attempt) -> Attempt:
    if (
        attempt.status == AttemptStatus.IN_PROGRESS
        and attempt.expires_at
        and timezone.now() >= attempt.expires_at
    ):
        return submit_attempt(
            student=attempt.student,
            attempt=attempt,
            answers={},
            auto_expired=True,
        )
    return attempt


@transaction.atomic
def start_attempt(*, student: Student, paper: PracticePaper) -> Attempt:
    if paper.status != PublishStatus.APPROVED:
        raise LearningServiceError(
            "This practice paper is not available.",
            code="paper_unavailable",
        )
    open_attempt = Attempt.objects.filter(
        student=student,
        paper=paper,
        status=AttemptStatus.IN_PROGRESS,
    ).first()
    if open_attempt:
        return _auto_expire_if_needed(open_attempt)

    expires_at = None
    if paper.time_limit_minutes:
        expires_at = timezone.now() + timedelta(minutes=paper.time_limit_minutes)

    return Attempt.objects.create(
        student=student,
        paper=paper,
        status=AttemptStatus.IN_PROGRESS,
        expires_at=expires_at,
        score_total=paper.paper_questions.count(),
    )


@transaction.atomic
def save_attempt_answers(
    *, student: Student, attempt: Attempt, answers: dict[int, str]
) -> Attempt:
    if attempt.student_id != student.id:
        raise LearningServiceError("Not your attempt.", code="forbidden")
    attempt = _auto_expire_if_needed(attempt)
    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise LearningServiceError(
            "Attempt is no longer in progress.",
            code="invalid_status",
        )

    valid_qids = set(
        attempt.paper.paper_questions.values_list("question_id", flat=True)
    )
    for qid, choice in answers.items():
        qid = int(qid)
        if qid not in valid_qids:
            raise LearningServiceError(
                f"Question {qid} is not on this paper.",
                code="invalid_question",
            )
        choice = (choice or "").upper().strip()
        if choice and choice not in {"A", "B", "C", "D"}:
            raise LearningServiceError(
                "selected_choice must be A, B, C, or D.",
                code="invalid_choice",
            )
        AttemptAnswer.objects.update_or_create(
            attempt=attempt,
            question_id=qid,
            defaults={"selected_choice": choice, "is_correct": False},
        )
    return attempt


@transaction.atomic
def submit_attempt(
    *,
    student: Student,
    attempt: Attempt,
    answers: dict | None = None,
    auto_expired: bool = False,
) -> Attempt:
    if attempt.student_id != student.id:
        raise LearningServiceError("Not your attempt.", code="forbidden")
    if attempt.status != AttemptStatus.IN_PROGRESS and not auto_expired:
        # Allow re-entry only for in-progress; already submitted is idempotent return.
        if attempt.status in {AttemptStatus.SUBMITTED, AttemptStatus.EXPIRED}:
            return attempt
        raise LearningServiceError(
            "Attempt is no longer in progress.",
            code="invalid_status",
        )

    if answers:
        # Persist final answers before grading (skip recursive expire).
        if attempt.status == AttemptStatus.IN_PROGRESS:
            valid_qids = set(
                attempt.paper.paper_questions.values_list("question_id", flat=True)
            )
            for qid, choice in answers.items():
                qid = int(qid)
                if qid not in valid_qids:
                    continue
                choice = (choice or "").upper().strip()
                if choice and choice not in {"A", "B", "C", "D"}:
                    continue
                AttemptAnswer.objects.update_or_create(
                    attempt=attempt,
                    question_id=qid,
                    defaults={"selected_choice": choice, "is_correct": False},
                )

    # Ensure an answer row exists for every question.
    for link in attempt.paper.paper_questions.select_related("question"):
        AttemptAnswer.objects.get_or_create(
            attempt=attempt,
            question=link.question,
            defaults={"selected_choice": "", "is_correct": False},
        )

    correct = 0
    total = 0
    for answer in attempt.answers.select_related("question"):
        total += 1
        is_correct = (
            answer.selected_choice
            and answer.selected_choice == answer.question.correct_choice
        )
        answer.is_correct = bool(is_correct)
        answer.save(update_fields=["is_correct"])
        if is_correct:
            correct += 1

    percent = Decimal("0")
    if total:
        percent = (Decimal(correct) * Decimal("100") / Decimal(total)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    attempt.score_correct = correct
    attempt.score_total = total
    attempt.score_percent = percent
    attempt.passed = percent >= Decimal(attempt.paper.pass_mark_percent)
    attempt.submitted_at = timezone.now()
    attempt.status = (
        AttemptStatus.EXPIRED if auto_expired else AttemptStatus.SUBMITTED
    )
    attempt.save()
    return attempt
