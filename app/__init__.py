# File: app/__init__.py
"""
/app/__init__.py
Application factory and initialization
"""

import logging
import sys
from flask import Flask, render_template
from config import Config
from app.extensions import db, csrf


def configure_logging(app):
    """Configure application logging"""
    log_level = getattr(
        logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO
    )

    # Create formatter
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set Flask's logger
    app.logger.setLevel(log_level)

    # Suppress noisy loggers
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def run_migrations(app):
    """Run database migrations for schema changes"""
    from sqlalchemy import text

    with app.app_context():
        # Migration 1: Add sort_order column
        try:
            result = db.session.execute(
                text("SELECT sort_order FROM account_mappings LIMIT 1")
            )
            result.close()
        except Exception:
            app.logger.info("Adding sort_order column to account_mappings table...")
            db.session.execute(
                text(
                    "ALTER TABLE account_mappings ADD COLUMN sort_order INTEGER DEFAULT 0 NOT NULL"
                )
            )
            db.session.execute(text("UPDATE account_mappings SET sort_order = id"))
            db.session.commit()
            app.logger.info("Migration complete: sort_order column added")

        # Migration 2: Add is_regex column
        try:
            result = db.session.execute(
                text("SELECT is_regex FROM account_mappings LIMIT 1")
            )
            result.close()
        except Exception:
            app.logger.info("Adding is_regex column to account_mappings table...")
            db.session.execute(
                text(
                    "ALTER TABLE account_mappings ADD COLUMN is_regex BOOLEAN DEFAULT 0 NOT NULL"
                )
            )
            db.session.commit()
            app.logger.info("Migration complete: is_regex column added")

        # Migration 3: Add category column
        try:
            result = db.session.execute(
                text("SELECT category FROM account_mappings LIMIT 1")
            )
            result.close()
        except Exception:
            app.logger.info("Adding category column to account_mappings table...")
            db.session.execute(
                text("ALTER TABLE account_mappings ADD COLUMN category VARCHAR(100)")
            )
            db.session.commit()
            app.logger.info("Migration complete: category column added")

        # Migration 4: Add realm_id column for multi-company support
        try:
            result = db.session.execute(
                text("SELECT realm_id FROM account_mappings LIMIT 1")
            )
            result.close()
        except Exception:
            app.logger.info(
                "Adding realm_id column to account_mappings table for multi-company support..."
            )
            db.session.execute(
                text("ALTER TABLE account_mappings ADD COLUMN realm_id VARCHAR(50)")
            )
            db.session.commit()
            app.logger.info("Migration complete: realm_id column added")

            # Try to migrate existing mappings to current active connection
            try:
                from app.models.qbo_connection import QBOConnection
                from app.models.db_account_mapping import DBAccountMapping

                connection = QBOConnection.query.order_by(
                    QBOConnection.updated_at.desc()
                ).first()
                if connection:
                    migrated = DBAccountMapping.migrate_mappings_to_realm(
                        connection.realm_id
                    )
                    if migrated > 0:
                        app.logger.info(
                            f"Migrated {migrated} existing mappings to realm {connection.realm_id}"
                        )
            except Exception as e:
                app.logger.warning(
                    f"Could not migrate existing mappings to realm: {str(e)}"
                )

        # Migration 5: Add realm_id column to update_history for multi-company support
        try:
            result = db.session.execute(
                text("SELECT realm_id FROM update_history LIMIT 1")
            )
            result.close()
        except Exception:
            app.logger.info(
                "Adding realm_id column to update_history table for multi-company support..."
            )
            db.session.execute(
                text("ALTER TABLE update_history ADD COLUMN realm_id VARCHAR(50)")
            )
            db.session.commit()
            app.logger.info(
                "Migration complete: realm_id column added to update_history"
            )

            # Try to migrate existing history to current active connection
            try:
                from app.models.qbo_connection import QBOConnection

                connection = QBOConnection.query.order_by(
                    QBOConnection.updated_at.desc()
                ).first()
                if connection:
                    result = db.session.execute(
                        text(
                            "UPDATE update_history SET realm_id = :realm_id WHERE realm_id IS NULL"
                        ),
                        {"realm_id": connection.realm_id},
                    )
                    db.session.commit()
                    app.logger.info(
                        f"Migrated {result.rowcount} existing history entries to realm {connection.realm_id}"
                    )
            except Exception as e:
                app.logger.warning(
                    f"Could not migrate existing history to realm: {str(e)}"
                )


