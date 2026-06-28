from django import forms

from .models import Area, TourPlan


class TourPlanForm(forms.ModelForm):
    class Meta:
        model = TourPlan
        fields = ["plan_date", "area", "worked_with", "remarks"]
        widgets = {
            "plan_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["area"].queryset = Area.objects.order_by("name")
        self.fields["area"].empty_label = "Select area"
        self.fields["worked_with"].empty_label = "Select member"


class TourPlanBulkForm(forms.Form):
    entries = forms.JSONField(required=False, widget=forms.HiddenInput())
