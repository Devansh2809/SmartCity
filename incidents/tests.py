from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import Department, Incident, StatusUpdate


class RoutingAndEscalationTests(TestCase):
    def setUp(self):
        self.citizen = get_user_model().objects.create_user(
            username='citizen1',
            password='testpass123',
            role='citizen',
        )

        self.public_works = Department.objects.create(
            name='Public Works Department',
            code='PUBLIC_WORKS',
        )
        self.sanitation = Department.objects.create(
            name='Sanitation Department',
            code='SANITATION',
        )
        self.electricity = Department.objects.create(
            name='Electricity Department',
            code='ELECTRICITY',
        )
        self.water = Department.objects.create(
            name='Water Supply Department',
            code='WATER',
        )
        self.traffic = Department.objects.create(
            name='Traffic Department',
            code='TRAFFIC',
        )

    def test_department_auto_routing(self):
        incident = Incident.objects.create(
            title='Water leakage near junction',
            description='Pipe is leaking heavily.',
            incident_type='WATER_LEAK',
            priority='MEDIUM',
            latitude=12.971599,
            longitude=77.594566,
            reported_by=self.citizen,
        )
        self.assertEqual(incident.department.code, 'WATER')

    def test_emergency_auto_assignment(self):
        worker = get_user_model().objects.create_user(
            username='worker1',
            password='testpass123',
            role='worker',
            department=self.traffic,
        )

        incident = Incident.objects.create(
            title='Major traffic signal failure',
            description='Signal down at major intersection.',
            incident_type='TRAFFIC',
            priority='EMERGENCY',
            latitude=12.971599,
            longitude=77.594566,
            reported_by=self.citizen,
        )

        self.assertEqual(incident.department.code, 'TRAFFIC')
        self.assertEqual(incident.assigned_to, worker)
        self.assertEqual(incident.status, 'ASSIGNED')
        self.assertIsNotNone(incident.deadline)

    def test_overdue_incident_auto_escalates(self):
        incident = Incident.objects.create(
            title='Overflowing garbage',
            description='Not cleaned for days.',
            incident_type='GARBAGE',
            priority='LOW',
            latitude=12.971599,
            longitude=77.594566,
            reported_by=self.citizen,
            deadline=timezone.now() - timedelta(hours=1),
        )
        incident.status = 'IN_PROGRESS'
        incident.save()

        call_command('escalate_incidents')
        incident.refresh_from_db()

        self.assertEqual(incident.status, 'ESCALATED')
        self.assertEqual(incident.priority, 'EMERGENCY')
        self.assertTrue(
            StatusUpdate.objects.filter(
                incident=incident,
                status='ESCALATED'
            ).exists()
        )