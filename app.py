import gradio as gr
import openai
import os

# Set your OpenAI API key from Hugging Face secrets
openai.api_key = os.getenv("OPENAI_API_KEY")

# System prompt that defines TINA’s behavior
SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You specialize in answering questions about Philippine taxation using publicly available sources such as: "
    "(1) The National Internal Revenue Code (NIRC), as amended, "
    "(2) BIR Revenue Regulations (RRs), "
    "(3) Revenue Memorandum Circulars (RMCs), "
    "(4) Tax Advisories and other BIR issuances. "
    "You do not provide legal advice or speculative answers. "
    "Speak in clear, friendly, and professional language."
)

def respond(message, history, system_message, max_tokens, temperature, top_p):
    messages = [{"role": "system", "content": system_message}]
    for user, assistant in history:
        messages.append({"role": "user", "content": user})
        messages.append({"role": "assistant", "content": assistant})
    messages.append({"role": "user", "content": message})

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        stream=True,
    )

    partial = ""
    for chunk in response:
        delta = chunk['choices'][0]['delta']
        if 'content' in delta:
            partial += delta['content']
            yield partial

demo = gr.ChatInterface(
    respond,
    additional_inputs=[
        gr.Textbox(value=SYSTEM_PROMPT, label="System message"),
        gr.Slider(minimum=256, maximum=2048, value=512, step=1, label="Max new tokens"),
        gr.Slider(minimum=0.1, maximum=1.5, value=0.7, step=0.1, label="Temperature"),
        gr.Slider(minimum=0.1, maximum=1.0, value=0.95, step=0.05, label="Top-p (nucleus sampling)")
    ],
    title="TINA – Tax Information Navigation Assistant 🇵🇭",
    description="Ask TINA anything about Philippine taxation. She uses BIR and NIRC resources to answer."
)

if __name__ == "__main__":
    demo.launch()
