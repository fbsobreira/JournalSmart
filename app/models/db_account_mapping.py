# File: app/models/db_account_mapping.py
"""
/app/models/db_account_mapping.py
Database model for account mapping rules
"""

import re
import logging
from datetime import datetime
from app.extensions import db

logger = logging.getLogger(__name__)


class DBAccountMapping(db.Model):
    """Account mapping rule stored in database"""

    __tablename__ = "account_mappings"

    id = db.Column(db.Integer, primary_key=True)
    pattern = db.Column(db.String(200), nullable=False)
    from_account_id = db.Column(db.String(50), nullable=False)
    from_account_name = db.Column(db.String(200))
    to_account_id = db.Column(db.String(50), nullable=False)
    to_account_name = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    is_regex = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(100), nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<DBAccountMapping {self.pattern}: {self.from_account_id} -> {self.to_account_id}>"

    def matches(self, description: str) -> bool:
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

    def get_match_position(self, description: str) -> tuple:
        """Get the start and end position of the match for highlighting"""
        if not description:
            return (-1, -1)

        if self.is_regex:
            try:
                match = re.search(self.pattern, description, re.IGNORECASE)
                if match:
                    return (match.start(), match.end())
            except re.error:
                pass
            return (-1, -1)
        else:
            start = description.lower().find(self.pattern.lower())
            if start >= 0:
                return (start, start + len(self.pattern))
            return (-1, -1)

    @classmethod
    def validate_regex(cls, pattern: str) -> tuple:
        """Validate a regex pattern. Returns (is_valid, error_message)"""
        try:
            re.compile(pattern)
            return (True, None)
        except re.error as e:
            return (False, str(e))

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "pattern": self.pattern,
            "from_account_id": self.from_account_id,
            "from_account_name": self.from_account_name,
            "to_account_id": self.to_account_id,
            "to_account_name": self.to_account_name,
            "is_active": self.is_active,
            "is_regex": self.is_regex,
            "category": self.category,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_categories(cls):
        """Get all unique categories"""
        result = (
            cls.query.with_entities(cls.category)
            .distinct()
            .filter(cls.category.isnot(None), cls.category != "")
            .all()
        )
        return sorted([r[0] for r in result])

    @classmethod
    def get_active_mappings(cls):
        """Get all active mappings ordered by sort_order"""
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order.asc()).all()

    @classmethod
    def get_next_sort_order(cls):
        """Get the next available sort_order value"""
        max_order = cls.query.with_entities(db.func.max(cls.sort_order)).scalar()
        return (max_order or 0) + 1
