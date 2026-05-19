from datetime import datetime, timezone
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from database import db, login_manager

bcrypt = Bcrypt()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id                = db.Column(db.Integer, primary_key=True)
    full_name         = db.Column(db.String(120), nullable=False)
    email             = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash     = db.Column(db.String(255), nullable=False)
    phone             = db.Column(db.String(50), nullable=True)
    country           = db.Column(db.String(100), nullable=True)
    subscription_tier = db.Column(db.String(20), default="free")
    demo_mode         = db.Column(db.Boolean, default=True)
    balance           = db.Column(db.Float, default=0.0)
    demo_balance      = db.Column(db.Float, default=100000.0)
    total_profit_loss = db.Column(db.Float, default=0.0)
    win_rate          = db.Column(db.Float, default=0.0)
    total_trades      = db.Column(db.Integer, default=0)
    winning_trades    = db.Column(db.Integer, default=0)
    risk_appetite     = db.Column(db.String(20), default="moderate")
    tech_weight       = db.Column(db.Integer, default=40)
    sentiment_weight  = db.Column(db.Integer, default=30)
    ml_weight         = db.Column(db.Integer, default=30)
    preferred_session = db.Column(db.String(20), default="all")
    is_verified       = db.Column(db.Boolean, default=False)
    is_active         = db.Column(db.Boolean, default=True)
    last_login        = db.Column(db.DateTime, nullable=True)
    login_count       = db.Column(db.Integer, default=0)
    created_at        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                  onupdate=lambda: datetime.now(timezone.utc))
    transactions = db.relationship("Transaction", backref="user", lazy="dynamic")
    positions    = db.relationship("Position", backref="user", lazy="dynamic")

    def set_password(self, p):
        self.password_hash = bcrypt.generate_password_hash(p).decode("utf-8")
    def check_password(self, p):
        return bcrypt.check_password_hash(self.password_hash, p)
    @property
    def active_balance(self):
        return self.demo_balance if self.demo_mode else self.balance
    def get_initials(self):
        parts = self.full_name.strip().split()
        return (parts[0][0]+parts[-1][0]).upper() if len(parts)>=2 else parts[0][:2].upper()

class Transaction(db.Model):
    __tablename__ = "transactions"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type         = db.Column(db.String(20), nullable=False)
    amount       = db.Column(db.Float, nullable=False)
    currency     = db.Column(db.String(10), default="USD")
    status       = db.Column(db.String(20), default="pending")
    method       = db.Column(db.String(50), nullable=True)
    reference    = db.Column(db.String(100), nullable=True)
    note         = db.Column(db.String(255), nullable=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Position(db.Model):
    __tablename__ = "positions"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pair          = db.Column(db.String(20), nullable=False)
    direction     = db.Column(db.String(10), nullable=False)
    lot_size      = db.Column(db.Float, default=0.01)
    entry_price   = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=True)
    stop_loss     = db.Column(db.Float, nullable=True)
    take_profit   = db.Column(db.Float, nullable=True)
    profit_loss   = db.Column(db.Float, default=0.0)
    pip_value     = db.Column(db.Float, default=10.0)
    status        = db.Column(db.String(20), default="open")
    is_demo       = db.Column(db.Boolean, default=True)
    opened_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    closed_at     = db.Column(db.DateTime, nullable=True)
    close_price   = db.Column(db.Float, nullable=True)

@login_manager.user_loader
def load_user(uid):
    try: return User.query.get(int(uid))
    except: return None
