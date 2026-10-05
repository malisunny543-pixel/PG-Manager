import pytest
from decimal import Decimal
from app.db import query_db, execute_db

def test_flow_01_public_landing(client):
    """Flow 1: Public landing page displays brand and navigation."""
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "PG Management System" in html
    assert "Login" in html
    assert "Register" in html


def test_flow_02_tenant_registration(client):
    """Flow 2: Public registration strictly creates TENANT accounts."""
    email = "integration.tenant@test.com"
    existing = query_db("SELECT id FROM users WHERE email = %s", (email,), one=True)
    if existing:
        execute_db("DELETE FROM tenants WHERE user_id = %s", (existing['id'],))
        execute_db("DELETE FROM users WHERE id = %s", (existing['id'],))

    reg_data = {
        'first_name': 'Integration',
        'last_name': 'Tenant',
        'email': email,
        'phone': '9876543299',
        'password': 'Password@123',
        'confirm_password': 'Password@123',
        'emergency_name': 'Emergency Contact',
        'emergency_phone': '9876543298',
        'id_proof_type': 'Aadhaar',
        'id_proof_number': '1234-9876-5432',
        'permanent_address': '456 Integration Lane, Tech City'
    }
    resp = client.post('/register', data=reg_data, follow_redirects=False)
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']

    user = query_db("SELECT * FROM users WHERE email = %s", (email,), one=True)
    assert user is not None
    assert user['role'] == 'TENANT'

    tenant = query_db("SELECT * FROM tenants WHERE user_id = %s", (user['id'],), one=True)
    assert tenant is not None
    assert tenant['id_proof_number'] == '1234-9876-5432'


def test_flow_03_login_logout_flows(client):
    """Flow 3: Authentication and role-based redirects for Admin, Manager, Tenant."""
    # 1. Admin login
    admin_login = client.post('/login', data={'email': 'admin@pgms.local', 'password': 'Admin@123'}, follow_redirects=False)
    assert admin_login.status_code == 302
    assert '/admin/dashboard' in admin_login.headers['Location']

    # Logout (POST)
    logout_resp = client.post('/logout', follow_redirects=False)
    assert logout_resp.status_code == 302
    assert '/login' in logout_resp.headers['Location']

    # 2. Manager login
    mgr_login = client.post('/login', data={'email': 'manager.koramangala@pgms.local', 'password': 'Manager@123'}, follow_redirects=False)
    assert mgr_login.status_code == 302
    assert '/manager/dashboard' in mgr_login.headers['Location']

    client.post('/logout')

    # 3. Tenant login
    tnt_login = client.post('/login', data={'email': 'rahul.sharma@example.com', 'password': 'Tenant@123'}, follow_redirects=False)
    assert tnt_login.status_code == 302
    assert '/tenant/dashboard' in tnt_login.headers['Location']

    client.post('/logout')


def test_flow_04_admin_dashboard(admin_client):
    """Flow 4: Admin dashboard renders successfully with metrics."""
    resp = admin_client.get('/admin/dashboard')
    assert resp.status_code == 200
    assert "Admin Dashboard" in resp.get_data(as_text=True)


def test_flow_05_manager_dashboard(manager_client):
    """Flow 5: Manager dashboard renders successfully with property stats."""
    resp = manager_client.get('/manager/dashboard')
    assert resp.status_code == 200
    assert "Manager Dashboard" in resp.get_data(as_text=True)


def test_flow_06_tenant_dashboard(tenant_client):
    """Flow 6: Tenant dashboard renders successfully with occupancy details."""
    resp = tenant_client.get('/tenant/dashboard')
    assert resp.status_code == 200
    assert "Tenant Dashboard" in resp.get_data(as_text=True)


