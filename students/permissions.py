"""
DRF permission classes for `students`.
"""

from rest_framework.permissions import BasePermission

from accounts.models import StaffRole
from accounts.permissions import user_has_any_role, user_is_staff_operator


class IsStudentStaff(BasePermission):
    """Staff who may view student records."""

    message = "Student staff access required."

    def has_permission(self, request, view) -> bool:
        return user_is_staff_operator(request.user)


class IsStudentManager(BasePermission):
    """Staff who may create/update student registrations."""

    message = "Student manager access required."

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
            [
                StaffRole.OWNER,
                StaffRole.RECEPTION,
                StaffRole.CONTENT,
                StaffRole.FINANCE,
            ],
        ) or user.is_staff


class IsStudentPortalUser(BasePermission):
    """Authenticated user who has a linked student profile."""

    message = "Student portal access required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return hasattr(user, "student_profile") and user.student_profile is not None
