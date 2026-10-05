# PG Management System — Database Schema Contract (Gate 2 Frozen)

## Engine & Encoding
- **Database Engine**: MySQL 8.0 / InnoDB
- **Character Set**: `utf8mb4`
- **Collation**: `utf8mb4_unicode_ci`
- **Monetary Representation**: `DECIMAL(10, 2)` (Strictly no floating point)
- **Primary Keys**: `BIGINT UNSIGNED AUTO_INCREMENT` or `INT UNSIGNED AUTO_INCREMENT`
- **Timestamps**: `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP` (and `ON UPDATE CURRENT_TIMESTAMP` where appropriate)

---

## 1. Table Definitions

### 1.1 `users`
System accounts for all roles (Admin, Manager/Warden, Tenant).

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique user ID |
| `email` | `VARCHAR(150)` | `NOT NULL UNIQUE` | Login identifier |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Werkzeug security hash |
| `role` | `ENUM('ADMIN', 'MANAGER', 'TENANT')` | `NOT NULL DEFAULT 'TENANT'` | Role-based authorization |
| `first_name` | `VARCHAR(100)` | `NOT NULL` | User first name |
| `last_name` | `VARCHAR(100)` | `NOT NULL` | User last name |
| `phone` | `VARCHAR(20)` | `NOT NULL` | Contact telephone number |
| `is_active` | `TINYINT(1)` | `NOT NULL DEFAULT 1` | 1 = Active, 0 = Deactivated |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Record creation timestamp |
| `updated_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | Last updated timestamp |

- **Indexes**: `idx_users_email` (`email`), `idx_users_role` (`role`)

---

### 1.2 `properties`
PG branches or physical properties.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique property ID |
| `name` | `VARCHAR(150)` | `NOT NULL` | Property name (e.g. "Sunrise PG Boys") |
| `code` | `VARCHAR(50)` | `NOT NULL UNIQUE` | Short code (e.g. "PG-BLR-01") |
| `address` | `TEXT` | `NOT NULL` | Street address |
| `city` | `VARCHAR(100)` | `NOT NULL` | City |
| `state` | `VARCHAR(100)` | `NOT NULL` | State |
| `pincode` | `VARCHAR(10)` | `NOT NULL` | Postal PIN code |
| `contact_phone` | `VARCHAR(20)` | `NOT NULL` | Property helpdesk phone |
| `default_deposit_amount` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0.00` | Configurable property-level default deposit |
| `default_utility_rate` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 10.00` | Configurable default electricity rate per unit |
| `is_active` | `TINYINT(1)` | `NOT NULL DEFAULT 1` | 1 = Active, 0 = Inactive |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Creation timestamp |
| `updated_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | Update timestamp |

- **Indexes**: `idx_properties_code` (`code`)

---

### 1.3 `property_managers`
Junction table mapping Manager/Warden accounts to specific properties for property-level isolation.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique assignment ID |
| `property_id` | `INT UNSIGNED` | `NOT NULL, FK -> properties(id) ON DELETE CASCADE` | Assigned property |
| `user_id` | `INT UNSIGNED` | `NOT NULL, FK -> users(id) ON DELETE CASCADE` | Manager account ID |
| `assigned_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Assignment timestamp |

- **Unique Constraint**: `unique_property_manager` (`property_id`, `user_id`)
- **Indexes**: `idx_pm_user` (`user_id`), `idx_pm_property` (`property_id`)

---

### 1.4 `rooms`
Rooms within a property.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique room ID |
| `property_id` | `INT UNSIGNED` | `NOT NULL, FK -> properties(id) ON DELETE RESTRICT` | Owning property |
| `room_number` | `VARCHAR(50)` | `NOT NULL` | Room label / number (e.g. "101", "G-02") |
| `floor` | `INT` | `NOT NULL DEFAULT 0` | Floor number (0 = Ground) |
| `room_type` | `ENUM('SINGLE', 'DOUBLE', 'TRIPLE', 'FOUR_SHARING')` | `NOT NULL DEFAULT 'DOUBLE'` | Room sharing type |
| `base_rent` | `DECIMAL(10,2)` | `NOT NULL` | Base monthly rent per bed in room |
| `default_deposit` | `DECIMAL(10,2)` | `NULL` | Optional room-level deposit override |
| `is_active` | `TINYINT(1)` | `NOT NULL DEFAULT 1` | 1 = Active, 0 = Inactive |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Creation timestamp |

- **Unique Constraint**: `unique_property_room` (`property_id`, `room_number`)
- **Indexes**: `idx_rooms_property` (`property_id`)

---

### 1.5 `beds`
Individual beds within a room.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique bed ID |
| `room_id` | `INT UNSIGNED` | `NOT NULL, FK -> rooms(id) ON DELETE RESTRICT` | Owning room |
| `bed_number` | `VARCHAR(20)` | `NOT NULL` | Bed designation (e.g. "A", "B", "1", "2") |
| `status` | `ENUM('AVAILABLE', 'OCCUPIED', 'UNDER_MAINTENANCE')` | `NOT NULL DEFAULT 'AVAILABLE'` | Bed lifecycle status |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Creation timestamp |
| `updated_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | Update timestamp |

