# File: app/routes/auth.py
"""
/app/routes/auth.py
Authentication routes (App password + QuickBooks OAuth)
"""
import logging
from datetime import timedelta
from flask import Blueprint, redirect, url_for, session, request, render_template, current_app
from app.services.qbo import qbo_service
from app.services.token_service import token_service
from intuitlib.enums import Scopes
from intuitlib.exceptions import AuthClientError

bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


# =============================================================================
# App Password Authentication
# =============================================================================

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """App password login page"""
    app_password = current_app.config.get('APP_PASSWORD', '')

    # If no password configured, skip login
    if not app_password:
        return redirect(url_for('journal.list_journals'))

    # Already authenticated
    if session.get('app_authenticated'):
        return redirect(url_for('journal.list_journals'))

    error = None

    if request.method == 'POST':
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        if password == app_password:
            session['app_authenticated'] = True
            session.permanent = remember

            if remember:
                # Set session to last 30 days
                current_app.permanent_session_lifetime = timedelta(days=30)

            logger.info("App password authentication successful")
            return redirect(url_for('journal.list_journals'))
        else:
            logger.warning("Failed app password attempt")
            error = "Invalid password. Please try again."

    return render_template('login.html', error=error)


@bp.route('/logout')
def logout():
    """Logout - clear all session data"""
    session.clear()
    logger.info("User logged out")
    return redirect(url_for('auth.login'))


# =============================================================================
# QuickBooks OAuth Authentication
# =============================================================================

@bp.route('/auth')
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
        return render_template('error.html',
                               title="Authentication Error",
                               message="Failed to initiate QuickBooks authentication. Please try again.",
                               details=str(e) if current_app.debug else None)


@bp.route('/callback')
def callback():
    """Handle QuickBooks OAuth callback"""
    try:
        # Check for error response from QuickBooks
        error = request.args.get('error')
        if error:
            error_description = request.args.get('error_description', 'Unknown error')
            logger.error(f"QBO OAuth error: {error} - {error_description}")
            return render_template('error.html',
                                   title="Authentication Failed",
                                   message=f"QuickBooks returned an error: {error_description}",
                                   show_retry=True)

        # Get authorization code from callback
        auth_code = request.args.get('code')
        realm_id = request.args.get('realmId')

        if not auth_code or not realm_id:
            logger.error("Missing auth_code or realm_id in callback")
            return render_template('error.html',
                                   title="Authentication Failed",
                                   message="Missing required parameters from QuickBooks.",
                                   show_retry=True)

        logger.info(f"OAuth callback received for realm: {realm_id}")

        # Exchange authorization code for tokens
        qbo_service.auth_client.get_bearer_token(auth_code, realm_id=realm_id)
        qbo_service.auth_client.realm_id = realm_id

        # Save tokens to database for persistence
        token_service.save_tokens(qbo_service.auth_client)

        # Store realm_id in session for reference
        session['qbo_realm_id'] = realm_id

        logger.info("QBO OAuth successful, tokens saved to database")
        return redirect(url_for('journal.list_journals'))

    except AuthClientError as e:
        logger.error(f"QBO AuthClientError: {str(e)}")
        return render_template('error.html',
                               title="Authentication Failed",
                               message="Failed to authenticate with QuickBooks. The authorization may have expired.",
                               details=str(e) if current_app.debug else None,
                               show_retry=True)

    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {str(e)}")
        return render_template('error.html',
                               title="Authentication Error",
                               message="An unexpected error occurred during authentication.",
                               details=str(e) if current_app.debug else None,
                               show_retry=True)


@bp.route('/disconnect')
def disconnect():
    """Disconnect QuickBooks (clear QBO tokens, keep app password session)"""
    try:
        # Get realm_id before clearing
        realm_id = session.get('qbo_realm_id') or (
            qbo_service.auth_client.realm_id if qbo_service.auth_client else None
        )

        # Clear QBO-related session data
        session.pop('qbo_realm_id', None)

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

    return redirect(url_for('auth.qbo_auth'))
