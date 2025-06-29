import os
import fitz
import pdfplumber
import pytesseract
from PIL import Image
from docx import Document
import numpy as np
import faiss
import logging
import shutil
import hashlib
import gradio as gr
import openai
from dotenv import load_dotenv
import re

from sentence_transformers import SentenceTransformer
from file_utils import (
    save_file,
    is_valid_file,
    extract_text_from_file,
    index_document,
    load_or_create_faiss_index,
    learn_from_text
)
from ask_tina import answer_query_with_knowledge
from auth import authenticate_user, register_user, is_admin, send_password_reset, recover_user_email
from database import log_query, get_conn, init_db, store_file_text, has_uploaded_knowledge

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
print("OpenAI API Key Loaded:", openai.api_key)

try:
    init_db()
except Exception as e:
    logging.error(f"❌ Failed to initialize database: {e}")
    raise SystemExit("Database initialization failed.")

load_or_create_faiss_index()

SESSION_TIMEOUT = 1800
MAX_GUEST_QUESTIONS = 5

EMBED_MODEL_PATH = os.getenv("EMBED_MODEL_PATH", "sentence-transformers/all-MiniLM-L6-v2")
model = SentenceTransformer(EMBED_MODEL_PATH)

FAISS_THRESHOLD = 0.45


def is_tax_related(question):
    keyword_file = "tax_keywords.txt"
    keywords = []
    try:
        with open(keyword_file, "r", encoding="utf-8") as f:
            keywords = [line.strip().lower() for line in f if line.strip()]
    except Exception as e:
        logging.warning(f"Keyword file not found or unreadable: {e}")
    q = question.lower()
    return any(word in q for word in keywords)

def count_guest_queries():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM logs WHERE username = 'guest'")
        return c.fetchone()[0]

def score_threshold_fallback(question):
    try:
        query_vec = model.encode([question], convert_to_tensor=False)
        scores, indices = index.search(np.array(query_vec, dtype=np.float32), 3)
        if scores[0][0] > FAISS_THRESHOLD:
            return [], "chatgpt"
        return [knowledge_texts[i] for i in indices[0] if i < len(knowledge_texts)], "faiss"
    except Exception as e:
        logging.warning(f"Semantic search failed: {e}")
        return [], "chatgpt"

def handle_ask(question, user):
    if not is_tax_related(question):
        return gr.update(value="❌ TINA only answers questions related to Philippine taxation."), gr.update(visible=False), gr.update()

    if user == "guest":
        used = count_guest_queries()
        if used >= MAX_GUEST_QUESTIONS:
            return gr.update(value=""), gr.update(value="❌ Guest users can only ask 5 questions."), gr.update()
    else:
        used = 0

    results, source = score_threshold_fallback(question)

    if source == "chatgpt":
        import openai
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": question}]
            )
            results = [completion.choices[0].message.content.strip()]
        except Exception as e:
            logging.error(f"OpenAI call failed: {e}")
            return gr.update(value="❌ Failed to get answer from AI."), gr.update(visible=False), gr.update()

    unique_results = list(dict.fromkeys(results))
    answer = "\n\n---\n\n".join(unique_results)

    if source == "chatgpt":
        learn_from_text(answer)

    log_query(user, question, source, answer)
    remaining = MAX_GUEST_QUESTIONS - used - 1 if user == 'guest' else "∞"
    return gr.update(value=answer + f"\n\n📌 {'Guest questions left: ' + str(remaining) if user == 'guest' else 'Logged in user'}"), gr.update(visible=False), gr.update()

def handle_upload(file, user):
    try:
        if user == "guest" or not user:
            return "❌ Only logged in users can upload."
        if not is_valid_file(file.name):
            return "❌ Invalid file type."

        path, err = save_file(file)
        if not path:
            return err

        text = extract_text_from_file(path)
        index_document(text)
        learn_from_text(text)
        store_file_text(file.name, text)

        return f"✅ Uploaded and indexed: {path} by user: {user}"
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        return "❌ Error"

with gr.Blocks() as interface:
    gr.Markdown("# 🇵🇭 TINA: Tax Information Navigation Assistant")
    login_state = gr.State("guest")

    with gr.Tabs() as tabs:
        with gr.Tab("Login", id=0):
            login_user = gr.Textbox(label="Email")
            login_pass = gr.Textbox(label="Password", type="password")
            login_result = gr.Textbox(label="Login Result")

            def handle_login(u, p):
                profile = authenticate_user(u, p)
                if not profile:
                    return "❌ Login failed.", "guest"
                if "error" in profile:
                    return profile["error"], "guest"
                return f"✅ Logged in as {profile['role']}", profile["email"]

            gr.Button("Login").click(handle_login, [login_user, login_pass], [login_result, login_state])
            gr.Button("Logout").click(fn=lambda: ("Logged out.", "guest"), inputs=None, outputs=[login_result, login_state])

        with gr.Tab("Ask TINA", id=1):
            q = gr.Textbox(label="Ask a Tax Question")
            a = gr.Textbox(label="Answer")
            error_box = gr.Textbox(visible=False)
            q.submit(fn=lambda question, uid: handle_ask(question, uid), inputs=[q, login_state], outputs=[a, error_box, tabs])

        with gr.Tab("Signup", id=2):
            signup_user = gr.Textbox(label="Username")
            signup_email = gr.Textbox(label="Email Address")
            signup_pass = gr.Textbox(label="Password", type="password")
            signup_result = gr.Textbox(label="Signup Result")

            def handle_signup(username, email, password):
                if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                    return "❌ Invalid email format."
                if len(password) < 6:
                    return "❌ Password must be at least 6 characters."
                return register_user(username, email, password)

            gr.Button("Signup").click(handle_signup, [signup_user, signup_email, signup_pass], signup_result)

        with gr.Tab("Reset Password", id=3):
            gr.Markdown("📧 Enter your email to reset password.")
            reset_email = gr.Textbox(label="Email")
            reset_result = gr.Textbox(label="Reset Status")
            gr.Button("Send Reset Email").click(send_password_reset, inputs=reset_email, outputs=reset_result)

        with gr.Tab("Recover Email", id=4):
            gr.Markdown("🔎 Enter your username or part of it to recover email.")
            recover_keyword = gr.Textbox(label="Keyword")
            recover_result = gr.Textbox(label="Possible Matches")
            gr.Button("Search Email").click(
                fn=lambda k: "\n".join(recover_user_email(k)),
                inputs=recover_keyword,
                outputs=recover_result
            )

        with gr.Tab("Help TINA Learn", id=5):
            file_upload = gr.File(label="Upload File", file_types=['.pdf', '.txt', '.jpg', '.png', '.docx', '.doc', '.odt', '.rtf'])
            upload_result = gr.Textbox(label="Upload Status")
            gr.Button("Upload").click(fn=handle_upload, inputs=[file_upload, login_state], outputs=upload_result)

    gr.HTML("""
    <hr>
    <div style='text-align:center; font-size: 14px; color: #555;'>
        <img src='https://www.bongcorpuz.com/favicon.ico' height='20' style='vertical-align:middle;margin-right:8px;'>
        <a href='https://www.bongcorpuz.com' target='_blank'><strong>powered by: Bong Corpuz & Co. CPAs</strong></a>
    </div>
    """)

def launch():
    return interface

if __name__ == "__main__":
    launch().launch()
