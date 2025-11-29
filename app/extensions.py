# File: app/extensions.py
"""
/app/extensions.py
Flask extensions initialization
"""
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()
