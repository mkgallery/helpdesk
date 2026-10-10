from django.urls import path

from . import views

urlpatterns = [
    # public
    path("", views.ticket_create, name="ticket_create"),
    path("submitted/", views.ticket_submitted, name="ticket_submitted"),
    path("track/", views.ticket_track, name="ticket_track"),
    # staff and supervisor
    path("dashboard/", views.dashboard, name="dashboard"),
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("supervisor/", views.supervisor_dashboard, name="supervisor_dashboard"),
    path("reports/", views.reports, name="reports"),
    path("reports/csv/", views.reports_csv, name="reports_csv"),
]