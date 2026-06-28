from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from doctors.models import Doctor

from .models import DoctorEmployeeRelation


def _is_hr_user(user):
    return user.is_authenticated and user.is_staff and user.type == "HR"


@login_required
def doctor_employee_relation_list(request, employee_id=None):
    if employee_id is None:
        employee = request.user
    else:
        employee = get_object_or_404(get_user_model(), pk=employee_id)
        if not request.user.is_staff and request.user != employee:
            raise PermissionDenied

    selected_status = request.GET.get("status", "all")
    queryset = DoctorEmployeeRelation.objects.filter(employee=employee).select_related("doctor")

    if selected_status == DoctorEmployeeRelation.Status.APPROVED:
        queryset = queryset.filter(status=DoctorEmployeeRelation.Status.APPROVED)
    elif selected_status == DoctorEmployeeRelation.Status.REJECTED:
        queryset = queryset.filter(status=DoctorEmployeeRelation.Status.REJECTED)
    elif selected_status == DoctorEmployeeRelation.Status.PENDING:
        queryset = queryset.filter(status=DoctorEmployeeRelation.Status.PENDING)

    doctor_employee_relations = queryset.order_by("doctor__name")

    return render(
        request,
        "doctor_employee_relation/doctor_employee_relation_list.html",
        {
            "employee": employee,
            "doctor_employee_relations": doctor_employee_relations,
            "selected_status": selected_status,
        },
    )


@login_required
def add_doctor_employee_relation(request, employee_id=None):
    if employee_id is None:
        employee = request.user
    else:
        employee = get_object_or_404(get_user_model(), pk=employee_id)
        if not request.user.is_staff and request.user != employee:
            raise PermissionDenied

    if request.method == "POST":
        doctor_id = request.POST.get("doctor")
        msl_number = request.POST.get("msl_number")

        if doctor_id:
            doctor = get_object_or_404(Doctor, pk=doctor_id)
            DoctorEmployeeRelation.objects.get_or_create(
                employee=employee,
                doctor=doctor,
                defaults={
                    "msl_number": msl_number or None,
                    "relation_date": date.today(),
                    "status": DoctorEmployeeRelation.Status.PENDING,
                },
            )

        return redirect("doctor_employee_relation")

    assigned_doctor_ids = set(
        DoctorEmployeeRelation.objects.filter(employee=employee).values_list("doctor_id", flat=True)
    )
    available_doctors = Doctor.objects.exclude(id__in=assigned_doctor_ids).order_by("name")

    return render(
        request,
        "doctor_employee_relation/add_doctor_employee_relation.html",
        {
            "employee": employee,
            "available_doctors": available_doctors,
        },
    )


@login_required
def hr_review_requests(request):
    if not _is_hr_user(request.user):
        raise PermissionDenied

    pending_requests = (
        DoctorEmployeeRelation.objects.filter(status=DoctorEmployeeRelation.Status.PENDING)
        .select_related("employee", "doctor")
        .order_by("employee__username", "doctor__name")
    )

    employees_with_pending = []
    for relation in pending_requests:
        employee = relation.employee
        if not any(item["employee"].pk == employee.pk for item in employees_with_pending):
            employees_with_pending.append(
                {
                    "employee": employee,
                    "count": pending_requests.filter(employee=employee).count(),
                }
            )

    return render(
        request,
        "doctor_employee_relation/hr_review_requests.html",
        {
            "employees_with_pending": employees_with_pending,
        },
    )


@login_required
def hr_review_employee_requests(request, employee_id):
    if not _is_hr_user(request.user):
        raise PermissionDenied

    employee = get_object_or_404(get_user_model(), pk=employee_id)
    pending_relations = (
        DoctorEmployeeRelation.objects.filter(employee=employee, status=DoctorEmployeeRelation.Status.PENDING)
        .select_related("doctor")
        .order_by("doctor__name")
    )

    if request.method == "POST":
        relation_id = request.POST.get("relation_id")
        action = request.POST.get("action")
        relation = get_object_or_404(DoctorEmployeeRelation, pk=relation_id, employee=employee)

        if action == "approve":
            relation.status = DoctorEmployeeRelation.Status.APPROVED
        elif action == "reject":
            relation.status = DoctorEmployeeRelation.Status.REJECTED
        else:
            relation.status = DoctorEmployeeRelation.Status.REJECTED

        relation.save()
        return redirect("hr_review_employee_requests", employee_id=employee.id)

    return render(
        request,
        "doctor_employee_relation/hr_review_employee_requests.html",
        {
            "employee": employee,
            "pending_relations": pending_relations,
        },
    )

