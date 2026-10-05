# PG Management System — Route Contract (Gate 2 Frozen)

## Standard Conventions
- **HTTP Methods**:
  - `GET`: Safe reads, page rendering, report viewing. No state changes.
  - `POST`: State mutations, form submissions, actions. Requires valid CSRF token.
- **Authentication & RBAC**:
  - `@login_required`: Authenticated session required. Unauthenticated requests redirect to `/login`.
  - `@role_required('ADMIN')`: Accessible strictly by Admin.
  - `@role_required('ADMIN', 'MANAGER')`: Accessible by Admin or Property Manager. For Manager, service enforces property scope isolation.
  - `@role_required('TENANT')`: Accessible strictly by Tenant. Service enforces record ownership isolation (`tenant_id == session['tenant_id']`).
- **CSRF Protection**: All `POST` forms must include `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- **Flash Messages**: Standard message categories: `'success'`, `'danger'`, `'warning'`, `'info'`.

---

## 1. Authentication & Public Blueprint (`auth`)

| Route | Method | Access | Description & Request Parameters | Template / Redirect |
| :--- | :--- | :--- | :--- | :--- |
| `/` | `GET` | Public | Landing page or redirect to role dashboard if authenticated | `public/index.html` or redirect |
| `/login` | `GET` | Public | Login form | `auth/login.html` |
| `/login` | `POST` | Public | Authenticate user. Body: `email`, `password`. Sets session. | Redirect to `/admin/dashboard`, `/manager/dashboard`, or `/tenant/dashboard` |
| `/logout` | `POST` | Authenticated | Clears user session. | Redirect to `/login` |
| `/register` | `GET` | Public | Public tenant registration form | `auth/register.html` |
| `/register` | `POST` | Public | Registers TENANT account only. Body: `email`, `password`, `first_name`, `last_name`, `phone`, `emergency_name`, `emergency_phone`, `id_proof_type`, `id_proof_number`, `permanent_address`. Creates user & tenant records. | Redirect to `/login` with success flash |

---

## 2. Shared User Blueprint (`shared` / `profile`)

| Route | Method | Access | Description & Request Parameters | Template / Redirect |
| :--- | :--- | :--- | :--- | :--- |
| `/profile` | `GET` | Authenticated | View current user profile | `shared/profile.html` |
| `/profile/password` | `POST` | Authenticated | Change password. Body: `current_password`, `new_password`, `confirm_password`. | Redirect to `/profile` |
| `/notifications` | `GET` | Authenticated | List in-app notifications for current user | `shared/notifications.html` |
| `/notifications/<int:id>/read`| `POST` | Authenticated | Mark notification as read (must belong to user) | Redirect back or JSON `{success: true}` |
| `/notifications/read-all`| `POST` | Authenticated | Mark all notifications read for current user | Redirect to `/notifications` |

---

## 3. Admin Blueprint (`admin`) — Global Access

| Route | Method | Access | Description & Request Parameters | Template / Redirect |
| :--- | :--- | :--- | :--- | :--- |
| `/admin/dashboard` | `GET` | ADMIN | KPI metrics (occupancy, collections, pending complaints, overdue rent) | `admin/dashboard.html` |
| **Properties** | | | | |
| `/admin/properties` | `GET` | ADMIN | List all properties with capacity and occupancy metrics | `admin/properties/index.html` |
| `/admin/properties/create` | `GET, POST` | ADMIN | GET: Form; POST: `name`, `code`, `address`, `city`, `state`, `pincode`, `contact_phone`, `default_deposit_amount`, `default_utility_rate` | Form: `admin/properties/form.html`<br>POST: Redirect `/admin/properties` |
| `/admin/properties/<int:id>/edit` | `GET, POST` | ADMIN | Edit property details | Form: `admin/properties/form.html`<br>POST: Redirect `/admin/properties` |
| `/admin/properties/<int:id>/managers` | `POST` | ADMIN | Assign manager to property. Body: `user_id` | Redirect to property details |
| `/admin/properties/<int:id>/managers/<int:user_id>/remove` | `POST` | ADMIN | Remove manager assignment | Redirect to property details |
| **Rooms & Beds** | | | | |
| `/admin/rooms` | `GET` | ADMIN | List rooms across properties with filters (`property_id`, `floor`) | `admin/rooms/index.html` |
| `/admin/rooms/create` | `GET, POST` | ADMIN | Create room. Body: `property_id`, `room_number`, `floor`, `room_type`, `base_rent`, `default_deposit` | Form: `admin/rooms/form.html`<br>POST: Redirect `/admin/rooms` |
| `/admin/rooms/<int:id>/edit` | `GET, POST` | ADMIN | Update room details | Form: `admin/rooms/form.html`<br>POST: Redirect `/admin/rooms` |
| `/admin/beds` | `GET` | ADMIN | List beds with filter by property/room/status | `admin/beds/index.html` |
| `/admin/beds/create` | `POST` | ADMIN | Add bed to room. Body: `room_id`, `bed_number` | Redirect to `/admin/beds` |
| `/admin/beds/<int:id>/approve-cleaning` | `POST` | ADMIN | Transition bed from `UNDER_MAINTENANCE` to `AVAILABLE` | Redirect to `/admin/beds` |
| **Tenants & Allocations** | | | | |
| `/admin/tenants` | `GET` | ADMIN | List tenants with status and search | `admin/tenants/index.html` |
| `/admin/tenants/create` | `GET, POST` | ADMIN | Create tenant and login credentials | Form: `admin/tenants/form.html` |
| `/admin/tenants/<int:id>` | `GET` | ADMIN | View tenant profile, active & past allocations, payment history | `admin/tenants/view.html` |
| `/admin/allocations/check-in` | `GET, POST` | ADMIN | GET: form with available beds; POST: `tenant_id`, `bed_id`, `check_in_date`, `expected_checkout_date`, `monthly_rent`, `security_deposit_amount` (Transactional `SELECT ... FOR UPDATE`) | Form: `admin/allocations/checkin.html`<br>POST: Redirect `/admin/tenants/<id>` |
| `/admin/allocations/<int:id>/transfer` | `POST` | ADMIN | Room transfer. Body: `new_bed_id`, `transfer_date`. Vacated bed -> `UNDER_MAINTENANCE`. | Redirect to tenant detail |
| `/admin/allocations/<int:id>/checkout-inspect` | `GET, POST` | ADMIN | Record inspection & deductions. Body: deduction items (category, amount, reason). Computes net settlement. | `admin/allocations/checkout_inspect.html` |
| `/admin/allocations/<int:id>/checkout-settle` | `POST` | ADMIN | Authorize final settlement. Disburses refund / logs recovery. Marks allocation `CHECKED_OUT`, bed `UNDER_MAINTENANCE`. | Redirect to tenant detail |
| **Invoices & Payments** | | | | |
| `/admin/invoices` | `GET` | ADMIN | List invoices (filters: property, status, billing_month) | `admin/invoices/index.html` |
| `/admin/invoices/generate` | `POST` | ADMIN | Generate monthly invoices for active allocations. Body: `property_id`, `billing_month`, `due_date`. | Redirect to `/admin/invoices` |
| `/admin/invoices/<int:id>` | `GET` | ADMIN | View invoice details & payments ledger | `admin/invoices/view.html` |
| `/admin/payments` | `GET` | ADMIN | View payments history ledger | `admin/payments/index.html` |
| `/admin/payments/record` | `GET, POST` | ADMIN | Record payment. Body: `invoice_id`, `amount`, `payment_method`, `transaction_reference`, `notes`. (Transactional balance update) | Form: `admin/payments/form.html`<br>POST: Redirect `/admin/invoices/<id>` |
| `/admin/deposits` | `GET` | ADMIN | Security deposit ledger | `admin/deposits/index.html` |
| **Utilities** | | | | |
| `/admin/utilities/meters` | `GET` | ADMIN | List utility meters | `admin/utilities/meters.html` |
| `/admin/utilities/meters/create` | `POST` | ADMIN | Add meter. Body: `property_id`, `room_id` (nullable), `meter_type`, `meter_identifier`, `rate_per_unit`. | Redirect to `/admin/utilities/meters` |
| `/admin/utilities/readings` | `GET` | ADMIN | List readings and billing records | `admin/utilities/readings.html` |
| `/admin/utilities/readings/record` | `POST` | ADMIN | Record reading. Body: `meter_id`, `current_reading`, `billing_period_start`, `billing_period_end`. | Redirect to `/admin/utilities/readings` |
| **Complaints & Notices** | | | | |
| `/admin/complaints` | `GET` | ADMIN | Complaints queue (filters: status, priority, property) | `admin/complaints/index.html` |
| `/admin/complaints/<int:id>` | `GET` | ADMIN | View complaint detail | `admin/complaints/view.html` |
| `/admin/complaints/<int:id>/status` | `POST` | ADMIN | Update complaint status & resolution notes. Body: `status`, `assigned_to_user_id`, `resolution_notes`. | Redirect `/admin/complaints/<id>` |
| `/admin/notices` | `GET` | ADMIN | Manage notices | `admin/notices/index.html` |
| `/admin/notices/create` | `GET, POST` | ADMIN | Publish notice. Body: `property_id` (optional), `target_audience`, `title`, `content`, `expires_at`. | `admin/notices/form.html` |
| `/admin/notices/<int:id>/delete` | `POST` | ADMIN | Remove notice | Redirect `/admin/notices` |
| **Reports & Audit** | | | | |
| `/admin/reports/occupancy` | `GET` | ADMIN | Occupancy report by property, room type, vacancy | `admin/reports/occupancy.html` |
| `/admin/reports/revenue` | `GET` | ADMIN | Revenue & collections report by property / month | `admin/reports/revenue.html` |
| `/admin/reports/defaulters` | `GET` | ADMIN | Overdue rent & outstanding balances report | `admin/reports/defaulters.html` |
| `/admin/audit-logs` | `GET` | ADMIN | Audit trail table with filters (actor, action, date range) | `admin/audit_logs/index.html` |

---

## 4. Manager Blueprint (`manager`) — Property-Scoped Access

*Note: All Manager queries automatically enforce `WHERE property_id IN (SELECT property_id FROM property_managers WHERE user_id = session['user_id'])`.*

| Route | Method | Access | Description & Request Parameters | Template / Redirect |
| :--- | :--- | :--- | :--- | :--- |
| `/manager/dashboard` | `GET` | MANAGER | Property-specific occupancy, pending complaints, pending checkouts | `manager/dashboard.html` |
| `/manager/rooms` | `GET` | MANAGER | List rooms in assigned property | `manager/rooms/index.html` |
| `/manager/rooms/create` | `GET, POST` | MANAGER | Create room within assigned property | Form: `manager/rooms/form.html` |
| `/manager/beds` | `GET` | MANAGER | List beds in assigned property | `manager/beds/index.html` |
| `/manager/beds/<int:id>/approve-cleaning` | `POST` | MANAGER | Approve bed after cleaning (`UNDER_MAINTENANCE` -> `AVAILABLE`) | Redirect `/manager/beds` |
| `/manager/tenants` | `GET` | MANAGER | List tenants residing in assigned property | `manager/tenants/index.html` |
| `/manager/tenants/<int:id>` | `GET` | MANAGER | View tenant details in assigned property | `manager/tenants/view.html` |
| `/manager/allocations/check-in` | `GET, POST` | MANAGER | Check-in tenant to assigned property bed | Form: `manager/allocations/checkin.html` |
| `/manager/allocations/<int:id>/checkout-inspect` | `GET, POST` | MANAGER | Record checkout inspection and itemized deductions | `manager/allocations/checkout_inspect.html` |
| `/manager/payments/record` | `GET, POST` | MANAGER | Record cash/UPI payment for tenant in assigned property | `manager/payments/form.html` |
| `/manager/utilities/readings/record` | `POST` | MANAGER | Record meter reading for assigned property | Redirect to `/manager/dashboard` |
| `/manager/complaints` | `GET` | MANAGER | View complaints for assigned property | `manager/complaints/index.html` |
| `/manager/complaints/<int:id>/status` | `POST` | MANAGER | Update status/resolution of assigned property complaint | Redirect `/manager/complaints` |
| `/manager/notices` | `GET, POST` | MANAGER | View and post notices for assigned property | `manager/notices/index.html` |

---

## 5. Tenant Blueprint (`tenant`) — Self-Record Scoped Access

*Note: All Tenant queries enforce `WHERE tenant_id = session['tenant_id']`.*

| Route | Method | Access | Description & Request Parameters | Template / Redirect |
| :--- | :--- | :--- | :--- | :--- |
| `/tenant/dashboard` | `GET` | TENANT | Overview: current room/bed, monthly rent, pending balance, recent notices | `tenant/dashboard.html` |
| `/tenant/profile` | `GET` | TENANT | View self profile and emergency details | `tenant/profile.html` |
| `/tenant/tenancy` | `GET` | TENANT | View current tenancy allocation, room amenities, room-mates | `tenant/tenancy.html` |
| `/tenant/invoices` | `GET` | TENANT | View all invoices and payment statuses | `tenant/invoices/index.html` |
| `/tenant/invoices/<int:id>` | `GET` | TENANT | View invoice breakdown and payments ledger | `tenant/invoices/view.html` |
| `/tenant/payments` | `GET` | TENANT | View all payment receipts and reference numbers | `tenant/payments/index.html` |
| `/tenant/complaints` | `GET` | TENANT | View submitted complaints and status | `tenant/complaints/index.html` |
| `/tenant/complaints/create` | `GET, POST` | TENANT | Submit a complaint. Body: `category`, `title`, `description`, `priority`. | Form: `tenant/complaints/form.html`<br>POST: Redirect `/tenant/complaints` |
| `/tenant/complaints/<int:id>` | `GET` | TENANT | View complaint timeline and staff resolution notes | `tenant/complaints/view.html` |
| `/tenant/notices` | `GET` | TENANT | View active notices published for property / all tenants | `tenant/notices/index.html` |
| `/tenant/checkout-request` | `GET, POST` | TENANT | Submit checkout notice. Body: `expected_checkout_date`, `reason`. | `tenant/checkout_request.html` |
