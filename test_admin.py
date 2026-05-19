from app import create_app
from database import db
from auth.models import User

app = create_app()
app.app_context().push()

email = 'mutindamorris718@gmail.com'
password = 'Admin@123'

u = User.query.filter_by(email=email).first()

print('=' * 60)
print('USER DETAILS:')
print('=' * 60)
print(f'User found     : {bool(u)}')
print(f'Email          : {u.email}')
print(f'Username       : {u.username}')
print(f'Is Admin       : {u.is_admin}')
print(f'Is Verified    : {u.is_verified}')
print(f'Profile Done   : {u.is_profile_complete}')
print(f'Has PW Hash    : {bool(u.password_hash)}')
print(f'Password Hash  : {u.password_hash[:40]}')
print(f'Password Check : {u.check_password(password)}')
print('=' * 60)

# Fix and reset password
print('RESETTING PASSWORD...')
u.set_password(password)
u.is_admin = True
u.is_verified = True
u.is_profile_complete = True
db.session.commit()

# Verify again
u2 = User.query.filter_by(email=email).first()
print(f'Password Check After Reset: {u2.check_password(password)}')
print('=' * 60)
print('LOGIN WITH:')
print(f'  URL      : http://localhost:5000/admin/login')
print(f'  Email    : {email}')
print(f'  Password : {password}')
print('=' * 60)
