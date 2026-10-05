from decimal import Decimal
from datetime import date, datetime
from app.db import query_db, execute_db, db_transaction
from app.services.audit_service import log_audit

def get_available_beds(property_id=None):
    """Retrieve all currently AVAILABLE beds for check-in."""
    sql = """
        SELECT b.id AS bed_id, b.bed_number, r.id AS room_id, r.room_number, r.room_type, r.base_rent,
               COALESCE(r.default_deposit, p.default_deposit_amount) AS suggested_deposit,
               p.id AS property_id, p.name AS property_name, p.code AS property_code
        FROM beds b
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        WHERE b.status = 'AVAILABLE' AND r.is_active = 1 AND p.is_active = 1
    """
    params = []
    if property_id:
        sql += " AND p.id = %s"
        params.append(property_id)
    sql += " ORDER BY p.name ASC, r.room_number ASC, b.bed_number ASC"
    return query_db(sql, tuple(params))


def allocate_bed_check_in(tenant_id, bed_id, check_in_date, expected_checkout_date,
                          monthly_rent, security_deposit_amount, actor_user_id=None):
    """Execute tenant check-in using explicit row-level locking (SELECT ... FOR UPDATE).
    Guarantees no race condition / double allocation can occur.
    """
    m_rent = Decimal(str(monthly_rent))
    s_deposit = Decimal(str(security_deposit_amount))

    with db_transaction() as conn:
        with conn.cursor() as cur:
            # 1. Acquire exclusive lock on target bed record
            cur.execute("SELECT id, room_id, status FROM beds WHERE id = %s FOR UPDATE", (bed_id,))
            bed = cur.fetchone()

            if not bed:
                raise ValueError("Specified bed not found.")

            if bed['status'] != 'AVAILABLE':
                raise ValueError(f"Bed is not available for allocation (current status: {bed['status']}).")

            # 2. Check if tenant already has an active allocation
            cur.execute(
                "SELECT id FROM tenant_allocations WHERE tenant_id = %s AND status = 'ACTIVE' FOR UPDATE",
                (tenant_id,)
            )
            existing_active = cur.fetchone()
            if existing_active:
                raise ValueError("Tenant already has an active bed allocation.")

            # 3. Transition bed to OCCUPIED
            cur.execute("UPDATE beds SET status = 'OCCUPIED' WHERE id = %s", (bed_id,))

            # 4. Insert active tenant allocation
            cur.execute(
                """INSERT INTO tenant_allocations
                   (tenant_id, bed_id, check_in_date, expected_checkout_date, monthly_rent, security_deposit_amount, status)
                   VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVE')""",
                (tenant_id, bed_id, check_in_date, expected_checkout_date or None, m_rent, s_deposit)
            )
            allocation_id = cur.lastrowid

            # 5. Create Security Deposit Ledger Entry
            cur.execute(
                """INSERT INTO security_deposits
                   (allocation_id, tenant_id, total_deposit_received, deductions_amount, refund_amount, recovery_amount, settlement_status)
                   VALUES (%s, %s, %s, 0.00, 0.00, 0.00, 'HELD')""",
                (allocation_id, tenant_id, s_deposit)
            )

            # 6. Update tenant status to ACTIVE
            cur.execute("UPDATE tenants SET status = 'ACTIVE' WHERE id = %s", (tenant_id,))

            # 7. Audit log
            log_audit('BED_ALLOCATED_CHECKIN', 'tenant_allocations', allocation_id, {
                'tenant_id': tenant_id,
                'bed_id': bed_id,
                'monthly_rent': str(m_rent),
                'deposit': str(s_deposit)
            }, actor_id=actor_user_id)

    return allocation_id


def transfer_room_bed(allocation_id, new_bed_id, transfer_date, actor_user_id=None):
    """Transfer an active tenant to a new bed.
    Vacated bed enters UNDER_MAINTENANCE.
    Target bed becomes OCCUPIED.
    """
    with db_transaction() as conn:
        with conn.cursor() as cur:
            # 1. Lock current allocation
            cur.execute(
                "SELECT id, tenant_id, bed_id, monthly_rent, status FROM tenant_allocations WHERE id = %s FOR UPDATE",
                (allocation_id,)
            )
            alloc = cur.fetchone()
            if not alloc or alloc['status'] != 'ACTIVE':
                raise ValueError("Active allocation required for transfer.")

            old_bed_id = alloc['bed_id']

            # 2. Lock target bed
            cur.execute("SELECT id, status FROM beds WHERE id = %s FOR UPDATE", (new_bed_id,))
            target_bed = cur.fetchone()
            if not target_bed or target_bed['status'] != 'AVAILABLE':
                raise ValueError("Target bed is not available.")

            # 3. Update old bed to UNDER_MAINTENANCE
            cur.execute("UPDATE beds SET status = 'UNDER_MAINTENANCE' WHERE id = %s", (old_bed_id,))

            # 4. Update new bed to OCCUPIED
            cur.execute("UPDATE beds SET status = 'OCCUPIED' WHERE id = %s", (new_bed_id,))

            # 5. Mark old allocation as TRANSFERRED
            cur.execute("UPDATE tenant_allocations SET status = 'TRANSFERRED' WHERE id = %s", (allocation_id,))

            # 6. Create new allocation
            cur.execute(
                """INSERT INTO tenant_allocations
                   (tenant_id, bed_id, check_in_date, monthly_rent, security_deposit_amount, status)
                   VALUES (%s, %s, %s, %s, 0.00, 'ACTIVE')""",
                (alloc['tenant_id'], new_bed_id, transfer_date, alloc['monthly_rent'])
            )
            new_alloc_id = cur.lastrowid

            log_audit('ROOM_TRANSFERRED', 'tenant_allocations', new_alloc_id, {
                'old_bed_id': old_bed_id,
                'new_bed_id': new_bed_id,
                'transfer_date': str(transfer_date)
            }, actor_id=actor_user_id)

    return new_alloc_id


