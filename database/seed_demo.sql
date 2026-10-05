-- =============================================================================
-- PG Management System - Seed Demo Data (Gate 4 Target)
-- Database: pg_management
-- Safe, realistic demo data with pre-hashed credentials:
-- Admin:    admin@pgms.local / Admin@123
-- Managers: manager.koramangala@pgms.local / Manager@123
--           manager.indiranagar@pgms.local / Manager@123
-- Tenants:  rahul.sharma@example.com / Tenant@123
--           priya.verma@example.com / Tenant@123
--           amit.patel@example.com / Tenant@123
-- =============================================================================

-- 1. USERS
INSERT INTO users (id, email, password_hash, role, first_name, last_name, phone, is_active) VALUES
(1, 'admin@pgms.local', 'scrypt:32768:8:1$QXC4fBuoSFVbsa51$2cb91a2aed243043a34e39476d0df980698d1ab99f234fa28d06541b63837bd20ccbd981e8acfb95612243748ff82af72805f7c3f0f87f48eacf8b63a19a0981', 'ADMIN', 'Super', 'Administrator', '9876543210', 1),
(2, 'manager.koramangala@pgms.local', 'scrypt:32768:8:1$E3emMOASxx6Cs6iK$bc903e3d9856af52ffbfd63057d574ab9ae0ed23999ff361abebc522b13f0e6624e9bd616331d9e097d382796589682bd22d65aaf0fd1b82791aa1101a74adef', 'MANAGER', 'Suresh', 'Kumar', '9876543211', 1),
(3, 'manager.indiranagar@pgms.local', 'scrypt:32768:8:1$E3emMOASxx6Cs6iK$bc903e3d9856af52ffbfd63057d574ab9ae0ed23999ff361abebc522b13f0e6624e9bd616331d9e097d382796589682bd22d65aaf0fd1b82791aa1101a74adef', 'MANAGER', 'Venkatesh', 'Rao', '9876543212', 1),
(4, 'rahul.sharma@example.com', 'scrypt:32768:8:1$JKVk29BvFvPOsDvg$aae8f0683de0545c69621ce345b2ba87f621c4b3a287a68951ca6136ea87fef743fcdc0fdb2aec12e2c3c2634e6145bdc287a444df5ca7fba21d31f995bb7f19', 'TENANT', 'Rahul', 'Sharma', '9876543213', 1),
(5, 'priya.verma@example.com', 'scrypt:32768:8:1$JKVk29BvFvPOsDvg$aae8f0683de0545c69621ce345b2ba87f621c4b3a287a68951ca6136ea87fef743fcdc0fdb2aec12e2c3c2634e6145bdc287a444df5ca7fba21d31f995bb7f19', 'TENANT', 'Priya', 'Verma', '9876543214', 1),
(6, 'amit.patel@example.com', 'scrypt:32768:8:1$JKVk29BvFvPOsDvg$aae8f0683de0545c69621ce345b2ba87f621c4b3a287a68951ca6136ea87fef743fcdc0fdb2aec12e2c3c2634e6145bdc287a444df5ca7fba21d31f995bb7f19', 'TENANT', 'Amit', 'Patel', '9876543215', 1);

-- 2. PROPERTIES
INSERT INTO properties (id, name, code, address, city, state, pincode, contact_phone, default_deposit_amount, default_utility_rate, is_active) VALUES
(1, 'Greenfield Luxury PG (Koramangala)', 'PG-BLR-KOR', '45, 4th Block, 80 Feet Road, Koramangala', 'Bengaluru', 'Karnataka', '560034', '080-25531001', 8000.00, 10.00, 1),
(2, 'Silver Oak Premium PG (Indiranagar)', 'PG-BLR-IND', '12, 100 Feet Road, HAL 2nd Stage, Indiranagar', 'Bengaluru', 'Karnataka', '560038', '080-25252002', 9000.00, 11.50, 1);

-- 3. PROPERTY MANAGERS
INSERT INTO property_managers (id, property_id, user_id) VALUES
(1, 1, 2), -- Suresh manages Koramangala
(2, 2, 3); -- Venkatesh manages Indiranagar

