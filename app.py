import sqlite3
import os
from dotenv import load_dotenv

# ✅ Load .env for database path
load_dotenv()
DB_PATH = os.getenv("DATABASE_PATH", "users.db")

# ✅ Initialize the SQLite database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            subscription_expires TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# ✅ Add a new user
def add_user(username, password, days_valid):
    from datetime import datetime, timedelta
    expiration = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, subscription_expires) VALUES (?, ?, ?)",
                  (username, password, expiration))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

# ✅ Fetch user data by username
def get_user(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user

# ✅ Update user's subscription
def update_subscription(username, days_valid):
    from datetime import datetime, timedelta
    new_expiration = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET subscription_expires = ? WHERE username = ?",
              (new_expiration, username))
    conn.commit()
    conn.close()
