# File: app/routes/auth.py
"""
/app/routes/auth.py
QuickBooks OAuth authentication routes
"""
from flask import Blueprint, redirect, url_for, session, request
from app.services.qbo import qbo_service
from intuitlib.enums import Scopes

bp = Blueprint('auth', __name__)

@bp.route('/auth')
def auth():
    # Define required scopes for QuickBooks API access
    scopes = [
        Scopes.ACCOUNTING
    ]

    # Generate authorization URL
    auth_url = qbo_service.auth_client.get_authorization_url(scopes)
    return redirect(auth_url)

@bp.route('/callback')
def callback():
    # Get authorization code from callback
    auth_code = request.args.get('code')
    realm_id = request.args.get('realmId')
    print(f"Args: {request.args}")
    intuit_tid = request.args.get('intuit_tid')  

    print(f"Auth Code: {auth_code}")
    print(f"Realm ID: {realm_id}")
    print(f"Intuit TID: {intuit_tid}")
    session['intuit_tid'] = intuit_tid
    
    # Exchange authorization code for tokens
    qbo_service.auth_client.get_bearer_token(auth_code, realm_id=realm_id)
    qbo_service.auth_client.realm_id = realm_id
    
    return redirect(url_for('journal.list_journals'))