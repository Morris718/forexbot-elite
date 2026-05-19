from database import db, login_manager
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from datetime import datetime
import re

bcrypt = Bcrypt()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(50), default="United States")
    balance = db.Column(db.Float, default=10000.0)
    total_profit_loss = db.Column(db.Float, default=0.0)
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    login_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trades = db.relationship("Trade", backref="user", lazy=True, cascade="all, delete-orphan")
    transactions = db.relationship("WalletTransaction", backref="user", lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    @staticmethod
    def validate_email(email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_password(password):
        """Password must be 8+ chars with uppercase, lowercase, number"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain an uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain a lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain a number"
        return True, "Password is valid"
    
    def record_login(self):
        self.last_login = datetime.utcnow()
        self.login_count += 1
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    from flask import flash, redirect, url_for
    flash("Please login to access this page", "warning")
    return redirect(url_for("auth.login"))
