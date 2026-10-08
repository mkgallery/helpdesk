import re

from django import forms

from .models import Ticket, TicketComment


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "requester_name", "requester_phone",
            "region", "district", "office", "department",
            "latitude", "longitude",
            "title", "description", "priority",
        ]
        labels = {
            "requester_name": "Your full name",
            "requester_phone": "Phone number",
            "office": "Office / site",
            "department": "Department (optional)",
        }
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
        self.fields["requester_phone"].widget.attrs["inputmode"] = "tel"

    def clean_requester_phone(self):
        phone = re.sub(r"[\s\-().]", "", self.cleaned_data["requester_phone"])
        if not re.fullmatch(r"\+?\d{9,15}", phone):
            raise forms.ValidationError(
                "Enter a valid phone number: digits only, optionally starting with +."
            )
        return phone


class CommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }