#!/usr/bin/env python3
# Unified & Cleaned Core Modules for TINA

# All previous content remains unchanged (auth, file_utils, database)
# The following is added: Cleaned Gradio app integration

# ------------------ app.py ------------------
import gradio as gr
import time
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

import os, logging, hashlib
from functools import lru_cache

try:
    init_db()
except Exception as e:
    logging.error(f"❌ Failed to initialize database: {e}")
    raise SystemExit("Database initialization failed. Please check database.py setup.")

load_or_create_faiss_index()

SESSION_TIMEOUT = 1800
MAX_GUEST_QUESTIONS = 5

try:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
except ImportError:
    openai = None

@lru_cache(maxsize=32)
def fallback_to_chatgpt(prompt: str) -> str:
    logging.warning("Fallback to ChatGPT activated.")
    if not openai or not openai.api_key:
        return "[OpenAI API not configured]"
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"[ChatGPT Retry {attempt+1}] {e}")
            time.sleep(1.5)
    return f"[ChatGPT Error] All retries failed."

def is_tax_related(question):
    tax_keywords = [
        "tax", "vat", "bir", "income tax", "withholding", "efile", "audit",
        "taxpayer", "refund", "penalty", "compromise", "rdo", "registration",
        "zonal value", "capital gains", "percentage tax", "excise tax",
        "documentary stamp", "expanded withholding", "fringe benefits",
        "alpha list", "form 1700", "form 1701", "form 1702", "form 2551q",
        "form 2316", "form 2307", "form 1601eq", "form 0605", "loose-leaf",
        "books of account", "bir ruling", "open case", "notice of discrepancy",
        "revenue regulation", "revenue memorandum", "rr", "rmc", "tax advisory",
        "ruling", "assessment", "letter of authority", "subpoena", "tax audit",
        "tax mapping", "stop filer", "efps", "efiling", "bir registration",
        "tax clearance", "certificate of registration", "cor", "bir form",
        "cra", "crea", "create", "train", "tax reform", "local tax", "municipal tax",
        "business tax", "estate tax", "donor's tax", "tax amnesty", "boi incentive",
        "peza", "nontaxable", "exempt", "tax due", "remittance", "deadline",
        "penalties", "interest", "taxpayer identification number", "tin"
    ]
    q = question.lower()
    return any(word in q for word in tax_keywords)

def handle_upload(file):
    if not file or not is_valid_file(file.name):
        return "❌ Unsupported or missing file."

    contents = file.read()
    digest = hashlib.sha256(contents).hexdigest()
    ext = os.path.splitext(file.name)[1].lower()
    file_hash_path = os.path.join("knowledge_files", f"{digest}{ext}")

    if os.path.exists(file_hash_path):
        return f"⚠ File already uploaded previously. Skipping duplicate."

    with open(file_hash_path, "wb") as f:
        f.write(contents)

    extracted_text = extract_text_from_file(file_hash_path)
    index_document(extracted_text)
    store_file_text(f"{digest}.txt", extracted_text)

    snippet = extracted_text[:300].strip().replace("\n", " ") + ("..." if len(extracted_text) > 300 else "")
    return f"✅ File '{file.name}' uploaded and indexed.\n\n📄 Extract Preview:\n{snippet}"

def count_guest_queries():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM logs WHERE username = 'guest'")
        return c.fetchone()[0]

def handle_ask(question):
    if not is_tax_related(question):
        return "❌ This assistant only answers questions related to Philippine taxation. Please ask a tax-related question."

    used = count_guest_queries()
    if used >= MAX_GUEST_QUESTIONS:
        return "❌ Guest users can only ask up to 5 questions. Please sign up to continue."

    try:
        results = semantic_search(question)
        source = "semantic"
    except Exception as e:
        print(f"[Fallback] Semantic search error: {e}")
        results = [fallback_to_chatgpt(question)]
        source = "chatgpt"

    answer = "\n\n---\n\n".join(results)
    log_query("guest", question, source, answer)
    remaining = MAX_GUEST_QUESTIONS - used - 1
    return f"{answer}\n\n📌 You have {remaining}/5 questions remaining as a guest."

# The rest of the app.py remains unchanged
# ...