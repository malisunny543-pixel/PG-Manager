from decimal import Decimal
from flask import session
from app import create_app
from app.db import query_db
from app.services import authenticate_user, log_audit

def test_sql_injection_protection_in_auth(app):
    """Verify parameterized queries prevent SQL injection bypass in login."""
    sqli_payloads = [
        "' OR '1'='1",
        "admin@pgms.local' --",
        "' UNION SELECT 1, 'admin', 'hash', 'ADMIN' --",
        "admin@pgms.local'; DROP TABLE users; --"
    ]
    for payload in sqli_payloads:
        result = authenticate_user(payload, "password")
        assert result is None

    # Verify tables still intact
    users = query_db("SELECT COUNT(*) AS cnt FROM users", one=True)
    assert users['cnt'] > 0


def test_csrf_token_enforcement():
    """Verify CSRF token validation blocks requests missing valid token when CSRF enabled."""
    app = create_app('development')
    client = app.test_client()

    # Attempt POST without CSRF token
    res = client.post('/login', data={'email': 'admin@pgms.local', 'password': 'Admin@123'})
    assert res.status_code == 400
    assert b"Invalid or missing CSRF token" in res.data


def test_audit_log_omits_passwords_and_secrets(app):
    """Verify audit logger explicitly removes passwords and secrets before writing to database."""
    log_audit('TEST_SECURITY_ACTION', 'users', 1, {
        'username': 'admin',
        'password': 'RawPassword123!',
        'api_token': 'secret-token-xyz',
        'action_note': 'Password change request'
    }, actor_id=1)

    log_entry = query_db("SELECT * FROM audit_logs WHERE action = 'TEST_SECURITY_ACTION' ORDER BY id DESC LIMIT 1", one=True)
    assert log_entry is not None
    assert 'RawPassword123!' not in log_entry['details_json']
    assert 'secret-token-xyz' not in log_entry['details_json']
    assert 'Password change request' in log_entry['details_json']
