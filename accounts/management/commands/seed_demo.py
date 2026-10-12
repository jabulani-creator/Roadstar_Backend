"""
Seed demo data across all Roadstar domains for local API testing.

Usage:
  poetry run python manage.py seed_demo
  poetry run python manage.py seed_demo --reset

All demo users share password: DemoPass123!
Emails use the @roadstar.demo domain so reset can clear them safely.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from accounts.models import StaffRole, StaffRoleAssignment
from catalogue.models import (
    Branch,
    Course,
    CourseLevel,
    LicenceClass,
    Promotion,
    PublishStatus as CatPublish,
    Transmission,
)
from commerce.models import (
    EntitlementAccount,
    EntitlementEntry,
    Payment,
    PaymentMethod,
    PaymentStatus,
    Receipt,
)
from commerce.services import record_manual_payment
from content.models import (
    Article,
    ArticleType,
    FAQ,
    FAQCategory,
    PublishStatus as ContentPublish,
    Resource,
    ResourceCategory,
    ResourceVisibility,
    RTSAGuidance,
    Testimonial,
)
from fleet.models import (
    InstructorProfile,
    InstructorStatus,
    PickupZone,
    Vehicle,
    VehicleStatus,
    VehicleType,
)
from leads.models import Lead, LeadChannel, LeadStatus, ReferralSource
from learning.models import (
    Attempt,
    AttemptStatus,
    PracticePaper,
    PracticePaperQuestion,
    PublishStatus as LearnPublish,
    Question,
    StudyDocument,
    Topic,
)
from learning.services import approve_practice_paper, start_attempt, submit_attempt
from scheduler.models import BookingStatus, LessonBooking
from scheduler.services import confirm_booking, create_schedule_request
from students.models import (
    ConsentRecord,
    ConsentType,
    DocumentChecklistStatus,
    Student,
    StudentStatus,
)

User = get_user_model()

DEMO_PASSWORD = "DemoPass123!"
DEMO_DOMAIN = "roadstar.demo"


class Command(BaseCommand):
    help = "Seed local demo data so Swagger / API testing has real records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previous @roadstar.demo data before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset_demo()
            self.stdout.write(self.style.WARNING("Cleared previous demo data."))

        owner = self._user(
            "owner@roadstar.demo",
            "Morgan",
            "Moyo",
            roles=[StaffRole.OWNER],
            is_superuser=True,
        )
        reception = self._user(
            "reception@roadstar.demo",
            "Thandi",
            "Banda",
            roles=[StaffRole.RECEPTION],
        )
        content = self._user(
            "content@roadstar.demo",
            "Chipo",
            "Phiri",
            roles=[StaffRole.CONTENT],
        )
        finance = self._user(
            "finance@roadstar.demo",
            "James",
            "Zulu",
            roles=[StaffRole.FINANCE],
        )
        instructor_user = self._user(
            "instructor@roadstar.demo",
            "Grace",
            "Mwale",
            roles=[StaffRole.INSTRUCTOR],
            public=True,
            public_title="Senior Instructor",
            public_bio="Patient Class B instructor based at Emmasdale.",
        )
        louise_user = self._user(
            "louise@roadstar.demo",
            "Louise",
            "Banda",
            roles=[StaffRole.INSTRUCTOR],
            public=True,
            public_title="Class B Instructor",
            public_bio="Patient instructor for nervous beginners.",
        )

        emmasdale, thornpark = self._branches()
        courses = self._courses(owner, emmasdale, thornpark)
        self._promotion(owner, courses[0])
        self._content(content)
        leads = self._leads(emmasdale, courses[0])
        learner, learner_pending = self._students(courses[0], emmasdale, leads[0])
        self._commerce(finance, learner, courses[0])
        instructor, vehicles, zone = self._fleet(
            instructor_user, emmasdale, thornpark, reception, louise_user
        )
        self._scheduler(reception, learner, courses[0], instructor, vehicles[0], zone)
        self._learning(content, learner)

        self.stdout.write(self.style.SUCCESS("\nDemo seed complete.\n"))
        self.stdout.write("Login password for all demo users:")
        self.stdout.write(f"  {DEMO_PASSWORD}\n")
        self.stdout.write("Accounts:")
        for email, label in [
            ("owner@roadstar.demo", "Owner / admin + Django admin"),
            ("reception@roadstar.demo", "Reception / scheduler"),
            ("content@roadstar.demo", "Content / learning editor"),
            ("finance@roadstar.demo", "Finance"),
            ("instructor@roadstar.demo", "Instructor (Grace)"),
            ("louise@roadstar.demo", "Instructor (Louise)"),
            ("learner@roadstar.demo", "Student (paid, has credits)"),
            ("learner2@roadstar.demo", "Student (registered, unpaid)"),
        ]:
            self.stdout.write(f"  {email:28}  {label}")
        self.stdout.write("\nTry:")
        self.stdout.write("  POST /api/v1/auth/token/  {\"email\",\"password\"}")
        self.stdout.write("  GET  /api/v1/courses/")
        self.stdout.write("  GET  /api/docs/\n")

    # --- reset ---

    def _reset_demo(self):
        # Order matters for FKs / PROTECT.
        Attempt.objects.filter(student__email__endswith=f"@{DEMO_DOMAIN}").delete()
        LessonBooking.objects.filter(student__email__endswith=f"@{DEMO_DOMAIN}").delete()
        Receipt.objects.filter(payment__student__email__endswith=f"@{DEMO_DOMAIN}").delete()
        EntitlementEntry.objects.filter(
            account__student__email__endswith=f"@{DEMO_DOMAIN}"
        ).delete()
        Payment.objects.filter(student__email__endswith=f"@{DEMO_DOMAIN}").delete()
        EntitlementAccount.objects.filter(
            student__email__endswith=f"@{DEMO_DOMAIN}"
        ).delete()
        ConsentRecord.objects.filter(student__email__endswith=f"@{DEMO_DOMAIN}").delete()
        Student.objects.filter(email__endswith=f"@{DEMO_DOMAIN}").delete()
        Lead.objects.filter(email__endswith=f"@{DEMO_DOMAIN}").delete()
        PracticePaperQuestion.objects.filter(
            paper__slug__startswith="demo-"
        ).delete()
        PracticePaper.objects.filter(slug__startswith="demo-").delete()
        Question.objects.filter(prompt__startswith="[DEMO]").delete()
        StudyDocument.objects.filter(slug__startswith="demo-").delete()
        Topic.objects.filter(slug__startswith="demo-").delete()
        InstructorProfile.objects.filter(user__email__endswith=f"@{DEMO_DOMAIN}").delete()
        # Pytest / local fixture instructors must not pollute the public site.
        InstructorProfile.objects.exclude(
            user__email__endswith=f"@{DEMO_DOMAIN}"
        ).filter(show_on_public_page=True).update(show_on_public_page=False)
        Vehicle.objects.filter(registration_number__startswith="DEMO").delete()
        PickupZone.objects.filter(slug__startswith="demo-").delete()
        Testimonial.objects.filter(author_name__startswith="Demo ").delete()
        FAQ.objects.filter(question__startswith="[DEMO]").delete()
        Article.objects.filter(slug__startswith="demo-").delete()
        RTSAGuidance.objects.filter(slug__startswith="demo-").delete()
        Resource.objects.filter(slug__startswith="demo-").delete()
        ResourceCategory.objects.filter(slug__startswith="demo-").delete()
        Promotion.objects.filter(slug__startswith="demo-").delete()
        Course.objects.filter(slug__startswith="demo-").delete()
        Branch.objects.filter(slug__startswith="demo-").delete()
        StaffRoleAssignment.objects.filter(
            user__email__endswith=f"@{DEMO_DOMAIN}"
        ).delete()
        User.objects.filter(email__endswith=f"@{DEMO_DOMAIN}").delete()

    # --- helpers ---

    def _user(
        self,
        email,
        first,
        last,
        *,
        roles,
        is_superuser=False,
        public=False,
        public_title="",
        public_bio="",
    ):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first,
                "last_name": last,
                "is_staff": True,
                "is_superuser": is_superuser,
                "phone": "+260970000000",
                "show_on_public_staff_list": public,
                "public_title": public_title,
                "public_bio": public_bio,
            },
        )
        user.set_password(DEMO_PASSWORD)
        user.first_name = first
        user.last_name = last
        user.is_staff = True
        user.is_superuser = is_superuser or user.is_superuser
        user.show_on_public_staff_list = public
        user.public_title = public_title
        user.public_bio = public_bio
        user.save()
        for role in roles:
            StaffRoleAssignment.objects.get_or_create(user=user, role=role)
        return user

    def _branches(self):
        from catalogue.golive_facts import (
            EMMASDALE_ADDRESS,
            EMMASDALE_HOURS,
            EMMASDALE_MAP_URL,
            PRIMARY_PHONE,
            THORNPARK_ADDRESS,
            THORNPARK_HOURS,
            ensure_branch,
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
                "email": "emmasdale@roadstar.demo",
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
                "email": "thornpark@roadstar.demo",
                "classes_available_note": "Ask reception which classes run at Thornpark",
                "is_active": True,
            },
        )
        return emmasdale, thornpark

    def _courses(self, owner, emmasdale, thornpark):
        """Phase 1 catalogue — owner-supplied draft prices (confirm before go-live)."""
        now = timezone.now()
        ladder = [
            (CourseLevel.BEGINNER_FULL, "Full", 20),
            (CourseLevel.STANDARD, "Standard", 15),
            (CourseLevel.HALF, "Half", 10),
            (CourseLevel.REFRESHER, "Refresher", 7),
            (CourseLevel.TEST_PREP, "Test preparation", 1),
        ]
        class_specs = [
            (
                LicenceClass.CLASS_B,
                "B",
                Transmission.BOTH,
                3500,
                18,
                {
                    CourseLevel.BEGINNER_FULL: "2600",
                    CourseLevel.STANDARD: "2450",
                    CourseLevel.HALF: "2250",
                    CourseLevel.REFRESHER: "1950",
                    CourseLevel.TEST_PREP: "800",
                },
                "For everyday motorists. Manual and automatic available.",
            ),
            (
                LicenceClass.CLASS_C1,
                "C1",
                Transmission.MANUAL,
                7500,
                18,
                {
                    CourseLevel.BEGINNER_FULL: "3500",
                    CourseLevel.STANDARD: "3200",
                    CourseLevel.HALF: "2950",
                    CourseLevel.REFRESHER: "2550",
                    CourseLevel.TEST_PREP: "1200",
                },
                "Class D / C1 light commercial pathway. Manual.",
            ),
            (
                LicenceClass.CLASS_C,
                "C",
                Transmission.MANUAL,
                16000,
                18,
                {
                    CourseLevel.BEGINNER_FULL: "4500",
                    CourseLevel.STANDARD: "4300",
                    CourseLevel.HALF: "4000",
                    CourseLevel.REFRESHER: "3600",
                    CourseLevel.TEST_PREP: "1200",
                },
                "Class C heavy vehicle pathway. Manual.",
            ),
        ]
        courses = []
        for licence, code, transmission, gvm, age, prices, class_blurb in class_specs:
            for level, label, days in ladder:
                slug = f"demo-class-{code.lower()}-{level.replace('_', '-')}"
                name = f"Class {code if code != 'C1' else 'D / C1'} — {label}"
                if level == CourseLevel.TEST_PREP:
                    summary = (
                        f"{label} ({days} day). Prepares you for the test — "
                        "not a guarantee that you will pass."
                    )
                else:
                    summary = f"{label} package · {days} days. {class_blurb}"
                course, _ = Course.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name": name,
                        "summary": summary[:255],
                        "description": (
                            f"{name}. Duration {days} days. "
                            f"Minimum age {age}. Max GVM {gvm} kg where applicable. "
                            "Roadstar tuition only — RTSA and medical fees are separate. "
                            "Draft prices pending management confirmation before public launch."
                        ),
                        "licence_class": licence,
                        "transmission": transmission,
                        "level": level,
                        "duration_days": days,
                        "min_age": age,
                        "max_gvm_kg": gvm,
                        "lesson_count": days,
                        "lesson_unit_minutes": 60,
                        "price_amount": Decimal(prices[level]),
                        "currency": "ZMW",
                        "show_price": True,
                        "inclusions": (
                            "All practical behind-the-wheel lessons\n"
                            "Vehicle use for every lesson\n"
                            "Certified instructor fees\n"
                            "Progress notes after each session\n"
                            "Test preparation and readiness guidance\n"
                            "Student registration support"
                        ),
                        "exclusions": (
                            "RTSA statutory fees (paid directly to RTSA)\n"
                            "Extra lessons beyond the package\n"
                            "Transport to/from lessons unless pickup is arranged"
                        ),
                        "status": CatPublish.APPROVED,
                        "price_updated_at": now,
                        "approved_by": owner,
                        "approved_at": now,
                    },
                )
                course.branches.set([emmasdale, thornpark])
                courses.append(course)
        return courses

    def _promotion(self, owner, course):
        now = timezone.now()
        promo, _ = Promotion.objects.update_or_create(
            slug="demo-july-starter",
            defaults={
                "title": "Demo July Starter Offer",
                "summary": "Limited demo promotion for testing expiry rules.",
                "discount_label": "10% off starter packages",
                "starts_at": now - timedelta(days=2),
                "ends_at": now + timedelta(days=28),
                "status": CatPublish.APPROVED,
            },
        )
        promo.courses.set([course])
        return promo

    def _content(self, content_user):
        now = timezone.now()
        today = timezone.localdate()
        faqs = [
            (
                "[DEMO] I've never driven before. Can I still join?",
                "Absolutely. Most of our students have never touched a steering wheel before. "
                "The Full Course is designed exactly for you. We start in a quiet area, at your "
                "pace. No pressure. No shouting.",
                FAQCategory.ENROLMENT,
                1,
            ),
            (
                "[DEMO] Do I need a provisional licence before I start lessons?",
                "No. You can start lessons with RoadStar before you have a provisional licence. "
                "However, you will need a provisional licence before you can take the RTSA "
                "theory test. We'll guide you through that step when you're ready.",
                FAQCategory.ENROLMENT,
                2,
            ),
            (
                "[DEMO] What documents do I need to register?",
                "You'll need your NRC or passport, a passport-sized photo, your phone number "
                "and email address. Proof of residence is optional but helpful. We'll send a "
                "full checklist when you register.",
                FAQCategory.ENROLMENT,
                3,
            ),
            (
                "[DEMO] How do I know which course is right for me?",
                "Use Find Your Course — it recommends a package based on your experience, "
                "licence class, transmission, and location. Or WhatsApp us and we'll help you decide.",
                FAQCategory.ENROLMENT,
                4,
            ),
            (
                "[DEMO] How much is the full cost?",
                "Course fees depend on the package you choose — see Courses & Fees for current "
                "tuition. RTSA statutory fees (provisional, tests, licence printing) plus medical "
                "are separate and typically total around K548 when all four pathway charges apply.",
                FAQCategory.COURSES,
                10,
            ),
            (
                "[DEMO] Are there any hidden fees?",
                "No. Every course shows what's included and what's not. Additional costs are RTSA "
                "statutory fees (paid to RTSA), optional extra lessons beyond your package, and "
                "transport/pickup fees where arranged.",
                FAQCategory.COURSES,
                11,
            ),
            (
                "[DEMO] Can I pay in instalments?",
                "Yes. We offer a deposit + instalment plan. Contact us on WhatsApp to discuss a "
                "payment plan that works for you.",
                FAQCategory.COURSES,
                12,
            ),
            (
                "[DEMO] Do you accept mobile money?",
                "Yes. We accept MTN Mobile Money, Airtel Money, and Zamtel Kwacha. We also accept "
                "bank transfer and cash at our Emmasdale office.",
                FAQCategory.COURSES,
                13,
            ),
            (
                "[DEMO] How long is each lesson?",
                "Lesson duration varies by course and preference. We offer flexible blocks "
                "(for example 30 / 60 / 90 minutes). We'll agree the right block during enrolment.",
                FAQCategory.LESSONS,
                20,
            ),
            (
                "[DEMO] When can I attend lessons?",
                "We offer lessons Monday to Saturday, with morning, daytime, and evening slots "
                "where capacity allows. Reception helps arrange times that fit your schedule.",
                FAQCategory.LESSONS,
                21,
            ),
            (
                "[DEMO] Can I choose my instructor?",
                "You can request a specific instructor when you book. We'll do our best to "
                "accommodate you. All our instructors are certified and chosen for patience.",
                FAQCategory.LESSONS,
                22,
            ),
            (
                "[DEMO] Do you offer pickup from my home or office?",
                "Yes, within approved pickup zones. There may be a travel fee depending on your "
                "location. Contact us to confirm if your area is covered.",
                FAQCategory.LESSONS,
                23,
            ),
            (
                "[DEMO] Does completing a Roadstar course guarantee I will pass?",
                "No. RoadStar prepares you for the test. RTSA administers the test and decides "
                "the outcome. We will give you an honest assessment of your readiness before you book.",
                FAQCategory.RTSA,
                30,
            ),
            (
                "[DEMO] What is the difference between Roadstar training and RTSA testing?",
                "RoadStar teaches you to drive and provides the vehicle, instructor, and structured "
                "lessons. RTSA registers learners, administers tests, and issues the licence. "
                "We guide you through the process, but the licence is RTSA's decision.",
                FAQCategory.RTSA,
                31,
            ),
            (
                "[DEMO] What is the difference between Class B, C1, and C?",
                "Class B is the standard passenger-car licence. Class C1 is light commercial. "
                "Class C is heavy vehicle. You must hold Class B before training for C1 or C.",
                FAQCategory.RTSA,
                32,
            ),
            (
                "[DEMO] Where are you located?",
                "Emmasdale (main): Plot No. 238, Vubu Road, Lusaka. Thornpark address confirmation "
                "is in progress — ask when you enquire. Class C1/C training is based at Emmasdale.",
                FAQCategory.GENERAL,
                40,
            ),
            (
                "[DEMO] Which number should I call or WhatsApp?",
                "Our primary enrolment line is +260 975 072617. This is the fastest way to reach us.",
                FAQCategory.GENERAL,
                41,
            ),
            (
                "[DEMO] Are your instructors certified?",
                "Yes. RoadStar instructors are certified and experienced. We choose instructors "
                "for their patience as much as their skill.",
                FAQCategory.GENERAL,
                42,
            ),
            (
                "[DEMO] What if I'm a very nervous driver?",
                "You're not alone. Many students are nervous when they start. Our instructors are "
                "trained to be patient and reassuring. We go at your pace. No shouting. No rushing.",
                FAQCategory.LESSONS,
                24,
            ),
            (
                "[DEMO] Does a one-day test preparation guarantee I will pass?",
                "No. Test preparation helps you practise for the test. Licence decisions belong "
                "to RTSA. RoadStar does not guarantee a pass.",
                FAQCategory.RTSA,
                33,
            ),
        ]
        for question, answer, category, order in faqs:
            FAQ.objects.update_or_create(
                question=question,
                defaults={
                    "answer": answer,
                    "category": category,
                    "display_order": order,
                    "status": ContentPublish.APPROVED,
                    "approved_by": content_user,
                    "approved_at": now,
                },
            )

        from content.golive_rtsa import upsert_rtsa_rows

        upsert_rtsa_rows(
            RTSAGuidance=RTSAGuidance,
            PublishStatus=ContentPublish,
            content_user=content_user,
            today=today,
            now=now,
        )
        Article.objects.update_or_create(
            slug="demo-how-enrolment-works",
            defaults={
                "title": "Demo: How enrolment works",
                "summary": "Step-by-step demo guide.",
                "body": "1) Find your course\n2) Register\n3) Pay\n4) Book lessons with reception.",
                "article_type": ArticleType.GUIDE,
                "status": ContentPublish.APPROVED,
                "approved_by": content_user,
                "approved_at": timezone.now(),
            },
        )
        cat, _ = ResourceCategory.objects.update_or_create(
            slug="demo-checklists",
            defaults={"name": "Demo Checklists"},
        )
        Resource.objects.update_or_create(
            slug="demo-enrolment-checklist",
            defaults={
                "title": "Demo enrolment checklist",
                "summary": "What to bring on day one.",
                "category": cat,
                "file_url": "https://example.com/demo-enrolment-checklist.pdf",
                "visibility": ResourceVisibility.PUBLIC,
                "status": ContentPublish.APPROVED,
                "approved_by": content_user,
                "approved_at": timezone.now(),
            },
        )
        course = Course.objects.filter(slug="demo-class-b-beginner-full").first()
        testimonials = [
            (
                "Demo Chanda M.",
                "I was nervous about learning to drive. The instructor was patient "
                "and explained everything clearly. I felt safe and ready. I passed.",
                "Class B Graduate · Emmasdale",
            ),
            (
                "Demo Mweemba K.",
                "Louise was so patient with me. I was terrified of driving, but after "
                "a few lessons I felt ready for my RTSA test.",
                "Class B Learner · Emmasdale",
            ),
            (
                "Demo Mutinta S.",
                "I got my licence years ago but never drove. I was too scared. The "
                "refresher course gave me my confidence back. Now I drive my kids to school every day.",
                "Class B Refresher · Thornpark",
            ),
            (
                "Demo Joseph P.",
                "I needed my Class C1 for work. The training was thorough and professional. "
                "I felt prepared and passed my test.",
                "Class C1 Graduate · Emmasdale",
            ),
            (
                "Demo Bwalya T.",
                "They fit my lessons around my work schedule. Early mornings and Saturdays. "
                "That's why I chose RoadStar and I'm glad I did.",
                "Class B Standard · Emmasdale",
            ),
        ]
        for name, quote, role in testimonials:
            Testimonial.objects.update_or_create(
                author_name=name,
                defaults={
                    "quote": quote,
                    "author_role": role,
                    "related_course": course,
                    "rating": 5,
                    # Demo quotes stay inactive — only consent-backed real quotes go public.
                    "consent_to_publish": False,
                    "status": ContentPublish.INACTIVE,
                    "approved_by": content_user,
                    "approved_at": timezone.now(),
                },
            )

    def _leads(self, branch, course):
        lead_new, _ = Lead.objects.update_or_create(
            phone="+260970100001",
            defaults={
                "full_name": "Demo Prospect New",
                "email": "prospect.new@roadstar.demo",
                "experience_level": "beginner",
                "licence_class": "B",
                "transmission": "manual",
                "preferred_branch": branch,
                "preferred_schedule": "Saturday mornings",
                "message": "Want to start next month.",
                "interested_course": course,
                "channel": LeadChannel.FIND_YOUR_COURSE,
                "referral_source": ReferralSource.WEBSITE,
                "whatsapp_summary": "Hi Roadstar, Class B manual beginner, Emmasdale, Saturdays.",
                "status": LeadStatus.NEW,
            },
        )
        lead_hot, _ = Lead.objects.update_or_create(
            phone="+260970100002",
            defaults={
                "full_name": "Demo Prospect Hot",
                "email": "prospect.hot@roadstar.demo",
                "experience_level": "beginner",
                "licence_class": "B",
                "transmission": "manual",
                "preferred_branch": branch,
                "interested_course": course,
                "recommended_course": course,
                "channel": LeadChannel.CONTACT_FORM,
                "referral_source": ReferralSource.WHATSAPP,
                "status": LeadStatus.QUOTE_PENDING,
            },
        )
        return [lead_new, lead_hot]

    def _students(self, course, branch, source_lead):
        # Paid learner
        user, _ = User.objects.get_or_create(
            email="learner@roadstar.demo",
            defaults={
                "first_name": "Lydia",
                "last_name": "Chanda",
                "phone": "+260970300001",
                "is_staff": False,
            },
        )
        user.set_password(DEMO_PASSWORD)
        user.is_staff = False
        user.save()
        student, _ = Student.objects.update_or_create(
            email="learner@roadstar.demo",
            defaults={
                "user": user,
                "full_name": "Lydia Chanda",
                "phone": "+260970300001",
                "selected_course": course,
                "preferred_branch": branch,
                "preferred_schedule": "Weekday evenings",
                "referral_source": "website",
                "source_lead": source_lead,
                "status": StudentStatus.ACTIVE,
                "checklist_status": DocumentChecklistStatus.PARTIAL,
                "has_nrc_copy": True,
                "has_proof_of_payment": True,
            },
        )
        for ctype in (ConsentType.TERMS, ConsentType.PRIVACY):
            ConsentRecord.objects.update_or_create(
                student=student,
                consent_type=ctype,
                defaults={
                    "accepted": True,
                    "accepted_at": timezone.now(),
                    "recorded_by": user,
                },
            )

        # Unpaid learner
        user2, _ = User.objects.get_or_create(
            email="learner2@roadstar.demo",
            defaults={
                "first_name": "Peter",
                "last_name": "Mwansa",
                "phone": "+260970300002",
                "is_staff": False,
            },
        )
        user2.set_password(DEMO_PASSWORD)
        user2.is_staff = False
        user2.save()
        student2, _ = Student.objects.update_or_create(
            email="learner2@roadstar.demo",
            defaults={
                "user": user2,
                "full_name": "Peter Mwansa",
                "phone": "+260970300002",
                "selected_course": course,
                "preferred_branch": branch,
                "status": StudentStatus.REGISTERED,
                "checklist_status": DocumentChecklistStatus.NOT_STARTED,
            },
        )
        for ctype in (ConsentType.TERMS, ConsentType.PRIVACY):
            ConsentRecord.objects.update_or_create(
                student=student2,
                consent_type=ctype,
                defaults={
                    "accepted": True,
                    "accepted_at": timezone.now(),
                    "recorded_by": user2,
                },
            )
        return student, student2

    def _commerce(self, finance_user, student, course):
        # Idempotent: if student already has a succeeded payment for this course, skip.
        existing = Payment.objects.filter(
            student=student,
            course=course,
            status=PaymentStatus.SUCCEEDED,
            purpose__startswith="[DEMO]",
        ).first()
        if existing:
            return existing

        payment = record_manual_payment(
            actor=finance_user,
            student_id=student.id,
            course_id=course.id,
            amount=course.price_amount or Decimal("4500.00"),
            method=PaymentMethod.CASH,
            credits_purchased=course.lesson_count or 20,
            provider_reference="DEMO-CASH-001",
            purpose="[DEMO] Class B Manual package",
        )
        return payment

    def _fleet(self, instructor_user, emmasdale, thornpark, reception, louise_user=None):
        profile, _ = InstructorProfile.objects.update_or_create(
            user=instructor_user,
            defaults={
                "display_name": "Grace Mwale",
                "employee_code": "INS-DEMO-01",
                "home_branch": emmasdale,
                "licence_classes": "B,C1",
                "transmission": "both",
                "credentials_note": "Senior certified instructor | Specialty: Class C1 & professional drivers",
                "status": InstructorStatus.ACTIVE,
                "show_on_public_page": True,
                "public_bio": (
                    "I believe in calm, patient instruction. No shouting. "
                    "We go at your pace until you feel ready. That's my promise."
                ),
                "notes": "[DEMO] Grace - Class C1 focus",
            },
        )
        if louise_user is not None:
            InstructorProfile.objects.update_or_create(
                user=louise_user,
                defaults={
                    "display_name": "Louise Banda",
                    "employee_code": "INS-DEMO-02",
                    "home_branch": emmasdale,
                    "licence_classes": "B",
                    "transmission": "both",
                    "credentials_note": "Certified RTSA instructor | Specialty: nervous beginners",
                    "status": InstructorStatus.ACTIVE,
                    "show_on_public_page": True,
                    "public_bio": (
                        "I've taught hundreds of learners who were terrified on their first "
                        "lesson. By the third, they're smiling. That's the moment I do this for."
                    ),
                    "notes": "[DEMO] Louise - nervous beginners",
                },
            )
        # RoadStar training fleet (no photos — upload in CMS).
        fleet_specs = [
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
        vehicles: list[Vehicle] = []
        keep_regs = {spec["registration_number"] for spec in fleet_specs}
        for spec in fleet_specs:
            vehicle, _ = Vehicle.objects.update_or_create(
                registration_number=spec["registration_number"],
                defaults={
                    "name": spec["name"],
                    "make_model": spec["make_model"],
                    "vehicle_type": spec["vehicle_type"],
                    "public_description": spec["public_description"],
                    "show_on_public_page": True,
                    "branch": emmasdale,
                    "licence_class": spec["licence_class"],
                    "transmission": spec["transmission"],
                    "status": VehicleStatus.AVAILABLE,
                    "status_note": "",
                    "photo": "",
                },
            )
            vehicles.append(vehicle)
        # Soft-retire legacy DEMO plates (scheduler bookings may still reference them).
        Vehicle.objects.filter(registration_number__startswith="DEMO").exclude(
            registration_number__in=keep_regs
        ).update(
            status=VehicleStatus.INACTIVE,
            show_on_public_page=False,
            status_note="Retired from development fleet seed",
        )
        zone, _ = PickupZone.objects.update_or_create(
            slug="demo-emmasdale-north",
            defaults={
                "name": "Emmasdale North Pickup",
                "branch": emmasdale,
                "description": "Demo pickup zone within ~5km.",
                "radius_km": Decimal("5.00"),
                "travel_buffer_minutes": 20,
                "travel_fee_amount": Decimal("50.00"),
                "currency": "ZMW",
                "is_active": True,
            },
        )
        # Prefer Corolla Manual for demo bookings when present.
        primary = next((v for v in vehicles if v.registration_number == "DEMO-COROLLA-M"), vehicles[0])
        return profile, [primary, *vehicles], zone

    def _scheduler(self, reception, student, course, instructor, vehicle, zone):
        account = EntitlementAccount.objects.filter(
            student=student, course=course
        ).first()
        start = timezone.now() + timedelta(days=2)
        start = start.replace(hour=9, minute=0, second=0, microsecond=0)

        existing = LessonBooking.objects.filter(
            student=student,
            internal_notes__startswith="[DEMO]",
            status=BookingStatus.APPROVED,
        ).first()
        if existing:
            return existing

        booking = create_schedule_request(
            actor=reception,
            data={
                "student": student.id,
                "instructor": instructor.id,
                "vehicle": vehicle.id,
                "course": course.id,
                "entitlement_account": account.id if account else None,
                "branch": zone.branch_id,
                "pickup_zone": zone.id,
                "starts_at": start,
                "duration_minutes": 60,
                "internal_notes": "[DEMO] Upcoming approved pickup lesson",
            },
        )
        booking = confirm_booking(actor=reception, booking=booking)
        return booking

    def _learning(self, content_user, student):
        topic, _ = Topic.objects.update_or_create(
            slug="demo-road-signs",
            defaults={
                "name": "Demo Road Signs",
                "description": "Practice topic for API testing.",
                "sort_order": 1,
            },
        )
        q1, _ = Question.objects.update_or_create(
            prompt="[DEMO] A red traffic light means?",
            defaults={
                "topic": topic,
                "choice_a": "Go",
                "choice_b": "Stop",
                "choice_c": "Hoot",
                "choice_d": "Turn freely",
                "correct_choice": "B",
                "explanation": "Red means stop and wait.",
                "status": LearnPublish.APPROVED,
                "is_rights_cleared": True,
                "created_by": content_user,
            },
        )
        q2, _ = Question.objects.update_or_create(
            prompt="[DEMO] Seat belts are?",
            defaults={
                "topic": topic,
                "choice_a": "Optional in town",
                "choice_b": "Required",
                "choice_c": "",
                "choice_d": "",
                "correct_choice": "B",
                "explanation": "Always wear a seat belt.",
                "status": LearnPublish.APPROVED,
                "is_rights_cleared": True,
                "created_by": content_user,
            },
        )
        q3, _ = Question.objects.update_or_create(
            prompt="[DEMO] At a stop sign you must?",
            defaults={
                "topic": topic,
                "choice_a": "Slow down only",
                "choice_b": "Come to a complete stop",
                "choice_c": "Hoot then go",
                "correct_choice": "B",
                "explanation": "Come to a complete stop, then proceed when safe.",
                "status": LearnPublish.APPROVED,
                "is_rights_cleared": True,
                "created_by": content_user,
            },
        )
        paper, _ = PracticePaper.objects.update_or_create(
            slug="demo-practice-paper-1",
            defaults={
                "title": "Demo Practice Paper 1",
                "summary": "Roadstar practice set — not an RTSA reprint.",
                "instructions": "Answer all questions. Timer is 20 minutes.",
                "time_limit_minutes": 20,
                "pass_mark_percent": 50,
                "shuffle_questions": False,
                "status": LearnPublish.DRAFT,
                "available_to_public_preview": True,
            },
        )
        PracticePaperQuestion.objects.filter(paper=paper).delete()
        for i, q in enumerate([q1, q2, q3]):
            PracticePaperQuestion.objects.create(
                paper=paper, question=q, sort_order=i
            )
        if paper.status != LearnPublish.APPROVED:
            approve_practice_paper(actor=content_user, paper=paper)

        StudyDocument.objects.update_or_create(
            slug="demo-highway-code-notes",
            defaults={
                "title": "Demo Highway Code notes",
                "summary": "Rights-cleared study link for testing.",
                "file_url": "https://example.com/demo-highway-notes.pdf",
                "topic": topic,
                "is_rights_cleared": True,
                "status": LearnPublish.APPROVED,
            },
        )

        # One submitted attempt for the paid learner
        if not Attempt.objects.filter(
            student=student, paper=paper, status=AttemptStatus.SUBMITTED
        ).exists():
            attempt = start_attempt(student=student, paper=paper)
            submit_attempt(
                student=student,
                attempt=attempt,
                answers={q1.id: "B", q2.id: "B", q3.id: "A"},
            )
