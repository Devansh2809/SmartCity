import uuid
from datetime import timedelta

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
        'EMERGENCY': 4,
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
        if not self.tracking_id:
            self.tracking_id = 'INC-' + str(uuid.uuid4()).upper().replace('-', '')[:8]
        if not self.department_id:
            dept_code = DEPT_ROUTING.get(self.incident_type, 'PUBLIC_WORKS')
            try:
                self.department = Department.objects.get(code=dept_code)
            except Department.DoesNotExist:
                pass
        if not self.deadline:
            hours = self.DEADLINE_HOURS.get(self.priority, 72)
            self.deadline = timezone.now() + timedelta(hours=hours)
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
