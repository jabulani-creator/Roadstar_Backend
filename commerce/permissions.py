"""
DRF permission classes for `commerce`.
"""

from rest_framework.permissions import BasePermission

from accounts.models import StaffRole
from accounts.permissions import user_has_any_role, user_is_staff_operator


class IsCommerceStaff(BasePermission):
    message = "Commerce staff access required."

    def has_permission(self, request, view) -> bool:
        return user_is_staff_operator(request.user)


class IsFinanceStaff(BasePermission):
    message = "Finance access required."

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
            [StaffRole.OWNER, StaffRole.FINANCE, StaffRole.RECEPTION],
        ) or user.is_staff
