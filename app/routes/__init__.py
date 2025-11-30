# File: app/routes/__init__.py
"""
/app/routes/__init__.py
Blueprint registry for JournalSmart routes
"""

from app.routes import auth, journal, mapping, api, history

__all__ = ["auth", "journal", "mapping", "api", "history"]
