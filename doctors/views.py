from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from daily_coverage.models import DailyCoverage
from doctor_employee_relation.models import DoctorEmployeeRelation
from notifications.utils import notify

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


@login_required
@never_cache
def edit_doctor(request, pk):
    if not _can_manage_doctors(request.user):
        raise PermissionDenied

    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == "POST":
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, f"Dr. {doctor.name} updated.")

            assigned_employees = list(
                DoctorEmployeeRelation.objects.filter(
                    doctor=doctor, status=DoctorEmployeeRelation.Status.APPROVED
                ).select_related("employee")
            )
            if assigned_employees:
                notify(
                    {rel.employee for rel in assigned_employees},
                    f"Dr. {doctor.name}'s details were updated.",
                    url=reverse("doctor_employee_relation"),
                )
            return redirect("doctor_list")
    else:
        form = DoctorForm(instance=doctor)

    return render(request, "doctors/edit_doctor.html", {"form": form, "doctor": doctor})


@login_required
@never_cache
def delete_doctor(request, pk):
    if not _can_manage_doctors(request.user):
        raise PermissionDenied

    doctor = get_object_or_404(Doctor, pk=pk)
    coverage_records = list(
        DailyCoverage.objects.filter(doctor=doctor)
        .select_related("created_by", "actual_working_place")
        .order_by("-report_date", "-call_time")
    )
    relations = list(
        DoctorEmployeeRelation.objects.filter(doctor=doctor).select_related("employee")
    )

    if request.method == "POST":
        if coverage_records and not request.POST.get("confirm_delete_coverage"):
            messages.error(request, "Confirm removing the coverage records to delete this doctor.")
            return render(request, "doctors/delete_doctor.html", {
                "doctor": doctor,
                "coverage_records": coverage_records,
                "relations": relations,
            })

        name = doctor.name

        # Figure out, per affected rep, exactly what's about to disappear for
        # them — an assignment, their own logged coverage, or both — before
        # any of it is deleted.
        relation_user_ids = {rel.employee_id for rel in relations}
        coverage_user_ids = {c.created_by_id for c in coverage_records if c.created_by_id}
        affected = {rel.employee_id: rel.employee for rel in relations}
        affected.update({c.created_by_id: c.created_by for c in coverage_records if c.created_by_id})

        coverage_count = len(coverage_records)
        if coverage_records:
            DailyCoverage.objects.filter(doctor=doctor).delete()
        doctor.delete()  # cascades DoctorEmployeeRelation

        for user_id, user in affected.items():
            parts = []
            if user_id in relation_user_ids:
                parts.append("your assignment to them was removed")
            if user_id in coverage_user_ids:
                parts.append("your logged coverage for them was removed")
            detail = " and ".join(parts)
            notify(
                user,
                f"Dr. {name} was removed from the doctor directory; {detail}.",
                url=reverse("doctor_employee_relation"),
            )

        messages.success(
            request,
            f"Dr. {name} removed from the directory"
            + (
                f" along with {coverage_count} coverage record{'s' if coverage_count != 1 else ''}"
                if coverage_count else ""
            )
            + ".",
        )
        return redirect("doctor_list")

    return render(request, "doctors/delete_doctor.html", {
        "doctor": doctor,
        "coverage_records": coverage_records,
        "relations": relations,
    })
