from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from auth.models import User

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Sign In")

class RegistrationForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Phone (Optional)", validators=[Length(max=20)])
    country = StringField("Country", validators=[Length(max=50)])
    password = PasswordField("Password", validators=[
        DataRequired(), 
        Length(min=8, message="Password must be at least 8 characters")
    ])
    confirm_password = PasswordField("Confirm Password", validators=[
        DataRequired(), 
        EqualTo("password", message="Passwords must match")
    ])
    agree_terms = BooleanField("I agree to Terms & Conditions", validators=[DataRequired()])
    submit = SubmitField("Create Account")
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("This email is already registered")
    
    def validate_password(self, password):
        is_valid, message = User.validate_password(password.data)
        if not is_valid:
            raise ValidationError(message)
