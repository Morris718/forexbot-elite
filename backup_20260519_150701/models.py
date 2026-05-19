from database import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random
import string


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(64), unique=True, nullable=True, index=True)
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    is_verified = db.Column(db.Boolean, default=True)
    is_profile_complete = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(256), unique=True, nullable=True)
    profile_picture = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Financial fields
    balance = db.Column(db.Float, default=0.0)  # NO STARTING BALANCE
    bonus_balance = db.Column(db.Float, default=0.0)  # Separate bonus tracking
    total_profit_loss = db.Column(db.Float, default=0.0)
    total_deposited = db.Column(db.Float, default=0.0)
    total_withdrawn = db.Column(db.Float, default=0.0)
    
    # Referral system
    referral_code = db.Column(db.String(10), unique=True, nullable=True, default=generate_referral_code)
    referred_by_code = db.Column(db.String(10), nullable=True)
    total_referrals = db.Column(db.Integer, default=0)
    referral_earnings = db.Column(db.Float, default=0.0)
    
    # Bonus tracking
    signup_bonus_given = db.Column(db.Boolean, default=False)
    has_deposited = db.Column(db.Boolean, default=False)  # Must deposit min $10 to withdraw
    
    # Phone for M-Pesa
    phone_number = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    
    # Relationships
    trades = db.relationship('Trade', backref='user', lazy='dynamic')
    sessions = db.relationship('TradingSession', backref='user', lazy='dynamic')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username or self.email.split('@')[0]
    
    @property
    def total_balance(self):
        """Real balance + bonus"""
        return round(self.balance + self.bonus_balance, 2)
    
    @property
    def withdrawable_balance(self):
        """Only deposited funds + profits are withdrawable, NOT bonus"""
        return round(self.balance, 2)
    
    def can_withdraw(self, amount):
        """Check if user can withdraw"""
        if not self.has_deposited:
            return False, "You must deposit at least $10 before withdrawing"
        if amount < 20:
            return False, "Minimum withdrawal is $20"
        if amount > self.withdrawable_balance:
            return False, f"Insufficient balance. Available: ${self.withdrawable_balance}"
        return True, "OK"


class VerificationCode(db.Model):
    __tablename__ = 'verification_codes'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(20), default='signup')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # DEPOSIT, WITHDRAWAL, BONUS, REFERRAL
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)
    payment_details = db.Column(db.Text, nullable=True)  # JSON string with payment info
    status = db.Column(db.String(20), default='PENDING')  # PENDING, PROCESSING, COMPLETED, REJECTED, FAILED
    reference_id = db.Column(db.String(50), unique=True, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.Integer, nullable=True)  # Admin user_id who processed
    
    # Crypto specific
    crypto_address = db.Column(db.String(255), nullable=True)
    crypto_tx_hash = db.Column(db.String(255), nullable=True)
    
    # Bank specific
    bank_name = db.Column(db.String(100), nullable=True)
    account_number = db.Column(db.String(50), nullable=True)
    account_name = db.Column(db.String(100), nullable=True)
    
    # M-Pesa specific
    mpesa_phone = db.Column(db.String(20), nullable=True)
    mpesa_code = db.Column(db.String(50), nullable=True)
    
    # PayPal
    paypal_email = db.Column(db.String(120), nullable=True)

    @staticmethod
    def generate_reference():
        return 'TXN' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))


class Referral(db.Model):
    __tablename__ = 'referrals'
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bonus_amount = db.Column(db.Float, default=2.0)
    is_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
