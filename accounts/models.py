from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CITIZEN = 'citizen'
    ROLE_ADMIN = 'admin'
    ROLE_WORKER = 'worker'

    ROLE_CHOICES = [
        (ROLE_CITIZEN, 'Citizen'),
        (ROLE_ADMIN, 'Administrator'),
        (ROLE_WORKER, 'Department Worker'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_CITIZEN)
    phone = models.CharField(max_length=15, blank=True)
    department = models.ForeignKey(
        'incidents.Department',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='workers'
    )

    def is_citizen(self):
        return self.role == self.ROLE_CITIZEN

    def is_admin_user(self):
        return self.role == self.ROLE_ADMIN

    def is_worker(self):
        return self.role == self.ROLE_WORKER

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
