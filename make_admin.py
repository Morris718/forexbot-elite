"""
Make a user an admin
Usage: python make_admin.py email@example.com
"""
import sys
from app import create_app
from database import db
from auth.models import User

if len(sys.argv) < 2:
    print("Usage: python make_admin.py <email>")
    sys.exit(1)

email = sys.argv[1].lower().strip()

app = create_app()
with app.app_context():
    user = User.query.filter(db.func.lower(User.email) == email).first()
    if not user:
        print(f"ERROR: User with email {email} not found!")
        print("\nAvailable users:")
        for u in User.query.all():
            print(f"  - {u.email} ({'ADMIN' if u.is_admin else 'USER'})")
        sys.exit(1)
    
    user.is_admin = True
    db.session.commit()
    print(f"\n[SUCCESS] {user.email} is now an ADMIN!")
    print(f"Login at: http://localhost:5000/admin/login")
    print(f"Username: {user.email}")
    print(f"Password: (the password you set during signup)")
