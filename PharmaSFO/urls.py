from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views

from api.api import api
from reports.views import (
    daily_activity_report,
    monthly_activity_report,
    monthly_target_report,
    yearly_activity_report,
    yearly_activity_report_excel,
)
from users.views import dashboard
from daily_coverage.views import (
    add_daily_coverage,
    daily_coverage_calendar,
    daily_coverage_list,
    delete_daily_coverage,
    edit_daily_coverage,
)
from doctors.views import doctor_list
from doctor_employee_relation.views import (
    add_doctor_employee_relation,
    doctor_employee_relation_list,
    hr_review_employee_requests,
    hr_review_requests,
)
from tour_plans.views import add_tour_plan, hr_review_employee_tour_plans, hr_review_tour_plans, tour_plan_list

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
    path("tour_plans/review/", hr_review_tour_plans, name="hr_review_tour_plans"),
    path("tour_plans/review/<int:employee_id>/", hr_review_employee_tour_plans, name="hr_review_employee_tour_plans"),
    path("daily_coverage/", daily_coverage_calendar, name="daily_coverage_calendar"),
    path("daily_coverage/<int:year>/<int:month>/", daily_coverage_calendar, name="daily_coverage_calendar_month"),
    path("daily_coverage/add/", add_daily_coverage, name="add_daily_coverage"),
    path("daily_coverage/add/<str:selected_date>/", add_daily_coverage, name="add_daily_coverage_with_date"),
    path("daily_coverage/records/", daily_coverage_list, name="daily_coverage_list"),
    path("reports/daily-activity/", daily_activity_report, name="daily_activity_report"),
    path("reports/monthly-activity/", monthly_activity_report, name="monthly_activity_report"),
    path("reports/monthly-target/", monthly_target_report, name="monthly_target_report"),
    path("reports/yearly-activity/", yearly_activity_report, name="yearly_activity_report"),
    path("reports/yearly-activity/export/", yearly_activity_report_excel, name="yearly_activity_report_excel"),
    path("daily_coverage/<int:pk>/edit/", edit_daily_coverage, name="edit_daily_coverage"),
    path("daily_coverage/<int:pk>/delete/", delete_daily_coverage, name="delete_daily_coverage"),
]
