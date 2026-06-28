# PharmaSFO - Pharma Sales Force Automation

## Stack
- **Backend:** Django 6 + Django Ninja Extra (REST API with JWT via django-ninja-jwt)
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
│   ├── models.py           # Doctor(name, nmc_number, area)
│   ├── admin.py            # DoctorAdmin with search/filter
│   ├── views.py            # doctor_list view
├── api/                    # Django Ninja API
│   ├── api.py              # NinjaExtraAPI + JWT controller + /doctors endpoint
├── templates/
│   ├── base.html           # Base layout with navbar (shows user type, POST logout)
│   ├── dashboard.html      # Dashboard with "Doctors List" button
│   ├── registration/
│   │   └── login.html      # Login form
│   └── doctors/
│       └── doctor_list.html # Doctor table
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
- Ordered by name
- Managed via Django admin only (no frontend add/edit)

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

## Credentials (dev only)
- **Admin login:** `admin` / `admin123` (type: GM, superuser)
- **DB:** `pharmasfo` / `pharmasfo_dev_password` on host port `5433`

## Key URLs
- http://localhost:8000/ — Dashboard (requires login)
- http://localhost:8000/login/ — Login page
- http://localhost:8000/doctors/ — Doctor list
- http://localhost:8000/admin/ — Django admin (add doctors here)
- http://localhost:8000/api/docs — API documentation (Swagger)

## Design Decisions
- All user types have the same permissions for now (role-based access to be added later)
- Doctor "area" is free text (not a predefined list, for now)
- Doctors can only be added via Django admin, not the frontend
- Timezone set to `Asia/Kathmandu`
- DB host port is 5433 (5432 was already in use on the dev machine)
