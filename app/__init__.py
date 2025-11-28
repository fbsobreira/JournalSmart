# File: app/__init__.py
"""
/app/__init__.py
Application factory and initialization
"""
from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    from app.services.qbo import init_qbo
    init_qbo(app)
    
    # Register blueprints
    from app.routes import journal, mapping, auth
    app.register_blueprint(journal.bp)
    app.register_blueprint(mapping.bp)
    app.register_blueprint(auth.bp)
    
    return app