-- =============================================================================
-- PG Management System - Database DDL Schema (Gate 2/3 Frozen Contract)
-- Target Engine: MySQL 8.0+ / InnoDB / utf8mb4
-- Database: pg_management
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Users table (Admin, Manager/Warden, Tenant)
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS notices;
DROP TABLE IF EXISTS complaints;
DROP TABLE IF EXISTS utility_readings;
DROP TABLE IF EXISTS utility_meters;
DROP TABLE IF EXISTS deposit_deductions;
DROP TABLE IF EXISTS security_deposits;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS tenant_allocations;
DROP TABLE IF EXISTS tenants;
DROP TABLE IF EXISTS beds;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS property_managers;
DROP TABLE IF EXISTS properties;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------------------------
-- 1. USERS
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('ADMIN', 'MANAGER', 'TENANT') NOT NULL DEFAULT 'TENANT',
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 2. PROPERTIES (Branches)
-- -----------------------------------------------------------------------------
CREATE TABLE properties (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    default_deposit_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    default_utility_rate DECIMAL(10,2) NOT NULL DEFAULT 10.00,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_properties_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 3. PROPERTY MANAGERS (Junction table for Manager property isolation)
-- -----------------------------------------------------------------------------
CREATE TABLE property_managers (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    property_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_property_manager UNIQUE (property_id, user_id),
    CONSTRAINT fk_pm_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE,
    CONSTRAINT fk_pm_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    INDEX idx_pm_user (user_id),
    INDEX idx_pm_property (property_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 4. ROOMS
-- -----------------------------------------------------------------------------
CREATE TABLE rooms (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    property_id INT UNSIGNED NOT NULL,
    room_number VARCHAR(50) NOT NULL,
    floor INT NOT NULL DEFAULT 0,
    room_type ENUM('SINGLE', 'DOUBLE', 'TRIPLE', 'FOUR_SHARING') NOT NULL DEFAULT 'DOUBLE',
    base_rent DECIMAL(10,2) NOT NULL,
    default_deposit DECIMAL(10,2) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_property_room UNIQUE (property_id, room_number),
    CONSTRAINT fk_rooms_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE RESTRICT,
    INDEX idx_rooms_property (property_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 5. BEDS (State machine: AVAILABLE -> OCCUPIED -> UNDER_MAINTENANCE -> AVAILABLE)
-- -----------------------------------------------------------------------------
CREATE TABLE beds (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    room_id INT UNSIGNED NOT NULL,
    bed_number VARCHAR(20) NOT NULL,
    status ENUM('AVAILABLE', 'OCCUPIED', 'UNDER_MAINTENANCE') NOT NULL DEFAULT 'AVAILABLE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT unique_room_bed UNIQUE (room_id, bed_number),
    CONSTRAINT fk_beds_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE RESTRICT,
    INDEX idx_beds_room (room_id),
    INDEX idx_beds_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 6. TENANTS (Persistent profile retained after checkout)
-- -----------------------------------------------------------------------------
CREATE TABLE tenants (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL UNIQUE,
    emergency_contact_name VARCHAR(100) NOT NULL,
    emergency_contact_phone VARCHAR(20) NOT NULL,
    id_proof_type VARCHAR(50) NOT NULL,
    id_proof_number VARCHAR(100) NOT NULL,
    permanent_address TEXT NOT NULL,
    status ENUM('ACTIVE', 'CHECKED_OUT', 'INACTIVE') NOT NULL DEFAULT 'INACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_tenants_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    INDEX idx_tenants_user (user_id),
    INDEX idx_tenants_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 7. TENANT ALLOCATIONS (Active & historical tenancy allocations)
-- -----------------------------------------------------------------------------
CREATE TABLE tenant_allocations (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT UNSIGNED NOT NULL,
    bed_id INT UNSIGNED NOT NULL,
    check_in_date DATE NOT NULL,
    expected_checkout_date DATE NULL,
    actual_checkout_date DATE NULL,
    monthly_rent DECIMAL(10,2) NOT NULL,
    security_deposit_amount DECIMAL(10,2) NOT NULL,
    status ENUM('ACTIVE', 'TRANSFERRED', 'CHECKED_OUT') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_alloc_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT,
    CONSTRAINT fk_alloc_bed FOREIGN KEY (bed_id) REFERENCES beds (id) ON DELETE RESTRICT,
    INDEX idx_allocations_tenant (tenant_id),
    INDEX idx_allocations_bed (bed_id),
    INDEX idx_allocations_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 8. INVOICES (Monthly rent & utility billing)
-- -----------------------------------------------------------------------------
CREATE TABLE invoices (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    allocation_id INT UNSIGNED NOT NULL,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    billing_month VARCHAR(7) NOT NULL, -- Format YYYY-MM
    due_date DATE NOT NULL,
    rent_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    utility_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_amount DECIMAL(10,2) NOT NULL,
    paid_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    balance_due DECIMAL(10,2) NOT NULL,
    status ENUM('UNPAID', 'PARTIAL', 'PAID', 'OVERDUE') NOT NULL DEFAULT 'UNPAID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT unique_allocation_month UNIQUE (allocation_id, billing_month),
    CONSTRAINT fk_invoices_alloc FOREIGN KEY (allocation_id) REFERENCES tenant_allocations (id) ON DELETE RESTRICT,
    INDEX idx_invoices_alloc (allocation_id),
    INDEX idx_invoices_status (status),
    INDEX idx_invoices_due (due_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 9. PAYMENTS (Preserves partial payment history)
-- -----------------------------------------------------------------------------
CREATE TABLE payments (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    invoice_id INT UNSIGNED NOT NULL,
    tenant_id INT UNSIGNED NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payment_method ENUM('CASH', 'UPI', 'BANK_TRANSFER') NOT NULL,
    transaction_reference VARCHAR(100) NOT NULL,
    recorded_by_user_id INT UNSIGNED NOT NULL,
    notes TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payments_invoice FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE RESTRICT,
    CONSTRAINT fk_payments_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT,
    CONSTRAINT fk_payments_recorder FOREIGN KEY (recorded_by_user_id) REFERENCES users (id) ON DELETE RESTRICT,
    INDEX idx_payments_invoice (invoice_id),
    INDEX idx_payments_tenant (tenant_id),
    INDEX idx_payments_date (payment_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 10. SECURITY DEPOSITS (Ledger for collection & checkout settlement)
-- -----------------------------------------------------------------------------
CREATE TABLE security_deposits (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    allocation_id INT UNSIGNED NOT NULL UNIQUE,
    tenant_id INT UNSIGNED NOT NULL,
    total_deposit_received DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    deductions_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    refund_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    recovery_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    settlement_status ENUM('HELD', 'PENDING_APPROVAL', 'SETTLED') NOT NULL DEFAULT 'HELD',
    settlement_notes TEXT NULL,
    settled_at DATETIME NULL,
    authorized_by_user_id INT UNSIGNED NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_deposits_alloc FOREIGN KEY (allocation_id) REFERENCES tenant_allocations (id) ON DELETE RESTRICT,
    CONSTRAINT fk_deposits_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE RESTRICT,
    CONSTRAINT fk_deposits_authorizer FOREIGN KEY (authorized_by_user_id) REFERENCES users (id) ON DELETE RESTRICT,
    INDEX idx_deposits_alloc (allocation_id),
    INDEX idx_deposits_tenant (tenant_id),
    INDEX idx_deposits_status (settlement_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 11. DEPOSIT DEDUCTIONS (Itemized deductions during checkout inspection)
-- -----------------------------------------------------------------------------
CREATE TABLE deposit_deductions (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    deposit_id INT UNSIGNED NOT NULL,
    category ENUM('DAMAGE', 'UNPAID_RENT', 'UNPAID_UTILITIES', 'CLEANING', 'OTHER') NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    reason TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_deductions_deposit FOREIGN KEY (deposit_id) REFERENCES security_deposits (id) ON DELETE CASCADE,
    INDEX idx_deductions_deposit (deposit_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 12. UTILITY METERS (Configurable rate per unit)
-- -----------------------------------------------------------------------------
CREATE TABLE utility_meters (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    property_id INT UNSIGNED NOT NULL,
    room_id INT UNSIGNED NULL,
    meter_type ENUM('ELECTRICITY', 'WATER') NOT NULL DEFAULT 'ELECTRICITY',
    meter_identifier VARCHAR(100) NOT NULL,
    rate_per_unit DECIMAL(10,2) NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_property_meter_tag UNIQUE (property_id, meter_identifier),
    CONSTRAINT fk_meters_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE,
    CONSTRAINT fk_meters_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE SET NULL,
    INDEX idx_meters_property (property_id),
    INDEX idx_meters_room (room_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 13. UTILITY READINGS (Consumption & charges tracking)
-- -----------------------------------------------------------------------------
CREATE TABLE utility_readings (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    meter_id INT UNSIGNED NOT NULL,
    previous_reading DECIMAL(10,2) NOT NULL,
    current_reading DECIMAL(10,2) NOT NULL,
    units_consumed DECIMAL(10,2) NOT NULL,
    rate_per_unit DECIMAL(10,2) NOT NULL,
    total_charge DECIMAL(10,2) NOT NULL,
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    verified_by_user_id INT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_readings_meter FOREIGN KEY (meter_id) REFERENCES utility_meters (id) ON DELETE CASCADE,
    CONSTRAINT fk_readings_verifier FOREIGN KEY (verified_by_user_id) REFERENCES users (id) ON DELETE RESTRICT,
    INDEX idx_readings_meter (meter_id),
    INDEX idx_readings_period (billing_period_start, billing_period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 14. COMPLAINTS (Tenant grievances & maintenance tickets)
-- -----------------------------------------------------------------------------
CREATE TABLE complaints (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT UNSIGNED NOT NULL,
    property_id INT UNSIGNED NOT NULL,
    room_id INT UNSIGNED NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    category ENUM('PLUMBING', 'ELECTRICAL', 'CLEANING', 'WIFI', 'NOISE', 'MAINTENANCE', 'OTHER') NOT NULL DEFAULT 'OTHER',
    priority ENUM('LOW', 'MEDIUM', 'HIGH', 'URGENT') NOT NULL DEFAULT 'MEDIUM',
    status ENUM('OPEN', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED') NOT NULL DEFAULT 'OPEN',
    assigned_to_user_id INT UNSIGNED NULL,
    resolution_notes TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_complaints_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_complaints_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE,
    CONSTRAINT fk_complaints_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE SET NULL,
    CONSTRAINT fk_complaints_assignee FOREIGN KEY (assigned_to_user_id) REFERENCES users (id) ON DELETE SET NULL,
    INDEX idx_complaints_tenant (tenant_id),
    INDEX idx_complaints_property (property_id),
    INDEX idx_complaints_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 15. NOTICES (Property or Global announcements)
-- -----------------------------------------------------------------------------
CREATE TABLE notices (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    property_id INT UNSIGNED NULL,
    target_audience ENUM('ALL', 'MANAGERS_ONLY', 'TENANTS_ONLY') NOT NULL DEFAULT 'ALL',
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    published_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NULL,
    created_by_user_id INT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notices_property FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE,
    CONSTRAINT fk_notices_author FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE RESTRICT,
    INDEX idx_notices_property (property_id),
    INDEX idx_notices_audience (target_audience)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 16. NOTIFICATIONS (In-app user notifications)
-- -----------------------------------------------------------------------------
CREATE TABLE notifications (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    category ENUM('RENT_DUE', 'PAYMENT_RECEIVED', 'COMPLAINT_UPDATE', 'NOTICE', 'CHECKOUT', 'SYSTEM') NOT NULL DEFAULT 'SYSTEM',
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    link_url VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    INDEX idx_notifications_user_read (user_id, is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- 17. AUDIT LOGS (Immutable tracking of administrative actions)
-- -----------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    actor_user_id INT UNSIGNED NULL,
    action VARCHAR(100) NOT NULL,
    target_entity_type VARCHAR(50) NOT NULL,
    target_entity_id VARCHAR(50) NOT NULL,
    details_json JSON NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_actor FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE SET NULL,
    INDEX idx_audit_actor (actor_user_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
