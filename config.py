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

load_dotenv(override=True)


class Config:
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

    # App Password (optional - leave empty to disable)
    APP_PASSWORD = os.getenv('APP_PASSWORD', '')

    # QuickBooks OAuth
    QBO_CLIENT_ID = os.getenv('QBO_CLIENT_ID')
    QBO_CLIENT_SECRET = os.getenv('QBO_CLIENT_SECRET')
    QBO_REDIRECT_URI = os.getenv('QBO_REDIRECT_URI')
    QBO_ENVIRONMENT = os.getenv('QBO_ENVIRONMENT', 'sandbox')

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