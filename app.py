import gradio as gr
from openai import OpenAI
import os

# ✅ Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 📌 TINA's strict system prompt
SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You ONLY answer questions related to Philippine taxation such as BIR forms, deadlines, tax types, and compliance. "
    "Base your answers strictly on publicly available resources like the NIRC, BIR Revenue Regulations (RRs), Revenue Memorandum Circulars (RMCs), and official BIR issuances. "
    "If asked anything not related to Philippine taxation, politely respond with: "
    "'Sorry, I can only assist with questions related to Philippine taxation.'"
)

# 🧠 Main response function (non-streaming for stability)
def respond(message, history, system_message, max_tokens, temperature, top_p):
    try:
        tax_keywords = ["bir", "tax", "vat", "income", "1701", "2550", "0619", "withholding", "rdo", "tin", "philippine"]
        if not any(word in message.lower() for word in tax_keywords):
            return "Sorry, I can only assist with questions related to Philippine taxation."

        messages = [{"role": "system", "content": system_message}]
        for user, assistant in history:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ An error occurred: {str(e)}"

# 🎨 Gradio interface for chatbot
demo = gr.ChatInterface(
    fn=respond,
    additional_inputs=[
        gr.Textbox(value=SYSTEM_PROMPT, label="System message"),
        gr.Slider(minimum=256, maximum=2048, value=512, step=1, label="Max new tokens"),
        gr.Slider(minimum=0.1, maximum=1.5, value=0.7, step=0.1, label="Temperature"),
        gr.Slider(minimum=0.1, maximum=1.0, value=0.95, step=0.05, label="Top-p (nucleus sampling)")
    ],
    title="TINA – Tax Information Navigation Assistant 🇵🇭",
    description="Ask TINA about BIR forms, deadlines, tax rules, and compliance in the Philippines. Questions outside PH taxation will be politely declined.",
)

if __name__ == "__main__":
    demo.launch()
