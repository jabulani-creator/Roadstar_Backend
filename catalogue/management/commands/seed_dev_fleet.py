"""
Upsert the RoadStar development fleet (no photos).

Usage:
  py manage.py seed_dev_fleet
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from catalogue.golive_facts import ensure_branch, EMMASDALE_ADDRESS, EMMASDALE_HOURS, EMMASDALE_MAP_URL, PRIMARY_PHONE
from catalogue.models import Branch
from fleet.models import Vehicle, VehicleStatus, VehicleType


FLEET = [
    {
        "registration_number": "DEMO-VITZ-07",
        "name": "Vitz 2007",
        "make_model": "Toyota Vitz 2007",
        "vehicle_type": VehicleType.PASSENGER,
        "licence_class": "B",
        "transmission": "automatic",
        "public_description": "Compact Class B automatic for learner lessons.",
    },
    {
        "registration_number": "DEMO-COROLLA-A",
        "name": "Corolla Automatic",
        "make_model": "Toyota Corolla",
        "vehicle_type": VehicleType.PASSENGER,
        "licence_class": "B",
        "transmission": "automatic",
        "public_description": "Class B automatic training car.",
    },
    {
        "registration_number": "DEMO-BELTA-M",
        "name": "Belta Manual",
        "make_model": "Toyota Belta",
        "vehicle_type": VehicleType.PASSENGER,
        "licence_class": "B",
        "transmission": "manual",
        "public_description": "Class B manual saloon for everyday learner training.",
    },
    {
        "registration_number": "DEMO-COROLLA-M",
        "name": "Corolla Manual",
        "make_model": "Toyota Corolla",
        "vehicle_type": VehicleType.PASSENGER,
        "licence_class": "B",
        "transmission": "manual",
        "public_description": "Class B manual training car.",
    },
    {
        "registration_number": "DEMO-COMFORT-M",
        "name": "Toyota Comfort",
        "make_model": "Toyota Comfort (Crown Comfort / XS10)",
        "vehicle_type": VehicleType.PASSENGER,
        "licence_class": "B",
        "transmission": "manual",
        "public_description": "Class B manual Comfort — durable training saloon.",
    },
    {
        "registration_number": "DEMO-FUSO-M",
        "name": "Fuso Fighter",
        "make_model": "Mitsubishi Fuso Fighter",
        "vehicle_type": VehicleType.LIGHT_COMMERCIAL,
        "licence_class": "C1",
        "transmission": "manual",
        "public_description": "Class D / C1 manual truck for light commercial training.",
    },
    {
        "registration_number": "DEMO-HORSE-M",
        "name": "Truck Horse",
        "make_model": "Truck horse (prime mover)",
        "vehicle_type": VehicleType.HEAVY,
        "licence_class": "C",
        "transmission": "manual",
        "public_description": "Class C manual truck horse for heavy vehicle training.",
    },
]


class Command(BaseCommand):
    help = "Seed the development training fleet (no photos)."

    @transaction.atomic
    def handle(self, *args, **options):
        emmasdale = ensure_branch(
            Branch=Branch,
            canonical_slug="emmasdale",
            legacy_slugs=["demo-emmasdale"],
            defaults={
                "name": "Emmasdale",
                "address": EMMASDALE_ADDRESS,
                "landmark": "Near Great North Road",
                "map_url": EMMASDALE_MAP_URL,
                "operating_hours": EMMASDALE_HOURS,
                "primary_phone": PRIMARY_PHONE,
                "email": "roadstardrivingschool2022@gmail.com",
                "classes_available_note": "Class B (manual & automatic), Class D/C1, Class C",
                "is_active": True,
            },
        )

        keep = {row["registration_number"] for row in FLEET}
        for row in FLEET:
            Vehicle.objects.update_or_create(
                registration_number=row["registration_number"],
                defaults={
                    "name": row["name"],
                    "make_model": row["make_model"],
                    "vehicle_type": row["vehicle_type"],
                    "public_description": row["public_description"],
                    "show_on_public_page": True,
                    "branch": emmasdale,
                    "licence_class": row["licence_class"],
                    "transmission": row["transmission"],
                    "status": VehicleStatus.AVAILABLE,
                    "status_note": "",
                    "photo": "",
                },
            )
            self.stdout.write(f"  · {row['name']} ({row['transmission']}, Class {row['licence_class']})")

        # Soft-retire legacy DEMO rows (bookings may still reference them).
        retired = (
            Vehicle.objects.filter(registration_number__startswith="DEMO")
            .exclude(registration_number__in=keep)
            .update(
                status=VehicleStatus.INACTIVE,
                show_on_public_page=False,
                status_note="Retired from development fleet seed",
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Fleet ready: {len(FLEET)} vehicles · retired {retired} legacy DEMO rows · no photos"
            )
        )
