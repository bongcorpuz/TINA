import gradio as gr
from openai import OpenAI
import os
import shutil
import tempfile
import json
import time
from datetime import datetime, timedelta

# NEW: Local modules for DB and email
from database import init_db, add_user, get_user, update_subscription
from email_confirm import send_confirmation_email

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

# 📚 Read and summarize uploaded files
def read_knowledge_files():
    combined_knowledge = ""
    summary_json = {}
    for file_name in os.listdir(KNOWLEDGE_FOLDER):
        file_path = os.path.join(KNOWLEDGE_FOLDER, file_name)
        try:
            if file_name.endswith((".txt", ".md")):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    combined_knowledge += f"\n\n{content}"
                    summary_json[file_name] = content[:500]
            elif file_name.endswith(".pdf"):
                import PyPDF2
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = "\n".join([page.extract_text() or "" for page in reader.pages])
                    combined_knowledge += text
                    summary_json[file_name] = text[:500]
            elif file_name.endswith((".jpeg", ".jpg", ".png")):
                import pytesseract
                from PIL import Image
                image = Image.open(file_path)
                text = pytesseract.image_to_string(image)
                text_filename = os.path.splitext(file_name)[0] + ".txt"
                with open(os.path.join(KNOWLEDGE_FOLDER, text_filename), "w", encoding="utf-8") as tf:
                    tf.write(text)
                combined_knowledge += f"\n\n{text}"
                summary_json[file_name] = text[:500]
        except Exception as e:
            combined_knowledge += f"\n[Error reading {file_name}: {e}]"
    with open(os.path.join(KNOWLEDGE_FOLDER, "summary.json"), "w", encoding="utf-8") as js:
        json.dump(summary_json, js, indent=2)
    return combined_knowledge[:4000]

# 🔐 Login + expiration + database auth
def authenticate(username, password):
    user = get_user(username)
    if not user:
        return False
    if user["password"] != password:
        return False
    if datetime.strptime(user["expires"], "%Y-%m-%d") < datetime.now():
        return False
    return True

# 📋 Viewer function for uploaded documents with preview
def list_uploaded_files_with_preview(authenticated):
    if not authenticated:
        return "🔐 Access Denied: Only admins or premium users can view files."
    files = os.listdir(KNOWLEDGE_FOLDER)
    if not files:
        return "📂 No files uploaded yet."
    output = ""
    for f in files:
        output += f"📄 {f}\n"
        path = os.path.join(KNOWLEDGE_FOLDER, f)
        try:
            if f.endswith((".txt", ".md")):
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read(300)
                    output += f"\n📝 Preview:\n{content}\n\n"
            elif f.endswith((".jpeg", ".jpg", ".png")):
                output += f"🖼️ [Image file preview not shown]\n\n"
            elif f.endswith(".pdf"):
                output += f"📄 [PDF preview not available]\n\n"
        except:
            output += f"⚠️ Could not preview {f}\n\n"
    return output

# 🧠 Response function
def respond(message, history, system_message, max_tokens, temperature, top_p, username, password, uploaded_file):
    if not authenticate(username, password):
        return "🔐 Access Denied. Please login with a premium account."

    if not any(word in message.lower() for word in TAX_KEYWORDS):
        return "Sorry, I can only assist with questions related to Philippine taxation."

    if uploaded_file:
        filename = os.path.basename(uploaded_file.name)
        dest_path = os.path.join(KNOWLEDGE_FOLDER, filename)
        with open(dest_path, "wb") as f:
            f.write(uploaded_file.read())

    knowledge_text = read_knowledge_files()
    final_prompt = BASE_SYSTEM_PROMPT + f"\n\nReference Files Summary:\n{knowledge_text}"

    messages = [{"role": "system", "content": final_prompt}]
    for entry in history:
        if isinstance(entry, dict):
            messages.append(entry)
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            messages.append({"role": "user", "content": entry[0]})
            messages.append({"role": "assistant", "content": entry[1]})
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p
    )

    return response.choices[0].message.content

# 🎨 Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("# TINA – Tax Information Navigation Assistant 🇵🇭")
    gr.Markdown("Login to ask about BIR forms, deadlines, tax rules, and compliance in the Philippines.")

    with gr.Row():
        username_input = gr.Textbox(label="Username")
        password_input = gr.Textbox(label="Password", type="password")

    subscri