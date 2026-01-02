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
    """Account mapping rule stored in database - scoped per QBO company"""

    __tablename__ = "account_mappings"

    id = db.Column(db.Integer, primary_key=True)
    realm_id = db.Column(
        db.String(50),
        db.ForeignKey("qbo_connections.realm_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
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

    # Relationship to QBO connection
    connection = db.relationship(
        "QBOConnection",
        backref=db.backref("mappings", lazy="dynamic", cascade="all, delete-orphan"),
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
            "realm_id": self.realm_id,
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
    def get_categories(cls, realm_id: str = None):
        """Get all unique categories for a specific realm"""
        query = cls.query.with_entities(cls.category).distinct()
        query = query.filter(cls.category.isnot(None), cls.category != "")
        if realm_id:
            query = query.filter(cls.realm_id == realm_id)
        result = query.all()
        return sorted([r[0] for r in result])

    @classmethod
    def get_active_mappings(cls, realm_id: str = None):
        """Get all active mappings for a specific realm ordered by sort_order"""
        query = cls.query.filter_by(is_active=True)
        if realm_id:
            query = query.filter(cls.realm_id == realm_id)
        return query.order_by(cls.sort_order.asc()).all()

    @classmethod
    def get_mappings_by_realm(cls, realm_id: str):
        """Get all mappings for a specific realm"""
        return (
            cls.query.filter_by(realm_id=realm_id).order_by(cls.sort_order.asc()).all()
        )

    @classmethod
    def get_next_sort_order(cls, realm_id: str = None):
        """Get the next available sort_order value for a realm"""
        query = cls.query.with_entities(db.func.max(cls.sort_order))
        if realm_id:
            query = query.filter(cls.realm_id == realm_id)
        max_order = query.scalar()
        return (max_order or 0) + 1

    @classmethod
    def migrate_mappings_to_realm(cls, realm_id: str) -> int:
        """
        Migrate existing mappings without realm_id to the specified realm.
        Returns the number of mappings migrated.
        """
        try:
            orphan_mappings = cls.query.filter(cls.realm_id.is_(None)).all()
            count = 0
            for mapping in orphan_mappings:
                mapping.realm_id = realm_id
                count += 1
            if count > 0:
                db.session.commit()
                logger.info(f"Migrated {count} orphan mappings to realm {realm_id}")
            return count
        except Exception as e:
            logger.error(f"Error migrating mappings: {str(e)}")
            db.session.rollback()
            return 0
