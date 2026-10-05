import pytest
import threading
from decimal import Decimal
from app.db import query_db, execute_db
from app.services import (
    allocate_bed_check_in, approve_bed_maintenance,
    register_tenant, finalize_checkout_settlement, transfer_room_bed
)

def test_bed_lifecycle_and_allocation_integrity(app):
    """Verify bed lifecycle state machine:
       AVAILABLE -> OCCUPIED -> UNDER_MAINTENANCE -> AVAILABLE.
    """
    t1_id = register_tenant(
        'lifecycle.tenant1@example.com', 'Pass@123', 'Life', 'One', '9811111111',
        'Contact', '9811111112', 'Aadhaar', 'ID-1001', 'Address 1'
    )
    t2_id = register_tenant(
        'lifecycle.tenant2@example.com', 'Pass@123', 'Life', 'Two', '9822222222',
        'Contact', '9822222223', 'Aadhaar', 'ID-1002', 'Address 2'
    )

    bed = query_db("SELECT status FROM beds WHERE id = 2", one=True)
    assert bed['status'] == 'AVAILABLE'

    # Check-in tenant 1 to Bed 2
    alloc_id = allocate_bed_check_in(
        tenant_id=t1_id,
        bed_id=2,
        check_in_date='2026-10-01',
        expected_checkout_date='2027-09-30',
        monthly_rent=Decimal('8000.00'),
        security_deposit_amount=Decimal('8000.00'),
        actor_user_id=1
    )
    assert alloc_id > 0

    bed_after = query_db("SELECT status FROM beds WHERE id = 2", one=True)
    assert bed_after['status'] == 'OCCUPIED'

    # Attempting to allocate OCCUPIED bed to tenant 2 must FAIL
    with pytest.raises(ValueError, match="not available"):
        allocate_bed_check_in(
            tenant_id=t2_id,
            bed_id=2,
            check_in_date='2026-10-05',
            expected_checkout_date=None,
            monthly_rent=Decimal('8000.00'),
            security_deposit_amount=Decimal('8000.00'),
            actor_user_id=1
        )

    # Checkout tenant 1
    finalize_checkout_settlement(alloc_id, actual_checkout_date='2026-10-05', authorizer_user_id=1)

    # Bed must NOT become AVAILABLE immediately; it must be UNDER_MAINTENANCE
    bed_vacated = query_db("SELECT status FROM beds WHERE id = 2", one=True)
    assert bed_vacated['status'] == 'UNDER_MAINTENANCE'

    # Attempting to allocate UNDER_MAINTENANCE bed must FAIL
    with pytest.raises(ValueError, match="not available"):
        allocate_bed_check_in(
            tenant_id=t2_id,
            bed_id=2,
            check_in_date='2026-10-05',
            expected_checkout_date=None,
            monthly_rent=Decimal('8000.00'),
            security_deposit_amount=Decimal('8000.00'),
            actor_user_id=1
        )

    # Authorized staff approves cleaning
    approve_bed_maintenance(2, approver_user_id=1)

    # Bed is now safely AVAILABLE again
    bed_approved = query_db("SELECT status FROM beds WHERE id = 2", one=True)
    assert bed_approved['status'] == 'AVAILABLE'

    # Now tenant 2 can successfully check in to Bed 2
    alloc2_id = allocate_bed_check_in(
        tenant_id=t2_id,
        bed_id=2,
        check_in_date='2026-10-06',
        expected_checkout_date=None,
        monthly_rent=Decimal('8000.00'),
        security_deposit_amount=Decimal('8000.00'),
        actor_user_id=1
    )
    assert alloc2_id > 0
    bed_final = query_db("SELECT status FROM beds WHERE id = 2", one=True)
    assert bed_final['status'] == 'OCCUPIED'


def test_room_transfer_bed_lifecycle(app):
    """Verify room transfer: old bed becomes UNDER_MAINTENANCE, new bed becomes OCCUPIED."""
    # Tenant 1 (Rahul) is currently in Bed 1 (Room 101)
    alloc = query_db("SELECT id FROM tenant_allocations WHERE tenant_id = 1 AND status = 'ACTIVE'", one=True)
    assert alloc is not None

    # Bed 6 (202-A) is AVAILABLE
    target_bed = query_db("SELECT id, status FROM beds WHERE id = 6", one=True)
    assert target_bed['status'] == 'AVAILABLE'

    # Transfer Rahul to Bed 6
    new_alloc_id = transfer_room_bed(alloc['id'], new_bed_id=6, transfer_date='2026-10-15', actor_user_id=1)
    assert new_alloc_id > 0

    # Old bed 1 must be UNDER_MAINTENANCE
    old_bed = query_db("SELECT status FROM beds WHERE id = 1", one=True)
    assert old_bed['status'] == 'UNDER_MAINTENANCE'

    # Target bed 6 must be OCCUPIED
    new_bed = query_db("SELECT status FROM beds WHERE id = 6", one=True)
    assert new_bed['status'] == 'OCCUPIED'


def test_concurrent_allocation_row_locking(app):
    """Verify that simulated concurrent allocation requests for the same bed:
       Exactly one succeeds, and the other is safely rejected.
    """
    t_a = register_tenant(
        'concurrent.a@example.com', 'Pass@123', 'Conc', 'A', '9844444441',
        'Contact', '9844444442', 'Aadhaar', 'ID-C1', 'City'
    )
    t_b = register_tenant(
        'concurrent.b@example.com', 'Pass@123', 'Conc', 'B', '9844444443',
        'Contact', '9844444444', 'Aadhaar', 'ID-C2', 'City'
    )

    # Bed 7 (202-B) is currently AVAILABLE
    assert query_db("SELECT status FROM beds WHERE id = 7", one=True)['status'] == 'AVAILABLE'

    results = []
    errors = []

    def try_allocate(tenant_id):
        try:
            with app.app_context():
                a_id = allocate_bed_check_in(
                    tenant_id=tenant_id,
                    bed_id=7,
                    check_in_date='2026-10-10',
                    expected_checkout_date=None,
                    monthly_rent=Decimal('6000.00'),
                    security_deposit_amount=Decimal('6000.00'),
                    actor_user_id=1
                )
                results.append((tenant_id, a_id))
        except Exception as e:
            errors.append((tenant_id, str(e)))

    thread1 = threading.Thread(target=try_allocate, args=(t_a,))
    thread2 = threading.Thread(target=try_allocate, args=(t_b,))

    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()

    # Exactly one allocation succeeds, and one fails
    assert len(results) == 1
    assert len(errors) == 1
    assert "not available" in errors[0][1]
