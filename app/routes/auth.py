# File: app/routes/auth.py
"""
/app/routes/auth.py
Authentication routes (App password + QuickBooks OAuth)
"""

import logging
from datetime import timedelta
from flask import (
    Blueprint,
    redirect,
    url_for,
    session,
    request,
    render_template,
    current_app,
)
from app.extensions import db
from app.services.qbo import qbo_service
from app.services.token_service import token_service
from app.utils.decorators import require_app_password, require_qbo_auth
from intuitlib.enums import Scopes
from intuitlib.exceptions import AuthClientError

bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


# =============================================================================
# App Password Authentication
# =============================================================================


@bp.route("/login", methods=["GET", "POST"])
def login():
    """App password login page"""
    app_password = current_app.config.get("APP_PASSWORD", "")

    # If no password configured, skip login
    if not app_password:
        return redirect(url_for("journal.list_journals"))

    # Already authenticated
    if session.get("app_authenticated"):
        return redirect(url_for("journal.list_journals"))

    error = None

    if request.method == "POST":
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if password == app_password:
            session["app_authenticated"] = True
            session.permanent = remember

            if remember:
                # Set session to last 30 days
                current_app.permanent_session_lifetime = timedelta(days=30)

            logger.info("App password authentication successful")
            return redirect(url_for("journal.list_journals"))
        else:
            logger.warning("Failed app password attempt")
            error = "Invalid password. Please try again."

    return render_template("login.html", error=error)


@bp.route("/logout")
def logout():
    """Logout - clear app session but preserve QBO connection"""
    # Preserve QBO realm_id so connection stays active
    qbo_realm_id = session.get("qbo_realm_id")

    # Clear session
    session.clear()

    # Restore QBO realm_id if it was set
    if qbo_realm_id:
        session["qbo_realm_id"] = qbo_realm_id

    logger.info("User logged out (QBO connection preserved)")
    return redirect(url_for("auth.login"))


# =============================================================================
# QuickBooks OAuth Authentication
# =============================================================================


@bp.route("/auth")
def qbo_auth():
    """Initiate QuickBooks OAuth flow"""
    try:
        # Define required scopes for QuickBooks API access
        scopes = [Scopes.ACCOUNTING]

        # Generate authorization URL
        auth_url = qbo_service.auth_client.get_authorization_url(scopes)
        logger.info("Redirecting to QuickBooks for OAuth")
        return redirect(auth_url)

    except Exception as e:
        logger.error(f"Error initiating QBO OAuth: {str(e)}")
        return render_template(
            "error.html",
            title="Authentication Error",
            message="Failed to initiate QuickBooks authentication. Please try again.",
            details=str(e) if current_app.debug else None,
        )


@bp.route("/callback")
def callback():
    """Handle QuickBooks OAuth callback"""
    try:
        # Check for error response from QuickBooks
        error = request.args.get("error")
        if error:
            error_description = request.args.get("error_description", "Unknown error")
            logger.error(f"QBO OAuth error: {error} - {error_description}")
            return render_template(
                "error.html",
                title="Authentication Failed",
                message=f"QuickBooks returned an error: {error_description}",
                show_retry=True,
            )

        # Get authorization code from callback
        auth_code = request.args.get("code")
        realm_id = request.args.get("realmId")

        if not auth_code or not realm_id:
            logger.error("Missing auth_code or realm_id in callback")
            return render_template(
                "error.html",
                title="Authentication Failed",
                message="Missing required parameters from QuickBooks.",
                show_retry=True,
            )

        logger.info(f"OAuth callback received for realm: {realm_id}")

        # Exchange authorization code for tokens
        qbo_service.auth_client.get_bearer_token(auth_code, realm_id=realm_id)
        qbo_service.auth_client.realm_id = realm_id

        # Try to fetch company name from QuickBooks
        company_name = None
        try:
            qbo_service.authenticate()
            from quickbooks.objects.company_info import CompanyInfo

            company_info = CompanyInfo.get(realm_id, qb=qbo_service.qb)
            if company_info:
                company_name = company_info.CompanyName
                logger.info(f"Retrieved company name: {company_name}")
        except Exception as e:
            logger.warning(f"Could not fetch company name: {str(e)}")

        # Save tokens to database for persistence (with company name)
        token_service.save_tokens(qbo_service.auth_client, company_name=company_name)

        # Store realm_id in session for reference
        session["qbo_realm_id"] = realm_id

        logger.info("QBO OAuth successful, tokens saved to database")
        return redirect(url_for("journal.list_journals"))

    except AuthClientError as e:
        logger.error(f"QBO AuthClientError: {str(e)}")
        return render_template(
            "error.html",
            title="Authentication Failed",
            message="Failed to authenticate with QuickBooks. The authorization may have expired.",
            details=str(e) if current_app.debug else None,
            show_retry=True,
        )

    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {str(e)}")
        return render_template(
            "error.html",
            title="Authentication Error",
            message="An unexpected error occurred during authentication.",
            details=str(e) if current_app.debug else None,
            show_retry=True,
        )


