from datetime import datetime
from backend import db

class TextFile(db.Model):
    __tablename__ = 'text_files'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)  # Name of the text file
    content = db.Column(db.Text, nullable=False)  # Content of the text file
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Owner of the text file
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    