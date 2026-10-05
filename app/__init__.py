import os
from flask import Flask, render_template, request
from app.config import config_by_name
from app.db import init_db
from app.extensions import init_extensions, verify_csrf_token

def create_app(config_name=None):
    """Application factory for PG Management System."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Initialize Database lifecycle
    init_db(app)

    # Initialize Extensions and Template Helpers
    init_extensions(app)

    # Global CSRF enforcement for state-changing HTTP methods
    @app.before_request
    def csrf_protect():
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            if not app.config.get('TESTING'):
                verify_csrf_token()

    # Register Custom Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html', error=e), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html', error=e), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html', error=e), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html', error=e), 500

    # Register Modular Blueprints
    from app.auth import auth_bp
    from app.shared import shared_bp
    from app.admin import admin_bp
    from app.manager import manager_bp
    from app.tenant import tenant_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(shared_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(tenant_bp)

    # Apply ProxyFix only for production environment behind reverse proxies
    if config_name == 'production' or os.environ.get('FLASK_ENV') == 'production':
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    return app
