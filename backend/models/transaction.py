from datetime import datetime
from backend import db

class TokenTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), 
                       nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # purchase/penalty/usage
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)