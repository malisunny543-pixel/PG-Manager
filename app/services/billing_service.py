from decimal import Decimal
from datetime import date, datetime
from app.db import query_db, execute_db, db_transaction
from app.services.audit_service import log_audit

# --- Invoices ---

def get_invoices(property_id=None, status=None, billing_month=None, tenant_id=None):
    """Retrieve invoices with allocation, room, and property details."""
    sql = """
        SELECT inv.*,
               ta.tenant_id, ta.bed_id,
               b.bed_number, r.room_number,
               p.id AS property_id, p.name AS property_name, p.code AS property_code,
               u.first_name, u.last_name, u.email, u.phone
        FROM invoices inv
        JOIN tenant_allocations ta ON ta.id = inv.allocation_id
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        JOIN tenants t ON t.id = ta.tenant_id
        JOIN users u ON u.id = t.user_id
    """
    conditions = []
    params = []
    if property_id:
        conditions.append("p.id = %s")
        params.append(property_id)
    if status:
        conditions.append("inv.status = %s")
        params.append(status)
    if billing_month:
        conditions.append("inv.billing_month = %s")
        params.append(billing_month)
    if tenant_id:
        conditions.append("ta.tenant_id = %s")
        params.append(tenant_id)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY inv.due_date DESC, inv.id DESC"
    return query_db(sql, tuple(params))


def get_invoice_by_id(invoice_id):
    """Fetch a single invoice with complete line-item breakdown and payment transactions."""
    sql = """
        SELECT inv.*,
               ta.tenant_id, ta.bed_id, ta.monthly_rent AS agreed_monthly_rent,
               b.bed_number, r.room_number, r.room_type,
               p.id AS property_id, p.name AS property_name, p.code AS property_code,
               u.first_name, u.last_name, u.email, u.phone
        FROM invoices inv
        JOIN tenant_allocations ta ON ta.id = inv.allocation_id
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        JOIN tenants t ON t.id = ta.tenant_id
        JOIN users u ON u.id = t.user_id
        WHERE inv.id = %s
    """
    inv = query_db(sql, (invoice_id,), one=True)
    if not inv:
        return None

    # Fetch associated payments
    payments_sql = """
        SELECT p.*, u.first_name AS recorded_by_first, u.last_name AS recorded_by_last
        FROM payments p
        JOIN users u ON u.id = p.recorded_by_user_id
        WHERE p.invoice_id = %s
        ORDER BY p.payment_date ASC
    """
    inv['payments'] = query_db(payments_sql, (invoice_id,))
    return inv


def generate_monthly_invoices(billing_month, due_date, property_id=None, actor_user_id=None):
    """Generate rent invoices for all ACTIVE tenant allocations in the given month.
    Idempotent: skips allocations that already have an invoice for this billing_month.
    """
    sql = """
        SELECT ta.id AS allocation_id, ta.monthly_rent, r.property_id
        FROM tenant_allocations ta
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        WHERE ta.status = 'ACTIVE'
    """
    params = []
    if property_id:
        sql += " AND r.property_id = %s"
        params.append(property_id)

    allocations = query_db(sql, tuple(params))
    generated_count = 0

    with db_transaction():
        for alloc in allocations:
            alloc_id = alloc['allocation_id']
            # Check if invoice exists
            exists = query_db(
                "SELECT id FROM invoices WHERE allocation_id = %s AND billing_month = %s",
                (alloc_id, billing_month), one=True
            )
            if exists:
                continue

            inv_number = f"INV-{billing_month.replace('-', '')}-{alloc_id:04d}"
            rent_amt = Decimal(str(alloc['monthly_rent']))
            total_amt = rent_amt
            bal_due = total_amt

            execute_db(
                """INSERT INTO invoices
                   (allocation_id, invoice_number, billing_month, due_date, rent_amount, utility_amount, total_amount, paid_amount, balance_due, status)
                   VALUES (%s, %s, %s, %s, %s, 0.00, %s, 0.00, %s, 'UNPAID')""",
                (alloc_id, inv_number, billing_month, due_date, rent_amt, total_amt, bal_due),
                commit=False
            )
            generated_count += 1

        log_audit('INVOICES_GENERATED', 'invoices', 0, {
            'billing_month': billing_month,
            'count': generated_count,
            'property_id': property_id
        }, actor_id=actor_user_id)

    return generated_count


