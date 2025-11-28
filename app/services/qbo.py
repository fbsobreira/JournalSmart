# File: app/services/qbo.py
"""
/app/services/qbo.py
QuickBooks Online API integration service
"""
import re
import logging
import traceback
from datetime import datetime
from typing import Optional, List, Dict, Any

from quickbooks import QuickBooks
from quickbooks.objects.journalentry import JournalEntry
from quickbooks.objects.account import Account
from intuitlib.client import AuthClient

from app.models.account_mapping import AccountMapping
from config import Config

logger = logging.getLogger(__name__)


class QBOService:
    def __init__(self, app=None):
        self.client = None
        self.auth_client = None
        self.qb = None
        # Account cache
        self._account_cache: Dict[str, Any] = {}
        self._cache_timeout = 3600  # 1 hour in seconds
        self._last_cache_update: Dict[str, datetime] = {}

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the QBO service with Flask app config"""
        self.auth_client = AuthClient(
            client_id=app.config['QBO_CLIENT_ID'],
            client_secret=app.config['QBO_CLIENT_SECRET'],
            redirect_uri=app.config['QBO_REDIRECT_URI'],
            environment=app.config['QBO_ENVIRONMENT']
        )
        logger.info("QBO AuthClient initialized")

        # Try to load saved tokens from database
        with app.app_context():
            from app.services.token_service import token_service
            connection = token_service.load_tokens(self.auth_client)
            if connection:
                logger.info(f"Loaded saved tokens for company: {connection.company_name or connection.realm_id}")

    def authenticate(self):
        """Initialize QuickBooks client with OAuth tokens"""
        if not self.auth_client.access_token:
            raise Exception("No access token available. Please authenticate first.")

        # Check if tokens need refresh before authenticating
        from app.services.token_service import token_service
        token_service.refresh_tokens_if_needed(self.auth_client, self)

        self.qb = QuickBooks(
            auth_client=self.auth_client,
            refresh_token=self.auth_client.refresh_token,
            company_id=self.auth_client.realm_id,
            minorversion=65
        )
        logger.debug("QuickBooks client authenticated")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _format_account(self, account) -> Dict[str, Any]:
        """
        Format a QuickBooks Account object into a dictionary.
        Single source of truth for account formatting.
        """
        return {
            "id": account.Id,
            "name": getattr(account, 'FullyQualifiedName', None) or account.Name,
            "account_type": account.AccountType,
            "account_subtype": getattr(account, 'AccountSubType', ''),
            "parent_id": account.ParentRef.value if hasattr(account, 'ParentRef') and account.ParentRef else None,
            "is_sub_account": hasattr(account, 'ParentRef') and account.ParentRef is not None,
            "balance": getattr(account, 'CurrentBalance', 0)
        }

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self._last_cache_update:
            return False

        now = datetime.now()
        time_diff = (now - self._last_cache_update[key]).total_seconds()
        return time_diff < self._cache_timeout

    def _sanitize_id(self, value: str) -> Optional[str]:
        """
        Sanitize an ID value to prevent injection.
        QuickBooks IDs are numeric strings.
        """
        if value is None:
            return None

        # Convert to string and strip whitespace
        value = str(value).strip()

        # QuickBooks IDs should only contain digits
        if not re.match(r'^\d+$', value):
            logger.warning(f"Invalid ID format rejected: {value}")
            return None

        return value

    # =========================================================================
    # Account Methods
    # =========================================================================

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Fetch all active accounts"""
        if not self.qb:
            self.authenticate()

        try:
            accounts = Account.where("Active = true", qb=self.qb)
            logger.debug(f"Fetched {len(accounts)} accounts from QuickBooks")

            return [self._format_account(account) for account in accounts]

        except Exception as e:
            logger.error(f"Error fetching accounts: {str(e)}")
            return []

    def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Fetch account by ID with caching"""
        # Sanitize the account_id
        safe_id = self._sanitize_id(account_id)
        if not safe_id:
            logger.error(f"Invalid account_id provided: {account_id}")
            return None

        if not self.qb:
            self.authenticate()

        try:
            # Check cache first
            cache_key = f"account_{safe_id}"
            if cache_key in self._account_cache and self._is_cache_valid(cache_key):
                logger.debug(f"Cache hit for account {safe_id}")
                return self._account_cache[cache_key]

            logger.debug(f"Cache miss for account {safe_id}, fetching from QuickBooks")

            # Use Account.get() which is safer than building WHERE clause
            account = Account.get(safe_id, qb=self.qb)

            if not account:
                return None

            # Format and cache
            account_data = self._format_account(account)
            self._account_cache[cache_key] = account_data
            self._last_cache_update[cache_key] = datetime.now()

            return account_data

        except Exception as e:
            logger.error(f"Error fetching account {safe_id}: {str(e)}")
            return None

    # =========================================================================
    # Journal Methods
    # =========================================================================

    def get_account_mappings(self) -> List[AccountMapping]:
        """
        Get account mappings from database.
        Falls back to .env configuration if database has no mappings.
        """
        from app.models.db_account_mapping import DBAccountMapping

        try:
            # Try to get mappings from database first
            db_mappings = DBAccountMapping.get_active_mappings()

            if db_mappings:
                logger.debug(f"Loaded {len(db_mappings)} mappings from database")
                return [
                    AccountMapping(
                        pattern=m.pattern,
                        from_account_id=m.from_account_id,
                        to_account_id=m.to_account_id
                    ) for m in db_mappings
                ]
        except Exception as e:
            logger.warning(f"Could not load mappings from database: {str(e)}")

        # Fall back to .env configuration
        raw_mappings = Config.get_account_mappings()
        logger.debug(f"Loaded {len(raw_mappings)} mappings from .env")

        return [
            AccountMapping(
                pattern=mapping['pattern'],
                from_account_id=mapping['from_account_id'],
                to_account_id=mapping['to_account_id']
            ) for mapping in raw_mappings
        ]

    def get_journals_by_account(self, account_id: str, start_date: str) -> List[Dict[str, Any]]:
        """Fetch journal entries filtered by account"""
        # Sanitize account_id
        safe_account_id = self._sanitize_id(account_id)
        if not safe_account_id:
            logger.error(f"Invalid account_id for journal query: {account_id}")
            return []

        if not self.qb:
            self.authenticate()

        try:
            # Query journals by date (QB API doesn't support line item filtering)
            query = f"select * from JournalEntry where TxnDate >= '{start_date}' MAXRESULTS 1000"
            journals = JournalEntry.query(query, qb=self.qb)

            logger.debug(f"Query executed: {query}")
            logger.debug(f"Total journals found before filtering: {len(journals)}")

            # Get account mappings
            account_mappings = self.get_account_mappings()

            # Filter journals that have lines with the selected account
            filtered_journals = []
            for journal in journals:
                for line in journal.Line:
                    if (hasattr(line, 'JournalEntryLineDetail') and
                        hasattr(line.JournalEntryLineDetail, 'AccountRef') and
                        line.JournalEntryLineDetail.AccountRef.value == safe_account_id):
                        filtered_journals.append(journal)
                        break

            logger.debug(f"Journals found with account {safe_account_id}: {len(filtered_journals)}")

            # Format journals with mappings
            formatted_journals = []
            for journal in filtered_journals:
                formatted_journal = self._format_journal(
                    journal=journal,
                    account_mappings=account_mappings,
                    selected_account_id=safe_account_id
                )
                if formatted_journal:
                    formatted_journals.append(formatted_journal)

            logger.info(f"Journals with changes: {len(formatted_journals)}")
            return formatted_journals

        except Exception as e:
            logger.error(f"Error fetching journals: {str(e)}")
            logger.debug(traceback.format_exc())
            return []

    def _format_journal(self, journal, account_mappings: List[AccountMapping],
                        selected_account_id: str) -> Optional[Dict[str, Any]]:
        """Format journal entry for API response"""
        try:
            formatted_journal = {
                "id": journal.Id,
                "date": getattr(journal, 'TxnDate', ''),
                "lines": [],
                "has_changes": False
            }

            for line in journal.Line:
                # Only process lines with the selected account
                if line.JournalEntryLineDetail.AccountRef.value != selected_account_id:
                    continue

                description = line.Description or ''
                account_ref = line.JournalEntryLineDetail.AccountRef

                # Look for matching pattern
                proposed_account = None
                for mapping in account_mappings:
                    if (mapping.from_account_id == account_ref.value and
                            mapping.matches(description)):
                        proposed_account = mapping.to_account_id
                        formatted_journal["has_changes"] = True
                        break

                # Only add the line if we found a matching pattern
                if proposed_account:
                    acc_proposed = self.get_account_by_id(proposed_account)

                    formatted_line = {
                        "description": description,
                        "amount": float(line.Amount) if hasattr(line, 'Amount') else 0.0,
                        "posting_type": line.JournalEntryLineDetail.PostingType,
                        "current_account": {
                            "id": account_ref.value,
                            "name": account_ref.name
                        },
                        "proposed_account": acc_proposed
                    }
                    formatted_journal["lines"].append(formatted_line)

            # Only return journal if it has changes
            return formatted_journal if formatted_journal["has_changes"] else None

        except Exception as e:
            logger.error(f"Error formatting journal {journal.Id}: {str(e)}")
            logger.debug(traceback.format_exc())
            return None

    def update_journals_accounts(self, journal_ids: List[str]) -> List[Dict[str, Any]]:
        """Update journal accounts based on mappings"""
        from app.extensions import db
        from app.models.update_history import UpdateHistory
        from datetime import datetime

        if not self.qb:
            self.authenticate()

        results = []
        account_mappings = self.get_account_mappings()

        logger.info(f"Starting update for {len(journal_ids)} journals")

        for journal_id in journal_ids:
            # Sanitize each journal ID
            safe_id = self._sanitize_id(journal_id)
            if not safe_id:
                logger.warning(f"Skipping invalid journal ID: {journal_id}")
                continue

            try:
                # Fetch the journal
                journal = JournalEntry.get(safe_id, qb=self.qb)
                if not journal:
                    logger.warning(f"Journal not found: {safe_id}")
                    continue

                # Track if we made any changes
                journal_updated = False
                journal_date = getattr(journal, 'TxnDate', None)

                # Process each line
                for line in journal.Line:
                    description = line.Description or ''
                    account_ref = line.JournalEntryLineDetail.AccountRef
                    amount = float(line.Amount) if hasattr(line, 'Amount') else None

                    # Check if this line matches any mapping
                    for mapping in account_mappings:
                        if (mapping.from_account_id == account_ref.value and
                            mapping.matches(description)):
                            # Update the account reference
                            old_account = {
                                "id": account_ref.value,
                                "name": account_ref.name
                            }

                            # Get new account details
                            new_account = Account.get(mapping.to_account_id, qb=self.qb)

                            if not new_account:
                                logger.warning(f"Target account not found: {mapping.to_account_id}")
                                break

                            new_account_dict = {
                                "id": new_account.Id,
                                "name": new_account.Name
                            }

                            # Update the line's account reference
                            line.JournalEntryLineDetail.AccountRef.value = new_account.Id
                            line.JournalEntryLineDetail.AccountRef.name = new_account.Name

                            journal_updated = True

                            # Log to history
                            try:
                                # Parse journal date
                                parsed_date = None
                                if journal_date:
                                    try:
                                        parsed_date = datetime.strptime(journal_date, '%Y-%m-%d').date()
                                    except (ValueError, TypeError):
                                        parsed_date = None

                                UpdateHistory.log_update(
                                    journal_id=safe_id,
                                    journal_date=parsed_date,
                                    line_description=description,
                                    from_account=old_account,
                                    to_account=new_account_dict,
                                    amount=amount
                                )
                            except Exception as hist_error:
                                logger.warning(f"Failed to log history: {str(hist_error)}")

                            results.append({
                                "journal_id": safe_id,
                                "line_description": description,
                                "old_account": old_account,
                                "new_account": new_account_dict
                            })
                            break

                # Only save if we made changes
                if journal_updated:
                    journal.save(qb=self.qb)
                    logger.info(f"Journal {safe_id} saved successfully")

            except Exception as e:
                logger.error(f"Error updating journal {safe_id}: {str(e)}")
                logger.debug(traceback.format_exc())
                # Continue with other journals instead of failing completely
                continue

        # Commit all history entries
        try:
            db.session.commit()
            logger.debug(f"Committed {len(results)} history entries")
        except Exception as e:
            logger.error(f"Failed to commit history: {str(e)}")
            db.session.rollback()

        logger.info(f"Update complete. {len(results)} lines updated.")
        return results


# Module-level service instance
qbo_service = QBOService()


def init_qbo(app):
    """Initialize QBO service with Flask app"""
    qbo_service.init_app(app)
