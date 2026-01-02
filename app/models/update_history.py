# File: app/models/update_history.py
"""
/app/models/update_history.py
Model for tracking journal entry update history
"""

from datetime import datetime
from app.extensions import db


class UpdateHistory(db.Model):
    """Audit log for journal entry updates - scoped per QBO company"""

    __tablename__ = "update_history"

    id = db.Column(db.Integer, primary_key=True)
    realm_id = db.Column(
        db.String(50),
        db.ForeignKey("qbo_connections.realm_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    journal_id = db.Column(db.String(50), nullable=False)
    journal_date = db.Column(db.Date)
    line_description = db.Column(db.String(500))
    from_account_id = db.Column(db.String(50))
    from_account_name = db.Column(db.String(200))
    to_account_id = db.Column(db.String(50))
    to_account_name = db.Column(db.String(200))
    amount = db.Column(db.Float)
    mapping_id = db.Column(
        db.Integer, db.ForeignKey("account_mappings.id"), nullable=True
    )
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    mapping = db.relationship("DBAccountMapping", backref="updates", lazy=True)
    connection = db.relationship(
        "QBOConnection",
        backref=db.backref("history", lazy="dynamic", cascade="all, delete-orphan"),
    )

    def __repr__(self):
        return f"<UpdateHistory Journal:{self.journal_id} {self.from_account_name} -> {self.to_account_name}>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "realm_id": self.realm_id,
            "journal_id": self.journal_id,
            "journal_date": self.journal_date.isoformat()
            if self.journal_date
            else None,
            "line_description": self.line_description,
            "from_account_id": self.from_account_id,
            "from_account_name": self.from_account_name,
            "to_account_id": self.to_account_id,
            "to_account_name": self.to_account_name,
            "amount": self.amount,
            "mapping_id": self.mapping_id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def log_update(
        cls,
        journal_id: str,
        journal_date,
        line_description: str,
        from_account: dict,
        to_account: dict,
        amount: float = None,
        mapping_id: int = None,
        realm_id: str = None,
    ):
        """Create a new history entry for a specific realm"""
        entry = cls(
            realm_id=realm_id,
            journal_id=journal_id,
            journal_date=journal_date,
            line_description=line_description,
            from_account_id=from_account.get("id"),
            from_account_name=from_account.get("name"),
            to_account_id=to_account.get("id"),
            to_account_name=to_account.get("name"),
            amount=amount,
            mapping_id=mapping_id,
        )
        db.session.add(entry)
        return entry

    @classmethod
    def get_history_by_realm(cls, realm_id: str, limit: int = 50, offset: int = 0):
        """Get history entries for a specific realm"""
        query = cls.query.filter_by(realm_id=realm_id)
        return query.order_by(cls.updated_at.desc()).offset(offset).limit(limit).all()

    @classmethod
    def get_history_count_by_realm(cls, realm_id: str) -> int:
        """Get total history count for a specific realm"""
        return cls.query.filter_by(realm_id=realm_id).count()
