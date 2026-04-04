import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import models
from django.utils import timezone

DEPT_ROUTING = {
    'POTHOLE': 'PUBLIC_WORKS',
    'GARBAGE': 'SANITATION',
    'STREETLIGHT': 'ELECTRICITY',
    'WATER_LEAK': 'WATER',
    'TRAFFIC': 'TRAFFIC',
}


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Incident(models.Model):
    TYPE_CHOICES = [
        ('POTHOLE', 'Pothole'),
        ('GARBAGE', 'Garbage Overflow'),
        ('STREETLIGHT', 'Streetlight Failure'),
        ('WATER_LEAK', 'Water Leakage'),
        ('TRAFFIC', 'Traffic Issue'),
    ]

    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
        ('ESCALATED', 'Escalated'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('EMERGENCY', 'Emergency'),
    ]

    DEADLINE_HOURS = {
    'EMERGENCY': 2,
    'HIGH': 24,
    'MEDIUM': 72,
    'LOW': 168,
    }

    tracking_id = models.CharField(max_length=20, unique=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    incident_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='SUBMITTED')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')

    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.CharField(max_length=255, blank=True)
    area = models.CharField(max_length=100, blank=True)

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reported_incidents',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_incidents',
    )
    department = models.ForeignKey(
        Department,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='incidents',
    )

    image = models.ImageField(upload_to='incidents/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        is_create = self._state.adding
        old_priority = None

        if not is_create:
            old_priority = (
                Incident.objects
                .filter(pk=self.pk)
                .values_list('priority', flat=True)
                .first()
            )

        if not self.tracking_id:
            self.tracking_id = 'INC-' + str(uuid.uuid4()).upper().replace('-', '')[:8]

        # Department routing by incident type
        if not self.department_id:
            dept_code = DEPT_ROUTING.get(self.incident_type, 'PUBLIC_WORKS')
            self.department = Department.objects.filter(code=dept_code).first()

        # SLA deadline by priority (recompute when priority changes)
        priority_changed = old_priority is not None and old_priority != self.priority
        if not self.deadline or (
            priority_changed and self.status not in ('RESOLVED', 'CLOSED', 'ESCALATED')
        ):
            hours = self.DEADLINE_HOURS.get(self.priority, 72)
            base_time = self.created_at or timezone.now()
            self.deadline = base_time + timedelta(hours=hours)

        # Emergency complaints: fast routing to department worker
        if self.priority == 'EMERGENCY' and not self.assigned_to_id and self.department_id:
            User = get_user_model()
            worker = (
                User.objects
                .filter(role='worker', department=self.department, is_active=True)
                .order_by('-last_login', 'date_joined')
                .first()
            )
            if worker:
                self.assigned_to = worker
                if self.status == 'SUBMITTED':
                    self.status = 'ASSIGNED'

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_id}: {self.title}"

    @property
    def is_overdue(self):
        return (
            self.deadline
            and timezone.now() > self.deadline
            and self.status not in ('RESOLVED', 'CLOSED')
        )


class StatusUpdate(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='status_updates')
    status = models.CharField(max_length=15, choices=Incident.STATUS_CHOICES)
    note = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.incident.tracking_id} → {self.status}"
