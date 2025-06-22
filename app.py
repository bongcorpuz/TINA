import os
import sqlite3
from datetime import datetime, timedelta
import bcrypt
import logging
from dotenv import load_dotenv
import gradio as gr
import openai
import pytesseract
from PIL import Image
import fitz  # PyMuPDF

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

DB_NAME = "tina_users.db"
KNOWLEDGE_FOLDER = "knowledge_files"
os.makedirs(KNOWLEDGE_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO)

# ========== DATABASE SETUP ==========
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
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
    c.execute("""CREATE TABLE IF NOT EXISTS qna_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        source TEXT DEFAULT 'chatGPT',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()
    logging.info("Database initialized.")

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

# ========== OPENAI LOGIC ==========
SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You are helpful, polite, and specialize in answering questions about Philippine taxation. "
    "Base your responses on publicly available tax laws such as the NIRC, BIR Revenue Regulations, RMCs, "
    "and tax reform laws like TRAIN, CREATE, and Ease of Paying Taxes Act. Do not offer legal advice."
)

def read_knowledge_files():
    texts = []
    for fname in os.listdir(KNOWLEDGE_FOLDER):
        path = os.path.join(KNOWLEDGE_FOLDER, fname)
        try:
            if fname.endswith((".txt", ".md")):
                with open(path, "r", encoding="utf-8") as f:
                    texts.append(f.read())
            elif fname.endswith(".pdf"):
                doc = fitz.open(path)
                text = "\n".join([page.get_text() for page in doc])
                texts.append(text)
            elif fname.endswith((".png", ".jpg", ".jpeg")):
                image = Image.open(path)
                texts.append(pytesseract.image_to_string(image))
        except Exception as e:
            logging.warning(f"Failed to read {fname}: {e}")
    return "\n".join(texts)

def ask_tina(question, username="User"):
    try:
        context = read_knowledge_files()
        if context.strip():
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Refer to the following data:\n{context}\n\nNow answer: {question}"}
            ]
        else:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ]
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
        answer = response.choices[0].message["content"]
        save_qna(question, answer, source="knowledge" if context else "chatGPT")
        return answer.strip()
    except Exception as e:
        return f"Sorry, something went wrong: {e}"

def upload_and_convert(files):
    for file in files:
        ext = os.path.splitext(file.name)[1].lower()
        dest_path = os.path.join(KNOWLEDGE_FOLDER, os.path.basename(file.name))
        with open(dest_path, "wb") as f:
            f.write(file.read())
    return "Files uploaded and processed successfully."

# ========== GRADIO UI ==========
def greet(name):
    return f"Hello, {name}! Welcome to TINA.", gr.update(visible=True), gr.update(visible=True)

def proceed_to_tina(name):
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.State(name)

def tina_chat(question, state_name, history):
    username = state_name or "User"
    answer = ask_tina(question, username)
    history = history or []
    history.append((question, answer))
    return "", history

with gr.Blocks() as demo:
    gr.Markdown("# TINA: Tax Information Navigation Assistance")

    with gr.Column(visible=True) as greet_section:
        name = gr.Textbox(label="Enter your name")
        greet_btn = gr.Button("Greet Me")
        greeting = gr.Textbox(label="Greeting", interactive=False)
        proceed_btn = gr.Button("Proceed to TINA", visible=False)

    with gr.Column(visible=False) as chat_section:
        gr.Markdown("### Ask TINA your tax-related questions!")
        chatbot = gr.Chatbot(label="TINA Chat", height=350)
        question = gr.Textbox(label="Your Question", placeholder="Type your tax question here and press Enter")
        submit_btn = gr.Button("Ask TINA")
        upload = gr.File(label="Upload Reference Files", file_types=[".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png"], file_count="multiple")
        upload_btn = gr.Button("Upload Files")

    state_name = gr.State()
    state_history = gr.State([])

    greet_btn.click(fn=greet, inputs=name, outputs=[greeting, proceed_btn, greeting])
    proceed_btn.click(fn=proceed_to_tina, inputs=name, outputs=[greet_section, proceed_btn, chat_section, state_name])
    submit_btn.click(fn=tina_chat, inputs=[question, state_name, chatbot], outputs=[question, chatbot])
    question.submit(fn=tina_chat, inputs=[question, state_name, chatbot], outputs=[question, chatbot])
    upload_btn.click(fn=upload_and_convert, inputs=upload, outputs=None)

init_db()
demo.launch()
