import openai
import os
import gradio as gr
import sqlite3
import shutil
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from dotenv import load_dotenv
from difflib import SequenceMatcher
import hashlib
import bcrypt
import csv
from datetime import datetime, timedelta
import json

# Load API key from .env
load_dotenv()

ADMIN_PASS = os.getenv("TINA_ADMIN_PASS", "admin")
openai.api_key = os.getenv("OPENAI_API_KEY")

conn = sqlite3.connect("query_log.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS logs (
    username TEXT,
    query TEXT,
    context TEXT,
    response TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS summaries (
    hash TEXT PRIMARY KEY,
    summary TEXT
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS subscribers (
    username TEXT PRIMARY KEY,
    password TEXT,
    subscription_level TEXT DEFAULT 'free',
    subscription_expires TEXT DEFAULT ''
)
""")
conn.commit()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

PLAN_DURATIONS = {
    "monthly": 30,
    "quarterly": 90,
    "annual": 365
}

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE_MB = 5

GUEST_LIMIT = 5

session = {}

def is_valid_file(file):
    ext = os.path.splitext(file.name)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, "Invalid file type. Allowed: PDF, TXT, MD, JPG, PNG."
    file.seek(0, os.SEEK_END)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)
    if size_mb > MAX_FILE_SIZE_MB:
        return False, f"File too large. Max size: {MAX_FILE_SIZE_MB}MB."
    return True, ""

def save_uploaded_file(file):
    if file:
        is_valid, error = is_valid_file(file)
        if not is_valid:
            return None, error
        save_path = os.path.join(UPLOAD_DIR, file.name)
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file, f)
        return save_path, ""
    return None, "No file uploaded."

def view_logs(user_filter="", date_filter=""):
    conn = sqlite3.connect("query_log.db")
    cursor = conn.cursor()
    query = "SELECT rowid, username, query, response, timestamp FROM logs"
    conditions = []
    params = []
    if user_filter:
        conditions.append("username = ?")
        params.append(user_filter)
    if date_filter:
        conditions.append("date(timestamp) = ?")
        params.append(date_filter)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY timestamp DESC LIMIT 100"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return "\n\n".join([f"[ID {r[0]}] [{r[4]}] {r[1]}: Q: {r[2]}\nA: {r[3]}" for r in rows]) or "No logs found."

def delete_log_by_id(log_id):
    conn = sqlite3.connect("query_log.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM logs WHERE rowid = ?", (log_id,))
    conn.commit()
    conn.close()
    return f"Log entry ID {log_id} deleted."

def export_logs_csv():
    conn = sqlite3.connect("query_log.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs")
    rows = cursor.fetchall()
    headers = [d[0] for d in cursor.description]
    csv_path = os.path.join(UPLOAD_DIR, "logs_export.csv")
    with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    conn.close()
    return csv_path

def view_summaries():
    conn = sqlite3.connect("query_log.db")
    cursor = conn.cursor()
    cursor.execute("SELECT hash, summary FROM summaries ORDER BY ROWID DESC LIMIT 100")
    rows = cursor.fetchall()
    conn.close()
    return "\n\n".join([f"{r[0][:10]}...: {r[1]}" for r in rows]) or "No summaries found."

def get_guest_usage():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("query_log.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM logs WHERE username = 'guest' AND date(timestamp) = ?", (today,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def enforce_guest_limit():
    return get_guest_usage() >= GUEST_LIMIT

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def login_user(user, pw):
    conn = sqlite3.connect("query_log.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password, subscription_level, subscription_expires FROM subscribers WHERE username = ?", (user,))
    row = cursor.fetchone()
    conn.close()
    if row and verify_password(pw, row[0]):
        expires = row[2] or ""
        plan = row[1]
        if expires and datetime.strptime(expires, "%Y-%m-%d") < datetime.now():
            return None, "Subscription expired."
        session["username"] = user
        session["plan"] = plan
        session["expires"] = expires
        return f"Logged in as {user} | Plan: {plan} | Expires: {expires}", ""
    return None, "Invalid credentials."

def renew_subscription(user, plan):
    duration = PLAN_DURATIONS.get(plan)
    if not duration:
        return f"Invalid plan: {plan}"
    new_expiry = (datetime.now() + timedelta(days=duration)).strftime("%Y-%m-%d")
    conn = sqlite3.connect("query_log.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE subscribers SET subscription_level = ?, subscription_expires = ? WHERE username = ?", (plan, new_expiry, user))
    conn.commit()
    conn.close()
    return f"Subscription for {user} renewed to {plan} until {new_expiry}."

# Fixed import: removed broken from-import
# Use openai.ChatCompletion.create() instead of direct import
