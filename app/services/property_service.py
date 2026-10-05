from decimal import Decimal
from app.db import query_db, execute_db, db_transaction
from app.services.audit_service import log_audit

# --- Properties ---

def get_all_properties(active_only=False):
    """Retrieve all properties with room and bed statistics."""
    sql = """
        SELECT p.*,
               COUNT(DISTINCT r.id) AS total_rooms,
               COUNT(DISTINCT b.id) AS total_beds,
               SUM(CASE WHEN b.status = 'OCCUPIED' THEN 1 ELSE 0 END) AS occupied_beds,
               SUM(CASE WHEN b.status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_beds,
               SUM(CASE WHEN b.status = 'UNDER_MAINTENANCE' THEN 1 ELSE 0 END) AS maintenance_beds
        FROM properties p
        LEFT JOIN rooms r ON r.property_id = p.id AND r.is_active = 1
        LEFT JOIN beds b ON b.room_id = r.id
    """
    if active_only:
        sql += " WHERE p.is_active = 1"
    sql += " GROUP BY p.id ORDER BY p.name ASC"
    return query_db(sql)


def get_property_by_id(property_id):
    """Fetch a single property by ID."""
    return query_db("SELECT * FROM properties WHERE id = %s", (property_id,), one=True)


def create_property(name, code, address, city, state, pincode, contact_phone,
                    default_deposit_amount=Decimal('0.00'), default_utility_rate=Decimal('10.00')):
    """Create a new PG property."""
    sql = """
        INSERT INTO properties (name, code, address, city, state, pincode, contact_phone,
                                default_deposit_amount, default_utility_rate, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
    """
    res = execute_db(sql, (
        name.strip(), code.strip().upper(), address.strip(), city.strip(),
        state.strip(), pincode.strip(), contact_phone.strip(),
        Decimal(str(default_deposit_amount)), Decimal(str(default_utility_rate))
    ))
    prop_id = res['lastrowid']
    log_audit('PROPERTY_CREATED', 'properties', prop_id, {'name': name, 'code': code})
    return prop_id


def update_property(property_id, name, code, address, city, state, pincode, contact_phone,
                    default_deposit_amount, default_utility_rate, is_active=1):
    """Update an existing property."""
    sql = """
        UPDATE properties
        SET name = %s, code = %s, address = %s, city = %s, state = %s, pincode = %s,
            contact_phone = %s, default_deposit_amount = %s, default_utility_rate = %s, is_active = %s
        WHERE id = %s
    """
    execute_db(sql, (
        name.strip(), code.strip().upper(), address.strip(), city.strip(),
        state.strip(), pincode.strip(), contact_phone.strip(),
        Decimal(str(default_deposit_amount)), Decimal(str(default_utility_rate)),
        int(is_active), property_id
    ))
    log_audit('PROPERTY_UPDATED', 'properties', property_id, {'name': name, 'code': code})


def get_property_managers(property_id):
    """Get managers assigned to a property."""
    sql = """
        SELECT pm.id AS assignment_id, u.id AS user_id, u.first_name, u.last_name, u.email, u.phone, pm.assigned_at
        FROM property_managers pm
        JOIN users u ON u.id = pm.user_id
        WHERE pm.property_id = %s
        ORDER BY u.first_name ASC
    """
    return query_db(sql, (property_id,))


def assign_property_manager(property_id, user_id):
    """Assign a manager to a property."""
    user = query_db("SELECT role FROM users WHERE id = %s", (user_id,), one=True)
    if not user or user['role'] != 'MANAGER':
        raise ValueError("Selected user is not a manager.")
    sql = "INSERT IGNORE INTO property_managers (property_id, user_id) VALUES (%s, %s)"
    execute_db(sql, (property_id, user_id))
    log_audit('MANAGER_ASSIGNED', 'property_managers', property_id, {'user_id': user_id})


def remove_property_manager(property_id, user_id):
    """Remove a manager assignment from a property."""
    sql = "DELETE FROM property_managers WHERE property_id = %s AND user_id = %s"
    execute_db(sql, (property_id, user_id))
    log_audit('MANAGER_REMOVED', 'property_managers', property_id, {'user_id': user_id})


# --- Rooms ---

