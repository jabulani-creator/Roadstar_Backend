"""DRF permission classes for `fleet`."""

from rest_framework.permissions import BasePermission

from accounts.models import StaffRole
from accounts.permissions import user_has_any_role, user_is_staff_operator


class IsFleetStaff(BasePermission):
    message = "Fleet staff access required."

    def has_permission(self, request, view) -> bool:
        return user_is_staff_operator(request.user)


class IsFleetManager(BasePermission):
    message = "Fleet manager access required."

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
            [StaffRole.OWNER, StaffRole.RECEPTION],
        ) or user.is_staff
