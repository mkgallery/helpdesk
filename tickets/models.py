from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        STAFF = "staff", "IT Staff"
        SUPERVISOR = "supervisor", "Supervisor"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)

    def save(self, *args, **kwargs):
        # a superuser created from the terminal becomes a supervisor automatically
        if self.is_superuser and self.role == self.Role.EMPLOYEE:
            self.role = self.Role.SUPERVISOR
        super().save(*args, **kwargs)

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_staff_member(self):
        return self.role == self.Role.STAFF

    @property
    def is_supervisor(self):
        return self.role == self.Role.SUPERVISOR


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    # Who reported the problem (no account needed)
    requester_name = models.CharField(max_length=150, default="")
    requester_phone = models.CharField(max_length=20, default="")

    # Kept optional, e.g. for tickets created by staff in the admin site
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    region = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    office = models.CharField(max_length=150)
    department = models.CharField(max_length=150, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.title}"


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="attachments/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        return self.file.name.split("/")[-1]


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