def get_rooms_by_property(property_id=None, active_only=False):
    """List rooms optionally filtered by property."""
    sql = """
        SELECT r.*, p.name AS property_name, p.code AS property_code,
               COUNT(b.id) AS total_beds,
               SUM(CASE WHEN b.status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_beds,
               SUM(CASE WHEN b.status = 'OCCUPIED' THEN 1 ELSE 0 END) AS occupied_beds,
               SUM(CASE WHEN b.status = 'UNDER_MAINTENANCE' THEN 1 ELSE 0 END) AS maintenance_beds
        FROM rooms r
        JOIN properties p ON p.id = r.property_id
        LEFT JOIN beds b ON b.room_id = r.id
    """
    params = []
    conditions = []
    if property_id:
        conditions.append("r.property_id = %s")
        params.append(property_id)
    if active_only:
        conditions.append("r.is_active = 1")
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " GROUP BY r.id ORDER BY p.name ASC, r.room_number ASC"
    return query_db(sql, tuple(params))


def get_room_by_id(room_id):
    """Retrieve single room with owning property."""
    sql = """
        SELECT r.*, p.name AS property_name, p.code AS property_code
        FROM rooms r
        JOIN properties p ON p.id = r.property_id
        WHERE r.id = %s
    """
    return query_db(sql, (room_id,), one=True)


def create_room(property_id, room_number, floor, room_type, base_rent, default_deposit=None):
    """Create a new room in a property."""
    deposit = Decimal(str(default_deposit)) if default_deposit else None
    sql = """
        INSERT INTO rooms (property_id, room_number, floor, room_type, base_rent, default_deposit, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, 1)
    """
    res = execute_db(sql, (
        property_id, room_number.strip(), int(floor), room_type,
        Decimal(str(base_rent)), deposit
    ))
    room_id = res['lastrowid']
    log_audit('ROOM_CREATED', 'rooms', room_id, {'room_number': room_number, 'property_id': property_id})
    return room_id


def update_room(room_id, room_number, floor, room_type, base_rent, default_deposit=None, is_active=1):
    """Update room details."""
    deposit = Decimal(str(default_deposit)) if default_deposit else None
    sql = """
        UPDATE rooms
        SET room_number = %s, floor = %s, room_type = %s, base_rent = %s,
            default_deposit = %s, is_active = %s
        WHERE id = %s
    """
    execute_db(sql, (
        room_number.strip(), int(floor), room_type, Decimal(str(base_rent)),
        deposit, int(is_active), room_id
    ))
    log_audit('ROOM_UPDATED', 'rooms', room_id, {'room_number': room_number})


# --- Beds ---

def get_beds(property_id=None, room_id=None, status=None):
    """Retrieve beds with room and property context."""
    sql = """
        SELECT b.*, r.room_number, r.room_type, r.base_rent,
               p.id AS property_id, p.name AS property_name, p.code AS property_code,
               ta.id AS current_allocation_id, u.first_name AS tenant_first_name, u.last_name AS tenant_last_name
        FROM beds b
        JOIN rooms r ON r.id = b.room_id
        JOIN properties p ON p.id = r.property_id
        LEFT JOIN tenant_allocations ta ON ta.bed_id = b.id AND ta.status = 'ACTIVE'
        LEFT JOIN tenants t ON t.id = ta.tenant_id
        LEFT JOIN users u ON u.id = t.user_id
    """
    conditions = []
    params = []
    if property_id:
        conditions.append("p.id = %s")
        params.append(property_id)
    if room_id:
        conditions.append("r.id = %s")
        params.append(room_id)
    if status:
        conditions.append("b.status = %s")
        params.append(status)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY p.name ASC, r.room_number ASC, b.bed_number ASC"
    return query_db(sql, tuple(params))


def create_bed(room_id, bed_number):
    """Add a bed to a room."""
    sql = "INSERT INTO beds (room_id, bed_number, status) VALUES (%s, %s, 'AVAILABLE')"
    res = execute_db(sql, (room_id, bed_number.strip().upper()))
    bed_id = res['lastrowid']
    log_audit('BED_CREATED', 'beds', bed_id, {'bed_number': bed_number, 'room_id': room_id})
    return bed_id
