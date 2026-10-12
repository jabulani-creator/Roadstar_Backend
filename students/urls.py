"""
URL routes for `students`.

Public / portal:
- POST /api/v1/students/register/
- GET/PATCH /api/v1/students/me/

Staff:
- GET /api/v1/staff/students/
- GET/PATCH /api/v1/staff/students/{id}/
- POST /api/v1/staff/students/{id}/activate/
- POST /api/v1/staff/students/{id}/withdraw/
- POST /api/v1/staff/students/from-lead/{lead_id}/
"""

from django.urls import path

from .viewsets import (
    PublicStudentRegisterView,
    StaffStudentActivateView,
    StaffStudentDetailView,
    StaffStudentFromLeadView,
    StaffStudentListView,
    StaffStudentWithdrawView,
    StudentMeView,
)

urlpatterns = [
    path(
        "students/register/",
        PublicStudentRegisterView.as_view(),
        name="public-student-register",
    ),
    path("students/me/", StudentMeView.as_view(), name="student-me"),
    path("staff/students/", StaffStudentListView.as_view(), name="staff-student-list"),
    path(
        "staff/students/from-lead/<int:lead_id>/",
        StaffStudentFromLeadView.as_view(),
        name="staff-student-from-lead",
    ),
    path(
        "staff/students/<int:student_id>/",
        StaffStudentDetailView.as_view(),
        name="staff-student-detail",
    ),
    path(
        "staff/students/<int:student_id>/activate/",
        StaffStudentActivateView.as_view(),
        name="staff-student-activate",
    ),
    path(
        "staff/students/<int:student_id>/withdraw/",
        StaffStudentWithdrawView.as_view(),
        name="staff-student-withdraw",
    ),
]
