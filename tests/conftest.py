import os
import pytest
import pymysql
import pymysql.cursors
from decimal import Decimal
from app import create_app
from app.db import get_pool, query_db, execute_db

@pytest.fixture(scope='session')
def setup_test_db():
    """Ensure pg_management_test exists and has schema applied."""
    config_host = os.environ.get('DB_HOST', 'localhost')
    config_port = int(os.environ.get('DB_PORT', 3306))
    config_user = os.environ.get('DB_USER', 'root')
    config_pass = os.environ.get('DB_PASSWORD', '@Roshan123')
    test_db_name = os.environ.get('DB_TEST_NAME', 'pg_management_test')

    # Connect to MySQL server to create test database
    root_conn = pymysql.connect(
        host=config_host,
        port=config_port,
        user=config_user,
        password=config_pass,
        charset='utf8mb4'
    )
    with root_conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{test_db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    root_conn.close()

    # Apply schema to test DB
    test_conn = pymysql.connect(
        host=config_host,
        port=config_port,
        user=config_user,
        password=config_pass,
        database=test_db_name,
        charset='utf8mb4'
    )
    with open('database/schema.sql', 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
    with test_conn.cursor() as cur:
        for stmt in statements:
            cur.execute(stmt)
    test_conn.commit()

    # Also load demo seed data
    with open('database/seed_demo.sql', 'r', encoding='utf-8') as f:
        seed_sql = f.read()
    seed_stmts = [stmt.strip() for stmt in seed_sql.split(';') if stmt.strip()]
    with test_conn.cursor() as cur:
        for stmt in seed_stmts:
            cur.execute(stmt)
    test_conn.commit()
    test_conn.close()

    yield test_db_name


@pytest.fixture
def app(setup_test_db):
    """Create Flask application configured for testing."""
    os.environ['DB_NAME'] = setup_test_db
    test_app = create_app('testing')
    test_app.config['DB_NAME'] = setup_test_db
    test_app.config['TESTING'] = True
    test_app.config['WTF_CSRF_ENABLED'] = False
    
    # Reset pool
    pool = get_pool(test_app)
    pool.database = setup_test_db

    with test_app.app_context():
        yield test_app


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def admin_client(app):
    """Client authenticated as ADMIN."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess['user'] = {
            'id': 1,
            'email': 'admin@pgms.local',
            'role': 'ADMIN',
            'first_name': 'Super',
            'last_name': 'Admin'
        }
        sess['_csrf_token'] = 'test-csrf-token'
    return c


@pytest.fixture
def manager_client(app):
    """Client authenticated as MANAGER for Property 1 (Koramangala)."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess['user'] = {
            'id': 2,
            'email': 'manager.koramangala@pgms.local',
            'role': 'MANAGER',
            'first_name': 'Suresh',
            'last_name': 'Kumar',
            'managed_property_ids': [1],
            'primary_property_id': 1
        }
        sess['_csrf_token'] = 'test-csrf-token'
    return c


@pytest.fixture
def tenant_client(app):
    """Client authenticated as TENANT (Rahul Sharma, Tenant ID 1)."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess['user'] = {
            'id': 4,
            'email': 'rahul.sharma@example.com',
            'role': 'TENANT',
            'first_name': 'Rahul',
            'last_name': 'Sharma',
            'tenant_id': 1
        }
        sess['_csrf_token'] = 'test-csrf-token'
    return c
