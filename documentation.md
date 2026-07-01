# PharmaSFO — System Documentation

Comprehensive reference for the PharmaSFO (Pharma Sales Force Automation) backend.
This document explains **what each app does**, **how its pieces fit together**, and
**how the end-to-end business flows work**. It complements `CLAUDE.md` (quick-start /
conventions) and `improvements.md` (open work items).

---

## 1. Overview

PharmaSFO digitises the daily work of a pharmaceutical field sales team in Nepal.
The core actors are **Medical Representatives (MRs)** who visit doctors, chemists and
stockists, and **HR** users who approve what MRs are allowed to do. The system tracks:

- **Who** an MR is allowed to call on (doctor assignments).
- **Where** an MR plans to work on a given day (tour plans).
- **What** actually happened on that day (daily coverage).
- **How well** targets were met (reports).

The chain is deliberately gated: an MR cannot record a day's work unless HR has first
approved a tour plan for that day, and an MR can only report against doctors HR has
assigned to them. This produces clean, trustworthy data for the reporting layer.

### Stack

| Layer | Technology |
|---|---|
| Web framework | Django 5.x |
| REST API | Django Ninja + `django-ninja-jwt` (JWT auth) |
| Database | PostgreSQL 16 (Docker) |
| Frontend | Django server-rendered templates (+ vanilla JS for dynamic forms, Chart.js for charts) |
| Excel export | openpyxl |
| Package manager | uv |
| Containerisation | Docker Compose (`web` + `db`) |
| Timezone | `Asia/Kathmandu`, `USE_TZ = True` |

### App map

| Python package | Django app? | Responsibility |
|---|---|---|
| `PharmaSFO/` | — (project config) | settings, root URL routing, WSGI/ASGI |
| `users/` | ✅ | Custom `User` model + roles, dashboard |
| `doctors/` | ✅ | Doctor master data |
| `doctor_employee_relation/` | ✅ | MR ↔ Doctor assignments + HR approval |
| `tour_plans/` | ✅ | Areas, day-level tour plans + HR approval |
| `daily_coverage/` | ✅ | Doctor / chemist / stockist call reporting |
| `reports/` | ❌ (plain module) | Daily / monthly / yearly analytics + Excel |
| `api/` | ❌ (router module) | Django Ninja JWT API |

> **Note:** `reports/` and `api/` have **no models and no `INSTALLED_APPS` entry**.
> They are plain Python modules whose views/routers are wired directly in
> `PharmaSFO/urls.py`. Only apps with models or migrations are registered in
> `INSTALLED_APPS`.

---

## 2. Architecture & Request Lifecycle

There are two distinct entry paths into the system:

```
                    ┌─────────────────────────────────────────────┐
   Browser  ───────▶│  Session auth  →  @login_required views      │──▶ Django templates
   (MR / HR)        │  (CSRF + cookies, server-rendered HTML)      │     (HTML response)
                    └─────────────────────────────────────────────┘
                    ┌─────────────────────────────────────────────┐
   API client ─────▶│  JWT auth  →  Django Ninja routers           │──▶ JSON
   (future SPA/     │  (Bearer access token)                       │
    mobile)         └─────────────────────────────────────────────┘
```

- **Templates** use Django's session authentication. Every authenticated view is
  decorated with `@login_required` and (almost everywhere) `@never_cache`.
- **API** uses JWT (`django-ninja-jwt`). Access token lives 8 hours, refresh token
  7 days (`settings.NINJA_JWT`). This path exists for the planned React/mobile
  frontend; today only `/api/doctors/` is implemented.

The `reports/` module is **read-only analytics** — it queries the other apps' models
but owns no tables.

---

## 3. Roles, Permissions & Auth

### Roles (`users.User.type`)

`HR`, `SGM` (Senior GM), `GM` (General Manager), `AGM` (Assistant GM),
`MR` (Medical Representative — the default). The `type` field is **descriptive**; it
becomes a *permission* only in combination with Django's built-in `is_staff` flag.

### Three permission tiers used in the code

