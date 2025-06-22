import gradio as gr
import os
from openai import OpenAI

# ✅ Initialize OpenAI client using your API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Load additional knowledge from a .txt or .md file
KNOWLEDGE_FILE = "knowledge.txt"
if os.path.exists(KNOWLEDGE_FILE):
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
        extra_knowledge = file.read()
else:
    extra_knowledge = ""

# 📌 Final system prompt with injected knowledge base
SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You ONLY answer questions related to Philippine taxation such as BIR forms, deadlines, tax types, and compliance. "
    "Base your answers strictly on publicly available resources like the NIRC, BIR Revenue Regulations (RRs), Revenue Memorandum Circulars (RMCs), and official BIR issuances. "
    "If asked anything not related to Philippine taxation, politely respond with: "
    "'Sorry, I can only assist with questions related to Philippine taxation.'\n\n"
    "Here is your knowledge base:\n"
    f"{extra_knowledge}"
)

# 🧠 Chat function with keyword filtering
def respond(message, history, system_message, max_tokens, temperature, top_p):
    try:
        tax_keywords = [
            "bir", "tax", "vat"
