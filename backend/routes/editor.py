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
            # Process blacklisted words first
            processed_text, tokens_charged = process_input(current_user.id, text)
            
            # Then send processed text to OpenAI
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": """You are a text correction assistant. When correcting text:
                    1. For each correction, wrap it with: <mark class='correction' data-original='[original word]'>[corrected word]</mark>
                    2. The data-original attribute MUST contain the original word being corrected
                    3. Mark each correction individually
                    4. Keep all other words unchanged
                    5. Maintain exact positions of asterisks (*) in the text"""
                }, {
                    "role": "user",
                    "content": processed_text
                }]
            )
            corrected = response.choices[0].message.content
            save_correction(text, corrected, 'llm')
            
            return jsonify({
                'original': text,
                'corrected': corrected,
                'word_mapping': {word: i for i, word in enumerate(text.split())}
            })
            
        except Exception as e:
            current_app.logger.error(f"OpenAI Error: {str(e)}")
            return jsonify({'error': 'AI processing failed'}), 500

    else:  # Paid user logic
        required_tokens = len(words)
        if current_user.balance < required_tokens:
            penalty = max(0, current_user.balance // 2)
            current_user.balance -= penalty
            db.session.commit()
            current_app.socketio.emit('update_tokens', {'balance': current_user.balance})
            return jsonify({
                'error': f'Insufficient tokens. You need {required_tokens} tokens but only have {current_user.balance + penalty}. As a penalty, {penalty} tokens have been deducted from your balance.',
                'balance': current_user.balance,
                'penalty': penalty,
                'required': required_tokens
            }), 402
        
        try:
            # Process blacklisted words first
            processed_text, tokens_charged = process_input(current_user.id, text)
            
            # Update required tokens to include blacklist charges
            required_tokens += tokens_charged
            
            if current_user.balance < required_tokens:
                # Handle insufficient tokens after blacklist processing
                penalty = max(0, current_user.balance // 2)
                current_user.balance -= penalty
                db.session.commit()
                current_app.socketio.emit('update_tokens', {'balance': current_user.balance})
                return jsonify({
                    'error': f'Insufficient tokens. You need {required_tokens} tokens but only have {current_user.balance + penalty}. As a penalty, {penalty} tokens have been deducted from your balance.',
                    'balance': current_user.balance,
                    'penalty': penalty,
                    'required': required_tokens
                }), 402

            # Then send processed text to OpenAI
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": """You are a text correction assistant. When correcting text:
                    1. For each correction, wrap it with: <mark class='correction' data-original='[original word]'>[corrected word]</mark>
                    2. The data-original attribute MUST contain the original word being corrected
                    3. Mark each correction individually
                    4. Keep all other words unchanged
                    5. Maintain exact positions of asterisks (*) in the text"""
                }, {
                    "role": "user",
                    "content": processed_text
                }]
            )
            corrected = response.choices[0].message.content
            
            # Check if text is more than 10 words and has no corrections
            no_corrections = "<mark class='correction'" not in corrected
            if len(words) > 10 and no_corrections:
                # Add 3 token bonus
                current_user.balance += 3
                # Record the bonus transaction
                bonus_transaction = TokenTransaction(
                    user_id=current_user.id,
                    amount=3,
                    transaction_type='bonus'
                )
                db.session.add(bonus_transaction)
                
            # Deduct required tokens
            current_user.balance -= required_tokens

            save_correction(text, corrected, 'llm', required_tokens)
            db.session.commit()
            
            current_app.socketio.emit('update_tokens', {'balance': current_user.balance})
            
            response_data = {
                'original': text,
                'corrected': corrected,
                'tokens_used': required_tokens,
                'balance': current_user.balance,
                'word_mapping': {word: i for i, word in enumerate(text.split())}
            }
            
            # Add bonus notification if applicable
            if len(words) > 10 and no_corrections:
                response_data['bonus'] = 3
                response_data['bonus_message'] = 'Perfect text! You received a 3 token bonus.'
            
            return jsonify(response_data)
            
        except Exception as e:
            current_app.logger.error(f"OpenAI Error: {str(e)}")
            return jsonify({'error': 'AI processing failed'}), 500

@editor_bp.route('/handle-decision', methods=['POST'])
@login_required
def handle_decision():
    data = request.get_json()
    original_text = data.get('original_text')
    selected_text = data.get('selected_text')
    decision = data.get('decision')

    correction = CorrectionHistory.query.filter_by(
        user_id=current_user.id,
        original_text=original_text
    ).order_by(CorrectionHistory.timestamp.desc()).first()

    if not correction:
        return jsonify({'error': 'Correction not found'}), 404

    if decision == 'accept':
        correction.status = 'pending'  # Keep as pending until all corrections are handled
        current_user.balance -= 1
        # Don't update final_text yet, just track the acceptance
        
    db.session.commit()
    current_app.socketio.emit('update_tokens', {'balance': current_user.balance})
    
    return jsonify({
        'new_balance': current_user.balance,
        'corrected_text': correction.corrected_text  # Return the full corrected text
    })

@editor_bp.route('/handle-rejection', methods=['POST'])
@login_required
def handle_rejection():
    data = request.get_json()
    original_text = data.get('original_text')
    rejection_reason = data.get('rejection_reason')

    correction = CorrectionHistory.query.filter_by(
        user_id=current_user.id,
        original_text=original_text
    ).order_by(CorrectionHistory.timestamp.desc()).first()

    if not correction:
        return jsonify({'error': 'Correction not found'}), 404

    # Update correction status and reason
    correction.status = 'rejected'
    correction.rejection_reason = rejection_reason
    correction.final_text = original_text  # Use original text since all corrections were rejected
    
    db.session.commit()
    
    return jsonify({
        'new_balance': current_user.balance,
        'original_text': original_text
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
    current_app.socketio.emit('update_tokens', {'balance': current_user.balance})

    return jsonify({
        "original": original,
        "corrected": highlighted_text,
        "token_cost": token_cost
    })

@editor_bp.route('/save-corrected', methods=['POST'])
@login_required
def save_corrected():
    if current_user.user_type != 'paid':
        return jsonify({'error': 'Only paid users can use the save feature.'}), 403

    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text to save.'}), 400

    if current_user.balance < 5:
        return jsonify({'error': 'Insufficient tokens to save. You need at least 5 tokens.'}), 402

    current_user.balance -= 5
    transaction = TokenTransaction(
        user_id=current_user.id,
        amount=5,
        transaction_type='save'
    )
    db.session.add(transaction)
    db.session.commit()
    try:
        current_app.socketio.emit('update_tokens', {'balance': current_user.balance})
    except Exception:
        pass

    return jsonify({'success': True, 'balance': current_user.balance})

def process_input(user_id, input_text):
    # Fetch all accepted blacklisted words for the user
    blacklisted_words = Blacklist.query.filter_by(status='approved').all()

    tokens_charged = 0
    processed_text = input_text
    
    for word_entry in blacklisted_words:
        word = word_entry.word
        # Count occurrences of the word
        count = processed_text.count(word)
        if count > 0:
            # Replace the word with '*' of the same length
            processed_text = processed_text.replace(word, '*' * len(word))
            # Charge tokens based on the length of the word
            tokens_charged += len(word)

    # Remove token deduction from here, just return the values
    return processed_text, tokens_charged


