# PharmaSFO - Pharma Sales Force Automation

> See `documentation.md` for full architecture, per-app, and end-to-end flow documentation.

## Stack
- **Backend:** Django 5.x + Django Ninja (REST API with JWT via django-ninja-jwt)
- **Database:** PostgreSQL 16 (Dockerized)
- **Package manager:** uv
- **Containerization:** Docker Compose
- **Frontend:** Django templates styled with the Lumo SFA design system (`static/lumo/`); plan to migrate to React later
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
│   ├── models.py           # User(AbstractUser) with hierarchical type field (MSO … Admin) + TYPE_RANK
│   ├── admin.py            # UserAdmin with type in fieldsets
│   ├── context_processors.py  # nav_counts — pending-approval counts for HR sidebar badges
│   ├── forms.py            # UserCreateForm — HR onboarding form (Admin type excluded; HR type ⇒ is_staff)
│   ├── views.py            # dashboard view (live stats, today's coverage, targets) + HR-only: add/list/edit/deactivate/delete_user, team_management (assign managers)
├── doctors/                # Doctors app
│   ├── models.py           # Doctor(name, nmc_number, area, specialization)
│   ├── admin.py            # DoctorAdmin with search/filter
│   ├── forms.py            # DoctorForm (HR add-doctor form; reused by edit_doctor)
│   ├── views.py            # doctor_list, add_doctor, edit_doctor, delete_doctor (all HR-only)
├── doctor_employee_relation/  # Doctor-MR assignment app
│   ├── models.py           # DoctorEmployeeRelation (employee, doctor, msl_number, status)
│   ├── views.py            # list, add, HR review views
├── notifications/          # In-app notifications
│   ├── models.py           # Notification (recipient, message, url, is_read, created_at)
│   ├── utils.py            # notify(recipients, message, url="") — one user or an iterable
│   ├── context_processors.py  # unread_count — badge count + latest 8 for the topbar dropdown (every page)
│   ├── views.py            # notification_list (paginated), mark_notification_read, mark_all_read
├── tour_plans/             # Tour planning app
│   ├── models.py           # Area, TourPlan (with status: pending/approved/rejected)
│   ├── forms.py            # TourPlanBulkForm
│   ├── views.py            # list, add, HR review/approve views
├── daily_coverage/         # Daily call reporting app
│   ├── models.py           # DailyCoverage, ChemistCoverage, StockistCoverage
│   ├── forms.py            # DailyCoverageBulkForm, DailyCoverageForm
│   ├── views.py            # calendar, add (bulk doctor/chemist/stockist), list, edit, delete
│   ├── templatetags/
│   │   └── dc_tags.py      # get_item filter (dict lookup in templates)
├── reports/                # Reporting module (no models, no INSTALLED_APPS entry needed)
│   ├── views.py            # daily_activity, monthly_activity, monthly_target, yearly_activity
├── api/                    # Django Ninja API
│   ├── api.py              # NinjaAPI + JWT controller + /doctors endpoint
├── templates/
│   ├── base.html           # Lumo app shell: desktop top-nav dropdowns + mobile sidebar drawer, topbar user menu (POST logout); `legacy_css` block; messages→toast bridge
│   ├── partials/
│   │   └── nav.html        # Primary nav, rendered twice: sidebar drawer (mobile) and topbar (desktop, `with topnav=True`) — flat daily-loop links + Reports/HR dropdowns
│   ├── 403.html / 404.html # Styled error pages (Django picks them up automatically)
│   ├── users/
│   │   └── add_user.html   # HR: onboard employee (UserCreateForm)
│   ├── dashboard.html      # Lumo rep dashboard (stats, today's coverage, targets, upcoming plans)
│   ├── registration/
│   │   └── login.html
│   ├── doctors/
│   │   ├── doctor_list.html
│   │   ├── add_doctor.html / edit_doctor.html  # Shared DoctorForm layout
│   │   └── delete_doctor.html          # GET-confirm page: relations + coverage table + cascade checkbox
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
│   │   ├── calendar.html               # Lumo monthly calendar in Bikram Sambat; days gated by tour plan approval
│   │   ├── add_daily_coverage.html     # Tabbed bulk add: Doctor / Chemist / Stockist
│   │   ├── daily_coverage_list.html    # List with edit/delete (2-day window)
│   │   └── edit_daily_coverage.html
│   ├── notifications/
│   │   └── notification_list.html      # Full paginated list; topbar dropdown lives in base.html
│   └── reports/
│       ├── daily_activity_report.html
│       ├── monthly_activity_report.html  # Chart.js frequency diagram + list of data tabs
│       ├── monthly_target_report.html    # Traffic-light dots per doctor
│       └── yearly_activity_report.html  # BS-year doctor × BS-month visit grid + MSL frequency chart + Excel export
├── static/
│   ├── css/app.css         # App-level styles on top of Lumo (skip link, .table--stack mobile card rows)
│   ├── css/style.css       # Legacy styling — no longer loaded (all pages ported to Lumo); safe to delete
│   └── lumo/               # Lumo design system: tokens.css, components.css, lumo.js — verbatim copies, do not hand-edit
├── lumo/design_handoff_lumo_sfa/  # Design handoff bundle (README.md there is the design source of truth)
├── docker-compose.yml      # web + db services
├── Dockerfile              # Python 3.12-slim + uv
├── pyproject.toml          # Dependencies (includes openpyxl, nepali-datetime)
├── .env                    # Environment variables (not committed)
├── documentation.md        # Full architecture, per-app & end-to-end flow docs
├── improvements.md         # Prioritised improvement / tech-debt checklist
```

## Models

### User (users.User)
- Extends `AbstractUser` (has username, password, email, etc.)
- `type` field — position, in **increasing hierarchy order**: MSO, Sr. MSO, DASM, ASM, Sr. ASM, DRSM, RSM, Sr. RSM, DSM, SM, Sr. SM, AGM, GM, Sr. GM, HR, Admin (default: MSO)
- `manager` — self-FK (`related_name="team_members"`, `on_delete=SET_NULL`), the higher-position person this employee reports to; forms the reporting tree. HR sets it on the Team management page (`/teams/`)
- `TYPE_RANK` (position → rank), `hierarchy_level` property, and `viewable_report_users()` — **team-scoped**: self plus this user's entire downstream reporting subtree (all direct + indirect reports via `manager`, walked by `team_member_ids()`). HR-type users and superusers see everyone; employees with no manager are visible only to HR/superusers
- Legacy types migrated in `users.0003`: MR → MSO, SGM → SR_GM
- `AUTH_USER_MODEL = "users.User"` in settings

### Doctor (doctors.Doctor)
- `name` — CharField(255)
- `nmc_number` — CharField(50), unique, "Nepal Medical Council Number"
- `hospital` — FK to Hospital (PROTECT), **required** (existing rows backfilled in `doctors.0005` with a per-area "General Hospital")
- `area` — CharField(255), free text (used as "City" in reports)
- `specialization` — CharField(255), optional
- `phone` — CharField(20), optional
- `email` — EmailField, optional
- Ordered by name; added, edited, and deleted via Django admin or the HR "Add/Edit Doctor" forms (`/doctors/add/`, `/doctors/<pk>/edit/`, `/doctors/<pk>/delete/` — same `_can_manage_doctors` gate as the directory itself)
- `/doctors/<pk>/delete/` is a GET-confirm/POST-act page (`delete_doctor.html`), not a JS `confirm()`: it lists every `DoctorEmployeeRelation` that will cascade and, if any `DailyCoverage` rows reference the doctor, a table of them plus a required "also delete these" checkbox — `ProtectedError` blocks a bare delete, but ticking the box deletes the coverage first, then the doctor. Every affected rep (assignment removed, coverage removed, or both — differentiated per user) gets a `notifications.notify()` call; editing a doctor notifies reps with an **approved** assignment only
- Phone/email surface in the doctor list ("Contact" column + client-side search), the add form, admin, and `GET /api/doctors/`

### Hospital (doctors.Hospital)
- `name` — CharField(255); `area` — FK to Area (PROTECT); `phone` — optional
- Unique on (name, area); managed via Django admin
- Surfaces in the Add Doctor form (required select), doctor list column, `GET /api/doctors/` (`hospital_id` + `hospital_name`), and the Yearly Activity report's "Hospital" column (previously derived from worked areas)

### Chemist / Stockist masters (daily_coverage.Chemist / .Stockist)
- `name` — CharField(255); `area` — FK to Area (PROTECT); `phone` — optional; unique on (name, area)
- Added by HR at `/chemists/add/` and `/stockists/add/` (shared `add_partner.html` template) or via Django admin
- The daily-coverage bulk form picks chemists/stockists from these directories (select pre-fills the entry's area); coverage rows still store the name as text

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
- Field reps (MSOs) request assignments; HR users (is_staff + type=="HR") approve/reject

### DailyCoverage (daily_coverage.DailyCoverage)
- `created_by` — FK to User (nullable)
- `report_date` — DateField
- `work_day` — choices: full_day / half_day / night_transit / meeting (default full_day); one **required** "Working day" select on the add form applies to all doctor entries in that submission; both it and "No Doctor Coverage Available" are scoped to the single Date field described below (they read oddly as "per submission" settings otherwise)
- `doctor` — FK to Doctor (PROTECT)
- `actual_working_place` — FK to Area (PROTECT)
- `call_time` — TimeField
- `products` — CharField(255), blank at model level but **required by the add form** (client gate + server-side skip)
- `worked_with` — CharField(255), stored as text; add/edit forms offer a select of "Self" + colleagues, **required on add** (defaults to "Self")
- `remarks` — TextField, optional
- Edit/delete allowed within 2 days of `created_at`; enforced in view with `PermissionDenied`

### ChemistCoverage / StockistCoverage (daily_coverage)
- `created_by` — FK to User (nullable)
- `report_date` — DateField
- `name` — CharField(255) — chemist/stockist name (picked from the Chemist/Stockist master directories in the bulk form; stored as text)
- `area` — FK to Area (PROTECT)
- `call_time` — TimeField
- `created_at` — DateTimeField (no `updated_at` yet)
- Structurally identical to each other; entered alongside doctors in the same bulk add form
- Logging only chemist/stockist on a doctor-less day requires a "no doctor coverage" reason (gate only — the reason is validated but not persisted)
- Listed in Coverage records via `?type=chemist|stockist` with edit/delete in the same 2-day window (`edit_chemist_coverage` etc.); also surfaced in the Daily Activity report

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
4. MR adds daily coverage (doctor + optional chemist/stockist) only for approved-plan days (enforced on POST for every row)
5. Logging only chemist/stockist on a doctor-less day requires a "no doctor coverage" reason; the form's Chemist/Stockist tabs stay locked until a doctor entry exists or that reason is given (client-side gate + server-side validation)
6. All coverage (doctor/chemist/stockist) can be edited/deleted within 2 days from Coverage records; calendar shows "Added (n)" badge (doctor rows only) linking to list — the badge swaps its dot for a lock icon (+ tooltip and legend entry) once every entry on that day is past the edit window
7. **Every non-muted calendar day is clickable** (`calendar.html`) except a locked "Added" day: approved days and "Added" days not yet locked go to Add Daily Coverage (`?date=`); "Added" is a `<div data-cell-href>` — its whole area targets Add Daily Coverage while the inner "Added (n)" badge keeps its own link to Coverage records, told apart by a delegated click/keydown handler (`e.target.closest('a')` wins) so the nested link isn't swallowed; pending and no-plan days are a plain `<a>` (new `.cal__cell--clickable` in `app.css`, since Lumo's `.cal__cell--approved` is semantically "approved") to Add Tour Plan (`?date=`), which reads that param in `add_tour_plan.html`'s JS to preset the first row's date (only the first — "Add another day" keeps incrementing from the last row as before)
8. The add form walks Doctor → Chemist → Stockist with a footer Next button; Next and Save All stay disabled until every added row's required fields are complete (client-side; server re-validates)
9. **One Date field for the whole add form**, shown once above the tabs (`initial_date` — from `?date=`/`selected_date`, else defaults server-side to today via `timezone.localdate()`; the page copy is singular — "your ... visits for the day" — this was always the intent). Doctor/Chemist/Stockist entry rows no longer have their own date picker; every entry (any tab) reads `report_date` from this one field at sync time, so adding several doctors (or chemists, or stockists) always means several people on the *same* day. Changing the date afterward re-tags every already-added row. Server-side is untouched — each entry in the posted JSON still carries its own `report_date` and is validated against `approved_dates` independently; the client now just always sends the same value for all of them.

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
- HR-only views check `user.is_superuser or (user.is_staff and user.type == "HR")` and raise `PermissionDenied`
- **Reports:** team-scoped visibility via `_get_employee` (reports/views.py) → `User.viewable_report_users()` — a user sees their own reports plus their entire downstream reporting team (via the `manager` chain); HR/superusers see everyone; requesting anyone outside that set 404s; template flag `can_view_others` shows the employee dropdown

## Credentials (dev only)
- **Admin login:** `admin` / `admin123` (type: GM, superuser)
- **DB:** `pharmasfo` / `pharmasfo_dev_password` on host port `5433`

## Key URLs
- http://localhost:8000/ — Dashboard
- http://localhost:8000/login/ — Login page
- http://localhost:8000/doctors/ — Doctor directory (**HR/superuser only**; reps see their doctors via My assignments)
- http://localhost:8000/doctors/add/ — HR: add a new doctor
- http://localhost:8000/chemists/add/ — HR: add a chemist to the directory
- http://localhost:8000/stockists/add/ — HR: add a stockist to the directory
- http://localhost:8000/users/add/ — HR: onboard a new employee (Admin position excluded; picking HR sets is_staff)
- http://localhost:8000/teams/ — HR: Team management — assign each employee's manager (reporting chain); scopes report visibility to teams
- http://localhost:8000/doctor_employee_relation/ — My assigned doctors (HR/superuser get an employee switcher to view anyone's list; `/<employee_id>/` variant)
- http://localhost:8000/doctor_employee_relation/add/ — Request a doctor assignment
- http://localhost:8000/review_requests/ — HR: pending doctor requests
- http://localhost:8000/review_requests/<id>/ — HR: approve/reject per employee
- http://localhost:8000/tour_plans/ — Tour plan list (with status)
- http://localhost:8000/tour_plans/add/ — Add tour plans (bulk)
- http://localhost:8000/tour_plans/review/ — HR: pending tour plans
- http://localhost:8000/tour_plans/review/<id>/ — HR: approve/reject per employee
- http://localhost:8000/daily_coverage/ — Monthly calendar
- http://localhost:8000/daily_coverage/add/ — Add daily coverage (bulk)
- http://localhost:8000/daily_coverage/records/ — My coverage list (edit/delete; `?type=doctor|chemist|stockist`)
- http://localhost:8000/daily_coverage/<pk>/edit/ — Edit a record (within 2 days)
- http://localhost:8000/daily_coverage/<pk>/delete/ — Delete a record (within 2 days)
- http://localhost:8000/reports/daily-activity/ — Daily Activity Report
- http://localhost:8000/reports/monthly-activity/ — Monthly Activity Report (chart + table)
- http://localhost:8000/reports/monthly-activity/export/ — Excel export of monthly report (Daily Calls + MSL Frequency sheets)
- http://localhost:8000/reports/monthly-target/ — Monthly Target Report (traffic-light dots)
- http://localhost:8000/reports/monthly-target/export/ — Excel export of target report (status-tinted rows + summary)
- http://localhost:8000/reports/yearly-activity/ — Yearly Activity Report (**BS year**: Baishakh–Chaitra grid + MSL frequency bar chart)
- http://localhost:8000/reports/yearly-activity/export/ — Excel export of yearly report
- http://localhost:8000/admin/ — Django admin (add doctors, areas, users here)
- http://localhost:8000/api/docs — API documentation (Swagger)

## Design Decisions
- **UI:** Lumo SFA design system — `static/lumo/` files are verbatim copies from `lumo/design_handoff_lumo_sfa/` (never re-derive colors/spacing; extend by composing `components.css` classes). `base.html` renders the app shell for all authenticated pages. The `.scrim` div must stay the **last** child of `.app` — as first child it occupies the grid's first cell and breaks the desktop layout.
- **Navigation:** desktop (>860px) hides the sidebar and renders `templates/partials/nav.html` in the topbar: Dashboard as a flat text link plus three dropdowns — My Work (Calendar, Coverage, Tour plans, My doctors), Reports, and HR (sectioned into Approvals/Manage with `.nav-label`/`.nav-sep`; combined pending badge on the collapsed trigger). A primary `+ Log visit` CTA (→ add daily coverage), a `.topnav__notif` bell (unread badge + dropdown of the latest 8, "Mark all read", "View all" → `/notifications/`), and a `.topnav__user` menu (avatar → identity + POST logout) sit on the right; the bell and user menu show at every width. The bell's dropdown panel is `position:fixed; left/right:var(--space-3)` (viewport-anchored) below 861px instead of the desktop `position:absolute; right:0` (trigger-anchored) — on phones the bell sits close to the equally-narrow avatar trigger, so a 340px panel anchored to it would land mostly off the left edge of the screen; anchoring to the viewport instead can't overflow at any width. Groups reuse Lumo's `data-collapsible`/`is-collapsed` toggle restyled as popovers in `app.css`; base.html's inline JS adds one-open-at-a-time, outside-click/Escape closing, and `has-active` on the current group's trigger. ≤860px keeps the sidebar drawer rendering the same partial (groups expanded, icons shown). The topbar breadcrumb was removed — `{% block breadcrumb %}` in page templates is defined but unrendered.
- **Action feedback:** views use `django.contrib.messages` (success/warning/error) for every create/edit/delete/approve/reject, including saved-vs-skipped counts on bulk forms; `base.html` renders them as Lumo toasts via `window.lumoToast` (defined in `lumo/lumo.js`). Add a message in the view and it just works.
- **A11y:** skip-to-content link in `base.html`, `aria-current="page"` set on the active nav item, autofocus on the primary field of add forms; inline SVG favicon (data URI) in `base.html` + `login.html`
- **Mobile tables:** wide list tables use `.table.table--stack` (defined in `static/css/app.css`) — under 860px each row collapses into a labeled card; every `<td>` needs `data-label`, `.stack-hide` hides noise cells (e.g. SN). Grid-like report tables (monthly list, yearly) intentionally keep horizontal scroll.
- **Bulk-entry rows** (Add Tour Plan's days; Add Daily Coverage's doctor/chemist/stockist entries) use `.entry-fields` (`app.css`) instead of Lumo's `.grid--2`: one field per line under 860px (same as `.grid--2`'s own collapse, just self-contained), a single flex line at ≥861px so adding several entries doesn't turn into a long vertical scroll. Each field's flex-basis is set inline per row template (Date/Call Time stay narrow, Doctor/Products get more room); a field flagged `.entry-fields__full` (Remarks) always keeps its own full-width line. All three row-builders (`renderEntry` in `add_tour_plan.html`; `makeRow` in `add_daily_coverage.html`, shared by doctor/chemist/stockist) use it — only wrapper classes/inline widths changed, no field `name`/`class` selectors touched, so the existing sync-to-hidden-JSON and tab validation logic needed no changes.
- **All pages are Lumo-ported** and empty the `{% block legacy_css %}` — `css/style.css` is no longer loaded anywhere (kept only for reference; safe to delete). The base template's `legacy_css` default remains as a safety net for any future non-ported template. Shared page patterns: `page-header` (title + sub + `page-actions`), `table-toolbar` for filters, `.table-wrap > .table` with `badge--success/warning/danger` status pills, `.empty` states, `card__footer` with ghost Cancel + primary submit for forms; report charts read colors from Lumo CSS variables via `getComputedStyle`
- Report visibility follows the position hierarchy (see User model); "subordinate" currently means *any lower position* — direct-report chains would need a `manager` FK
- HR users (is_staff=True, type="HR") approve doctor assignments and tour plans
- Tour plan approval gates daily coverage entry for that date
- Doctor classification (Super Core/Core/VIP) derived from MSL number at report time, not stored
- Daily coverage edit window is 2 days from `created_at` (defined as `EDIT_WINDOW_DAYS = 2`)
- Chemist/Stockist coverage is implemented (models + bulk add form + list/edit/delete + Daily Activity report); inclusion in monthly/target/yearly reports is still pending
- List views (`daily_coverage_list`, `doctor_employee_relation_list`) paginate at 25/page with date/status filters
- **Coverage calendar renders in Bikram Sambat** via `nepali-datetime`: the `/daily_coverage/<year>/<month>/` URL params are **BS**, weeks run Sunday-first, cells show the BS day (AD date bottom-right), and all queries/links use the BS month's AD range. Storage stays Gregorian; the monthly/yearly reports render BS months (activity + target parse a BS `month=YYYY-MM` param via `_parse_bs_month`, filtering by the BS month's AD span)
- **BS date picker** (`static/js/bs-date.js` + `{% bs_calendar_json %}` tag in dc_tags, both loaded by base.html): renders Year/Month/Day BS selects that write ISO AD into a hidden input. Auto-enhances every server-rendered `input[type=date]` (filters, edit forms); JS-built entry rows call `bsDateAttach(input, {defaultToday})`. Month inputs (`type=month`) get the BS month picker below
- **BS month picker** (`static/js/month-picker.js`, loaded by the monthly target + activity report templates): auto-enhances `input[type=month]` into a grid popover — `‹ BS year ›` steppers (clamped to the `bs_calendar_json` table, embedded by base.html as `{% bs_calendar_json 5 1 %}`), 4×3 Baishakh–Chaitra grid, "This month" shortcut — writing **BS** `YYYY-MM` to the hidden input for `_parse_bs_month` (native `type=month` speaks AD, hides year scroll in Chrome, and is unsupported in Firefox/desktop Safari)
- Excel export uses openpyxl, served as streaming `HttpResponse`
- `reports/` is a plain Python module (no models), not a Django app — no INSTALLED_APPS entry
- Timezone set to `Asia/Kathmandu`
- DB host port is 5433 (5432 was already in use on the dev machine)
