from django.core.management.base import BaseCommand
from django.utils import timezone

from incidents.models import DEPT_ROUTING, Department, Incident, StatusUpdate


class Command(BaseCommand):
    help = 'Escalate incidents that have passed their deadline without resolution.'

    def handle(self, *args, **options):
        now = timezone.now()
        overdue = (
            Incident.objects
            .filter(deadline__lt=now)
            .exclude(status__in=['RESOLVED', 'ESCALATED'])
        )

        count = 0
        for incident in overdue:
            previous_status = incident.status

            # Ensure routed department exists before escalation
            if not incident.department_id:
                dept_code = DEPT_ROUTING.get(incident.incident_type, 'PUBLIC_WORKS')
                incident.department = Department.objects.filter(code=dept_code).first()

            incident.status = 'ESCALATED'

            # Escalated tickets become emergency
            if incident.priority != 'EMERGENCY':
                incident.priority = 'EMERGENCY'

            incident.save()

            StatusUpdate.objects.create(
                incident=incident,
                status='ESCALATED',
                note=(
                    f'Auto-escalated: deadline exceeded without resolution. '
                    f'Previous status: {previous_status}.'
                ),
                updated_by=None,
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Escalated {count} incident(s).'))