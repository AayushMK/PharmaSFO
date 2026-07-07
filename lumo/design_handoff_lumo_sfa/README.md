# Handoff: Lumo SFA Design System

## Overview
Lumo SFA is a flat, clinical design system for a B2B pharmaceutical sales-force-automation
web app. Field sales reps (often on phones) use it to log doctor visits, manage a doctor
directory, and read analytics dashboards. This bundle contains the **complete, production-ready
design system** as plain HTML + vanilla CSS custom properties, plus reference pages showing it in use.

## About the design files — READ THIS FIRST
Unlike a typical handoff, **`tokens.css`, `components.css`, and `lumo.js` are real, drop-in
production files** — not prototypes to reverse-engineer. They have no framework, no build step,
and no dependencies. The intended implementation path is:

1. **Copy `tokens.css`, `components.css`, and `lumo.js` into the app as-is** (e.g. Django
   `static/lumo/`). These are the source of truth.
2. **Recreate the *pages* (`home.html`, `calendar.html`, `index.html`) in the app's real
   templating/framework layer** — Django templates, React, etc. — by reusing the class names
   from `components.css`. The HTML pages show the exact markup structure to reproduce; port the
   markup into your templates and feed it real data.

In short: **the CSS/JS are shipped verbatim; the HTML is the markup reference for how to compose it.**

## Fidelity
**High-fidelity.** Final colors, spacing, radius, typography, and interaction states are all
locked in `tokens.css`. Reproduce class-for-class — do not re-derive values.

## Design principles (keep these when extending)
- **Flat and minimal.** No gradients, no glassmorphism. Exactly two shadows exist and both live
  in tokens: `--shadow-card` (elevated cards) and `--shadow-modal` (modals only). Nothing else
  casts a shadow.
- **Structure from borders, spacing, and type** — never from color washes or shadows.
- **Color is spent sparingly.** One primary (`--primary`) for actions/links/active-nav only.
  Success/warning/danger are for status only. No decorative color.
- **4px everything.** Radius is `4px` everywhere (never pill-shaped). Spacing uses the
  4/8/12/16/24/32/48 ramp.

## Files in this bundle
- `tokens.css` — **source of truth.** All design tokens as CSS custom properties. Load first.
- `components.css` — every component + the app shell. Requires `tokens.css`. Load second.
- `lumo.js` — progressive-enhancement behaviour (accordion, modal, toast, mobile sidebar).
  Everything degrades to a static page without it. Load with `defer`.
