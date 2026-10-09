import re

from django import forms

from .models import Ticket, TicketComment


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "requester_name", "requester_phone", "office",
            "latitude", "longitude",
            "title", "description",
        ]
        labels = {
            "requester_name": "Your full name",
            "requester_phone": "Phone number",
            "office": "Office / site",
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
                field.widget.attrs["class"] = "form-control"
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