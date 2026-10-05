from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from app.extensions import login_required, role_required
from app.db import query_db, execute_db
from app.services import (
    get_invoices, get_invoice_by_id, get_payments_ledger,
    create_complaint, get_complaints, get_complaint_by_id,
    get_notices, log_audit
)

tenant_bp = Blueprint('tenant', __name__, url_prefix='/tenant')

@tenant_bp.before_request
@login_required
@role_required('TENANT')
def enforce_tenant():
    pass


def _get_tenant_id():
    """Retrieve verified tenant_id for the current logged-in user."""
    t_id = session['user'].get('tenant_id')
    if not t_id:
        t_row = query_db("SELECT id FROM tenants WHERE user_id = %s", (session['user']['id'],), one=True)
        if t_row:
            t_id = t_row['id']
            session['user']['tenant_id'] = t_id
    return t_id


@tenant_bp.route('/dashboard')
def dashboard():
    tenant_id = _get_tenant_id()
    if not tenant_id:
        flash("Tenant profile incomplete.", "warning")
        return redirect(url_for('shared.profile'))

    # Fetch active allocation
    alloc = query_db("""
        SELECT ta.*, b.bed_number, r.room_number, r.room_type, p.id AS property_id, p.name AS property_name,
               sd.total_deposit_received
        FROM tenant_allocations ta
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        LEFT JOIN security_deposits sd ON sd.allocation_id = ta.id
        WHERE ta.tenant_id = %s AND ta.status = 'ACTIVE'
    """, (tenant_id,), one=True)

    # Balance due across all unpaid invoices
    bal_row = query_db(
        "SELECT SUM(balance_due) AS total_bal FROM invoices inv JOIN tenant_allocations ta ON ta.id = inv.allocation_id WHERE ta.tenant_id = %s",
        (tenant_id,), one=True
    )
    balance_due = bal_row['total_bal'] if bal_row and bal_row['total_bal'] else Decimal('0.00')

    # Recent notices
    prop_id = alloc['property_id'] if alloc else None
    notices = get_notices(property_id=prop_id, role='TENANT')[:3]

    return render_template('tenant/dashboard.html',
                           allocation=alloc,
                           room_number=alloc['room_number'] if alloc else None,
                           bed_number=alloc['bed_number'] if alloc else None,
                           property_name=alloc['property_name'] if alloc else 'No Active Allocation',
                           monthly_rent=alloc['monthly_rent'] if alloc else Decimal('0.00'),
                           security_deposit=alloc['total_deposit_received'] if alloc and alloc['total_deposit_received'] else Decimal('0.00'),
                           balance_due=balance_due,
                           notices=notices)


@tenant_bp.route('/profile')
def profile():
    tenant_id = _get_tenant_id()
    tenant = query_db("""
        SELECT t.*, u.first_name, u.last_name, u.email, u.phone
        FROM tenants t
        JOIN users u ON u.id = t.user_id
        WHERE t.id = %s
    """, (tenant_id,), one=True)
    return render_template('tenant/profile.html', tenant=tenant)


@tenant_bp.route('/tenancy')
def tenancy():
    tenant_id = _get_tenant_id()
    alloc = query_db("""
        SELECT ta.*, b.bed_number, r.id AS room_id, r.room_number, r.room_type, r.base_rent,
               p.name AS property_name, p.code AS property_code, p.address AS property_address,
               p.contact_phone AS property_phone
        FROM tenant_allocations ta
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        WHERE ta.tenant_id = %s AND ta.status = 'ACTIVE'
    """, (tenant_id,), one=True)

    room_mates = []
    if alloc:
        room_mates = query_db("""
            SELECT u.first_name, u.last_name, b.bed_number, ta.check_in_date
            FROM tenant_allocations ta
            JOIN beds b ON b.id = ta.bed_id
            JOIN tenants t ON t.id = ta.tenant_id
            JOIN users u ON u.id = t.user_id
            WHERE b.room_id = %s AND ta.status = 'ACTIVE' AND ta.id != %s
        """, (alloc['room_id'], alloc['id']))

    return render_template('tenant/tenancy.html', allocation=alloc, room_mates=room_mates)


