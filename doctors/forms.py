from django import forms

from .models import Doctor


class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ["name", "nmc_number", "area", "specialization"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Doctor's full name"}),
            "nmc_number": forms.TextInput(attrs={"placeholder": "Nepal Medical Council number"}),
            "area": forms.TextInput(attrs={"placeholder": "Area / City"}),
            "specialization": forms.TextInput(attrs={"placeholder": "e.g. Cardiology (optional)"}),
        }
