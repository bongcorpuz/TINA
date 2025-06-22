import gradio as gr
from huggingface_hub import InferenceClient

client = InferenceClient("HuggingFaceH4/zephyr-7b-beta")

def respond(
    message,
    history: list[dict],
    system_message,
    max_tokens,
    temperature,
    top_p,
):
    messages = [{"role": "system", "content": system_message}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    response = ""
    for message in client.chat_completion(
        messages,
        max_tokens=max_tokens,
        stream=True,
        temperature=temperature,
        top_p=top_p,
    ):
        token = message.choices[0].delta.content
        response += token
        yield response

demo = gr.ChatInterface(
    respond,
    additional_inputs=[
        gr.Textbox(
    value="You are TINA, the Tax Information Navigation Assistant. You are helpful, polite, and specialize in answering questions about Philippine taxation. Base your responses on publicly available tax laws such as the NIRC, BIR Revenue Regulations, Revenue Memorandum Circulars, and recent tax reform laws like TRAIN, CREATE, and the Ease of Paying Taxes Act. Do not offer legal advice.",
    label="System message"
)
        gr.Slider(minimum=1, maximum=2048, value=512, step=1, label="Max new tokens"),
        gr.Slider(minimum=0.1, maximum=4.0, value=0.7, step=0.1, label="Temperature"),
        gr.Slider(minimum=0.1, maximum=1.0, value=0.95, step=0.05, label="Top-p (nucleus sampling)"),
    ],
)

if __name__ == "__main__":
    demo.launch(share=True)
