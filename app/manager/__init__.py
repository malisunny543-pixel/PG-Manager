from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from app.extensions import login_required, role_required
from app.db import query_db
from app.services import (
    get_manager_dashboard_stats, get_rooms_by_property, get_room_by_id,
    create_room, update_room, get_beds, create_bed, approve_bed_maintenance,
    get_available_beds, allocate_bed_check_in, record_checkout_inspection,
    record_payment, record_meter_reading,
    get_complaints, get_complaint_by_id, update_complaint_status,
    get_notices, create_notice, register_tenant, get_invoices, get_payments_ledger
)

manager_bp = Blueprint('manager', __name__, url_prefix='/manager')

@manager_bp.before_request
@login_required
@role_required('MANAGER')
def enforce_manager():
    pass


def _get_manager_props():
    """Retrieve list of property IDs assigned to current manager."""
    props = session['user'].get('managed_property_ids', [])
    if not props:
        # Refresh from database if not in session
        rows = query_db("SELECT property_id FROM property_managers WHERE user_id = %s", (session['user']['id'],))
        props = [r['property_id'] for r in rows]
        session['user']['managed_property_ids'] = props
    return props


@manager_bp.route('/dashboard')
def dashboard():
    prop_ids = _get_manager_props()
    stats = get_manager_dashboard_stats(prop_ids)
    return render_template('manager/dashboard.html', **stats)


@manager_bp.route('/rooms')
def rooms_index():
    prop_ids = _get_manager_props()
    if not prop_ids:
        return render_template('manager/rooms/index.html', rooms=[])
    rooms = get_rooms_by_property(property_id=prop_ids[0])
    return render_template('manager/rooms/index.html', rooms=rooms)


@manager_bp.route('/rooms/create', methods=['GET', 'POST'])
def room_create():
    prop_ids = _get_manager_props()
    if not prop_ids:
        flash("No assigned property found.", "danger")
        return redirect(url_for('manager.rooms_index'))

    if request.method == 'POST':
        try:
            create_room(
                property_id=prop_ids[0],
                room_number=request.form['room_number'],
                floor=request.form.get('floor', 0),
                room_type=request.form.get('room_type', 'DOUBLE'),
                base_rent=request.form['base_rent'],
                default_deposit=request.form.get('default_deposit')
            )
            flash("Room created in assigned property.", "success")
            return redirect(url_for('manager.rooms_index'))
        except Exception as e:
            flash(str(e), "danger")
    return render_template('manager/rooms/form.html', room=None)


@manager_bp.route('/rooms/<int:id>/edit', methods=['GET', 'POST'])
def room_edit(id):
    prop_ids = _get_manager_props()
    room = get_room_by_id(id)
    if not room or room['property_id'] not in prop_ids:
        abort(403)

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
            flash("Room updated.", "success")
            return redirect(url_for('manager.rooms_index'))
        except Exception as e:
            flash(str(e), "danger")
    return render_template('manager/rooms/form.html', room=room)


@manager_bp.route('/beds')
def beds_index():
    prop_ids = _get_manager_props()
    beds = get_beds(property_id=prop_ids[0]) if prop_ids else []
    rooms = get_rooms_by_property(property_id=prop_ids[0]) if prop_ids else []
    return render_template('manager/beds/index.html', beds=beds, rooms=rooms)


@manager_bp.route('/beds/create', methods=['POST'])
def bed_create():
    room_id = request.form.get('room_id')
    bed_number = request.form.get('bed_number')
    prop_ids = _get_manager_props()
    room = get_room_by_id(room_id)
    if not room or room['property_id'] not in prop_ids:
        abort(403)

    if room_id and bed_number:
        try:
            create_bed(int(room_id), bed_number)
            flash("Bed added.", "success")
        except Exception as e:
            flash(str(e), "danger")
    return redirect(url_for('manager.beds_index'))


