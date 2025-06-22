import bcrypt
import sqlite3
from datetime import datetime, timedelta
from database import get_conn

RATE_LIMIT = {}
MAX_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=10)

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def is_locked_out(user):
    record = RATE_LIMIT.get(user)
    if not record:
        return False
    attempts, last_attempt = record
    if attempts >= MAX_ATTEMPTS:
        if datetime.now() - last_attempt < LOCKOUT_DURATION:
            return True
        else:
            RATE_LIMIT[user] = (0, datetime.now())  # Reset after lockout duration
    return False

def record_attempt(user):
    attempts, last_time = RATE_LIMIT.get(user, (0, datetime.now()))
    if datetime.now() - last_time > LOCKOUT_DURATION:
        RATE_LIMIT[user] = (1, datetime.now())
    else:
        RATE_LIMIT[user] = (attempts + 1, datetime.now())

def login_user(user, pw):
    if is_locked_out(user):
        return None, f"Too many failed attempts. Try again later."

    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password, subscription_level, subscription_expires FROM subscribers WHERE username = ?", (user,))
        row = cursor.fetchone()
        if row and verify_password(pw, row[0]):
            RATE_LIMIT[user] = (0, datetime.now())  # Reset counter on success
            expires = row[2] or ""
            plan = row[1]
            return f"Logged in as {user} | Plan: {plan} | Expires: {expires}", ""
        else:
            record_attempt(user)
            return None, "Invalid credentials."

def signup_user(user, pw):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM subscribers WHERE username = ?", (user,))
        if cursor.fetchone():
            return "Username already exists."
        hashed = hash_password(pw)
        cursor.execute("INSERT INTO subscribers (username, password) VALUES (?, ?)", (user, hashed))
        conn.commit()
        return "Signup successful. Please login."

def renew_subscription(user, plan):
    PLAN_DURATIONS = {"monthly": 30, "quarterly": 90, "annual": 365}
    duration = PLAN_DURATIONS.get(plan)
    if not duration:
        return f"Invalid plan: {plan}"
    new_expiry = (datetime.now() + timedelta(days=duration)).strftime("%Y-%m-%d")
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE subscribers SET subscription_level = ?, subscription_expires = ? WHERE username = ?",
                       (plan, new_expiry, user))
        conn.commit()
    return f"Subscription for {user} renewed to {plan} until {new_expiry}."
