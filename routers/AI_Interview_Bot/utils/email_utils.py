import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def generate_otp():
    import random
    return str(random.randint(100000, 999999))

def send_otp(email: str, otp: str):
    message = MIMEText(f"Your OTP for AI Interview Login is: {otp}")
    message["Subject"] = "AI Interview OTP Verification"
    message["From"] = EMAIL_USER
    message["To"] = email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, email, message.as_string())
