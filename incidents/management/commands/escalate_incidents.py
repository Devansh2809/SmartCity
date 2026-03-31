from django.core.management.base import BaseCommand
from django.utils import timezone

from incidents.models import Incident, StatusUpdate


class Command(BaseCommand):
    help = 'Escalate incidents that have passed their deadline without resolution.'

    def handle(self, *args, **options):
        overdue = Incident.objects.filter(
            deadline__lt=timezone.now(),
        ).exclude(status__in=['RESOLVED', 'CLOSED', 'ESCALATED'])

        count = 0
        for incident in overdue:
            incident.status = 'ESCALATED'
            incident.save()
            StatusUpdate.objects.create(
                incident=incident,
                status='ESCALATED',
                note='Auto-escalated: deadline exceeded without resolution.',
                updated_by=None,
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Escalated {count} incident(s).'))