def test_flow_07_08_property_and_room_management(admin_client):
    """Flow 7 & 8: Property creation, manager assignment, and room/bed setup."""
    # Ensure clean slate for test property
    existing_prop = query_db("SELECT id FROM properties WHERE code = 'E2E-01'", one=True)
    if existing_prop:
        # Clear child records if any
        p_id = existing_prop['id']
        execute_db("DELETE FROM utility_readings WHERE meter_id IN (SELECT id FROM utility_meters WHERE property_id = %s)", (p_id,))
        execute_db("DELETE FROM utility_meters WHERE property_id = %s", (p_id,))
        execute_db("DELETE FROM complaints WHERE property_id = %s", (p_id,))
        execute_db("DELETE FROM property_managers WHERE property_id = %s", (p_id,))
        execute_db("DELETE FROM deposit_deductions WHERE deposit_id IN (SELECT sd.id FROM security_deposits sd JOIN tenant_allocations ta ON ta.id = sd.allocation_id JOIN beds b ON b.id = ta.bed_id JOIN rooms r ON r.id = b.room_id WHERE r.property_id = %s)", (p_id,))
        execute_db("DELETE FROM security_deposits WHERE allocation_id IN (SELECT ta.id FROM tenant_allocations ta JOIN beds b ON b.id = ta.bed_id JOIN rooms r ON r.id = b.room_id WHERE r.property_id = %s)", (p_id,))
        execute_db("DELETE FROM payments WHERE invoice_id IN (SELECT inv.id FROM invoices inv JOIN tenant_allocations ta ON ta.id = inv.allocation_id JOIN beds b ON b.id = ta.bed_id JOIN rooms r ON r.id = b.room_id WHERE r.property_id = %s)", (p_id,))
        execute_db("DELETE FROM invoices WHERE allocation_id IN (SELECT ta.id FROM tenant_allocations ta JOIN beds b ON b.id = ta.bed_id JOIN rooms r ON r.id = b.room_id WHERE r.property_id = %s)", (p_id,))
        execute_db("DELETE FROM tenant_allocations WHERE bed_id IN (SELECT b.id FROM beds b JOIN rooms r ON r.id = b.room_id WHERE r.property_id = %s)", (p_id,))
        execute_db("DELETE FROM beds WHERE room_id IN (SELECT id FROM rooms WHERE property_id = %s)", (p_id,))
        execute_db("DELETE FROM rooms WHERE property_id = %s", (p_id,))
        execute_db("DELETE FROM properties WHERE id = %s", (p_id,))

    # Create Property
    prop_data = {
        'name': 'E2E Test Property',
        'code': 'E2E-01',
        'address': 'Plot 99, Electronic City Phase 2',
        'city': 'Bengaluru',
        'state': 'Karnataka',
        'pincode': '560100',
        'contact_phone': '9112233445',
        'default_deposit_amount': '15000.00',
        'default_utility_rate': '11.50'
    }
    resp = admin_client.post('/admin/properties/create', data=prop_data, follow_redirects=True)
    assert resp.status_code == 200
    assert "Property created successfully" in resp.get_data(as_text=True)

    prop = query_db("SELECT * FROM properties WHERE code = 'E2E-01'", one=True)
    assert prop is not None
    assert prop['default_utility_rate'] == Decimal('11.50')

    # Assign Manager (User ID 2)
    resp = admin_client.post(f"/admin/properties/{prop['id']}/managers", data={'user_id': 2}, follow_redirects=True)
    assert resp.status_code == 200
    pm = query_db("SELECT * FROM property_managers WHERE property_id = %s AND user_id = 2", (prop['id'],), one=True)
    assert pm is not None

    # Create Room
    room_data = {
        'property_id': prop['id'],
        'room_number': '301',
        'floor': '3',
        'room_type': 'DOUBLE',
        'base_rent': '7500.00',
        'default_deposit': '15000.00'
    }
    resp = admin_client.post('/admin/rooms/create', data=room_data, follow_redirects=True)
    assert resp.status_code == 200

    room = query_db("SELECT * FROM rooms WHERE property_id = %s AND room_number = '301'", (prop['id'],), one=True)
    assert room is not None
    assert room['base_rent'] == Decimal('7500.00')

    # Add Beds
    admin_client.post('/admin/beds/create', data={'room_id': room['id'], 'bed_number': 'A'})
    admin_client.post('/admin/beds/create', data={'room_id': room['id'], 'bed_number': 'B'})

    beds = query_db("SELECT * FROM beds WHERE room_id = %s ORDER BY bed_number", (room['id'],))
    assert len(beds) == 2
    assert beds[0]['status'] == 'AVAILABLE'
    assert beds[1]['status'] == 'AVAILABLE'


