from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from frontend.models import User, db
from openai import OpenAI
from dotenv import load_dotenv
import os
from sqlalchemy import func
import logging
# Add at the top
from datetime import datetime, timedelta
# Add at the top
from datetime import datetime, timedelta
from frontend.models import Blacklist, TokenTransaction, CorrectionHistory

bp = Blueprint('main', __name__)
load_dotenv()  # Load environment variables explicitly

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Helper functions
def handle_error(message, code):
    flash(message, 'danger')
    return jsonify({'error': message}), code

@bp.route('/')
def home():
    return render_template('index.html', username=current_user.username if current_user.is_authenticated else None)

    if current_user.is_authenticated:
        return render_template('index.html', username=current_user.username)
    return render_template('index.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        user = User.query.filter(func.lower(User.email) == email).first()

        if user and user.check_password(password):
            login_user(user, remember=request.form.get('remember', False))
            flash('Login successful!', 'success')
            return redirect(url_for('main.home'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('main.signup'))

        if User.query.filter(func.lower(User.email) == func.lower(email)).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('main.signup'))

        new_user = User(
            username=username,
            email=email,
            balance=50.0 if request.form.get('account_type') == 'paid' else 0.0,
            user_type='paid' if request.form.get('account_type') == 'paid' else 'free'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully!', 'success')
        return redirect(url_for('main.login'))
    return render_template('signup.html')
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('main.signup'))

        existing_user = User.query.filter(func.lower(User.email) == func.lower(email)).first()
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('main.signup'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully!', 'success')
        return redirect(url_for('main.login'))

    return render_template('signup.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.home'))

@bp.route('/llm-correct', methods=['POST'])
@login_required
def llm_correct():
    if check_cooldown():
        return jsonify({'error': 'Free users can submit once every 3 minutes'}), 429
    
    text = request.get_json().get('text', '')
    words = text.split()
    
    if current_user.user_type == 'free':
        if len(words) > 20:
            return handle_error('Free users limited to 20 words', 400)
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": "Highlight changes with <mark class='correction'> tags"
                }, {
                    "role": "user",
                    "content": text
                }]
            )
            corrected = response.choices[0].message.content
            save_correction(text, corrected, 'llm')
            return jsonify({'original': text, 'corrected': corrected})
            
        except Exception as e:
            current_app.logger.error(f"OpenAI Error: {str(e)}")
            return handle_error('AI processing failed', 500)
    
    else:  # Paid user logic
        required_tokens = len(words)
        if current_user.balance < required_tokens:
            penalty = max(0, current_user.balance // 2)
            current_user.balance -= penalty
            db.session.commit()
            return jsonify({
                'error': f'Insufficient tokens. {penalty} tokens deducted',
                'balance': current_user.balance
            }), 402
        
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": "Highlight changes with <mark class='correction'> tags"
                }, {
                    "role": "user",
                    "content": text
                }]
            )
            corrected = response.choices[0].message.content
            current_user.balance -= required_tokens
            save_correction(text, corrected, 'llm', required_tokens)
            db.session.commit()
            return jsonify({
                'original': text,
                'corrected': corrected,
                'tokens_used': required_tokens,
                'balance': current_user.balance
            })
            
        except Exception as e:
            current_app.logger.error(f"OpenAI Error: {str(e)}")
            return handle_error('AI processing failed', 500)
# Add helper functions
def handle_error(message, code):
    flash(message, 'danger')
    return jsonify({'error': message}), code

