from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("tickets/new/", views.ticket_create, name="ticket_create"),
    path("tickets/mine/", views.my_tickets, name="my_tickets"),
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("supervisor/", views.supervisor_dashboard, name="supervisor_dashboard"),
]