@manager_bp.route('/beds/<int:id>/approve-cleaning', methods=['POST'])
def bed_approve_cleaning(id):
    try:
        approve_bed_maintenance(id, session['user']['id'])
        flash("Bed inspected, cleaned, and approved for AVAILABLE status.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(request.referrer or url_for('manager.beds_index'))


@manager_bp.route('/tenants')
def tenants_index():
    prop_ids = _get_manager_props()
    if not prop_ids:
        return render_template('manager/tenants/index.html', tenants=[])

    placeholders = ', '.join(['%s'] * len(prop_ids))
    sql = f"""
        SELECT t.*, u.first_name, u.last_name, u.email, u.phone,
               ta.id AS active_alloc_id, b.bed_number, r.room_number, p.name AS property_name
        FROM tenants t
        JOIN users u ON u.id = t.user_id
        JOIN tenant_allocations ta ON ta.tenant_id = t.id AND ta.status = 'ACTIVE'
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        WHERE p.id IN ({placeholders})
        ORDER BY r.room_number ASC, b.bed_number ASC
    """
    tenants = query_db(sql, tuple(prop_ids))
    return render_template('manager/tenants/index.html', tenants=tenants)


@manager_bp.route('/tenants/<int:id>')
def tenant_view(id):
    prop_ids = _get_manager_props()
    sql = """
        SELECT t.*, u.first_name, u.last_name, u.email, u.phone
        FROM tenants t
        JOIN users u ON u.id = t.user_id
        WHERE t.id = %s
    """
    tenant = query_db(sql, (id,), one=True)
    if not tenant:
        abort(404)

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
    invoices = get_invoices(tenant_id=id)
    payments = get_payments_ledger(tenant_id=id)

    return render_template('manager/tenants/view.html', tenant=tenant, allocations=allocations,
                           invoices=invoices, payments=payments)


@manager_bp.route('/allocations/check-in', methods=['GET', 'POST'])
def checkin():
    prop_ids = _get_manager_props()
    primary_prop = prop_ids[0] if prop_ids else None

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
            flash("Tenant checked in successfully!", "success")
            return redirect(url_for('manager.tenants_index'))
        except Exception as e:
            flash(str(e), "danger")

    tenants = query_db("""
        SELECT t.id, u.first_name, u.last_name, u.email, u.phone
        FROM tenants t
        JOIN users u ON u.id = t.user_id
        WHERE t.id NOT IN (SELECT tenant_id FROM tenant_allocations WHERE status = 'ACTIVE')
        ORDER BY u.first_name ASC
    """)
    beds = get_available_beds(property_id=primary_prop)
    return render_template('manager/allocations/checkin.html', tenants=tenants, beds=beds)


@manager_bp.route('/allocations/<int:id>/checkout-inspect', methods=['GET', 'POST'])
def checkout_inspect(id):
    prop_ids = _get_manager_props()
    alloc = query_db("""
        SELECT ta.*, u.first_name, u.last_name, b.bed_number, r.room_number, p.name AS property_name,
               r.property_id, sd.id AS deposit_id, sd.total_deposit_received, sd.deductions_amount, sd.settlement_status
        FROM tenant_allocations ta
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        JOIN tenants t ON t.id = ta.tenant_id
        JOIN users u ON u.id = t.user_id
        JOIN security_deposits sd ON sd.allocation_id = ta.id
        WHERE ta.id = %s
    """, (id,), one=True)
    if not alloc or alloc['property_id'] not in prop_ids:
        abort(403)

    if request.method == 'POST':
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
            flash("Inspection report recorded for administrative review.", "success")
            return redirect(url_for('manager.checkout_inspect', id=id))
        except Exception as e:
            flash(str(e), "danger")

    deductions_items = query_db("SELECT * FROM deposit_deductions WHERE deposit_id = %s", (alloc['deposit_id'],))
    return render_template('manager/allocations/checkout_inspect.html', allocation=alloc, deductions=deductions_items)


@manager_bp.route('/payments/record', methods=['GET', 'POST'])
def payment_record():
    prop_ids = _get_manager_props()
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
            return redirect(url_for('manager.dashboard'))
        except Exception as e:
            flash(str(e), "danger")

    # Open invoices in manager's property
    placeholders = ', '.join(['%s'] * len(prop_ids)) if prop_ids else '0'
    open_invoices = query_db(f"""
        SELECT inv.id, inv.invoice_number, inv.balance_due, inv.billing_month,
               u.first_name, u.last_name, p.name AS property_name
        FROM invoices inv
        JOIN tenant_allocations ta ON ta.id = inv.allocation_id
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        JOIN tenants t ON t.id = ta.tenant_id
        JOIN users u ON u.id = t.user_id
        WHERE inv.balance_due > 0 AND p.id IN ({placeholders})
        ORDER BY inv.due_date ASC
    """, tuple(prop_ids) if prop_ids else ())
    return render_template('manager/payments/form.html', invoices=open_invoices)


@manager_bp.route('/utilities/readings/record', methods=['POST'])
def utility_reading_record():
    meter_id = request.form['meter_id']
    curr_reading = request.form['current_reading']
    start_date = request.form['billing_period_start']
    end_date = request.form['billing_period_end']
    try:
        record_meter_reading(int(meter_id), curr_reading, start_date, end_date, session['user']['id'])
        flash("Utility reading logged.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('manager.dashboard'))


@manager_bp.route('/complaints')
def complaints_index():
    prop_ids = _get_manager_props()
    complaints = get_complaints(property_id=prop_ids[0]) if prop_ids else []
    return render_template('manager/complaints/index.html', complaints=complaints)


@manager_bp.route('/complaints/<int:id>')
def complaint_view(id):
    prop_ids = _get_manager_props()
    complaint = get_complaint_by_id(id)
    if not complaint or complaint['property_id'] not in prop_ids:
        abort(403)
    return render_template('manager/complaints/view.html', complaint=complaint)


@manager_bp.route('/complaints/<int:id>/status', methods=['POST'])
def complaint_status(id):
    prop_ids = _get_manager_props()
    complaint = get_complaint_by_id(id)
    if not complaint or complaint['property_id'] not in prop_ids:
        abort(403)

    new_status = request.form['status']
    notes = request.form.get('resolution_notes')
    try:
        update_complaint_status(id, new_status, assigned_to_user_id=session['user']['id'],
                                resolution_notes=notes, actor_user_id=session['user']['id'])
        flash("Complaint status updated.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('manager.complaint_view', id=id))


@manager_bp.route('/notices', methods=['GET', 'POST'])
def notices_index():
    prop_ids = _get_manager_props()
    primary_prop = prop_ids[0] if prop_ids else None
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        try:
            create_notice(session['user']['id'], title, content, property_id=primary_prop,
                          target_audience='TENANTS_ONLY')
            flash("Notice posted to property notice board.", "success")
        except Exception as e:
            flash(str(e), "danger")
    notices = get_notices(property_id=primary_prop, role='MANAGER')
    return render_template('manager/notices/index.html', notices=notices)