| Tier | Check | Where used |
|---|---|---|
| **Authenticated** | `@login_required` | Every template view |
| **Staff** | `request.user.is_staff` | Reports (can view *other* employees' data via `?employee_id=`); viewing another employee's relation/assignment pages |
| **HR** | `user.is_authenticated and user.is_staff and user.type == "HR"` (`_is_hr_user`) | All approval/review screens (doctor requests, tour plans) |

Key consequences:

- **Approving** doctor assignments and tour plans requires **HR** specifically.
- **Viewing** another employee's data in reports requires only **staff** (any
  `is_staff` user — e.g. a GM — can act as a supervisor in the report screens).
- A plain MR (`is_staff = False`, `type = "MR"`) can only ever see and act on
  **their own** data.

> `_is_hr_user()` is currently duplicated in `doctor_employee_relation/views.py` and
> `tour_plans/views.py` (flagged in `improvements.md`).

### Auth flow details

- Login/logout use Django's built-in `auth_views.LoginView` / `LogoutView`.
  `LOGIN_URL=/login/`, `LOGIN_REDIRECT_URL=/`, `LOGOUT_REDIRECT_URL=/login/`.
- **Logout is POST-only** (Django 5 requirement) — see the form in `base.html`.
- `@never_cache` is applied to authenticated views so a logged-out user pressing the
  browser **Back** button cannot see cached protected pages. (The four
  `doctor_employee_relation` views are currently missing this — see `improvements.md`.)

---

## 4. Core Domain Concepts (shared across apps)

These ideas recur throughout the system; understanding them once explains most of the
behaviour.

### 4.1 Status lifecycle (`pending → approved / rejected`)

Both `DoctorEmployeeRelation` and `TourPlan` carry a `status` field with the same three
values and the same default (`pending`). The MR creates the record; HR transitions it.
A `rejected` record is **kept** (not deleted) so there is an audit trail.

### 4.2 Doctor classification (MSL-based)

When an MR is assigned a doctor, the assignment carries an **`msl_number`** — an
*importance rank* (lower number = more important). This rank, evaluated **at report
time** (never stored as a category), drives the doctor's class and monthly visit target.

| Class | MSL range | Monthly visit target |
|---|---|---|
| **Super Core** | 1 – 25 | 4 visits |
| **Core** | 26 – 75 | 2 visits |
| **VIP** | 76+ **or no MSL** | 1 visit |

Defined in `reports/views.py`: `SUPER_CORE_MAX = 25`, `CORE_MAX = 75`,
`VISIT_TARGETS = {"super_core": 4, "core": 2, "vip": 1}`, and the `_doctor_category(msl)`
helper. A doctor with a `NULL` MSL falls through to **VIP**.

### 4.3 Tour-plan gating

A day is **"unlocked"** for daily-coverage entry only if the MR has a tour plan for that
day with `status = approved`. This is enforced **twice**:

1. **UI:** the calendar only makes approved days clickable.
2. **Server:** `add_daily_coverage` discards any submitted entry whose `report_date`
   is not in the set of approved tour-plan dates — even chemist/stockist rows.

### 4.4 Edit window

Daily-coverage records can be edited or deleted only within **2 days** of creation
(`EDIT_WINDOW_DAYS = 2`, measured against `created_at`). Enforced in the view layer via
`_can_edit()`, which raises `PermissionDenied` past the window.

### 4.5 Areas

`tour_plans.Area` is a shared lookup table (unique `name`) used by **both** tour plans
(planned area) and daily coverage (actual working place, chemist/stockist area). Managed
via Django admin.

---

## 5. Apps

### 5.1 `users` — Identity & roles

**Purpose:** custom user model that adds a role (`type`) to Django's auth user, plus the
landing dashboard.

**Model — `User(AbstractUser)`** (`users/models.py`)

- Inherits everything from `AbstractUser` (`username`, `password`, `email`, `is_staff`,
  `is_active`, `first_name`, `last_name`, …).
- Adds **`type`** — `TextChoices` (`HR/SGM/GM/AGM/MR`), default `MR`.
- `AUTH_USER_MODEL = "users.User"` (set in settings, must never change after first
  migration).
