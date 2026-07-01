from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from .forms import DoctorForm
from .models import Doctor


def _can_add_doctor(user):
    return user.is_authenticated and (
        user.is_superuser or (user.is_staff and user.type == "HR")
    )


@login_required
@never_cache
def doctor_list(request):
    doctors = Doctor.objects.all()
    return render(
        request,
        "doctors/doctor_list.html",
        {"doctors": doctors, "can_add": _can_add_doctor(request.user)},
    )


@login_required
@never_cache
def add_doctor(request):
    if not _can_add_doctor(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = DoctorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("doctor_list")
    else:
        form = DoctorForm()

    return render(request, "doctors/add_doctor.html", {"form": form})
