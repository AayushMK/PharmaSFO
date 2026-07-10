from django import forms

from doctors.models import Doctor
from tour_plans.models import Area

from .models import Chemist, ChemistCoverage, DailyCoverage, Stockist, StockistCoverage


class _PartnerForm(forms.ModelForm):
    """Shared base for the Chemist / Stockist master forms (same fields)."""

    class Meta:
        fields = ["name", "area", "phone"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Full name", "autofocus": True}),
            "area": forms.Select(attrs={"class": "select"}),
            "phone": forms.TextInput(attrs={"class": "input", "type": "tel", "placeholder": "e.g. 98XXXXXXXX (optional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["area"].queryset = Area.objects.order_by("name")
        self.fields["area"].empty_label = "Select area"


class ChemistForm(_PartnerForm):
    class Meta(_PartnerForm.Meta):
        model = Chemist


class StockistForm(_PartnerForm):
    class Meta(_PartnerForm.Meta):
        model = Stockist


class DailyCoverageForm(forms.ModelForm):
    class Meta:
        model = DailyCoverage
        fields = ["report_date", "doctor", "actual_working_place", "call_time", "products", "worked_with", "remarks"]
        widgets = {
            "report_date": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "doctor": forms.Select(attrs={"class": "select"}),
            "actual_working_place": forms.Select(attrs={"class": "select"}),
            "call_time": forms.TimeInput(attrs={"type": "time", "class": "input"}, format="%H:%M"),
            "products": forms.TextInput(attrs={"class": "input", "placeholder": "Products promoted (optional)"}),
            "remarks": forms.Textarea(attrs={"rows": 3, "class": "textarea"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = Doctor.objects.order_by("name")
        self.fields["doctor"].empty_label = "Select doctor"
        self.fields["actual_working_place"].queryset = Area.objects.order_by("name")
        self.fields["actual_working_place"].empty_label = "Select place"
        # "Worked with" — Self plus colleagues; a legacy free-text value stays selectable
        from django.contrib.auth import get_user_model
        names = [
            u.get_full_name() or u.username
            for u in get_user_model().objects.exclude(pk=self.instance.created_by_id).order_by("username")
        ]
        choices = [("Self", "Self")] + [(n, n) for n in names]
        current = (self.instance.worked_with or "").strip() if self.instance.pk else ""
        if current and current not in dict(choices):
            choices.insert(0, (current, current))
        self.fields["worked_with"].widget = forms.Select(attrs={"class": "select"}, choices=choices)


class _PartnerCoverageForm(forms.ModelForm):
    """Edit form for a chemist/stockist coverage row. The name is picked from
    the master directory; a legacy name that isn't in the directory stays
    selectable so old records can be saved unchanged."""

    master_model = None

    class Meta:
        fields = ["report_date", "name", "area", "call_time"]
        widgets = {
            "report_date": forms.DateInput(attrs={"type": "date", "class": "input"}, format="%Y-%m-%d"),
            "name": forms.Select(attrs={"class": "select"}),
            "area": forms.Select(attrs={"class": "select"}),
            "call_time": forms.TimeInput(attrs={"type": "time", "class": "input"}, format="%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        names = list(
            self.master_model.objects.order_by("name").values_list("name", flat=True).distinct()
        )
        current = self.instance.name if self.instance.pk else None
        if current and current not in names:
            names.insert(0, current)
        self.fields["name"].widget.choices = [("", "Select name")] + [(n, n) for n in names]
        self.fields["area"].queryset = Area.objects.order_by("name")
        self.fields["area"].empty_label = "Select area"


class ChemistCoverageForm(_PartnerCoverageForm):
    master_model = Chemist

    class Meta(_PartnerCoverageForm.Meta):
        model = ChemistCoverage


class StockistCoverageForm(_PartnerCoverageForm):
    master_model = Stockist

    class Meta(_PartnerCoverageForm.Meta):
        model = StockistCoverage


class DailyCoverageBulkForm(forms.Form):
    entries          = forms.JSONField(required=False, widget=forms.HiddenInput())
    chemist_entries  = forms.JSONField(required=False, widget=forms.HiddenInput())
    stockist_entries = forms.JSONField(required=False, widget=forms.HiddenInput())
    no_doctor_reason = forms.CharField(required=False, widget=forms.HiddenInput())
