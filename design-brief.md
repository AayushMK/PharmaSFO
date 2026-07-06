# PharmaSFO — UI/UX Design Brief

A reference document to hand to a design tool (e.g. Claude design) to produce a
state-of-the-art redesign. Pair this with (a) screenshots of the current screens
and (b) the current stylesheet `static/css/style.css`.

---

## 1. What the product is

**PharmaSFO** is a Pharma Sales Force Automation web app used by a pharmaceutical
company in Nepal to plan, record, and report field activity of medical
representatives (MRs) visiting doctors, chemists, and stockists.

It is an **internal line-of-business tool**, not a consumer product. Priorities:
clarity, trust, speed of data entry, and dense-but-legible reporting. Think
"calm, professional healthcare enterprise SaaS," not flashy marketing site.

Current frontend: **server-rendered Django templates + a single CSS file** (no
React yet). Any redesign must be expressible as HTML + CSS classes, not a
component framework. A move to React/HTMX may happen later, so a clean,
token-based, component-oriented CSS system is the goal.

---

## 2. Who uses it (personas & context)

| Persona | Role | Device / context | Primary needs |
|---|---|---|---|
| **Medical Rep (MR)** | Field sales | **Mobile, on the go**, often one-handed, variable connectivity | Fast daily data entry (coverage, tour plans), see their calendar & targets, request doctor assignments |
| **HR** | Approvals | Desktop | Review & approve/reject doctor assignments and tour plans; add doctors |
| **Managers (SGM/GM/AGM)** | Oversight | Desktop | Read data-dense reports, track targets, export to Excel |
| **Admin** | Superuser | Desktop | Everything + Django admin |

**Design implication:** data-entry screens (daily coverage, tour plans) must be
**mobile-first and thumb-friendly**; reports and review screens are
**desktop-first and data-dense**. The design system must serve both.

Locale: Nepal. English UI. Dates currently Gregorian (Nepali BS calendar may come
later). Keep number/date formatting neutral and unambiguous.

---

## 3. Screen inventory (what must be designed)

**Auth & shell**
- Login page
- App shell: top navbar (brand, current user + role, logout), main content area

**Dashboard** — role-aware launcher grouped into cards: *My Work*, *Reports*,
*HR Actions* (HR/superuser only). Currently plain link-buttons; wants to feel like
a real dashboard (quick stats / at-a-glance status would be a plus).

**Doctors**
- Doctor list (table)
- Add Doctor form (HR/superuser)

**Doctor–Employee relations**
- My assigned doctors (list, filter by status, paginated)
- Request a doctor assignment (searchable select)
- HR review: employees with pending requests → approve/reject per employee

**Tour plans**
- Tour plan list (with status)
- Add tour plans (bulk / multi-row entry)
- HR review: pending plans → approve/reject per employee

**Daily coverage** *(highest-complexity area — treat as the hero flow)*
- Monthly **calendar** grid; days gated by tour-plan approval, badges show status ("Plan Approved", "Added (n)")
- **Add coverage**: tabbed bulk form — Doctor / Chemist / Stockist, multi-row, with validation
- Coverage list (edit/delete within a 2-day window)
- Edit coverage

**Reports** *(data-dense, desktop)*
- Daily Activity report
- Monthly Activity report (Chart.js frequency chart + tabular data)
- Monthly Target report (traffic-light dots per doctor vs visit target)
- Yearly Activity report (doctor × month grid of visit dates; Excel export)

