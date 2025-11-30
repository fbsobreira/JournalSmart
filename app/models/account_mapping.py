# File: app/models/account_mapping.py
"""
/app/models/account_mapping.py
Account mapping model for description-to-account rules
"""

import re
import logging

logger = logging.getLogger(__name__)


class AccountMapping:
    def __init__(self, pattern, from_account_id, to_account_id, is_regex=False):
        self.pattern = pattern
        self.from_account_id = from_account_id
        self.to_account_id = to_account_id
        self.is_regex = is_regex

    def matches(self, description):
        """Check if description matches the pattern (case-insensitive)"""
        if not description:
            return False

        if self.is_regex:
            try:
                return bool(re.search(self.pattern, description, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{self.pattern}': {e}")
                return False
        else:
            return self.pattern.lower() in description.lower()

    def __repr__(self):
        regex_str = ", regex=True" if self.is_regex else ""
        return f"AccountMapping(pattern='{self.pattern}', from='{self.from_account_id}', to='{self.to_account_id}'{regex_str})"
