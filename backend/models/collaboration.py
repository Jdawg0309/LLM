from datetime import datetime
from backend import db

class Collaboration(db.Model):
    __tablename__ = 'collaborations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text_file_id = db.Column(db.Integer, db.ForeignKey('text_files.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())