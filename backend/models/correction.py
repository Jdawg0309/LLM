from datetime import datetime
from backend import db

class CorrectionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), 
                       nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    corrected_text = db.Column(db.Text, nullable=False)
    correction_type = db.Column(db.String(20), nullable=False)  # self/llm
    tokens_used = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(25), default='pending')
    rejection_reason = db.Column(db.Text)
    final_text = db.Column(db.Text)

    __table_args__ = (
        db.Index('idx_status', 'status'),  # Added for better query performance
    )