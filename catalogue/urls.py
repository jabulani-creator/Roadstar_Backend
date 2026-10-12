"""
URL routes for `catalogue`.

Public:
- GET /api/v1/branches/
- GET /api/v1/branches/{slug}/
- GET /api/v1/courses/
- GET /api/v1/courses/{slug}/
- GET /api/v1/promotions/

Staff:
- /api/v1/staff/branches/
- /api/v1/staff/courses/
- /api/v1/staff/promotions/
"""

from django.urls import path

from .viewsets import (
    PublicBranchDetailView,
    PublicBranchListView,
    PublicCourseDetailView,
    PublicCourseListView,
    PublicPromotionListView,
    StaffBranchDetailView,
    StaffBranchListCreateView,
    StaffCourseApproveView,
    StaffCourseDeactivateView,
    StaffCourseDetailView,
    StaffCourseListCreateView,
    StaffCourseRejectView,
    StaffCourseSubmitView,
    StaffPromotionApproveView,
    StaffPromotionDetailView,
    StaffPromotionListCreateView,
    StaffPromotionRejectView,
)

urlpatterns = [
    # Public
    path("branches/", PublicBranchListView.as_view(), name="public-branch-list"),
    path("branches/<slug:slug>/", PublicBranchDetailView.as_view(), name="public-branch-detail"),
    path("courses/", PublicCourseListView.as_view(), name="public-course-list"),
    path("courses/<slug:slug>/", PublicCourseDetailView.as_view(), name="public-course-detail"),
    path("promotions/", PublicPromotionListView.as_view(), name="public-promotion-list"),
    # Staff
    path("staff/branches/", StaffBranchListCreateView.as_view(), name="staff-branch-list"),
    path("staff/branches/<slug:slug>/", StaffBranchDetailView.as_view(), name="staff-branch-detail"),
    path("staff/courses/", StaffCourseListCreateView.as_view(), name="staff-course-list"),
    path("staff/courses/<slug:slug>/", StaffCourseDetailView.as_view(), name="staff-course-detail"),
    path(
        "staff/courses/<slug:slug>/submit/",
        StaffCourseSubmitView.as_view(),
        name="staff-course-submit",
    ),
    path(
        "staff/courses/<slug:slug>/approve/",
        StaffCourseApproveView.as_view(),
        name="staff-course-approve",
    ),
    path(
        "staff/courses/<slug:slug>/reject/",
        StaffCourseRejectView.as_view(),
        name="staff-course-reject",
    ),
    path(
        "staff/courses/<slug:slug>/deactivate/",
        StaffCourseDeactivateView.as_view(),
        name="staff-course-deactivate",
    ),
    path("staff/promotions/", StaffPromotionListCreateView.as_view(), name="staff-promotion-list"),
    path(
        "staff/promotions/<slug:slug>/",
        StaffPromotionDetailView.as_view(),
        name="staff-promotion-detail",
    ),
    path(
        "staff/promotions/<slug:slug>/approve/",
        StaffPromotionApproveView.as_view(),
        name="staff-promotion-approve",
    ),
    path(
        "staff/promotions/<slug:slug>/reject/",
        StaffPromotionRejectView.as_view(),
        name="staff-promotion-reject",
    ),
]