- `__str__` → `"username (Role Display)"`.

**View — `dashboard`** (`users/views.py`): `@login_required @never_cache`; renders
`dashboard.html`. The dashboard groups links into **My Work**, **Reports**, and
**HR Actions** (the last block renders only when `user.is_staff and user.type == 'HR'`).

**Admin** (`users/admin.py`): extends `BaseUserAdmin`; surfaces `type` in `list_display`,
`list_filter`, and both the change and add fieldsets, so superusers can set roles when
creating users.

**How users are created:** there is **no self-service signup**. Users (and their
`type`/`is_staff` flags) are created in Django admin or via `createsuperuser`.

---

### 5.2 `doctors` — Doctor master data

**Purpose:** the catalogue of doctors an MR can be assigned to and report against.

**Model — `Doctor`** (`doctors/models.py`)

| Field | Type | Notes |
|---|---|---|
| `name` | CharField(255) | Doctor name |
| `nmc_number` | CharField(50), **unique** | "Nepal Medical Council Number" |
| `area` | CharField(255) | Free text; surfaces as **"City"** in reports/Excel |
| `specialization` | CharField(255), blank | Optional; used to group columns in the monthly report |

Ordered by `name`. Added incrementally (migration `0002` introduced `specialization`).

**View — `doctor_list`**: `@login_required @never_cache`; lists **all** doctors
(read-only) to any authenticated user.

**Admin:** search by name/NMC/area, filter by area. **Doctors are created and edited
only through Django admin** — there is no create/update view in the app.

---

### 5.3 `doctor_employee_relation` — MR ↔ Doctor assignments

**Purpose:** records which doctors an MR is responsible for, the importance rank
(`msl_number`) of each, and routes those requests through HR approval. This is the table
that the reporting layer treats as the MR's "doctor list".

**Model — `DoctorEmployeeRelation`** (`doctor_employee_relation/models.py`)

| Field | Type | Notes |
|---|---|---|
| `employee` | FK → User (**CASCADE**) | The MR |
| `doctor` | FK → Doctor (**CASCADE**) | ⚠ Other Doctor FKs use `PROTECT`; this `CASCADE` is flagged in `improvements.md` |
| `msl_number` | PositiveInteger, nullable | Importance rank → drives Super Core/Core/VIP |
| `relation_date` | DateField, nullable | Set to "today" when the MR requests the assignment |
| `status` | pending / approved / rejected | Default `pending` |
| `assigned_at` | DateTime (`auto_now_add`) | When the request row was created |

- **Unique constraint** on `(employee, doctor)` — an MR cannot request the same doctor
  twice.
- Ordered by `doctor__name`.
- Only **approved** relations are counted by the reports (target & yearly reports filter
  on `status = approved`).

**Views** (`doctor_employee_relation/views.py`)

| View | Access | Behaviour |
|---|---|---|
| `doctor_employee_relation_list(employee_id=None)` | login; staff may pass `employee_id` to view another MR, non-staff viewing others → `PermissionDenied` | Lists the employee's relations; optional `?status=` filter (`all`/`pending`/`approved`/`rejected`); ordered by `msl_number, doctor__name`; paginated 25 |
| `add_doctor_employee_relation(employee_id=None)` | same resolution as above | GET shows doctors **not already assigned** to this employee. POST creates a `pending` relation via `get_or_create` (date = today). `msl_number` taken straight from POST |
| `hr_review_requests` | **HR only** | Groups all `pending` requests by employee (with a per-employee count) |
| `hr_review_employee_requests(employee_id)` | **HR only** | Lists one employee's pending relations; POST `approve`/`reject` flips a single relation's `status` |

**Templates:** `doctor_employee_relation_list.html`, `add_doctor_employee_relation.html`,
`hr_review_requests.html`, `hr_review_employee_requests.html`.

**Gotchas / known gaps** (from `improvements.md`): these four views lack `@never_cache`;
`msl_number` is not validated as an integer before hitting the DB; the per-employee
`.count()` is an N+1; and there is no uniqueness guard on `(employee, msl_number)`, so
two doctors could share a rank.

