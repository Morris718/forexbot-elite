import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()

SMTP_SERVER = os.getenv("MAIL_SERVER")
SMTP_PORT = int(os.getenv("MAIL_PORT", 587))
SMTP_USER = os.getenv("MAIL_USERNAME")
SMTP_PASS = os.getenv("MAIL_PASSWORD")
SENDER = os.getenv("MAIL_DEFAULT_SENDER")

print("=" * 60)
print("EMAIL DIAGNOSTIC TEST")
print("=" * 60)
print(f"SMTP Server: {SMTP_SERVER}")
print(f"SMTP Port: {SMTP_PORT}")
print(f"SMTP Login: {SMTP_USER}")
print(f"Sender Email: {SENDER}")
print(f"Password set: {bool(SMTP_PASS)}")
print("=" * 60)

recipient = input("Enter your email to test: ").strip()

msg = MIMEMultipart("alternative")
msg["Subject"] = "ForexBot Pro - Test Email"
msg["From"] = SENDER
msg["To"] = recipient

html = "<h2>Test Email Successful!</h2><p>Your Brevo setup works!</p>"
msg.attach(MIMEText(html, "html"))

try:
    print(f"\nConnecting to {SMTP_SERVER}:{SMTP_PORT}...")
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
    print("Starting TLS...")
    server.starttls()
    print("Logging in...")
    server.login(SMTP_USER, SMTP_PASS)
    print("Sending email...")
    server.send_message(msg)
    server.quit()
    print(f"\nSUCCESS! Email sent to {recipient}")
    print("Check inbox AND spam folder!")
except smtplib.SMTPSenderRefused as e:
    print(f"\nERROR: Sender not verified on Brevo!")
    print(f"Details: {e}")
    print(f"FIX: Go to https://app.brevo.com/senders/list and verify {SENDER}")
except smtplib.SMTPAuthenticationError as e:
    print(f"\nERROR: Wrong credentials!")
    print(f"Details: {e}")
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")

input("\nPress Enter to exit...")
