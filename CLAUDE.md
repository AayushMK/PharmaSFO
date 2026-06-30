# PharmaSFO - Pharma Sales Force Automation

## Stack
- **Backend:** Django 5.x + Django Ninja (REST API with JWT via django-ninja-jwt)
- **Database:** PostgreSQL 16 (Dockerized)
- **Package manager:** uv
- **Containerization:** Docker Compose
- **Frontend:** Django templates (plan to migrate to React later)
- **Auth:** Session-based for templates, JWT for API (ready for SPA/mobile)
- **Excel export:** openpyxl

## Running
```bash
docker compose up -d                                              # Start everything
docker compose logs web -f                                        # Watch logs
docker compose run --rm web uv run python manage.py <command>     # Django management commands
docker compose run --rm web uv run python manage.py createsuperuser  # Create new admin user
docker compose down                                               # Stop everything
docker compose up --build -d                                      # Rebuild after dependency changes
```

## Project Structure
```
PharmSFAO/
├── PharmaSFO/              # Django project config
│   ├── settings.py         # Main settings (AUTH_USER_MODEL, DB, JWT config)
│   ├── urls.py             # Root URL routing
│   ├── wsgi.py / asgi.py
├── users/                  # Custom User app
│   ├── models.py           # User(AbstractUser) with type field (HR, SGM, GM, AGM, MR)
│   ├── admin.py            # UserAdmin with type in fieldsets
│   ├── views.py            # dashboard view
├── doctors/                # Doctors app
│   ├── models.py           # Doctor(name, nmc_number, area, specialization)
│   ├── admin.py            # DoctorAdmin with search/filter
│   ├── views.py            # doctor_list view
├── doctor_employee_relation/  # Doctor-MR assignment app
│   ├── models.py           # DoctorEmployeeRelation (employee, doctor, msl_number, status)
│   ├── views.py            # list, add, HR review views
├── tour_plans/             # Tour planning app
│   ├── models.py           # Area, TourPlan (with status: pending/approved/rejected)
│   ├── forms.py            # TourPlanBulkForm
│   ├── views.py            # list, add, HR review/approve views
├── daily_coverage/         # Daily call reporting app
│   ├── models.py           # DailyCoverage model
│   ├── forms.py            # DailyCoverageBulkForm, DailyCoverageForm
│   ├── views.py            # calendar, add (bulk), list, edit, delete views
├── reports/                # Reporting module (no models, no INSTALLED_APPS entry needed)
│   ├── views.py            # daily_activity, monthly_activity, monthly_target, yearly_activity
├── api/                    # Django Ninja API
│   ├── api.py              # NinjaAPI + JWT controller + /doctors endpoint
├── templates/
│   ├── base.html           # Base layout with navbar (shows user type, POST logout)
│   ├── dashboard.html      # Dashboard with links to all features
│   ├── registration/
│   │   └── login.html
│   ├── doctors/
│   │   └── doctor_list.html
│   ├── doctor_employee_relation/
│   │   ├── doctor_employee_relation_list.html
│   │   ├── add_doctor_employee_relation.html
│   │   ├── hr_review_requests.html
│   │   └── hr_review_employee_requests.html
│   ├── tour_plans/
│   │   ├── tour_plan_list.html          # Shows status column
│   │   ├── add_tour_plan.html
│   │   ├── hr_review_tour_plans.html    # HR: employees with pending plans
│   │   └── hr_review_employee_tour_plans.html  # HR: approve/reject per employee
│   ├── daily_coverage/
│   │   ├── calendar.html               # Monthly calendar; days gated by tour plan approval
│   │   ├── add_daily_coverage.html     # Bulk add form
│   │   ├── daily_coverage_list.html    # List with edit/delete (2-day window)
│   │   └── edit_daily_coverage.html
│   └── reports/
│       ├── daily_activity_report.html
│       ├── monthly_activity_report.html  # Chart.js frequency diagram + list of data tabs
│       ├── monthly_target_report.html    # Traffic-light dots per doctor
│       └── yearly_activity_report.html  # Doctor × month visit-date grid + Excel export
├── static/css/style.css    # App styling
├── docker-compose.yml      # web + db services
├── Dockerfile              # Python 3.12-slim + uv
├── pyproject.toml          # Dependencies (includes openpyxl)
├── .env                    # Environment variables (not committed)
```

## Models

### User (users.User)
- Extends `AbstractUser` (has username, password, email, etc.)
- Added `type` field: HR, SGM (Senior General Manager), GM (General Manager), AGM (Assistant General Manager), MR (Medical Representative)
- `AUTH_USER_MODEL = "users.User"` in settings

### Doctor (doctors.Doctor)
- `name` — CharField(255)
- `nmc_number` — CharField(50), unique, "Nepal Medical Council Number"
- `area` — CharField(255), free text (used as "City" in reports)
- `specialization` — CharField(255), optional
- Ordered by name; managed via Django admin only

### Area (tour_plans.Area)
- `name` — CharField(255), unique
- Shared between TourPlan and DailyCoverage
- Managed via Django admin

### TourPlan (tour_plans.TourPlan)
- `created_by` — FK to User (nullable)
- `reporting_date` — DateField, auto-set on create
- `plan_date` — DateField
- `area` — FK to Area (PROTECT)
- `worked_with` — FK to User, optional
- `remarks` — TextField, optional
- `status` — choices: pending / approved / rejected (default: pending)
- HR must approve before employee can add daily coverage for that date

