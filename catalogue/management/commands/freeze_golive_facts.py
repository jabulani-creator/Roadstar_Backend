"""
Apply go-live NAP, branch slug normalisation, RTSA fee freeze, and hide Demo testimonials.

Usage (from backend/):
  poetry run python manage.py freeze_golive_facts
  py manage.py freeze_golive_facts
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalogue.golive_facts import (
    EMMASDALE_ADDRESS,
    EMMASDALE_HOURS,
    EMMASDALE_MAP_URL,
    PRIMARY_PHONE,
    THORNPARK_ADDRESS,
    THORNPARK_HOURS,
    ensure_branch,
)
from catalogue.models import Branch
from content.golive_rtsa import upsert_rtsa_rows
from content.models import PublishStatus, RTSAGuidance, Testimonial


class Command(BaseCommand):
    help = "Freeze go-live NAP, RTSA fees, and deactivate Demo testimonials on the live DB."

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()
        now = timezone.now()
        User = get_user_model()
        content_user = (
            User.objects.filter(is_superuser=True).order_by("id").first()
            or User.objects.filter(is_staff=True).order_by("id").first()
        )

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
        thornpark = ensure_branch(
            Branch=Branch,
            canonical_slug="thornpark",
            legacy_slugs=["demo-thornpark"],
            defaults={
                "name": "Thornpark",
                "address": THORNPARK_ADDRESS,
                "landmark": "",
                "map_url": "",
                "operating_hours": THORNPARK_HOURS,
                "primary_phone": PRIMARY_PHONE,
                "email": "",
                "classes_available_note": "Ask reception which classes run at Thornpark",
                "is_active": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Branches OK: {emmasdale.slug} · {thornpark.slug} (map_url empty for Thornpark)"
            )
        )

        n = upsert_rtsa_rows(
            RTSAGuidance=RTSAGuidance,
            PublishStatus=PublishStatus,
            content_user=content_user,
            today=today,
            now=now,
        )
        self.stdout.write(self.style.SUCCESS(f"RTSA guidance rows upserted: {n}"))

        demo_qs = Testimonial.objects.filter(author_name__istartswith="Demo")
        deactivated = demo_qs.update(status=PublishStatus.INACTIVE, consent_to_publish=False)
        self.stdout.write(
            self.style.SUCCESS(f"Demo testimonials deactivated: {deactivated}")
        )

        self.stdout.write(self.style.SUCCESS("Go-live facts freeze complete."))