**Django admin** — leave as-is (Django's own UI), but our color palette can lightly theme it.

---

## 4. Current visual state — audit (what to fix)

The current CSS has a reasonable skeleton but reads as "unpolished" because of:

1. **Two conflicting brand blues:** navbar & buttons `#1a73e8`; section/table
   headers `#1a4f7a`. → Establish ONE primary color + a deliberate scale.
2. **No design tokens.** Colors, spacing, radii are hardcoded literals, many
   inline in templates. → Introduce CSS custom properties (`--color-*`,
   `--space-*`, `--radius-*`, `--shadow-*`, type scale).
3. **Duplicate table systems:** modern `.data-table` vs legacy `table`
   (login/admin). → One table style.
4. **Weak typographic hierarchy:** single system font, no defined scale/weights.
   → Define a type scale (e.g. 12/14/16/20/24/32) and weight usage.
5. **Ad-hoc spacing & inline styles** in templates (esp. `dashboard.html`).
   → Move to utility classes / tokens; remove inline hex.
6. **Minimal feedback states:** no toast/messages region rendered in `base.html`;
   sparse empty states; no loading/skeleton states.
7. **No iconography.** → Add a lightweight icon set (e.g. Lucide/Heroicons) for
   nav, actions, status.
8. **Status communicated by color only** (approved/pending/rejected). → Add
   icon/shape + label for accessibility.

Keep what works: card layout, badge concept, status colors, calendar grid,
pagination, responsive breakpoint at 700px.

---

## 5. Target design direction

- **Aesthetic:** clean, trustworthy, calm healthcare-enterprise. Generous
  whitespace, restrained color, strong data legibility. References in spirit:
  Stripe/Linear restraint + a good analytics dashboard's data density.
- **Color:** one primary (a confident medical blue or teal — *decision needed,
  see §8*), a neutral grey scale for surfaces/borders/text, and a semantic set
  (success / warning / danger / info) used consistently for statuses.
- **Depth:** subtle elevation (1–2 shadow levels), 6–8px radii, hairline borders.
- **Density:** comfortable on mobile forms, compact on desktop tables (allow a
  "compact" table density for reports).
- **Motion:** minimal, purposeful (hover, focus, expand). No decorative animation.
- **Accessibility:** WCAG AA contrast, visible focus rings, 44px min touch
  targets on mobile, don't rely on color alone.

---

## 6. Components the design system must define

Buttons (primary / secondary / danger / success / ghost / sizes) · Inputs, selects,
textareas, date/time pickers, searchable select · Form layout + inline validation +
error/help text · Data table (default + compact + row hover + sticky header +
horizontal scroll on mobile) · Cards & section headers · Badges & status pills
(approved/pending/rejected, category tags) · Tabs (for the coverage add form) ·
Calendar cell states (empty / plan-approved / has-entries / disabled / today /
weekend) · Pagination · Alerts/toasts (success/error/info) · Empty states ·
Modal/confirm dialog (delete) · Nav bar + mobile nav · Traffic-light indicator (for
target report) · Chart container styling (works with Chart.js).

---

## 7. Deliverables to request from the design tool

Ask for, in this order:

1. **Design tokens** — a documented palette (with hex + usage), type scale,
   spacing scale, radii, shadows, delivered as CSS custom properties I can drop
   into `style.css` (`:root { --color-primary: ... }`).
2. **Restyled core components** (§6) as HTML + CSS using those tokens, matching
   the existing class names in `static/css/style.css` where possible so templates
   need minimal edits (`.btn`, `.card`, `.data-table`, `.badge`, `.alert`,
   `.cal-cell`, `.filter-row`, `.pagination`, `.form-group`, `.section-hd`).
3. **Hero screen mockups** for the 3 screens that carry the product:
   **Dashboard**, **Daily Coverage calendar**, and the **tabbed bulk-add coverage
   form** — desktop AND mobile.
4. **One report screen** mockup (Monthly Target, the traffic-light one) to prove
   the dense/desktop direction.
5. A short **before/after rationale** so changes are intentional.

**Constraint to state to the tool:** output must be plain semantic HTML + CSS
(no framework), and should re-use / extend the existing class names so it maps
onto Django templates. Prefer CSS custom properties over hardcoded values.

---

## 8. Decisions the owner should make (fill in before generating)

- **Primary brand color:** ______ (suggest: medical blue `#1E5AA8`-ish, or teal
  `#0E8C8C`-ish). Any existing company brand color/logo? ______
- **Product name shown in UI:** "PharmaSFO" — keep? Need a logo/wordmark? ______
- **Priority device for v1 polish:** mobile-first (MR entry) vs desktop-first
  (reports)? Recommend **mobile-first for entry screens, desktop-first for
  reports** — but confirm.
- **Light mode only**, or also dark mode? (Recommend light-only for v1.)
- **Localization:** English only for now? Nepali later? ______

---

## 9. Current tech facts the design must respect

- Server-rendered **Django templates**; styling via **one CSS file**
  (`static/css/style.css`). No build step, no CSS framework currently.
- Charts via **Chart.js**. Excel export via openpyxl (not a UI concern).
- Responsive breakpoint currently at **700px**.
- Existing key classes (re-skin, don't rename where avoidable): `.navbar`,
  `.container`, `.card`, `.page-hd`, `.section-hd`, `.btn` (+`-sm/-danger/-green`),
  `.filter-row`, `.data-table`, `.badge` (+colors), `.alert` (+states),
  `.pagination`, `.cal-grid`/`.cal-cell`, `.form-group`, `.empty-state`.
```
