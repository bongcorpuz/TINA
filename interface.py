import gradio as gr
import openai
import os
from app import init_db, is_valid_tax_question, save_qna

# Initialize the database
init_db()

# Load OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# System prompt tailored for PH taxation
SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You are helpful, polite, and specialize in answering questions about Philippine taxation. "
    "Base your responses on publicly available tax laws such as the NIRC, BIR Revenue Regulations, RMCs, "
    "and tax reform laws like TRAIN, CREATE, and Ease of Paying Taxes Act. Do not offer legal advice."
)

# Chat function
def chat_with_tina(message):
    if not is_valid_tax_question(message):
        return "Sorry, this question doesn't seem related to Philippine taxation."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # or gpt-4 if your plan supports it
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ]
        )
        answer = response.choices[0].message["content"].strip()
        save_qna(message, answer)
        return answer
    except Exception as e:
        return f"Error calling OpenAI: {str(e)}"

# Gradio UI
iface = gr.Interface(
    fn=chat_with_tina,
    inputs=gr.Textbox(lines=4, label="Ask a PH Tax Question to TINA"),
    outputs=gr.Textbox(label="TINA's Response"),
    title="TINA - Tax Information Navigation Assistant",
    description="Ask TINA about Philippine taxation laws, forms, compliance, and more. Type a valid tax-related question to get started.",
    theme="default"
)

# Launch
if __name__ == "__main__":
    iface.launch()