@tenant_bp.route('/invoices')
def invoices():
    tenant_id = _get_tenant_id()
    invs = get_invoices(tenant_id=tenant_id)
    return render_template('tenant/invoices/index.html', invoices=invs)


@tenant_bp.route('/invoices/<int:id>')
def invoice_view(id):
    tenant_id = _get_tenant_id()
    inv = get_invoice_by_id(id)
    if not inv or inv['tenant_id'] != tenant_id:
        abort(403)
    return render_template('tenant/invoices/view.html', invoice=inv)


@tenant_bp.route('/payments')
def payments():
    tenant_id = _get_tenant_id()
    pmts = get_payments_ledger(tenant_id=tenant_id)
    return render_template('tenant/payments/index.html', payments=pmts)


@tenant_bp.route('/complaints')
def complaints():
    tenant_id = _get_tenant_id()
    cmps = get_complaints(tenant_id=tenant_id)
    return render_template('tenant/complaints/index.html', complaints=cmps)


@tenant_bp.route('/complaints/create', methods=['GET', 'POST'])
def complaint_create():
    tenant_id = _get_tenant_id()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form.get('category', 'OTHER')
        priority = request.form.get('priority', 'MEDIUM')
        try:
            create_complaint(tenant_id, title, description, category=category, priority=priority)
            flash("Complaint submitted. Our team will look into it promptly.", "success")
            return redirect(url_for('tenant.complaints'))
        except Exception as e:
            flash(str(e), "danger")
    return render_template('tenant/complaints/form.html')


@tenant_bp.route('/complaints/<int:id>')
def complaint_view(id):
    tenant_id = _get_tenant_id()
    complaint = get_complaint_by_id(id)
    if not complaint or complaint['tenant_id'] != tenant_id:
        abort(403)
    return render_template('tenant/complaints/view.html', complaint=complaint)


@tenant_bp.route('/notices')
def notices():
    tenant_id = _get_tenant_id()
    alloc = query_db(
        "SELECT r.property_id FROM tenant_allocations ta JOIN beds b ON b.id = ta.bed_id JOIN rooms r ON r.id = b.room_id WHERE ta.tenant_id = %s AND ta.status = 'ACTIVE'",
        (tenant_id,), one=True
    )
    prop_id = alloc['property_id'] if alloc else None
    notice_list = get_notices(property_id=prop_id, role='TENANT')
    return render_template('tenant/notices/index.html', notices=notice_list)


@tenant_bp.route('/checkout-request', methods=['GET', 'POST'])
def checkout_request():
    tenant_id = _get_tenant_id()
    alloc = query_db(
        "SELECT id FROM tenant_allocations WHERE tenant_id = %s AND status = 'ACTIVE'",
        (tenant_id,), one=True
    )
    if not alloc:
        flash("You do not currently have an active bed allocation.", "warning")
        return redirect(url_for('tenant.dashboard'))

    if request.method == 'POST':
        expected_date = request.form.get('expected_checkout_date')
        reason = request.form.get('reason', '')
        # Update expected checkout date on active allocation
        execute_db(
            "UPDATE tenant_allocations SET expected_checkout_date = %s WHERE id = %s",
            (expected_date, alloc['id'])
        )
        log_audit('CHECKOUT_REQUESTED', 'tenant_allocations', alloc['id'], {
            'expected_date': str(expected_date),
            'reason': reason
        }, actor_id=session['user']['id'])
        flash("Checkout notice submitted successfully. Warden has been informed.", "success")
        return redirect(url_for('tenant.dashboard'))

    return render_template('tenant/checkout_request.html', allocation=alloc)
