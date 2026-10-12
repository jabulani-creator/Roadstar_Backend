"""
Permission checks for `accounts`.

Plain English:
- Answers: "Is this user allowed to do this?"
- Frontend menu hiding is convenience only.
- These backend checks are the real security gate.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import StaffRole, User
from .selectors import get_user_roles


def user_has_role(user: User, role: str) -> bool:
    """True if the user holds the given staff role code."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return role in get_user_roles(user)


def user_has_any_role(user: User, roles: list[str]) -> bool:
    """True if the user holds at least one of the given roles."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    held = set(get_user_roles(user))
    return any(role in held for role in roles)


def user_is_staff_operator(user: User) -> bool:
    """
    True for people who may use the staff dashboard.

    Includes Django superuser/staff flags or any Roadstar staff role badge.
    Students with only a portal account (no staff role) return False.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return bool(get_user_roles(user))


class IsStaffOperator(BasePermission):
    """
    DRF permission: allow only staff operators.

    Use on dashboard endpoints later (leads, catalogue admin, scheduler, etc.).
    """

    message = "Staff access required."

    def has_permission(self, request, view) -> bool:
        return user_is_staff_operator(request.user)


class IsOwner(BasePermission):
    """Allow owner role (or superuser)."""

    message = "Owner access required."

    def has_permission(self, request, view) -> bool:
        return user_has_role(request.user, StaffRole.OWNER)


class IsReceptionOrOwner(BasePermission):
    """Allow reception/scheduler or owner (typical ops controllers)."""

    message = "Reception or owner access required."

    def has_permission(self, request, view) -> bool:
        return user_has_any_role(
            request.user,
            [StaffRole.RECEPTION, StaffRole.OWNER],
        )


class IsContentManagerOrOwner(BasePermission):
    """Allow content managers or owners to publish catalogue/content."""

    message = "Content manager or owner access required."

    def has_permission(self, request, view) -> bool:
        return user_has_any_role(
            request.user,
            [StaffRole.CONTENT, StaffRole.OWNER],
        )


class ReadOnly(BasePermission):
    """
    Allow safe read methods only (GET/HEAD/OPTIONS).

    Useful later when combining permissions, e.g. public read + staff write.
    """

    def has_permission(self, request, view) -> bool:
        return request.method in SAFE_METHODS
