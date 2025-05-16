from datetime import datetime
from backend import db

class Invitation(db.Model):
    __tablename__ = 'invitations'
    id = db.Column(db.Integer, primary_key=True)
    inviter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invitee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text_file_id = db.Column(db.Integer, db.ForeignKey('text_files.id'), nullable=False)
    status = db.Column(db.Enum('pending', 'accepted', 'rejected'), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())