from decimal import Decimal
from app.services import authenticate_user, register_tenant

def test_password_hashing_and_auth(app):
    """Verify password hashing and authentication with valid and invalid credentials."""
    # Valid admin login
    admin = authenticate_user('admin@pgms.local', 'Admin@123')
    assert admin is not None
    assert admin['role'] == 'ADMIN'
    assert admin['email'] == 'admin@pgms.local'

    # Valid tenant login
    tenant = authenticate_user('rahul.sharma@example.com', 'Tenant@123')
    assert tenant is not None
    assert tenant['role'] == 'TENANT'
    assert tenant['tenant_id'] == 1

    # Invalid password
    bad_login = authenticate_user('admin@pgms.local', 'WrongPassword!')
    assert bad_login is None

    # Non-existent user
    non_existent = authenticate_user('ghost@example.com', 'AnyPass123')
    assert non_existent is None


def test_public_tenant_registration_restricts_role(app):
    """Verify public registration always forces TENANT role and prevents privilege escalation."""
    t_id = register_tenant(
        email='new.test.tenant@example.com',
        password='Password@123',
        first_name='Ananya',
        last_name='Iyer',
        phone='9876599999',
        emergency_name='Sanjay Iyer',
        emergency_phone='9876588888',
        id_proof_type='Aadhaar',
        id_proof_number='9999-8888-7777',
        permanent_address='Chennai, Tamil Nadu'
    )
    assert t_id > 0

    user = authenticate_user('new.test.tenant@example.com', 'Password@123')
    assert user is not None
    assert user['role'] == 'TENANT'


def test_unauthenticated_access_redirects(client):
    """Unauthenticated requests to protected endpoints must redirect to login."""
    res_admin = client.get('/admin/dashboard')
    assert res_admin.status_code == 302
    assert '/login' in res_admin.location

    res_manager = client.get('/manager/dashboard')
    assert res_manager.status_code == 302
    assert '/login' in res_manager.location

    res_tenant = client.get('/tenant/dashboard')
    assert res_tenant.status_code == 302
    assert '/login' in res_tenant.location


def test_rbac_admin_routes_block_non_admins(manager_client, tenant_client):
    """Managers and Tenants must be strictly blocked (403) from Admin routes."""
    res_m = manager_client.get('/admin/dashboard')
    assert res_m.status_code == 403

    res_t = tenant_client.get('/admin/dashboard')
    assert res_t.status_code == 403


def test_rbac_manager_routes_block_tenants(tenant_client):
    """Tenants must be blocked (403) from Manager operational routes."""
    res = tenant_client.get('/manager/dashboard')
    assert res.status_code == 403


def test_manager_property_isolation(manager_client):
    """Manager 1 (assigned to Property 1) must be forbidden (403) from editing rooms in Property 2."""
    # Room 3 belongs to Property 2 (Silver Oak Indiranagar)
    res = manager_client.get('/manager/rooms/3/edit')
    assert res.status_code == 403


def test_tenant_self_isolation(tenant_client):
    """Tenant 1 (Rahul) must be blocked (403) from viewing Tenant 2's invoices and complaints."""
    # Invoice 3 belongs to Tenant 2 (Priya Verma)
    res_inv = tenant_client.get('/tenant/invoices/3')
    assert res_inv.status_code == 403

    # Complaint 2 belongs to Tenant 2
    res_cmp = tenant_client.get('/tenant/complaints/2')
    assert res_cmp.status_code == 403