def record_checkout_inspection(allocation_id, deductions_list, settlement_notes=None):
    """Record checkout inspection and itemized deductions.
    deductions_list: list of dicts [{'category': 'CLEANING', 'amount': 500, 'reason': 'Deep cleaning'}]
    """
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, total_deposit_received, settlement_status FROM security_deposits WHERE allocation_id = %s FOR UPDATE",
                (allocation_id,)
            )
            deposit = cur.fetchone()
            if not deposit:
                raise ValueError("No deposit record found for this allocation.")

            deposit_id = deposit['id']
            total_received = deposit['total_deposit_received']

            # Clear previous deductions if re-inspecting
            cur.execute("DELETE FROM deposit_deductions WHERE deposit_id = %s", (deposit_id,))

            total_deductions = Decimal('0.00')
            for item in deductions_list:
                amt = Decimal(str(item['amount']))
                if amt > 0:
                    cur.execute(
                        "INSERT INTO deposit_deductions (deposit_id, category, amount, reason) VALUES (%s, %s, %s, %s)",
                        (deposit_id, item['category'], amt, item['reason'])
                    )
                    total_deductions += amt

            # Compute settlement figures
            if total_received >= total_deductions:
                refund_amt = total_received - total_deductions
                recovery_amt = Decimal('0.00')
            else:
                refund_amt = Decimal('0.00')
                recovery_amt = total_deductions - total_received

            cur.execute(
                """UPDATE security_deposits
                   SET deductions_amount = %s, refund_amount = %s, recovery_amount = %s,
                       settlement_notes = %s, settlement_status = 'PENDING_APPROVAL'
                   WHERE id = %s""",
                (total_deductions, refund_amt, recovery_amt, settlement_notes, deposit_id)
            )

            log_audit('CHECKOUT_INSPECTION_RECORDED', 'security_deposits', deposit_id, {
                'allocation_id': allocation_id,
                'total_deductions': str(total_deductions),
                'refund': str(refund_amt),
                'recovery': str(recovery_amt)
            })

    return True


def finalize_checkout_settlement(allocation_id, actual_checkout_date, authorizer_user_id):
    """Finalize checkout settlement:
    1. Authorize deposit settlement (SETTLED).
    2. Mark allocation CHECKED_OUT.
    3. Vacated bed enters UNDER_MAINTENANCE (never immediately AVAILABLE).
    4. Tenant profile marked CHECKED_OUT.
    """
    with db_transaction() as conn:
        with conn.cursor() as cur:
            # Lock allocation
            cur.execute(
                "SELECT id, tenant_id, bed_id, status FROM tenant_allocations WHERE id = %s FOR UPDATE",
                (allocation_id,)
            )
            alloc = cur.fetchone()
            if not alloc or alloc['status'] != 'ACTIVE':
                raise ValueError("Valid active allocation required for checkout.")

            # Lock deposit
            cur.execute(
                "SELECT id, settlement_status FROM security_deposits WHERE allocation_id = %s FOR UPDATE",
                (allocation_id,)
            )
            deposit = cur.fetchone()
            if not deposit:
                raise ValueError("Security deposit record not found.")

            # 1. Update deposit status
            cur.execute(
                """UPDATE security_deposits
                   SET settlement_status = 'SETTLED', settled_at = CURRENT_TIMESTAMP,
                       authorized_by_user_id = %s
                   WHERE id = %s""",
                (authorizer_user_id, deposit['id'])
            )

            # 2. Mark allocation as CHECKED_OUT
            cur.execute(
                "UPDATE tenant_allocations SET status = 'CHECKED_OUT', actual_checkout_date = %s WHERE id = %s",
                (actual_checkout_date, allocation_id)
            )

            # 3. Vacated bed enters UNDER_MAINTENANCE
            cur.execute("UPDATE beds SET status = 'UNDER_MAINTENANCE' WHERE id = %s", (alloc['bed_id'],))

            # 4. Check if tenant has any other active allocations; if not, mark tenant CHECKED_OUT
            cur.execute(
                "SELECT COUNT(*) AS active_cnt FROM tenant_allocations WHERE tenant_id = %s AND status = 'ACTIVE'",
                (alloc['tenant_id'],)
            )
            remaining = cur.fetchone()['active_cnt']
            if remaining == 0:
                cur.execute("UPDATE tenants SET status = 'CHECKED_OUT' WHERE id = %s", (alloc['tenant_id'],))

            log_audit('CHECKOUT_SETTLED', 'tenant_allocations', allocation_id, {
                'bed_id': alloc['bed_id'],
                'checkout_date': str(actual_checkout_date)
            }, actor_id=authorizer_user_id)

    return True


def approve_bed_maintenance(bed_id, approver_user_id):
    """Transition bed from UNDER_MAINTENANCE back to AVAILABLE after cleaning and inspection."""
    with db_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, status FROM beds WHERE id = %s FOR UPDATE", (bed_id,))
            bed = cur.fetchone()
            if not bed:
                raise ValueError("Bed not found.")
            if bed['status'] != 'UNDER_MAINTENANCE':
                raise ValueError(f"Bed is not under maintenance (status: {bed['status']}).")

            cur.execute("UPDATE beds SET status = 'AVAILABLE' WHERE id = %s", (bed_id,))
            log_audit('BED_MAINTENANCE_APPROVED', 'beds', bed_id, {'status': 'AVAILABLE'}, actor_id=approver_user_id)

    return True
