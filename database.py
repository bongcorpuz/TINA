# database.py
import sqlite3
from datetime import datetime, timedelta

DB_NAME = "tina_users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            email TEXT,
            role TEXT,
            subscription_plan TEXT,
            expiration_date TEXT,
            is_confirmed INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password, email, role, plan):
    expiration = datetime.now() + {
        'Monthly': timedelta(days=30),
        'Quarterly': timedelta(days=90),
        'Yearly': timedelta(days=365),
    }.get(plan, timedelta(days=30))
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, 0)",
              (username, password, email, role, plan, expiration.strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

# email_confirm.py
import smtplib
from email.message import EmailMessage

def send_confirmation_email(to_email, username):
    msg = EmailMessage()
    msg['Subject'] = 'Confirm your TINA Premium Account'
    msg['From'] = 'your.email@example.com'
    msg['To'] = to_email
    msg.set_content(f"""
Hi {username},

Please confirm your premium access by replying to this email or clicking the link below (in future upgrade).

Thank you,
TINA Support Team
""")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login('your.email@example.com', 'your_app_password')
            smtp.send_message(msg)
        return True
    except Exception as e:
        print("Email error:", e)
        return False
