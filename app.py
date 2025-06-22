from openai import OpenAI
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
import openai
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

def register_user(username, password):
    try:
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        c.execute("INSERT INTO subscribers (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        return "Registration successful."
    except:
        return "Username already exists."

def login_user(username, password):
    c.execute("SELECT password FROM subscribers WHERE username = ?", (username,))
    row = c.fetchone()
    return row and bcrypt.checkpw(password.encode(), row[0].encode())

def check_subscription(username):
    c.execute("SELECT subscription_level, subscription_expires FROM subscribers WHERE username = ?", (username,))
    row = c.fetchone()
    if row:
        level, expires = row
        if expires:
            if datetime.strptime(expires, "%Y-%m-%d") >= datetime.today():
                return True
    return False

def activate_subscription(username, plan):
    if plan not in PLAN_DURATIONS:
        return False
    new_expiry = (datetime.today() + timedelta(days=PLAN_DURATIONS[plan])).strftime("%Y-%m-%d")
    c.execute("UPDATE subscribers SET subscription_level = ?, subscription_expires = ? WHERE username = ?", (plan, new_expiry, username))
    conn.commit()
    return True

def guest_limit_reached():
    today = datetime.today().strftime('%Y-%m-%d')
    c.execute("""
        SELECT COUNT(*) FROM logs
        WHERE username = 'guest' AND DATE(timestamp) = ?
    """, (today,))
    count = c.fetchone()[0]
    return count >= 5, 5 - count

def guest_remaining_count():
    today = datetime.today().strftime('%Y-%m-%d')
    c.execute("SELECT COUNT(*) FROM logs WHERE username = 'guest' AND DATE(timestamp) = ?", (today,))
    count = c.fetchone()[0]
    return max(0, 5 - count)

def save_uploaded_file(file):
    if file:
        save_path = os.path.join(UPLOAD_DIR, file.name)
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file, f)
        return save_path
    return None

def extract_text_from_file(file_path):
    ext = file_path.lower()
    if ext.endswith(".pdf"):
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    elif ext.endswith(".txt") or ext.endswith(".md"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    elif ext.endswith(".jpg") or ext.endswith(".jpeg") or ext.endswith(".png"):
        return pytesseract.image_to_string(Image.open(file_path))
    return ""

def summarize_text(text):
    if not text.strip():
        return ""
    h = hashlib.sha256(text.encode()).hexdigest()
    c.execute("SELECT summary FROM summaries WHERE hash = ?", (h,))
    cached = c.fetchone()
    if cached:
        return cached[0]
    messages = [
        {"role": "system", "content": "Summarize the following document in 3-5 bullet points related to Philippine tax compliance."},
        {"role": "user", "content": text[:3000]}
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        summary = response.choices[0].message['content'].strip()
        c.execute("INSERT INTO summaries (hash, summary) VALUES (?, ?)", (h, summary))
        conn.commit()
        return summary
    except:
        return ""

def aggregate_past_knowledge():
    c.execute("SELECT query, response FROM logs")
    entries = c.fetchall()
    return "\n".join([f"Q: {q}\nA: {a}" for q, a in entries])

def find_similar_query(user_input, threshold=0.85):
    c.execute("SELECT query, response FROM logs")
    for q, a in c.fetchall():
        similarity = SequenceMatcher(None, user_input.lower(), q.lower()).ratio()
        if similarity >= threshold:
            return a
    return None

def chat_with_tina(user_input, file=None, username=None):
    if not username:
        return "Access denied. Please log in."

    if username == "guest":
        limit_reached, remaining = guest_limit_reached()
        if limit_reached:
            return "Daily guest limit reached (5 questions per day). Please register for unlimited access."

    if username != "guest" and not check_subscription(username):
        return "Subscription expired or invalid. Please renew via PayMongo."

    if not any(word in user_input.lower() for word in ["tax", "bir", "rdo", "tin", "vat", "1701", "1702", "2550", "0619", "0605", "return", "compliance", "philippine"]):
        return "Sorry, I can only assist with questions related to Philippine taxation."

    previous = find_similar_query(user_input)
    if previous:
        return previous

    file_path = save_uploaded_file(file)
    raw_context = extract_text_from_file(file_path) if file_path else ""
    context_summary = summarize_text(raw_context) if raw_context else ""

    learned_qa = aggregate_past_knowledge()
    full_context = f"Previous Q&A:\n{learned_qa}\n\nDocument Summary:\n{context_summary}" if learned_qa else context_summary

    system_prompt = (
        "You are TINA, the Tax Information Navigation Assistant. "
        "You ONLY answer questions related to Philippine taxation such as BIR forms, deadlines, tax types, and compliance. "
        "Base your answers strictly on publicly available resources like the NIRC, BIR Revenue Regulations (RRs), Revenue Memorandum Circulars (RMCs), and official BIR issuances. "
        "If asked anything not related to Philippine taxation, politely respond with: "
        "'Sorry, I can only assist with questions related to Philippine taxation.'"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{full_context}\n\n{user_input}" if full_context else user_input}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        answer = response.choices[0].message['content'].strip()
        c.execute("INSERT INTO logs (username, query, context, response) VALUES (?, ?, ?, ?)", (username, user_input, full_context, answer))
        conn.commit()
        return answer
    except Exception as e:
        return f"Error: {e}"

# Interface
with gr.Blocks() as demo:
    username = gr.Textbox(label="Username", placeholder="Enter your username")
    password = gr.Textbox(label="Password", type="password", placeholder="Enter your password")
    login_btn = gr.Button("Login / Continue as Guest")
    file_input = gr.File(label="Upload File (PDF/TXT/IMG, optional)", file_types=[".pdf", ".txt", ".md", ".jpg", ".png"])
    user_query = gr.Textbox(label="Your Tax Question", placeholder="Ask something about PH taxation...")
    submit_btn = gr.Button("Ask TINA")
    output = gr.Textbox(label="TINA's Answer")
    gr.Markdown("👉 No account? Register or upgrade at [your WordPress site].")

    session = {"username": None}

    def handle_login(u, p):
        if u == "guest":
            session["username"] = "guest"
            return "Logged in as guest (limit: 5 questions/day)"
        if login_user(u, p):
            session["username"] = u
            return f"Welcome back, {u}!"
        return "Login failed. Check credentials."

    def handle_submit(question, file):
        if not session.get("username"):
            return "Please log in first."
        return chat_with_tina(question, file=file, username=session["username"])

    login_btn.click(fn=handle_login, inputs=[username, password], outputs=output)
    submit_btn.click(fn=handle_submit, inputs=[user_query, file_input], outputs=output)

demo.launch(share=True)
