from flask import Blueprint, request, jsonify, current_app, flash, url_for
from flask_login import login_required, current_user, logout_user
from datetime import datetime, timedelta
from openai import OpenAI
import os
from backend.models import User, TokenTransaction, Blacklist, CorrectionHistory  # Updated import path
from backend import db
import math
import difflib

editor_bp = Blueprint('editor', __name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def check_cooldown():
    if current_user.user_type == 'free' and current_user.last_submission:
        cooldown_end = current_user.last_submission + timedelta(minutes=3)
        if datetime.utcnow() < cooldown_end:
            remaining = (cooldown_end - datetime.utcnow()).seconds
            return True, remaining
    return False, 0

@editor_bp.route('/llm-correct', methods=['POST'])
@login_required  # This will automatically redirect to login if user is not authenticated
def llm_correct():
    text = request.get_json().get('text', '')
    words = text.split()
    
    if current_user.user_type == 'free':
        if len(words) > 20:
            # Set last submission time
            current_user.last_submission = datetime.utcnow()
            db.session.commit()
            # Force logout
            logout_user()
            return jsonify({
                'error': 'Word limit exceeded',
                'force_logout': True,
                'cooldown': 180  # 3 minutes in seconds
            }), 403

        has_cooldown, remaining = check_cooldown()
        if has_cooldown:
            return jsonify({
                'error': 'Free users can submit once every 3 minutes',
                'cooldown': True,
                'remaining': remaining
            }), 429

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
            return jsonify({'error': 'AI processing failed'}), 500

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
            return jsonify({'error': 'AI processing failed'}), 500

@editor_bp.route('/handle-decision', methods=['POST'])
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
        penalty = 5 if not reason else 1
        current_user.balance -= penalty
        correction.final_text = correction.original_text

    db.session.commit()
    return jsonify({
        'new_balance': current_user.balance,
        'final_text': correction.final_text
    })

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

import difflib

@editor_bp.route('/self-correct', methods=['POST'])
@login_required
def self_correct():
    data = request.get_json()
    original = data.get('original', '').strip()
    corrected = data.get('corrected', '').strip()

    if not original or not corrected:
        return jsonify({"error": "Original and corrected text are required."}), 400

    original_words = original.split()
    corrected_words = corrected.split()

    # Use SequenceMatcher to find changes
    matcher = difflib.SequenceMatcher(None, original_words, corrected_words)
    highlighted_corrected = []

    changes = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            highlighted_corrected.extend(corrected_words[j1:j2])
        else:
            # Highlight added/changed words
            changed_segment = corrected_words[j1:j2]
            highlighted_corrected.extend([f"<mark class='correction'>{word}</mark>" for word in changed_segment])
            changes += len(changed_segment)

    highlighted_text = ' '.join(highlighted_corrected)

    token_cost = math.ceil(changes / 2)

    if current_user.balance < token_cost:
        return jsonify({
            "error": f"Insufficient tokens. Required: {token_cost}, Available: {current_user.balance}"
        }), 403

    current_user.balance -= token_cost
    save_correction(original, corrected, 'self', token_cost)
    db.session.commit()

    return jsonify({
        "original": original,
        "corrected": highlighted_text,
        "token_cost": token_cost
    })
