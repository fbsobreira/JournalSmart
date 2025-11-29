# File: app/__init__.py
"""
/app/__init__.py
Application factory and initialization
"""
import logging
import sys
from flask import Flask, render_template
from config import Config
from app.extensions import db


def configure_logging(app):
    """Configure application logging"""
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
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
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def run_migrations(app):
    """Run database migrations for schema changes"""
    from sqlalchemy import text

    with app.app_context():
        # Check if sort_order column exists in account_mappings
        try:
            result = db.session.execute(
                text("SELECT sort_order FROM account_mappings LIMIT 1")
            )
            result.close()
        except Exception:
            # Column doesn't exist, add it
            app.logger.info("Adding sort_order column to account_mappings table...")
            db.session.execute(
                text("ALTER TABLE account_mappings ADD COLUMN sort_order INTEGER DEFAULT 0 NOT NULL")
            )
            # Set initial sort_order based on id
            db.session.execute(
                text("UPDATE account_mappings SET sort_order = id")
            )
            db.session.commit()
            app.logger.info("Migration complete: sort_order column added")


def register_error_handlers(app):
    """Register error handlers for common HTTP errors"""

    @app.errorhandler(404)
    def not_found_error(error):  # noqa: F841 - registered via decorator
        _ = error  # Acknowledge the error parameter
        return render_template('error.html',
                               title="Page Not Found",
                               message="The page you're looking for doesn't exist."), 404

    @app.errorhandler(500)
    def internal_error(error):  # noqa: F841 - registered via decorator
        return render_template('error.html',
                               title="Server Error",
                               message="An unexpected error occurred. Please try again later.",
                               details=str(error) if app.debug else None), 500

    @app.errorhandler(403)
    def forbidden_error(error):  # noqa: F841 - registered via decorator
        _ = error  # Acknowledge the error parameter
        return render_template('error.html',
                               title="Access Denied",
                               message="You don't have permission to access this resource."), 403


def create_app(config_class=Config):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure logging
    configure_logging(app)
    app.logger.info("JournalSmart starting up...")

    # Initialize database
    db.init_app(app)
    with app.app_context():
        # Import models to ensure they're registered
        from app.models import QBOConnection, DBAccountMapping, UpdateHistory  # noqa: F401
        db.create_all()
        app.logger.info(f"Database initialized at {app.config.get('SQLALCHEMY_DATABASE_URI')}")

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

    app.logger.info("JournalSmart initialized successfully")

    return app
