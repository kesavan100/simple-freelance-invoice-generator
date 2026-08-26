from flask import Flask, request, redirect, url_for, session
from app.config import Config
from app.database.db import close_db, init_db
from app.services.calculation_service import format_currency


def create_app(config_class=Config):
    """Application factory for Smart Freelance Invoice & Financial Management Platform."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Database & Teardown
    with app.app_context():
        init_db(app)
    app.teardown_appcontext(close_db)

    # Register Jinja Filters & Globals
    @app.template_filter("currency")
    def currency_filter(amount, code="INR", include_symbol=True):
        return format_currency(amount, code, include_symbol)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.invoices import invoices_bp
    from app.routes.clients import clients_bp
    from app.routes.expenses import expenses_bp
    from app.routes.ai import ai_bp
    from app.routes.verification import verification_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(verification_bp)
    app.register_blueprint(settings_bp)

    # Protect internal routes with Authentication (Verification & Auth endpoints remain public)
    @app.before_request
    def require_login():
        if app.config.get("TESTING"):
            return None

        # Allow static files, auth endpoints, and public invoice verification
        public_endpoints = {"auth.login", "auth.logout", "verification.verify_invoice", "static"}
        if request.endpoint in public_endpoints or (request.endpoint and request.endpoint.startswith("static")):
            return None

        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.url))

    return app
