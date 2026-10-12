"""
URL routes for `fleet`.

Public:
- GET /api/v1/instructors/
- GET /api/v1/instructors/{id}/
- GET /api/v1/vehicles/
- GET /api/v1/vehicles/{id}/

Staff:
- /api/v1/staff/instructors/
- /api/v1/staff/vehicles/
- /api/v1/staff/pickup-zones/
- /api/v1/staff/fleet/eligible-instructors/
- /api/v1/staff/fleet/eligible-vehicles/
"""

from django.urls import path

from .viewsets import (
    PublicInstructorDetailView,
    PublicInstructorListView,
    PublicVehicleDetailView,
    PublicVehicleListView,
    StaffEligibleInstructorsView,
    StaffEligibleVehiclesView,
    StaffInstructorDetailView,
    StaffInstructorListCreateView,
    StaffPickupZoneDetailView,
    StaffPickupZoneListCreateView,
    StaffVehicleDetailView,
    StaffVehicleListCreateView,
    StaffVehicleStatusView,
)

urlpatterns = [
    path("instructors/", PublicInstructorListView.as_view(), name="public-instructor-list"),
    path(
        "instructors/<int:instructor_id>/",
        PublicInstructorDetailView.as_view(),
        name="public-instructor-detail",
    ),
    path("vehicles/", PublicVehicleListView.as_view(), name="public-vehicle-list"),
    path(
        "vehicles/<int:vehicle_id>/",
        PublicVehicleDetailView.as_view(),
        name="public-vehicle-detail",
    ),
    path(
        "staff/instructors/",
        StaffInstructorListCreateView.as_view(),
        name="staff-instructor-list",
    ),
    path(
        "staff/instructors/<int:instructor_id>/",
        StaffInstructorDetailView.as_view(),
        name="staff-instructor-detail",
    ),
    path(
        "staff/vehicles/",
        StaffVehicleListCreateView.as_view(),
        name="staff-vehicle-list",
    ),
    path(
        "staff/vehicles/<int:vehicle_id>/",
        StaffVehicleDetailView.as_view(),
        name="staff-vehicle-detail",
    ),
    path(
        "staff/vehicles/<int:vehicle_id>/status/",
        StaffVehicleStatusView.as_view(),
        name="staff-vehicle-status",
    ),
    path(
        "staff/pickup-zones/",
        StaffPickupZoneListCreateView.as_view(),
        name="staff-pickup-zone-list",
    ),
    path(
        "staff/pickup-zones/<int:zone_id>/",
        StaffPickupZoneDetailView.as_view(),
        name="staff-pickup-zone-detail",
    ),
    path(
        "staff/fleet/eligible-instructors/",
        StaffEligibleInstructorsView.as_view(),
        name="staff-eligible-instructors",
    ),
    path(
        "staff/fleet/eligible-vehicles/",
        StaffEligibleVehiclesView.as_view(),
        name="staff-eligible-vehicles",
    ),
]
