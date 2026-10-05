import json
from flask import has_request_context, request, session
from app.db import execute_db

def log_audit(action, target_type, target_id, details=None, actor_id=None):
    """Record an administrative action into audit_logs table.
    Ensures zero sensitive credentials or passwords are logged.
    Safely operates within or outside active HTTP request context.
    """
    ip_address = None
    if has_request_context():
        if actor_id is None and 'user' in session:
            actor_id = session['user'].get('id')
        ip_address = request.remote_addr

    details_json = None
    if details:
        sanitized = {k: v for k, v in details.items() if 'password' not in k.lower() and 'token' not in k.lower()}
        details_json = json.dumps(sanitized)

    sql = """
        INSERT INTO audit_logs (actor_user_id, action, target_entity_type, target_entity_id, details_json, ip_address)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    return execute_db(sql, (actor_id, action, target_type, str(target_id), details_json, ip_address))
