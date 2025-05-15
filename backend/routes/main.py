from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from backend.models import User, TokenTransaction, Blacklist, CorrectionHistory  # Updated import path
from backend import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    if current_user.is_authenticated:
        correction_count = CorrectionHistory.query.filter_by(user_id=current_user.id).count()
        word_count = db.session.query(db.func.sum(CorrectionHistory.tokens_used))\
            .filter_by(user_id=current_user.id).scalar() or 0
        user_blacklist = Blacklist.query.filter_by(submitted_by=current_user.id).all()
        return render_template('index.html', 
                             correction_count=correction_count,
                             word_count=word_count,
                             user_blacklist=user_blacklist)
    return render_template('index.html')

@main_bp.route('/pricing')
def pricing():
    return render_template('pricing.html')

@main_bp.route('/upgrade_with_50', methods=['POST'])
@login_required
def paid_50():
    user_id = request.form.get('user_id')  # Get user ID from the form
    if not user_id or int(user_id) != current_user.id:
        flash('Invalid request.', 'error')
        return redirect(url_for('main.pricing'))

    # Update the user's type and balance
    user = User.query.get(current_user.id)
    if user:
        user.user_type = 'paid'
        user.balance += 50
        db.session.commit()
        flash('You have been upgraded to the Paid Plan, and 50 tokens have been added!', 'success')
    else:
        flash('User not found.', 'error')

    return redirect(url_for('main.pricing'))

@main_bp.route('/upgrade_with_120', methods=['POST'])
@login_required
def paid_120():
    user_id = request.form.get('user_id')  # Get user ID from the form
    if not user_id or int(user_id) != current_user.id:
        flash('Invalid request.', 'error')
        return redirect(url_for('main.pricing'))

    # Update the user's type and balance
    user = User.query.get(current_user.id)
    if user:
        user.user_type = 'paid'  
        user.balance += 120
        db.session.commit()
        flash('You have been upgraded to the Pro Plan, and 120 tokens have been added!', 'success')
    else:
        flash('User not found.', 'error')

    return redirect(url_for('main.pricing'))

@main_bp.route('/upgrade_with_300', methods=['POST'])
@login_required
def paid_300():
    user_id = request.form.get('user_id')  # Get user ID from the form
    if not user_id or int(user_id) != current_user.id:
        flash('Invalid request.', 'error')
        return redirect(url_for('main.pricing'))

    # Update the user's type and balance
    user = User.query.get(current_user.id)
    if user:
        user.user_type = 'paid'  
        user.balance += 300
        db.session.commit()
        flash('You have been upgraded to the Pro Plan, and 300 tokens have been added!', 'success')
    else:
        flash('User not found.', 'error')

    return redirect(url_for('main.pricing'))

@main_bp.route('/blacklist_word', methods=['POST'])
@login_required
def blacklist_word():
    word = request.form.get('word').strip().lower()  # Get the word from the form
    if not word:
        flash('Please enter a valid word.', 'error')
        return redirect(url_for('main.home'))

    # Check if the word already exists in the blacklist
    existing_word = Blacklist.query.filter_by(word=word, submitted_by=current_user.id).first()
    if existing_word:
        flash('This word is already in your blacklist.', 'info')
        return redirect(url_for('main.home'))

    # Add the word to the blacklist
    new_blacklist_entry = Blacklist(word=word, submitted_by=current_user.id, status='pending')
    db.session.add(new_blacklist_entry)
    db.session.commit()

    flash('Your suggestion has been submitted for review.', 'success')
    return redirect(url_for('main.home'))