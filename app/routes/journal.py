# File: app/routes/journal.py
"""
/app/routes/journal.py
Journal entry routes and views
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.services.qbo import qbo_service
from app.utils.decorators import require_qbo_auth
from datetime import datetime, timedelta

bp = Blueprint('journal', __name__)

@bp.route('/')
@require_qbo_auth
def index():
    return redirect(url_for('journal.list_journals'))

@bp.route('/journals')
@require_qbo_auth
def list_journals():
    try:
        accounts = qbo_service.get_accounts()  # Add this line
        account_id = request.args.get('account_id')

        # Get date from query params or default to first day of last month
        today = datetime.today()
        first_day_last_month = today.replace(day=1) - timedelta(days=1)
        first_day_last_month = first_day_last_month.replace(day=1)
        
        start_date = request.args.get('start_date', 
            first_day_last_month.strftime('%Y-%m-%d'))

        print(f"Account ID: {account_id}")  # Debug print
        if not account_id:
            return render_template('journal_list.html', journals=[], accounts=accounts, start_date=start_date)
        
        journals = qbo_service.get_journals_by_account(account_id, start_date)
        return render_template('journal_list.html', journals=journals, accounts=accounts, start_date=start_date)
    except Exception as e:
        return render_template('journal_list.html', journals=[], accounts=[], error=str(e), start_date=start_date)

@bp.route('/journals/update', methods=['POST'])
def update_journals():
    try:
        data = request.json
        journal_ids = data.get('journals', [])
        
        if not journal_ids:
            return jsonify({"error": "No journals provided"}), 400
            
        # Get updates from service
        results = qbo_service.update_journals_accounts(journal_ids)
        
        return jsonify({
            "success": True,
            "updated": results
        })
    except Exception as e:
        print(f"Error updating journals: {str(e)}")
        return jsonify({"error": str(e)}), 500
