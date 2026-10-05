import pytest
from decimal import Decimal
from app.db import query_db, execute_db
from app.services import (
    record_payment, record_meter_reading, create_utility_meter,
    get_invoice_by_id
)

def test_decimal_precision_and_partial_payments(app):
    """Verify Decimal monetary precision and multi-installment partial payment tracking."""
    # Invoice 2 in seed data has:
    # rent: 8000, utility: 420 -> total: 8420.00
    # initial payment: 5000.00 -> balance: 3420.00, status: PARTIAL
    inv_before = get_invoice_by_id(2)
    assert isinstance(inv_before['total_amount'], Decimal)
    assert inv_before['total_amount'] == Decimal('8420.00')
    assert inv_before['paid_amount'] == Decimal('5000.00')
    assert inv_before['balance_due'] == Decimal('3420.00')
    assert inv_before['status'] == 'PARTIAL'

    # Make second partial payment of ₹2,000.00
    pay_id1 = record_payment(
        invoice_id=2,
        amount=Decimal('2000.00'),
        payment_method='CASH',
        transaction_reference='CASH-REC-101',
        recorded_by_user_id=1,
        notes='Second installment'
    )
    assert pay_id1 > 0

    inv_mid = get_invoice_by_id(2)
    assert inv_mid['paid_amount'] == Decimal('7000.00')
    assert inv_mid['balance_due'] == Decimal('1420.00')
    assert inv_mid['status'] == 'PARTIAL'

    # Attempting to pay ₹1,500.00 (more than balance ₹1,420.00) must raise ValueError
    with pytest.raises(ValueError, match="cannot exceed outstanding balance"):
        record_payment(
            invoice_id=2,
            amount=Decimal('1500.00'),
            payment_method='UPI',
            transaction_reference='UPI-OVERPAY',
            recorded_by_user_id=1
        )

    # Settle final balance of ₹1,420.00
    pay_id2 = record_payment(
        invoice_id=2,
        amount=Decimal('1420.00'),
        payment_method='UPI',
        transaction_reference='UPI-FINAL-SETTLE',
        recorded_by_user_id=1
    )
    assert pay_id2 > 0

    inv_final = get_invoice_by_id(2)
    assert inv_final['paid_amount'] == Decimal('8420.00')
    assert inv_final['balance_due'] == Decimal('0.00')
    assert inv_final['status'] == 'PAID'

    # Both payment transactions must exist in invoice history
    payments = inv_final['payments']
    assert len(payments) == 3  # Initial seed payment + 2 test payments


def test_utility_meter_reading_and_rate_calculation(app):
    """Verify metered consumption units and configurable rate per unit calculation."""
    # Create meter with custom rate ₹12.50 per unit
    m_id = create_utility_meter(
        property_id=1,
        room_id=1,
        meter_type='ELECTRICITY',
        meter_identifier='MTR-TEST-CUSTOM-01',
        rate_per_unit=Decimal('12.50')
    )
    assert m_id > 0

    # Initial reading 100.00
    rdg_id1 = record_meter_reading(
        meter_id=m_id,
        current_reading=Decimal('100.00'),
        start_date='2026-08-01',
        end_date='2026-08-31',
        verified_by_user_id=1
    )
    r1 = query_db("SELECT * FROM utility_readings WHERE id = %s", (rdg_id1,), one=True)
    assert r1['previous_reading'] == Decimal('0.00')
    assert r1['units_consumed'] == Decimal('100.00')
    assert r1['total_charge'] == Decimal('1250.00')  # 100 * 12.50

    # Next reading 160.50 (units consumed = 60.50)
    rdg_id2 = record_meter_reading(
        meter_id=m_id,
        current_reading=Decimal('160.50'),
        start_date='2026-09-01',
        end_date='2026-09-30',
        verified_by_user_id=1
    )
    r2 = query_db("SELECT * FROM utility_readings WHERE id = %s", (rdg_id2,), one=True)
    assert r2['previous_reading'] == Decimal('100.00')
    assert r2['units_consumed'] == Decimal('60.50')
    assert r2['total_charge'] == Decimal('756.25')  # 60.50 * 12.50