- **Unique Constraint**: `unique_room_bed` (`room_id`, `bed_number`)
- **Indexes**: `idx_beds_room` (`room_id`), `idx_beds_status` (`status`)

---

### 1.6 `tenants`
Persistent tenant profile records.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique tenant profile ID |
| `user_id` | `INT UNSIGNED` | `NOT NULL UNIQUE, FK -> users(id) ON DELETE CASCADE` | Associated login account |
| `emergency_contact_name` | `VARCHAR(100)` | `NOT NULL` | Emergency contact person |
| `emergency_contact_phone` | `VARCHAR(20)` | `NOT NULL` | Emergency contact phone |
| `id_proof_type` | `VARCHAR(50)` | `NOT NULL` | Aadhaar / Passport / Driving License / Voter ID |
| `id_proof_number` | `VARCHAR(100)` | `NOT NULL` | Identification document number |
| `permanent_address` | `TEXT` | `NOT NULL` | Permanent residential address |
| `status` | `ENUM('ACTIVE', 'CHECKED_OUT', 'INACTIVE')` | `NOT NULL DEFAULT 'INACTIVE'` | Overall tenant status |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Profile creation timestamp |
| `updated_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | Profile update timestamp |

- **Indexes**: `idx_tenants_user` (`user_id`), `idx_tenants_status` (`status`)

---

### 1.7 `tenant_allocations`
Historical and active tenancy allocations. Supports tenant re-entry without profile deletion.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique allocation ID |
| `tenant_id` | `INT UNSIGNED` | `NOT NULL, FK -> tenants(id) ON DELETE RESTRICT` | Allocated tenant |
| `bed_id` | `INT UNSIGNED` | `NOT NULL, FK -> beds(id) ON DELETE RESTRICT` | Assigned bed |
| `check_in_date` | `DATE` | `NOT NULL` | Official check-in date |
| `expected_checkout_date` | `DATE` | `NULL` | Optional expected departure |
| `actual_checkout_date` | `DATE` | `NULL` | Recorded when checkout completes |
| `monthly_rent` | `DECIMAL(10,2)` | `NOT NULL` | Agreed monthly rent |
| `security_deposit_amount` | `DECIMAL(10,2)` | `NOT NULL` | Agreed security deposit (configurable) |
| `status` | `ENUM('ACTIVE', 'TRANSFERRED', 'CHECKED_OUT')` | `NOT NULL DEFAULT 'ACTIVE'` | Tenancy allocation status |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Record creation timestamp |
| `updated_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | Last updated timestamp |

- **Indexes**: `idx_allocations_tenant` (`tenant_id`), `idx_allocations_bed` (`bed_id`), `idx_allocations_status` (`status`)

---

### 1.8 `invoices`
Monthly rent and utility charge invoices.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique invoice ID |
| `allocation_id` | `INT UNSIGNED` | `NOT NULL, FK -> tenant_allocations(id) ON DELETE RESTRICT` | Tenancy allocation |
| `invoice_number` | `VARCHAR(50)` | `NOT NULL UNIQUE` | Human-readable identifier (e.g. "INV-202610-0001") |
| `billing_month` | `VARCHAR(7)` | `NOT NULL` | Format "YYYY-MM" (e.g. "2026-10") |
| `due_date` | `DATE` | `NOT NULL` | Due date for payment |
| `rent_amount` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0.00` | Rent component |
| `utility_amount` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0.00` | Electricity/water component |
| `total_amount` | `DECIMAL(10,2)` | `NOT NULL` | Total charge (`rent_amount + utility_amount`) |
| `paid_amount` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0.00` | Cumulative amount paid against invoice |
| `balance_due` | `DECIMAL(10,2)` | `NOT NULL` | Remaining balance (`total_amount - paid_amount`) |
| `status` | `ENUM('UNPAID', 'PARTIAL', 'PAID', 'OVERDUE')` | `NOT NULL DEFAULT 'UNPAID'` | Payment status |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Invoice creation timestamp |
| `updated_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | Update timestamp |

