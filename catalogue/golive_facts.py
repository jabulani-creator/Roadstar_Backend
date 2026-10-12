"""
Canonical go-live NAP + branch facts (shared by seed_demo and freeze_golive_facts).
"""

from __future__ import annotations

EMMASDALE_ADDRESS = "Plot No. 238 Vubu Road, Emmasdale, Lusaka, Zambia, 10101"
EMMASDALE_MAP_URL = (
    "https://maps.google.com/?q=Plot+No.+238+Vubu+Road+Emmasdale+Lusaka+Zambia+10101"
)
EMMASDALE_HOURS = "Mon–Fri 08:00–17:00 · Sat 08:00–13:00 · Sun closed"
PRIMARY_PHONE = "+260975072617"

THORNPARK_ADDRESS = "Ask us for directions when you enquire"
THORNPARK_HOURS = "Ask us when you enquire"


def ensure_branch(*, Branch, canonical_slug: str, legacy_slugs: list[str], defaults: dict):
    """Create or update a branch under the canonical slug; retire legacy demo slugs."""
    branch = Branch.objects.filter(slug=canonical_slug).first()
    if not branch:
        for legacy in legacy_slugs:
            branch = Branch.objects.filter(slug=legacy).first()
            if branch:
                branch.slug = canonical_slug
                break

    if branch:
        for key, value in defaults.items():
            setattr(branch, key, value)
        branch.save()
    else:
        branch = Branch.objects.create(slug=canonical_slug, **defaults)

    Branch.objects.filter(slug__in=legacy_slugs).exclude(pk=branch.pk).update(is_active=False)
    return branch
