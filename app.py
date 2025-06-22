import gradio as gr
import os
import glob
from dotenv import load_dotenv
import openai
from App_Main_Ai import (
    init_db,
    get_user,
    save_qna,
    is_valid_tax_question,
    process_uploaded_file,
    KNOWLEDGE_FOLDER
)

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize the database
init_db()

# System Prompt (always enforced)
SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You ONLY answer questions related to Philippine taxation such as BIR forms, deadlines, tax types, and compliance. "
    "Base your answers strictly on publicly available resources like the NIRC, BIR Revenue Regulations (RRs), Revenue Memorandum Circulars (RMCs), and official BIR issuances. "
    "If asked anything not related to Philippine taxation, politely respond with: 'Sorry, I can only assist with questions related to Philippine taxation.'"
)

# Search local text knowledge files
def search_local_knowledge(query):
    results = []
    for path in glob.glob(os.path.join(KNOWLEDGE_FOLDER, '*.txt')):
        with open(path, encoding='utf-8') as f:
            text = f.read()
            if query.lower() in text.lower():
                results.append(text)
    return results

# Main chatbot logic

def tina_response(user_input):
    if not is_valid_tax_question(user_input):
        return "Sorry, I can only assist with questions related to Philippine taxation."

    local_hits = search_local_knowledge(user_input)

    if local_hits:
        answer = "\n---\n".join(local_hits[:1])[:2000]  # Limit to avoid overflow
        save_qna(user_input, answer, source="local")
        return answer
    
    # fallback to GPT
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ]
        )
        reply = response.choices[0].message.content.strip()
        save_qna(user_input, reply, source="chatGPT")
        return reply
    except Exception as e:
        return f"Error: {str(e)}"

# Upload handler
def handle_upload(file):
    if file is None:
        return "No file uploaded."
    file_path = file.name
    with open(file_path, "wb") as f:
        f.write(file.read())
    result = process_uploaded_file(file_path)
    return f"File processed: {os.path.basename(result) if result else 'Error'}"

# Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("## TINA: Tax Information Navigation Assistant (PH)")
    chatbot = gr.Chatbot()
    txt = gr.Textbox(placeholder="Ask about Philippine taxation...", show_label=False)
    file_upload = gr.File(label="Upload Tax Docs (PDF, JPG, PNG, TXT)")
    upload_btn = gr.Button("Upload and Process")

    def chat_submit(user_input):
        bot_response = tina_response(user_input)
        return [(user_input, bot_response)]

    txt.submit(chat_submit, inputs=txt, outputs=chatbot)
    upload_btn.click(handle_upload, inputs=file_upload, outputs=chatbot)

if __name__ == "__main__":
    demo.launch()

