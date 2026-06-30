# PharmaSFO - Pharma Sales Force Automation

## Stack
- **Backend:** Django 5.x + Django Ninja (REST API with JWT via django-ninja-jwt)
- **Database:** PostgreSQL 16 (Dockerized)
- **Package manager:** uv
- **Containerization:** Docker Compose
- **Frontend:** Django templates (plan to migrate to React later)
- **Auth:** Session-based for templates, JWT for API (ready for SPA/mobile)

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
│   ├── models.py           # Area, TourPlan models
│   ├── forms.py            # TourPlanBulkForm
│   ├── views.py            # tour_plan_list, add_tour_plan views
├── daily_coverage/         # Daily call reporting app
│   ├── models.py           # DailyCoverage model
│   ├── forms.py            # DailyCoverageBulkForm
│   ├── views.py            # daily_coverage_calendar, add_daily_coverage views
├── api/                    # Django Ninja API
│   ├── api.py              # NinjaAPI + JWT controller + /doctors endpoint
├── templates/
│   ├── base.html           # Base layout with navbar (shows user type, POST logout)
│   ├── dashboard.html      # Dashboard
│   ├── registration/
│   │   └── login.html      # Login form
│   ├── doctors/
│   │   └── doctor_list.html
│   ├── doctor_employee_relation/
│   │   ├── doctor_employee_relation_list.html
│   │   ├── add_doctor_employee_relation.html
│   │   ├── hr_review_requests.html       # HR: list employees with pending requests
│   │   └── hr_review_employee_requests.html  # HR: approve/reject per employee
│   ├── tour_plans/
│   │   ├── tour_plan_list.html
│   │   └── add_tour_plan.html
│   └── daily_coverage/
│       ├── calendar.html   # Monthly calendar view of coverage entries
│       └── add_daily_coverage.html  # Bulk add form
├── static/css/style.css    # App styling
├── docker-compose.yml      # web + db services
├── Dockerfile              # Python 3.12-slim + uv
├── pyproject.toml          # Dependencies
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
- `area` — CharField(255), free text
- `specialization` — CharField(255), optional
- Ordered by name
- Managed via Django admin only (no frontend add/edit)

### Area (tour_plans.Area)
- `name` — CharField(255), unique
- Shared between TourPlan and DailyCoverage
- Managed via Django admin

### TourPlan (tour_plans.TourPlan)
- `created_by` — FK to User (nullable)
- `reporting_date` — DateField, auto-set on create
- `plan_date` — DateField
- `area` — FK to Area (PROTECT)
- `worked_with` — FK to User, optional (who accompanied)
- `remarks` — TextField, optional
- Filtered by `created_by` in list view; bulk-add form

### DoctorEmployeeRelation (doctor_employee_relation.DoctorEmployeeRelation)
- `employee` — FK to User
- `doctor` — FK to Doctor
- `msl_number` — PositiveIntegerField, optional (importance rank)
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
- Ordered by `-report_date`, `-created_at`
- Filtered by `created_by` in views; bulk-add form

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

## Credentials (dev only)
- **Admin login:** `admin` / `admin123` (type: GM, superuser)
- **DB:** `pharmasfo` / `pharmasfo_dev_password` on host port `5433`

## Key URLs
- http://localhost:8000/ — Dashboard (requires login)
- http://localhost:8000/login/ — Login page
- http://localhost:8000/doctors/ — Doctor list
- http://localhost:8000/doctor_employee_relation/ — My assigned doctors (filterable by status)
- http://localhost:8000/doctor_employee_relation/add/ — Request a doctor assignment
- http://localhost:8000/review_requests/ — HR: list employees with pending doctor requests
- http://localhost:8000/review_requests/<employee_id>/ — HR: approve/reject per employee
- http://localhost:8000/tour_plans/ — Tour plan list (filterable by month)
- http://localhost:8000/tour_plans/add/ — Add tour plans (bulk form)
- http://localhost:8000/daily_coverage/ — Monthly calendar of daily coverage entries
- http://localhost:8000/daily_coverage/add/ — Add daily coverage entries (bulk form)
- http://localhost:8000/admin/ — Django admin (add doctors, areas, users here)
- http://localhost:8000/api/docs — API documentation (Swagger)

## Design Decisions
- HR users (is_staff=True, type="HR") can review and approve/reject doctor-employee relation requests
- All other user types have the same permissions for now
- Doctor "area" is free text; `Area` (for tour plans / daily coverage) is a managed FK model
- Doctors and Areas can only be added via Django admin, not the frontend
- Tour plans and daily coverage use bulk JSON forms (multiple entries submitted at once)
- Daily coverage calendar view is scoped to the logged-in user's entries
- Timezone set to `Asia/Kathmandu`
- DB host port is 5433 (5432 was already in use on the dev machine)