### DoctorEmployeeRelation (doctor_employee_relation.DoctorEmployeeRelation)
- `employee` — FK to User
- `doctor` — FK to Doctor
- `msl_number` — PositiveIntegerField, optional (importance rank — drives category)
- `relation_date` — DateField, optional
- `status` — choices: pending / approved / rejected (default: pending)
- Unique constraint on (employee, doctor)
- MRs request assignments; HR users (is_staff + type=="HR") approve/reject

### DailyCoverage (daily_coverage.DailyCoverage)
- `created_by` — FK to User (nullable)
- `report_date` — DateField
- `doctor` — FK to Doctor (PROTECT)
- `actual_working_place` — FK to Area (PROTECT)
- `call_time` — TimeField
- `products` — CharField(255), optional
- `worked_with` — CharField(255), optional (free text)
- `remarks` — TextField, optional
- Edit/delete allowed within 2 days of `created_at`; enforced in view with `PermissionDenied`

## Doctor Classification (MSL-based)
Used across all reports and the daily coverage calendar:
| Class | MSL range | Monthly visit target |
|---|---|---|
| Super Core | 1 – 25 | 4 |
| Core | 26 – 75 | 2 |
| VIP | 76+ (or no MSL) | 1 |

Defined in `reports/views.py` as `SUPER_CORE_MAX = 25`, `CORE_MAX = 75`, `VISIT_TARGETS`.

## Tour Plan → Daily Coverage Flow
1. MR submits tour plan (status: pending)
2. HR approves/rejects from `/tour_plans/review/`
3. Calendar shows approved days as clickable ("Plan Approved" badge)
4. MR adds daily coverage only for approved-plan days (enforced on POST)
5. Coverage can be edited/deleted within 2 days; calendar shows "Added" badge linking to list

## API Endpoints (Django Ninja)
- `POST /api/token/pair` — Get JWT access + refresh tokens
- `POST /api/token/refresh` — Refresh access token
- `GET /api/doctors/` — List all doctors (JWT auth required)
- Swagger docs at `/api/docs`

## Auth Flow
- **Templates:** Django session auth (`@login_required` + `@never_cache`)
- **API:** JWT via `django-ninja-jwt` (for future React/mobile)
- Logout uses POST (Django 5+ requirement)
- `@never_cache` on all authenticated views to prevent back-button access after logout
- HR-only views check `user.is_staff and user.type == "HR"` and raise `PermissionDenied`
- Staff views (reports with employee dropdown) check `user.is_staff`

## Credentials (dev only)
- **Admin login:** `admin` / `admin123` (type: GM, superuser)
- **DB:** `pharmasfo` / `pharmasfo_dev_password` on host port `5433`

## Key URLs
- http://localhost:8000/ — Dashboard
- http://localhost:8000/login/ — Login page
- http://localhost:8000/doctors/ — Doctor list
- http://localhost:8000/doctor_employee_relation/ — My assigned doctors
- http://localhost:8000/doctor_employee_relation/add/ — Request a doctor assignment
- http://localhost:8000/review_requests/ — HR: pending doctor requests
- http://localhost:8000/review_requests/<id>/ — HR: approve/reject per employee
- http://localhost:8000/tour_plans/ — Tour plan list (with status)
- http://localhost:8000/tour_plans/add/ — Add tour plans (bulk)
- http://localhost:8000/tour_plans/review/ — HR: pending tour plans
- http://localhost:8000/tour_plans/review/<id>/ — HR: approve/reject per employee
- http://localhost:8000/daily_coverage/ — Monthly calendar
- http://localhost:8000/daily_coverage/add/ — Add daily coverage (bulk)
- http://localhost:8000/daily_coverage/records/ — My coverage list (edit/delete)
- http://localhost:8000/daily_coverage/<pk>/edit/ — Edit a record (within 2 days)
- http://localhost:8000/daily_coverage/<pk>/delete/ — Delete a record (within 2 days)
- http://localhost:8000/reports/daily-activity/ — Daily Activity Report
- http://localhost:8000/reports/monthly-activity/ — Monthly Activity Report (chart + table)
- http://localhost:8000/reports/monthly-target/ — Monthly Target Report (traffic-light dots)
- http://localhost:8000/reports/yearly-activity/ — Yearly Activity Report
- http://localhost:8000/reports/yearly-activity/export/ — Excel export of yearly report
- http://localhost:8000/admin/ — Django admin (add doctors, areas, users here)
- http://localhost:8000/api/docs — API documentation (Swagger)

## Design Decisions
- HR users (is_staff=True, type="HR") approve doctor assignments and tour plans
- Tour plan approval gates daily coverage entry for that date
- Doctor classification (Super Core/Core/VIP) derived from MSL number at report time, not stored
- Daily coverage edit window is 2 days from `created_at` (defined as `EDIT_WINDOW_DAYS = 2`)
- Chemist/Stockist features are planned but not yet implemented
- Reports use Gregorian dates (Nepali BS calendar conversion deferred)
- Excel export uses openpyxl, served as streaming `HttpResponse`
- `reports/` is a plain Python module (no models), not a Django app — no INSTALLED_APPS entry
- Timezone set to `Asia/Kathmandu`
- DB host port is 5433 (5432 was already in use on the dev machine)
