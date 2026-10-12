"""DRF permission classes for `learning`."""

from rest_framework.permissions import BasePermission

from accounts.models import StaffRole
from accounts.permissions import user_has_any_role, user_is_staff_operator


class IsLearningStaff(BasePermission):
    message = "Learning staff access required."

    def has_permission(self, request, view) -> bool:
        return user_is_staff_operator(request.user)


class IsLearningEditor(BasePermission):
    message = "Learning editor access required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not user_is_staff_operator(user):
            return False
        return user_has_any_role(
            user, [StaffRole.OWNER, StaffRole.CONTENT]
        ) or user.is_staff
