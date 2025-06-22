# file: app.py

import os
import sqlite3
from datetime import datetime
import bcrypt
import logging
from dotenv import load_dotenv
import gradio as gr
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from openai import OpenAI  # updated

# ========== CONFIGURATION ==========
load_dotenv()
client = OpenAI()  # updated OpenAI client
DB_NAME = "tina_users.db"
REFERENCE_FILE = "reference_text.txt"
logging.basicConfig(level=logging.INFO)

# ========== DATABASE SETUP ==========
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
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS qna_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        source TEXT DEFAULT 'chatGPT',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()
    logging.info("Database initialized.")

# ========== HELPERS ==========
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def is_valid_tax_question(text):
    keywords = os.getenv("TAX_KEYWORDS", "tax,vat,bir,rdo,tin,withholding,income tax,1701,1702,2550,0605,0619,form,return,compliance,Philippine taxation,CREATE law,TRAIN law,ease of paying taxes").split(",")
    return any(k.lower() in text.lower() for k in keywords)

def save_qna(question, answer, source="chatGPT"):
    if not is_valid_tax_question(question):
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO qna_log (question, answer, source) VALUES (?, ?, ?)", (question, answer, source))
    conn.commit()
    conn.close()

def extract_text_from_file(file):
    try:
        file_path = file.name if hasattr(file, "name") else file
        ext = os.path.splitext(file_path)[1].lower()
        content = ""

        if ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        elif ext == ".pdf":
            with open(file_path, "rb") as f:
                pdf = fitz.open(stream=f.read(), filetype="pdf")
                content = "\n".join([page.get_text() for page in pdf])
        elif ext in [".jpg", ".jpeg", ".png"]:
            img = Image.open(file_path)
            content = pytesseract.image_to_string(img)

        if content.strip():
            with open(REFERENCE_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n--- Uploaded {datetime.now()} ---\n{content}\n")
            return "File content processed and saved."
        return "No readable content found in uploaded file."
    except Exception as e:
        logging.exception("File extraction failed: %s", e)
        return f"Error processing file: {e}"

def load_reference_text():
    if os.path.exists(REFERENCE_FILE):
        with open(REFERENCE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return ""

# ========== OPENAI CHAT ==========
SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You are helpful, polite, and specialize in answering questions about Philippine taxation. "
    "Base your responses on publicly available tax laws such as the NIRC, BIR Revenue Regulations, RMCs, "
    "and tax reform laws like TRAIN, CREATE, and Ease of Paying Taxes Act. Do not offer legal advice."
)

def ask_tina(question, username="User"):
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]

        ref = load_reference_text()
        if ref:
            messages.insert(1, {"role": "system", "content": f"Reference material:\n{ref[:3000]}"})

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        answer = response.choices[0].message.content
        save_qna(question, answer, source="chatGPT+ref" if ref else "chatGPT")
        return answer.strip()
    except Exception as e:
        logging.exception("ask_tina failed: %s", e)
        return f"Sorry, something went wrong: {e}"

init_db()

# ========== GRADIO UI ==========
with gr.Blocks() as demo:
    chatbot = gr.Chatbot(label="TINA Chat", value=[], elem_id="chatbot", type="markdown")
    file_upload = gr.File(label="Upload Reference Files (.txt, .md, .pdf, .jpg, .jpeg, .png)")
    user_input = gr.Textbox(placeholder="Type your tax question and press Enter", label="Your Question")

    def handle_file(file):
        return extract_text_from_file(file)

    def handle_chat(message, history):
        answer = ask_tina(message)
        history = history or []
        history.append((message, answer))
        return history

    file_upload.change(fn=handle_file, inputs=file_upload, outputs=chatbot)
    user_input.submit(fn=handle_chat, inputs=[user_input, chatbot], outputs=chatbot)

demo.launch()
