# PG Management System — User & Operations Guide

Welcome to the **PG Management System (PGMS)**. This guide provides comprehensive operational walkthroughs for all three system roles: **Administrator**, **Property Manager / Warden**, and **Resident (Tenant)**.

---

## 1. System Access & Roles Overview

The system operates across three dedicated portals protected by role-based access control (RBAC):

| Role | Access URL | Primary Responsibilities |
| :--- | :--- | :--- |
| **Administrator (`ADMIN`)** | `/admin/dashboard` | Portfolio-wide management, property creation, manager assignments, global financial auditing, reports, settlement approvals. |
| **Property Manager (`MANAGER`)** | `/manager/dashboard` | Branch-scoped operations, room & bed management, resident check-ins, meter readings, complaint resolution, local notices. |
| **Resident (`TENANT`)** | `/tenant/dashboard` | Room & bed details, roommate directory, rent invoices, payment receipts, maintenance tickets, property announcements. |

---

## 2. Seeded Demo Accounts (Development & Testing Only)

> [!WARNING]
> **DEVELOPMENT & DEMONSTRATION USE ONLY**  
> All accounts and credentials listed below are pre-populated demo records for local development, automated verification, and demonstration walkthroughs. Never reuse these credentials in a live or production environment.

| Role | Email | Password | Scope / Notes |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `admin@pgms.local` | `Admin@123` | Global authority across all PG properties |
| **Manager (Koramangala)** | `manager.koramangala@pgms.local` | `Manager@123` | Greenfield Luxury PG (Koramangala) |
| **Manager (Indiranagar)** | `manager.indiranagar@pgms.local` | `Manager@123` | Silver Oak Premium PG (Indiranagar) |
| **Resident 1** | `rahul.sharma@example.com` | `Tenant@123` | Room 101, Bed 101-A (Greenfield Luxury PG) |
| **Resident 2** | `priya.verma@example.com` | `Tenant@123` | Room 201, Bed 201-A (Silver Oak Premium PG) |
| **Resident 3** | `amit.patel@example.com` | `Tenant@123` | Checked-out historical tenant |

---

## 3. Administrator Operations Walkthrough

### 3.1 Managing Properties
1. Navigate to **Properties** (`/admin/properties`).
2. Click **Create Property** (`/admin/properties/create`).
3. Enter property name, code (e.g., `PG-BLR-KOR`), address, city, state, pincode, contact number.
4. Set default security deposit (e.g., `8000.00`) and default utility rate per unit (e.g., `10.00`).
5. To assign property managers, open the property edit view (`/admin/properties/<id>/edit`), select an active manager from the dropdown, and click **Assign Manager**.

### 3.2 Managing Rooms & Beds
1. Navigate to **Rooms** (`/admin/rooms`).
2. Click **Add Room** (`/admin/rooms/create`), specify the property, room number, floor, room type (`SINGLE`, `DOUBLE`, `TRIPLE`), and base rent.
3. Open **Beds** (`/admin/beds`) to view bed capacity and occupancy status across properties.
4. Add beds to rooms by selecting the room and entering the bed identifier (e.g., `101-A`, `101-B`).

### 3.3 Bed Allocation & Check-in
1. Navigate to **Tenants** (`/admin/tenants`) or **Check-in** (`/admin/allocations/check-in`).
2. Select an unallocated tenant and an available bed.
3. Specify check-in date, expected checkout date, monthly rent, and security deposit amount.
4. Click **Complete Check-In**. The system atomically executes row locking (`SELECT ... FOR UPDATE`), marks the bed `OCCUPIED`, creates the active allocation record, and logs the security deposit in escrow.

### 3.4 Rent Invoicing & Payments
1. Navigate to **Invoices & Rent** (`/admin/invoices`).
2. Click **Generate Monthly Invoices**: choose billing month (`YYYY-MM`) and payment due date.
3. Invoices are generated for all active allocations in the selected property.
4. To record a payment, navigate to **Payments** → **Record Payment** (`/admin/payments/record`), select an open invoice, specify the amount, payment method (`UPI`, `CASH`, `BANK_TRANSFER`, `CARD`), and transaction reference.

### 3.5 Checkout Settlement Authorization
1. After a manager completes a checkout inspection and itemizes deductions, the allocation appears under **Pending Settlement Approval**.
2. Open the inspection report (`/admin/allocations/<id>/checkout-inspect`).
3. Review itemized deductions (e.g., `CLEANING`, `DAMAGE`, `UNPAID_RENT`, `UNPAID_UTILITY`).
4. Click **Finalize & Authorize Settlement** (`/admin/allocations/<id>/checkout-settle`).
5. The system transitions the allocation to `CHECKED_OUT`, sets the security deposit to `SETTLED`, marks the bed as `UNDER_MAINTENANCE`, and retains full historical records.

