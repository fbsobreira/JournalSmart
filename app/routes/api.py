# File: app/routes/api.py
"""
/app/routes/api.py
REST API endpoints for mappings and other resources
"""
import logging
from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models.db_account_mapping import DBAccountMapping
from app.utils.decorators import require_qbo_auth

bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


# =============================================================================
# Mapping CRUD Endpoints
# =============================================================================

@bp.route('/mappings', methods=['GET'])
@require_qbo_auth
def list_mappings():
    """Get all account mappings"""
    try:
        # Get optional filter parameters
        active_only = request.args.get('active', 'true').lower() == 'true'

        if active_only:
            mappings = DBAccountMapping.query.filter_by(is_active=True).all()
        else:
            mappings = DBAccountMapping.query.all()

        logger.debug(f"Retrieved {len(mappings)} mappings")

        return jsonify({
            'success': True,
            'mappings': [m.to_dict() for m in mappings],
            'count': len(mappings)
        })

    except Exception as e:
        logger.error(f"Error listing mappings: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/mappings', methods=['POST'])
@require_qbo_auth
def create_mapping():
    """Create a new account mapping"""
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields
        required_fields = ['pattern', 'from_account_id', 'to_account_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Check for duplicate pattern with same from_account_id
        existing = DBAccountMapping.query.filter_by(
            pattern=data['pattern'],
            from_account_id=data['from_account_id'],
            is_active=True
        ).first()

        if existing:
            return jsonify({
                'error': 'A mapping with this pattern and source account already exists'
            }), 409

        # Create new mapping
        mapping = DBAccountMapping(
            pattern=data['pattern'],
            from_account_id=data['from_account_id'],
            from_account_name=data.get('from_account_name'),
            to_account_id=data['to_account_id'],
            to_account_name=data.get('to_account_name'),
            is_active=data.get('is_active', True)
        )

        db.session.add(mapping)
        db.session.commit()

        logger.info(f"Created mapping: {mapping.pattern} ({mapping.from_account_id} -> {mapping.to_account_id})")

        return jsonify({
            'success': True,
            'mapping': mapping.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating mapping: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/mappings/<int:mapping_id>', methods=['GET'])
@require_qbo_auth
def get_mapping(mapping_id):
    """Get a specific mapping by ID"""
    try:
        mapping = DBAccountMapping.query.get(mapping_id)

        if not mapping:
            return jsonify({'error': 'Mapping not found'}), 404

        return jsonify({
            'success': True,
            'mapping': mapping.to_dict()
        })

    except Exception as e:
        logger.error(f"Error getting mapping {mapping_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/mappings/<int:mapping_id>', methods=['PUT'])
@require_qbo_auth
def update_mapping(mapping_id):
    """Update an existing mapping"""
    try:
        mapping = DBAccountMapping.query.get(mapping_id)

        if not mapping:
            return jsonify({'error': 'Mapping not found'}), 404

        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update fields if provided
        if 'pattern' in data:
            mapping.pattern = data['pattern']
        if 'from_account_id' in data:
            mapping.from_account_id = data['from_account_id']
        if 'from_account_name' in data:
            mapping.from_account_name = data['from_account_name']
        if 'to_account_id' in data:
            mapping.to_account_id = data['to_account_id']
        if 'to_account_name' in data:
            mapping.to_account_name = data['to_account_name']
        if 'is_active' in data:
            mapping.is_active = data['is_active']

        db.session.commit()

        logger.info(f"Updated mapping {mapping_id}")

        return jsonify({
            'success': True,
            'mapping': mapping.to_dict()
        })

    except Exception as e:
        logger.error(f"Error updating mapping {mapping_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/mappings/<int:mapping_id>', methods=['DELETE'])
@require_qbo_auth
def delete_mapping(mapping_id):
    """Delete a mapping"""
    try:
        mapping = DBAccountMapping.query.get(mapping_id)

        if not mapping:
            return jsonify({'error': 'Mapping not found'}), 404

        db.session.delete(mapping)
        db.session.commit()

        logger.info(f"Deleted mapping {mapping_id}")

        return jsonify({
            'success': True,
            'message': f'Mapping {mapping_id} deleted'
        })

    except Exception as e:
        logger.error(f"Error deleting mapping {mapping_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/mappings/<int:mapping_id>/toggle', methods=['POST'])
@require_qbo_auth
def toggle_mapping(mapping_id):
    """Toggle a mapping's active status"""
    try:
        mapping = DBAccountMapping.query.get(mapping_id)

        if not mapping:
            return jsonify({'error': 'Mapping not found'}), 404

        mapping.is_active = not mapping.is_active
        db.session.commit()

        logger.info(f"Toggled mapping {mapping_id} to {'active' if mapping.is_active else 'inactive'}")

        return jsonify({
            'success': True,
            'mapping': mapping.to_dict()
        })

    except Exception as e:
        logger.error(f"Error toggling mapping {mapping_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Pattern Testing Endpoints
# =============================================================================

@bp.route('/mappings/test', methods=['POST'])
@require_qbo_auth
def test_pattern():
    """Test a pattern against recent journal entries"""
    from app.services.qbo import qbo_service
    from datetime import datetime, timedelta
    import re

    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        pattern = data.get('pattern', '').strip()
        from_account_id = data.get('from_account_id', '').strip()

        if not pattern:
            return jsonify({'error': 'Pattern is required'}), 400

        if not from_account_id:
            return jsonify({'error': 'From account is required'}), 400

        # Get journals from the last 90 days for testing
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

        # Fetch journals for the specified account
        journals = qbo_service.get_journals_for_pattern_test(from_account_id, start_date)

        # Test pattern against journal descriptions
        matches = []
        pattern_lower = pattern.lower()

        for journal in journals:
            for line in journal.get('lines', []):
                description = line.get('description', '')
                if description and pattern_lower in description.lower():
                    # Find match position for highlighting
                    match_start = description.lower().find(pattern_lower)
                    match_end = match_start + len(pattern)

                    matches.append({
                        'journal_id': journal.get('id'),
                        'journal_date': journal.get('date'),
                        'description': description,
                        'match_start': match_start,
                        'match_end': match_end,
                        'amount': line.get('amount'),
                        'posting_type': line.get('posting_type')
                    })

        logger.debug(f"Pattern '{pattern}' matched {len(matches)} lines")

        return jsonify({
            'success': True,
            'pattern': pattern,
            'matches': matches[:50],  # Limit to 50 results
            'total_matches': len(matches),
            'truncated': len(matches) > 50
        })

    except Exception as e:
        logger.error(f"Error testing pattern: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Import/Export Endpoints
# =============================================================================

@bp.route('/mappings/import', methods=['POST'])
@require_qbo_auth
def import_mappings():
    """Import mappings from JSON array (for migration from .env)"""
    try:
        data = request.json

        if not data or not isinstance(data, list):
            return jsonify({'error': 'Expected JSON array of mappings'}), 400

        imported = 0
        skipped = 0

        for mapping_data in data:
            # Validate required fields
            if not all(k in mapping_data for k in ['pattern', 'from_account_id', 'to_account_id']):
                skipped += 1
                continue

            # Check for existing
            existing = DBAccountMapping.query.filter_by(
                pattern=mapping_data['pattern'],
                from_account_id=mapping_data['from_account_id']
            ).first()

            if existing:
                skipped += 1
                continue

            # Create new mapping
            mapping = DBAccountMapping(
                pattern=mapping_data['pattern'],
                from_account_id=mapping_data['from_account_id'],
                from_account_name=mapping_data.get('from_account_name'),
                to_account_id=mapping_data['to_account_id'],
                to_account_name=mapping_data.get('to_account_name'),
                is_active=mapping_data.get('is_active', True)
            )
            db.session.add(mapping)
            imported += 1

        db.session.commit()

        logger.info(f"Imported {imported} mappings, skipped {skipped}")

        return jsonify({
            'success': True,
            'imported': imported,
            'skipped': skipped
        })

    except Exception as e:
        logger.error(f"Error importing mappings: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/mappings/export', methods=['GET'])
@require_qbo_auth
def export_mappings():
    """Export all mappings as JSON array"""
    try:
        mappings = DBAccountMapping.query.all()

        export_data = [{
            'pattern': m.pattern,
            'from_account_id': m.from_account_id,
            'from_account_name': m.from_account_name,
            'to_account_id': m.to_account_id,
            'to_account_name': m.to_account_name,
            'is_active': m.is_active
        } for m in mappings]

        return jsonify(export_data)

    except Exception as e:
        logger.error(f"Error exporting mappings: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# History Endpoints
# =============================================================================

@bp.route('/history', methods=['GET'])
@require_qbo_auth
def list_history():
    """Get update history with optional filtering"""
    from app.models.update_history import UpdateHistory

    try:
        # Get optional query parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        journal_id = request.args.get('journal_id')

        # Build query
        query = UpdateHistory.query.order_by(UpdateHistory.updated_at.desc())

        if journal_id:
            query = query.filter_by(journal_id=journal_id)

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        history = query.offset(offset).limit(limit).all()

        return jsonify({
            'success': True,
            'history': [h.to_dict() for h in history],
            'total': total,
            'limit': limit,
            'offset': offset
        })

    except Exception as e:
        logger.error(f"Error listing history: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/history/stats', methods=['GET'])
@require_qbo_auth
def history_stats():
    """Get update history statistics"""
    from app.models.update_history import UpdateHistory
    from sqlalchemy import func

    try:
        # Get total updates
        total_updates = UpdateHistory.query.count()

        # Get updates by account
        updates_by_account = db.session.query(
            UpdateHistory.to_account_name,
            func.count(UpdateHistory.id).label('count')
        ).group_by(UpdateHistory.to_account_name).all()

        return jsonify({
            'success': True,
            'total_updates': total_updates,
            'updates_by_account': [
                {'account': acc, 'count': cnt}
                for acc, cnt in updates_by_account if acc
            ]
        })

    except Exception as e:
        logger.error(f"Error getting history stats: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# System Status Endpoints
# =============================================================================

@bp.route('/status', methods=['GET'])
def system_status():
    """Get system status including encryption status"""
    from app.models.qbo_connection import QBOConnection
    from flask import current_app

    try:
        # Check QBO connection and encryption
        connection = QBOConnection.query.first()

        qbo_status = {
            'connected': False,
            'tokens_encrypted': False
        }

        if connection:
            qbo_status['connected'] = True
            qbo_status['tokens_encrypted'] = connection.tokens_encrypted

        # Check if encryption key is configured (not auto-generated)
        import os
        encryption_key_set = bool(os.getenv('ENCRYPTION_KEY'))

        return jsonify({
            'success': True,
            'status': {
                'qbo_connection': qbo_status,
                'encryption': {
                    'key_configured': encryption_key_set,
                    'tokens_encrypted': qbo_status['tokens_encrypted']
                }
            }
        })

    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({'error': str(e)}), 500

