 import sqlite3
from datetime import datetime, timedelta
import bcrypt
import logging
import os

DB_NAME = "tina_users.db"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        email_confirmed INTEGER DEFAULT 0,
        subscription_level TEXT CHECK(subscription_level IN ('monthly', 'quarterly', 'yearly')) NOT NULL,
        subscription_expires TEXT NOT NULL,
        role TEXT DEFAULT 'user' CHECK(role IN ('user', 'admin', 'premium')),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # Trigger for updated_at timestamp
    c.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_update_timestamp
    AFTER UPDATE ON users
    BEGIN
        UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
    """)
    # Indexes for performance
    c.execute("CREATE INDEX IF NOT EXISTS idx_username ON users(username)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_email ON users(email)")
    conn.commit()
    conn.close()
    logging.info("Database initialized successfully.")

    # Auto-create admin account if not exists
    create_default_admin()

# Hash password securely
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Verify password
def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Add new user
def add_user(username, password, email, subscription_level):
    days = {'monthly': 30, 'quarterly': 90, 'yearly': 365}
    if subscription_level not in days:
        logging.warning("Invalid subscription level provided.")
        return False
    expires = (datetime.now() + timedelta(days=days[subscription_level])).strftime("%Y-%m-%d")
    hashed_pw = hash_password(password)
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, email, subscription_level, subscription_expires) VALUES (?, ?, ?, ?, ?)",
                  (username, hashed_pw, email, subscription_level, expires))
        conn.commit()
        conn.close()
        logging.info(f"User {username} added successfully.")
        return True
    except sqlite3.IntegrityError as e:
        logging.error(f"Failed to add user {username}: {e}")
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
            "role": row[7],
            "created_at": row[8],
            "updated_at": row[9]
        }
    return None

# Update subscription manually (admin use)
def update_subscription(username, new_level):
    days = {'monthly': 30, 'quarterly': 90, 'yearly': 365}
    if new_level not in days:
        logging.warning("Invalid subscription level provided for update.")
        return
    expires = (datetime.now() + timedelta(days=days[new_level])).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET subscription_level = ?, subscription_expires = ? WHERE username = ?",
              (new_level, expires, username))
    conn.commit()
    conn.close()
    logging.info(f"Subscription updated for {username} to {new_level}.")

# Confirm user's email
def confirm_email(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET email_confirmed = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    logging.info(f"Email confirmed for user {username}.")

# Automatically create a default admin account if not present
def create_default_admin():
    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin@1971")
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "info@bongcorpuz.com")

    user = get_user(admin_username)
    if user is None:
        add_user(admin_username, admin_password, admin_email, "yearly")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET role = 'admin' WHERE username = ?", (admin_username,))
        conn.commit()
        conn.close()
        logging.info("Default admin account created.")