- `home.html` — reference: rep dashboard (stats, today's coverage table, targets, empty states).
- `calendar.html` — reference: full-page monthly coverage calendar with tour-plan gating.
- `index.html` — reference: the component gallery / living style guide (expandable sections).

### Load order (every page)
```html
<link rel="stylesheet" href="{% static 'lumo/tokens.css' %}">
<link rel="stylesheet" href="{% static 'lumo/components.css' %}">
<script src="{% static 'lumo/lumo.js' %}" defer></script>
```

## Design tokens
All defined in `tokens.css` under `:root`. Do not hardcode these values in components — reference
the custom properties so a future theme change is one file.

**Neutral gray (6 steps):** `--gray-50 #f7f8fa`, `--gray-100 #eef0f3`, `--gray-200 #dee2e8`,
`--gray-400 #9aa2ae`, `--gray-600 #58616e`, `--gray-900 #1b2027`.

**Primary:** `--primary #1e64d6` (hover `#1a55b8`, active `#14468f`, tint `#eaf2fd`, border `#cfe0fa`).

**Semantic:** success `#1a875a`, warning `#b3730c`, danger `#c23934` — each with a `-tint` and
`-border` companion for filled surfaces.

**Radius:** `--radius 4px`, `--radius-sm 3px`.

**Spacing:** `--space-1 4px` · `-2 8px` · `-3 12px` · `-4 16px` · `-6 24px` · `-8 32px` · `-12 48px`.

**Type:** `--font-sans` = system stack (`system-ui, -apple-system, "Segoe UI", Roboto, …`).
Scale: xs 11 · sm 12 · base 14 · md 15 · lg 18 · xl 22 · 2xl 28 · 3xl 34.
Weights 400/500/600/700. Line-heights: tight 1.25, normal 1.5, relaxed 1.65. Hierarchy comes from
size + weight, never color.

**Elevation:** `--shadow-card`, `--shadow-modal`. **Focus:** `--ring` (primary), `--ring-danger`.

**Layout constants:** `--sidebar-width 244px`, `--topbar-height 56px`, `--control-height 36px`,
`--content-max 1180px`.

## Components (class reference)
Full live examples of every one are in `index.html`.

- **Buttons** — `.btn` + `.btn--primary` / `.btn--secondary` / `.btn--ghost` / `.btn--danger`;
  sizes `.btn--sm` / `.btn--lg`; `.btn--icon`, `.btn--block`. Inline SVG icons carry class `.ico`.
- **Forms** — wrap each control in `.field`; `.label` (with `.req` / `.optional`); `.input`,
  `.select`, `.textarea`; `.help` text; validation by adding `.is-error` / `.is-success` to
  `.field`. `.input-group` + `.affix` for prefixes; `.choice` for checkbox/radio.
- **Data table** — `.table-wrap` (border frame) > `.table` (+ `.table--zebra`). Sticky header,
  hairline rows, `tr.is-selected`, `.num` for right-aligned mono numbers, `.col-actions`.
  `.table-toolbar` sits above it.
- **Card** — `.card` (+ `.card--flat` for no shadow); `.card__header` / `__body` / `__footer`.
  `.stat` block for metric cards (`.stat__label` / `__value` / `__meta` `--up`/`--down`).
- **Badge / status pill** — `.badge` + `--neutral` / `--primary` / `--success` / `--warning` /
  `--danger`; add a `.dot`. `.badge--count` for nav counters. Rectangular (4px), never pill.
- **Alert** — `.alert` + variant; left keyline, `.alert__icon` / `__body` / `__title` / `__text`.
- **Toast** — fire from JS: `lumoToast({ type, title, text, duration })`, or declaratively with
  `data-toast="success" data-toast-title="…" data-toast-text="…"` on any element.
- **Modal** — `.modal-overlay` (scrim, toggle `hidden`) > `.modal` (+ `.modal--wide`). Open with
  `data-open-modal="#id"`; close with `data-close-modal`, scrim click, or Esc.
- **Empty state** — `.empty` > `.empty__glyph` / `__title` / `__text` / `__actions`.
- **App shell** — `.app` (grid) > `.sidebar` + `.main`. Sidebar uses collapsible `.nav-group`
  (header button `data-toggle="collapse"`, add `.is-collapsed` to start closed) with `.nav-item`
  (`.is-active`). `.topbar` with `.breadcrumb`, `.topbar__search`. `.page` > `.page__inner` >
  `.page-header`. Mobile (≤860px): sidebar becomes an off-canvas drawer toggled by
  `data-nav-toggle`; a `.scrim` element must be present inside `.app`.

## Interactions & behaviour (all in `lumo.js`)
- **Collapsible nav / accordion** — click toggles `.is-collapsed` (nav) / `.is-open` (gallery
  accordion) and syncs `aria-expanded`. Panels animate via `grid-template-rows` transition.
- **Modals** — open/close via data attributes; Esc and scrim-click close; body scroll locked
  while open.
- **Toasts** — auto-dismiss after `duration` (default 4200ms; `0` = sticky), slide in/out.
- **Mobile sidebar** — `data-nav-toggle` toggles `.nav-open` on `.app`; scrim click closes.
- All of this is progressive enhancement — pages render and are readable with JS disabled.

## Screens (reference pages)
- **Dashboard (`home.html`)** — page header with greeting + Log-visit CTA, an approved-tour-plan
  success alert, a 4-up stat card row, then a 2-col grid: today's coverage table (left) and
  monthly-target card + tour-plan empty state (right).
- **Coverage calendar (`calendar.html`)** — page header + 4-up month summary stats, then a
  full-month 7-col grid. **Core rule encoded visually:** reps can only log on HR-approved days.
  Green tag = coverage logged, blue = plan approved (clickable), amber = plan pending. Today is
  the primary-filled date square. Mobile: horizontal scroll below 860px.
- **Component gallery (`index.html`)** — living style guide; each section header expands.

## State / data (for the real implementation)
The pages are static references. When porting, wire real data into: tour-plan approval status per
day (drives calendar cell/tag classes and whether a day is loggable), coverage counts, monthly
target attainment, doctor directory rows, and pending-approval badge counts. Form validation
classes (`.is-error` / `.is-success` on `.field`) should be driven by your server/client
validation.

## Assets
No external assets. All icons are inline SVG (stroke-based, `currentColor`, class `.ico`) so they
inherit color from tokens. Select-caret and checkbox tick are inline data-URI SVGs in
`components.css`. Fonts are the system stack — nothing to load.
