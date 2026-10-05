from werkzeug.security import generate_password_hash, check_password_hash
from app.db import query_db, execute_db, db_transaction
from app.services.audit_service import log_audit

def authenticate_user(email, password):
    """Authenticate a user by email and password.
    Returns user dict with session context (role, tenant_id, managed_property_ids) or None.
    """
    sql = "SELECT id, email, password_hash, role, first_name, last_name, phone, is_active FROM users WHERE email = %s"
    user = query_db(sql, (email.strip().lower(),), one=True)
    if not user or not user['is_active']:
        return None

    if not check_password_hash(user['password_hash'], password):
        return None

    user_info = {
        'id': user['id'],
        'email': user['email'],
        'role': user['role'],
        'first_name': user['first_name'],
        'last_name': user['last_name'],
        'phone': user['phone']
    }

    # If tenant, fetch tenant_id
    if user['role'] == 'TENANT':
        t_row = query_db("SELECT id, status FROM tenants WHERE user_id = %s", (user['id'],), one=True)
        user_info['tenant_id'] = t_row['id'] if t_row else None
        user_info['tenant_status'] = t_row['status'] if t_row else None

    # If manager, fetch assigned property IDs
    elif user['role'] == 'MANAGER':
        m_rows = query_db("SELECT property_id FROM property_managers WHERE user_id = %s", (user['id'],))
        user_info['managed_property_ids'] = [r['property_id'] for r in m_rows]
        if user_info['managed_property_ids']:
            user_info['primary_property_id'] = user_info['managed_property_ids'][0]
        else:
            user_info['primary_property_id'] = None

    return user_info


def register_tenant(email, password, first_name, last_name, phone,
                    emergency_name, emergency_phone, id_proof_type, id_proof_number, permanent_address):
    """Public tenant self-registration.
    Strictly registers accounts as TENANT role.
    """
    clean_email = email.strip().lower()
    existing = query_db("SELECT id FROM users WHERE email = %s", (clean_email,), one=True)
    if existing:
        raise ValueError("An account with this email address already exists.")

    password_hash = generate_password_hash(password)

    with db_transaction():
        # 1. Insert User
        user_res = execute_db(
            """INSERT INTO users (email, password_hash, role, first_name, last_name, phone, is_active)
               VALUES (%s, %s, 'TENANT', %s, %s, %s, 1)""",
            (clean_email, password_hash, first_name.strip(), last_name.strip(), phone.strip()),
            commit=False
        )
        user_id = user_res['lastrowid']

        # 2. Insert Tenant Profile
        tenant_res = execute_db(
            """INSERT INTO tenants (user_id, emergency_contact_name, emergency_contact_phone,
                                   id_proof_type, id_proof_number, permanent_address, status)
               VALUES (%s, %s, %s, %s, %s, %s, 'INACTIVE')""",
            (user_id, emergency_name.strip(), emergency_phone.strip(),
             id_proof_type.strip(), id_proof_number.strip(), permanent_address.strip()),
            commit=False
        )
        tenant_id = tenant_res['lastrowid']

        log_audit('TENANT_REGISTERED', 'tenants', tenant_id, {'email': clean_email}, actor_id=user_id)

    return tenant_id


def change_user_password(user_id, current_password, new_password):
    """Update a user's password after verifying their current password."""
    user = query_db("SELECT password_hash FROM users WHERE id = %s", (user_id,), one=True)
    if not user or not check_password_hash(user['password_hash'], current_password):
        raise ValueError("Current password does not match.")

    new_hash = generate_password_hash(new_password)
    execute_db("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id))
    log_audit('PASSWORD_CHANGED', 'users', user_id, actor_id=user_id)
    return True
