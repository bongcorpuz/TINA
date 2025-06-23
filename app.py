# ------------------ app.py ------------------
#!/usr/bin/env python3
import gradio as gr
import time
import os
import logging
import hashlib
from functools import lru_cache
from transformers import AutoTokenizer, AutoModelForCausalLM
from datasets import load_dataset
import torch

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

# Load fine-tuned LoRA model
try:
    lora_tokenizer = AutoTokenizer.from_pretrained("tina-lora")
    lora_model = AutoModelForCausalLM.from_pretrained("tina-lora")
    lora_model.eval()
except Exception as e:
    lora_model = None
    logging.warning(f"LoRA model not loaded: {e}")

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
    logging.warning("Fallback to fine-tuned LoRA model activated.")
    if lora_model:
        try:
            inputs = lora_tokenizer(prompt, return_tensors="pt")
            outputs = lora_model.generate(**inputs, max_new_tokens=300)
            return lora_tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        except Exception as e:
            logging.warning(f"LoRA generation failed: {e}")
            return f"[LoRA Error] {e}"
    return "[LoRA model not available]"

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
        return gr.update(value="❌ This assistant only answers questions related to Philippine taxation."), gr.update(visible=False)

    used = count_guest_queries()
    if used >= MAX_GUEST_QUESTIONS:
        return gr.update(visible=False), gr.update(value="❌ Guest users can only ask up to 5 questions. Please sign up to continue.", visible=True), gr.Tabs.update(selected=1)

    try:
        results = semantic_search(question)
        source = "semantic"
    except Exception as e:
        logging.warning(f"[Fallback] Semantic search error: {e}")
        fallback_answer = fallback_to_chatgpt(question)
        source = "lora"
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

# ✅ Complete UI Tabs and Footer
with gr.Blocks() as demo:
    gr.Markdown("## TINA: Philippine Tax Assistant\nUpload tax-related files or ask a question below.")

    with gr.Tabs() as tabs:
        with gr.TabItem("Ask TINA"):
            chatbot = gr.Textbox(lines=2, label="Enter your tax question")
            output = gr.Textbox(lines=8, interactive=False)
            ask_button = gr.Button("Ask")
            ask_button.click(fn=handle_ask, inputs=[chatbot], outputs=[output])

        with gr.TabItem("Upload Files"):
            upload_box = gr.File(label="Upload File")
            upload_output = gr.Textbox(label="Result", lines=6)
            upload_button = gr.Button("Upload")
            upload_button.click(fn=handle_upload, inputs=upload_box, outputs=upload_output)

    gr.Markdown("---")
    gr.Markdown("Powered by: [Bong Corpuz & Co. CPAs](https://bongcorpuz.com)")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=True)
