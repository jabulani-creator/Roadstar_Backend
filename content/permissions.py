"""
DRF permission classes for `content`.

Plain English: thin wrappers around accounts role checks for views.
"""

from rest_framework.permissions import BasePermission

from accounts.models import StaffRole
from accounts.permissions import user_has_any_role, user_is_staff_operator


class IsContentStaff(BasePermission):
    """Staff who may access content dashboard endpoints."""

    message = "Content staff access required."

    def has_permission(self, request, view) -> bool:
        return user_is_staff_operator(request.user)


class IsContentEditor(BasePermission):
    """Owner/content (or superuser) who may create/update/publish content."""

    message = "Content editor access required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user_has_any_role(user, [StaffRole.OWNER, StaffRole.CONTENT])
