from django.core.management.base import BaseCommand

from incidents.models import Department

DEPARTMENTS = [
    {'name': 'Public Works Department', 'code': 'PUBLIC_WORKS',
     'email': 'publicworks@smartcity.gov', 'phone': '1800-001-0001',
     'description': 'Handles roads, pavements, and civil infrastructure.'},
    {'name': 'Sanitation Department', 'code': 'SANITATION',
     'email': 'sanitation@smartcity.gov', 'phone': '1800-001-0002',
     'description': 'Manages garbage collection and waste disposal.'},
    {'name': 'Electricity Department', 'code': 'ELECTRICITY',
     'email': 'electricity@smartcity.gov', 'phone': '1800-001-0003',
     'description': 'Manages street lighting and electrical infrastructure.'},
    {'name': 'Water Supply Department', 'code': 'WATER',
     'email': 'water@smartcity.gov', 'phone': '1800-001-0004',
     'description': 'Manages water pipelines and leakage repairs.'},
    {'name': 'Traffic Department', 'code': 'TRAFFIC',
     'email': 'traffic@smartcity.gov', 'phone': '1800-001-0005',
     'description': 'Manages traffic signals, congestion, and road safety.'},
]


class Command(BaseCommand):
    help = 'Create the five default municipal departments.'

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for dept_data in DEPARTMENTS:
            _, was_created = Department.objects.update_or_create(
                code=dept_data['code'],
                defaults=dept_data,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. {created} created, {updated} updated.'
        ))