def test_flow_09_to_14_bed_allocation_invoicing_payments(admin_client):
    """Flow 9-14: Bed check-in, rent invoice generation, partial payments, balance resolution."""
    # Ensure test property and room exist
    prop = query_db("SELECT * FROM properties WHERE code = 'E2E-01'", one=True)
    if not prop:
        test_flow_07_08_property_and_room_management(admin_client)
        prop = query_db("SELECT * FROM properties WHERE code = 'E2E-01'", one=True)

    room = query_db("SELECT * FROM rooms WHERE property_id = %s AND room_number = '301'", (prop['id'],), one=True)
    bed = query_db("SELECT * FROM beds WHERE room_id = %s AND bed_number = 'A'", (room['id'],), one=True)
    assert bed is not None

    # Clean existing allocations for this bed if rerun
    execute_db("DELETE FROM deposit_deductions WHERE deposit_id IN (SELECT sd.id FROM security_deposits sd JOIN tenant_allocations ta ON ta.id = sd.allocation_id WHERE ta.bed_id = %s)", (bed['id'],))
    execute_db("DELETE FROM security_deposits WHERE allocation_id IN (SELECT id FROM tenant_allocations WHERE bed_id = %s)", (bed['id'],))
    execute_db("DELETE FROM payments WHERE invoice_id IN (SELECT id FROM invoices WHERE allocation_id IN (SELECT id FROM tenant_allocations WHERE bed_id = %s))", (bed['id'],))
    execute_db("DELETE FROM invoices WHERE allocation_id IN (SELECT id FROM tenant_allocations WHERE bed_id = %s)", (bed['id'],))
    execute_db("DELETE FROM tenant_allocations WHERE bed_id = %s", (bed['id'],))
    execute_db("UPDATE beds SET status = 'AVAILABLE' WHERE id = %s", (bed['id'],))

    # Register new tenant for this check-in
    existing_t = query_db("SELECT id FROM users WHERE email = 'aditya.verma@test.com'", one=True)
    if not existing_t:
        admin_client.post('/admin/tenants/create', data={
            'first_name': 'Aditya',
            'last_name': 'Verma',
            'email': 'aditya.verma@test.com',
            'phone': '9876500001',
            'password': 'Password@123',
            'emergency_name': 'Mr. Verma',
            'emergency_phone': '9876500002',
            'id_proof_type': 'Passport',
            'id_proof_number': 'N1234567',
            'permanent_address': 'Delhi, India'
        })
    tenant = query_db("SELECT * FROM tenants WHERE id_proof_number = 'N1234567'", one=True)
    assert tenant is not None

    # Check-in allocation
    checkin_data = {
        'tenant_id': tenant['id'],
        'bed_id': bed['id'],
        'check_in_date': '2026-10-01',
        'expected_checkout_date': '2027-04-01',
        'monthly_rent': '7500.00',
        'security_deposit_amount': '15000.00'
    }
    resp = admin_client.post('/admin/allocations/check-in', data=checkin_data, follow_redirects=True)
    assert resp.status_code == 200

    # Verify Bed status transitioned to OCCUPIED
    updated_bed = query_db("SELECT * FROM beds WHERE id = %s", (bed['id'],), one=True)
    assert updated_bed['status'] == 'OCCUPIED'

    # Verify Allocation & Security Deposit records
    alloc = query_db("SELECT * FROM tenant_allocations WHERE bed_id = %s AND status = 'ACTIVE'", (bed['id'],), one=True)
    assert alloc is not None
    assert alloc['monthly_rent'] == Decimal('7500.00')

    deposit = query_db("SELECT * FROM security_deposits WHERE allocation_id = %s", (alloc['id'],), one=True)
    assert deposit is not None
    assert deposit['total_deposit_received'] == Decimal('15000.00')

    # Flow 12: Generate monthly rent invoice
    admin_client.post('/admin/invoices/generate', data={
        'billing_month': '2026-10',
        'due_date': '2026-10-10',
        'property_id': prop['id']
    })
    invoice = query_db("SELECT * FROM invoices WHERE allocation_id = %s AND billing_month = '2026-10'", (alloc['id'],), one=True)
    assert invoice is not None
    assert invoice['total_amount'] == Decimal('7500.00')
    assert invoice['balance_due'] == Decimal('7500.00')
    assert invoice['status'] == 'UNPAID'

    # Flow 13: Partial Payment of 4500.00
    admin_client.post('/admin/payments/record', data={
        'invoice_id': invoice['id'],
        'amount': '4500.00',
        'payment_method': 'UPI',
        'transaction_reference': 'UPI-TXN-1001',
        'notes': 'Partial first installment'
    })
    inv_partial = query_db("SELECT * FROM invoices WHERE id = %s", (invoice['id'],), one=True)
    assert inv_partial['paid_amount'] == Decimal('4500.00')
    assert inv_partial['balance_due'] == Decimal('3000.00')
    assert inv_partial['status'] == 'PARTIAL'

    # Complete balance payment of 3000.00
    admin_client.post('/admin/payments/record', data={
        'invoice_id': invoice['id'],
        'amount': '3000.00',
        'payment_method': 'BANK_TRANSFER',
        'transaction_reference': 'NEFT-TXN-1002',
        'notes': 'Remaining balance cleared'
    })
    inv_paid = query_db("SELECT * FROM invoices WHERE id = %s", (invoice['id'],), one=True)
    assert inv_paid['paid_amount'] == Decimal('7500.00')
    assert inv_paid['balance_due'] == Decimal('0.00')
    assert inv_paid['status'] == 'PAID'