def handle_insufficient_tokens(required):
    if current_user.user_type == 'paid':
        penalty = max(0, current_user.balance // 2)
        current_user.balance -= penalty
        db.session.commit()
        msg = f'Insufficient tokens. {penalty} token penalty applied'
    else:
        msg = 'Upgrade to paid plan for more capacity'
    
    flash(msg, 'warning')
    return jsonify({'error': msg}), 402

def save_correction(original, corrected, correction_type, tokens=0):
    correction = CorrectionHistory(
        user_id=current_user.id,
        original_text=original,
        corrected_text=corrected,
        correction_type=correction_type,
        tokens_used=tokens,
        status='pending'
    )
    db.session.add(correction)
    db.session.commit()
    return correction

@bp.route('/submit', methods=['POST'])
@login_required
def submit_text():
    # Free user cooldown check
    if current_user.user_type == 'free':
        if current_user.last_submission and \
           (datetime.utcnow() - current_user.last_submission) < timedelta(minutes=3):
            return jsonify({'error': 'Free user cooldown active'}), 429

    # Word count validation
    text = request.json.get('text', '')
    word_count = len(text.split())
    
    if current_user.user_type == 'free' and word_count > 20:
        current_user.last_submission = datetime.utcnow()
        db.session.commit()
        return jsonify({'error': 'Free user word limit exceeded'}), 400

    # Process blacklist words
    blacklisted_words = Blacklist.query.filter_by(status='approved').all()
    processed_text, penalty = process_blacklist(text, blacklisted_words)
    
    # Token management
    required_tokens = word_count + penalty
    if current_user.balance < required_tokens:
        if current_user.user_type == 'paid':
            current_user.balance = max(0, current_user.balance - (required_tokens // 2))
            db.session.commit()
        return jsonify({'error': 'Insufficient tokens'}), 402

    # Deduct tokens
    current_user.balance -= required_tokens
    db.session.add(TokenTransaction(
        user_id=current_user.id,
        amount=-required_tokens,
        transaction_type='usage'
    ))
    
    # Save correction history
    correction = CorrectionHistory(
        user_id=current_user.id,
        original_text=text,
        corrected_text=processed_text,
        correction_type='self',
        tokens_used=required_tokens
    )
    db.session.add(correction)
    db.session.commit()
    
    return jsonify({'processed_text': processed_text})


def process_blacklist(text):
    blacklisted = Blacklist.query.filter_by(status='approved').all()
    for entry in blacklisted:
        text = re.sub(
            r'\b{}\b'.format(re.escape(entry.word)),
            '*' * len(entry.word),
            text,
            flags=re.IGNORECASE
        )
    return text

@bp.route('/handle-decision', methods=['POST'])
@login_required
def handle_decision():
    data = request.get_json()
    correction = CorrectionHistory.query.get(data['correction_id'])

    if data['decision'] == 'accept':
        correction.status = 'accepted'
        current_user.balance -= 1
        correction.final_text = correction.corrected_text
    else:
        correction.status = 'rejected'
        reason = data.get('reason','').strip()
        # assume you handle super-user approval elsewhere…
        penalty = 5 if not reason else 1
        current_user.balance -= penalty
        correction.final_text = correction.original_text

    db.session.commit()
    return jsonify({
        'new_balance': current_user.balance,
        'final_text': correction.final_text
    })

    data = request.get_json()
    decision = data.get('decision')
    correction_id = data.get('correction_id')
    reason = data.get('reason', '')

    # Security check
    correction = CorrectionHistory.query.filter_by(
        id=correction_id,
        user_id=current_user.id
    ).first_or_404()

    if decision == 'accept':
        if current_user.balance < 1:
            return jsonify({'error': 'Insufficient tokens'}), 402
        correction.status = 'accepted'
        correction.final_text = correction.corrected_text
        current_user.balance -= 1
    elif decision == 'reject':
        correction.status = 'rejected'
        correction.rejection_reason = reason
        if not reason.strip():
            current_user.balance = max(0, current_user.balance - 5)
    else:
        return jsonify({'error': 'Invalid decision'}), 400

    db.session.commit()
    return jsonify({'new_balance': current_user.balance})


@bp.route('/upgrade', methods=['POST'])
@login_required
def upgrade_account():
    if current_user.user_type != 'free':
        flash('Already a paid user', 'info')
        return redirect(url_for('main.home'))
    
    current_user.user_type = 'paid'
    current_user.balance = 100.0  # Initial tokens
    db.session.commit()
    flash('Upgraded to paid account with 100 tokens!', 'success')
    return redirect(url_for('main.home'))
    if current_user.user_type != 'free':
        flash('You are already a paid user', 'info')
        return redirect(url_for('main.home'))
    
    # Add payment processing logic here
    current_user.user_type = 'paid'
    db.session.commit()
    flash('Account upgraded successfully!', 'success')
    return redirect(url_for('main.home'))

def check_cooldown():
    if current_user.user_type == 'free' and current_user.last_submission:
        remaining = (current_user.last_submission + 
                    timedelta(minutes=3) - datetime.utcnow()).seconds // 60
        if remaining > 0:
            flash(f'Free users can only submit every 3 minutes ({remaining} min remaining)', 'warning')
            return True
    return False

@bp.route('/pricing')
def pricing():
    return render_template('pricing.html')