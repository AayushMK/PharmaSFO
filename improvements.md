# PharmaSFO — Improvement Checklist

Items are grouped by priority. Tick off each item as it is completed.

---

## Priority 1 — Bugs / Data Integrity

- [ ] **`DoctorEmployeeRelation.doctor` uses `CASCADE` instead of `PROTECT`**
  Deleting a Doctor silently destroys all assignment history. Change to `on_delete=PROTECT` to match every other Doctor FK in the project. Requires a migration.
  _File: `doctor_employee_relation/models.py:18`_

- [ ] **N+1 queries in both HR review views**
  Each employee found triggers a separate `.count()` query. Fix with `annotate(count=Count("pk"))` on the initial queryset.
  _Files: `doctor_employee_relation/views.py:103`, `tour_plans/views.py:113`_

- [ ] **`@never_cache` missing from 4 views in `doctor_employee_relation`**
  A logged-out user pressing back can see protected pages from the browser cache.
  Add `@never_cache` to `doctor_employee_relation_list`, `add_doctor_employee_relation`, `hr_review_requests`, `hr_review_employee_requests`.
  _File: `doctor_employee_relation/views.py`_

- [ ] **Redundant `if request.user.is_authenticated` inside `@login_required` views**
  The decorator already guarantees authentication — the guard is dead code.
  _Files: `tour_plans/views.py:37`, `daily_coverage/views.py:48`_

- [ ] **`msl_number` has no uniqueness constraint per employee**
  Two doctors can share the same MSL rank for the same employee, silently breaking the Super Core / Core / VIP category system.
  Add `UniqueConstraint(fields=["employee", "msl_number"], condition=Q(msl_number__isnull=False))`. Requires a migration.
  _File: `doctor_employee_relation/models.py`_

---

## Priority 2 — Code Quality / Duplication

- [ ] **`_is_hr_user()` is defined in two places**
  Identical function copied in `doctor_employee_relation/views.py:13` and `tour_plans/views.py:18`.
  Move to `users/utils.py` and import from both.

- [ ] **URLs are one flat 80-line file**
  Split into per-app `urls.py` files and `include()` them from the root `PharmaSFO/urls.py`.
  _File: `PharmaSFO/urls.py`_

- [ ] **`ChemistCoverage` and `StockistCoverage` are structurally identical**
  Both have the same 5 fields and Meta. Extract a shared `abstract = True` base model to eliminate duplication and ensure both models stay in sync (e.g. `updated_at` is currently missing from both but present on `DailyCoverage`).
  _File: `daily_coverage/models.py`_

- [ ] **Add `updated_at` to `ChemistCoverage` and `StockistCoverage`**
  `DailyCoverage` has `updated_at = models.DateTimeField(auto_now=True)` but the two newer models do not. Inconsistent. Requires a migration.
  _File: `daily_coverage/models.py`_

- [x] **Bulk form failures are silent**
  When entries are skipped (missing fields, unapproved date) the user is redirected with no indication that anything was dropped.
  Use Django messages to report how many entries were saved and how many were skipped.
  _File: `daily_coverage/views.py`_ — Done: saved/skipped counts reported via Django messages, rendered as Lumo toasts (see base.html bridge). Tour plan bulk add reports counts too.

- [ ] **`msl_number` not validated as integer on input**
  `request.POST.get("msl_number")` is passed straight to the model. A non-integer string causes an unhandled DB error at the model layer.
  Add `int()` conversion with a try/except in the view.
  _File: `doctor_employee_relation/views.py:60`_

---

## Priority 3 — Missing Functionality

- [ ] **Django messages not used anywhere**
  The messages framework is in middleware and `INSTALLED_APPS` but never called. Add success/error messages after every form submission (tour plans, daily coverage, HR approvals, doctor assignments).
  Add message display block to `templates/base.html`.

- [ ] **Calendar "Added" badge does not account for ChemistCoverage / StockistCoverage**
  A day with only chemist or stockist entries still shows "Plan Approved" (clickable add) instead of "Added".
  Update `daily_coverage_calendar` to also check `ChemistCoverage` and `StockistCoverage` for the date set.
  _File: `daily_coverage/views.py`_

- [ ] **No edit / delete for ChemistCoverage and StockistCoverage**
  The 2-day edit window and list page exist only for `DailyCoverage`. Add equivalent views and URL patterns for chemist and stockist records, and include them in the coverage list page.
  _Files: `daily_coverage/views.py`, `PharmaSFO/urls.py`, `templates/daily_coverage/daily_coverage_list.html`_

- [ ] **ChemistCoverage / StockistCoverage not shown in `daily_coverage_list`**
  The list page only shows doctor coverage records. Add chemist and stockist sections below the doctor table.
  _File: `templates/daily_coverage/daily_coverage_list.html`_

---

## Priority 4 — UX Polish

- [x] **Dashboard is an unorganised flat list of buttons**
  Group into sections: **My Work** (Daily Coverage, Tour Plans, Doctor Relations), **Reports** (Daily Activity, Monthly Activity, Monthly Target, Yearly Activity), **HR Actions** (visible only to HR users).
  _File: `templates/dashboard.html`_

- [x] **No pagination on list views**
  `daily_coverage_list` and `doctor_employee_relation_list` grow unbounded. Add Django's `Paginator` with a page size of ~25.
  _Files: `daily_coverage/views.py`, `doctor_employee_relation/views.py`_

- [x] **Heavy use of inline styles across all templates**
  Move repeated patterns (card header bar, dark table header, status badge, btn variants) into `static/css/style.css` as utility classes. Reduces template size significantly and makes restyling easier.
  _Files: all templates_

- [x] **No mobile responsiveness**
  No media queries. Wide tables and grid layouts overflow on small screens.
  Add responsive breakpoints to `static/css/style.css` and make the navbar collapse on mobile.

- [x] **Calendar "Added" badge does not show visit count**
  Show the number of coverage entries for that day (e.g. "Added (3)") so the user can tell at a glance how many records exist without navigating to the list.
  _File: `daily_coverage/views.py`, `templates/daily_coverage/calendar.html`_

---

## Future / Deferred

- [ ] Chemist and Stockist models in Monthly Activity Report (frequency chart + list tab)
- [ ] Chemist and Stockist in Monthly Target Report
- [ ] Chemist and Stockist in Yearly Activity Report and Excel export
- [ ] Nepali BS calendar conversion for date display
- [ ] React / SPA frontend migration (JWT auth already in place)
- [ ] Tests — unit tests for category logic, view permission checks, edit-window enforcement
- [ ] Rate limiting on the login endpoint
- [ ] API endpoints for Tour Plans, Daily Coverage, and Reports (currently only `/api/doctors/` exists)
