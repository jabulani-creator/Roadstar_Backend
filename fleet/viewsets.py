"""
HTTP endpoints for `fleet`.

Public instructor opt-in list + staff fleet management + eligibility helpers.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from config.api import RoadstarAPIView

from .permissions import IsFleetManager, IsFleetStaff
from .selectors import (
    eligible_instructors,
    eligible_vehicles,
    instructor_by_id,
    instructors_public,
    instructors_staff,
    pickup_zone_by_id,
    pickup_zones_staff,
    vehicle_by_id,
    vehicles_public,
    vehicles_staff,
)
from .serializers import (
    InstructorCreateSerializer,
    InstructorPublicSerializer,
    InstructorSerializer,
    PickupZoneSerializer,
    VehiclePublicSerializer,
    VehicleSerializer,
    VehicleStatusSerializer,
)
from .models import VehicleStatus
from .services import (
    FleetServiceError,
    create_instructor_profile,
    create_pickup_zone,
    create_vehicle,
    set_vehicle_status,
    update_instructor_profile,
    update_pickup_zone,
    update_vehicle,
)


def _service_error(exc: FleetServiceError) -> Response:
    http_status = (
        status.HTTP_403_FORBIDDEN
        if exc.code == "forbidden"
        else status.HTTP_400_BAD_REQUEST
    )
    return Response({"detail": exc.message, "code": exc.code}, status=http_status)


def _vehicle_data(vehicle, request, *, many: bool = False):
    return VehicleSerializer(vehicle, many=many, context={"request": request}).data


def _vehicle_public_data(vehicle, request, *, many: bool = False):
    return VehiclePublicSerializer(vehicle, many=many, context={"request": request}).data


def _instructor_data(profile, request, *, many: bool = False):
    return InstructorSerializer(profile, many=many, context={"request": request}).data


def _instructor_public_data(profile, request, *, many: bool = False):
    return InstructorPublicSerializer(
        profile, many=many, context={"request": request}
    ).data


# --- Public ---


class PublicInstructorListView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(
            _instructor_public_data(instructors_public(), request, many=True)
        )


class PublicInstructorDetailView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, instructor_id: int) -> Response:
        profile = instructor_by_id(instructor_id=instructor_id)
        if profile is None or not profile.show_on_public_page:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_instructor_public_data(profile, request))


class PublicVehicleListView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(_vehicle_public_data(vehicles_public(), request, many=True))


class PublicVehicleDetailView(RoadstarAPIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, vehicle_id: int) -> Response:
        vehicle = vehicle_by_id(vehicle_id=vehicle_id)
        if (
            vehicle is None
            or not vehicle.show_on_public_page
            or vehicle.status != VehicleStatus.AVAILABLE
        ):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_vehicle_public_data(vehicle, request))


# --- Staff: instructors ---


class StaffInstructorListCreateView(RoadstarAPIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsFleetStaff()]
        return [IsAuthenticated(), IsFleetManager()]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status") or None
        return Response(
            _instructor_data(instructors_staff(status=status_filter), request, many=True)
        )

    def post(self, request: Request) -> Response:
        serializer = InstructorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if not data.get("display_name"):
            data.pop("display_name", None)
        try:
            profile = create_instructor_profile(actor=request.user, data=data)
        except FleetServiceError as exc:
            return _service_error(exc)
        return Response(
            _instructor_data(profile, request), status=status.HTTP_201_CREATED
        )


class StaffInstructorDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsFleetStaff]

    def get(self, request: Request, instructor_id: int) -> Response:
        profile = instructor_by_id(instructor_id=instructor_id)
        if profile is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_instructor_data(profile, request))

    def patch(self, request: Request, instructor_id: int) -> Response:
        if not IsFleetManager().has_permission(request, self):
            return Response(
                {"detail": "Fleet manager access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        profile = instructor_by_id(instructor_id=instructor_id)
        if profile is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = InstructorSerializer(
            profile, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        try:
            profile = update_instructor_profile(
                actor=request.user,
                profile=profile,
                data=serializer.validated_data,
            )
        except FleetServiceError as exc:
            return _service_error(exc)
        return Response(_instructor_data(profile, request))


class StaffEligibleInstructorsView(RoadstarAPIView):
    """GET /api/v1/staff/fleet/eligible-instructors/?licence_class=B&transmission=manual"""

    permission_classes = [IsAuthenticated, IsFleetStaff]

    def get(self, request: Request) -> Response:
        licence_class = request.query_params.get("licence_class") or ""
        transmission = request.query_params.get("transmission") or ""
        branch = request.query_params.get("branch")
        branch_id = int(branch) if branch and branch.isdigit() else None
        qs = eligible_instructors(
            licence_class=licence_class,
            transmission=transmission,
            branch_id=branch_id,
        )
        return Response(_instructor_data(qs, request, many=True))


# --- Staff: vehicles ---


class StaffVehicleListCreateView(RoadstarAPIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsFleetStaff()]
        return [IsAuthenticated(), IsFleetManager()]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status") or None
        return Response(
            _vehicle_data(vehicles_staff(status=status_filter), request, many=True)
        )

    def post(self, request: Request) -> Response:
        serializer = VehicleSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        try:
            vehicle = create_vehicle(
                actor=request.user, data=serializer.validated_data
            )
        except FleetServiceError as exc:
            return _service_error(exc)
        return Response(
            _vehicle_data(vehicle, request), status=status.HTTP_201_CREATED
        )


class StaffVehicleDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsFleetStaff]

    def get(self, request: Request, vehicle_id: int) -> Response:
        vehicle = vehicle_by_id(vehicle_id=vehicle_id)
        if vehicle is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_vehicle_data(vehicle, request))

    def patch(self, request: Request, vehicle_id: int) -> Response:
        if not IsFleetManager().has_permission(request, self):
            return Response(
                {"detail": "Fleet manager access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        vehicle = vehicle_by_id(vehicle_id=vehicle_id)
        if vehicle is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = VehicleSerializer(
            vehicle, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        try:
            vehicle = update_vehicle(
                actor=request.user,
                vehicle=vehicle,
                data=serializer.validated_data,
            )
        except FleetServiceError as exc:
            return _service_error(exc)
        return Response(_vehicle_data(vehicle, request))


class StaffVehicleStatusView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsFleetManager]

    def post(self, request: Request, vehicle_id: int) -> Response:
        vehicle = vehicle_by_id(vehicle_id=vehicle_id)
        if vehicle is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        body = VehicleStatusSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            vehicle = set_vehicle_status(
                actor=request.user,
                vehicle=vehicle,
                status=body.validated_data["status"],
                note=body.validated_data.get("note", ""),
            )
        except FleetServiceError as exc:
            return _service_error(exc)
        return Response(_vehicle_data(vehicle, request))


class StaffEligibleVehiclesView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsFleetStaff]

    def get(self, request: Request) -> Response:
        licence_class = request.query_params.get("licence_class") or ""
        transmission = request.query_params.get("transmission") or ""
        branch = request.query_params.get("branch")
        branch_id = int(branch) if branch and branch.isdigit() else None
        qs = eligible_vehicles(
            licence_class=licence_class,
            transmission=transmission,
            branch_id=branch_id,
        )
        return Response(_vehicle_data(qs, request, many=True))


# --- Staff: pickup zones ---


class StaffPickupZoneListCreateView(RoadstarAPIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated(), IsFleetStaff()]
        return [IsAuthenticated(), IsFleetManager()]

    def get(self, request: Request) -> Response:
        branch = request.query_params.get("branch")
        branch_id = int(branch) if branch and branch.isdigit() else None
        active_only = request.query_params.get("active") in {"1", "true", "yes"}
        qs = pickup_zones_staff(branch_id=branch_id, active_only=active_only)
        return Response(PickupZoneSerializer(qs, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PickupZoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            zone = create_pickup_zone(
                actor=request.user, data=serializer.validated_data
            )
        except FleetServiceError as exc:
            return _service_error(exc)
        return Response(PickupZoneSerializer(zone).data, status=status.HTTP_201_CREATED)


class StaffPickupZoneDetailView(RoadstarAPIView):
    permission_classes = [IsAuthenticated, IsFleetStaff]

    def get(self, request: Request, zone_id: int) -> Response:
        zone = pickup_zone_by_id(zone_id=zone_id)
        if zone is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PickupZoneSerializer(zone).data)

    def patch(self, request: Request, zone_id: int) -> Response:
        if not IsFleetManager().has_permission(request, self):
            return Response(
                {"detail": "Fleet manager access required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        zone = pickup_zone_by_id(zone_id=zone_id)
        if zone is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PickupZoneSerializer(zone, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            zone = update_pickup_zone(
                actor=request.user,
                zone=zone,
                data=serializer.validated_data,
            )
        except FleetServiceError as exc:
            return _service_error(exc)
        return Response(PickupZoneSerializer(zone).data)
