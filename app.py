import gradio as gr
import os
from dotenv import load_dotenv
from database import init_db, add_user, get_user, verify_password
from email_confirm import send_confirmation_email

# Load environment variables
load_dotenv()

# Initialize database
init_db()

# Login system
SESSION_STATE = {"username": None, "role": None}

def login(username, password):
    user = get_user(username)
    if user and verify_password(password, user['password']):
        SESSION_STATE["username"] = user["username"]
        SESSION_STATE["role"] = user["role"]
        return f"✅ Welcome back, {username}!"
    return "❌ Invalid username or password."

def register(username, password, email, subscription_level):
    success = add_user(username, password, email, subscription_level)
    if success:
        send_confirmation_email(email)
        return f"✅ Registration successful! Confirmation email sent to {email}."
    return "❌ Registration failed. Username or email may already be taken."

def logout():
    SESSION_STATE["username"] = None
    SESSION_STATE["role"] = None
    return "✅ Logged out successfully."

# Main ChatBot Prompt
SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You ONLY answer questions related to Philippine taxation such as BIR forms, deadlines, tax types, and compliance. "
    "Base your answers strictly on publicly available resources like the NIRC, BIR Revenue Regulations (RRs), Revenue Memorandum Circulars (RMCs), and official BIR issuances. "
    "If asked anything not related to Philippine taxation, politely respond with: "
    "'Sorry, I can only assist with questions related to Philippine taxation.'"
)

def chatbot_respond(message, history, system_message, max_tokens, temperature, top_p):
    # Example simple validation
    if SESSION_STATE['username'] is None:
        return "⚠️ You must log in to chat with TINA."
    tax_keywords = ["bir", "tax", "vat", "income", "1701", "2550", "0619", "withholding", "rdo", "tin", "philippine"]
    if not any(word in message.lower() for word in tax_keywords):
        return "Sorry, I can only assist with questions related to Philippine taxation."

    # Simulated response (replace with OpenAI call)
    return f"[Simulated TINA Reply to: {message}]"

# Gradio app
with gr.Blocks() as demo:
    gr.Markdown("## 🧾 TINA – Tax Information Navigation Assistant 🇵🇭")
    
    with gr.Tab("Login"):
        username = gr.Textbox(label="Username")
        password = gr.Textbox(label="Password", type="password")
        login_btn = gr.Button("Login")
        login_output = gr.Textbox()
        login_btn.click(login, inputs=[username, password], outputs=login_output)

    with gr.Tab("Register"):
        new_user = gr.Textbox(label="Username")
        new_pass = gr.Textbox(label="Password", type="password")
        new_email = gr.Textbox(label="Email")
        new_level = gr.Dropdown(["monthly", "quarterly", "yearly"], label="Subscription")
        reg_btn = gr.Button("Register")
        reg_output = gr.Textbox()
        reg_btn.click(register, inputs=[new_user, new_pass, new_email, new_level], outputs=reg_output)

    with gr.Tab("Chat with TINA"):
        chatbot = gr.ChatInterface(fn=chatbot_respond,
            additional_inputs=[
                gr.Textbox(value=SYSTEM_PROMPT, label="System message"),
                gr.Slider(minimum=256, maximum=2048, value=512, step=1, label="Max new tokens"),
                gr.Slider(minimum=0.1, maximum=1.0, value=0.7, step=0.1, label="Temperature"),
                gr.Slider(minimum=0.1, maximum=1.0, value=0.95, step=0.05, label="Top-p (nucleus sampling)")
            ])

    with gr.Tab("Logout"):
        logout_btn = gr.Button("Logout")
        logout_output = gr.Textbox()
        logout_btn.click(logout, outputs=logout_output)

if __name__ == "__main__":
    demo.launch(share=True)