-- 4. ROOMS
INSERT INTO rooms (id, property_id, room_number, floor, room_type, base_rent, default_deposit, is_active) VALUES
(1, 1, '101', 1, 'DOUBLE', 8000.00, 8000.00, 1),
(2, 1, '102', 1, 'SINGLE', 12000.00, 12000.00, 1),
(3, 2, '201', 2, 'DOUBLE', 7500.00, 7500.00, 1),
(4, 2, '202', 2, 'TRIPLE', 6000.00, 6000.00, 1);

-- 5. BEDS
INSERT INTO beds (id, room_id, bed_number, status) VALUES
(1, 1, '101-A', 'OCCUPIED'),
(2, 1, '101-B', 'AVAILABLE'),
(3, 2, '102-A', 'UNDER_MAINTENANCE'),
(4, 3, '201-A', 'OCCUPIED'),
(5, 3, '201-B', 'AVAILABLE'),
(6, 4, '202-A', 'AVAILABLE'),
(7, 4, '202-B', 'AVAILABLE'),
(8, 4, '202-C', 'AVAILABLE');

-- 6. TENANTS
INSERT INTO tenants (id, user_id, emergency_contact_name, emergency_contact_phone, id_proof_type, id_proof_number, permanent_address, status) VALUES
(1, 4, 'Ramesh Sharma (Father)', '9876500001', 'Aadhaar', '1234-5678-9012', 'Flat 402, Shanti Apts, Pune, Maharashtra', 'ACTIVE'),
(2, 5, 'Sunita Verma (Mother)', '9876500002', 'Aadhaar', '2345-6789-0123', 'House 56, Sector 14, Gurugram, Haryana', 'ACTIVE'),
(3, 6, 'Kiran Patel (Brother)', '9876500003', 'Passport', 'Z1234567', '78 Navrangpura, Ahmedabad, Gujarat', 'CHECKED_OUT');

-- 7. TENANT ALLOCATIONS
INSERT INTO tenant_allocations (id, tenant_id, bed_id, check_in_date, expected_checkout_date, actual_checkout_date, monthly_rent, security_deposit_amount, status) VALUES
(1, 1, 1, '2026-09-01', '2027-08-31', NULL, 8000.00, 8000.00, 'ACTIVE'),
(2, 2, 4, '2026-09-15', '2027-09-14', NULL, 7500.00, 7500.00, 'ACTIVE'),
(3, 3, 3, '2026-06-01', '2026-09-30', '2026-09-30', 12000.00, 12000.00, 'CHECKED_OUT');

-- 8. INVOICES
INSERT INTO invoices (id, allocation_id, invoice_number, billing_month, due_date, rent_amount, utility_amount, total_amount, paid_amount, balance_due, status) VALUES
(1, 1, 'INV-202609-001', '2026-09', '2026-09-05', 8000.00, 350.00, 8350.00, 8350.00, 0.00, 'PAID'),
(2, 1, 'INV-202610-001', '2026-10', '2026-10-05', 8000.00, 420.00, 8420.00, 5000.00, 3420.00, 'PARTIAL'),
(3, 2, 'INV-202610-002', '2026-10', '2026-10-05', 7500.00, 300.00, 7800.00, 0.00, 7800.00, 'OVERDUE');

-- 9. PAYMENTS (Preserves partial payment history)
INSERT INTO payments (id, invoice_id, tenant_id, amount, payment_date, payment_method, transaction_reference, recorded_by_user_id, notes) VALUES
(1, 1, 1, 8350.00, '2026-09-04 11:30:00', 'UPI', 'UPI/20260904/998811', 2, 'Full payment for Sept'),
(2, 2, 1, 5000.00, '2026-10-03 14:15:00', 'BANK_TRANSFER', 'IMPS987654321', 2, 'First partial installment for Oct');

