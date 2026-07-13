from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from .forms import DoctorForm
from .models import Doctor


def _can_manage_doctors(user):
    return user.is_authenticated and (
        user.is_superuser or (user.is_staff and user.type == "HR")
    )


@login_required
@never_cache
def doctor_list(request):
    # The doctor directory is HR-only; reps see doctors via "My assignments"
    if not _can_manage_doctors(request.user):
        raise PermissionDenied

    doctors = Doctor.objects.select_related("hospital")
    return render(
        request,
        "doctors/doctor_list.html",
        {"doctors": doctors, "can_add": True},
    )


@login_required
@never_cache
def add_doctor(request):
    if not _can_manage_doctors(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = DoctorForm(request.POST)
        if form.is_valid():
            doctor = form.save()
            messages.success(request, f"Dr. {doctor.name} added to the directory.")
            return redirect("doctor_list")
    else:
        form = DoctorForm()

    return render(request, "doctors/add_doctor.html", {"form": form})