---

### 5.4 `tour_plans` — Areas & day-level plans

**Purpose:** an MR declares, per day, which **area** they intend to work in. HR approves,
which unlocks daily-coverage entry for that date.

**Models** (`tour_plans/models.py`)

**`Area`** — `name` (unique), ordered by name. Shared lookup (see §4.5).

**`TourPlan`**

| Field | Type | Notes |
|---|---|---|
| `created_by` | FK → User (CASCADE, nullable) | The MR who made the plan |
| `reporting_date` | DateField (`auto_now_add`) | Date the plan was filed |
| `plan_date` | DateField | The day being planned |
| `area` | FK → Area (**PROTECT**) | Planned area |
| `worked_with` | FK → User (SET_NULL, nullable) | Optional companion |
| `remarks` | TextField, blank | |
| `status` | pending / approved / rejected | Default `pending`; **approval gates coverage** |
| `created_at` / `updated_at` | DateTime | |

Ordered by `-plan_date, -created_at`.

**Forms** (`tour_plans/forms.py`)

- `TourPlanBulkForm` — a single hidden `entries` `JSONField`. The add page is a JS grid;
  on submit, all rows are serialised into this one JSON field. **This is the form the
  view actually uses.**
- `TourPlanForm` — a conventional `ModelForm` (defined but not wired into the current
  views).

**Views** (`tour_plans/views.py`)

| View | Access | Behaviour |
|---|---|---|
| `tour_plan_list` | login | Shows **only the current user's** plans for a chosen month. Month dropdown spans current year + next year. Defaults to the current month |
| `add_tour_plan` | login | GET renders the JS grid (areas + users passed as JSON). POST decodes `entries`, creating one `TourPlan` per row; rows missing `plan_date` or `area` are **silently skipped**. New plans are `pending` |
| `hr_review_tour_plans` | **HR only** | Groups `pending` plans by employee (with count) |
| `hr_review_employee_tour_plans(employee_id)` | **HR only** | Lists one employee's pending plans; POST `approve`/`reject` flips a single plan's `status` |

**Templates:** `tour_plan_list.html` (status column), `add_tour_plan.html` (bulk JS
grid), `hr_review_tour_plans.html`, `hr_review_employee_tour_plans.html`.

---

### 5.5 `daily_coverage` — The call-reporting core

**Purpose:** the operational heart of the app. An MR records the doctors (and optionally
chemists/stockists) they actually called on, for an HR-approved day. This is the data
every report reads.

**Models** (`daily_coverage/models.py`) — three models:

**`DailyCoverage`** (doctor visits)

| Field | Type | Notes |
|---|---|---|
| `created_by` | FK → User (CASCADE, nullable) | The MR |
| `report_date` | DateField | Day of the visit |
| `doctor` | FK → Doctor (**PROTECT**) | |
| `actual_working_place` | FK → Area (**PROTECT**) | Where the visit happened |
| `call_time` | TimeField | |
| `products` | CharField(255), blank | Products discussed |
| `worked_with` | CharField(255), blank | **Free text** (note: tour plan's `worked_with` is an FK; here it's text) |
| `remarks` | TextField, blank | |
| `created_at` / `updated_at` | DateTime | `created_at` drives the 2-day edit window |

**`ChemistCoverage`** and **`StockistCoverage`** (structurally identical to each other)

| Field | Type |
|---|---|
| `created_by` | FK → User (CASCADE, nullable) |
| `report_date` | DateField |
| `name` | CharField(255) — chemist/stockist name (free text, no master table) |
| `area` | FK → Area (**PROTECT**) |
| `call_time` | TimeField |
| `created_at` | DateTime |

All three order by `-report_date, -created_at`. (Chemist/Stockist lack `updated_at`;
flagged in `improvements.md`.)

**Forms** (`daily_coverage/forms.py`)

- `DailyCoverageBulkForm` — four hidden fields populated by JS:
  `entries` (doctor rows), `chemist_entries`, `stockist_entries` (all JSON), and
  `no_doctor_reason` (text). Used by the **add** page.
