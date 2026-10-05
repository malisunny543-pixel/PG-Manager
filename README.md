# PG Management System (PGMS)

A robust, responsive, database-backed Paying Guest (PG) Management System built with Python, Flask, Jinja2, Vanilla JavaScript, and MySQL.

---

## 1. System Overview

The PG Management System delivers end-to-end multi-property hostel/PG management across three distinct portals:
- **Admin Portal**: Complete portfolio-wide authority across branches, accounts, finances, and audit trails.
- **Manager / Warden Portal**: Branch-scoped operations restricted strictly to assigned PG properties.
- **Tenant Portal**: Resident self-service for room details, roommate directory, rent invoices, payments, maintenance tickets, and announcements.

### Key Architectural Strengths
- **Strict Role-Based Access Control (RBAC)**: Server-side `@login_required` and `@role_required` enforcement on all state-changing endpoints.
- **Manager Property Isolation**: Managers are cryptographically isolated to their assigned branches via property manager junctions.
- **Row-Level Concurrency Protection**: High-concurrency bed check-ins protected via atomic `SELECT ... FOR UPDATE` row locks, preventing double allocation.
- **Bed Lifecycle State Machine**: Enforces `AVAILABLE` → `OCCUPIED` → `UNDER_MAINTENANCE` → `AVAILABLE` state transitions. Vacated beds require authorized maintenance approval before re-allocation.
- **DECIMAL Financial Precision**: All rent, deposit, and utility math uses MySQL `DECIMAL(10,2)` and Python `decimal.Decimal` to eliminate floating-point rounding errors.
- **Clean Architecture**: Flask Application Factory pattern, modular Blueprints, Service Layer pattern, and PyMySQL Connection Pool with `DictCursor` (Zero external ORM).

---

## 2. Technology Stack

| Component | Technology |
| :--- | :--- |
| **Language** | Python 3.14 / 3.10+ |
| **Framework** | Flask 3.1 (Application Factory, Modular Blueprints, Service Layer) |
| **Database** | MySQL Server 8.0+ (InnoDB Engine, Foreign Keys, Transactions, Row Locks) |
| **Database Driver** | PyMySQL 1.1+ with Custom Thread-Safe Connection Pooling & `DictCursor` |
| **Frontend** | HTML5, Modern CSS Design System (Slate & Indigo Tokens), Vanilla JavaScript |
| **Templating** | Jinja2 (Custom currency `₹` and date formatting filters, CSRF injection) |
| **Security** | Werkzeug `scrypt` hashing, CSRF token validation, SQL parameterization |
| **Testing** | pytest, pytest-cov (32 automated tests, 74% coverage) |

---

## 3. Demo Credentials (Development & Testing Only)

> [!WARNING]
> **DEVELOPMENT & DEMO PURPOSES ONLY**  
> The credentials listed below are provided strictly for local development, demonstration, and automated test execution. They must never be used in production or public-facing environments.

| Portal | Email | Password | Role & Scope |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@pgms.local` | `Admin@123` | System Administrator (Global Authority) |
| **Manager (Koramangala)** | `manager.koramangala@pgms.local` | `Manager@123` | Manager for Greenfield Luxury PG |
| **Manager (Indiranagar)** | `manager.indiranagar@pgms.local` | `Manager@123` | Manager for Silver Oak Premium PG |
| **Resident 1** | `rahul.sharma@example.com` | `Tenant@123` | Active Tenant (Room 101, Bed 101-A) |
| **Resident 2** | `priya.verma@example.com` | `Tenant@123` | Active Tenant (Room 201, Bed 201-A) |
| **Resident 3** | `amit.patel@example.com` | `Tenant@123` | Historical Tenant (Checked out) |

---

## 4. Local Setup & Quick Start

### Prerequisites
- Python 3.10 or higher
- MySQL Server 8.0+ running on `localhost:3306`

### Installation Steps
1. Navigate to the project root:
   ```bash
   cd "d:/Projects/PG Management System"
   ```

2. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. Install project dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   Copy `.env.example` to `.env` and configure your credentials:
   ```env
   FLASK_ENV=development
   FLASK_SECRET_KEY=your-secret-key-here
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=pg_management
   DB_TEST_NAME=pg_management_test
   DB_POOL_SIZE=10
   ```

5. Initialize the database schema & seed demo data:
   ```bash
   mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS pg_management;"
   mysql -u root -p pg_management < database/schema.sql
   mysql -u root -p pg_management < database/seed_demo.sql
   ```

6. Start the development server:
   ```bash
   python run.py
   ```
   Open your browser to [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## 5. Running the Test Suite

The test suite validates database integrity, RBAC permissions, concurrency locks, financial calculations, and 25 end-to-end integration workflows against an isolated test database (`pg_management_test`).

Run all tests:
```bash
pytest -v
```

Run tests with code coverage analysis:
```bash
pytest --cov=app --cov-report=term-missing
```

Test Results: **32 passed in 4.56s (100% pass rate, 74% coverage)**.

---

## 6. Project Documentation Directory

- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) — Comprehensive user and operations manual for Admin, Manager, and Tenant roles.
- [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) — 17-table schema contract, column definitions, foreign keys, and indexes.
- [`docs/ROUTE_CONTRACT.md`](docs/ROUTE_CONTRACT.md) — Route catalog, HTTP methods, RBAC rules, and payload specifications.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System architectural design, layering, and data access flows.
- [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) — Business logic policies, financial rules, and bed lifecycle state machine.
- [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) — Slate & Indigo UI tokens, responsive layouts, badges, and components.
- [`docs/INTEGRATION_LOG.md`](docs/INTEGRATION_LOG.md) — Verification logs and test execution reports for Gates 4 and 5.
