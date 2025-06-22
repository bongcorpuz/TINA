import gradio as gr
import openai
import os
from dotenv import load_dotenv
from app import save_qna, is_valid_tax_question  # Import from app.py

# Load environment variables
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

# System prompt tailored for Philippine tax Q&A
SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You are helpful, polite, and specialize in answering questions about Philippine taxation. "
    "Base your responses on publicly available tax laws such as the NIRC, BIR Revenue Regulations, RMCs, "
    "and tax reform laws like TRAIN, CREATE, and Ease of Paying Taxes Act. Do not offer legal advice."
)

# Chat function using OpenAI API
def ask_tina(user_input):
    if not user_input.strip():
        return "Please enter a question related to Philippine taxation."
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            temperature=0.4
        )
        answer = response.choices[0].message.content.strip()

        # Log to QnA DB only if it's a tax-related question
        if is_valid_tax_question(user_input):
            save_qna(user_input, answer)

        return answer
    except Exception as e:
        return f"Error: {str(e)}"

# Launch Gradio interface
def launch_ui():
    with gr.Blocks(title="TINA - Philippine Tax Chatbot") as demo:
        gr.Markdown("## 💬 TINA: Your Tax Info Navigation Assistant\nAsk anything about Philippine taxation!")
        
        with gr.Row():
            user_input = gr.Textbox(label="Your Question", placeholder="e.g., What is the deadline for filing BIR Form 1701?")
        
        with gr.Row():
            submit_btn = gr.Button("Ask TINA")
        
        output = gr.Textbox(label="TINA's Answer")

        submit_btn.click(fn=ask_tina, inputs=user_input, outputs=output)

    demo.launch()