- `DailyCoverageForm` — a `ModelForm` over the seven editable doctor fields. Used by the
  **edit** page only.

**Template tag** (`daily_coverage/templatetags/dc_tags.py`): a `get_item` filter for
`dict[key]` lookups in templates — used by the calendar to read the
`days_with_entries` map (`{day_number: visit_count}`).

**Views** (`daily_coverage/views.py`)

#### `daily_coverage_calendar(year=None, month=None)`
Builds a month grid (`calendar.Calendar(firstweekday=0)`, Monday-first). For the logged-in
MR it computes, for the visible month:

- `days_with_entries` → `{day: count}` of **doctor** `DailyCoverage` rows (powers the
  "Added (n)" badge). ⚠ Chemist/stockist-only days are not counted here (known gap).
- `days_approved` / `days_pending` → day numbers from the MR's approved / pending tour
  plans.
- prev/next month for navigation.

Each calendar cell renders one of: **Added (n)** (green, links to the filtered list) →
**Plan Approved** (blue, links to the add page for that date) → **Plan Pending** (amber)
→ plain number (no plan).

#### `add_daily_coverage(selected_date=None)`
The most involved view. On POST it decodes the four hidden fields and runs this logic:

1. Build `approved_dates` = the set of the MR's `approved` tour-plan `plan_date`s.
2. Determine `submitted_doctor_dates` (dates that have a doctor row with both a doctor and
   a date).
3. Determine `chemist_dates` / `stockist_dates`, and
   `non_doctor_dates = (chemist ∪ stockist) − submitted_doctor_dates`.
4. From those, subtract dates that **already** have a saved `DailyCoverage` →
   `truly_missing`.
5. **Validation rule:** if `truly_missing` is non-empty **and** `no_doctor_reason` is
   blank → set `form_error` and save **nothing**. In other words: *you may not log a
   chemist/stockist visit on a day that has no doctor visit unless you explicitly state
   why there was no doctor coverage.*
6. Otherwise, save each list. **Every** saved row must (a) have its required fields and
   (b) have a `report_date` that is in `approved_dates` — rows failing either are
   **silently skipped**.

> **Important behaviour:** `no_doctor_reason` is only a **gate**. It is validated but
> **not persisted** to any model — there is no field for it. Its sole effect is to allow
> the save to proceed.

#### `daily_coverage_list`
Lists the MR's **doctor** coverage (optionally filtered by `?date=`), paginated 25. Each
row gets a transient `.editable` flag (true within the 2-day window) so the template can
show/hide edit & delete controls. ⚠ Chemist/stockist records are not shown here (known
gap).

#### `edit_daily_coverage(pk)` / `delete_daily_coverage(pk)`
Both fetch the record scoped to `created_by=request.user` (so an MR can only touch their
own), then enforce the 2-day window via `_can_edit()` (`PermissionDenied` otherwise).
Edit uses `DailyCoverageForm`; delete is **POST-only** (a GET just redirects back to the
list).

**Templates:** `calendar.html`, `add_daily_coverage.html` (tabbed JS grid:
Doctor / Chemist / Stockist + "No Doctor Coverage Available" checkbox),
`daily_coverage_list.html`, `edit_daily_coverage.html`.

---

### 5.6 `reports` — Analytics & Excel (no models)

**Purpose:** read-only reporting over `DailyCoverage`, `DoctorEmployeeRelation`,
`TourPlan`, and chemist/stockist data. A plain module — no tables, no admin.

**Shared helpers** (`reports/views.py`)

- `_get_employee(request)` — the **supervisor switch**. If `request.user.is_staff` and a
  `?employee_id=` is supplied, the report renders for *that* employee; otherwise it
  renders for the requester. For staff it also returns `all_employees` to populate a
  dropdown. (This is why reports are gated on `is_staff`, not HR.)
