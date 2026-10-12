"""
DRF permission classes for `leads`.

Plain English: reception/owner (and content) may run the enquiry inbox.
"""

from rest_framework.permissions import BasePermission

from accounts.models import StaffRole
from accounts.permissions import user_has_any_role, user_is_staff_operator


class IsLeadStaff(BasePermission):
    """Staff who may view the lead inbox."""

    message = "Lead staff access required."

    def has_permission(self, request, view) -> bool:
        return user_is_staff_operator(request.user)


class IsLeadManager(BasePermission):
    """Staff who may assign/update/convert leads."""

    message = "Lead manager access required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not user_is_staff_operator(user):
            return False
        return user_has_any_role(
            user,
            [StaffRole.OWNER, StaffRole.RECEPTION, StaffRole.CONTENT],
        ) or user.is_staff
