from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        STAFF = 'STAFF', 'Pharmacy Staff'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STAFF,
        help_text="Designates user role and permissions in the pharmacy system."
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    qualification = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. Pharm.D, B.Pharm, Pharmacist Assistant")
    is_active_staff = models.BooleanField(default=True, help_text="Designates whether this staff member is active.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    def is_staff_user(self):
        return self.role in [self.Role.STAFF, self.Role.ADMIN] or self.is_superuser

    @property
    def display_role(self):
        return dict(self.Role.choices).get(self.role, self.role)

    def __str__(self):
        full_name = self.get_full_name()
        if full_name:
            return f"{full_name} ({self.username}) - {self.display_role}"
        return f"{self.username} ({self.display_role})"
