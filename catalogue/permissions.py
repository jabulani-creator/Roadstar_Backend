"""
DRF permission classes for `catalogue`.

Plain English: thin wrappers around accounts role checks for views.
"""

from rest_framework.permissions import BasePermission

from accounts.models import StaffRole
from accounts.permissions import user_has_any_role, user_is_staff_operator


class IsCatalogueStaff(BasePermission):
    """Staff who may access catalogue dashboard endpoints."""

    message = "Catalogue staff access required."

    def has_permission(self, request, view) -> bool:
        return user_is_staff_operator(request.user)


class IsCatalogueEditor(BasePermission):
    """Owner/content (or superuser) who may create/update/publish catalogue items."""

    message = "Catalogue editor access required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user_has_any_role(user, [StaffRole.OWNER, StaffRole.CONTENT])


class IsBranchManager(BasePermission):
    """Owner/content/reception may manage branch location records."""

    message = "Branch manager access required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user_has_any_role(
            user,
            [StaffRole.OWNER, StaffRole.CONTENT, StaffRole.RECEPTION],
        )
