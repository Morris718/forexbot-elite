"""
Authentication Blueprint - Complete with Signup & Login
"""
from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, session, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from auth.models import User
from datetime import datetime
import re
import os
import urllib.parse

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def get_google_auth_url():
    """Build Google OAuth URL (optional)"""
    client_id = os.getenv('GOOGLE_CLIENT_ID', '')
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
    
    if not client_id:
        return None
    
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'select_account'
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


# ============================================================
# SIGNUP
# ============================================================
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('trading.dashboard'))

    ref_code = request.args.get('ref', '')

    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone_number', '').strip()
            country = request.form.get('country', '').strip()
            referred_by = request.form.get('ref_code', '').strip() or ref_code

            # Validation
            if not username or not email or not password:
                flash('Username, email and password are required', 'danger')
                return render_template('signup.html', google_auth_url=get_google_auth_url(), ref_code=ref_code)

            if not is_valid_email(email):
                flash('Invalid email address', 'danger')
                return render_template('signup.html', google_auth_url=get_google_auth_url(), ref_code=ref_code)

            if len(password) < 6:
                flash('Password must be at least 6 characters', 'danger')
                return render_template('signup.html', google_auth_url=get_google_auth_url(), ref_code=ref_code)

            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return render_template('signup.html', google_auth_url=get_google_auth_url(), ref_code=ref_code)

            # Check duplicates
            if User.query.filter(db.func.lower(User.email) == email).first():
                flash('Email already registered. Please login.', 'danger')
                return render_template('signup.html', google_auth_url=get_google_auth_url(), ref_code=ref_code)

            if User.query.filter_by(username=username).first():
                flash('Username already taken', 'danger')
                return render_template('signup.html', google_auth_url=get_google_auth_url(), ref_code=ref_code)

            # Create user
            new_user = User(
                username=username,
                email=email,
                first_name=first_name or None,
                last_name=last_name or None,
                phone_number=phone or None,
                country=country or None,
                referred_by_code=referred_by or None,
                is_verified=True,
                is_profile_complete=True,
                is_admin=False,
                balance=0.0,
                bonus_balance=5.0,
                signup_bonus_given=True
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()

            # Handle referral
            if referred_by:
                referrer = User.query.filter_by(referral_code=referred_by).first()
                if referrer:
                    referrer.total_referrals = (referrer.total_referrals or 0) + 1
                    referrer.bonus_balance = (referrer.bonus_balance or 0) + 2.0
                    referrer.referral_earnings = (referrer.referral_earnings or 0) + 2.0
                    db.session.commit()

            # Auto-login
            login_user(new_user, remember=True)
            new_user.last_login = datetime.utcnow()
            db.session.commit()

            flash(f'Welcome {username}! Your account has been created with a $5 bonus!', 'success')
            return redirect(url_for('trading.dashboard'))

        except Exception as e:
            db.session.rollback()
            print(f"[SIGNUP ERROR] {e}")
            flash(f'Signup error: {str(e)}', 'danger')
            return render_template('signup.html', google_auth_url=get_google_auth_url(), ref_code=ref_code)

    return render_template('signup.html', google_auth_url=get_google_auth_url(), ref_code=ref_code)


# ============================================================
# LOGIN
# ============================================================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('trading.dashboard'))

    if request.method == 'POST':
        try:
            email_or_username = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            remember = request.form.get('remember') == 'on'

            if not email_or_username or not password:
                flash('Please enter your credentials', 'danger')
                return render_template('login.html', google_auth_url=get_google_auth_url())

            user = User.query.filter(
                (db.func.lower(User.email) == email_or_username) |
                (db.func.lower(User.username) == email_or_username)
            ).first()

            if not user:
                flash('No account found with these credentials', 'danger')
                return render_template('login.html', google_auth_url=get_google_auth_url())

            if not user.password_hash:
                flash('This account uses Google login. Please sign in with Google.', 'warning')
                return render_template('login.html', google_auth_url=get_google_auth_url())

            if not user.check_password(password):
                flash('Invalid password', 'danger')
                return render_template('login.html', google_auth_url=get_google_auth_url())

            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()

            flash(f'Welcome back, {user.username}!', 'success')

            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            
            return redirect(url_for('trading.dashboard'))

        except Exception as e:
            print(f"[LOGIN ERROR] {e}")
            flash(f'Login error: {str(e)}', 'danger')
            return render_template('login.html', google_auth_url=get_google_auth_url())

    return render_template('login.html', google_auth_url=get_google_auth_url())


# ============================================================
# LOGOUT
# ============================================================
@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username if current_user.username else 'User'
    logout_user()
    session.clear()
    flash(f'Goodbye {username}! You have been logged out.', 'success')
    return redirect(url_for('auth.login'))


# ============================================================
# PROFILE
# ============================================================
@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


# ============================================================
# GOOGLE OAUTH CALLBACK (placeholder)
# ============================================================
@auth_bp.route('/google/callback')
def google_callback():
    flash('Google OAuth not configured yet', 'warning')
    return redirect(url_for('auth.login'))


# ============================================================
# COMPLETE PROFILE (for Google users)
# ============================================================
@auth_bp.route('/complete-profile', methods=['GET', 'POST'])
def complete_profile():
    email = session.get('pending_email')
    if not email:
        return redirect(url_for('auth.signup'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if not username:
            flash('Username required', 'danger')
            return render_template('complete_profile.html', email=email, is_google_user=True)
        
        # Create or update user
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, username=username, is_verified=True, is_profile_complete=True)
            db.session.add(user)
        else:
            user.username = username
            user.is_profile_complete = True
        
        db.session.commit()
        login_user(user)
        session.pop('pending_email', None)
        return redirect(url_for('trading.dashboard'))
    
    return render_template('complete_profile.html', email=email, is_google_user=True)
