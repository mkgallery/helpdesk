from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
import os


class Command(BaseCommand):
    help = "Create a superuser non-interactively from environment variables"

    def handle(self, *args, **options):
        User = get_user_model()
        
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not password:
            self.stdout.write(
                self.style.ERROR("DJANGO_SUPERUSER_PASSWORD not set — skipping superuser creation")
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f"Superuser '{username}' already exists — skipping")
            )
            return

        with transaction.atomic():
            User.objects.create_superuser(username=username, email=email, password=password)
        
        self.stdout.write(
            self.style.SUCCESS(f"Superuser '{username}' created successfully")
        )