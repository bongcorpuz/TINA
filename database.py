import sqlite3
from datetime import datetime, timedelta
import bcrypt

DB_NAME = "tina_users.db"

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        email TEXT UNIQUE,
        email_confirmed INTEGER DEFAULT 0,
        subscription_level TEXT CHECK(subscription_level IN ('monthly', 'quarterly', 'yearly')),
        subscription_expires TEXT,
        role TEXT DEFAULT 'user' CHECK(role IN ('user', 'admin', 'premium'))
    )
    """)
    conn.commit()
    conn.close()

# Hash password securely
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Verify password
def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Add new user
def add_user(username, password, email, subscription_level):
    days = {'monthly': 30, 'quarterly': 90, 'yearly': 365}
    expires = (datetime.now() + timedelta(days=days[subscription_level])).strftime("%Y-%m-%d")
    hashed_pw = hash_password(password)
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, email, subscription_level, subscription_expires, role) VALUES (?, ?, ?, ?, ?, ?)",
                  (username, hashed_pw, email, subscription_level, expires, 'user'))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

# Get user by username
def get_user(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "username": row[1],
            "password": row[2],
            "email": row[3],
            "email_confirmed": bool(row[4]),
            "subscription_level": row[5],
            "subscription_expires": row[6],
            "role": row[7]
        }
    return None

# Update subscription manually (admin use)
def update_subscription(username, new_level):
    days = {'monthly': 30, 'quarterly': 90, 'yearly': 365}
    expires = (datetime.now() + timedelta(days=days[new_level])).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET subscription_level = ?, subscription_expires = ? WHERE username = ?",
              (new_level, expires, username))
    conn.commit()
    conn.close()

# Confirm user's email
def confirm_email(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET email_confirmed = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()
