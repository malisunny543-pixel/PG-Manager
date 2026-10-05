# PG Management System — Design System & UI Specifications (Gate 2 Frozen)

## 1. Visual Identity & Brand Direction
The PG Management System UI is designed for professional property operations. It delivers a modern, clean, high-contrast, data-dense interface that works equally well for fast desktop administrative data entry and mobile tenant interactions.

- **Design Tone**: Reliable, clean, modern, administrative clarity.
- **Aesthetic**: Slate-and-Indigo theme with crisp bordered cards, subtle shadows, and prominent status pills.

---

## 2. Color Palette & CSS Variables

```css
:root {
  /* Brand / Primary */
  --primary-50:  #eef2ff;
  --primary-100: #e0e7ff;
  --primary-200: #c7d2fe;
  --primary-500: #4f46e5; /* Primary CTA & Brand */
  --primary-600: #4338ca; /* Hover / Focus */
  --primary-700: #3730a3;

  /* Secondary / Slate Neutrals */
  --slate-50:  #f8fafc; /* Background */
  --slate-100: #f1f5f9; /* Card background / Table headers */
  --slate-200: #e2e8f0; /* Borders */
  --slate-300: #cbd5e1;
  --slate-500: #64748b; /* Subtitles / Muted text */
  --slate-700: #334155; /* Secondary text */
  --slate-800: #1e293b; /* Sidebar / Dark nav */
  --slate-900: #0f172a; /* Primary Headings */

  /* Bed & Operational Status Tokens */
  --status-available-bg:   #ecfdf5;
  --status-available-text: #065f46;
  --status-available-border: #a7f3d0;

  --status-occupied-bg:    #eff6ff;
  --status-occupied-text:  #1e40af;
  --status-occupied-border: #bfdbfe;

  --status-maintenance-bg:   #fef3c7;
  --status-maintenance-text: #92400e;
  --status-maintenance-border: #fde68a;

  /* Financial Status Tokens */
  --status-paid-bg:       #f0fdf4;
  --status-paid-text:     #166534;
  --status-partial-bg:    #fffbeb;
  --status-partial-text:  #b45309;
  --status-overdue-bg:    #fef2f2;
  --status-overdue-text:  #991b1b;

  /* System Feedback */
  --feedback-success: #10b981;
  --feedback-warning: #f59e0b;
  --feedback-danger:  #ef4444;
  --feedback-info:    #3b82f6;

  /* Surface & Shadows */
  --bg-body:       #f8fafc;
  --bg-card:       #ffffff;
  --border-color:  #e2e8f0;
  --shadow-sm:     0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md:     0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg:     0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
  --radius-sm:     0.375rem; /* 6px */
  --radius-md:     0.5rem;   /* 8px */
  --radius-lg:     0.75rem;  /* 12px */
}
```

---

## 3. Typography Hierarchy
- **Font Stack**: `system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif`
- **Heading 1**: `1.75rem` (28px), `font-weight: 700`, line-height: `1.25`
- **Heading 2**: `1.375rem` (22px), `font-weight: 600`, line-height: `1.3`
- **Heading 3 / Card Titles**: `1.125rem` (18px), `font-weight: 600`, line-height: `1.4`
- **Body Regular**: `0.875rem` (14px), `font-weight: 400`, line-height: `1.5`
- **Small / Captions / Badges**: `0.75rem` (12px), `font-weight: 500`

---

## 4. Layout Architecture

### 4.1 Admin & Manager Dashboard Shell
- **Desktop**:
  - Left Sidebar (`260px` fixed width) styled in dark slate (`--slate-800`), containing PG branding, navigation links, property switcher, and user role pill.
  - Top Navigation Bar (`64px` height) with search/breadcrumbs, quick notification bell with badge counter, and user profile dropdown.
  - Main Content Area (`padding: 1.5rem 2rem`) with fluid grid and standard container max-width `1440px`.
- **Mobile**:
  - Hamburger toggle collapses the sidebar into an off-canvas drawer.
  - Top bar remains sticky with notification bell and compact profile avatar.

### 4.2 Tenant Portal Shell
- **Top Navigation Bar**: Sticky, clean white background with brand logo, direct links (`Dashboard`, `Rent & Payments`, `Complaints`, `Notices`), notification bell, and user menu.
- **Mobile Navigation**: Bottom tab bar or responsive slide-out drawer for key tenant actions.

---

## 5. Core UI Components

### 5.1 Metric / KPI Stat Cards
Compact cards displaying operational data backed by actual database counts:
```html
<div class="stat-card">
  <div class="stat-icon-wrapper bg-indigo-50 text-indigo-600">
    <i class="icon-bed"></i>
  </div>
  <div class="stat-details">
    <span class="stat-label">Occupancy Rate</span>
    <h3 class="stat-value">84.2%</h3>
    <span class="stat-subtext text-slate-500">42 / 50 Beds occupied</span>
  </div>
</div>
```

### 5.2 Status Badges (Pills)
Standardized pill classes:
- `.badge-available`: Green background, emerald text (Bed Available)
- `.badge-occupied`: Blue background, navy text (Bed Occupied / Active Tenant)
- `.badge-maintenance`: Amber background, bronze text (Bed Under Maintenance)
- `.badge-paid`: Green badge (Invoice Paid)
- `.badge-partial`: Amber badge (Invoice Partial)
- `.badge-overdue`: Red badge (Invoice Overdue)
- `.badge-open`: Slate badge (Complaint Open)
- `.badge-resolved`: Teal badge (Complaint Resolved)

### 5.3 Data Tables
- Header: Light slate (`--slate-100`) background with uppercase `0.75rem` text.
- Row hover: Subtle background shift (`--slate-50`).
- Responsive: Horizontal scrolling wrapper (`table-responsive`) with preserved column alignment on small screens.
- Empty State: Integrated illustration/icon with helpful call to action (e.g., "No active allocations found. Check-in a tenant.").

### 5.4 Forms & Input Fields
- Floating labels or crisp top labels (`font-size: 0.8125rem`, `font-weight: 500`).
- Inputs have `border: 1px solid var(--slate-300)`, `border-radius: var(--radius-sm)`, and focus rings with `outline: none; border-color: var(--primary-500); box-shadow: 0 0 0 3px var(--primary-100)`.
- Explicit invalid state: Red border (`--feedback-danger`) with immediate helper message below input.

### 5.5 Action Modals & Confirmation Dialogs
- Accessible modal backdrop (`rgba(15, 23, 42, 0.6)`).
- Destructive operations (Checkout clearance, bed maintenance transition, allocations) require explicit confirmation dialogs with cancellation button and primary action button.

---

## 6. Accessibility & Responsive Standards
- **Color Contrast**: All text pairings meet WCAG AA standard (minimum 4.5:1 for body text).
- **Interactive Focus**: All interactive buttons, links, and form fields retain visible focus rings for keyboard navigation.
- **Breakpoints**:
  - `sm`: `640px` (Phone portrait & landscape)
  - `md`: `768px` (Tablets)
  - `lg`: `1024px` (Small laptops / Desktop sidebar lock)
  - `xl`: `1280px` (Full desktop widescreen)
- **Semantic HTML**: Mandatory `<main>`, `<nav>`, `<aside>`, `<header>`, `<footer>`, `<section>`, and `<article>` tags.
