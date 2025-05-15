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

@main_bp.route('/feature')
def feature():
    return render_template('feature.html')

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

@main_bp.route('/admin')
@login_required
def admin():
    if current_user.user_type != 'super':
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('main.home'))

    # Fetch blacklisted words
    blacklisted_words = db.session.query(
        Blacklist.id, Blacklist.word, Blacklist.status, User.username, User.email
    ).join(User, Blacklist.submitted_by == User.id).all()

    # Fetch corrections with rejections and include user information
    corrections = CorrectionHistory.query.filter_by(status='rejected').join(
        User, CorrectionHistory.user_id == User.id
    ).order_by(CorrectionHistory.timestamp.desc()).all()

    return render_template('admin.html', 
                         blacklisted_words=blacklisted_words,
                         corrections=corrections)

@main_bp.route('/reject_word/<int:word_id>', methods=['POST'])
@login_required
def reject_word(word_id):
    if current_user.user_type != 'super':
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('main.admin'))

    # Find the word in the database
    word_entry = Blacklist.query.get(word_id)
    if not word_entry:
        flash('Word not found.', 'error')
        return redirect(url_for('main.admin'))

    # Update the status to "rejected"
    word_entry.status = 'rejected'
    db.session.commit()

    flash(f'The word "{word_entry.word}" has been rejected.', 'success')
    return redirect(url_for('main.admin'))

@main_bp.route('/accept_word/<int:word_id>', methods=['POST'])
@login_required
def accept_word(word_id):
    if current_user.user_type != 'super':
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('main.admin'))

    # Find the word in the database
    word_entry = Blacklist.query.get(word_id)
    if not word_entry:
        flash('Word not found.', 'error')
        return redirect(url_for('main.admin'))

    # Update the status to "accepted"
    word_entry.status = 'approved'
    db.session.commit()

    flash(f'The word "{word_entry.word}" has been accepted.', 'success')
    return redirect(url_for('main.admin'))

@main_bp.route('/review_rejection/<int:rejection_id>/<decision>', methods=['POST'])
@login_required
def review_rejection(rejection_id, decision):
    if current_user.user_type != 'super':
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('main.admin'))

    correction = CorrectionHistory.query.get(rejection_id)
    if not correction:
        flash('Rejection not found.', 'error')
        return redirect(url_for('main.admin'))

    user = User.query.get(correction.user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('main.admin'))

    if decision == 'accept':
        # Deduct 1 token for accepted rejection
        token_deduction = 1
        correction.status = 'rejection_approved'
    else:
        # Deduct 5 tokens for rejected rejection
        token_deduction = 5
        correction.status = 'rejection_denied'

    user.balance -= token_deduction
    db.session.commit()

    flash(f'Rejection {"accepted" if decision == "accept" else "rejected"}. {token_deduction} tokens deducted.', 'success')
    return redirect(url_for('main.admin'))

@main_bp.route('/process_input', methods=['POST'])
@login_required
def process_user_input():
    input_text = request.form.get('input_text')  # Get user input from the form
    if not input_text:
        flash('Please enter some text.', 'error')
        return redirect(url_for('main.home'))

    # Process the input to replace blacklisted words and charge tokens
    processed_text, tokens_charged = process_input(current_user.id, input_text)

    flash(f'Your input has been processed. {tokens_charged} tokens were charged.', 'success')
    return render_template('result.html', processed_text=processed_text)