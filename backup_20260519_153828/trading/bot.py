from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from database import db
from datetime import datetime

trading_bp = Blueprint("trading", __name__, template_folder="../templates/trading")

class Trade(db.Model):
    __tablename__ = "trades"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    pair = db.Column(db.String(20), nullable=False)
    trade_type = db.Column(db.String(10), nullable=False)
    lot_size = db.Column(db.Float, default=0.01)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=True)
    stop_loss = db.Column(db.Float, nullable=True)
    take_profit = db.Column(db.Float, nullable=True)
    profit_loss = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="OPEN")
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

@trading_bp.route("/dashboard")
@login_required
def dashboard():
    open_trades = Trade.query.filter_by(user_id=current_user.id, status="OPEN").count()
    closed_trades = Trade.query.filter_by(user_id=current_user.id, status="CLOSED").count()
    total_pnl = current_user.total_profit_loss
    
    recent_trades = Trade.query.filter_by(user_id=current_user.id).order_by(Trade.opened_at.desc()).limit(5).all()
    
    return render_template("dashboard.html", 
                         balance=current_user.balance,
                         open_trades=open_trades,
                         closed_trades=closed_trades,
                         total_pnl=total_pnl,
                         recent_trades=recent_trades)
