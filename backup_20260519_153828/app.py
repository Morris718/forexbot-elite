from flask import Flask, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from database import db, login_manager
from datetime import datetime
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "forex_secret_key_2024_change_in_production")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///forex_bot.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_ENABLED"] = True

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager.init_app(app)

from auth import auth_bp
from trading.bot import trading_bp
from wallet import wallet_bp

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(trading_bp, url_prefix="/trading")
app.register_blueprint(wallet_bp, url_prefix="/wallet")

@app.context_processor
def inject_globals():
    return {"now": datetime.utcnow(), "year": datetime.now().year}

@app.route("/")
def index():
    return redirect(url_for("auth.login"))

@app.errorhandler(404)
def not_found(e):
    flash("Page not found", "warning")
    return redirect(url_for("auth.login"))

@app.errorhandler(500)
def server_error(e):
    flash("Server error. Please try again.", "danger")
    return redirect(url_for("auth.login"))

with app.app_context():
    db.create_all()
    print("✅ Database initialized successfully")

if __name__ == "__main__":
    print("\n🚀 Starting Forex Trading Bot...")
    print("📍 URL: http://127.0.0.1:5000")
    print("📝 Register: http://127.0.0.1:5000/auth/register")
    print("🔐 Login: http://127.0.0.1:5000/auth/login\n")
    app.run(debug=True, port=5000)