### 3.6 Financial & Occupancy Reports
1. **Occupancy Report** (`/admin/reports/occupancy`): Live count of total rooms, total beds, occupied beds, vacant beds, under-maintenance beds, and property occupancy percentage.
2. **Revenue Collections Report** (`/admin/reports/revenue`): Monthly breakdown of total invoiced rent, collected amounts, outstanding dues, and collection efficiency percentage.
3. **Defaulters Report** (`/admin/reports/defaulters`): Itemized list of overdue invoices with tenant contact phone numbers and days past due.

### 3.7 Audit Trail
- Navigate to **Audit Logs** (`/admin/audit-logs`) to review immutable, time-stamped system events including actor ID, action name, target entity, client IP address, and sanitized metadata.

---

## 4. Property Manager / Warden Operations

Managers have full operational control over their assigned property branches, with server-enforced isolation preventing access to other properties:

1. **Manager Dashboard** (`/manager/dashboard`): Real-time metrics for assigned property occupancy, active residents, pending complaints, and monthly collection status.
2. **Room & Bed Management** (`/manager/rooms`, `/manager/beds`): Add new rooms and beds within the assigned property.
3. **Resident Check-In** (`/manager/allocations/check-in`): Check in approved residents to available beds in their branch.
4. **Maintenance Approvals** (`/manager/beds/<id>/approve-cleaning`): Inspect vacated beds under maintenance. Once deep cleaning and touch-ups are complete, click **Approve Bed** to return the bed status from `UNDER_MAINTENANCE` back to `AVAILABLE`.
5. **Utility Meter Readings** (`/manager/utilities/readings/record`): Log monthly meter readings. The system automatically computes consumption deltas and applies the configured per-unit rate.
6. **Complaint Ticket Resolution** (`/manager/complaints`): Review resident tickets, update status (`IN_PROGRESS` → `RESOLVED`), and attach resolution notes. Automatic notifications are dispatched to the resident.
7. **Property Notices** (`/manager/notices`): Publish announcements targeted directly to branch residents (`TENANTS_ONLY`).

---

## 5. Resident (Tenant) Portal Walkthrough

Residents enjoy an intuitive self-service experience:

1. **Dashboard** (`/tenant/dashboard`): Immediate overview of assigned bed number, room number, PG branch name, monthly rent amount, security deposit held in escrow, and outstanding balance due.
2. **Room & Roommate Details** (`/tenant/tenancy`): View room amenities, base rent, property contact phone, and details of roommates sharing the room.
3. **Invoices & Receipts** (`/tenant/invoices`, `/tenant/payments`): Review monthly bills, payment status (`PAID`, `PARTIAL`, `OVERDUE`), line-item breakdown (rent vs. utilities), and payment history with transaction references.
4. **Maintenance Grievances** (`/tenant/complaints`): Submit maintenance tickets with category (`PLUMBING`, `ELECTRICAL`, `WIFI`, `CLEANING`, `NOISE`, `MAINTENANCE`, `OTHER`) and priority (`LOW`, `MEDIUM`, `HIGH`, `URGENT`). Receive instant in-app alerts when status is updated.
5. **Notice Board** (`/tenant/notices`): Read global PG announcements and branch-specific notices.
6. **Checkout Notice** (`/tenant/checkout-request`): Submit planned departure date and reason to notify management in advance.
7. **Profile & Security** (`/profile`): View KYC profile details and update account password safely.

---

## 6. Bed Lifecycle & Concurrency Guarantees

```
   [ AVAILABLE ]
        │
        │ Check-In (SELECT ... FOR UPDATE)
        ▼
   [ OCCUPIED ]
        │
        │ Checkout Settlement Finalized
        ▼
[ UNDER_MAINTENANCE ]
        │
        │ Staff Inspection Approved
        ▼
   [ AVAILABLE ]
```

- **Race Condition Prevention**: During concurrent check-in attempts, database rows are locked via `SELECT ... FOR UPDATE`. Exactly one transaction claims the bed, while competing transactions receive an immediate `ValueError: Bed is not available`.
- **Sanitary & Safety Standard**: Vacated beds can never be re-allocated immediately. They enter `UNDER_MAINTENANCE` until an authorized warden or administrator certifies cleaning and room restoration.
