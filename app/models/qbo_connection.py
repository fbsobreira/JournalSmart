# File: app/models/qbo_connection.py
"""
/app/models/qbo_connection.py
QuickBooks Online connection model for storing OAuth tokens
"""
from datetime import datetime
from app.extensions import db
from app.utils.encryption import encrypt_token, decrypt_token, is_encrypted


class QBOConnection(db.Model):
    """Stores QuickBooks OAuth connection details with encrypted tokens"""
    __tablename__ = 'qbo_connections'

    id = db.Column(db.Integer, primary_key=True)
    realm_id = db.Column(db.String(50), unique=True, nullable=False)
    company_name = db.Column(db.String(200))

    # Tokens stored encrypted - use properties for access
    _access_token = db.Column('access_token', db.Text, nullable=False)
    _refresh_token = db.Column('refresh_token', db.Text, nullable=False)

    token_expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def access_token(self) -> str:
        """Decrypt and return the access token"""
        return decrypt_token(self._access_token)

    @access_token.setter
    def access_token(self, value: str):
        """Encrypt and store the access token"""
        self._access_token = encrypt_token(value)

    @property
    def refresh_token(self) -> str:
        """Decrypt and return the refresh token"""
        return decrypt_token(self._refresh_token)

    @refresh_token.setter
    def refresh_token(self, value: str):
        """Encrypt and store the refresh token"""
        self._refresh_token = encrypt_token(value)

    @property
    def tokens_encrypted(self) -> bool:
        """Check if tokens are currently encrypted"""
        return (
            is_encrypted(self._access_token) if self._access_token else False
        )

    def __repr__(self):
        return f'<QBOConnection {self.realm_id}: {self.company_name}>'

    def is_token_expired(self) -> bool:
        """Check if the access token is expired"""
        if not self.token_expires_at:
            return True
        return datetime.utcnow() >= self.token_expires_at

    def to_dict(self):
        """Convert to dictionary (excludes sensitive tokens)"""
        return {
            'id': self.id,
            'realm_id': self.realm_id,
            'company_name': self.company_name,
            'token_expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'tokens_encrypted': self.tokens_encrypted
        }
