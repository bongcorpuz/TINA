import gradio as gr
import time
import os
import logging
import hashlib
import re
from functools import lru_cache
import openai
from dotenv import load_dotenv
from file_utils import (
    save_file,
    is_valid_file,
    extract_text_from_file,
    index_document,
    load_or_create_faiss_index
)
from ask_tina import answer_query_with_knowledge  # ✅ Works now, no circular import
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

def handle_ask(question, user):
    if not is_tax_related(question):
        return gr.update(value="❌ TINA only answers questions related to Philippine taxation."), gr.update(visible=False), gr.update()

    if user == "guest":
        used = count_guest_queries()
        if used >= MAX_GUEST_QUESTIONS:
            return gr.update(value=""), gr.update(value="❌ Guest users can only ask 5 questions."), gr.update()
    else:
        used = 0

    results, source = answer_query_with_knowledge(question)

    answer = "\n\n---\n\n".join(results)
    log_query(user, question, source, answer)
    remaining = MAX_GUEST_QUESTIONS - used - 1 if user == "guest" else "∞"
    return gr.update(value=answer + f"\n\n📌 {'Guest questions left: ' + str(remaining) if user == 'guest' else 'Logged in user'}"), gr.update(visible=False), gr.update()
