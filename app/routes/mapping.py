# File: app/routes/mapping.py
"""
/app/routes/mapping.py
Account mapping configuration routes
"""
from flask import Blueprint, render_template, request, jsonify
from app.services.qbo import qbo_service
from config import Config
from app.utils.decorators import require_qbo_auth

bp = Blueprint('mapping', __name__)

@bp.route('/mapping')
@require_qbo_auth
def mapping_config():
    # Get accounts for dropdowns
    accounts = qbo_service.get_accounts()
    # Get current mappings
    mappings = Config.get_account_mappings()
    
    return render_template('mapping_config.html', 
                         accounts=accounts, 
                         mappings=mappings)

@bp.route('/mapping', methods=['POST'])
def save_mapping():
    mapping_data = request.json
    # Save mapping configuration
    return jsonify({"status": "success"})
