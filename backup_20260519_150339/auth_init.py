from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from functools import wraps
import json
import os

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

class User(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
    
    @staticmethod
    def get_users_file():
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users.json')
    
    @staticmethod
    def load_users():
        users_file = User.get_users_file()
        try:
            if os.path.exists(users_file):
                with open(users_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        return json.loads(content)
            return {}
        except Exception as e:
            print(f"Error loading users: {e}")
            return {}
    
    @staticmethod
    def save_users(users):
        users_file = User.get_users_file()
        os.makedirs(os.path.dirname(users_file), exist_ok=True)
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)
    
    @staticmethod
    def get(user_id):
        users = User.load_users()
        if user_id in users:
            u = users[user_id]
            return User(user_id, u['username'], u['email'], u['password_hash'])
        return None
    
    @staticmethod
    def get_by_username(username):
        users = User.load_users()
        for user_id, u in users.items():
            if u['username'] == username:
                return User(user_id, u['username'], u['email'], u['password_hash'])
        return None
    
    @staticmethod
    def get_by_email(email):
        users = User.load_users()
        for user_id, u in users.items():
            if u['email'] == email:
                return User(user_id, u['username'], u['email'], u['password_hash'])
        return None
    
    @staticmethod
    def create(username, email, password):
        users = User.load_users()
        user_id = str(len(users) + 1)
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        users[user_id] = {
            'username': username,
            'email': email,
            'password_hash': password_hash
        }
        User.save_users(users)
        return User(user_id, username, email, password_hash)
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def init_auth(app):
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.get_by_username(username)
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page if next_page else url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if User.get_by_username(username):
            flash('Username already exists', 'danger')
        elif User.get_by_email(email):
            flash('Email already registered', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
        else:
            User.create(username, email, password)
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

__all__ = ['auth_bp', 'User', 'init_auth', 'login_manager', 'bcrypt']
