from doctor_employee_relation.models import DoctorEmployeeRelation
from tour_plans.models import TourPlan


def nav_counts(request):
    """Pending-approval counts for the sidebar HR badges (HR staff only)."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated and user.is_staff and user.type == "HR"):
        return {}
    return {
        "nav_pending_doctor_requests": DoctorEmployeeRelation.objects.filter(
            status=DoctorEmployeeRelation.Status.PENDING
        ).count(),
        "nav_pending_tour_plans": TourPlan.objects.filter(
            status=TourPlan.Status.PENDING
        ).count(),
    }
