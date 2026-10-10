import re

from django import forms

from .models import Ticket, TicketComment


def normalize_phone(raw):
    """
    Enforce Tanzanian mobile format:
      07XXXXXXXX  or  06XXXXXXXX  (10 digits, starting with 0)
    Also accepts +255XXXXXXXXX and 255XXXXXXXXX, and stores them
    as 0XXXXXXXXX for consistency.

    Raises ValidationError for anything else.
    """
    if not raw:
        raise forms.ValidationError("Phone number is required.")

    digits = re.sub(r"[\s\-().]", "", raw)
    if digits.startswith("+255"):
        digits = "0" + digits[4:]
    elif digits.startswith("255"):
        digits = "0" + digits[3:]

    if not re.fullmatch(r"0[67]\d{8}", digits):
        raise forms.ValidationError(
            "Enter a valid Tanzanian number: 07XXXXXXXX or 06XXXXXXXX."
        )
    return digits
def phone_key(phone):
    """Last 9 digits, so 0712345678 and +255712345678 match the same person."""
    return re.sub(r"\D", "", phone)[-9:]


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
        return normalize_phone(self.cleaned_data["requester_phone"])


class TrackForm(forms.Form):
    number = forms.IntegerField(
        min_value=1,
        label="Ticket number",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        max_length=20,
        label="Phone number you used on the ticket",
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "tel"}),
    )

    def clean_phone(self):
        return normalize_phone(self.cleaned_data["phone"])


class CommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }