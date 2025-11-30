# File: config.py
"""
/config.py
Configuration management for the application
"""
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv(override=True)


def get_or_generate_encryption_key() -> str:
    """
    Get encryption key from environment or generate a new one.
    In production, ENCRYPTION_KEY should always be set in .env
    """
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        # Generate a key for development (logged as warning)
        logging.warning(
            "ENCRYPTION_KEY not set - generating temporary key. "
            "Set ENCRYPTION_KEY in .env for production!"
        )
        key = Fernet.generate_key().decode()
    return key


class Config:
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'  # Disabled by default

    # Session Security
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection for cookies

    # Encryption key for tokens at rest
    ENCRYPTION_KEY = get_or_generate_encryption_key()

    # App Password (optional - leave empty to disable)
    APP_PASSWORD = os.getenv('APP_PASSWORD', '')

    # QuickBooks OAuth
    QBO_CLIENT_ID = os.getenv('QBO_CLIENT_ID')
    QBO_CLIENT_SECRET = os.getenv('QBO_CLIENT_SECRET')
    QBO_REDIRECT_URI = os.getenv('QBO_REDIRECT_URI')
    QBO_ENVIRONMENT = os.getenv('QBO_ENVIRONMENT', 'sandbox')

    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '443'))
    SSL_CERT = os.getenv('SSL_CERT', '')  # Path to SSL certificate
    SSL_KEY = os.getenv('SSL_KEY', '')    # Path to SSL key

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', './data/journalsmart.db')

    # SQLAlchemy configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def init_database_uri():
        """Initialize and return SQLAlchemy database URI"""
        db_path = os.getenv('DATABASE_PATH', './data/journalsmart.db')
        # Ensure path is absolute
        db_path = Path(db_path).resolve()
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f'sqlite:///{db_path}'

    # Set class attribute
    SQLALCHEMY_DATABASE_URI = init_database_uri()

    # Load and parse account mappings
    @staticmethod
    def get_account_mappings():
        mappings_str = os.getenv('ACCOUNT_MAPPINGS', '[]')
        try:
            # Strip any extra whitespace and newlines
            mappings_str = mappings_str.strip()

            return json.loads(mappings_str)
        except json.JSONDecodeError:
            print("Error parsing ACCOUNT_MAPPINGS from env")
            return []