# File: app/routes/api.py
"""
/app/routes/api.py
REST API endpoints for mappings and other resources

CSRF protection: All POST/PUT/DELETE requests require X-CSRFToken header.
The token is automatically added by main.js fetch override.
"""

import logging
from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models.db_account_mapping import DBAccountMapping
from app.utils.decorators import require_qbo_auth

bp = Blueprint("api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


# =============================================================================
# Mapping CRUD Endpoints
# =============================================================================


@bp.route("/mappings", methods=["GET"])
@require_qbo_auth
def list_mappings():
    """Get all account mappings ordered by sort_order"""
    try:
        # Get optional filter parameters
        active_only = request.args.get("active", "true").lower() == "true"

        query = DBAccountMapping.query.order_by(DBAccountMapping.sort_order.asc())

        if active_only:
            query = query.filter_by(is_active=True)

        mappings = query.all()

        logger.debug(f"Retrieved {len(mappings)} mappings")

        return jsonify(
            {
                "success": True,
                "mappings": [m.to_dict() for m in mappings],
                "count": len(mappings),
            }
        )

    except Exception as e:
        logger.error(f"Error listing mappings: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/mappings", methods=["POST"])
@require_qbo_auth
def create_mapping():
    """Create a new account mapping"""
    try:
        data = request.json

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["pattern", "from_account_id", "to_account_id"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check for duplicate pattern with same from_account_id
        existing = DBAccountMapping.query.filter_by(
            pattern=data["pattern"],
            from_account_id=data["from_account_id"],
            is_active=True,
        ).first()

        if existing:
            return jsonify(
                {
                    "error": "A mapping with this pattern and source account already exists"
                }
            ), 409

        # Validate regex pattern if is_regex is true
        is_regex = data.get("is_regex", False)
        if is_regex:
            is_valid, error = DBAccountMapping.validate_regex(data["pattern"])
            if not is_valid:
                return jsonify({"error": f"Invalid regex pattern: {error}"}), 400

        # Create new mapping with next sort_order
        mapping = DBAccountMapping(
            pattern=data["pattern"],
            from_account_id=data["from_account_id"],
            from_account_name=data.get("from_account_name"),
            to_account_id=data["to_account_id"],
            to_account_name=data.get("to_account_name"),
            is_active=data.get("is_active", True),
            is_regex=is_regex,
            category=data.get("category", "").strip() or None,
            sort_order=DBAccountMapping.get_next_sort_order(),
        )

        db.session.add(mapping)
        db.session.commit()

        logger.info(
            f"Created mapping: {mapping.pattern} ({mapping.from_account_id} -> {mapping.to_account_id})"
        )

        return jsonify({"success": True, "mapping": mapping.to_dict()}), 201

    except Exception as e:
        logger.error(f"Error creating mapping: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/mappings/<int:mapping_id>", methods=["GET"])
@require_qbo_auth
def get_mapping(mapping_id):
    """Get a specific mapping by ID"""
    try:
        mapping = DBAccountMapping.query.get(mapping_id)

        if not mapping:
            return jsonify({"error": "Mapping not found"}), 404

        return jsonify({"success": True, "mapping": mapping.to_dict()})

    except Exception as e:
        logger.error(f"Error getting mapping {mapping_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/mappings/<int:mapping_id>", methods=["PUT"])
@require_qbo_auth
def update_mapping(mapping_id):
    """Update an existing mapping"""
    try:
        mapping = DBAccountMapping.query.get(mapping_id)

        if not mapping:
            return jsonify({"error": "Mapping not found"}), 404

        data = request.json

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate regex pattern if changing to regex mode
        is_regex = data.get("is_regex", mapping.is_regex)
        pattern = data.get("pattern", mapping.pattern)
        if is_regex and ("is_regex" in data or "pattern" in data):
            is_valid, error = DBAccountMapping.validate_regex(pattern)
            if not is_valid:
                return jsonify({"error": f"Invalid regex pattern: {error}"}), 400

        # Update fields if provided
        if "pattern" in data:
            mapping.pattern = data["pattern"]
        if "from_account_id" in data:
            mapping.from_account_id = data["from_account_id"]
        if "from_account_name" in data:
            mapping.from_account_name = data["from_account_name"]
        if "to_account_id" in data:
            mapping.to_account_id = data["to_account_id"]
        if "to_account_name" in data:
            mapping.to_account_name = data["to_account_name"]
        if "is_active" in data:
            mapping.is_active = data["is_active"]
        if "is_regex" in data:
            mapping.is_regex = data["is_regex"]
        if "category" in data:
            mapping.category = data["category"].strip() if data["category"] else None

        db.session.commit()

        logger.info(f"Updated mapping {mapping_id}")

        return jsonify({"success": True, "mapping": mapping.to_dict()})

    except Exception as e:
        logger.error(f"Error updating mapping {mapping_id}: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/mappings/<int:mapping_id>", methods=["DELETE"])
@require_qbo_auth
def delete_mapping(mapping_id):
    """Delete a mapping"""
    try:
        mapping = DBAccountMapping.query.get(mapping_id)

        if not mapping:
            return jsonify({"error": "Mapping not found"}), 404

        db.session.delete(mapping)
        db.session.commit()

        logger.info(f"Deleted mapping {mapping_id}")

        return jsonify({"success": True, "message": f"Mapping {mapping_id} deleted"})

    except Exception as e:
        logger.error(f"Error deleting mapping {mapping_id}: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/mappings/<int:mapping_id>/toggle", methods=["POST"])
@require_qbo_auth
def toggle_mapping(mapping_id):
    """Toggle a mapping's active status"""
    try:
        mapping = DBAccountMapping.query.get(mapping_id)

        if not mapping:
            return jsonify({"error": "Mapping not found"}), 404

        mapping.is_active = not mapping.is_active
        db.session.commit()

        logger.info(
            f"Toggled mapping {mapping_id} to {'active' if mapping.is_active else 'inactive'}"
        )

        return jsonify({"success": True, "mapping": mapping.to_dict()})

    except Exception as e:
        logger.error(f"Error toggling mapping {mapping_id}: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/mappings/reorder", methods=["POST"])
@require_qbo_auth
def reorder_mappings():
    """Reorder mappings by updating their sort_order values"""
    try:
        data = request.json

        if not data or "order" not in data:
            return jsonify({"error": "No order provided"}), 400

        order = data["order"]

        if not isinstance(order, list):
            return jsonify({"error": "Order must be an array of mapping IDs"}), 400

        # Update sort_order for each mapping
        for index, mapping_id in enumerate(order):
            mapping = DBAccountMapping.query.get(mapping_id)
            if mapping:
                mapping.sort_order = index

        db.session.commit()

        logger.info(f"Reordered {len(order)} mappings")

        return jsonify({"success": True, "message": f"Reordered {len(order)} mappings"})

    except Exception as e:
        logger.error(f"Error reordering mappings: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Pattern Testing Endpoints
# =============================================================================


@bp.route("/mappings/test", methods=["POST"])
@require_qbo_auth
def test_pattern():
    """Test a pattern against recent journal entries"""
    from app.services.qbo import qbo_service
    from datetime import datetime, timedelta
    import re

    try:
        data = request.json

        if not data:
            return jsonify({"error": "No data provided"}), 400

        pattern = data.get("pattern", "").strip()
        from_account_id = data.get("from_account_id", "").strip()
        is_regex = data.get("is_regex", False)

        if not pattern:
            return jsonify({"error": "Pattern is required"}), 400

        if not from_account_id:
            return jsonify({"error": "From account is required"}), 400

        # Validate regex if is_regex is true
        if is_regex:
            is_valid, error = DBAccountMapping.validate_regex(pattern)
            if not is_valid:
                return jsonify({"error": f"Invalid regex pattern: {error}"}), 400

        # Get journals from the last 90 days for testing
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        # Fetch journals for the specified account
        journals = qbo_service.get_journals_for_pattern_test(
            from_account_id, start_date
        )

        # Test pattern against journal descriptions
        matches = []

        for journal in journals:
            for line in journal.get("lines", []):
                description = line.get("description", "")
                if not description:
                    continue

                match_found = False
                match_start = -1
                match_end = -1

                if is_regex:
                    try:
                        match = re.search(pattern, description, re.IGNORECASE)
                        if match:
                            match_found = True
                            match_start = match.start()
                            match_end = match.end()
                    except re.error:
                        pass
                else:
                    pattern_lower = pattern.lower()
                    if pattern_lower in description.lower():
                        match_found = True
                        match_start = description.lower().find(pattern_lower)
                        match_end = match_start + len(pattern)

                if match_found:
                    matches.append(
                        {
                            "journal_id": journal.get("id"),
                            "journal_date": journal.get("date"),
                            "description": description,
                            "match_start": match_start,
                            "match_end": match_end,
                            "amount": line.get("amount"),
                            "posting_type": line.get("posting_type"),
                        }
                    )

        logger.debug(
            f"Pattern '{pattern}' (regex={is_regex}) matched {len(matches)} lines"
        )

        return jsonify(
            {
                "success": True,
                "pattern": pattern,
                "is_regex": is_regex,
                "matches": matches[:50],  # Limit to 50 results
                "total_matches": len(matches),
                "truncated": len(matches) > 50,
            }
        )

    except Exception as e:
        logger.error(f"Error testing pattern: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/mappings/validate-regex", methods=["POST"])
@require_qbo_auth
def validate_regex():
    """Validate a regex pattern"""
    try:
        data = request.json

        if not data or "pattern" not in data:
            return jsonify({"error": "Pattern is required"}), 400

        pattern = data["pattern"]
        is_valid, error = DBAccountMapping.validate_regex(pattern)

        return jsonify({"success": True, "is_valid": is_valid, "error": error})

    except Exception as e:
        logger.error(f"Error validating regex: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/mappings/categories", methods=["GET"])
@require_qbo_auth
def get_categories():
    """Get all unique mapping categories"""
    try:
        categories = DBAccountMapping.get_categories()

        return jsonify({"success": True, "categories": categories})

    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Import/Export Endpoints
# =============================================================================


@bp.route("/mappings/import", methods=["POST"])
@require_qbo_auth
def import_mappings():
    """Import mappings from JSON array"""
    try:
        data = request.json

        if not data or not isinstance(data, list):
            return jsonify({"error": "Expected JSON array of mappings"}), 400

        imported = 0
        skipped = 0
        errors = []

        for idx, mapping_data in enumerate(data):
            # Validate required fields
            if not all(
                k in mapping_data
                for k in ["pattern", "from_account_id", "to_account_id"]
            ):
                skipped += 1
                errors.append(f"Item {idx}: Missing required fields")
                continue

            # Validate regex if is_regex is true
            is_regex = mapping_data.get("is_regex", False)
            if is_regex:
                is_valid, error = DBAccountMapping.validate_regex(
                    mapping_data["pattern"]
                )
                if not is_valid:
                    skipped += 1
                    errors.append(f"Item {idx}: Invalid regex - {error}")
                    continue

            # Check for existing
            existing = DBAccountMapping.query.filter_by(
                pattern=mapping_data["pattern"],
                from_account_id=mapping_data["from_account_id"],
            ).first()

            if existing:
                skipped += 1
                errors.append(f"Item {idx}: Duplicate pattern/account")
                continue

            # Create new mapping
            mapping = DBAccountMapping(
                pattern=mapping_data["pattern"],
                from_account_id=mapping_data["from_account_id"],
                from_account_name=mapping_data.get("from_account_name"),
                to_account_id=mapping_data["to_account_id"],
                to_account_name=mapping_data.get("to_account_name"),
                is_active=mapping_data.get("is_active", True),
                is_regex=is_regex,
                category=mapping_data.get("category", "").strip() or None,
                sort_order=DBAccountMapping.get_next_sort_order(),
            )
            db.session.add(mapping)
            imported += 1

        db.session.commit()

        logger.info(f"Imported {imported} mappings, skipped {skipped}")

        return jsonify(
            {
                "success": True,
                "imported": imported,
                "skipped": skipped,
                "errors": errors[:10] if errors else [],  # Limit error messages
            }
        )

    except Exception as e:
        logger.error(f"Error importing mappings: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/mappings/export", methods=["GET"])
@require_qbo_auth
def export_mappings():
    """Export all mappings as JSON array"""
    try:
        mappings = DBAccountMapping.query.order_by(
            DBAccountMapping.sort_order.asc()
        ).all()

        export_data = [
            {
                "pattern": m.pattern,
                "from_account_id": m.from_account_id,
                "from_account_name": m.from_account_name,
                "to_account_id": m.to_account_id,
                "to_account_name": m.to_account_name,
                "is_active": m.is_active,
                "is_regex": m.is_regex,
                "category": m.category,
            }
            for m in mappings
        ]

        return jsonify(export_data)

    except Exception as e:
        logger.error(f"Error exporting mappings: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/mappings/check-duplicate", methods=["POST"])
@require_qbo_auth
def check_duplicate():
    """Check if a mapping with the same pattern and from_account already exists"""
    try:
        data = request.json

        if not data:
            return jsonify({"error": "No data provided"}), 400

        pattern = data.get("pattern", "").strip()
        from_account_id = data.get("from_account_id", "").strip()
        exclude_id = data.get("exclude_id")  # For edit mode

        if not pattern or not from_account_id:
            return jsonify({"error": "Pattern and from_account_id required"}), 400

        query = DBAccountMapping.query.filter_by(
            pattern=pattern, from_account_id=from_account_id, is_active=True
        )

        if exclude_id:
            query = query.filter(DBAccountMapping.id != exclude_id)

        existing = query.first()

        return jsonify(
            {
                "success": True,
                "is_duplicate": existing is not None,
                "existing_mapping": existing.to_dict() if existing else None,
            }
        )

    except Exception as e:
        logger.error(f"Error checking duplicate: {str(e)}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# History Endpoints
# =============================================================================


@bp.route("/history", methods=["GET"])
@require_qbo_auth
def list_history():
    """Get update history with optional filtering"""
    from app.models.update_history import UpdateHistory

    try:
        # Get optional query parameters
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)
        journal_id = request.args.get("journal_id")

        # Build query
        query = UpdateHistory.query.order_by(UpdateHistory.updated_at.desc())

        if journal_id:
            query = query.filter_by(journal_id=journal_id)

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        history = query.offset(offset).limit(limit).all()

        return jsonify(
            {
                "success": True,
                "history": [h.to_dict() for h in history],
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )

    except Exception as e:
        logger.error(f"Error listing history: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/history/stats", methods=["GET"])
@require_qbo_auth
def history_stats():
    """Get update history statistics"""
    from app.models.update_history import UpdateHistory
    from sqlalchemy import func

    try:
        # Get total updates
        total_updates = UpdateHistory.query.count()

        # Get updates by account
        updates_by_account = (
            db.session.query(
                UpdateHistory.to_account_name,
                func.count(UpdateHistory.id).label("count"),
            )
            .group_by(UpdateHistory.to_account_name)
            .all()
        )

        return jsonify(
            {
                "success": True,
                "total_updates": total_updates,
                "updates_by_account": [
                    {"account": acc, "count": cnt}
                    for acc, cnt in updates_by_account
                    if acc
                ],
            }
        )

    except Exception as e:
        logger.error(f"Error getting history stats: {str(e)}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# System Status Endpoints
# =============================================================================


@bp.route("/status", methods=["GET"])
def system_status():
    """Get system status including encryption status"""
    from app.models.qbo_connection import QBOConnection

    try:
        # Check QBO connection and encryption
        connection = QBOConnection.query.first()

        qbo_status = {"connected": False, "tokens_encrypted": False}

        if connection:
            qbo_status["connected"] = True
            qbo_status["tokens_encrypted"] = connection.tokens_encrypted

        # Check if encryption key is configured (not auto-generated)
        import os

        encryption_key_set = bool(os.getenv("ENCRYPTION_KEY"))

        return jsonify(
            {
                "success": True,
                "status": {
                    "qbo_connection": qbo_status,
                    "encryption": {
                        "key_configured": encryption_key_set,
                        "tokens_encrypted": qbo_status["tokens_encrypted"],
                    },
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({"error": str(e)}), 500
