import smtplib
import ssl
import os
from email.message import EmailMessage
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()
EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")

def send_confirmation_email(to_email):
    msg = EmailMessage()
    msg["Subject"] = "TINA Premium Access Confirmation"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg.set_content(
        f"""
Hi there,

Thanks for registering for premium access to TINA 🇵🇭.

Your subscription is being processed. This email confirms that we received your request. If you did not sign up, please ignore this message.

Regards,  
TINA Admin
"""
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"✅ Email sent to {to_email}")
        return f"✅ Email sent to {to_email}"
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return f"❌ Failed to send email: {e}"
