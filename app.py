import os
import sqlite3
from datetime import datetime, timedelta
import bcrypt
import logging
from dotenv import load_dotenv
import gradio as gr
import openai

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

DB_NAME = "tina_users.db"
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

def ask_tina(question, username="User"):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ]
        )
        answer = response.choices[0].message["content"]
        save_qna(question, answer)
        return answer.strip()
    except Exception as e:
        return f"Sorry, something went wrong: {e}"

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
        name = gr.Textbox(label="Enter your name", interactive=True)
        greet_btn = gr.Button("Greet Me")
        greeting = gr.Textbox(label="Greeting", interactive=False)
        proceed_btn = gr.Button("Proceed to TINA", visible=False)

    with gr.Column(visible=False) as chat_section:
        gr.Markdown("### Ask TINA your tax-related questions!")
        chatbot = gr.Chatbot(label="TINA Chat", height=350)
        question = gr.Textbox(label="Your Question", placeholder="Type your tax question here and press Enter")
        submit_btn = gr.Button("Ask TINA")

    state_name = gr.State()
    state_history = gr.State([])

    greet_btn.click(fn=greet, inputs=name, outputs=[greeting, proceed_btn, greeting])
    proceed_btn.click(fn=proceed_to_tina, inputs=name, outputs=[greet_section, proceed_btn, chat_section, state_name])
    submit_btn.click(fn=tina_chat, inputs=[question, state_name, chatbot], outputs=[question, chatbot])
    question.submit(fn=tina_chat, inputs=[question, state_name, chatbot], outputs=[question, chatbot])

# Initialize DB only once when app starts
init_db()

demo.launch()
