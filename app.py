import os
import sqlite3
from datetime import datetime, timedelta
import bcrypt
import logging
from dotenv import load_dotenv
from PIL import Image
import pytesseract
import fitz  # PyMuPDF
import gradio as gr
import openai

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

DB_NAME = "tina_users.db"
KNOWLEDGE_FOLDER = "knowledge_files"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
os.makedirs(KNOWLEDGE_FOLDER, exist_ok=True)

# === DATABASE INIT ===
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
    c.execute("""
    CREATE TABLE IF NOT EXISTS qna_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        source TEXT DEFAULT 'chatGPT',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_update_timestamp
    AFTER UPDATE ON users
    BEGIN
        UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
    """)
    conn.commit()
    conn.close()
    create_default_admin()
    logging.info("Database initialized successfully.")

def create_default_admin():
    username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    if get_user(username) is None:
        add_user(username, password, email, "yearly")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET role = 'admin' WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        logging.info("Default admin account created.")

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def add_user(username, password, email, subscription_level):
    days = {"monthly": 30, "quarterly": 90, "yearly": 365}
    expires = (datetime.now() + timedelta(days=days[subscription_level])).strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, email, subscription_level, subscription_expires) VALUES (?, ?, ?, ?, ?)",
                  (username, hash_password(password), email, subscription_level, expires))
        conn.commit()
        conn.close()
        logging.info(f"User {username} added.")
    except sqlite3.IntegrityError:
        logging.warning(f"User {username} already exists.")

def get_user(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    return row

def is_valid_tax_question(text):
    keywords = os.getenv("TAX_KEYWORDS", "tax,vat,bir,rdo,tin,withholding,income tax,1701,1702,2550,0605,0619,form,return,compliance,Philippine taxation,CREATE law,TRAIN law,ease of paying taxes").split(",")
    return any(k.lower() in text.lower() for k in keywords)

def save_qna(question, answer, source="chatGPT"):
    if not is_valid_tax_question(question): return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO qna_log (question, answer, source) VALUES (?, ?, ?)", (question, answer, source))
    conn.commit()
    conn.close()

# === OPENAI LOGIC ===
SYSTEM_PROMPT = """
You are TINA, the Tax Information Navigation Assistant.
You are helpful, polite, and specialize in answering questions about Philippine taxation.
Base your responses on publicly available tax laws such as the NIRC, BIR Revenue Regulations, RMCs,
and tax reform laws like TRAIN, CREATE, and Ease of Paying Taxes Act. Do not offer legal advice.
"""

def query_openai(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ]
        )
        reply = response.choices[0].message["content"].strip()
        save_qna(message, reply)
        return reply
    except Exception as e:
        logging.error(f"OpenAI Error: {e}")
        return "Sorry, I encountered an error while processing your request."

# === GRADIO UI ===
def chat_interface(message):
    return query_openai(message)

init_db()
ui = gr.Interface(fn=chat_interface, inputs="text", outputs="text", title="TINA - PH Tax Chatbot")
ui.launch()