- `_doctor_category(msl)` — maps an MSL number to `super_core` / `core` / `vip` (see §4.2).
- `_build_yearly_rows(employee, year)` — shared by the yearly HTML report and its Excel
  export: one row per **approved** relation, with a 12-element `month_visits` list (each
  a sorted list of the day-numbers visited that month), the distinct `hospitals`
  (working places), and `total_calls`.

**The four reports**

| Report | URL | What it shows |
|---|---|---|
| **Daily Activity** | `/reports/daily-activity/` | For one date: doctor coverages (with MSL), planned vs. actually-worked areas, plus chemist & stockist visits |
| **Monthly Activity** | `/reports/monthly-activity/` | A Chart.js frequency diagram of visits per day split by category (Super Core/Core/VIP), category totals, and a per-day table (planned areas, actual areas, specialization counts, total doctors) |
| **Monthly Target** | `/reports/monthly-target/` | One traffic-light row per approved doctor: **green** = target met (`visits ≥ target`), **orange** = some visits but short, **red** = zero. Target comes from the MSL category |
| **Yearly Activity** | `/reports/yearly-activity/` (+ `/export/`) | A doctor × month grid of the day-numbers visited, with totals. The `/export/` route streams the same data as a styled `.xlsx` (openpyxl) |

**Excel export** (`yearly_activity_report_excel`): builds a workbook in memory with a
styled header row (blue fill, white bold, wrapped), one row per doctor (MSL, name,
speciality, NMC, City=`doctor.area`, hospitals, 12 month columns of comma-joined day
numbers, total calls), fixed column widths, and returns it as an
`application/vnd.openxmlformats-...sheet` attachment named per employee + year.

> Chemist/stockist data appears **only** in the Daily Activity report today; the monthly,
> target and yearly reports cover doctors only (deferred items in `improvements.md`).

---

### 5.7 `api` — Django Ninja JWT API

**Purpose:** a JWT-secured JSON API for the planned SPA/mobile client.

`api/api.py` builds a `NinjaExtraAPI`, registers `NinjaJWTDefaultController` (token
endpoints), and mounts a `doctor_router`:

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /api/token/pair` | — | Obtain access + refresh tokens |
| `POST /api/token/refresh` | — | Refresh the access token |
| `GET /api/doctors/` | JWT | List doctors (`id, name, nmc_number, area`) |
| `GET /api/docs` | — | Swagger UI |

Token lifetimes come from `settings.NINJA_JWT` (access 8h, refresh 7d). This is the only
API surface so far — tour plans, coverage and reports are template-only for now.

---

## 6. End-to-End Flows

### 6.1 Setup / onboarding (admin)

```
Superuser (Django admin)
  ├─ create Users, set type (HR/SGM/GM/AGM/MR) and is_staff
  ├─ create Doctors (name, NMC, area, specialization)
  └─ create Areas
```

Nothing in the MR-facing UI creates users, doctors, or areas — all master data is seeded
through `/admin/`.

### 6.2 Doctor assignment flow

```
MR  ── add_doctor_employee_relation ──▶  DoctorEmployeeRelation(status=pending, msl_number)
                                              │
HR  ── hr_review_requests ──▶ hr_review_employee_requests ──▶ approve / reject
                                              │
                                         status=approved
                                              │
                                              ▼
                          Counts toward reports (target & yearly read approved only)
```

The `msl_number` set here is what later classifies the doctor as Super Core / Core / VIP.

### 6.3 Tour plan → daily coverage gating flow

This is the central control of the system:

```
MR  ── add_tour_plan (bulk) ──▶  TourPlan(plan_date, area, status=pending)
                                       │
HR  ── hr_review_tour_plans ──▶ approve ──▶ status=approved
                                       │
                                       ▼
   daily_coverage_calendar:  approved day becomes CLICKABLE ("Plan Approved")
                                       │
   MR clicks the day ──▶ add_daily_coverage (date pre-filled)
                                       │
   On save, the server re-checks: report_date ∈ approved tour-plan dates?
        ├─ yes → record saved
        └─ no  → record silently skipped
