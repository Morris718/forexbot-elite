from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, jsonify
)
from flask_login import login_user, logout_user, login_required, current_user
from database import db
from auth.models import User, Transaction, Referral, generate_referral_code
from auth.google_auth import get_google_auth_url, exchange_code_for_token
from datetime import datetime, date
import re

auth_bp = Blueprint('auth', __name__, template_folder='../templates')


def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain an uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain a lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain a digit"
    if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
        return False, "Password must contain a special character"
    return True, "OK"


def give_signup_bonus(user):
    """Give $5 signup bonus"""
    if not user.signup_bonus_given:
        user.bonus_balance += 5.0
        user.signup_bonus_given = True
        
        # Create transaction record
        bonus_tx = Transaction(
            user_id=user.id,
            transaction_type='BONUS',
            amount=5.0,
            payment_method='SYSTEM',
            status='COMPLETED',
            reference_id=Transaction.generate_reference(),
            notes='Welcome bonus - $5 for new signup',
            completed_at=datetime.utcnow()
        )
        db.session.add(bonus_tx)
        db.session.commit()


def process_referral(new_user, ref_code):
    """Process referral relationship (bonus paid after first deposit)"""
    if not ref_code:
        return
    
    referrer = User.query.filter_by(referral_code=ref_code).first()
    if not referrer or referrer.id == new_user.id:
        return
    
    new_user.referred_by_code = ref_code
    referrer.total_referrals += 1
    
    # Create pending referral (bonus paid when referee deposits $10+)
    referral = Referral(
        referrer_id=referrer.id,
        referred_id=new_user.id,
        bonus_amount=2.0,
        is_paid=False
    )
    db.session.add(referral)
    db.session.commit()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('trading.dashboard'))

    if request.method == 'POST':
        email_or_username = request.form.get('email_or_username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        user = User.query.filter(
            (db.func.lower(User.email) == email_or_username.lower()) |
            (User.username == email_or_username)
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('trading.dashboard'))
        else:
            flash('Invalid email/username or password.', 'danger')

    google_auth_url = get_google_auth_url()
    return render_template('login.html', google_auth_url=google_auth_url)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('trading.dashboard'))

    # Get referral code from URL
    ref_code = request.args.get('ref', '').strip().upper()
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        username = request.form.get('username', '').strip()
        dob_str = request.form.get('date_of_birth', '')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        ref_code = request.form.get('ref_code', '').strip().upper()

        errors = []

        if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors.append('Please enter a valid email address.')

        if User.query.filter(db.func.lower(User.email) == email.lower()).first():
            errors.append('Email already registered.')

        if not first_name or len(first_name) < 2:
            errors.append('First name must be at least 2 characters.')
        if not last_name or len(last_name) < 2:
            errors.append('Last name must be at least 2 characters.')

        if not username or len(username) < 3 or len(username) > 20:
            errors.append('Username must be 3-20 characters.')
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append('Username can only contain letters, numbers, and underscores.')
        elif User.query.filter_by(username=username).first():
            errors.append('Username is already taken.')

        dob = None
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 18:
                errors.append('You must be at least 18 years old.')
        except ValueError:
            errors.append('Invalid date of birth.')

        if password != confirm_password:
            errors.append('Passwords do not match.')

        valid_pw, pw_msg = validate_password(password)
        if not valid_pw:
            errors.append(pw_msg)

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('signup.html',
                                   email=email, first_name=first_name,
                                   last_name=last_name, username=username,
                                   ref_code=ref_code,
                                   google_auth_url=get_google_auth_url())

        try:
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                username=username,
                date_of_birth=dob,
                is_verified=True,
                is_profile_complete=True,
                balance=0.0,  # NO STARTING BALANCE
                bonus_balance=0.0,
                referral_code=generate_referral_code()
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            # Give $5 signup bonus
            give_signup_bonus(user)
            
            # Process referral if any
            if ref_code:
                process_referral(user, ref_code)
            
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            bonus_msg = ''
            if ref_code:
                bonus_msg = ' You were referred - your referrer will earn $2 when you make your first deposit!'
            
            flash(f'🎉 Welcome to ForexBot Pro, {first_name}! You received a $5 welcome bonus!{bonus_msg}', 'success')
            return redirect(url_for('trading.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return render_template('signup.html', google_auth_url=get_google_auth_url())

    google_auth_url = get_google_auth_url()
    return render_template('signup.html', google_auth_url=google_auth_url, ref_code=ref_code)


@auth_bp.route('/google/login')
def google_login():
    auth_url = get_google_auth_url()
    return redirect(auth_url)


@auth_bp.route('/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        flash('Google authentication failed.', 'danger')
        return redirect(url_for('auth.login'))

    user_info = exchange_code_for_token(code)
    if not user_info:
        flash('Failed to get Google account info.', 'danger')
        return redirect(url_for('auth.login'))

    email = user_info['email'].lower()
    google_id = user_info['google_id']

    user = User.query.filter(
        (User.google_id == google_id) | (db.func.lower(User.email) == email)
    ).first()

    if user:
        if not user.google_id:
            user.google_id = google_id
        if user_info.get('picture'):
            user.profile_picture = user_info['picture']
        user.is_verified = True
        db.session.commit()

        if user.is_profile_complete:
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('trading.dashboard'))
        else:
            session['completing_profile_email'] = email
            return redirect(url_for('auth.complete_profile'))
    else:
        user = User(
            email=email,
            google_id=google_id,
            first_name=user_info.get('first_name', ''),
            last_name=user_info.get('last_name', ''),
            profile_picture=user_info.get('picture', ''),
            is_verified=True,
            balance=0.0,
            referral_code=generate_referral_code()
        )
        db.session.add(user)
        db.session.commit()
        give_signup_bonus(user)
        session['completing_profile_email'] = email
        flash('Google account linked! Complete your profile to get $5 bonus.', 'success')
        return redirect(url_for('auth.complete_profile'))


@auth_bp.route('/complete-profile', methods=['GET', 'POST'])
def complete_profile():
    email = session.get('completing_profile_email')
    if not email:
        return redirect(url_for('auth.signup'))

    user = User.query.filter(db.func.lower(User.email) == email.lower()).first()
    if not user:
        return redirect(url_for('auth.signup'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        dob_str = request.form.get('date_of_birth', '')
        first_name = request.form.get('first_name', '').strip() or user.first_name
        last_name = request.form.get('last_name', '').strip() or user.last_name

        errors = []
        if not username or len(username) < 3:
            errors.append('Username required (min 3 chars).')
        elif User.query.filter_by(username=username).filter(User.id != user.id).first():
            errors.append('Username already taken.')

        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 18:
                errors.append('Must be 18+.')
        except ValueError:
            errors.append('Invalid date.')
            dob = None

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('complete_profile.html', email=email, is_google_user=True)

        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        user.date_of_birth = dob
        user.is_profile_complete = True
        db.session.commit()

        session.pop('completing_profile_email', None)
        login_user(user)
        user.last_login = datetime.utcnow()
        db.session.commit()
        flash(f'Welcome, {first_name}! You received a $5 welcome bonus!', 'success')
        return redirect(url_for('trading.dashboard'))

    return render_template('complete_profile.html', email=email, is_google_user=True)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/check-username', methods=['POST'])
def check_username():
    username = request.json.get('username', '').strip()
    if len(username) < 3:
        return jsonify({'available': False, 'message': 'Too short'})
    if User.query.filter_by(username=username).first():
        return jsonify({'available': False, 'message': 'Taken'})
    return jsonify({'available': True, 'message': 'Available'})


@auth_bp.route('/verify-email')
def verify_email():
    return redirect(url_for('auth.signup'))

@auth_bp.route('/resend-code', methods=['POST'])
def resend_code():
    return redirect(url_for('auth.signup'))
