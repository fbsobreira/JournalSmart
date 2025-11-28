# File: app/utils/decorators.py
"""
/app/utils/decorators.py
Custom decorators for the application
"""
from functools import wraps
from flask import redirect, url_for
from app.services.qbo import qbo_service

def require_qbo_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not qbo_service.auth_client.access_token:
            return redirect(url_for('auth.auth'))
        return f(*args, **kwargs)
    return decorated_function