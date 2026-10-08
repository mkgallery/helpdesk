from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Ticket, TicketAttachment, TicketComment, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Helpdesk role", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Helpdesk role", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_active")
    list_filter = ("role",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "priority", "created_by", "assigned_to", "created_at")
    list_filter = ("status", "priority", "region")


admin.site.register(TicketAttachment)
admin.site.register(TicketComment)
