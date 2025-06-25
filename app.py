import os
import gradio as gr
from auth import register_user, authenticate_user, send_password_reset, recover_user_email, renew_subscription, is_admin
from dotenv import load_dotenv

load_dotenv()

SESSION = {"user": None}

def login(email, password):
    auth_result = authenticate_user(email, password)
    if not auth_result or "error" in auth_result:
        return f"❌ Login failed. {auth_result.get('error', '') if auth_result else ''}", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
    SESSION["user"] = auth_result
    return "✅ Logged in as user" if auth_result['role'] != 'admin' else "🔑 Logged in as admin", gr.update(visible=True), gr.update(visible=True), gr.update(visible=auth_result['role'] == 'admin'), gr.update(visible=False)

def logout():
    SESSION["user"] = None
    return "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)

def signup(username, email, password):
    return register_user(username, email, password)

def ask_tina(question):
    if not SESSION["user"]:
        return "❌ Please login to ask questions."
    remaining = 5  # Simulated quota logic placeholder
    return f"Taxation is the process of levying and collecting taxes from individuals, businesses, and other entities by a government. Taxes are mandatory payments imposed on income, property, goods, and services to fund public services and government operations. Taxation is a crucial aspect of a country's economy as it generates revenue for the government to finance public services such as education, healthcare, infrastructure, and defense.\n\n🌟 {remaining}/5 guest questions left."

def admin_upload(data):
    if not SESSION["user"] or SESSION["user"].get("role") != "admin":
        return "❌ Unauthorized"
    return "✅ Data uploaded (simulation)."

def reset_password(email):
    return send_password_reset(email)

def recover_email(keyword):
    results = recover_user_email(keyword)
    return "\n".join(results) if results else "❌ No matches found."

def extend_subscription(plan):
    if not SESSION["user"]:
        return "❌ Login required"
    return renew_subscription(SESSION["user"]["id"], plan)

with gr.Blocks() as demo:
    gr.Markdown("**PH TINA: Tax Information Navigation Assistant**")

    with gr.Tab("Login"):
        email = gr.Textbox(label="Email")
        password = gr.Textbox(label="Password", type="password")
        login_btn = gr.Button("Login")
        logout_btn = gr.Button("Logout", visible=False)
        login_status = gr.Textbox(label="Login Result", interactive=False)

    with gr.Tab("Ask TINA"):
        question = gr.Textbox(label="Ask a Tax Question")
        answer = gr.Textbox(label="Answer", interactive=False)
        ask_btn = gr.Button("Ask", visible=False)

    with gr.Tab("Signup"):
        username = gr.Textbox(label="Username")
        new_email = gr.Textbox(label="Email")
        new_password = gr.Textbox(label="Password", type="password")
        signup_btn = gr.Button("Signup")
        signup_status = gr.Textbox(label="Signup Result", interactive=False)

    with gr.Tab("Reset Password"):
        reset_email = gr.Textbox(label="Email")
        reset_btn = gr.Button("Reset Password")
        reset_status = gr.Textbox(label="Status", interactive=False)

    with gr.Tab("Recover Email"):
        keyword = gr.Textbox(label="Username Keyword")
        recover_btn = gr.Button("Recover Email")
        recovered_emails = gr.Textbox(label="Matching Emails", interactive=False)

    with gr.Tab("Admin Upload"):
        admin_input = gr.Textbox(label="Upload Data")
        upload_btn = gr.Button("Upload")
        upload_status = gr.Textbox(label="Upload Status", interactive=False)

    login_btn.click(login, [email, password], [login_status, ask_btn, logout_btn, upload_btn, login_btn])
    logout_btn.click(logout, [], [login_status, ask_btn, logout_btn, upload_btn, login_btn])
    signup_btn.click(signup, [username, new_email, new_password], signup_status)
    ask_btn.click(ask_tina, question, answer)
    reset_btn.click(reset_password, reset_email, reset_status)
    recover_btn.click(recover_email, keyword, recovered_emails)
    upload_btn.click(admin_upload, admin_input, upload_status)

demo.launch()
