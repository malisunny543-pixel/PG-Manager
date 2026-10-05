from decimal import Decimal
from app.db import query_db

def get_admin_dashboard_stats():
    """Retrieve operational KPIs for the Admin Dashboard."""
    props_cnt = query_db("SELECT COUNT(*) AS cnt FROM properties WHERE is_active = 1", one=True)['cnt']
    rooms_cnt = query_db("SELECT COUNT(*) AS cnt FROM rooms WHERE is_active = 1", one=True)['cnt']
    
    bed_stats = query_db("""
        SELECT COUNT(*) AS total_beds,
               SUM(CASE WHEN status = 'OCCUPIED' THEN 1 ELSE 0 END) AS occupied_beds,
               SUM(CASE WHEN status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_beds,
               SUM(CASE WHEN status = 'UNDER_MAINTENANCE' THEN 1 ELSE 0 END) AS maintenance_beds
        FROM beds
    """, one=True)

    total_b = bed_stats['total_beds'] or 0
    occ_b = bed_stats['occupied_beds'] or 0
    avail_b = bed_stats['available_beds'] or 0
    maint_b = bed_stats['maintenance_beds'] or 0

    occ_rate = f"{(occ_b / total_b * 100):.1f}%" if total_b > 0 else "0.0%"

    overdue_row = query_db("""
        SELECT SUM(balance_due) AS total_overdue
        FROM invoices
        WHERE status IN ('UNPAID', 'PARTIAL', 'OVERDUE') AND due_date < CURRENT_DATE
    """, one=True)
    overdue_rent = overdue_row['total_overdue'] if overdue_row and overdue_row['total_overdue'] else Decimal('0.00')

    complaints_cnt = query_db("SELECT COUNT(*) AS cnt FROM complaints WHERE status IN ('OPEN', 'IN_PROGRESS', 'ASSIGNED')", one=True)['cnt']

    return {
        'total_properties': props_cnt,
        'total_rooms': rooms_cnt,
        'total_beds': total_b,
        'occupied_beds': occ_b,
        'available_beds': avail_b,
        'maintenance_beds': maint_b,
        'occupancy_rate': occ_rate,
        'overdue_rent': overdue_rent,
        'open_complaints': complaints_cnt
    }


def get_manager_dashboard_stats(property_ids):
    """Retrieve operational KPIs for a Manager scoped to assigned properties."""
    if not property_ids:
        return {
            'property_name': 'No assigned property',
            'property_code': '-',
            'total_beds': 0,
            'occupied_beds': 0,
            'available_beds': 0,
            'maintenance_beds': 0,
            'active_tenants': 0,
            'open_complaints': 0
        }

    prop = query_db("SELECT name, code FROM properties WHERE id = %s", (property_ids[0],), one=True)

    placeholders = ', '.join(['%s'] * len(property_ids))
    bed_stats = query_db(f"""
        SELECT COUNT(b.id) AS total_beds,
               SUM(CASE WHEN b.status = 'OCCUPIED' THEN 1 ELSE 0 END) AS occupied_beds,
               SUM(CASE WHEN b.status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_beds,
               SUM(CASE WHEN b.status = 'UNDER_MAINTENANCE' THEN 1 ELSE 0 END) AS maintenance_beds
        FROM beds b
        JOIN rooms r ON r.id = b.room_id
        WHERE r.property_id IN ({placeholders})
    """, tuple(property_ids), one=True)

    tenants_cnt = query_db(f"""
        SELECT COUNT(DISTINCT ta.tenant_id) AS cnt
        FROM tenant_allocations ta
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        WHERE r.property_id IN ({placeholders}) AND ta.status = 'ACTIVE'
    """, tuple(property_ids), one=True)['cnt']

    comp_cnt = query_db(f"""
        SELECT COUNT(*) AS cnt
        FROM complaints
        WHERE property_id IN ({placeholders}) AND status IN ('OPEN', 'ASSIGNED', 'IN_PROGRESS')
    """, tuple(property_ids), one=True)['cnt']

    return {
        'property_name': prop['name'] if prop else 'Assigned PG',
        'property_code': prop['code'] if prop else '',
        'total_beds': bed_stats['total_beds'] or 0,
        'occupied_beds': bed_stats['occupied_beds'] or 0,
        'available_beds': bed_stats['available_beds'] or 0,
        'maintenance_beds': bed_stats['maintenance_beds'] or 0,
        'active_tenants': tenants_cnt,
        'open_complaints': comp_cnt
    }


def get_occupancy_report(property_id=None):
    """Detailed occupancy report grouped by property and room type."""
    sql = """
        SELECT p.name AS property_name, p.code AS property_code,
               r.room_number, r.room_type, r.base_rent,
               COUNT(b.id) AS total_beds,
               SUM(CASE WHEN b.status = 'OCCUPIED' THEN 1 ELSE 0 END) AS occupied_count,
               SUM(CASE WHEN b.status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_count,
               SUM(CASE WHEN b.status = 'UNDER_MAINTENANCE' THEN 1 ELSE 0 END) AS maintenance_count
        FROM rooms r
        JOIN properties p ON p.id = r.property_id
        LEFT JOIN beds b ON b.room_id = r.id
    """
    params = []
    if property_id:
        sql += " WHERE p.id = %s"
        params.append(property_id)
    sql += " GROUP BY r.id ORDER BY p.name ASC, r.room_number ASC"
    return query_db(sql, tuple(params))


def get_revenue_report(billing_month=None):
    """Revenue collection report by property and billing month."""
    sql = """
        SELECT p.name AS property_name, p.code AS property_code,
               inv.billing_month,
               COUNT(inv.id) AS invoice_count,
               SUM(inv.total_amount) AS total_billed,
               SUM(inv.paid_amount) AS total_collected,
               SUM(inv.balance_due) AS total_outstanding
        FROM invoices inv
        JOIN tenant_allocations ta ON ta.id = inv.allocation_id
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
    """
    params = []
    if billing_month:
        sql += " WHERE inv.billing_month = %s"
        params.append(billing_month)
    sql += " GROUP BY p.id, inv.billing_month ORDER BY inv.billing_month DESC, p.name ASC"
    return query_db(sql, tuple(params))


def get_defaulters_report(property_id=None):
    """Report of tenants with overdue or unpaid rent balances."""
    sql = """
        SELECT u.first_name, u.last_name, u.email, u.phone,
               p.name AS property_name, r.room_number, b.bed_number,
               inv.id AS invoice_id, inv.invoice_number, inv.billing_month,
               inv.due_date, inv.total_amount, inv.paid_amount, inv.balance_due, inv.status
        FROM invoices inv
        JOIN tenant_allocations ta ON ta.id = inv.allocation_id
        JOIN beds b ON b.id = ta.bed_id
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        JOIN tenants t ON t.id = ta.tenant_id
        JOIN users u ON u.id = t.user_id
        WHERE inv.balance_due > 0
    """
    params = []
    if property_id:
        sql += " AND p.id = %s"
        params.append(property_id)
    sql += " ORDER BY inv.due_date ASC, inv.balance_due DESC"
    return query_db(sql, tuple(params))


def get_audit_logs(limit=100):
    """Retrieve audit log records with user actor context."""
    sql = """
        SELECT al.*, u.email AS actor_email, u.first_name AS actor_first, u.last_name AS actor_last, u.role AS actor_role
        FROM audit_logs al
        LEFT JOIN users u ON u.id = al.actor_user_id
        ORDER BY al.created_at DESC
        LIMIT %s
    """
    return query_db(sql, (limit,))
