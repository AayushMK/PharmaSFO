from django import forms

from .models import LeaveRequest


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "reason"]
        widgets = {
            "leave_type": forms.Select(attrs={"class": "select", "autofocus": True}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "input"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "input"}),
            "reason": forms.Textarea(attrs={"class": "textarea", "rows": 3, "placeholder": "Reason for leave"}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "End date can't be before the start date.")
        return cleaned
