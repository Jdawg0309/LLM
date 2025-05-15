from datetime import datetime
from backend import db

class Blacklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(50), unique=True, nullable=False)
    submitted_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), 
                           nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending/approved/rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)