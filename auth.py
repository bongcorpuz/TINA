# ------------------ auth.py ------------------
import bcrypt
import sqlite3
from datetime import datetime, timedelta
from database import get_conn

RATE_LIMIT = {}
MAX_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=10)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def is_locked_out(user: str) -> bool:
    record = RATE_LIMIT.get(user)
    if not record:
        return False
    attempts, last_attempt = record
    if attempts >= MAX_ATTEMPTS:
        if datetime.now() - last_attempt < LOCKOUT_DURATION:
            return True
        RATE_LIMIT[user] = (0, datetime.now())
    return False

def record_attempt(user: str) -> None:
    attempts, last_time = RATE_LIMIT.get(user, (0, datetime.now()))
    if datetime.now() - last_time > LOCKOUT_DURATION:
        RATE_LIMIT[user] = (1, datetime.now())
    else:
        RATE_LIMIT[user] = (attempts + 1, datetime.now())

def authenticate_user(username: str, password: str) -> str | None:
    if is_locked_out(username):
        return None
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM subscribers WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row and verify_password(password, row[0]):
            RATE_LIMIT[username] = (0, datetime.now())
            return "admin" if username == "admin" else "user"
        record_attempt(username)
        return None

def register_user(username: str, password: str) -> bool:
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM subscribers WHERE username = ?", (username,))
        if cursor.fetchone():
            return False
        hashed = hash_password(password)
        cursor.execute("INSERT INTO subscribers (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        return True

def login_user(user: str, pw: str) -> tuple[str | None, str]:
    if is_locked_out(user):
        return None, "Too many failed attempts. Try again later."
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password, subscription_level, subscription_expires FROM subscribers WHERE username = ?", (user,))
        row = cursor.fetchone()
        if row and verify_password(pw, row[0]):
            RATE_LIMIT[user] = (0, datetime.now())
            expires = row[2] or ""
            return f"Logged in as {user} | Plan: {row[1]} | Expires: {expires}", ""
        record_attempt(user)
        return None, "Invalid credentials."

def renew_subscription(user: str, plan: str) -> str:
    PLAN_DURATIONS = {"monthly": 30, "quarterly": 90, "annual": 365}
    duration = PLAN_DURATIONS.get(plan)
    if not duration:
        return f"Invalid plan: {plan}"
    new_expiry = (datetime.now() + timedelta(days=duration)).strftime("%Y-%m-%d")
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE subscribers 
            SET subscription_level = ?, subscription_expires = ? 
            WHERE username = ?
        """, (plan, new_expiry, user))
        conn.commit()
    return f"Subscription for {user} renewed to {plan} until {new_expiry}."

def is_admin(username: str) -> bool:
    return username == "admin"