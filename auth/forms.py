from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from auth.models import User

class LoginForm(FlaskForm):
    email    = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit   = SubmitField("Sign In")

class RegistrationForm(FlaskForm):
    full_name        = StringField("Full Name", validators=[DataRequired(), Length(min=2,max=120)])
    email            = StringField("Email", validators=[DataRequired(), Email()])
    phone            = StringField("Phone", validators=[Optional(), Length(max=50)])
    country          = StringField("Country", validators=[Optional(), Length(max=100)])
    password         = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField("Confirm", validators=[DataRequired(), EqualTo("password")])
    accept_terms     = BooleanField("Accept Terms", validators=[DataRequired()])
    submit           = SubmitField("Create Account")
    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError("Email already registered.")

class DepositForm(FlaskForm):
    amount = StringField("Amount (USD)", validators=[DataRequired()])
    method = SelectField("Method", choices=[("card","Card"),("bank","Bank"),("crypto","Crypto"),("paypal","PayPal")])
    note   = StringField("Note", validators=[Optional(), Length(max=200)])
    submit = SubmitField("Deposit")

class WithdrawalForm(FlaskForm):
    amount = StringField("Amount (USD)", validators=[DataRequired()])
    method = SelectField("Method", choices=[("bank","Bank"),("card","Card"),("crypto","Crypto"),("paypal","PayPal")])
    note   = StringField("Account/Wallet", validators=[Optional(), Length(max=200)])
    submit = SubmitField("Withdraw")
