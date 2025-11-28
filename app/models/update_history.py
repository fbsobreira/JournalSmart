# File: app/models/update_history.py
"""
/app/models/update_history.py
Model for tracking journal entry update history
"""
from datetime import datetime
from app.extensions import db


class UpdateHistory(db.Model):
    """Audit log for journal entry updates"""
    __tablename__ = 'update_history'

    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.String(50), nullable=False)
    journal_date = db.Column(db.Date)
    line_description = db.Column(db.String(500))
    from_account_id = db.Column(db.String(50))
    from_account_name = db.Column(db.String(200))
    to_account_id = db.Column(db.String(50))
    to_account_name = db.Column(db.String(200))
    amount = db.Column(db.Float)
    mapping_id = db.Column(db.Integer, db.ForeignKey('account_mappings.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to mapping
    mapping = db.relationship('DBAccountMapping', backref='updates', lazy=True)

    def __repr__(self):
        return f'<UpdateHistory Journal:{self.journal_id} {self.from_account_name} -> {self.to_account_name}>'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'journal_id': self.journal_id,
            'journal_date': self.journal_date.isoformat() if self.journal_date else None,
            'line_description': self.line_description,
            'from_account_id': self.from_account_id,
            'from_account_name': self.from_account_name,
            'to_account_id': self.to_account_id,
            'to_account_name': self.to_account_name,
            'amount': self.amount,
            'mapping_id': self.mapping_id,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def log_update(cls, journal_id: str, journal_date, line_description: str,
                   from_account: dict, to_account: dict, amount: float = None,
                   mapping_id: int = None):
        """Create a new history entry"""
        entry = cls(
            journal_id=journal_id,
            journal_date=journal_date,
            line_description=line_description,
            from_account_id=from_account.get('id'),
            from_account_name=from_account.get('name'),
            to_account_id=to_account.get('id'),
            to_account_name=to_account.get('name'),
            amount=amount,
            mapping_id=mapping_id
        )
        db.session.add(entry)
        return entry
