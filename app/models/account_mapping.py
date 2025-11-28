# File: app/models/account_mapping.py
"""
/app/models/account_mapping.py
Account mapping model for description-to-account rules
"""

class AccountMapping:
    def __init__(self, pattern, from_account_id, to_account_id):
        self.pattern = pattern
        self.from_account_id = from_account_id
        self.to_account_id = to_account_id
    
    def matches(self, description):
        return self.pattern.lower() in description.lower()

    def __repr__(self):
        return f"AccountMapping(pattern='{self.pattern}', from='{self.from_account_id}', to='{self.to_account_id}')"