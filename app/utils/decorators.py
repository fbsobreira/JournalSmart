# File: app/utils/decorators.py
"""
/app/utils/decorators.py
Custom decorators for the application
"""

import logging
from functools import wraps
from flask import redirect, url_for, session, current_app
from app.services.qbo import qbo_service

logger = logging.getLogger(__name__)


def require_app_password(f):
    """
    Decorator to require app password authentication.
    If APP_PASSWORD is not set in config, this check is skipped.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        app_password = current_app.config.get("APP_PASSWORD", "")

        # If no password is configured, skip this check
        if not app_password:
            return f(*args, **kwargs)

        # Check if user is authenticated
        if not session.get("app_authenticated"):
            logger.debug("App password required but not authenticated")
            return redirect(url_for("auth.login"))

        return f(*args, **kwargs)

    return decorated_function


def require_qbo_auth(f):
    """
    Decorator to require QuickBooks OAuth authentication.
    Also checks app password if configured.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check app password (if configured)
        app_password = current_app.config.get("APP_PASSWORD", "")
        if app_password and not session.get("app_authenticated"):
            logger.debug("App password required but not authenticated")
            return redirect(url_for("auth.login"))

        # Then check QBO authentication
        if not qbo_service.auth_client or not qbo_service.auth_client.access_token:
            logger.debug("QBO authentication required")
            return redirect(url_for("auth.qbo_auth"))

        return f(*args, **kwargs)

    return decorated_function
