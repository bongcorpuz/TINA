import gradio as gr
import time
import os
import logging
import hashlib
from functools import lru_cache
import openai
from file_utils import (
    save_file,
    is_valid_file,
    extract_text_from_file,
    semantic_search,
    index_document,
    load_or_create_faiss_index
)
from auth import authenticate_user, register_user, is_admin
from database import log_query, get_conn, init_db, store_file_text, has_uploaded_knowledge

openai.api_key = os.getenv("OPENAI_API_KEY")
print("OpenAI API Key Loaded:", openai.api_key is not None)

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
    last_error = ""
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message["content"].strip()
        except Exception as e:
            last_error = str(e)
            logging.error(f"[ChatGPT Retry {attempt+1}] {last_error}")
            time.sleep(1.5)
    return f"[ChatGPT Error] All retries failed. Reason: {last_error}"

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
        return gr.update(value=""), gr.update(value="❌ Guest users can only ask up to 5 questions. Please sign up to continue.", visible=True)

    if not has_uploaded_knowledge():
        logging.info("No documents in knowledge base. Using ChatGPT directly.")
        fallback_answer = fallback_to_chatgpt(question)
        source = "chatgpt"
        results = [fallback_answer]
    else:
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

    if not results or not isinstance(results, list):
        results = ["[No relevant knowledge found. Using ChatGPT fallback.]"]

    answer = "\n\n---\n\n".join(results)
    log_query("guest", question, source, answer)
    remaining = MAX_GUEST_QUESTIONS - used - 1
    return gr.update(value=answer + f"\n\n📌 You have {remaining}/5 questions remaining as a guest."), gr.update(visible=False)

with gr.Blocks() as interface:
    gr.Markdown("""
    # 🇵🇭 TINA: Tax Information Navigation Assistant
    """)
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
            error_box = gr.Textbox(visible=False)
            q.submit(fn=handle_ask, inputs=q, outputs=[a, error_box])

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
    interface.launch()
