from datetime import datetime
from backend import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150))
    user_type = db.Column(db.String(20), default='free')  # free/paid/super
    balance = db.Column(db.Float, default=0.0)
    last_submission = db.Column(db.DateTime)
    is_suspended = db.Column(db.Boolean, default=False)

    # Relationships
    transactions = db.relationship('TokenTransaction', backref='user', lazy=True)
    corrections = db.relationship('CorrectionHistory', backref='user', lazy=True)
    blacklist_entries = db.relationship('Blacklist', backref='submitter', lazy=True)

    def set_password(self, password):
        self.password_hash = password  # Switch back to generate_password_hash(password)

    def check_password(self, password):
        return self.password_hash == password  # Switch to check_password_hash