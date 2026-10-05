# PG Management System — Project Specification (Gate 3 Baseline)

## 1. Project Overview
- **Project Name**: PG Management System
- **Core Purpose**: Comprehensive web application for managing Paying Guest (PG) hostels, multi-property branches, rooms, beds, tenants, rent billing, security deposits, electricity utilities, complaints, notices, and audit logging.
- **Delivery**: Local development and demonstration first.
- **Principles**: Practical, maintainable, secure, and fast to build. Zero over-engineering.

---

## 2. Technology Stack
- **Backend**: Python 3.14 + Flask (Application Factory, Modular Blueprints, Service Layer, Thin Routes).
- **Frontend**: HTML5, Modern Responsive CSS, Vanilla JavaScript, Jinja2 Templates (Inheritance, reusable components, CSRF tokens).
- **Database**: MySQL 8.0 (InnoDB engine, strict foreign keys, explicit transactions, `SELECT ... FOR UPDATE` row locking).
- **Driver**: PyMySQL with `DictCursor`.
- **Security**: PBKDF2/scrypt password hashing (`werkzeug.security`), session cookie security, server-side RBAC, and parameterized SQL queries.

---

## 3. Roles & Scopes
- **ADMIN**: Global administrative control over all properties, rooms, beds, tenants, allocations, check-ins, checkout settlements, finances, reports, and audit logs.
- **MANAGER**: Property-level operational control restricted strictly to their assigned PG branch (`property_managers` junction).
- **TENANT**: Self-service resident portal restricted strictly to their own profile, assigned room/bed, invoices, payments, complaints, and relevant notices.

---

## 4. Frozen Core Business Policies
1. **Bed Lifecycle**: `AVAILABLE` → `OCCUPIED` → `UNDER_MAINTENANCE` → `AVAILABLE` (explicit approval required after cleaning).
2. **Concurrency Safety**: Atomic transactions using `SELECT ... FOR UPDATE` on bed records prevent race conditions and duplicate allocations.
3. **Security Deposit**: Configurable per property and individual tenant allocation.
4. **Utility & Electricity**: Metered readings (`units_consumed = current - previous`) with configurable `rate_per_unit`.
5. **Overdue Invoices**: Automated late fees excluded from MVP; system tracks due dates and tags unpaid balances as `OVERDUE`.
6. **Checkout Settlement**: 2-stage checkout (Inspection & itemized deductions → Authorized clearance and refund/recovery → Tenancy marked `CHECKED_OUT` → Bed marked `UNDER_MAINTENANCE`).
7. **Tenant Retention**: Checked-out tenants preserve historical records and can receive future allocations.
8. **Monetary Handling**: All currency fields strictly use `DECIMAL(10,2)` in MySQL and Python `decimal.Decimal`.
