# PG Management System — Architecture & Structural Blueprint

```
                      +-----------------------------------+
                      |   Client Browser (Desktop/Mobile) |
                      +-----------------+-----------------+
                                        | HTTP / HTTPS
                                        v
                      +-----------------------------------+
                      |         Flask WSGI Server         |
                      |              (run.py)             |
                      +-----------------+-----------------+
                                        |
                 +----------------------+----------------------+
                 | Application Factory: create_app()           |
                 | - Config Loading (app/config.py)            |
                 | - CSRF & Extension Setup (app/extensions.py)|
                 | - Error Handlers (400, 403, 404, 500)       |
                 +----------------------+----------------------+
                                        |
           +----------------------------+----------------------------+
           |                            |                            |
           v                            v                            v
+---------------------+      +---------------------+      +---------------------+
|     auth_bp         |      |    admin_bp         |      |   manager_bp        |
|  - Login / Logout   |      |  - Global PG Mgmt   |      |  - Scoped PG Mgmt   |
|  - Public Register  |      |  - All Properties   |      |  - Assigned Branch  |
+---------------------+      +---------------------+      +---------------------+
           |                            |                            |
           +----------------------------+----------------------------+
                                        |
                         +--------------+--------------+
                         |                             |
                         v                             v
              +---------------------+       +---------------------+
              |    tenant_bp        |       |    shared_bp        |
              |  - Resident Portal  |       |  - Profile & Pwd    |
              |  - My Invoices/Beds |       |  - Notifications    |
              +---------------------+       +---------------------+
                                        |
                                        v
                      +-----------------------------------+
                      |          Services Layer           |
                      |  - Allocation / Check-in Engine   |
                      |  - Checkout & Settlement Engine   |
                      |  - Billing & Utility Calculator   |
                      +-----------------+-----------------+
                                        |
                                        v
                      +-----------------------------------+
                      |       Database Access Layer       |
                      |         (app/db/connection.py)    |
                      |  - PyMySQL DictCursor Pool        |
                      |  - Parameterized Query Execution  |
                      |  - Atomic Transactions & Locks    |
                      +-----------------+-----------------+
                                        |
                                        v
                      +-----------------------------------+
                      |         MySQL 8.0 InnoDB          |
                      |       (pg_management DB)          |
                      +-----------------------------------+
```

## Directory Ownership Matrix

| Agent | Directory / Files | Scope |
| :--- | :--- | :--- |
| **Orchestrator** | `README.md`, `run.py`, `.env.example`, `.gitignore`, `requirements.txt`, `docs/*` | Architecture, shared contracts, coordination |
| **Agent B (Database)** | `database/schema.sql`, `database/seed_demo.sql`, `database/README.md`, `docs/DATABASE_SCHEMA.md` | DDL scripts, demo data, migrations |
| **Agent C (Backend)** | `app/**/*.py`, `app/config.py`, `app/extensions.py`, `app/db/*`, `app/*/*.py` | Flask factory, blueprints, service logic, transactions |
| **Agent A (Frontend)** | `app/templates/**`, `app/static/**`, `docs/DESIGN_SYSTEM.md` | Jinja2 templates, CSS design system, responsive UI |
| **Agent D (QA/Sec)** | `tests/**`, `docs/INTEGRATION_LOG.md` | Test fixtures, unit, integration, and security test suites |