@bp.route("/disconnect")
@require_app_password
def disconnect():
    """Disconnect QuickBooks (clear QBO tokens, keep app password session)"""
    try:
        # Get realm_id before clearing
        realm_id = session.get("qbo_realm_id") or (
            qbo_service.auth_client.realm_id if qbo_service.auth_client else None
        )

        # Clear QBO-related session data
        session.pop("qbo_realm_id", None)

        # Delete connection from database
        if realm_id:
            token_service.delete_connection(realm_id)

        # Reset QBO service tokens
        if qbo_service.auth_client:
            qbo_service.auth_client.access_token = None
            qbo_service.auth_client.refresh_token = None
            qbo_service.auth_client.realm_id = None

        logger.info("QuickBooks disconnected")

    except Exception as e:
        logger.error(f"Error disconnecting QBO: {str(e)}")

    return redirect(url_for("auth.qbo_auth"))


# =============================================================================
# Company Management API
# =============================================================================


@bp.route("/api/companies")
@require_app_password
def list_companies():
    """
    Get list of all connected QBO companies.

    Uses @require_app_password instead of @require_qbo_auth so users can
    see and switch to other companies even if current connection has expired tokens.
    """
    try:
        connections = token_service.get_all_connections()
        current_realm = (
            qbo_service.auth_client.realm_id if qbo_service.auth_client else None
        )

        companies = []
        for conn in connections:
            companies.append(
                {
                    **conn.to_dict(),
                    "is_current": conn.realm_id == current_realm,
                }
            )

        return {"companies": companies, "current_realm_id": current_realm}

    except Exception as e:
        logger.error(f"Error listing companies: {str(e)}")
        return {"error": str(e)}, 500


@bp.route("/api/companies/current")
@require_qbo_auth
def get_current_company():
    """Get the currently active QBO company (requires valid QBO connection)"""
    try:
        connection = token_service.get_connection()
        if not connection:
            return {"company": None}

        return {
            "company": {
                **connection.to_dict(),
                "is_current": True,
            }
        }

    except Exception as e:
        logger.error(f"Error getting current company: {str(e)}")
        return {"error": str(e)}, 500


@bp.route("/api/companies/switch", methods=["POST"])
@require_app_password
def switch_company():
    """
    Switch to a different QBO company.

    Uses @require_app_password instead of @require_qbo_auth so users can
    switch away from a company with expired tokens. CSRF protected.
    """
    try:
        data = request.get_json()
        if not data or "realm_id" not in data:
            return {"error": "realm_id is required"}, 400

        realm_id = data["realm_id"]
        connection = token_service.switch_connection(realm_id, qbo_service.auth_client)

        if not connection:
            return {"error": f"Company with realm_id {realm_id} not found"}, 404

        # Update session
        session["qbo_realm_id"] = realm_id

        # Reset the QBO client so it re-authenticates with new tokens
        qbo_service.qb = None

        # Check if tokens need refresh
        token_service.refresh_tokens_if_needed(qbo_service.auth_client, qbo_service)

        return {
            "success": True,
            "company": {
                **connection.to_dict(),
                "is_current": True,
            },
        }

    except Exception as e:
        logger.error(f"Error switching company: {str(e)}")
        return {"error": str(e)}, 500


@bp.route("/api/companies/refresh-name", methods=["POST"])
@require_qbo_auth
def refresh_company_name():
    """
    Refresh the company name from QuickBooks for the current connection.
    Useful when company_name is missing or outdated.
    """
    try:
        connection = token_service.get_connection()
        if not connection:
            return {"error": "No active connection"}, 404

        # Fetch company name from QuickBooks
        qbo_service.authenticate()
        from quickbooks.objects.company_info import CompanyInfo

        company_info = CompanyInfo.get(connection.realm_id, qb=qbo_service.qb)
        if company_info and company_info.CompanyName:
            connection.company_name = company_info.CompanyName
            db.session.commit()
            logger.info(f"Updated company name to: {company_info.CompanyName}")
            return {
                "success": True,
                "company_name": company_info.CompanyName,
            }
        else:
            return {"error": "Could not fetch company name from QuickBooks"}, 500

    except Exception as e:
        logger.error(f"Error refreshing company name: {str(e)}")
        db.session.rollback()
        return {"error": str(e)}, 500


@bp.route("/api/companies/<realm_id>", methods=["DELETE"])
@require_app_password
def delete_company(realm_id):
    """
    Delete a specific QBO company connection.

    Uses @require_app_password instead of @require_qbo_auth so users can
    delete companies with expired tokens. CSRF protected.
    """
    try:
        current_realm = (
            qbo_service.auth_client.realm_id if qbo_service.auth_client else None
        )

        # Don't allow deleting the current active company
        if realm_id == current_realm:
            return {
                "error": "Cannot delete the currently active company. Switch to another company first."
            }, 400

        success = token_service.delete_connection(realm_id)
        if not success:
            return {"error": f"Company with realm_id {realm_id} not found"}, 404

        return {"success": True, "message": f"Company {realm_id} disconnected"}

    except Exception as e:
        logger.error(f"Error deleting company: {str(e)}")
        return {"error": str(e)}, 500