def test_flow_15_utility_meter_and_readings(admin_client):
    """Flow 15: Utility meter registration and reading calculation."""
    prop = query_db("SELECT * FROM properties WHERE code = 'E2E-01'", one=True)
    if not prop:
        test_flow_07_08_property_and_room_management(admin_client)
        prop = query_db("SELECT * FROM properties WHERE code = 'E2E-01'", one=True)

    room = query_db("SELECT * FROM rooms WHERE property_id = %s AND room_number = '301'", (prop['id'],), one=True)

    # Clean existing meter if any
    meter = query_db("SELECT id FROM utility_meters WHERE meter_identifier = 'MTR-RM301-ELEC'", one=True)
    if meter:
        execute_db("DELETE FROM utility_readings WHERE meter_id = %s", (meter['id'],))
        execute_db("DELETE FROM utility_meters WHERE id = %s", (meter['id'],))

    # Register Meter
    meter_data = {
        'property_id': prop['id'],
        'room_id': room['id'],
        'meter_type': 'ELECTRICITY',
        'meter_identifier': 'MTR-RM301-ELEC',
        'rate_per_unit': '12.00'
    }
    admin_client.post('/admin/utilities/meters/create', data=meter_data)
    meter = query_db("SELECT * FROM utility_meters WHERE meter_identifier = 'MTR-RM301-ELEC'", one=True)
    assert meter is not None

    # Record initial reading
    admin_client.post('/admin/utilities/readings/record', data={
        'meter_id': meter['id'],
        'current_reading': '100.00',
        'billing_period_start': '2026-09-01',
        'billing_period_end': '2026-09-30'
    })

    # Record second reading: 180.00 (Delta = 80 units @ 12.00 = 960.00)
    admin_client.post('/admin/utilities/readings/record', data={
        'meter_id': meter['id'],
        'current_reading': '180.00',
        'billing_period_start': '2026-10-01',
        'billing_period_end': '2026-10-31'
    })
    readings = query_db("SELECT * FROM utility_readings WHERE meter_id = %s ORDER BY id DESC", (meter['id'],))
    assert len(readings) == 2
    latest = readings[0]
    assert latest['units_consumed'] == Decimal('80.00')
    assert latest['rate_per_unit'] == Decimal('12.00')
    assert latest['total_charge'] == Decimal('960.00')


def test_flow_16_complaint_lifecycle(app, tenant_client):
    """Flow 16: Complaint filing by tenant, manager lifecycle handling."""
    # Clean previous test complaint
    execute_db("DELETE FROM complaints WHERE title = 'Leaky faucet in bathroom'")

    # 1. Tenant submits complaint
    resp = tenant_client.post('/tenant/complaints/create', data={
        'title': 'Leaky faucet in bathroom',
        'description': 'Bathroom tap in room 101 drips continuously',
        'category': 'PLUMBING',
        'priority': 'MEDIUM'
    }, follow_redirects=True)
    assert resp.status_code == 200

    comp = query_db("SELECT * FROM complaints WHERE title = 'Leaky faucet in bathroom'", one=True)
    assert comp is not None
    assert comp['status'] == 'OPEN'

    # 2. Get manager for the property the complaint belongs to
    mgr_pm = query_db("SELECT user_id FROM property_managers WHERE property_id = %s", (comp['property_id'],), one=True)
    mgr_user_id = mgr_pm['user_id'] if mgr_pm else 2
    mgr_user = query_db("SELECT * FROM users WHERE id = %s", (mgr_user_id,), one=True)

    mgr_client = app.test_client()
    with mgr_client.session_transaction() as sess:
        sess['user'] = {
            'id': mgr_user['id'],
            'email': mgr_user['email'],
            'role': 'MANAGER',
            'first_name': mgr_user['first_name'],
            'last_name': mgr_user['last_name'],
            'managed_property_ids': [comp['property_id']],
            'primary_property_id': comp['property_id']
        }
        sess['_csrf_token'] = 'test-csrf-token'

    # Manager views and updates status to IN_PROGRESS then RESOLVED
    resp_prog = mgr_client.post(f"/manager/complaints/{comp['id']}/status", data={
        'status': 'IN_PROGRESS',
        'resolution_notes': 'Plumber scheduled for afternoon inspection'
    }, follow_redirects=True)
    assert resp_prog.status_code == 200
    comp_progress = query_db("SELECT * FROM complaints WHERE id = %s", (comp['id'],), one=True)
    assert comp_progress['status'] == 'IN_PROGRESS'

    resp_res = mgr_client.post(f"/manager/complaints/{comp['id']}/status", data={
        'status': 'RESOLVED',
        'resolution_notes': 'Faucet washer replaced, leak completely fixed'
    }, follow_redirects=True)
    assert resp_res.status_code == 200
    comp_resolved = query_db("SELECT * FROM complaints WHERE id = %s", (comp['id'],), one=True)
    assert comp_resolved['status'] == 'RESOLVED'


def test_flow_17_notice_board(admin_client, tenant_client):
    """Flow 17: Notice board publishing and resident view."""
    # Notice Board
    resp_pub = admin_client.post('/admin/notices/create', data={
        'title': 'Diwali Celebration and Dinner Announcement',
        'content': 'Special festive dinner will be served on Sunday evening at 8:00 PM.',
        'target_audience': 'ALL'
    }, follow_redirects=True)
    assert resp_pub.status_code == 200

    resp = tenant_client.get('/tenant/notices')
    assert resp.status_code == 200
    assert "Diwali Celebration and Dinner Announcement" in resp.get_data(as_text=True)


def test_flow_18_to_21_checkout_deductions_maintenance_lifecycle(admin_client):
    """Flow 18-21: Checkout inspection, itemized deductions, settlement authorization, bed maintenance return to available."""
    # Locate Aditya Verma's active allocation in Room 301 Bed A
    alloc = query_db("""
        SELECT ta.*, b.room_id, r.property_id
        FROM tenant_allocations ta
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN tenants t ON t.id = ta.tenant_id
        WHERE t.id_proof_number = 'N1234567' AND ta.status = 'ACTIVE'
    """, one=True)
    assert alloc is not None
    bed_id = alloc['bed_id']
    deposit = query_db("SELECT * FROM security_deposits WHERE allocation_id = %s", (alloc['id'],), one=True)
    assert deposit['total_deposit_received'] == Decimal('15000.00')

    # Flow 18: Record inspection with itemized deductions
    # Deductions: CLEANING: 600.00, DAMAGE: 1400.00 (Total deductions = 2000.00, Net refund = 13000.00)
    admin_client.post(f"/admin/allocations/{alloc['id']}/checkout-inspect", data={
        'category[]': ['CLEANING', 'DAMAGE'],
        'amount[]': ['600.00', '1400.00'],
        'reason[]': ['Deep cleaning of mattress and room', 'Broken window latch replacement'],
        'settlement_notes': 'Tenant agreed with cleaning and latch deduction.'
    })

    deposit_updated = query_db("SELECT * FROM security_deposits WHERE id = %s", (deposit['id'],), one=True)
    assert deposit_updated['deductions_amount'] == Decimal('2000.00')
    assert deposit_updated['refund_amount'] == Decimal('13000.00')
    assert deposit_updated['settlement_status'] == 'PENDING_APPROVAL'

    # Flow 19: Final Settlement Authorization
    admin_client.post(f"/admin/allocations/{alloc['id']}/checkout-settle", data={
        'actual_checkout_date': '2026-10-31'
    })

    # Verify allocation status
    alloc_closed = query_db("SELECT * FROM tenant_allocations WHERE id = %s", (alloc['id'],), one=True)
    assert alloc_closed['status'] == 'CHECKED_OUT'
    assert str(alloc_closed['actual_checkout_date']) == '2026-10-31'

    # Verify security deposit status
    deposit_settled = query_db("SELECT * FROM security_deposits WHERE id = %s", (deposit['id'],), one=True)
    assert deposit_settled['settlement_status'] == 'SETTLED'
    assert deposit_settled['authorized_by_user_id'] is not None

    # Flow 20: Bed must be UNDER_MAINTENANCE immediately following checkout
    bed_maint = query_db("SELECT * FROM beds WHERE id = %s", (bed_id,), one=True)
    assert bed_maint['status'] == 'UNDER_MAINTENANCE'

    # Maintenance inspection approval returns bed to AVAILABLE
    admin_client.post(f"/admin/beds/{bed_id}/approve-cleaning")
    bed_avail = query_db("SELECT * FROM beds WHERE id = %s", (bed_id,), one=True)
    assert bed_avail['status'] == 'AVAILABLE'

    # Flow 21: Tenant historical record retention verified
    tenant_history = query_db("SELECT * FROM tenant_allocations WHERE tenant_id = %s", (alloc['tenant_id'],))
    assert len(tenant_history) >= 1
    assert any(a['status'] == 'CHECKED_OUT' for a in tenant_history)


def test_flow_22_23_24_reports_notifications_audit(admin_client):
    """Flow 22-24: Reports rendering, notification system, and audit logs."""
    # Reports
    resp_occ = admin_client.get('/admin/reports/occupancy')
    assert resp_occ.status_code == 200
    assert "Occupancy" in resp_occ.get_data(as_text=True)

    resp_rev = admin_client.get('/admin/reports/revenue')
    assert resp_rev.status_code == 200
    assert "Revenue" in resp_rev.get_data(as_text=True)

    resp_def = admin_client.get('/admin/reports/defaulters')
    assert resp_def.status_code == 200
    assert "Defaulters" in resp_def.get_data(as_text=True)

    # Notifications
    resp_notif = admin_client.get('/notifications')
    assert resp_notif.status_code == 200
    assert "Notifications" in resp_notif.get_data(as_text=True)

    # Notifications mark all read
    resp_read_all = admin_client.post('/notifications/read-all', follow_redirects=True)
    assert resp_read_all.status_code == 200

    # Profile & Password change
    resp_prof = admin_client.get('/profile')
    assert resp_prof.status_code == 200

    resp_pwd = admin_client.post('/profile/password', data={
        'current_password': 'Admin@123',
        'new_password': 'NewAdminPassword@123',
        'confirm_password': 'NewAdminPassword@123'
    }, follow_redirects=True)
    assert resp_pwd.status_code == 200
    # Revert back
    admin_client.post('/profile/password', data={
        'current_password': 'NewAdminPassword@123',
        'new_password': 'Admin@123',
        'confirm_password': 'Admin@123'
    })

    # Audit Logs
    resp_audit = admin_client.get('/admin/audit-logs')
    assert resp_audit.status_code == 200
    assert "Audit Logs" in resp_audit.get_data(as_text=True)

    logs = query_db("SELECT * FROM audit_logs WHERE action IN ('CHECK_IN', 'PAYMENT_RECORDED', 'CHECKOUT_SETTLED')")
    assert len(logs) >= 1


def test_manager_portal_operations(manager_client):
    """Verify Manager portal operations: rooms, beds, tenants, invoices, utilities, notices."""
    # Rooms
    resp = manager_client.get('/manager/rooms')
    assert resp.status_code == 200

    # Beds
    resp = manager_client.get('/manager/beds')
    assert resp.status_code == 200

    # Tenants list
    resp = manager_client.get('/manager/tenants')
    assert resp.status_code == 200

    # Tenant view
    resp = manager_client.get('/manager/tenants/1')
    assert resp.status_code == 200

    # Notices
    resp = manager_client.get('/manager/notices')
    assert resp.status_code == 200

    # Post notice as manager
    resp_post = manager_client.post('/manager/notices', data={
        'title': 'Water Tank Cleaning Notice',
        'content': 'Water supply will be paused from 10am to 12pm for overhead tank maintenance.'
    }, follow_redirects=True)
    assert resp_post.status_code == 200


def test_tenant_portal_operations(tenant_client):
    """Verify Tenant portal views: profile, tenancy, invoices, payments, complaints, checkout notice."""
    # Profile
    resp = tenant_client.get('/tenant/profile')
    assert resp.status_code == 200

    # Tenancy & Roommates
    resp = tenant_client.get('/tenant/tenancy')
    assert resp.status_code == 200

    # Invoices
    resp = tenant_client.get('/tenant/invoices')
    assert resp.status_code == 200

    # Payments
    resp = tenant_client.get('/tenant/payments')
    assert resp.status_code == 200

    # Complaints
    resp = tenant_client.get('/tenant/complaints')
    assert resp.status_code == 200

    # Checkout Notice Submission
    resp_co = tenant_client.post('/tenant/checkout-request', data={
        'expected_checkout_date': '2026-12-31',
        'reason': 'Relocating to another city for work.'
    }, follow_redirects=True)
    assert resp_co.status_code == 200
    assert "Checkout notice submitted successfully" in resp_co.get_data(as_text=True)


def test_flow_25_security_and_rbac_isolation(client, manager_client, tenant_client):
    """Flow 25: Strict RBAC boundaries, Manager property isolation, Tenant self-isolation."""
    # 1. Unauthenticated request to protected route redirects to /login
    resp = client.get('/admin/dashboard')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']

    # 2. Tenant attempting Admin routes gets 403 Forbidden
    resp = tenant_client.get('/admin/dashboard')
    assert resp.status_code == 403

    # 3. Manager attempting Admin routes gets 403 Forbidden
    resp = manager_client.get('/admin/properties')
    assert resp.status_code == 403

    # 4. Manager property isolation: Manager of Property 1 attempting to view Room in Property 2
    room_other = query_db("SELECT id FROM rooms WHERE property_id != 1 LIMIT 1", one=True)
    if room_other:
        resp = manager_client.get(f"/manager/rooms/{room_other['id']}/edit")
        assert resp.status_code == 403

    # 5. Tenant self-isolation: Tenant 1 attempting to view Tenant 2's invoice
    inv_other = query_db("SELECT id FROM invoices WHERE allocation_id NOT IN (SELECT id FROM tenant_allocations WHERE tenant_id = 1) LIMIT 1", one=True)
    if inv_other:
        resp = tenant_client.get(f"/tenant/invoices/{inv_other['id']}")
        assert resp.status_code == 403