def register_security_headers(app):
    """Register security headers on all responses"""
    import secrets
    from flask import g, request

    @app.before_request
    def generate_nonce():
        """Generate a unique nonce for each request (for CSP)"""
        # Only generate for HTML responses (not API calls)
        if not request.path.startswith("/api/"):
            g.csp_nonce = secrets.token_urlsafe(16)

    @app.after_request
    def add_security_headers(response):
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Permissions policy (restrict browser features)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # Content Security Policy (XSS protection)
        # Only add for HTML responses
        if response.content_type and "text/html" in response.content_type:
            nonce = getattr(g, "csp_nonce", "")
            csp = "; ".join(
                [
                    "default-src 'self'",
                    f"script-src 'self' 'nonce-{nonce}' https://cdn.tailwindcss.com",
                    "style-src 'self' 'unsafe-inline'",  # Tailwind needs inline styles
                    "img-src 'self' data:",
                    "font-src 'self'",
                    "connect-src 'self'",
                    "frame-ancestors 'self'",
                    "form-action 'self'",
                    "base-uri 'self'",
                ]
            )
            response.headers["Content-Security-Policy"] = csp

        return response

    @app.context_processor
    def inject_csp_nonce():
        """Make nonce available in all templates"""
        return {"csp_nonce": getattr(g, "csp_nonce", "")}


def register_error_handlers(app):
    """Register error handlers for common HTTP errors"""

    @app.errorhandler(404)
    def not_found_error(error):  # noqa: F841 - registered via decorator
        _ = error  # Acknowledge the error parameter
        return render_template(
            "error.html",
            title="Page Not Found",
            message="The page you're looking for doesn't exist.",
        ), 404

    @app.errorhandler(500)
    def internal_error(error):  # noqa: F841 - registered via decorator
        return render_template(
            "error.html",
            title="Server Error",
            message="An unexpected error occurred. Please try again later.",
            details=str(error) if app.debug else None,
        ), 500

    @app.errorhandler(403)
    def forbidden_error(error):  # noqa: F841 - registered via decorator
        _ = error  # Acknowledge the error parameter
        return render_template(
            "error.html",
            title="Access Denied",
            message="You don't have permission to access this resource.",
        ), 403


def create_app(config_class=Config):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure logging
    configure_logging(app)
    app.logger.info("JournalSmart starting up...")

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        # Import models to ensure they're registered
        from app.models import QBOConnection, DBAccountMapping, UpdateHistory  # noqa: F401

        db.create_all()
        app.logger.info(
            f"Database initialized at {app.config.get('SQLALCHEMY_DATABASE_URI')}"
        )

    # Run database migrations
    run_migrations(app)

    # Initialize QBO service
    from app.services.qbo import init_qbo

    init_qbo(app)

    # Migrate any plain text tokens to encrypted (safe to run multiple times)
    with app.app_context():
        from app.services.token_service import token_service

        migrated = token_service.migrate_to_encrypted_tokens()
        if migrated > 0:
            app.logger.info(f"Migrated {migrated} connection(s) to encrypted tokens")

    # Register blueprints
    from app.routes import journal, mapping, auth, api, history

    app.register_blueprint(journal.bp)
    app.register_blueprint(mapping.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(history.bp)

    # Register error handlers
    register_error_handlers(app)

    # Register security headers
    register_security_headers(app)

    app.logger.info("JournalSmart initialized successfully")

    return app
