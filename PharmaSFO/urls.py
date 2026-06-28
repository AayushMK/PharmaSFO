from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views

from api.api import api
from users.views import dashboard
from daily_coverage.views import add_daily_coverage, daily_coverage_calendar
from doctors.views import doctor_list
from doctor_employee_relation.views import (
    add_doctor_employee_relation,
    doctor_employee_relation_list,
    hr_review_employee_requests,
    hr_review_requests,
)
from tour_plans.views import add_tour_plan, tour_plan_list

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    path("", dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("doctors/", doctor_list, name="doctor_list"),
    path(
        "doctor_employee_relation/",
        doctor_employee_relation_list,
        name="doctor_employee_relation",
    ),
    path(
        "doctor_employee_relation/<int:employee_id>/",
        doctor_employee_relation_list,
        name="doctor_employee_relation_for_employee",
    ),
    path(
        "doctor_employee_relation/add/",
        add_doctor_employee_relation,
        name="add_doctor_employee_relation",
    ),
    path(
        "doctor_employee_relation/add/<int:employee_id>/",
        add_doctor_employee_relation,
        name="add_doctor_employee_relation_for_employee",
    ),
    path("review_requests/", hr_review_requests, name="hr_review_requests"),
    path(
        "review_requests/<int:employee_id>/",
        hr_review_employee_requests,
        name="hr_review_employee_requests",
    ),
    path("tour_plans/", tour_plan_list, name="tour_plans"),
    path("tour_plans/add/", add_tour_plan, name="add_tour_plan"),
    path("daily_coverage/", daily_coverage_calendar, name="daily_coverage_calendar"),
    path("daily_coverage/<int:year>/<int:month>/", daily_coverage_calendar, name="daily_coverage_calendar_month"),
    path("daily_coverage/add/", add_daily_coverage, name="add_daily_coverage"),
    path("daily_coverage/add/<str:selected_date>/", add_daily_coverage, name="add_daily_coverage_with_date"),
]
