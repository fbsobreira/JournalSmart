# File: app/services/qbo.py
"""
/app/services/qbo.py
QuickBooks Online API integration service
"""
from quickbooks import QuickBooks
from quickbooks.objects.journalentry import JournalEntry
from intuitlib.client import AuthClient
from quickbooks.objects.account import Account
from app.models.account_mapping import AccountMapping
from datetime import datetime
from config import Config

class QBOService:
    def __init__(self, app=None):
        self.client = None
        self.auth_client = None
        self.qb = None
        # Add cache dictionary
        self._account_cache = {}
        # Add cache timeout (e.g., 1 hour in seconds)
        self._cache_timeout = 3600
        # Add last cache update time
        self._last_cache_update = {}

        if app is not None:
            self.init_app(app)        

    def init_app(self, app):
        self.auth_client = AuthClient(
            client_id=app.config['QBO_CLIENT_ID'],
            client_secret=app.config['QBO_CLIENT_SECRET'],
            redirect_uri=app.config['QBO_REDIRECT_URI'],
            environment=app.config['QBO_ENVIRONMENT']
        )

    def authenticate(self):
        """Initialize QuickBooks client with OAuth tokens"""
        if not self.auth_client.access_token:
            # Here you would typically redirect to OAuth flow
            # For testing, you can set the tokens directly
            raise Exception("No access token available. Please authenticate first.")
        
        self.qb = QuickBooks(
            auth_client=self.auth_client,
            refresh_token=self.auth_client.refresh_token,
            company_id=self.auth_client.realm_id,  # You'll need to set this
            minorversion=65
        )
    
    def get_accounts(self):
        """Fetch all accounts"""
        if not self.qb:
            self.authenticate()
            
        try:
            # Get all accounts with select query
            # This ensures we get all account types, including custom ones
            where_clause = "Active = true"
            accounts = Account.where(
                where_clause,
                qb=self.qb
            )
            
            # Format accounts for response, include parent reference
            return [{
                "id": account.Id,
                "name": account.FullyQualifiedName if hasattr(account, 'FullyQualifiedName') else account.Name,
                "account_type": account.AccountType,
                "account_subtype": getattr(account, 'AccountSubType', ''),
                "parent_id": account.ParentRef.value if hasattr(account, 'ParentRef') and account.ParentRef else None,
                "is_sub_account": hasattr(account, 'ParentRef') and account.ParentRef is not None,
                "balance": getattr(account, 'CurrentBalance', 0)
            } for account in accounts]
        except Exception as e:
            print(f"Error fetching accounts: {str(e)}")
            return []

    def _is_cache_valid(self, key):
        """Check if cache is still valid"""
        if key not in self._last_cache_update:
            return False
        
        now = datetime.now()
        time_diff = (now - self._last_cache_update[key]).total_seconds()
        return time_diff < self._cache_timeout

    def get_account_by_id(self, account_id):
        """Fetch account by ID"""
        if not self.qb:
            self.authenticate()
            
        try:
            # Check cache first
            cache_key = f"account_{account_id}"
            if cache_key in self._account_cache and self._is_cache_valid(cache_key):
                print(f"Cache hit for account {account_id}")
                return self._account_cache[cache_key]

            print(f"Cache miss for account {account_id}, fetching from QuickBooks")
            
            where_clause = "Active = true and Id = '{}'".format(account_id)
            accounts = Account.where(
                where_clause,
                qb=self.qb
            )

            if not accounts:
                return None

            account = accounts[0]

            # Format account data
            account_data = {
                "id": account.Id,
                "name": account.FullyQualifiedName if hasattr(account, 'FullyQualifiedName') else account.Name,
                "account_type": account.AccountType,
                "account_subtype": getattr(account, 'AccountSubType', ''),
                "parent_id": account.ParentRef.value if hasattr(account, 'ParentRef') and account.ParentRef else None,
                "is_sub_account": hasattr(account, 'ParentRef') and account.ParentRef is not None,
                "balance": getattr(account, 'CurrentBalance', 0)
            }
            
            # Update cache
            self._account_cache[cache_key] = account_data
            self._last_cache_update[cache_key] = datetime.now()
            
            return account_data
        except Exception as e:
            print(f"Error fetching accounts: {str(e)}")
            return []

    def get_journals_by_account(self, account_id, start_date):
        """Fetch journal entries filtered by account"""
        if not self.qb:
            self.authenticate()

        try:     
            # query = f"""
            #     select * from JournalEntry 
            #     where MetaData.CreateTime >= '{start_date}'
            #     MAXRESULTS 1000
            # """

            query = f"""
                select * from JournalEntry 
                where TxnDate >= '{start_date}'
                MAXRESULTS 1000
            """
            journals = JournalEntry.query(query, qb=self.qb)

            print(f"Query executed: {query}")
            print(f"Total journals found before filtering: {len(journals)}")

            # Get account mappings
            account_mappings = self.get_account_mappings()  # We need to implement this

            # Filter in Python since QB API doesn't support Line item filtering
            filtered_journals = []
            count = 0
            for journal in journals:
                for line in journal.Line:
                    if (hasattr(line, 'JournalEntryLineDetail') and 
                        hasattr(line.JournalEntryLineDetail, 'AccountRef') and 
                        line.JournalEntryLineDetail.AccountRef.value == account_id):
                        filtered_journals.append(journal)
                        count += 1
                        break  # Found a matching line, no need to check other lines
                        
            print(f"Journals found with account {account_id}: {count}")

            # Format journals with mappings
            formatted_journals = []
            for journal in filtered_journals:
                formatted_journal = self._format_journal(
                    journal=journal,
                    account_mappings=account_mappings,
                    selected_account_id=account_id
                )
                if formatted_journal:  # Only add if there are changes
                    formatted_journals.append(formatted_journal)
                        
            print(f"Journals with changes: {len(formatted_journals)}")
            return formatted_journals
        except Exception as e:
            print(f"Error fetching journals: {str(e)}")
            print(f"Account ID used: {account_id}")
            import traceback
            print(traceback.format_exc())
            return []

    def get_account_mappings(self):
        """Get account mappings from environment configuration"""
        raw_mappings = Config.get_account_mappings()
        
        return [
            AccountMapping(
                pattern=mapping['pattern'],
                from_account_id=mapping['from_account_id'],
                to_account_id=mapping['to_account_id']
            ) for mapping in raw_mappings
        ]

    def _format_journal(self, journal, account_mappings, selected_account_id):
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

                description = line.Description
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
                            "id": line.JournalEntryLineDetail.AccountRef.value,
                            "name": line.JournalEntryLineDetail.AccountRef.name
                        },
                        "proposed_account": acc_proposed
                    }
                    formatted_journal["lines"].append(formatted_line)

            # Only return journal if it has changes
            return formatted_journal if formatted_journal["has_changes"] else None
        except Exception as e:
            print(f"Error formatting journal: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None

    def update_journals_accounts(self, journal_ids):
        """Update journal accounts based on mappings"""
        if not self.qb:
            self.authenticate()
        
        results = []
        account_mappings = self.get_account_mappings()
        
        try:
            print(f"Updating journals: {journal_ids}")
            for journal_id in journal_ids:
                # Fetch the journal
                journal = JournalEntry.get(journal_id, qb=self.qb)
                
                # Track if we made any changes
                journal_updated = False
                
                # Process each line
                for line in journal.Line:
                    description = line.Description
                    account_ref = line.JournalEntryLineDetail.AccountRef
                    
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
                                print(f"Account not found: {mapping.to_account_id}")
                                break
                            
                            # Update the line's account reference
                            line.JournalEntryLineDetail.AccountRef.value = new_account.Id
                            line.JournalEntryLineDetail.AccountRef.name = new_account.Name
                            
                            journal_updated = True
                            results.append({
                                "journal_id": journal_id,
                                "line_description": description,
                                "old_account": old_account,
                                "new_account": {
                                    "id": new_account.Id,
                                    "name": new_account.Name
                                }
                            })
                            break
                
                # Only save if we made changes
                if journal_updated:
                    journal.save(qb=self.qb)
        
        except Exception as e:
            print(f"Error updating journals: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise e
        
        return results

qbo_service = QBOService()

def init_qbo(app):
    qbo_service.init_app(app)