import sqlite3
from datetime import datetime, timedelta

DB_NAME = "tina_users.db"

# 🔧 Initialize database and create tables

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            subscription TEXT,
            expires TEXT,
            confirmed INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            amount REAL,
            method TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ➕ Add new user

def add_user(username, password, email, subscription):
    days = {"Monthly (₱150)": 30, "Quarterly (₱400)": 90, "Yearly (₱1500)": 365}.get(subscription, 30)
    expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password, email, subscription, expires) VALUES (?, ?, ?, ?, ?)",
              (username, password, email, subscription, expires))
    conn.commit()
    conn.close()

# 🔍 Get user info

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
            "subscription": row[3],
            "expires": row[4],
            "confirmed": bool(row[5])
        }
    return None

# ✅ Update subscription expiration

def update_subscription(username, days):
    new_expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET expires = ? WHERE username = ?", (new_expiry, username))
    conn.commit()
    conn.close()

# ✅ Confirm email

def confirm_user_email(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET confirmed = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()

# 💰 Record payment

def record_payment(username, amount, method):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO payments (username, amount, method, timestamp) VALUES (?, ?, ?, ?)",
              (username, amount, method, timestamp))
    conn.commit()
    conn.close()
