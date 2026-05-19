from app import create_app
from database import db
from auth.models import User
from werkzeug.security import generate_password_hash, check_password_hash

app = create_app()
app.app_context().push()

email = 'mutindamorris718@gmail.com'
password = 'Admin@123'

print('=' * 60)
print('STEP 1: Find user')
print('=' * 60)
user = User.query.filter(db.func.lower(User.email) == email).first()
print(f'User found: {bool(user)}')
print(f'Email: {user.email}')
print(f'Is Admin: {user.is_admin}')

print('')
print('=' * 60)
print('STEP 2: Test current password')
print('=' * 60)
print(f'check_password(Admin@123): {user.check_password(password)}')

print('')
print('=' * 60)
print('STEP 3: FORCE RESET PASSWORD')
print('=' * 60)
new_hash = generate_password_hash(password)
user.password_hash = new_hash
user.is_admin = True
user.is_verified = True
user.is_profile_complete = True
db.session.commit()
print(f'New hash saved: {new_hash[:50]}...')

print('')
print('=' * 60)
print('STEP 4: Verify after reset')
print('=' * 60)
db.session.expire_all()
user2 = User.query.filter(db.func.lower(User.email) == email).first()
print(f'Password Check: {user2.check_password(password)}')
print(f'Direct hash check: {check_password_hash(user2.password_hash, password)}')

print('')
print('=' * 60)
print('READY TO LOGIN!')
print('=' * 60)
print(f'URL     : http://localhost:5000/admin/login')
print(f'Email   : {email}')
print(f'Password: {password}')
print('=' * 60)
