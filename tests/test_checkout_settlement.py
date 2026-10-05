from decimal import Decimal
from app.db import query_db
from app.services import (
    register_tenant, allocate_bed_check_in,
    record_checkout_inspection, finalize_checkout_settlement
)

def test_checkout_settlement_workflow_and_deductions(app):
    """Verify inspection, itemized deductions calculation, settlement approval, and history retention."""
    # 1. Register tenant
    t_id = register_tenant(
        'checkout.test@example.com', 'Pass@123', 'Vikram', 'Singh', '9833333333',
        'Contact', '9833333334', 'Passport', 'V998877', 'Jaipur, Rajasthan'
    )

    # 2. Check-in to Bed 5 (201-B, rent 7500, deposit 7500)
    alloc_id = allocate_bed_check_in(
        tenant_id=t_id,
        bed_id=5,
        check_in_date='2026-08-01',
        expected_checkout_date='2026-10-01',
        monthly_rent=Decimal('7500.00'),
        security_deposit_amount=Decimal('7500.00'),
        actor_user_id=1
    )

    # 3. Record checkout inspection with itemized deductions
    deductions = [
        {'category': 'CLEANING', 'amount': Decimal('600.00'), 'reason': 'Deep cleaning charges'},
        {'category': 'DAMAGE', 'amount': Decimal('400.00'), 'reason': 'Damaged curtain rod replacement'}
    ]
    record_checkout_inspection(alloc_id, deductions, settlement_notes="Inspection complete, 2 items deducted.")

    # Verify calculation: 7500 - 1000 = 6500 refund
    dep = query_db("SELECT * FROM security_deposits WHERE allocation_id = %s", (alloc_id,), one=True)
    assert dep['total_deposit_received'] == Decimal('7500.00')
    assert dep['deductions_amount'] == Decimal('1000.00')
    assert dep['refund_amount'] == Decimal('6500.00')
    assert dep['recovery_amount'] == Decimal('0.00')
    assert dep['settlement_status'] == 'PENDING_APPROVAL'

    # 4. Finalize settlement
    finalize_checkout_settlement(alloc_id, actual_checkout_date='2026-10-02', authorizer_user_id=1)

    # Verify post-settlement state
    dep_after = query_db("SELECT * FROM security_deposits WHERE allocation_id = %s", (alloc_id,), one=True)
    assert dep_after['settlement_status'] == 'SETTLED'
    assert dep_after['authorized_by_user_id'] == 1

    alloc_after = query_db("SELECT * FROM tenant_allocations WHERE id = %s", (alloc_id,), one=True)
    assert alloc_after['status'] == 'CHECKED_OUT'
    assert str(alloc_after['actual_checkout_date']) == '2026-10-02'

    # Vacated bed must be UNDER_MAINTENANCE
    bed = query_db("SELECT status FROM beds WHERE id = 5", one=True)
    assert bed['status'] == 'UNDER_MAINTENANCE'

    # 5. Historical retention: Tenant profile still exists with CHECKED_OUT status
    tenant = query_db("SELECT * FROM tenants WHERE id = %s", (t_id,), one=True)
    assert tenant is not None
    assert tenant['status'] == 'CHECKED_OUT'
