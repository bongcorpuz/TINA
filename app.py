import gradio as gr
import openai
import os

# 🔐 Load OpenAI API key securely from Hugging Face Space secret
openai.api_key = os.getenv("OPENAI_API_KEY")

# 💡 Define strict system instructions for TINA
SYSTEM_PROMPT = (
    "You are TINA, the Tax Information Navigation Assistant. "
    "You ONLY answer questions related to Philippine taxation such as BIR forms, deadlines, taxes, and compliance. "
    "Base your answers strictly on public resources like the NIRC, BIR Revenue Regulations (RRs), Revenue Memorandum Circulars (RMCs), and other official BIR issuances. "
    "If asked anything not related to Philippine taxation, politely respond with: "
    "'Sorry, I can only assist with questions related to Philippine taxation.' "
    "Do not answer questions about general topics, law outside the Philippines, or anything unrelated to BIR or tax compliance."
)

# 🧠 Response function
def respond(message, history, system_message, max_tokens, temperature, top_p):
    try:
        # Optional: block totally off-topic queries before calling API
        tax_keywords = ["bir", "tax", "vat", "income", "1701", "2550", "0619", "withholding", "rdo", "tin", "philippine"]
        if not any(word in message.lower() for word in tax_keywords):
            return "Sorry, I can only assist with questions related to Philippine taxation. Please try again with a BIR-related query."

        # Build conversation messages for OpenAI
        messages = [{"role": "system", "content": system_message}]
        for user, assistant in history:
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": message})

        # OpenAI streaming response
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
            delta = chunk["choices"][0]["delta"]
            if "content" in delta:
                partial += delta["content"]
                yield partial

    except Exception as e:
        yield f"⚠️ An error occurred: {str(e)}"

# 🖼️ Build the chatbot interface
demo = gr.ChatInterface(
    fn=respond,
    additional_inputs=[
        gr.Textbox(value=SYSTEM_PROMPT, label="System message"),
        gr.Slider(minimum=256, maximum=2048, value=512, step=1, label="Max new tokens"),
        gr.Slider(minimum=0.1, maximum=1.5, value=0.7, step=0.1, label="Temperature"),
        gr.Slider(minimum=0.1, maximum=1.0, value=0.95, step=0.05, label="Top-p (nucleus sampling)")
    ],
    title="TINA – Tax Information Navigation Assistant 🇵🇭",
    description="Ask TINA about BIR forms, deadlines, tax rules, and compliance in the Philippines. Questions outside Philippine taxation will be declined politely.",
)

if __name__ == "__main__":
    demo.launch()
