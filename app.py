import gradio as gr
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from database import init_db, get_user
from email_confirm import send_confirmation_email

# Load environment variables
load_dotenv()

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Uploaded files folder
UPLOAD_FOLDER = "uploaded_knowledge"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# System prompt for TINA
BASE_SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You ONLY answer questions related to Philippine taxation such as BIR forms, deadlines, tax types, and compliance. "
    "Base your answers strictly on publicly available resources like the NIRC, BIR Revenue Regulations (RRRs), "
    "Revenue Memorandum Circulars (RMCs), and official BIR issuances. "
    "If asked anything not related to Philippine taxation, politely respond with: "
    "'Sorry, I can only assist with questions related to Philippine taxation.'"
)

# Valid keywords
TAX_KEYWORDS = [
    "bir", "tax", "vat", "income", "1701", "2550", "2551", "0619", "withholding",
    "rdo", "tin", "books", "taxpayer", "philippine", "registration", "bmbe", "clearance"
]

# Subscription tiers
SUBSCRIPTION_OPTIONS = {
    "Monthly (₱150)": 30,
    "Quarterly (₱400)": 90,
    "Yearly (₱1500)": 365
}

# Authenticate user
def authenticate(username, password):
    user = get_user(username)
    if user and user[2] == password:
        expiration = datetime.strptime(user[3], "%Y-%m-%d")
        if expiration >= datetime.now():
            return user
    return None

# Respond to messages
def respond(message, system_prompt, max_tokens, temperature, top_p, username, password, uploaded_file):
    user = authenticate(username, password)
    if not user:
        return [(message, "❌ Invalid login or subscription expired.")]

    if not any(keyword in message.lower() for keyword in TAX_KEYWORDS):
        return [(message, "❌ I can only assist with Philippine taxation topics.")]

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
        return [(message, f"❌ OpenAI API Error: {e}")]

# File preview
def list_user_files(user):
    if not user:
        return "❌ Invalid credentials."
    result = []
    for f in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, f)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read(300)
            result.append(f"📄 {f}:\n{content}\n---")
        except:
            result.append(f"📄 {f} (binary file, preview unavailable)")
    return "\n\n".join(result)

# Send confirmation
def trigger_email(user, plan):
    return send_confirmation_email(user, plan)

# UI
with gr.Blocks() as demo:
    gr.Markdown("# 🤖 TINA – Tax Information Navigation Assistant (Philippines)")
    gr.Markdown("Login to ask questions about BIR forms, deadlines, and PH tax rules.")

    with gr.Row():
        username_input = gr.Textbox(label="Username")
        password_input = gr.Textbox(label="Password", type="password")

    subscription_input = gr.Dropdown(choices=list(SUBSCRIPTION_OPTIONS.keys()), label="Subscription Plan")
    email_status = gr.Textbox(label="Email Status")
    gr.Button("📧 Send Confirmation").click(
        trigger_email,
        inputs=[username_input, subscription_input],
        outputs=email_status
    )

    gr.ChatInterface(
        fn=respond,
        additional_inputs=[
            gr.Textbox(value=BASE_SYSTEM_PROMPT, visible=False),
            gr.Slider(256, 2048, value=512, step=1, label="Max tokens"),
            gr.Slider(0.1, 1.5, value=0.7, step=0.1, label="Temperature"),
            gr.Slider(0.1, 1.0, value=0.95, step=0.05, label="Top-p"),
            username_input,
            password_input,
            gr.File(label="Upload Reference File", type="binary")
        ],
        type="messages"
    )

    with gr.Accordion("📂 View Uploaded Files", open=False):
        view_user = gr.Textbox(label="Username")
        view_pass = gr.Textbox(label="Password", type="password")
        out = gr.Textbox(lines=20, label="File Previews")
        gr.Button("🔄 Load Files").click(
            lambda u, p: list_user_files(authenticate(u, p)),
            inputs=[view_user, view_pass],
            outputs=out
        )

if __name__ == "__main__":
    init_db()
    demo.launch()
