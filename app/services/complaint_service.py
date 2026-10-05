from app.db import query_db, execute_db, db_transaction
from app.services.audit_service import log_audit

def create_complaint(tenant_id, title, description, category='OTHER', priority='MEDIUM'):
    """Create a new tenant complaint linked to tenant's current property and room."""
    # Find active allocation to determine property and room
    alloc = query_db(
        """SELECT ta.id, b.room_id, r.property_id
           FROM tenant_allocations ta
           JOIN beds b ON b.id = ta.bed_id
           JOIN rooms r ON r.id = b.room_id
           WHERE ta.tenant_id = %s AND ta.status = 'ACTIVE'""",
        (tenant_id,), one=True
    )
    if not alloc:
        # If no active allocation, try finding recent property or fail gracefully
        recent = query_db(
            """SELECT r.property_id, b.room_id
               FROM tenant_allocations ta
               JOIN beds b ON b.id = ta.bed_id
               JOIN rooms r ON r.id = b.room_id
               WHERE ta.tenant_id = %s ORDER BY ta.id DESC LIMIT 1""",
            (tenant_id,), one=True
        )
        if not recent:
            raise ValueError("You must have a PG bed allocation to submit a maintenance complaint.")
        property_id = recent['property_id']
        room_id = recent['room_id']
    else:
        property_id = alloc['property_id']
        room_id = alloc['room_id']

    sql = """
        INSERT INTO complaints (tenant_id, property_id, room_id, title, description, category, priority, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'OPEN')
    """
    res = execute_db(sql, (
        tenant_id, property_id, room_id,
        title.strip(), description.strip(), category, priority
    ))
    complaint_id = res['lastrowid']
    log_audit('COMPLAINT_CREATED', 'complaints', complaint_id, {'title': title, 'category': category})
    return complaint_id


def get_complaints(property_id=None, tenant_id=None, status=None):
    """Retrieve complaints with tenant, room, and property details."""
    sql = """
        SELECT c.*,
               u.first_name AS tenant_first_name, u.last_name AS tenant_last_name, u.phone AS tenant_phone,
               r.room_number, p.name AS property_name, p.code AS property_code,
               u_assign.first_name AS assigned_first_name, u_assign.last_name AS assigned_last_name
        FROM complaints c
        JOIN tenants t ON t.id = c.tenant_id
        JOIN users u ON u.id = t.user_id
        JOIN properties p ON p.id = c.property_id
        LEFT JOIN rooms r ON r.id = c.room_id
        LEFT JOIN users u_assign ON u_assign.id = c.assigned_to_user_id
    """
    conditions = []
    params = []
    if property_id:
        conditions.append("c.property_id = %s")
        params.append(property_id)
    if tenant_id:
        conditions.append("c.tenant_id = %s")
        params.append(tenant_id)
    if status:
        conditions.append("c.status = %s")
        params.append(status)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY c.created_at DESC"
    return query_db(sql, tuple(params))


def get_complaint_by_id(complaint_id):
    """Fetch a single complaint by ID."""
    sql = """
        SELECT c.*,
               u.first_name AS tenant_first_name, u.last_name AS tenant_last_name, u.phone AS tenant_phone,
               r.room_number, p.name AS property_name, p.code AS property_code,
               u_assign.first_name AS assigned_first_name, u_assign.last_name AS assigned_last_name
        FROM complaints c
        JOIN tenants t ON t.id = c.tenant_id
        JOIN users u ON u.id = t.user_id
        JOIN properties p ON p.id = c.property_id
        LEFT JOIN rooms r ON r.id = c.room_id
        LEFT JOIN users u_assign ON u_assign.id = c.assigned_to_user_id
        WHERE c.id = %s
    """
    return query_db(sql, (complaint_id,), one=True)


def update_complaint_status(complaint_id, new_status, assigned_to_user_id=None, resolution_notes=None, actor_user_id=None):
    """Update complaint status and record resolution notes with notification."""
    valid_statuses = ('OPEN', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED')
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid complaint status: {new_status}")

    with db_transaction():
        # Fetch tenant user_id for notification
        comp = query_db(
            """SELECT c.id, c.title, t.user_id
               FROM complaints c
               JOIN tenants t ON t.id = c.tenant_id
               WHERE c.id = %s""",
            (complaint_id,), one=True
        )
        if not comp:
            raise ValueError("Complaint not found.")

        sql = """
            UPDATE complaints
            SET status = %s,
                assigned_to_user_id = COALESCE(%s, assigned_to_user_id),
                resolution_notes = COALESCE(%s, resolution_notes)
            WHERE id = %s
        """
        execute_db(sql, (new_status, assigned_to_user_id, resolution_notes, complaint_id), commit=False)

        # Notify tenant
        execute_db(
            """INSERT INTO notifications (user_id, title, message, category, is_read)
               VALUES (%s, %s, %s, 'COMPLAINT_UPDATE', 0)""",
            (comp['user_id'], 'Complaint Status Updated',
             f"Your complaint '{comp['title']}' status has been updated to {new_status}."),
            commit=False
        )

        log_audit('COMPLAINT_STATUS_UPDATED', 'complaints', complaint_id, {
            'status': new_status,
            'assigned_to': assigned_to_user_id
        }, actor_id=actor_user_id)

    return True
