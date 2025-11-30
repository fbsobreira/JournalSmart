# File: app/routes/journal.py
"""
/app/routes/journal.py
Journal entry routes and views
"""

import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.services.qbo import qbo_service
from app.utils.decorators import require_qbo_auth
from datetime import datetime, timedelta

bp = Blueprint("journal", __name__)
logger = logging.getLogger(__name__)


@bp.route("/")
@require_qbo_auth
def index():
    """Redirect to journal list"""
    return redirect(url_for("journal.list_journals"))


@bp.route("/journals")
@require_qbo_auth
def list_journals():
    """List journal entries with proposed changes"""
    # Calculate default date first (before try block)
    today = datetime.today()
    first_day_last_month = today.replace(day=1) - timedelta(days=1)
    first_day_last_month = first_day_last_month.replace(day=1)
    default_start_date = first_day_last_month.strftime("%Y-%m-%d")

    try:
        accounts = qbo_service.get_accounts()
        account_id = request.args.get("account_id")
        start_date = request.args.get("start_date", default_start_date)

        logger.debug(
            f"Listing journals - Account ID: {account_id}, Start Date: {start_date}"
        )

        if not account_id:
            return render_template(
                "journal_list.html",
                journals=[],
                accounts=accounts,
                start_date=start_date,
            )

        journals = qbo_service.get_journals_by_account(account_id, start_date)

        return render_template(
            "journal_list.html",
            journals=journals,
            accounts=accounts,
            start_date=start_date,
        )

    except Exception as e:
        logger.error(f"Error listing journals: {str(e)}")
        return render_template(
            "journal_list.html",
            journals=[],
            accounts=[],
            error=str(e),
            start_date=default_start_date,
        )


@bp.route("/journals/update", methods=["POST"])
@require_qbo_auth
def update_journals():
    """Update journal entries with new account mappings"""
    try:
        data = request.json

        if not data:
            logger.warning("Update journals called with no JSON data")
            return jsonify({"error": "No data provided"}), 400

        journal_ids = data.get("journals", [])

        if not journal_ids:
            logger.warning("Update journals called with empty journal list")
            return jsonify({"error": "No journals provided"}), 400

        # Validate journal_ids are strings/integers (basic sanitization)
        validated_ids = []
        for jid in journal_ids:
            if isinstance(jid, (str, int)):
                validated_ids.append(str(jid))
            else:
                logger.warning(f"Invalid journal ID type: {type(jid)}")

        if not validated_ids:
            return jsonify({"error": "No valid journal IDs provided"}), 400

        logger.info(f"Updating {len(validated_ids)} journals")

        # Get updates from service
        results = qbo_service.update_journals_accounts(validated_ids)

        logger.info(f"Successfully updated {len(results)} journal entries")

        return jsonify({"success": True, "updated": results})

    except Exception as e:
        logger.error(f"Error updating journals: {str(e)}")
        return jsonify({"error": str(e)}), 500
