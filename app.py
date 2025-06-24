#-------------app.py------------
import gradio as gr
import time
import os
import logging
import hashlib
import openai
from functools import lru_cache
from file_utils import (
    save_file,
    is_valid_file,
    extract_text_from_file,
    semantic_search,
    index_document,
    load_or_create_faiss_index
)
from auth import authenticate_user, register_user, is_admin
from database import log_query, get_conn, init_db, store_file_text

openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai

try:
    init_db()
except Exception as e:
    logging.error(f"❌ Failed to initialize database: {e}")
    raise SystemExit("Database initialization failed. Please check database.py setup.")

load_or_create_faiss_index()

SESSION_TIMEOUT = 1800
MAX_GUEST_QUESTIONS = 5

@lru_cache(maxsize=32)
def fallback_to_chatgpt(prompt: str) -> str:
    logging.warning("Fallback to ChatGPT activated.")
    if not client:
        return "[OpenAI API not configured]"
    for attempt in range(3):
        try:
            response = client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message["content"].strip()
        except Exception as e:
            logging.error(f"[ChatGPT Retry {attempt+1}] {e}")
            time.sleep(1.5)
    return f"[ChatGPT Error] All retries failed."

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

def handle_ask(question):
    if not is_tax_related(question):
        return gr.update(value="❌ TINA only answers questions related to Philippine taxation. Please refine your question."), gr.update(visible=False)

    used = count_guest_queries()
    if used >= MAX_GUEST_QUESTIONS:
        return gr.update(visible=False), gr.update(value="❌ Guest users can only ask up to 5 questions. Please sign up to continue.", visible=True), gr.Tabs.update(selected=1)

    try:
        results = semantic_search(question)
        source = "semantic"
    except Exception as e:
        logging.warning(f"[Fallback] Semantic search error: {e}")
        fallback_answer = fallback_to_chatgpt(question)
        source = "chatgpt"
        results = [fallback_answer]

        content_hash = hashlib.sha256(fallback_answer.encode("utf-8")).hexdigest()
        filename = f"chatgpt_{content_hash}.txt"
        path = os.path.join("knowledge_files", filename)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(fallback_answer)
            index_document(fallback_answer)
            store_file_text(filename, fallback_answer)

    answer = "\n\n---\n\n".join(results)
    log_query("guest", question, source, answer)
    remaining = MAX_GUEST_QUESTIONS - used - 1
    return gr.update(value=answer + f"\n\n📌 You have {remaining}/5 questions remaining as a guest."), gr.update(visible=False), gr.Tabs.update(selected=0)

# UI with login/register and Ask tab
with gr.Blocks() as interface:
    gr.Markdown("# 🇵🇭 TINA: Tax Info Navigation Assistant")
    login_state = gr.State("")

    with gr.Tabs() as tabs:
        with gr.Tab("Login", id=0):
            login_user = gr.Textbox(label="Username")
            login_pass = gr.Textbox(label="Password", type="password")
            login_result = gr.Textbox(label="Login Result")

            def handle_login(u, p):
                role = authenticate_user(u, p)
                if not role:
                    return "❌ Login failed.", ""
                return f"✅ Logged in as {role}", u

            login_btn = gr.Button("Login")
            login_btn.click(handle_login, [login_user, login_pass], [login_result, login_state])

            logout_btn = gr.Button("Logout")
            def handle_logout():
                return "Logged out.", ""
            logout_btn.click(fn=handle_logout, inputs=None, outputs=[login_result, login_state])

        with gr.Tab("Ask TINA", id=1):
            q = gr.Textbox(label="Ask a Tax Question")
            a = gr.Textbox(label="Answer")
            q.submit(fn=handle_ask, inputs=q, outputs=a)

        with gr.Tab("Admin Upload", id=2):
            file_upload = gr.File(label="Upload File", file_types=['.pdf', '.txt', '.jpg', '.png', '.docx'])
            upload_result = gr.Textbox(label="Upload Status")

            def handle_upload(file, user):
                if not is_admin(user):
                    return "❌ Only admin can upload."
                if not is_valid_file(file.name):
                    return "❌ Invalid file type."
                path, _ = save_file(file)
                extracted = extract_text_from_file(path)
                index_document(extracted)
                store_file_text(file.name, extracted)
                return f"✅ Uploaded and indexed: {file.name}"

            upload_btn = gr.Button("Upload")
            upload_btn.click(fn=handle_upload, inputs=[file_upload, login_state], outputs=upload_result)

# Required for Hugging Face Spaces

def launch():
    return interface

if __name__ == "__main__":
    interface.launch()
