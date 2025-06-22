import gradio as gr
from openai import OpenAI
import os

# ✅ Initialize OpenAI client with API key from environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Load custom knowledge file (e.g., BIR references)
KNOWLEDGE_FILE = "bir_reference.txt"
if os.path.exists(KNOWLEDGE_FILE):
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        knowledge_content = f.read()
else:
    knowledge_content = ""

# ✅ System prompt with reference injected
BASE_SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You ONLY answer questions related to Philippine taxation such as BIR forms, deadlines, tax types, and compliance. "
    "Base your answers strictly on publicly available resources like the NIRC, BIR Revenue Regulations (RRs), Revenue Memorandum Circulars (RMCs), and official BIR issuances. "
    "If asked anything not related to Philippine taxation, politely respond with: "
    "'Sorry, I can only assist with questions related to Philippine taxation.'"
)
SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + "\n\nTax Reference Guide:\n" + knowledge_content

# ✅ Main response function
def respond(message, history, system_message, max_tokens, temperature, top_p):
    try:
        # 🔒 Restrict to PH tax-related queries
        tax_keywords = [
            "bir", "tax", "vat", "income", "1701", "2550", "2551", "0619", "withholding",
            "tin", "rdo", "bir form", "philippine", "percentage tax", "expanded", "train", "create law"
        ]
        if not any(keyword in message.lower() for keyword in tax_keywords):
            return "Sorry,
