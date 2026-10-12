"""
URL routes for `leads`.

Public:
- POST /api/v1/leads/

Staff:
- GET  /api/v1/staff/leads/
- GET  /api/v1/staff/leads/stats/
- GET/PATCH /api/v1/staff/leads/{id}/
- POST /api/v1/staff/leads/{id}/assign/
- POST /api/v1/staff/leads/{id}/contacted/
- POST /api/v1/staff/leads/{id}/recommended/
- POST /api/v1/staff/leads/{id}/quote-pending/
- POST /api/v1/staff/leads/{id}/lost/
- POST /api/v1/staff/leads/{id}/convert/
"""

from django.urls import path

from .viewsets import (
    PublicLeadCreateView,
    StaffLeadAssignView,
    StaffLeadContactedView,
    StaffLeadConvertView,
    StaffLeadDetailView,
    StaffLeadListView,
    StaffLeadLostView,
    StaffLeadQuotePendingView,
    StaffLeadRecommendedView,
    StaffLeadStatsView,
)

urlpatterns = [
    path("leads/", PublicLeadCreateView.as_view(), name="public-lead-create"),
    path("staff/leads/", StaffLeadListView.as_view(), name="staff-lead-list"),
    path("staff/leads/stats/", StaffLeadStatsView.as_view(), name="staff-lead-stats"),
    path(
        "staff/leads/<int:lead_id>/",
        StaffLeadDetailView.as_view(),
        name="staff-lead-detail",
    ),
    path(
        "staff/leads/<int:lead_id>/assign/",
        StaffLeadAssignView.as_view(),
        name="staff-lead-assign",
    ),
    path(
        "staff/leads/<int:lead_id>/contacted/",
        StaffLeadContactedView.as_view(),
        name="staff-lead-contacted",
    ),
    path(
        "staff/leads/<int:lead_id>/recommended/",
        StaffLeadRecommendedView.as_view(),
        name="staff-lead-recommended",
    ),
    path(
        "staff/leads/<int:lead_id>/quote-pending/",
        StaffLeadQuotePendingView.as_view(),
        name="staff-lead-quote-pending",
    ),
    path(
        "staff/leads/<int:lead_id>/lost/",
        StaffLeadLostView.as_view(),
        name="staff-lead-lost",
    ),
    path(
        "staff/leads/<int:lead_id>/convert/",
        StaffLeadConvertView.as_view(),
        name="staff-lead-convert",
    ),
]
