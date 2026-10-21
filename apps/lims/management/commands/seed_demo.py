"""
Usage:

python manage.py seed_demo

python manage.py seed_demo --flush  // reset created objects
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.lims.models import Result, ResultStatus, Sample, SampleStatus

DEMO_DATA = [
    (
        "SMP-001",
        "ORD-2026-001",
        "CLIENT-001",
        SampleStatus.COMPLETED,
        [
            ("Protein", 12.5, "%", ResultStatus.APPROVED),
            ("Moisture", 8.1, "%", ResultStatus.APPROVED),
        ],
    ),
    (
        "SMP-002",
        "ORD-2026-001",
        "CLIENT-001",
        SampleStatus.IN_PROGRESS,
        [
            ("Protein", 11.9, "%", ResultStatus.APPROVED),
            ("pH", 6.8, "", ResultStatus.DRAFT),
        ],
    ),
    ("SMP-003", "ORD-2026-002", "CLIENT-002", SampleStatus.REGISTERED, []),
    ("SMP-004", "ORD-2026-002", "CLIENT-002", SampleStatus.CANCELLED, []),
]


class Command(BaseCommand):
    help = "Load demo samples and results. Safe to run repeatedly; existing samples are skipped."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all samples and results before loading the demo data.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            Result.objects.all().delete()
            Sample.objects.all().delete()
            self.stdout.write("Existing samples and results deleted.")

        created = 0
        for sample_id, order_id, client_id, sample_status, results in DEMO_DATA:
            sample, is_new = Sample.objects.get_or_create(
                sample_id=sample_id,
                defaults={
                    "order_id": order_id,
                    "client_id": client_id,
                    "status": sample_status,
                },
            )
            if not is_new:
                continue
            created += 1
            for parameter, value, unit, result_status in results:
                Result.objects.create(
                    sample=sample,
                    parameter=parameter,
                    value=value,
                    unit=unit,
                    status=result_status,
                )

        self.stdout.write(
            self.style.SUCCESS(f"Demo data ready: {created} new sample(s) created.")
        )
