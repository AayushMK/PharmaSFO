from django import forms

from doctors.models import Doctor
from tour_plans.models import Area

from .models import DailyCoverage


class DailyCoverageForm(forms.ModelForm):
    class Meta:
        model = DailyCoverage
        fields = ["report_date", "doctor", "actual_working_place", "call_time", "products", "worked_with", "remarks"]
        widgets = {
            "report_date": forms.DateInput(attrs={"type": "date"}),
            "call_time": forms.TimeInput(attrs={"type": "time"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = Doctor.objects.order_by("name")
        self.fields["doctor"].empty_label = "Select doctor"
        self.fields["actual_working_place"].queryset = Area.objects.order_by("name")
        self.fields["actual_working_place"].empty_label = "Select place"


class DailyCoverageBulkForm(forms.Form):
    entries = forms.JSONField(required=False, widget=forms.HiddenInput())
