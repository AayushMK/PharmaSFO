from django import forms

from .models import Doctor, Hospital


class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ["name", "nmc_number", "hospital", "area", "specialization", "phone", "email"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Doctor's full name", "autofocus": True}),
            "nmc_number": forms.TextInput(attrs={"class": "input", "placeholder": "Nepal Medical Council number"}),
            "hospital": forms.Select(attrs={"class": "select"}),
            "area": forms.TextInput(attrs={"class": "input", "placeholder": "Area / City"}),
            "specialization": forms.TextInput(attrs={"class": "input", "placeholder": "e.g. Cardiology (optional)"}),
            "phone": forms.TextInput(attrs={"class": "input", "type": "tel", "placeholder": "e.g. 98XXXXXXXX (optional)"}),
            "email": forms.EmailInput(attrs={"class": "input", "placeholder": "doctor@example.com (optional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["hospital"].queryset = Hospital.objects.select_related("area")
        self.fields["hospital"].empty_label = "Select hospital"