-- 10. SECURITY DEPOSITS
INSERT INTO security_deposits (id, allocation_id, tenant_id, total_deposit_received, deductions_amount, refund_amount, recovery_amount, settlement_status, settlement_notes, settled_at, authorized_by_user_id) VALUES
(1, 1, 1, 8000.00, 0.00, 0.00, 0.00, 'HELD', 'Security deposit safely held in escrow', NULL, NULL),
(2, 2, 2, 7500.00, 0.00, 0.00, 0.00, 'HELD', 'Security deposit held', NULL, NULL),
(3, 3, 3, 12000.00, 1500.00, 10500.00, 0.00, 'SETTLED', 'Checkout completed on 30 Sep. Deducted cleaning and touch-up.', '2026-09-30 17:00:00', 1);

-- 11. DEPOSIT DEDUCTIONS
INSERT INTO deposit_deductions (id, deposit_id, category, amount, reason) VALUES
(1, 3, 'CLEANING', 1000.00, 'Deep cleaning of single bedroom after checkout'),
(2, 3, 'DAMAGE', 500.00, 'Replacement of damaged door latch');

-- 12. UTILITY METERS
INSERT INTO utility_meters (id, property_id, room_id, meter_type, meter_identifier, rate_per_unit, is_active) VALUES
(1, 1, 1, 'ELECTRICITY', 'MTR-KOR-R101', 10.00, 1),
(2, 1, 2, 'ELECTRICITY', 'MTR-KOR-R102', 10.00, 1),
(3, 2, 3, 'ELECTRICITY', 'MTR-IND-R201', 11.50, 1);

-- 13. UTILITY READINGS
INSERT INTO utility_readings (id, meter_id, previous_reading, current_reading, units_consumed, rate_per_unit, total_charge, billing_period_start, billing_period_end, verified_by_user_id) VALUES
(1, 1, 1250.00, 1292.00, 42.00, 10.00, 420.00, '2026-09-01', '2026-09-30', 2),
(2, 3, 850.00, 876.08, 26.08, 11.50, 300.00, '2026-09-01', '2026-09-30', 3);

-- 14. COMPLAINTS
INSERT INTO complaints (id, tenant_id, property_id, room_id, title, description, category, priority, status, assigned_to_user_id, resolution_notes) VALUES
(1, 1, 1, 1, 'Bathroom tap leaking slowly', 'The washbasin tap in room 101 drips continuously.', 'PLUMBING', 'MEDIUM', 'OPEN', 2, NULL),
(2, 2, 2, 3, 'Study lamp switch sparking', 'Loose contact in the study table socket.', 'ELECTRICAL', 'HIGH', 'RESOLVED', 3, 'Replaced socket unit on 28 Sept 2026.');

-- 15. NOTICES
INSERT INTO notices (id, property_id, target_audience, title, content, published_at, created_by_user_id) VALUES
(1, NULL, 'ALL', 'PG Holiday Housekeeping Schedule', 'Housekeeping services will run on Sunday from 9:00 AM to 1:00 PM.', '2026-10-01 09:00:00', 1),
(2, 1, 'TENANTS_ONLY', 'Wi-Fi Router Maintenance in Koramangala', 'Broadband ISP will conduct fiber maintenance between 2:00 AM and 4:00 AM tonight.', '2026-10-04 18:00:00', 2);

-- 16. NOTIFICATIONS
INSERT INTO notifications (id, user_id, title, message, category, is_read) VALUES
(1, 4, 'Partial Payment Received', 'Your payment of INR 5,000.00 for October rent has been logged.', 'PAYMENT_RECEIVED', 0),
(2, 5, 'Rent Invoice Overdue', 'Your October rent invoice of INR 7,800.00 is overdue. Please settle at the reception.', 'RENT_DUE', 0);

-- 17. AUDIT LOGS
INSERT INTO audit_logs (id, actor_user_id, action, target_entity_type, target_entity_id, details_json, ip_address) VALUES
(1, 1, 'TENANT_CHECKIN', 'tenant_allocations', '1', '{"tenant": "Rahul Sharma", "bed": "101-A", "rent": 8000, "deposit": 8000}', '127.0.0.1'),
(2, 1, 'CHECKOUT_SETTLED', 'tenant_allocations', '3', '{"tenant": "Amit Patel", "deposit_refund": 10500, "deductions": 1500}', '127.0.0.1');
