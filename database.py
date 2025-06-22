import sqlite3
from datetime import datetime, timedelta

DB_NAME = "tina_users.db"

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        email TEXT,
        email_confirmed INTEGER DEFAULT 0,
        subscription TEXT,
        expires TEXT
    )
    """)
    conn.commit()
    conn.close()

# Add new user
def add_user(username, password, email, subscription_days):
    expires = (datetime.now() + timedelta(days=subscription_days)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (username, password, email, subscription, expires) VALUES (?, ?, ?, ?, ?)",
              (username, password, email, f"{subscription_days} days", expires))
    conn.commit()
    conn.close()

# Get user by username
def get_user(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "username": row[0],
            "password": row[1],
            "email": row[2],
            "email_confirmed": bool(row[3]),
            "subscription": row[4],
            "expires": row[5]
        }
    return None

# Update subscription manually (for admin control)
def update_subscription(username, new_days):
    expires = (datetime.now() + timedelta(days=new_days)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET subscription = ?, expires = ? WHERE username = ?",
              (f"{new_days} days", expires, username))
    conn.commit()
    conn.close()

# Confirm user's email
def confirm_email(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET email_confirmed = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()