# --- Payments ---

def record_payment(invoice_id, amount, payment_method, transaction_reference, recorded_by_user_id, notes=None):
    """Record a payment (partial or full) against an invoice using atomic transaction.
    Recalculates paid_amount, balance_due, and updates invoice status.
    """
    pay_amount = Decimal(str(amount))
    if pay_amount <= Decimal('0.00'):
        raise ValueError("Payment amount must be greater than zero.")

    with db_transaction() as conn:
        with conn.cursor() as cur:
            # Lock invoice row
            cur.execute(
                """SELECT inv.id, inv.allocation_id, inv.total_amount, inv.paid_amount, inv.balance_due,
                          ta.tenant_id
                   FROM invoices inv
                   JOIN tenant_allocations ta ON ta.id = inv.allocation_id
                   WHERE inv.id = %s FOR UPDATE""",
                (invoice_id,)
            )
            inv = cur.fetchone()
            if not inv:
                raise ValueError("Invoice not found.")

            current_paid = Decimal(str(inv['paid_amount']))
            total_amt = Decimal(str(inv['total_amount']))
            current_balance = Decimal(str(inv['balance_due']))

            if pay_amount > current_balance:
                raise ValueError(f"Payment amount (₹{pay_amount}) cannot exceed outstanding balance (₹{current_balance}).")

            # 1. Insert payment record
            cur.execute(
                """INSERT INTO payments
                   (invoice_id, tenant_id, amount, payment_method, transaction_reference, recorded_by_user_id, notes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (invoice_id, inv['tenant_id'], pay_amount, payment_method, transaction_reference.strip(), recorded_by_user_id, notes)
            )
            payment_id = cur.lastrowid

            # 2. Update invoice paid_amount, balance_due, and status
            new_paid = current_paid + pay_amount
            new_balance = total_amt - new_paid
            new_status = 'PAID' if new_balance == Decimal('0.00') else 'PARTIAL'

            cur.execute(
                "UPDATE invoices SET paid_amount = %s, balance_due = %s, status = %s WHERE id = %s",
                (new_paid, new_balance, new_status, invoice_id)
            )

            # 3. Create in-app notification for the tenant's user
            cur.execute("SELECT user_id FROM tenants WHERE id = %s", (inv['tenant_id'],))
            t_user = cur.fetchone()
            if t_user:
                cur.execute(
                    """INSERT INTO notifications (user_id, title, message, category, is_read)
                       VALUES (%s, %s, %s, 'PAYMENT_RECEIVED', 0)""",
                    (t_user['user_id'], 'Payment Recorded',
                     f"Payment of ₹{pay_amount:,.2f} recorded successfully (Ref: {transaction_reference}).")
                )

            log_audit('PAYMENT_RECORDED', 'payments', payment_id, {
                'invoice_id': invoice_id,
                'amount': str(pay_amount),
                'method': payment_method,
                'ref': transaction_reference
            }, actor_id=recorded_by_user_id)

    return payment_id


def get_payments_ledger(property_id=None, tenant_id=None):
    """Retrieve payments ledger with invoice and recorder details."""
    sql = """
        SELECT p.*, inv.invoice_number, inv.billing_month,
               u_ten.first_name AS tenant_first_name, u_ten.last_name AS tenant_last_name,
               u_rec.first_name AS recorded_by_first, u_rec.last_name AS recorded_by_last,
               prop.name AS property_name
        FROM payments p
        JOIN invoices inv ON inv.id = p.invoice_id
        JOIN tenant_allocations ta ON ta.id = inv.allocation_id
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties prop ON prop.id = r.property_id
        JOIN tenants t ON t.id = p.tenant_id
        JOIN users u_ten ON u_ten.id = t.user_id
        JOIN users u_rec ON u_rec.id = p.recorded_by_user_id
    """
    conditions = []
    params = []
    if property_id:
        conditions.append("prop.id = %s")
        params.append(property_id)
    if tenant_id:
        conditions.append("p.tenant_id = %s")
        params.append(tenant_id)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY p.payment_date DESC, p.id DESC"
    return query_db(sql, tuple(params))


# --- Utilities ---

def get_utility_meters(property_id=None):
    """Fetch utility meters with room and property associations."""
    sql = """
        SELECT m.*, p.name AS property_name, p.code AS property_code,
               r.room_number,
               (SELECT current_reading FROM utility_readings WHERE meter_id = m.id ORDER BY id DESC LIMIT 1) AS last_reading
        FROM utility_meters m
        JOIN properties p ON p.id = m.property_id
        LEFT JOIN rooms r ON r.id = m.room_id
    """
    params = []
    if property_id:
        sql += " WHERE m.property_id = %s"
        params.append(property_id)
    sql += " ORDER BY p.name ASC, m.meter_identifier ASC"
    return query_db(sql, tuple(params))


def create_utility_meter(property_id, room_id, meter_type, meter_identifier, rate_per_unit):
    """Create a new utility meter with a configurable rate per unit."""
    rate = Decimal(str(rate_per_unit))
    sql = """
        INSERT INTO utility_meters (property_id, room_id, meter_type, meter_identifier, rate_per_unit, is_active)
        VALUES (%s, %s, %s, %s, %s, 1)
    """
    res = execute_db(sql, (property_id, room_id or None, meter_type, meter_identifier.strip(), rate))
    meter_id = res['lastrowid']
    log_audit('METER_CREATED', 'utility_meters', meter_id, {
        'identifier': meter_identifier,
        'rate': str(rate)
    })
    return meter_id


def record_meter_reading(meter_id, current_reading, start_date, end_date, verified_by_user_id):
    """Record a utility meter reading.
    Calculates units_consumed = current - previous, and total_charge = units_consumed * rate_per_unit.
    Uses Python Decimal throughout.
    """
    curr_rdg = Decimal(str(current_reading))

    with db_transaction() as conn:
        with conn.cursor() as cur:
            # 1. Fetch meter details & latest reading
            cur.execute("SELECT id, rate_per_unit FROM utility_meters WHERE id = %s", (meter_id,))
            meter = cur.fetchone()
            if not meter:
                raise ValueError("Meter not found.")

            cur.execute(
                "SELECT current_reading FROM utility_readings WHERE meter_id = %s ORDER BY id DESC LIMIT 1",
                (meter_id,)
            )
            last_reading_row = cur.fetchone()
            prev_rdg = Decimal(str(last_reading_row['current_reading'])) if last_reading_row else Decimal('0.00')

            if curr_rdg < prev_rdg:
                raise ValueError(f"Current reading ({curr_rdg}) cannot be lower than previous reading ({prev_rdg}).")

            units = curr_rdg - prev_rdg
            rate = Decimal(str(meter['rate_per_unit']))
            charge = units * rate

            # 2. Insert reading
            cur.execute(
                """INSERT INTO utility_readings
                   (meter_id, previous_reading, current_reading, units_consumed, rate_per_unit, total_charge,
                    billing_period_start, billing_period_end, verified_by_user_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (meter_id, prev_rdg, curr_rdg, units, rate, charge, start_date, end_date, verified_by_user_id)
            )
            reading_id = cur.lastrowid

            log_audit('METER_READING_RECORDED', 'utility_readings', reading_id, {
                'meter_id': meter_id,
                'units': str(units),
                'charge': str(charge)
            }, actor_id=verified_by_user_id)

    return reading_id


def get_utility_readings(property_id=None):
    """List historical utility readings."""
    sql = """
        SELECT ur.*, m.meter_identifier, m.meter_type,
               p.name AS property_name, r.room_number,
               u.first_name AS verifier_first, u.last_name AS verifier_last
        FROM utility_readings ur
        JOIN utility_meters m ON m.id = ur.meter_id
        JOIN properties p ON p.id = m.property_id
        LEFT JOIN rooms r ON r.id = m.room_id
        JOIN users u ON u.id = ur.verified_by_user_id
    """
    params = []
    if property_id:
        sql += " WHERE p.id = %s"
        params.append(property_id)
    sql += " ORDER BY ur.created_at DESC, ur.id DESC"
    return query_db(sql, tuple(params))
