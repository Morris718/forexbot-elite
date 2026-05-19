import random, string
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from database import db
from auth import auth_bp
from auth.models import User, Transaction
from auth.forms import LoginForm, RegistrationForm, DepositForm, WithdrawalForm

def _safe(t):
    r = urlparse(request.host_url)
    u = urlparse(urljoin(request.host_url, t))
    return u.scheme in ("http","https") and r.netloc == u.netloc

def _ref():
    return "TXN-"+"".join(random.choices(string.ascii_uppercase+string.digits,k=10))

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash("Account disabled.","danger"); return redirect(url_for("auth.login"))
            login_user(user, remember=form.remember.data)
            user.last_login = datetime.now(timezone.utc)
            user.login_count += 1; db.session.commit()
            nxt = request.args.get("next")
            return redirect(nxt if nxt and _safe(nxt) else url_for("dashboard.index"))
        flash("Invalid email or password.","danger")
    return render_template("auth/login.html", form=form)

@auth_bp.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated: return redirect(url_for("dashboard.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(full_name=form.full_name.data, email=form.email.data,
                    phone=form.phone.data or None, country=form.country.data or None)
        user.set_password(form.password.data)
        db.session.add(user); db.session.commit()
        flash("Account created!","success"); return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user(); flash("Logged out.","info"); return redirect(url_for("auth.login"))

@auth_bp.route("/profile")
@login_required
def profile():
    txns = current_user.transactions.order_by(Transaction.created_at.desc()).limit(10).all()
    return render_template("auth/profile.html", txns=txns)

@auth_bp.route("/wallet")
@login_required
def wallet():
    txns = current_user.transactions.order_by(Transaction.created_at.desc()).all()
    return render_template("wallet/wallet.html", txns=txns, dep_form=DepositForm(), wit_form=WithdrawalForm())

@auth_bp.route("/wallet/deposit", methods=["POST"])
@login_required
def deposit():
    form = DepositForm()
    if form.validate_on_submit():
        try:
            amount = float(form.amount.data.replace(",",""))
            if amount <= 0: raise ValueError
            txn = Transaction(user_id=current_user.id, type="deposit", amount=amount,
                              method=form.method.data, note=form.note.data or None,
                              reference=_ref(), status="completed",
                              processed_at=datetime.now(timezone.utc))
            current_user.balance += amount
            db.session.add(txn); db.session.commit()
            flash(f"${amount:,.2f} deposited!","success")
        except ValueError: flash("Invalid amount.","danger")
    return redirect(url_for("auth.wallet"))

@auth_bp.route("/wallet/withdraw", methods=["POST"])
@login_required
def withdraw():
    form = WithdrawalForm()
    if form.validate_on_submit():
        try:
            amount = float(form.amount.data.replace(",",""))
            if amount <= 0 or amount > current_user.balance:
                flash("Insufficient balance.","danger"); return redirect(url_for("auth.wallet"))
            txn = Transaction(user_id=current_user.id, type="withdrawal", amount=amount,
                              method=form.method.data, note=form.note.data or None,
                              reference=_ref(), status="pending")
            current_user.balance -= amount
            db.session.add(txn); db.session.commit()
            flash(f"${amount:,.2f} withdrawal submitted.","info")
        except ValueError: flash("Invalid amount.","danger")
    return redirect(url_for("auth.wallet"))

@auth_bp.route("/toggle-mode", methods=["POST"])
@login_required
def toggle_mode():
    current_user.demo_mode = not current_user.demo_mode; db.session.commit()
    flash(f"Switched to {'Demo' if current_user.demo_mode else 'Live'} mode.","info")
    return redirect(request.referrer or url_for("dashboard.index"))
