"""
RTSA Driver Licencing schedule frozen for go-live (owner-supplied).

Pathway estimate slugs must stay stable for frontend/src/lib/cost.ts.
"""

from __future__ import annotations

from decimal import Decimal

SOURCE_NOTE = (
    "RTSA Driver Licencing schedule as supplied for go-live. "
    "Confirm at RTSA before paying; fees can change."
)
SOURCE_URL = "https://www.rtsa.org.zm/"

# (slug, title, body, fee_amount_str|None, display_order)
RTSA_ROWS: list[tuple[str, str, str, str | None, int]] = [
    (
        "demo-rtsa-provisional",
        "Provisional driving licence",
        "Requirements: medical certificate; age 18+; copy of NRC or passport. "
        "RTSA fee K117.00. " + SOURCE_NOTE,
        "117",
        1,
    ),
    (
        "demo-medical-certificate",
        "Medical certificate",
        "Medical provider fee used for Roadstar budgeting (not an RTSA charge). "
        "Required before a provisional licence. Confirm the current clinic fee when you book.",
        "200",
        2,
    ),
    (
        "demo-rtsa-practical-test",
        "Practical driver’s test",
        "RTSA fee K87.00. Typically booked 7 days after obtaining a provisional licence. "
        + SOURCE_NOTE,
        "87",
        3,
    ),
    (
        "demo-rtsa-licence-printing",
        "Printing of licence (after practical pass)",
        "RTSA fee K144.00 after passing the practical test (standard learner path). "
        + SOURCE_NOTE,
        "144",
        4,
    ),
    (
        "demo-rtsa-foreign-conversion",
        "Conversion of foreign driver’s licence",
        "Requirements: NRC or passport; valid foreign driver’s licence; authentication "
        "from issuing office or embassy; roadworthy motor vehicle for the class applied. "
        "Fee K348.00. " + SOURCE_NOTE,
        "348",
        10,
    ),
    (
        "demo-rtsa-renewal",
        "Renewal of driver’s licence",
        "Requirements: copy of NRC or passport; copy of driver’s licence. Fee K312.00. "
        + SOURCE_NOTE,
        "312",
        11,
    ),
    (
        "demo-rtsa-renewal-expired",
        "Renewal of expired driver’s licence",
        "Requirements: copy of NRC or passport; copy of driver’s licence. Fee K398.00. "
        + SOURCE_NOTE,
        "398",
        12,
    ),
    (
        "demo-rtsa-replacement-lost",
        "Replacement of lost driver’s licence",
        "Requirements: police report; general affidavit; copy of NRC or passport. "
        "Fee K144.00. If the licence is expired, the cost is K398.00. " + SOURCE_NOTE,
        "144",
        13,
    ),
    (
        "demo-rtsa-replacement-defaced",
        "Replacement of a defaced driver’s licence",
        "Requirements: police report; actual defaced licence. Fee K144.00. " + SOURCE_NOTE,
        "144",
        14,
    ),
    (
        "demo-rtsa-psv-passengers",
        "PSV endorsement — passengers (Class B, C1, C)",
        "Requirements: medical certificate with receipt from an approved government medical "
        "facility; age 25+; NRC or passport; 2 years’ experience. Provisional after theory "
        "K117.00; practical test K87.00 (7 days after provisional); printing K364.00. "
        + SOURCE_NOTE,
        "364",
        20,
    ),
    (
        "demo-rtsa-psv-dangerous-goods",
        "PSV endorsement — dangerous goods",
        "Requirements: medical certificate with receipt from an approved government medical "
        "facility; age 18+; NRC or passport; HAZCHAM certificate. Provisional after theory "
        "K117.00; practical K87.00; printing K364.00. " + SOURCE_NOTE,
        "364",
        21,
    ),
    (
        "demo-rtsa-psv-goods",
        "PSV endorsement — goods",
        "Requirements: medical certificate with receipt from an approved government medical "
        "facility; age 18+; NRC or passport. Provisional after theory K117.00; practical "
        "K87.00; printing K364.00. " + SOURCE_NOTE,
        "364",
        22,
    ),
    (
        "demo-rtsa-psv-taxi",
        "PSV endorsement — taxi only (Class B)",
        "Requirements: medical certificate with receipt from an approved government medical "
        "facility; age 18+; NRC or passport. Provisional after theory K117.00; practical "
        "K87.00; printing K364.00. Limited to 8 passengers only. " + SOURCE_NOTE,
        "364",
        23,
    ),
    (
        "demo-rtsa-instructor",
        "Driving instructor’s licence",
        "Requirements: age 25+; Zambian citizen; valid Zambian licence with PSV endorsement; "
        "defensive driving lessons; proof of First Aid ability; copy of driver’s licence; "
        "medical certificate. Test of competence K132.00; instructor’s licence K162.00. "
        + SOURCE_NOTE,
        "294",
        30,
    ),
    (
        "demo-rtsa-provisional-rider",
        "Provisional rider’s licence",
        "Requirements: medical certificate; age 16+; NRC or passport. Fee K117.00; practical "
        "test K87.00 (7 days after provisional); printing K144.00. " + SOURCE_NOTE,
        "117",
        31,
    ),
    (
        "demo-rtsa-psv-renewal",
        "Renewal of PSV driver’s licence",
        "Requirements: medical certificate; NRC or passport; copy of PSV driver’s licence. "
        "Fee K364.00. " + SOURCE_NOTE,
        "364",
        32,
    ),
    (
        "demo-rtsa-idp",
        "International driving permit",
        "Requirements: copy of valid Zambian driver’s licence; copy of valid passport; "
        "two passport-size photos. Fee K81.00. " + SOURCE_NOTE,
        "81",
        33,
    ),
]


def upsert_rtsa_rows(*, RTSAGuidance, PublishStatus, content_user, today, now) -> int:
    count = 0
    for slug, title, body, fee, order in RTSA_ROWS:
        defaults = {
            "title": title,
            "body": body,
            "fee_amount": Decimal(fee) if fee is not None else None,
            "currency": "ZMW",
            "source_url": SOURCE_URL,
            "effective_date": today,
            "last_reviewed_at": today,
            "display_order": order,
            "status": PublishStatus.APPROVED,
            "approved_by": content_user,
            "approved_at": now,
        }
        RTSAGuidance.objects.update_or_create(slug=slug, defaults=defaults)
        count += 1
    return count
