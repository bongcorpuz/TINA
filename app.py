import gradio as gr
from openai import OpenAI
import os
import shutil
import tempfile
import json
import time
from datetime import datetime, timedelta
from database import init_db, add_user, get_user, update_subscription
from email_confirm import send_confirmation_email
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()

# ✅ Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 📁 Create and use a knowledge folder for uploaded files
KNOWLEDGE_FOLDER = "uploaded_knowledge"
os.makedirs(KNOWLEDGE_FOLDER, exist_ok=True)

# 🎫 Subscription levels with pricing
SUBSCRIPTION_OPTIONS = {
    "Monthly (₱150)": 30,
    "Quarterly (₱400)": 90,
    "Yearly (₱1500)": 365
}

# 📌 Base system prompt
BASE_SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You ONLY answer questions related to Philippine taxation such as BIR forms, deadlines, tax types, and compliance. "
    "Base your answers strictly on publicly available resources like the NIRC, BIR Revenue Regulations (RRRs), "
    "Revenue Memorandum Circulars (RMCs), and official BIR issuances. "
    "If asked anything not related to Philippine taxation, politely respond with: "
    "'Sorry, I can only assist with questions related to Philippine taxation.'"
)

# 🔍 Keywords for valid topics
TAX_KEYWORDS = [
    "bir", "tax", "vat", "income", "1701", "1701q", "1702", "1702q", "2550m", "2550q",
    "2551m", "0619e", "0619f", "withholding", "rdo", "tin", "philippine", "taxpayer",
    "bmbe", "books of accounts", "bir form", "registration", "tax clearance"
]

# 🛡️ Authentication function
def authenticate(username, password):
    user = get_user(username)
    if user and user[2] == password:
        expiration_date = datetime.strptime(user[3], "%Y-%m-%d")
        if expiration_date >= datetime.now():
            return user
    return None

# 📁 Read uploaded files
def list_uploaded_files_with_preview(user):
    if not user:
        return "❌ Invalid login."
    files = os.listdir(KNOWLEDGE_FOLDER)
    previews = []
    for fname in files:
        try:
            path = os.path.join(KNOWLEDGE_FOLDER, fname)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(500)
            previews.append(f"📄 {fname}\n{head[:300]}...\n")
        except:
            previews.append(f"📄 {fname} (binary file preview unavailable)\n")
    return "\n".join(previews)

# 🧠 Chatbot response logic
def respond(message, system_prompt, max_tokens, temperature, top_p, username, password, uploaded_file):
    user = authenticate(username, password)
    if not user:
        return [(message, "❌ Invalid login or expired subscription.")]

    if not any(word in message.lower() for word in TAX_KEYWORDS):
        return [(message, "❌ Sorry, I can only assist with questions related to Philippine taxation.")]

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens
        )
        reply = completion.choices[0].message.content.strip()
        return [(message, reply)]
    except Exception as e:
        return [(message, f"❌ Error: {e}")]

# 🎨 Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("# TINA – Tax Information Navigation Assistant 🇵🇭")
    gr.Markdown("Login to ask about BIR forms, deadlines, tax rules, and compliance in the Philippines.")

    with gr.Row():
        username_input = gr.Textbox(label="Username")
        password_input = gr.Textbox(label="Password", type="password")

    subscription_dropdown = gr.Dropdown(choices=list(SUBSCRIPTION_OPTIONS.keys()), label="Choose Subscription Plan")
    status = gr.Textbox(label="Status Message")
    confirm_email_btn = gr.Button("📧 Send Email Confirmation")

    def send_email_with_plan(user, plan):
        return send_confirmation_email(user, plan)

    confirm_email_btn.click(
        fn=send_email_with_plan,
        inputs=[username_input, subscription_dropdown],
        outputs=status
    )

    chat = gr.ChatInterface(
        fn=respond,
        additional_inputs=[
            gr.Textbox(value=BASE_SYSTEM_PROMPT, visible=False),
            gr.Slider(minimum=256, maximum=2048, value=512, step=1, label="Max new tokens"),
            gr.Slider(minimum=0.1, maximum=1.5, value=0.7, step=0.1, label="Temperature"),
            gr.Slider(minimum=0.1, maximum=1.0, value=0.95, step=0.05, label="Top-p (nucleus sampling)"),
            username_input,
            password_input,
            gr.File(label="Upload Knowledge File (txt, pdf, md, jpg, png)", type="binary")
        ]
    )

    with gr.Accordion("📂 View Uploaded Files", open=False):
        auth_user = gr.Textbox(label="Enter Username")
        auth_pass = gr.Textbox(label="Enter Password", type="password")
        file_list_output = gr.Textbox(label="Uploaded Files & Previews", lines=20)
        refresh_btn = gr.Button("🔄 Refresh File List")

        refresh_btn.click(
            fn=lambda u, p: list_uploaded_files_with_preview(authenticate(u, p)),
            inputs=[auth_user, auth_pass],
            outputs=file_list_output
        )

if __name__ == "__main__":
    init_db()
    demo.launch()