```

A day with a **pending** plan shows an amber "Plan Pending" badge and is not clickable; a
day with **no** plan is inert.

### 6.4 Daily coverage entry (deep dive)

The add page (`add_daily_coverage.html`) is a tabbed, JS-driven multi-row form:

```
┌ Doctor Coverage tab ─────────────────────────────────────────┐
│  [Add Another Doctor] rows → serialised to hidden `entries`   │
│  ☐ "No Doctor Coverage Available" → reveals a Reason textarea  │
│      (writes hidden `no_doctor_reason`; disables doctor rows)  │
├ Chemist Coverage tab → hidden `chemist_entries`               │
├ Stockist Coverage tab → hidden `stockist_entries`             │
└──────────────────────────────────────────────────────────────┘
                         │  Save All (POST)
                         ▼
add_daily_coverage validation (see §5.5):
   • chemist/stockist on a doctor-less day  → require `no_doctor_reason`
   • every saved row’s date must be in approved tour-plan dates
   • rows missing required fields are skipped
                         │
                         ▼
   redirect → calendar (day now shows "Added (n)" for doctor rows)
```

**Why the "no doctor reason" gate exists:** the business expects a doctor visit on any
working day. Logging only a chemist or stockist visit is allowed but must be *justified* —
otherwise the data would silently show productive days with no doctor coverage. The reason
is a guard rail, not stored data.

### 6.5 Edit / delete window

```
record.created_at  ──── ≤ 2 days ────▶  edit & delete allowed (buttons visible)
                   ──── > 2 days ────▶  PermissionDenied (controls hidden in list)
```

Scope is always `created_by = request.user`, so MRs can never edit another MR's records.

### 6.6 Reporting flow

```
MR        → opens a report → sees own data
Staff/HR  → opens a report → optional employee dropdown (?employee_id=) → sees that MR's data
                                   │
                                   ▼
   Reports read DailyCoverage (+ approved DoctorEmployeeRelation for MSL/targets,
   + approved TourPlan for planned areas, + Chemist/StockistCoverage in daily report)
                                   │
            Yearly report → "Export to Excel" → streamed .xlsx
```

---

## 7. Data Model Relationships

```
              users.User ───────────────────────────────────────────────┐
                  │  (created_by / employee / worked_with)               │
   ┌──────────────┼───────────────┬───────────────┬─────────────────┐    │
   ▼              ▼               ▼               ▼                 ▼    │
TourPlan   DoctorEmployeeRelation  DailyCoverage  Chemist/Stockist      │
   │              │                    │           Coverage             │
   │ area         │ doctor             │ doctor                         │
   ▼              ▼                    ▼ actual_working_place / area     │
 Area         doctors.Doctor      doctors.Doctor                        │
   ▲                                   │                                │
   └──────────── Area (shared) ◀───────┘────────────────◀───────────────┘

FK delete rules:
  • Doctor   ←PROTECT─ DailyCoverage            (cannot delete a doctor with coverage)
  • Doctor   ←CASCADE─ DoctorEmployeeRelation   (⚠ flagged: should be PROTECT)
  • Area     ←PROTECT─ TourPlan, DailyCoverage, Chemist/StockistCoverage
  • User     ←CASCADE─ created_by / employee;  ←SET_NULL─ TourPlan.worked_with
