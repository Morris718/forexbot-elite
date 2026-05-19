from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from database import db
from datetime import datetime

wallet_bp = Blueprint("wallet", __name__)

class WalletTransaction(db.Model):
    __tablename__ = "wallet_transactions"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@wallet_bp.route("/")
@login_required
def index():
    txs = WalletTransaction.query.filter_by(user_id=current_user.id).order_by(WalletTransaction.created_at.desc()).limit(50).all()
    return render_template("wallet/wallet.html", balance=current_user.balance, transactions=txs)

@wallet_bp.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    if request.method == "POST":
        amount = float(request.form.get("amount", 0))
        if amount <= 0:
            flash("Invalid amount", "danger")
            return redirect(url_for("wallet.deposit"))
        
        current_user.balance += amount
        tx = WalletTransaction(user_id=current_user.id, transaction_type="DEPOSIT", amount=amount)
        db.session.add(tx)
        db.session.commit()
        flash(f"Deposited ${amount:.2f} successfully!", "success")
        return redirect(url_for("wallet.index"))
    return render_template("wallet/deposit.html")

@wallet_bp.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    if request.method == "POST":
        amount = float(request.form.get("amount", 0))
        if amount <= 0 or amount > current_user.balance:
            flash("Invalid amount or insufficient balance", "danger")
            return redirect(url_for("wallet.withdraw"))
        
        current_user.balance -= amount
        tx = WalletTransaction(user_id=current_user.id, transaction_type="WITHDRAW", amount=amount)
        db.session.add(tx)
        db.session.commit()
        flash(f"Withdrew ${amount:.2f} successfully!", "success")
        return redirect(url_for("wallet.index"))
    return render_template("wallet/withdraw.html", balance=current_user.balance)
