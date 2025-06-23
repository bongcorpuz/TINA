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

load_or_create_faiss_index()

SESSION_TIMEOUT = 1800

# Fallback inline compatible with openai==1.0.0
import os, logging
from functools import lru_cache
try:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
except ImportError:
    openai = None

@lru_cache(maxsize=32)
def fallback_to_chatgpt(prompt: str) -> str:
    logging.warning("Fallback to ChatGPT activated.")
    if not openai:
        return "[OpenAI is not available]"
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

def handle_upload(file):
    if not file or not is_valid_file(file.name):
        return "Unsupported or missing file."
    path, error = save_file(file)
    if error:
        return error
    text = extract_text_from_file(path)
    index_document(text)
    return "File uploaded and indexed."

def handle_ask(question):
    try:
        results = semantic_search(question)
    except Exception as e:
        print(f"[Fallback] Semantic search error: {e}")
        results = [fallback_to_chatgpt(question)]
    return "\n\n---\n\n".join(results)

def handle_login(username, password):
    role = authenticate_user(username, password)
    if role:
        return f"Welcome {username}!", role, str(time.time())
    return "Login failed.", "guest", "0"

def handle_signup(username, password):
    success = register_user(username, password)
    return "Signup successful." if success else "Username already exists."

def update_admin_visibility(role):
    return gr.update(visible=(role == "admin"))

def reset_user():
    return "Logged out.", "guest", "0"

def session_expired(last_time_str):
    try:
        return time.time() - float(last_time_str) > SESSION_TIMEOUT
    except ValueError:
        return True

with gr.Blocks(title="TINA: Tax Information Navigation Assistant") as demo:
    gr.Markdown("# 📄 TINA: Tax Inquiry & Navigator Assistant")

    # Hidden states as textboxes
    hidden_user_role = gr.Textbox(value="guest", visible=False)
    hidden_last_login = gr.Textbox(value="0", visible=False)

    with gr.Tab("Login"):
        login_user = gr.Textbox(label="Username")
        login_pass = gr.Textbox(label="Password", type="password")
        login_btn = gr.Button("Login")
        login_msg = gr.Textbox(label="Status")
        login_btn.click(handle_login, inputs=[login_user, login_pass], outputs=[login_msg, hidden_user_role, hidden_last_login])

    with gr.Tab("Signup"):
        signup_user = gr.Textbox(label="Username")
        signup_pass = gr.Textbox(label="Password", type="password")
        signup_btn = gr.Button("Signup")
        signup_msg = gr.Textbox(label="Status")
        signup_btn.click(handle_signup, inputs=[signup_user, signup_pass], outputs=signup_msg)

    with gr.Tab("Upload"):
        file_input = gr.File()
        upload_btn = gr.Button("Upload")
        upload_output = gr.Textbox()
        upload_btn.click(handle_upload, inputs=file_input, outputs=upload_output)

    with gr.Tab("Ask"):
        query_input = gr.Textbox(label="Enter your query")
        ask_btn = gr.Button("Submit")
        answer_output = gr.Textbox(label="Answer")
        ask_btn.click(handle_ask, inputs=query_input, outputs=answer_output)

    with gr.Tab("Admin", visible=False) as admin_tab:
        admin_content = gr.Textbox(label="Admin commands here...")

    hidden_user_role.change(update_admin_visibility, inputs=hidden_user_role, outputs=admin_tab)

    with gr.Row():
        logout_btn = gr.Button("Logout")
        logout_status = gr.Textbox(label="Status")
        logout_btn.click(reset_user, outputs=[logout_status, hidden_user_role, hidden_last_login])

    def auto_logout(role, last_time):
        if role != "guest" and session_expired(last_time):
            return "Session expired.", "guest", "0", gr.update(visible=False)
        return gr.update(), gr.update(), gr.update(), gr.update()

    demo.load(fn=auto_logout, inputs=[hidden_user_role, hidden_last_login], outputs=[logout_status, hidden_user_role, hidden_last_login, admin_tab])

if __name__ == "__main__":
    demo.launch()
