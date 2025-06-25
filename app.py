# ------------------ app.py ------------------
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
from auth import authenticate_user, register_user, is_admin, send_password_reset, recover_user_email
from database import log_query, get_conn, init_db, store_file_text, has_uploaded_knowledge

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
        # Block if expired user
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

with gr.Blocks() as interface:
    gr.Markdown("""
    # 🇵🇭 TINA: Tax Information Navigation Assistant
    """)
    login_state = gr.State("")
    subscription_status = gr.State("")

    with gr.Tabs() as tabs:
        def should_disable_renew(sub_info):
            try:
                if 'Expires:' in sub_info:
                    from datetime import datetime, timedelta
                    exp_date = sub_info.split('Expires:')[-1].strip()
                    expiry = datetime.strptime(exp_date, "%Y-%m-%d")
                    if expiry - datetime.now() > timedelta(days=60):
                        return True
            except Exception as e:
                logging.warning(f"Could not parse subscription info: {e}")
            return False

        renew_disabled = should_disable_renew(subscription_status.value)
        with gr.Tab("Renew Subscription", id=6, visible=not renew_disabled):
            renew_result = gr.Textbox(label="Renewal Result")

            def renew_plan_wrapper(plan):
                from auth import renew_subscription, authenticate_user
                def inner(user_id):
                    if not user_id:
                        return "❌ Please login first.", ""
                    msg = renew_subscription(user_id, plan)
                    refreshed = authenticate_user(user_id, None)
                    if refreshed:
                        sub_info = f"📅 Plan: {refreshed['subscription_level']} | Expires: {refreshed['subscription_expires']}"
                    else:
                        sub_info = ""
                    return msg, sub_info
                return inner

            gr.Row([
                gr.Button("Monthly Plan (₱)").click(fn=renew_plan_wrapper("monthly"), inputs=[login_state], outputs=[renew_result, subscription_status]),
                gr.Button("Quarterly Plan (₱₱)").click(fn=renew_plan_wrapper("quarterly"), inputs=[login_state], outputs=renew_result),
                gr.Button("Annual Plan (₱₱₱)").click(fn=renew_plan_wrapper("annual"), inputs=[login_state], outputs=renew_result)
            ])
                    with gr.Tab("Login", id=0):
            login_email = gr.Textbox(label="Email")
            login_pass = gr.Textbox(label="Password", type="password")
            login_result = gr.Textbox(label="Login Result")
            sub_status_box = gr.Textbox(label="Subscription Info", interactive=False)
            badge_box = gr.Textbox(label="⏳ Days Left", interactive=False, info="Renew option hidden: active plan")

            def handle_login(e, p):
                user = authenticate_user(e, p)
                if not user:
                    return "❌ Login failed.", "", ""
                sub_info = f"📅 Plan: {user['subscription_level']} | Expires: {user['subscription_expires']}"
                from datetime import datetime
                try:
                    days_left = (datetime.strptime(user['subscription_expires'], "%Y-%m-%d") - datetime.utcnow()).days
                    badge = f"⏳ {days_left} days left"
                except:
                    badge = ""
                return f"✅ Logged in as {user['role']}", user["id"], sub_info, badge

            gr.Button("Login").click(handle_login, [login_email, login_pass], [login_result, login_state, sub_status_box, badge_box])
            gr.Button("Logout").click(fn=lambda: ("Logged out.", "", ""), inputs=None, outputs=[login_result, login_state, sub_status_box])

        with gr.Tab("Ask TINA", id=1):
            q = gr.Textbox(label="Ask a Tax Question")
            a = gr.Textbox(label="Answer")
            error_box = gr.Textbox(visible=False)
            q.submit(fn=handle_ask, inputs=[q, login_state, subscription_status], outputs=[a, error_box, tabs])

        with gr.Tab("Signup", id=2):
            signup_email = gr.Textbox(label="Email Address")
            signup_pass = gr.Textbox(label="Password", type="password")
            signup_result = gr.Textbox(label="Signup Result")

            def handle_signup(e, p):
                return register_user(e, p)

            gr.Button("Signup").click(handle_signup, [signup_email, signup_pass], signup_result)

        with gr.Tab("Forgot Password", id=3):
            reset_email = gr.Textbox(label="Email")
            reset_result = gr.Textbox(label="Reset Result")
            gr.Button("Send Reset Email").click(send_password_reset, [reset_email], [reset_result])

        with gr.Tab("Recover Username", id=4):
            recover_key = gr.Textbox(label="Keyword")
            recover_result = gr.Textbox(label="Matched Usernames")

            def handle_recover(k):
                return "\n".join(recover_user_email(k))

            gr.Button("Search").click(handle_recover, [recover_key], [recover_result])

        with gr.Tab("Admin Upload", id=5):
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
    interface.launch()
