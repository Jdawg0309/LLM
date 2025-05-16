from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from backend.models import User, TokenTransaction, Blacklist, CorrectionHistory, Invitation, Collaboration, TextFile  # Updated import path
from backend import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    if current_user.is_authenticated:
        page = request.args.get('page', 1, type=int)
        per_page = 5

        correction_count = CorrectionHistory.query.filter_by(user_id=current_user.id).count()
        word_count = db.session.query(db.func.sum(CorrectionHistory.tokens_used))\
            .filter_by(user_id=current_user.id).scalar() or 0
        user_blacklist = Blacklist.query.filter_by(submitted_by=current_user.id).all()

        paginated_history = CorrectionHistory.query.filter_by(user_id=current_user.id)\
            .order_by(CorrectionHistory.timestamp.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        return render_template('index.html',
                               correction_count=correction_count,
                               word_count=word_count,
                               user_blacklist=user_blacklist,
                               correction_history=paginated_history)
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

@main_bp.route('/invite', methods=['POST'])
@login_required
def invite():
    if current_user.user_type != 'paid':
        flash('Only paid users can send invitations.', 'error')
        return redirect(url_for('main.home'))

    invitee_email = request.form.get('invitee_email').strip()
    text_file_id = request.form.get('text_file_id')

    # Find the invitee
    invitee = User.query.filter_by(email=invitee_email, user_type='paid').first()
    if not invitee:
        flash('The invitee must be a paid user.', 'error')
        return redirect(url_for('main.home'))

    # Check if the text file exists and belongs to the inviter
    text_file = TextFile.query.filter_by(id=text_file_id, owner_id=current_user.id).first()
    if not text_file:
        flash('Invalid text file.', 'error')
        return redirect(url_for('main.home'))

    # Create an invitation
    invitation = Invitation(inviter_id=current_user.id, invitee_id=invitee.id, text_file_id=text_file.id)
    db.session.add(invitation)
    db.session.commit()

    flash(f'Invitation sent to {invitee.email}.', 'success')
    return redirect(url_for('main.home'))

@main_bp.route('/respond_invitation/<int:invitation_id>/<string:response>', methods=['POST'])
@login_required
def respond_invitation(invitation_id, response):
    # Find the invitation
    invitation = Invitation.query.get(invitation_id)
    if not invitation or invitation.invitee_id != current_user.id:
        flash('Invalid invitation.', 'error')
        return redirect(url_for('main.home'))

    if response == 'accept':
        # Update the invitation status
        print('Processing invitation acceptance...')
        invitation.status = 'accepted'

        # Add the invitee as a collaborator on the text file
        collaboration = Collaboration(user_id=current_user.id, text_file_id=invitation.text_file_id)
        db.session.add(collaboration)
        db.session.delete(invitation)  # Remove the invitation after acceptance
        db.session.commit()

        flash('You have accepted the invitation.', 'success')

    elif response == 'reject':
        # Update the invitation status
        invitation.status = 'rejected'

        # Deduct 3 tokens from the inviter
        inviter = User.query.get(invitation.inviter_id)
        if inviter:
            inviter.balance -= 3
            db.session.delete(invitation)  # Remove the invitation after rejection
            db.session.commit()

        flash('You have rejected the invitation. The inviter has been charged 3 tokens.', 'info')

    return redirect(url_for('main.home'))

@main_bp.route('/collab', methods=['GET', 'POST'])
@login_required
def collab():
    if current_user.user_type not in ['paid', 'super']:
        flash('Only paid or super users can access this page.', 'error')
        return redirect(url_for('main.home'))

    # Handle text file creation
    if request.method == 'POST' and 'create_text_file' in request.form:
        name = request.form.get('name').strip()
        content = request.form.get('content').strip()

        if not name or not content:
            flash('Both name and content are required.', 'error')
        else:
            # Save the text file to the database
            text_file = TextFile(name=name, content=content, owner_id=current_user.id)
            db.session.add(text_file)
            db.session.commit()
            flash('Text file created successfully.', 'success')

    # Handle file deletion
    if request.method == 'POST' and 'delete_file' in request.form:
        text_file_id = request.form.get('text_file_id')
        text_file = TextFile.query.filter_by(id=text_file_id, owner_id=current_user.id).first()

        if not text_file:
            flash('Invalid text file.', 'error')
        else:
            # Delete associated collaborations first
            Collaboration.query.filter_by(text_file_id=text_file.id).delete()
            db.session.delete(text_file)
            db.session.commit()
            flash('Text file deleted successfully.', 'success')

    # Handle invitations
    if request.method == 'POST' and 'invite_user' in request.form:
        invitee_email = request.form.get('invitee_email').strip()
        text_file_id = request.form.get('text_file_id')

        # Find the invitee (allow both 'paid' and 'super' users)
        invitee = User.query.filter(
            (User.email == invitee_email) & (User.user_type.in_(['paid', 'super']))
        ).first()

        if not invitee:
            flash('The invitee must be a paid or super user.', 'error')
        else:
            # Check if the text file exists and belongs to the inviter
            text_file = TextFile.query.filter_by(id=text_file_id, owner_id=current_user.id).first()
            if not text_file:
                flash('Invalid text file.', 'error')
            else:
                # Create an invitation
                invitation = Invitation(inviter_id=current_user.id, invitee_id=invitee.id, text_file_id=text_file.id)
                db.session.add(invitation)
                db.session.commit()
                flash(f'Invitation sent to {invitee.email}.', 'success')

    # Fetch the user's text files (owned or collaborated on)
    owned_files = TextFile.query.filter_by(owner_id=current_user.id).all()
    collaborated_files = TextFile.query.join(Collaboration, TextFile.id == Collaboration.text_file_id)\
                                       .filter(Collaboration.user_id == current_user.id).all()
    text_files = owned_files + collaborated_files

    # Fetch collaborators for each file
    file_collaborators = {
        file.id: [
            User.query.get(collab.user_id).email
            for collab in Collaboration.query.filter_by(text_file_id=file.id).all()
        ]
        for file in text_files
    }

    # Fetch invitations for the logged-in user
    invitations = db.session.query(
        Invitation.id, Invitation.text_file_id, Invitation.status, User.username, User.email, TextFile.name
    ).join(User, Invitation.inviter_id == User.id)\
     .join(TextFile, Invitation.text_file_id == TextFile.id)\
     .filter(Invitation.invitee_id == current_user.id)\
     .all()

    return render_template('collab.html', text_files=text_files, file_collaborators=file_collaborators, invitations=invitations)