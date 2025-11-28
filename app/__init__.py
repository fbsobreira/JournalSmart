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

    # Initialize QBO service
    from app.services.qbo import init_qbo
    init_qbo(app)

    # Register blueprints
    from app.routes import journal, mapping, auth, api
    app.register_blueprint(journal.bp)
    app.register_blueprint(mapping.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(api.bp)

    # Register error handlers
    register_error_handlers(app)

    app.logger.info("JournalSmart initialized successfully")

    return app
