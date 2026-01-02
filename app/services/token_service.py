# File: app/services/token_service.py
"""
/app/services/token_service.py
Token persistence and management service
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.extensions import db
from app.models.qbo_connection import QBOConnection
from app.utils.encryption import encrypt_token, is_encrypted

logger = logging.getLogger(__name__)


class TokenService:
    """Service for managing QBO OAuth tokens in the database"""

    @staticmethod
    def save_tokens(auth_client, company_name: str = None) -> Optional[QBOConnection]:
        """
        Save OAuth tokens to the database after successful authentication.

        Args:
            auth_client: The IntuitLib AuthClient with tokens
            company_name: Optional company name from QBO

        Returns:
            QBOConnection object or None on error
        """
        try:
            realm_id = auth_client.realm_id
            if not realm_id:
                logger.error("Cannot save tokens: realm_id is missing")
                return None

            # Calculate token expiration (access tokens typically expire in 1 hour)
            # IntuitLib provides expires_in as seconds
            expires_in = getattr(auth_client, "expires_in", 3600)
            token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=expires_in
            )

            # Check if connection already exists
            connection = QBOConnection.query.filter_by(realm_id=realm_id).first()

            if connection:
                # Update existing connection
                connection.access_token = auth_client.access_token
                connection.refresh_token = auth_client.refresh_token
                connection.token_expires_at = token_expires_at
                connection.updated_at = datetime.now(timezone.utc)
                if company_name:
                    connection.company_name = company_name
                logger.info(f"Updated tokens for realm {realm_id}")
            else:
                # Create new connection
                connection = QBOConnection(
                    realm_id=realm_id,
                    company_name=company_name,
                    access_token=auth_client.access_token,
                    refresh_token=auth_client.refresh_token,
                    token_expires_at=token_expires_at,
                )
                db.session.add(connection)
                logger.info(f"Created new connection for realm {realm_id}")

            db.session.commit()
            return connection

        except Exception as e:
            logger.error(f"Error saving tokens: {str(e)}")
            db.session.rollback()
            return None

    @staticmethod
    def load_tokens(auth_client) -> Optional[QBOConnection]:
        """
        Load saved tokens from the database and apply to auth_client.
        Returns the most recent connection.

        Args:
            auth_client: The IntuitLib AuthClient to populate with tokens

        Returns:
            QBOConnection object or None if no saved connection
        """
        try:
            # Get the most recent connection
            connection = QBOConnection.query.order_by(
                QBOConnection.updated_at.desc()
            ).first()

            if not connection:
                logger.debug("No saved QBO connection found")
                return None

            # Apply tokens to auth_client
            auth_client.access_token = connection.access_token
            auth_client.refresh_token = connection.refresh_token
            auth_client.realm_id = connection.realm_id

            logger.info(f"Loaded tokens for realm {connection.realm_id}")
            return connection

        except Exception as e:
            logger.error(f"Error loading tokens: {str(e)}")
            return None

    @staticmethod
    def refresh_tokens_if_needed(auth_client, qbo_service) -> bool:
        """
        Check if tokens need refresh and refresh them if so.

        Args:
            auth_client: The IntuitLib AuthClient
            qbo_service: The QBO service instance

        Returns:
            True if tokens are valid (refreshed or still valid), False on error
        """
        try:
            if not auth_client.refresh_token:
                logger.warning("No refresh token available")
                return False

            # Get the connection to check expiration
            connection = QBOConnection.query.filter_by(
                realm_id=auth_client.realm_id
            ).first()

            if not connection:
                logger.warning("No connection found for refresh check")
                return False

            # Check if token is expired or will expire in next 5 minutes
            buffer = timedelta(minutes=5)
            now = datetime.now(timezone.utc)

            # Handle naive datetime from database
            expires_at = connection.token_expires_at
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at and now < (expires_at - buffer):
                logger.debug("Tokens still valid, no refresh needed")
                return True

            # Refresh the tokens
            logger.info("Access token expired or expiring soon, refreshing...")
            auth_client.refresh()

            # Save the new tokens
            TokenService.save_tokens(auth_client, connection.company_name)

            # Re-initialize the QBO client with new tokens (avoid recursive authenticate call)
            if qbo_service.qb:
                from quickbooks import QuickBooks

                qbo_service.qb = QuickBooks(
                    auth_client=auth_client,
                    refresh_token=auth_client.refresh_token,
                    company_id=auth_client.realm_id,
                    minorversion=65,
                )

            logger.info("Tokens refreshed successfully")
            return True

        except Exception as e:
            error_str = str(e)
            logger.error(f"Error refreshing tokens: {error_str}")

            # If refresh fails due to invalid/expired refresh token, clear tokens
            # so user gets redirected to re-authenticate
            if (
                "401" in error_str
                or "invalid_grant" in error_str.lower()
                or "expired" in error_str.lower()
            ):
                logger.warning(
                    "Refresh token invalid/expired - clearing tokens for re-auth"
                )
                auth_client.access_token = None
                auth_client.refresh_token = None

            return False

    @staticmethod
    def delete_connection(realm_id: str) -> bool:
        """
        Delete a QBO connection from the database.

        Args:
            realm_id: The QuickBooks realm ID to delete

        Returns:
            True if deleted, False on error
        """
        try:
            connection = QBOConnection.query.filter_by(realm_id=realm_id).first()
            if connection:
                db.session.delete(connection)
                db.session.commit()
                logger.info(f"Deleted connection for realm {realm_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting connection: {str(e)}")
            db.session.rollback()
            return False

    @staticmethod
    def get_connection() -> Optional[QBOConnection]:
        """
        Get the current QBO connection.

        Returns:
            QBOConnection object or None
        """
        try:
            return QBOConnection.query.order_by(QBOConnection.updated_at.desc()).first()
        except Exception as e:
            logger.error(f"Error getting connection: {str(e)}")
            return None

    @staticmethod
    def get_all_connections() -> list:
        """
        Get all QBO connections.

        Returns:
            List of QBOConnection objects
        """
        try:
            return QBOConnection.query.order_by(QBOConnection.updated_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting all connections: {str(e)}")
            return []

    @staticmethod
    def get_connection_by_realm(realm_id: str) -> Optional[QBOConnection]:
        """
        Get a specific QBO connection by realm ID.

        Args:
            realm_id: The QuickBooks realm ID

        Returns:
            QBOConnection object or None
        """
        try:
            return QBOConnection.query.filter_by(realm_id=realm_id).first()
        except Exception as e:
            logger.error(f"Error getting connection for realm {realm_id}: {str(e)}")
            return None

    @staticmethod
    def switch_connection(realm_id: str, auth_client) -> Optional[QBOConnection]:
        """
        Switch to a different QBO company connection.

        Args:
            realm_id: The QuickBooks realm ID to switch to
            auth_client: The IntuitLib AuthClient to update

        Returns:
            QBOConnection object or None if not found
        """
        try:
            connection = QBOConnection.query.filter_by(realm_id=realm_id).first()
            if not connection:
                logger.warning(f"No connection found for realm {realm_id}")
                return None

            # Update the auth_client with the new connection's tokens
            auth_client.access_token = connection.access_token
            auth_client.refresh_token = connection.refresh_token
            auth_client.realm_id = connection.realm_id

            # Update the connection's updated_at to make it the "current" one
            from datetime import datetime, timezone

            connection.updated_at = datetime.now(timezone.utc)
            db.session.commit()

            logger.info(f"Switched to company: {connection.company_name} ({realm_id})")
            return connection

        except Exception as e:
            logger.error(f"Error switching connection to realm {realm_id}: {str(e)}")
            db.session.rollback()
            return None

    @staticmethod
    def migrate_to_encrypted_tokens() -> int:
        """
        Migrate any existing plain text tokens to encrypted format.
        Safe to run multiple times - only encrypts unencrypted tokens.

        Returns:
            Number of connections migrated
        """
        migrated = 0
        try:
            connections = QBOConnection.query.all()

            for conn in connections:
                needs_migration = False

                # Check if access token needs encryption
                if conn._access_token and not is_encrypted(conn._access_token):
                    logger.info(f"Encrypting access token for realm {conn.realm_id}")
                    # Store plain text temporarily
                    plain_access = conn._access_token
                    # Encrypt via setter
                    conn._access_token = encrypt_token(plain_access)
                    needs_migration = True

                # Check if refresh token needs encryption
                if conn._refresh_token and not is_encrypted(conn._refresh_token):
                    logger.info(f"Encrypting refresh token for realm {conn.realm_id}")
                    plain_refresh = conn._refresh_token
                    conn._refresh_token = encrypt_token(plain_refresh)
                    needs_migration = True

                if needs_migration:
                    migrated += 1

            if migrated > 0:
                db.session.commit()
                logger.info(f"Migrated {migrated} connection(s) to encrypted tokens")

            return migrated

        except Exception as e:
            logger.error(f"Error migrating tokens: {str(e)}")
            db.session.rollback()
            return 0


# Module-level singleton
token_service = TokenService()
