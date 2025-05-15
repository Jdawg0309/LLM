from flask import Blueprint, request, jsonify, current_app, flash, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from openai import OpenAI
import os
from backend.models import User, TokenTransaction, Blacklist, CorrectionHistory  # Updated import path
from backend import db
import re

editor_bp = Blueprint('editor', __name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def check_cooldown():
    if current_user.user_type == 'free' and current_user.last_submission:
        remaining = (current_user.last_submission + 
                    timedelta(minutes=3) - datetime.utcnow()).seconds // 60
        if remaining > 0:
            flash(f'Free users can only submit every 3 minutes ({remaining} min remaining)', 'warning')
            return True
    return False

@editor_bp.route('/llm-correct', methods=['POST'])
@login_required  # This will automatically redirect to login if user is not authenticated
def llm_correct():
    if check_cooldown():
        return jsonify({'error': 'Free users can submit once every 3 minutes'}), 429
    
    text = request.get_json().get('text', '')
    words = text.split()
    
    if current_user.user_type == 'free':
        if len(words) > 20:
            flash('Free users limited to 20 words', 'danger')
            return jsonify({'error': 'Free users limited to 20 words'}), 400

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