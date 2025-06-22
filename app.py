import os
import sqlite3
from datetime import datetime
import bcrypt
import logging
from dotenv import load_dotenv
import gradio as gr
import openai
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
DB_NAME = "tina_users.db"
REFERENCE_FILE = "reference_text.txt"
logging.basicConfig(level=logging.INFO)

# ========== DATABASE ==========
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
    if not is_valid_tax_question(question): return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO qna_log (question, answer, source) VALUES (?, ?, ?)", (question, answer, source))
    conn.commit()
    conn.close()

def extract_text_from_file(file):
    ext = os.path.splitext(file.name)[1].lower()
    content = ""

    if ext in [".txt", ".md"]:
        content = file.read().decode("utf-8")
    elif ext == ".pdf":
        pdf = fitz.open(stream=file.read(), filetype="pdf")
        content = "\n".join([page.get_text() for page in pdf])
    elif ext in [".jpg", ".jpeg", ".png"]:
        img = Image.open(file)
        content = pytesseract.image_to_string(img)
    
    if content.strip():
        with open(REFERENCE_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n--- Uploaded {datetime.now()} ---\n{content}\n")
        return "File content processed and saved."
    return "No readable content found in uploaded file."

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
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        ref = load_reference_text()
        if ref:
            messages.append({"role": "system", "content": f"Reference material:\n{ref[:3000]}"})
        messages.append({"role": "user", "content": question})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        answer = response.choices[0].message["content"]
        save_qna(question, answer, source="chatGPT+ref" if ref else "chatGPT")
        return answer.strip()
    except Exception as e:
        return f"Sorry, something went wrong: {e}"

# ========== UI HANDLERS ==========
def greet(name):
    return f"Hello, {name}! Welcome to TINA.", gr.update(visible=True), gr.update(visible=True)

def proceed_to_tina(name):
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), name

def tina_chat(question, username, history):
    answer = ask_tina(question, username)
    history = history or []
    history.append((question, answer))
    return "", history

def handle_upload(files):
    return "\n".join([extract_text_from_file(f) for f in files])

# ========== LAUNCH UI ==========
init_db()

with gr.Blocks() as demo:
    gr.Markdown("# TINA: Tax Information Navigation Assistance")

    with gr.Column(visible=True) as greet_section:
        name = gr.Textbox(label="Enter your name")
        greet_btn = gr.Button("Greet Me")
        greeting = gr.Textbox(label="Greeting", interactive=False)
        proceed_btn = gr.Button("Proceed to TINA", visible=False)

    with gr.Column(visible=False) as chat_section:
        gr.Markdown("### Ask TINA your tax-related questions!")
        chatbot = gr.Chatbot(label="TINA Chat", value=[], type="messages")
        question = gr.Textbox(label="Your Question", placeholder="Type your tax question and press Enter")
        submit_btn = gr.Button("Ask TINA")
        upload = gr.File(label="Upload Reference Files (.txt, .md, .pdf, .jpg, .jpeg, .png)",
                         file_types=[".txt", ".md", ".pdf", ".jpg", ".jpeg", ".png"],
                         file_count="multiple")
        upload_status = gr.Textbox(label="Upload Result", interactive=False)

    state_name = gr.State()
    state_history = gr.State([])

    greet_btn.click(fn=greet, inputs=name, outputs=[greeting, proceed_btn, greeting])
    proceed_btn.click(fn=proceed_to_tina, inputs=name, outputs=[greet_section, proceed_btn, chat_section, state_name])
    submit_btn.click(fn=tina_chat, inputs=[question, state_name, chatbot], outputs=[question, chatbot])
    question.submit(fn=tina_chat, inputs=[question, state_name, chatbot], outputs=[question, chatbot])
    upload.change(fn=handle_upload, inputs=upload, outputs=upload_status)

# ✅ Required for Hugging Face Spaces — no `.launch()`
demo.queue()
