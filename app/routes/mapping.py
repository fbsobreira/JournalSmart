# File: app/routes/mapping.py
"""
/app/routes/mapping.py
Account mapping configuration routes
"""

import logging
from flask import Blueprint, render_template, request, jsonify
from app.services.qbo import qbo_service
from app.extensions import db
from app.models.db_account_mapping import DBAccountMapping
from app.utils.decorators import require_qbo_auth

bp = Blueprint("mapping", __name__)
logger = logging.getLogger(__name__)


@bp.route("/mapping")
@require_qbo_auth
def mapping_config():
    """Display mapping configuration page"""
    try:
        # Get current realm_id
        realm_id = qbo_service.get_current_realm_id()

        # Get accounts for dropdowns
        accounts = qbo_service.get_accounts()

        # Get current mappings from database ordered by sort_order (filtered by realm)
        query = DBAccountMapping.query.order_by(DBAccountMapping.sort_order.asc())
        if realm_id:
            query = query.filter(DBAccountMapping.realm_id == realm_id)
        db_mappings = query.all()
        mappings = [m.to_dict() for m in db_mappings]

        logger.debug(
            f"Loaded {len(accounts)} accounts and {len(mappings)} mappings for realm {realm_id}"
        )

        return render_template(
            "mapping_config.html", accounts=accounts, mappings=mappings
        )

    except Exception as e:
        logger.error(f"Error loading mapping config: {str(e)}")
        return render_template(
            "mapping_config.html", accounts=[], mappings=[], error=str(e)
        )


@bp.route("/mapping", methods=["POST"])
@require_qbo_auth
def save_mapping():
    """Save mapping configuration to database for current company"""
    try:
        realm_id = qbo_service.get_current_realm_id()
        mapping_data = request.json

        if not mapping_data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["pattern", "from_account_id", "to_account_id"]
        for field in required_fields:
            if field not in mapping_data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check for duplicate within current realm
        query = DBAccountMapping.query.filter_by(
            pattern=mapping_data["pattern"],
            from_account_id=mapping_data["from_account_id"],
            is_active=True,
        )
        if realm_id:
            query = query.filter(DBAccountMapping.realm_id == realm_id)
        existing = query.first()

        if existing:
            return jsonify(
                {
                    "error": "A mapping with this pattern and source account already exists"
                }
            ), 409

        # Create new mapping with next sort_order for this realm
        mapping = DBAccountMapping(
            realm_id=realm_id,
            pattern=mapping_data["pattern"],
            from_account_id=mapping_data["from_account_id"],
            from_account_name=mapping_data.get("from_account_name"),
            to_account_id=mapping_data["to_account_id"],
            to_account_name=mapping_data.get("to_account_name"),
            is_active=mapping_data.get("is_active", True),
            sort_order=DBAccountMapping.get_next_sort_order(realm_id),
        )

        db.session.add(mapping)
        db.session.commit()

        logger.info(f"Created mapping for realm {realm_id}: {mapping.pattern}")

        return jsonify({"success": True, "mapping": mapping.to_dict()}), 201

    except Exception as e:
        logger.error(f"Error saving mapping: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
