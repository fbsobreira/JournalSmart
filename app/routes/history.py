# File: app/routes/history.py
"""
/app/routes/history.py
Routes for viewing update history
"""
import logging
from flask import Blueprint, render_template, request, jsonify
from app.utils.decorators import require_qbo_auth
from app.models.update_history import UpdateHistory
from app.extensions import db
from sqlalchemy import func

bp = Blueprint('history', __name__, url_prefix='/history')
logger = logging.getLogger(__name__)


@bp.route('/')
@require_qbo_auth
def view_history():
    """Render the history page"""
    return render_template('history.html')


@bp.route('/data')
@require_qbo_auth
def get_history_data():
    """Get history data with filtering and pagination"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        journal_id = request.args.get('journal_id', '').strip()
        from_date = request.args.get('from_date', '').strip()
        to_date = request.args.get('to_date', '').strip()

        # Build query
        query = UpdateHistory.query.order_by(UpdateHistory.updated_at.desc())

        # Apply filters
        if journal_id:
            query = query.filter(UpdateHistory.journal_id == journal_id)

        if from_date:
            query = query.filter(UpdateHistory.journal_date >= from_date)

        if to_date:
            query = query.filter(UpdateHistory.journal_date <= to_date)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * per_page
        history = query.offset(offset).limit(per_page).all()

        return jsonify({
            'success': True,
            'history': [h.to_dict() for h in history],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })

    except Exception as e:
        logger.error(f"Error getting history data: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/stats')
@require_qbo_auth
def get_stats():
    """Get history statistics for dashboard"""
    try:
        # Total updates
        total_updates = UpdateHistory.query.count()

        # Updates this month
        from datetime import datetime, timedelta
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        updates_this_month = UpdateHistory.query.filter(
            UpdateHistory.updated_at >= month_start
        ).count()

        # Updates by destination account (top 5)
        updates_by_account = db.session.query(
            UpdateHistory.to_account_name,
            func.count(UpdateHistory.id).label('count')
        ).group_by(UpdateHistory.to_account_name).order_by(
            func.count(UpdateHistory.id).desc()
        ).limit(5).all()

        # Recent activity (last 7 days by day)
        week_ago = datetime.now() - timedelta(days=7)
        daily_updates = db.session.query(
            func.date(UpdateHistory.updated_at).label('date'),
            func.count(UpdateHistory.id).label('count')
        ).filter(
            UpdateHistory.updated_at >= week_ago
        ).group_by(
            func.date(UpdateHistory.updated_at)
        ).order_by(
            func.date(UpdateHistory.updated_at)
        ).all()

        return jsonify({
            'success': True,
            'total_updates': total_updates,
            'updates_this_month': updates_this_month,
            'top_accounts': [
                {'account': acc, 'count': cnt}
                for acc, cnt in updates_by_account if acc
            ],
            'daily_updates': [
                {'date': str(d), 'count': c}
                for d, c in daily_updates
            ]
        })

    except Exception as e:
        logger.error(f"Error getting history stats: {str(e)}")
        return jsonify({'error': str(e)}), 500
