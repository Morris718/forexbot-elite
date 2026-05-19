from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from auth import auth_bp
from auth.forms import LoginForm, RegistrationForm
from auth.models import User
from database import db
from datetime import datetime

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("trading.dashboard"))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash("This account has been deactivated. Contact support.", "danger")
                return redirect(url_for("auth.login"))
            
            login_user(user, remember=form.remember.data)
            user.record_login()
            
            next_page = request.args.get("next")
            flash(f"Welcome back, {user.full_name}!", "success")
            return redirect(next_page if next_page else url_for("trading.dashboard"))
        else:
            flash("Invalid email or password. Please try again.", "danger")
            # Log failed attempt (for security monitoring)
            print(f"⚠️ Failed login attempt for: {form.email.data}")
    
    return render_template("login.html", form=form)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("trading.dashboard"))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data,
            email=form.email.data,
            phone=form.phone.data or None,
            country=form.country.data or "United States"
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash("🎉 Account created successfully! Please login.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            flash(f"Registration failed: {str(e)}", "danger")
    
    return render_template("register.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)

@auth_bp.route("/profile/update", methods=["GET", "POST"])
@login_required
def update_profile():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        phone = request.form.get("phone")
        country = request.form.get("country")
        
        current_user.full_name = full_name
        current_user.phone = phone
        current_user.country = country
        current_user.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("auth.profile"))
    
    return render_template("profile.html", user=current_user)

@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        if not current_user.check_password(current_password):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("auth.change_password"))
        
        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("auth.change_password"))
        
        is_valid, message = User.validate_password(new_password)
        if not is_valid:
            flash(message, "danger")
            return redirect(url_for("auth.change_password"))
        
        current_user.set_password(new_password)
        db.session.commit()
        flash("Password changed successfully!", "success")
        return redirect(url_for("auth.profile"))
    
    return render_template("change_password.html")
