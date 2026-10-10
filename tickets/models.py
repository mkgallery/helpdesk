from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import IntegrityError, models, transaction
from django.utils import timezone


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

    # Public ticket number. Only active tickets have one. It is released when
    # the ticket is closed and given to the next new ticket.
    number = models.PositiveIntegerField(unique=True, null=True, blank=True, editable=False)
    closed_number = models.PositiveIntegerField(null=True, blank=True, editable=False)
    closed_at = models.DateTimeField(null=True, blank=True, editable=False)

    # Who reported the problem (no account needed)
    requester_name = models.CharField(max_length=150, default="")
    requester_phone = models.CharField(max_length=20, default="")

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
    office = models.CharField(max_length=150)
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
        return f"{self.display_number} {self.title}"

    @property
    def display_number(self):
        if self.number is not None:
            return f"#{self.number}"
        return f"closed (was #{self.closed_number or self.pk})"

    @classmethod
    def _next_free_number(cls):
        used = set(
            cls.objects.exclude(number__isnull=True).values_list("number", flat=True)
        )
        n = 1
        while n in used:
            n += 1
        return n

    def save(self, *args, **kwargs):
        # Closing a ticket releases its number so a new ticket can use it.
        if self.status == self.Status.CLOSED:
            if self.number is not None:
                self.closed_number = self.number
                self.number = None
                self.closed_at = timezone.now()
            return super().save(*args, **kwargs)

        # Active ticket that already has a number: nothing special to do.
        if self.number is not None:
            return super().save(*args, **kwargs)

        # New (or re-opened) ticket: give it the lowest free number.
        self.closed_at = None
        for _ in range(5):
            self.number = self._next_free_number()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.number = None  # someone took it at the same moment, try again
        raise IntegrityError("Could not assign a ticket number, please try again.")


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