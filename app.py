# ------------------ app.py ------------------
import gradio as gr
import time
import os
import logging
import hashlib
from functools import lru_cache
import openai
from dotenv import load_dotenv
from file_utils import (
    save_file,
    is_valid_file,
    extract_text_from_file,
    semantic_search,
    index_document,
    load_or_create_faiss_index
)
from auth import authenticate_user, register_user, is_admin, send_password_reset, recover_user_email
from database import log_query, get_conn, init_db, store_file_text, has_uploaded_knowledge

load_dotenv()

# For openai==0.27.8 compatibility
openai.api_key = os.getenv("OPENAI_API_KEY")
print("OpenAI API Key Loaded:", openai.api_key)

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

def handle_ask(question, user_id, subscription_info):
    if user_id and 'Expires:' in subscription_info:
        try:
            exp_date = subscription_info.split('Expires: ')[-1].strip()
            if exp_date and exp_date < time.strftime("%Y-%m-%d"):
                return gr.update(value="❌ Your subscription has expired. Please renew to continue."), gr.update(visible=False), gr.update()
        except Exception as e:
            logging.warning(f"Subscription parse failed: {e}")

    if not is_tax_related(question):
        return gr.update(value="❌ TINA only answers questions related to Philippine taxation. Please refine your question."), gr.update(visible=False), gr.update()

    used = count_guest_queries()
    if used >= MAX_GUEST_QUESTIONS:
        return gr.update(value=""), gr.update(value="❌ Guest users can only ask up to 5 questions. Please go to the Signup tab to register and continue.", visible=True), gr.update()

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
    return gr.update(value=answer + f"\n\n📌 You have {remaining}/5 questions remaining as a guest."), gr.update(visible=False), gr.update()


def launch():
    return interface

if __name__ == "__main__":
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        raise EnvironmentError("Missing SUPABASE_URL or SUPABASE_KEY in environment. Please check .env file.")
    interface.launch()
