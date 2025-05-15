from flask import Blueprint, render_template
from flask_login import current_user
from backend.models import User, TokenTransaction, Blacklist, CorrectionHistory  # Updated import path
from backend import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    if current_user.is_authenticated:
        correction_count = CorrectionHistory.query.filter_by(user_id=current_user.id).count()
        word_count = db.session.query(db.func.sum(CorrectionHistory.tokens_used))\
            .filter_by(user_id=current_user.id).scalar() or 0
        return render_template('index.html', 
                             correction_count=correction_count,
                             word_count=word_count)
    return render_template('index.html')