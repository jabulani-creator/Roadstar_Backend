"""
URL routes for `scheduler`.

Staff:
- POST /api/v1/scheduler/conflicts/check/
- GET/POST /api/v1/scheduler/bookings/
- GET/PATCH /api/v1/scheduler/bookings/{id}/
- POST .../confirm|reject|request-changes|cancel|complete/
- GET /api/v1/scheduler/instructors/{id}/daily/

Portal:
- GET /api/v1/scheduler/me/upcoming/
"""

from django.urls import path

from .viewsets import (
    PortalUpcomingLessonsView,
    StaffBookingCancelView,
    StaffBookingCompleteView,
    StaffBookingConfirmView,
    StaffBookingDetailView,
    StaffBookingListCreateView,
    StaffBookingRejectView,
    StaffBookingRequestChangesView,
    StaffConflictCheckView,
    StaffInstructorDailyView,
)

urlpatterns = [
    path(
        "scheduler/conflicts/check/",
        StaffConflictCheckView.as_view(),
        name="scheduler-conflict-check",
    ),
    path(
        "scheduler/bookings/",
        StaffBookingListCreateView.as_view(),
        name="scheduler-booking-list",
    ),
    path(
        "scheduler/bookings/<int:booking_id>/",
        StaffBookingDetailView.as_view(),
        name="scheduler-booking-detail",
    ),
    path(
        "scheduler/bookings/<int:booking_id>/confirm/",
        StaffBookingConfirmView.as_view(),
        name="scheduler-booking-confirm",
    ),
    path(
        "scheduler/bookings/<int:booking_id>/reject/",
        StaffBookingRejectView.as_view(),
        name="scheduler-booking-reject",
    ),
    path(
        "scheduler/bookings/<int:booking_id>/request-changes/",
        StaffBookingRequestChangesView.as_view(),
        name="scheduler-booking-request-changes",
    ),
    path(
        "scheduler/bookings/<int:booking_id>/cancel/",
        StaffBookingCancelView.as_view(),
        name="scheduler-booking-cancel",
    ),
    path(
        "scheduler/bookings/<int:booking_id>/complete/",
        StaffBookingCompleteView.as_view(),
        name="scheduler-booking-complete",
    ),
    path(
        "scheduler/instructors/<int:instructor_id>/daily/",
        StaffInstructorDailyView.as_view(),
        name="scheduler-instructor-daily",
    ),
    path(
        "scheduler/me/upcoming/",
        PortalUpcomingLessonsView.as_view(),
        name="scheduler-me-upcoming",
    ),
]
