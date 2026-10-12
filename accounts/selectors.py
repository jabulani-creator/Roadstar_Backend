"""
Read/query helpers for `accounts`.

Plain English:
- Selectors answer "get me the right records" questions.
- They do not change data and do not make permission decisions.
- Views/viewsets call these so query logic is not copied around.
"""

from django.contrib.auth import get_user_model
from django.db.models import Prefetch, QuerySet

from .models import StaffRoleAssignment

User = get_user_model()


def get_user_queryset() -> QuerySet:
    """
    Base user list query.

    Prefetch role assignments so serializing many users does not
    hit the database once per user (N+1 problem).
    """
    return User.objects.prefetch_related(
        Prefetch(
            "role_assignments",
            queryset=StaffRoleAssignment.objects.order_by("role"),
        )
    )


def get_user_by_id(user_id: int) -> User | None:
    """Fetch one user with roles loaded, or None if missing."""
    return get_user_queryset().filter(pk=user_id).first()


def get_current_user(user: User) -> User:
    """
    Reload the request user with roles ready for UserMeSerializer.

    Why reload?
    - request.user from JWT auth may not have role_assignments prefetched.
    - We want one consistent shape for /auth/me/.
    """
    return get_user_queryset().get(pk=user.pk)


def get_user_roles(user: User) -> list[str]:
    """
    Return role codes only, e.g. ["owner", "instructor"].

    Useful later in permissions.py without re-querying ad hoc.
    """
    return list(
        StaffRoleAssignment.objects.filter(user=user)
        .order_by("role")
        .values_list("role", flat=True)
    )


def get_public_staff_queryset() -> QuerySet:
    """
    People approved to appear on public trust/instructor pages.

    Excludes inactive accounts. Does not expose private emails by itself —
    the public serializer chooses safe fields.
    """
    return (
        get_user_queryset()
        .filter(is_active=True, show_on_public_staff_list=True)
        .order_by("public_list_order", "first_name", "last_name", "email")
    )
