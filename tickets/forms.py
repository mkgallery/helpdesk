from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Ticket, TicketComment, User


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "region", "district", "office", "latitude", "longitude",
            "title", "description", "priority",
        ]
        widgets = {
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ("latitude", "longitude"):
                css = "form-select" if name == "priority" else "form-control"
                field.widget.attrs["class"] = css


class CommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }
