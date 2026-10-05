from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from app.extensions import login_required, role_required
from app.db import query_db, execute_db
from app.services import (
    get_admin_dashboard_stats, get_all_properties, get_property_by_id,
    create_property, update_property, get_property_managers, assign_property_manager, remove_property_manager,
    get_rooms_by_property, get_room_by_id, create_room, update_room,
    get_beds, create_bed, get_available_beds, allocate_bed_check_in, transfer_room_bed,
    record_checkout_inspection, finalize_checkout_settlement, approve_bed_maintenance,
    get_invoices, get_invoice_by_id, generate_monthly_invoices,
    record_payment, get_payments_ledger,
    get_utility_meters, create_utility_meter, record_meter_reading, get_utility_readings,
    get_complaints, get_complaint_by_id, update_complaint_status,
    get_notices, create_notice, delete_notice,
    get_occupancy_report, get_revenue_report, get_defaulters_report, get_audit_logs,
    register_tenant
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
@role_required('ADMIN')
def enforce_admin():
    pass


@admin_bp.route('/dashboard')
def dashboard():
    stats = get_admin_dashboard_stats()
    return render_template('admin/dashboard.html', **stats)


# --- Properties ---

@admin_bp.route('/properties')
def properties_index():
    props = get_all_properties()
    return render_template('admin/properties/index.html', properties=props)


@admin_bp.route('/properties/create', methods=['GET', 'POST'])
def property_create():
    if request.method == 'POST':
        try:
            prop_id = create_property(
                name=request.form['name'],
                code=request.form['code'],
                address=request.form['address'],
                city=request.form['city'],
                state=request.form['state'],
                pincode=request.form['pincode'],
                contact_phone=request.form['contact_phone'],
                default_deposit_amount=request.form.get('default_deposit_amount', '0.00'),
                default_utility_rate=request.form.get('default_utility_rate', '10.00')
            )
            flash("Property created successfully.", "success")
            return redirect(url_for('admin.properties_index'))
        except Exception as e:
            flash(str(e), "danger")
    return render_template('admin/properties/form.html', property=None)


@admin_bp.route('/properties/<int:id>/edit', methods=['GET', 'POST'])
def property_edit(id):
    prop = get_property_by_id(id)
    if not prop:
        abort(404)
    if request.method == 'POST':
        try:
            update_property(
                property_id=id,
                name=request.form['name'],
                code=request.form['code'],
                address=request.form['address'],
                city=request.form['city'],
                state=request.form['state'],
                pincode=request.form['pincode'],
                contact_phone=request.form['contact_phone'],
                default_deposit_amount=request.form.get('default_deposit_amount', '0.00'),
                default_utility_rate=request.form.get('default_utility_rate', '10.00'),
                is_active=1 if request.form.get('is_active') == 'on' else 0
            )
            flash("Property updated successfully.", "success")
            return redirect(url_for('admin.properties_index'))
        except Exception as e:
            flash(str(e), "danger")
    
    managers = get_property_managers(id)
    available_managers = query_db("SELECT id, first_name, last_name, email FROM users WHERE role = 'MANAGER' AND is_active = 1")
    return render_template('admin/properties/form.html', property=prop, managers=managers, available_managers=available_managers)


@admin_bp.route('/properties/<int:id>/managers', methods=['POST'])
def property_assign_manager(id):
    user_id = request.form.get('user_id')
    if user_id:
        try:
            assign_property_manager(id, int(user_id))
            flash("Manager assigned to property.", "success")
        except Exception as e:
            flash(str(e), "danger")
    return redirect(url_for('admin.property_edit', id=id))


@admin_bp.route('/properties/<int:id>/managers/<int:user_id>/remove', methods=['POST'])
def property_remove_manager(id, user_id):
    remove_property_manager(id, user_id)
    flash("Manager removed from property.", "info")
    return redirect(url_for('admin.property_edit', id=id))


# --- Rooms & Beds ---

@admin_bp.route('/rooms')
def rooms_index():
    property_id = request.args.get('property_id')
    rooms = get_rooms_by_property(property_id=property_id)
    properties = get_all_properties(active_only=True)
    return render_template('admin/rooms/index.html', rooms=rooms, properties=properties, selected_prop=property_id)


@admin_bp.route('/rooms/create', methods=['GET', 'POST'])
def room_create():
    properties = get_all_properties(active_only=True)
    if request.method == 'POST':
        try:
            create_room(
                property_id=request.form['property_id'],
                room_number=request.form['room_number'],
                floor=request.form.get('floor', 0),
                room_type=request.form.get('room_type', 'DOUBLE'),
                base_rent=request.form['base_rent'],
                default_deposit=request.form.get('default_deposit')
            )
            flash("Room created successfully.", "success")
            return redirect(url_for('admin.rooms_index'))
        except Exception as e:
            flash(str(e), "danger")
    return render_template('admin/rooms/form.html', room=None, properties=properties)


@admin_bp.route('/rooms/<int:id>/edit', methods=['GET', 'POST'])
def room_edit(id):
    room = get_room_by_id(id)
    if not room:
        abort(404)
    properties = get_all_properties(active_only=True)
    if request.method == 'POST':
        try:
            update_room(
                room_id=id,
                room_number=request.form['room_number'],
                floor=request.form.get('floor', 0),
                room_type=request.form.get('room_type', 'DOUBLE'),
                base_rent=request.form['base_rent'],
                default_deposit=request.form.get('default_deposit'),
                is_active=1 if request.form.get('is_active') == 'on' else 0
            )
            flash("Room updated successfully.", "success")
            return redirect(url_for('admin.rooms_index'))
        except Exception as e:
            flash(str(e), "danger")
    return render_template('admin/rooms/form.html', room=room, properties=properties)


@admin_bp.route('/beds')
def beds_index():
    status = request.args.get('status')
    property_id = request.args.get('property_id')
    beds = get_beds(property_id=property_id, status=status)
    properties = get_all_properties(active_only=True)
    rooms = get_rooms_by_property()
    return render_template('admin/beds/index.html', beds=beds, properties=properties, rooms=rooms,
                           selected_status=status, selected_prop=property_id)


@admin_bp.route('/beds/create', methods=['POST'])
def bed_create():
    room_id = request.form.get('room_id')
    bed_number = request.form.get('bed_number')
    if room_id and bed_number:
        try:
            create_bed(int(room_id), bed_number)
            flash("Bed added successfully.", "success")
        except Exception as e:
            flash(str(e), "danger")
    return redirect(url_for('admin.beds_index'))


@admin_bp.route('/beds/<int:id>/approve-cleaning', methods=['POST'])
def bed_approve_cleaning(id):
    try:
        approve_bed_maintenance(id, session['user']['id'])
        flash("Bed approved and returned to AVAILABLE status.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(request.referrer or url_for('admin.beds_index'))


# --- Tenants & Allocations ---

@admin_bp.route('/tenants')
def tenants_index():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    sql = """
        SELECT t.*, u.first_name, u.last_name, u.email, u.phone,
               ta.id AS active_alloc_id, b.bed_number, r.room_number, p.name AS property_name
        FROM tenants t
        JOIN users u ON u.id = t.user_id
        LEFT JOIN tenant_allocations ta ON ta.tenant_id = t.id AND ta.status = 'ACTIVE'
        LEFT JOIN beds b ON b.id = ta.bed_id
        LEFT JOIN rooms r ON r.id = b.room_id
        LEFT JOIN properties p ON p.id = r.property_id
    """
    conditions = []
    params = []
    if status:
        conditions.append("t.status = %s")
        params.append(status)
    if search:
        conditions.append("(u.first_name LIKE %s OR u.last_name LIKE %s OR u.email LIKE %s OR u.phone LIKE %s)")
        term = f"%{search}%"
        params.extend([term, term, term, term])

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY t.created_at DESC"
    tenants = query_db(sql, tuple(params))
    return render_template('admin/tenants/index.html', tenants=tenants, search=search, selected_status=status)


@admin_bp.route('/tenants/create', methods=['GET', 'POST'])
def tenant_create():
    if request.method == 'POST':
        try:
            tenant_id = register_tenant(
                email=request.form['email'],
                password=request.form['password'],
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                phone=request.form['phone'],
                emergency_name=request.form['emergency_name'],
                emergency_phone=request.form['emergency_phone'],
                id_proof_type=request.form.get('id_proof_type', 'Aadhaar'),
                id_proof_number=request.form['id_proof_number'],
                permanent_address=request.form['permanent_address']
            )
            flash("Tenant account registered successfully. You may now allocate a bed.", "success")
            return redirect(url_for('admin.tenant_view', id=tenant_id))
        except Exception as e:
            flash(str(e), "danger")
    return render_template('admin/tenants/form.html')


@admin_bp.route('/tenants/<int:id>')
def tenant_view(id):
    sql = """
        SELECT t.*, u.first_name, u.last_name, u.email, u.phone
        FROM tenants t
        JOIN users u ON u.id = t.user_id
        WHERE t.id = %s
    """
    tenant = query_db(sql, (id,), one=True)
    if not tenant:
        abort(404)

    # Allocations history
    alloc_sql = """
        SELECT ta.*, b.bed_number, r.room_number, r.room_type, p.name AS property_name,
               sd.settlement_status, sd.total_deposit_received, sd.refund_amount
        FROM tenant_allocations ta
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        LEFT JOIN security_deposits sd ON sd.allocation_id = ta.id
        WHERE ta.tenant_id = %s
        ORDER BY ta.check_in_date DESC
    """
    allocations = query_db(alloc_sql, (id,))

    # Invoices & payments
    invoices = get_invoices(tenant_id=id)
    payments = get_payments_ledger(tenant_id=id)
    available_beds = get_available_beds()

    return render_template('admin/tenants/view.html',
                           tenant=tenant, allocations=allocations,
                           invoices=invoices, payments=payments, available_beds=available_beds)


@admin_bp.route('/allocations/check-in', methods=['GET', 'POST'])
def checkin():
    if request.method == 'POST':
        tenant_id = request.form['tenant_id']
        bed_id = request.form['bed_id']
        check_in_date = request.form['check_in_date']
        expected_checkout_date = request.form.get('expected_checkout_date')
        monthly_rent = request.form['monthly_rent']
        security_deposit_amount = request.form['security_deposit_amount']

        try:
            allocate_bed_check_in(
                tenant_id=int(tenant_id),
                bed_id=int(bed_id),
                check_in_date=check_in_date,
                expected_checkout_date=expected_checkout_date,
                monthly_rent=monthly_rent,
                security_deposit_amount=security_deposit_amount,
                actor_user_id=session['user']['id']
            )
            flash("Tenant check-in completed successfully!", "success")
            return redirect(url_for('admin.tenant_view', id=tenant_id))
        except Exception as e:
            flash(str(e), "danger")

    # For GET: fetch unallocated or checked-out tenants and available beds
    tenants = query_db("""
        SELECT t.id, u.first_name, u.last_name, u.email, u.phone
        FROM tenants t
        JOIN users u ON u.id = t.user_id
        WHERE t.id NOT IN (SELECT tenant_id FROM tenant_allocations WHERE status = 'ACTIVE')
        ORDER BY u.first_name ASC
    """)
    beds = get_available_beds()
    return render_template('admin/allocations/checkin.html', tenants=tenants, beds=beds)


@admin_bp.route('/allocations/<int:id>/transfer', methods=['POST'])
def transfer(id):
    new_bed_id = request.form['new_bed_id']
    transfer_date = request.form.get('transfer_date')
    try:
        transfer_room_bed(id, int(new_bed_id), transfer_date, actor_user_id=session['user']['id'])
        flash("Room transfer completed successfully.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(request.referrer or url_for('admin.tenants_index'))


@admin_bp.route('/allocations/<int:id>/checkout-inspect', methods=['GET', 'POST'])
def checkout_inspect(id):
    alloc = query_db("""
        SELECT ta.*, u.first_name, u.last_name, b.bed_number, r.room_number, p.name AS property_name,
               sd.id AS deposit_id, sd.total_deposit_received, sd.deductions_amount, sd.refund_amount, sd.settlement_status
        FROM tenant_allocations ta
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        JOIN tenants t ON t.id = ta.tenant_id
        JOIN users u ON u.id = t.user_id
        JOIN security_deposits sd ON sd.allocation_id = ta.id
        WHERE ta.id = %s
    """, (id,), one=True)
    if not alloc:
        abort(404)

    if request.method == 'POST':
        # Parse deductions items
        categories = request.form.getlist('category[]')
        amounts = request.form.getlist('amount[]')
        reasons = request.form.getlist('reason[]')
        notes = request.form.get('settlement_notes', '')

        deductions = []
        for cat, amt, rsn in zip(categories, amounts, reasons):
            if amt and float(amt) > 0:
                deductions.append({'category': cat, 'amount': amt, 'reason': rsn})

        try:
            record_checkout_inspection(id, deductions, settlement_notes=notes)
            flash("Inspection and deductions recorded. Review final settlement.", "success")
            return redirect(url_for('admin.checkout_inspect', id=id))
        except Exception as e:
            flash(str(e), "danger")

    # Fetch existing itemized deductions
    deductions_items = query_db("SELECT * FROM deposit_deductions WHERE deposit_id = %s", (alloc['deposit_id'],))
    return render_template('admin/allocations/checkout_inspect.html', allocation=alloc, deductions=deductions_items)


@admin_bp.route('/allocations/<int:id>/checkout-settle', methods=['POST'])
def checkout_settle(id):
    actual_date = request.form.get('actual_checkout_date')
    try:
        finalize_checkout_settlement(id, actual_date, authorizer_user_id=session['user']['id'])
        flash("Checkout settlement finalized. Bed is now UNDER_MAINTENANCE.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('admin.tenants_index'))


# --- Invoices & Billing ---

@admin_bp.route('/invoices')
def invoices_index():
    status = request.args.get('status')
    billing_month = request.args.get('billing_month')
    property_id = request.args.get('property_id')
    invoices = get_invoices(property_id=property_id, status=status, billing_month=billing_month)
    properties = get_all_properties(active_only=True)
    return render_template('admin/invoices/index.html',
                           invoices=invoices, properties=properties,
                           selected_status=status, selected_month=billing_month, selected_prop=property_id)


@admin_bp.route('/invoices/generate', methods=['POST'])
def invoices_generate():
    billing_month = request.form['billing_month']
    due_date = request.form['due_date']
    property_id = request.form.get('property_id') or None
    try:
        cnt = generate_monthly_invoices(billing_month, due_date, property_id=property_id, actor_user_id=session['user']['id'])
        flash(f"Generated {cnt} invoices for {billing_month}.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('admin.invoices_index'))


@admin_bp.route('/invoices/<int:id>')
def invoice_view(id):
    inv = get_invoice_by_id(id)
    if not inv:
        abort(404)
    return render_template('admin/invoices/view.html', invoice=inv)


@admin_bp.route('/payments')
def payments_index():
    payments = get_payments_ledger()
    return render_template('admin/payments/index.html', payments=payments)


@admin_bp.route('/payments/record', methods=['GET', 'POST'])
def payment_record():
    if request.method == 'POST':
        invoice_id = request.form['invoice_id']
        amount = request.form['amount']
        method = request.form['payment_method']
        ref = request.form['transaction_reference']
        notes = request.form.get('notes')

        try:
            record_payment(
                invoice_id=int(invoice_id),
                amount=amount,
                payment_method=method,
                transaction_reference=ref,
                recorded_by_user_id=session['user']['id'],
                notes=notes
            )
            flash("Payment logged successfully.", "success")
            return redirect(url_for('admin.invoice_view', id=invoice_id))
        except Exception as e:
            flash(str(e), "danger")

    # For GET: get open/partial/overdue invoices
    open_invoices = query_db("""
        SELECT inv.id, inv.invoice_number, inv.balance_due, inv.billing_month,
               u.first_name, u.last_name, p.name AS property_name
        FROM invoices inv
        JOIN tenant_allocations ta ON ta.id = inv.allocation_id
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        JOIN tenants t ON t.id = ta.tenant_id
        JOIN users u ON u.id = t.user_id
        WHERE inv.balance_due > 0
        ORDER BY inv.due_date ASC
    """)
    preselected_invoice = request.args.get('invoice_id')
    return render_template('admin/payments/form.html', invoices=open_invoices, selected_inv=preselected_invoice)


@admin_bp.route('/deposits')
def deposits_index():
    sql = """
        SELECT sd.*, u.first_name, u.last_name, u.phone,
               p.name AS property_name, r.room_number, b.bed_number,
               u_auth.first_name AS authorizer_first
        FROM security_deposits sd
        JOIN tenant_allocations ta ON ta.id = sd.allocation_id
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        JOIN tenants t ON t.id = sd.tenant_id
        JOIN users u ON u.id = t.user_id
        LEFT JOIN users u_auth ON u_auth.id = sd.authorized_by_user_id
        ORDER BY sd.created_at DESC
    """
    deposits = query_db(sql)
    return render_template('admin/deposits/index.html', deposits=deposits)


# --- Utilities ---

@admin_bp.route('/utilities/meters')
def utility_meters_index():
    meters = get_utility_meters()
    properties = get_all_properties(active_only=True)
    rooms = get_rooms_by_property()
    return render_template('admin/utilities/meters.html', meters=meters, properties=properties, rooms=rooms)


@admin_bp.route('/utilities/meters/create', methods=['POST'])
def utility_meter_create():
    prop_id = request.form['property_id']
    room_id = request.form.get('room_id') or None
    m_type = request.form.get('meter_type', 'ELECTRICITY')
    tag = request.form['meter_identifier']
    rate = request.form['rate_per_unit']
    try:
        create_utility_meter(prop_id, room_id, m_type, tag, rate)
        flash("Utility meter registered.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('admin.utility_meters_index'))


@admin_bp.route('/utilities/readings')
def utility_readings_index():
    readings = get_utility_readings()
    meters = get_utility_meters()
    return render_template('admin/utilities/readings.html', readings=readings, meters=meters)


@admin_bp.route('/utilities/readings/record', methods=['POST'])
def utility_reading_record():
    meter_id = request.form['meter_id']
    curr_reading = request.form['current_reading']
    start_date = request.form['billing_period_start']
    end_date = request.form['billing_period_end']
    try:
        record_meter_reading(int(meter_id), curr_reading, start_date, end_date, session['user']['id'])
        flash("Utility reading logged and charge computed.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('admin.utility_readings_index'))


# --- Complaints & Notices ---

@admin_bp.route('/complaints')
def complaints_index():
    status = request.args.get('status')
    property_id = request.args.get('property_id')
    complaints = get_complaints(property_id=property_id, status=status)
    properties = get_all_properties(active_only=True)
    return render_template('admin/complaints/index.html', complaints=complaints, properties=properties,
                           selected_status=status, selected_prop=property_id)


@admin_bp.route('/complaints/<int:id>')
def complaint_view(id):
    complaint = get_complaint_by_id(id)
    if not complaint:
        abort(404)
    staff_users = query_db("SELECT id, first_name, last_name, role FROM users WHERE role IN ('ADMIN', 'MANAGER') AND is_active = 1")
    return render_template('admin/complaints/view.html', complaint=complaint, staff_users=staff_users)


@admin_bp.route('/complaints/<int:id>/status', methods=['POST'])
def complaint_update(id):
    new_status = request.form['status']
    assigned_to = request.form.get('assigned_to_user_id') or None
    notes = request.form.get('resolution_notes')
    try:
        update_complaint_status(id, new_status, assigned_to_user_id=assigned_to,
                                resolution_notes=notes, actor_user_id=session['user']['id'])
        flash("Complaint status updated.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('admin.complaint_view', id=id))


@admin_bp.route('/notices')
def notices_index():
    notices = get_notices(role='ALL')
    properties = get_all_properties(active_only=True)
    return render_template('admin/notices/index.html', notices=notices, properties=properties)


@admin_bp.route('/notices/create', methods=['GET', 'POST'])
def notice_create():
    if request.method == 'POST':
        prop_id = request.form.get('property_id') or None
        audience = request.form.get('target_audience', 'ALL')
        title = request.form['title']
        content = request.form['content']
        expires_at = request.form.get('expires_at') or None
        try:
            create_notice(session['user']['id'], title, content, property_id=prop_id,
                          target_audience=audience, expires_at=expires_at)
            flash("Notice announcement published.", "success")
            return redirect(url_for('admin.notices_index'))
        except Exception as e:
            flash(str(e), "danger")
    properties = get_all_properties(active_only=True)
    return render_template('admin/notices/form.html', properties=properties)


@admin_bp.route('/notices/<int:id>/delete', methods=['POST'])
def notice_delete(id):
    delete_notice(id, actor_user_id=session['user']['id'])
    flash("Notice deleted.", "info")
    return redirect(url_for('admin.notices_index'))


# --- Reports & Audit ---

@admin_bp.route('/reports/occupancy')
def report_occupancy():
    prop_id = request.args.get('property_id')
    report_data = get_occupancy_report(property_id=prop_id)
    properties = get_all_properties(active_only=True)
    return render_template('admin/reports/occupancy.html', report_data=report_data, properties=properties, selected_prop=prop_id)


@admin_bp.route('/reports/revenue')
def report_revenue():
    month = request.args.get('billing_month')
    report_data = get_revenue_report(billing_month=month)
    return render_template('admin/reports/revenue.html', report_data=report_data, selected_month=month)


@admin_bp.route('/reports/defaulters')
def report_defaulters():
    prop_id = request.args.get('property_id')
    defaulters = get_defaulters_report(property_id=prop_id)
    properties = get_all_properties(active_only=True)
    return render_template('admin/reports/defaulters.html', defaulters=defaulters, properties=properties, selected_prop=prop_id)


@admin_bp.route('/audit-logs')
def audit_logs_index():
    logs = get_audit_logs()
    return render_template('admin/audit_logs/index.html', logs=logs)