- **Unique Constraint**: `unique_allocation_month` (`allocation_id`, `billing_month`)
- **Indexes**: `idx_invoices_allocation` (`allocation_id`), `idx_invoices_status` (`status`), `idx_invoices_due` (`due_date`)

---

### 1.9 `payments`
Individual payment transactions preserving partial payment history.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique payment transaction ID |
| `invoice_id` | `INT UNSIGNED` | `NOT NULL, FK -> invoices(id) ON DELETE RESTRICT` | Associated invoice |
| `tenant_id` | `INT UNSIGNED` | `NOT NULL, FK -> tenants(id) ON DELETE RESTRICT` | Paying tenant |
| `amount` | `DECIMAL(10,2)` | `NOT NULL` | Transaction amount paid |
| `payment_date` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Timestamp of payment |
| `payment_method` | `ENUM('CASH', 'UPI', 'BANK_TRANSFER')` | `NOT NULL` | Method of payment |
| `transaction_reference` | `VARCHAR(100)` | `NOT NULL` | Receipt no., UPI UTR, or bank ref |
| `recorded_by_user_id` | `INT UNSIGNED` | `NOT NULL, FK -> users(id) ON DELETE RESTRICT` | Staff who logged the payment |
| `notes` | `TEXT` | `NULL` | Optional comments |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Creation timestamp |

- **Indexes**: `idx_payments_invoice` (`invoice_id`), `idx_payments_tenant` (`tenant_id`), `idx_payments_date` (`payment_date`)

---

