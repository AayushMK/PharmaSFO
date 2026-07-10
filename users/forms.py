from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class UserCreateForm(UserCreationForm):
    """HR-facing form for onboarding employees from the site (not Django admin).

    The Admin position is deliberately excluded — admin-ranked accounts are
    created by superusers in Django admin. Users created with the HR position
    get `is_staff=True` to match the project convention for HR checks
    (`is_staff and type == "HR"`).
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "type"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "input", "placeholder": "Given name", "autofocus": True}),
            "last_name": forms.TextInput(attrs={"class": "input", "placeholder": "Family name"}),
            "username": forms.TextInput(attrs={"class": "input", "placeholder": "Login username"}),
            "email": forms.EmailInput(attrs={"class": "input", "placeholder": "name@company.com (optional)"}),
            "type": forms.Select(attrs={"class": "select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["type"].choices = [
            (value, label)
            for value, label in User.UserType.choices
            if value != User.UserType.ADMIN
        ]
        self.fields["password1"].widget.attrs.update({"class": "input", "autocomplete": "new-password"})
        self.fields["password2"].widget.attrs.update({"class": "input", "autocomplete": "new-password"})

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.type == User.UserType.HR:
            user.is_staff = True  # project convention: HR checks require is_staff
        if commit:
            user.save()
        return user
