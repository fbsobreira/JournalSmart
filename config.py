# File: config.py
"""
/config.py
Configuration management for the application
"""
import os
import json
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    QBO_CLIENT_ID = os.getenv('QBO_CLIENT_ID')
    QBO_CLIENT_SECRET = os.getenv('QBO_CLIENT_SECRET')
    QBO_REDIRECT_URI = os.getenv('QBO_REDIRECT_URI')
    QBO_ENVIRONMENT = os.getenv('QBO_ENVIRONMENT', 'sandbox')

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