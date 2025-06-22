import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# 🔐 SMTP configuration - Set these in your environment for security
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "your_email@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your_email_password")

# 🌐 Email sender details
FROM_NAME = "TINA AI Support"
FROM_EMAIL = SMTP_USERNAME

def send_confirmation_email(to_email):
    subject = "Confirm your TINA Premium Subscription"
    confirmation_link = f"https://your-domain.com/confirm?email={to_email}"
    body = f"""
    Hello,

    Thank you for registering for premium access to TINA – Tax Information Navigation Assistant.

    Please confirm your email address by clicking the link below:

    👉 {confirmation_link}

    If you did not request this, kindly ignore this email.

    Regards,  
    TINA AI Support Team
    """

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"✅ Confirmation email sent to {to_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False