```

---

## 8. URL Reference

| URL | View | Access |
|---|---|---|
| `/` | `dashboard` | login |
| `/login/`, `/logout/` | Django auth views | — / login |
| `/doctors/` | `doctor_list` | login |
| `/doctor_employee_relation/` | `doctor_employee_relation_list` | login (self) / staff (others) |
| `/doctor_employee_relation/<employee_id>/` | same | staff |
| `/doctor_employee_relation/add/[<employee_id>/]` | `add_doctor_employee_relation` | login / staff |
| `/review_requests/` | `hr_review_requests` | HR |
| `/review_requests/<employee_id>/` | `hr_review_employee_requests` | HR |
| `/tour_plans/` | `tour_plan_list` | login |
| `/tour_plans/add/` | `add_tour_plan` | login |
| `/tour_plans/review/` | `hr_review_tour_plans` | HR |
| `/tour_plans/review/<employee_id>/` | `hr_review_employee_tour_plans` | HR |
| `/daily_coverage/` | `daily_coverage_calendar` | login |
| `/daily_coverage/<year>/<month>/` | calendar (specific month) | login |
| `/daily_coverage/add/[<selected_date>/]` | `add_daily_coverage` | login |
| `/daily_coverage/records/` | `daily_coverage_list` | login |
| `/daily_coverage/<pk>/edit/` | `edit_daily_coverage` | login + 2-day window |
| `/daily_coverage/<pk>/delete/` | `delete_daily_coverage` | login + 2-day window, POST |
| `/reports/daily-activity/` | `daily_activity_report` | login (staff → others) |
| `/reports/monthly-activity/` | `monthly_activity_report` | login (staff → others) |
| `/reports/monthly-target/` | `monthly_target_report` | login (staff → others) |
| `/reports/yearly-activity/` | `yearly_activity_report` | login (staff → others) |
| `/reports/yearly-activity/export/` | `yearly_activity_report_excel` | login (staff → others) |
| `/admin/` | Django admin | superuser/staff |
| `/api/token/pair`, `/api/token/refresh` | Ninja JWT | — |
| `/api/doctors/` | `list_doctors` | JWT |
| `/api/docs` | Swagger | — |

> All routes live in one flat `PharmaSFO/urls.py` (splitting into per-app `urls.py` is a
> noted improvement).

---

## 9. Permission Matrix

| Action | MR | Staff (GM/AGM/SGM) | HR (`is_staff` + `type=HR`) |
|---|---|---|---|
| View own coverage / plans / assignments | ✅ | ✅ | ✅ |
| View **another** MR's coverage (reports) | ❌ | ✅ (`?employee_id=`) | ✅ |
| Request doctor assignment | ✅ | ✅ | ✅ |
| **Approve** doctor assignment | ❌ | ❌ | ✅ |
| Submit tour plan | ✅ | ✅ | ✅ |
| **Approve** tour plan | ❌ | ❌ | ✅ |
| Add daily coverage (approved days) | ✅ | ✅ | ✅ |
| Edit/delete own coverage (≤2 days) | ✅ | ✅ | ✅ |
| Create users / doctors / areas | ❌ | ❌ (admin only) | ❌ (admin only) |

---

## 10. Running the system

```bash
docker compose up -d                                               # start web + db
docker compose logs web -f                                         # tail logs
docker compose run --rm web uv run python manage.py migrate        # apply migrations
docker compose run --rm web uv run python manage.py createsuperuser
docker compose up --build -d                                       # rebuild after dep changes
docker compose down                                                # stop
```

- App: <http://localhost:8000/> · Admin: `/admin/` · API docs: `/api/docs`
- Postgres is exposed on host port **5433** (container 5432 was already in use locally).
- Dev superuser: `admin` / `admin123` (type GM); DB `pharmasfo` / `pharmasfo_dev_password`.

---

## 11. Known gaps & deferred work

The authoritative, prioritised list lives in **`improvements.md`**. Highlights that affect
how the current code behaves:

- **`DoctorEmployeeRelation.doctor` is `CASCADE`** (should be `PROTECT`) — deleting a
  doctor would wipe assignment history.
- **Calendar "Added" badge counts doctor rows only** — a day with only chemist/stockist
  entries still shows "Plan Approved", not "Added".
- **Chemist/Stockist have no edit/delete/list UI** and appear only in the Daily Activity
  report (not monthly/target/yearly/Excel).
- **`no_doctor_reason` is a save-gate but is not persisted** anywhere.
- **Bulk-form skips are silent** — rows dropped for missing fields or unapproved dates
  give no user feedback (the Django messages framework is installed but unused).
- **Four `doctor_employee_relation` views lack `@never_cache`**; `_is_hr_user` is
  duplicated; `msl_number` isn't validated as an integer on input.
- **Dates are Gregorian** — Nepali BS calendar conversion is deferred.
- **API covers only `/doctors/`** — tour plans, coverage and reports are template-only.
```
