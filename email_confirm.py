import smtplib
import ssl
from email.message import EmailMessage
import os

# Environment variables (set these in your Hugging Face or local environment)
GMAIL_SENDER = os.getenv("GMAIL_SENDER")      # Your Gmail address
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")  # Your Gmail App Password

def send_confirmation_email(to_email):
    try:
        if not GMAIL_SENDER or not GMAIL_PASSWORD:
            return "❌ Email sender not configured."

        msg = EmailMessage()
        msg['Subject'] = 'TINA Email Confirmation'
        msg['From'] = GMAIL_SENDER
        msg['To'] = to_email
        msg.set_content(f"""
Hello,

This is a confirmation email for your access to TINA – Tax Information Navigation Assistant.

Your account is now eligible for activation by admin. Kindly wait for confirmation.

Thank you,
TINA Support Team
        """.strip())

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(GMAIL_SENDER, GMAIL_PASSWORD)
            server.send_message(msg)

        return f"✅ Confirmation email sent to {to_email}"
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"
