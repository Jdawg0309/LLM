from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from backend.models import User  # Updated import path
from backend import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
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

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('auth.signup'))

        if User.query.filter(func.lower(User.email) == func.lower(email)).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('auth.signup'))

        new_user = User(
            username=username,
            email=email,
            balance=50.0 if request.form.get('account_type') == 'paid' else 0.0,
            user_type='paid' if request.form.get('account_type') == 'paid' else 'free'
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Automatically log in the user after signup
        login_user(new_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('main.home'))
        
    return render_template('signup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('main.home'))

@auth_bp.route('/upgrade', methods=['POST'])
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