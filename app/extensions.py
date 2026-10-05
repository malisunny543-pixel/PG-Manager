import secrets
from functools import wraps
from flask import session, request, abort, redirect, url_for, flash, g

def init_extensions(app):
    """Register custom template filters and context processors."""

    @app.context_processor
    def inject_csrf_and_user():
        """Inject csrf_token generator and current_user into all templates."""
        return {
            'csrf_token': get_or_create_csrf_token,
            'current_user': session.get('user', None)
        }

    @app.template_filter('currency')
    def currency_filter(value):
        """Format a decimal or float as Indian Rupee (₹)."""
        if value is None:
            return '₹0.00'
        try:
            return f"₹{float(value):,.2f}"
        except (ValueError, TypeError):
            return str(value)

    @app.template_filter('format_date')
    def date_filter(value, fmt='%d %b %Y'):
        """Format date/datetime objects."""
        if not value:
            return '-'
        try:
            return value.strftime(fmt)
        except AttributeError:
            return str(value)


def get_or_create_csrf_token():
    """Retrieve existing CSRF token from session or generate a new one."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def verify_csrf_token():
    """Verify CSRF token for state-changing requests."""
    token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
    session_token = session.get('_csrf_token')
    if not session_token or not token or not secrets.compare_digest(session_token, token):
        abort(400, description="Invalid or missing CSRF token.")


def login_required(f):
    """Decorator to enforce authenticated session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """Decorator to enforce role-based access control (ADMIN, MANAGER, TENANT)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login', next=request.url))
            user_role = session['user'].get('role')
            if user_role not in allowed_roles:
                abort(403, description="You do not have permission to access this resource.")
            return f(*args, **kwargs)
        return decorated_function
    return decorator
