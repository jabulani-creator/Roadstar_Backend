"""
Write workflows for `students`.

Plain English:
- Public registration creates a login account + learner profile + consents.
- Portal users may update their own non-sensitive contact details.
- Staff may update checklist, status, and assisted registrations.
- Terms + privacy consent are required; marketing is optional.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.models import StaffRole, User
from accounts.permissions import user_has_any_role, user_is_staff_operator
from catalogue.models import Branch, Course

from .models import (
    ConsentRecord,
    ConsentType,
    DocumentChecklistStatus,
    Student,
    StudentStatus,
)

UserModel = get_user_model()


class StudentServiceError(Exception):
    """Domain error with a safe API message."""

    def __init__(self, message: str, code: str = "error"):
        self.message = message
        self.code = code
        super().__init__(message)


def _can_manage(user: User) -> bool:
    return user_is_staff_operator(user) and (
        user_has_any_role(
            user,
            [StaffRole.OWNER, StaffRole.RECEPTION, StaffRole.CONTENT, StaffRole.FINANCE],
        )
        or user.is_superuser
        or user.is_staff
    )


def _require_manager(actor: User) -> None:
    if not _can_manage(actor):
        raise StudentServiceError("Not allowed to manage students.", code="forbidden")


def _refresh_checklist_status(student: Student) -> None:
    flags = [
        student.has_nrc_copy,
        student.has_medical_form,
        student.has_photos,
        student.has_proof_of_payment,
    ]
    if all(flags):
        student.checklist_status = DocumentChecklistStatus.COMPLETE
    elif any(flags):
        student.checklist_status = DocumentChecklistStatus.PARTIAL
    elif student.checklist_status != DocumentChecklistStatus.WAIVED:
        student.checklist_status = DocumentChecklistStatus.NOT_STARTED


def _record_consent(
    *,
    student: Student,
    consent_type: str,
    accepted: bool,
    actor: User | None,
) -> ConsentRecord:
    now = timezone.now() if accepted else None
    record, _ = ConsentRecord.objects.update_or_create(
        student=student,
        consent_type=consent_type,
        defaults={
            "accepted": accepted,
            "accepted_at": now,
            "recorded_by": actor,
        },
    )
    return record


def _link_and_convert_lead(*, student: Student, lead_id: int | None, actor: User | None) -> None:
    if not lead_id:
        return
    from leads.models import Lead
    from leads.services import LeadServiceError, apply_lead_conversion

    lead = Lead.objects.filter(pk=lead_id).first()
    if lead is None:
        raise StudentServiceError("Source lead not found.", code="lead_not_found")

    student.source_lead = lead
    student.save(update_fields=["source_lead", "updated_at"])

    if lead.status == "converted" and lead.converted_student_id == student.id:
        return

    convert_actor = actor or student.user
    if convert_actor is None:
        return

    try:
        # Move lead into a convertible state if still early in the funnel.
        if lead.status == "new":
            lead.status = "contacted"
            lead.save(update_fields=["status", "updated_at"])
        if lead.status in {"contacted", "recommended"}:
            if lead.status == "contacted" and lead.recommended_course_id is None:
                lead.recommended_course_id = student.selected_course_id
            lead.status = "quote_pending"
            lead.save(update_fields=["status", "recommended_course_id", "updated_at"])

        apply_lead_conversion(
            actor=convert_actor,
            lead=lead,
            note=f"Converted via student registration #{student.id}.",
            converted_student_id=student.id,
        )
    except LeadServiceError as exc:
        # Registration should still succeed; staff can finish lead conversion manually.
        if exc.code not in {"already_converted", "invalid_transition"}:
            raise StudentServiceError(exc.message, code=exc.code) from exc

@transaction.atomic
def register_student(*, data: dict, actor: User | None = None) -> Student:
    """
    Public (or staff-assisted) registration.

    Creates User + Student + required ConsentRecords.
    """
    payload = dict(data)
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    full_name = (payload.get("full_name") or "").strip()
    phone = (payload.get("phone") or "").strip()

    if not email:
        raise StudentServiceError("Email is required.", code="invalid_email")
    if not password or len(password) < 8:
        raise StudentServiceError(
            "Password must be at least 8 characters.",
            code="invalid_password",
        )
    if not full_name:
        raise StudentServiceError("Full name is required.", code="invalid_name")
    if not phone:
        raise StudentServiceError("Phone number is required.", code="invalid_phone")

    if not payload.get("accept_terms"):
        raise StudentServiceError(
            "You must accept the terms of training.",
            code="terms_required",
        )
    if not payload.get("accept_privacy"):
        raise StudentServiceError(
            "You must accept the privacy / data processing notice.",
            code="privacy_required",
        )

    if UserModel.objects.filter(email__iexact=email).exists():
        raise StudentServiceError(
            "An account with this email already exists.",
            code="email_taken",
        )
    if Student.objects.filter(email__iexact=email).exists():
        raise StudentServiceError(
            "A student profile with this email already exists.",
            code="email_taken",
        )

    course_id = payload.get("selected_course")
    branch_id = payload.get("preferred_branch")
    if course_id is not None and not Course.objects.filter(pk=course_id).exists():
        raise StudentServiceError("Selected course not found.", code="course_not_found")
    if branch_id is not None and not Branch.objects.filter(pk=branch_id).exists():
        raise StudentServiceError("Preferred branch not found.", code="branch_not_found")

    # Split name into User first/last for Django admin niceness.
    parts = full_name.split(None, 1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""

    user = UserModel.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
    )

    student = Student.objects.create(
        user=user,
        full_name=full_name,
        phone=phone,
        email=email,
        date_of_birth=payload.get("date_of_birth"),
        selected_course_id=course_id,
        preferred_branch_id=branch_id,
        preferred_schedule=payload.get("preferred_schedule") or "",
        pickup_notes=payload.get("pickup_notes") or "",
        sponsor_name=payload.get("sponsor_name") or "",
        sponsor_phone=payload.get("sponsor_phone") or "",
        sponsor_email=payload.get("sponsor_email") or "",
        sponsor_relationship=payload.get("sponsor_relationship") or "",
        referral_source=payload.get("referral_source") or "",
        referral_detail=payload.get("referral_detail") or "",
        status=StudentStatus.REGISTERED,
    )

    consent_actor = actor or user
    _record_consent(
        student=student,
        consent_type=ConsentType.TERMS,
        accepted=True,
        actor=consent_actor,
    )
    _record_consent(
        student=student,
        consent_type=ConsentType.PRIVACY,
        accepted=True,
        actor=consent_actor,
    )
    _record_consent(
        student=student,
        consent_type=ConsentType.MARKETING,
        accepted=bool(payload.get("accept_marketing")),
        actor=consent_actor,
    )

    _link_and_convert_lead(
        student=student,
        lead_id=payload.get("source_lead"),
        actor=consent_actor,
    )

    return (
        Student.objects.select_related("selected_course", "preferred_branch")
        .prefetch_related("consents")
        .get(pk=student.pk)
    )


@transaction.atomic
def create_student_from_lead(*, actor: User, lead, password: str | None = None) -> Student:
    """
    Staff converts a lead into a student profile.

    Requires lead.email. Creates a portal account when password is provided;
    otherwise creates a profile without login until the learner sets one later.
    """
    _require_manager(actor)
    email = (lead.email or "").strip().lower()
    if not email:
        raise StudentServiceError(
            "Lead needs an email before conversion to a student account.",
            code="email_required",
        )
    if Student.objects.filter(email__iexact=email).exists():
        raise StudentServiceError(
            "A student profile with this email already exists.",
            code="email_taken",
        )

    user = None
    if password:
        if UserModel.objects.filter(email__iexact=email).exists():
            raise StudentServiceError(
                "An account with this email already exists.",
                code="email_taken",
            )
        parts = lead.full_name.split(None, 1)
        user = UserModel.objects.create_user(
            email=email,
            password=password,
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else "",
            phone=lead.phone,
        )

    course_id = lead.recommended_course_id or lead.interested_course_id
    student = Student.objects.create(
        user=user,
        full_name=lead.full_name,
        phone=lead.phone,
        email=email,
        selected_course_id=course_id,
        preferred_branch_id=lead.preferred_branch_id,
        preferred_schedule=lead.preferred_schedule or "",
        referral_source=lead.referral_source or "",
        referral_detail=lead.referral_detail or "",
        source_lead=lead,
        status=StudentStatus.REGISTERED,
    )

    # Staff-assisted conversion still requires recorded terms/privacy acceptance.
    _record_consent(
        student=student,
        consent_type=ConsentType.TERMS,
        accepted=True,
        actor=actor,
    )
    _record_consent(
        student=student,
        consent_type=ConsentType.PRIVACY,
        accepted=True,
        actor=actor,
    )
    _record_consent(
        student=student,
        consent_type=ConsentType.MARKETING,
        accepted=False,
        actor=actor,
    )

    _link_and_convert_lead(student=student, lead_id=lead.id, actor=actor)

    return (
        Student.objects.select_related("selected_course", "preferred_branch")
        .prefetch_related("consents")
        .get(pk=student.pk)
    )


def update_student_portal(*, user: User, student: Student, data: dict) -> Student:
    if student.user_id != user.id:
        raise StudentServiceError("Not your student profile.", code="forbidden")

    allowed = {
        "full_name",
        "phone",
        "date_of_birth",
        "preferred_branch",
        "preferred_schedule",
        "pickup_notes",
        "sponsor_name",
        "sponsor_phone",
        "sponsor_email",
        "sponsor_relationship",
    }
    for field, value in data.items():
        if field not in allowed:
            continue
        setattr(student, field, value)
    student.save()

    if "full_name" in data or "phone" in data:
        if student.user_id:
            parts = student.full_name.split(None, 1)
            student.user.first_name = parts[0]
            student.user.last_name = parts[1] if len(parts) > 1 else ""
            student.user.phone = student.phone
            student.user.save(update_fields=["first_name", "last_name", "phone"])

    return student


def update_student_staff(*, actor: User, student: Student, data: dict) -> Student:
    _require_manager(actor)
    protected = {"id", "user", "source_lead", "registered_at", "updated_at", "email"}
    checklist_fields = {
        "has_nrc_copy",
        "has_medical_form",
        "has_photos",
        "has_proof_of_payment",
        "checklist_status",
    }
    touched_checklist = False

    for field, value in data.items():
        if field in protected:
            continue
        if field in checklist_fields:
            touched_checklist = True
        setattr(student, field, value)

    if touched_checklist and "checklist_status" not in data:
        _refresh_checklist_status(student)

    student.save()
    return student


def set_student_status(
    *,
    actor: User,
    student: Student,
    new_status: str,
    note: str = "",
) -> Student:
    _require_manager(actor)
    if new_status not in StudentStatus.values:
        raise StudentServiceError("Unknown student status.", code="invalid_status")

    student.status = new_status
    if note.strip():
        stamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        line = f"[{stamp} {actor.email}] status→{new_status}: {note.strip()}"
        student.internal_notes = (
            f"{student.internal_notes}\n{line}" if student.internal_notes else line
        )
    student.save()
    return student