### 1.10 `security_deposits`
Ledger tracking security deposit collection, deductions, and authorized checkout settlement.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique deposit record ID |
| `allocation_id` | `INT UNSIGNED` | `NOT NULL UNIQUE, FK -> tenant_allocations(id) ON DELETE RESTRICT` | Associated allocation |
| `tenant_id` | `INT UNSIGNED` | `NOT NULL, FK -> tenants(id) ON DELETE RESTRICT` | Tenant |
| `total_deposit_received` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0.00` | Actual deposit paid by tenant |
| `deductions_amount` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0.00` | Total approved deductions |
| `refund_amount` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0.00` | Net refund payable to tenant |
| `recovery_amount` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0.00` | Net amount owed by tenant if deductions > deposit |
| `settlement_status` | `ENUM('HELD', 'PENDING_APPROVAL', 'SETTLED')` | `NOT NULL DEFAULT 'HELD'` | Deposit settlement lifecycle |
| `settlement_notes` | `TEXT` | `NULL` | Inspection and settlement notes |
| `settled_at` | `DATETIME` | `NULL` | When settlement disbursement/collection completed |
| `authorized_by_user_id`| `INT UNSIGNED` | `NULL, FK -> users(id) ON DELETE RESTRICT` | Admin/Manager who approved settlement |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Record creation timestamp |
| `updated_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | Update timestamp |

- **Indexes**: `idx_deposits_allocation` (`allocation_id`), `idx_deposits_tenant` (`tenant_id`), `idx_deposits_status` (`settlement_status`)

---

### 1.11 `deposit_deductions`
Itemized deductions recorded during checkout inspection.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique deduction item ID |
| `deposit_id` | `INT UNSIGNED` | `NOT NULL, FK -> security_deposits(id) ON DELETE CASCADE` | Associated deposit record |
| `category` | `ENUM('DAMAGE', 'UNPAID_RENT', 'UNPAID_UTILITIES', 'CLEANING', 'OTHER')` | `NOT NULL` | Deduction type |
| `amount` | `DECIMAL(10,2)` | `NOT NULL` | Deduction amount |
| `reason` | `TEXT` | `NOT NULL` | Justification / item description |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Creation timestamp |

- **Indexes**: `idx_deductions_deposit` (`deposit_id`)

---

### 1.12 `utility_meters`
Configurable utility meters assigned to rooms or whole properties.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique meter ID |
| `property_id` | `INT UNSIGNED` | `NOT NULL, FK -> properties(id) ON DELETE CASCADE` | Associated property |
| `room_id` | `INT UNSIGNED` | `NULL, FK -> rooms(id) ON DELETE SET NULL` | Specific room (NULL = whole property) |
| `meter_type` | `ENUM('ELECTRICITY', 'WATER')` | `NOT NULL DEFAULT 'ELECTRICITY'` | Utility meter type |
| `meter_identifier` | `VARCHAR(100)` | `NOT NULL` | Physical meter serial / tag |
| `rate_per_unit` | `DECIMAL(10,2)` | `NOT NULL` | Configurable rate per kWh/unit |
| `is_active` | `TINYINT(1)` | `NOT NULL DEFAULT 1` | Meter status |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Creation timestamp |

- **Unique Constraint**: `unique_property_meter_tag` (`property_id`, `meter_identifier`)
- **Indexes**: `idx_meters_property` (`property_id`), `idx_meters_room` (`room_id`)

---

### 1.13 `utility_readings`
Historical meter readings, consumption calculations, and charges.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique reading record ID |
| `meter_id` | `INT UNSIGNED` | `NOT NULL, FK -> utility_meters(id) ON DELETE CASCADE` | Utility meter |
| `previous_reading`| `DECIMAL(10,2)` | `NOT NULL` | Starting meter reading |
| `current_reading` | `DECIMAL(10,2)` | `NOT NULL` | Ending meter reading |
| `units_consumed` | `DECIMAL(10,2)` | `NOT NULL` | Computed units (`current - previous`) |
| `rate_per_unit` | `DECIMAL(10,2)` | `NOT NULL` | Applied per-unit rate at time of reading |
| `total_charge` | `DECIMAL(10,2)` | `NOT NULL` | Computed charge (`units_consumed * rate`) |
| `billing_period_start` | `DATE` | `NOT NULL` | Start date of billing cycle |
| `billing_period_end` | `DATE` | `NOT NULL` | End date of billing cycle |
| `verified_by_user_id` | `INT UNSIGNED` | `NOT NULL, FK -> users(id) ON DELETE RESTRICT` | Staff member who read meter |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Reading logged timestamp |

- **Indexes**: `idx_readings_meter` (`meter_id`), `idx_readings_period` (`billing_period_start`, `billing_period_end`)

---

### 1.14 `complaints`
Tenant grievances and resolution workflows.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique ticket ID |
| `tenant_id` | `INT UNSIGNED` | `NOT NULL, FK -> tenants(id) ON DELETE CASCADE` | Submitting tenant |
| `property_id` | `INT UNSIGNED` | `NOT NULL, FK -> properties(id) ON DELETE CASCADE` | Property location |
| `room_id` | `INT UNSIGNED` | `NULL, FK -> rooms(id) ON DELETE SET NULL` | Relevant room |
| `title` | `VARCHAR(150)` | `NOT NULL` | Complaint headline |
| `description` | `TEXT` | `NOT NULL` | Detailed complaint content |
| `category` | `ENUM('PLUMBING', 'ELECTRICAL', 'CLEANING', 'WIFI', 'NOISE', 'MAINTENANCE', 'OTHER')` | `NOT NULL DEFAULT 'OTHER'` | Issue classification |
| `priority` | `ENUM('LOW', 'MEDIUM', 'HIGH', 'URGENT')` | `NOT NULL DEFAULT 'MEDIUM'` | Severity |
| `status` | `ENUM('OPEN', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED')` | `NOT NULL DEFAULT 'OPEN'` | Complaint lifecycle |
| `assigned_to_user_id`| `INT UNSIGNED` | `NULL, FK -> users(id) ON DELETE SET NULL` | Staff member assigned |
| `resolution_notes`| `TEXT` | `NULL` | Actions taken to resolve |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Submission timestamp |
| `updated_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | Status change timestamp |

- **Indexes**: `idx_complaints_tenant` (`tenant_id`), `idx_complaints_property` (`property_id`), `idx_complaints_status` (`status`)

---

### 1.15 `notices`
Notice board announcements.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique notice ID |
| `property_id` | `INT UNSIGNED` | `NULL, FK -> properties(id) ON DELETE CASCADE` | Property-specific (NULL = Global) |
| `target_audience` | `ENUM('ALL', 'MANAGERS_ONLY', 'TENANTS_ONLY')` | `NOT NULL DEFAULT 'ALL'` | Target role audience |
| `title` | `VARCHAR(200)` | `NOT NULL` | Notice title |
| `content` | `TEXT` | `NOT NULL` | Notice body |
| `published_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Publishing date |
| `expires_at` | `DATETIME` | `NULL` | Expiration date |
| `created_by_user_id`| `INT UNSIGNED` | `NOT NULL, FK -> users(id) ON DELETE RESTRICT` | Author staff member |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Record timestamp |

- **Indexes**: `idx_notices_property` (`property_id`), `idx_notices_audience` (`target_audience`)

---

### 1.16 `notifications`
In-app notification records for individual users.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique notification ID |
| `user_id` | `INT UNSIGNED` | `NOT NULL, FK -> users(id) ON DELETE CASCADE` | Recipient user |
| `title` | `VARCHAR(150)` | `NOT NULL` | Notification heading |
| `message` | `TEXT` | `NOT NULL` | Notification message text |
| `category` | `ENUM('RENT_DUE', 'PAYMENT_RECEIVED', 'COMPLAINT_UPDATE', 'NOTICE', 'CHECKOUT', 'SYSTEM')` | `NOT NULL DEFAULT 'SYSTEM'` | Notification type |
| `is_read` | `TINYINT(1)` | `NOT NULL DEFAULT 0` | 0 = Unread, 1 = Read |
| `link_url` | `VARCHAR(255)` | `NULL` | Optional redirect URL within app |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Created timestamp |

- **Indexes**: `idx_notifications_user_read` (`user_id`, `is_read`)

---

### 1.17 `audit_logs`
Immutable audit records for compliance and traceability.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `BIGINT UNSIGNED` | `PRIMARY KEY AUTO_INCREMENT` | Unique audit log ID |
| `actor_user_id` | `INT UNSIGNED` | `NULL, FK -> users(id) ON DELETE SET NULL` | Performing user (NULL for system) |
| `action` | `VARCHAR(100)` | `NOT NULL` | Action code (e.g. "BED_ALLOCATED", "CHECKOUT_APPROVED") |
| `target_entity_type` | `VARCHAR(50)` | `NOT NULL` | Target table (e.g. "tenant_allocations", "beds") |
| `target_entity_id` | `VARCHAR(50)` | `NOT NULL` | ID of target entity |
| `details_json` | `JSON` | `NULL` | Structured metadata (Zero passwords/tokens) |
| `ip_address` | `VARCHAR(45)` | `NULL` | Client IP address |
| `created_at` | `DATETIME` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Action timestamp |

- **Indexes**: `idx_audit_actor` (`actor_user_id`), `idx_audit_action` (`action`), `idx_audit_created` (`created_at`)

---

## 2. Concurrency & Transaction Standards

### Bed Allocation Concurrency Guard
```sql
START TRANSACTION;

-- 1. Acquire exclusive row lock on targeted bed
SELECT id, status, room_id 
FROM beds 
WHERE id = ? 
FOR UPDATE;

-- Application checks: if bed.status != 'AVAILABLE', ROLLBACK and abort.

-- 2. Update bed to OCCUPIED
UPDATE beds SET status = 'OCCUPIED' WHERE id = ?;

-- 3. Create active tenant allocation record
INSERT INTO tenant_allocations (
    tenant_id, bed_id, check_in_date, expected_checkout_date, 
    monthly_rent, security_deposit_amount, status
) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE');

-- 4. Create initial security deposit ledger entry
INSERT INTO security_deposits (
    allocation_id, tenant_id, total_deposit_received, settlement_status
) VALUES (LAST_INSERT_ID(), ?, ?, 'HELD');

-- 5. Update tenant profile status
UPDATE tenants SET status = 'ACTIVE' WHERE id = ?;

COMMIT;
```

### Bed Vacating Concurrency Guard (Checkout & Transfer)
- Bed transition on checkout or transfer *always* sets `status = 'UNDER_MAINTENANCE'`.
- Only an authorized staff endpoint (`/beds/<id>/approve-cleaning`) can execute:
  `UPDATE beds SET status = 'AVAILABLE' WHERE id = ? AND status = 'UNDER_MAINTENANCE'`.
