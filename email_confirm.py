import smtplib
import ssl
import os
from email.message import EmailMessage
from dotenv import load_dotenv

# 🔐 Load environment variables from .env
load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")

# Optional Debug
if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    print("❌ EMAIL_USER or EMAIL_PASS not loaded from .env")
else:
    print("✅ Email credentials loaded")

def send_confirmation_email(to_email):
    msg = EmailMessage()
    msg["Subject"] = "TINA Premium Access Confirmation"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg.set_content(
        f"""
Hi there,

Thank you for registering for premium access to TINA 🇵🇭.

Your subscription is being processed. This email confirms that we received your request.
If you did not sign up, please ignore this message.

Regards,  
TINA Admin
"""
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ Email successfull
