import gradio as gr
from app import ask_tina  # Make sure app.py defines ask_tina(question, username)

def greet(name):
    return f"Hello, {name}! Welcome to TINA.", gr.update(visible=True), gr.update(visible=True)

def proceed_to_tina(name):
    # Hide greeting and proceed button, show chat section
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.State(name)

def tina_chat(question, state_name, history):
    username = state_name or "User"
    answer = ask_tina(question, username)
    history = history or []
    history.append((question, answer))
    return "", history

with gr.Blocks() as demo:
    gr.Markdown("# TINA: Tax Information Navigation Assistance")

    with gr.Column(visible=True) as greet_section:
        name = gr.Textbox(label="Enter your name", interactive=True)
        greet_btn = gr.Button("Greet Me")
        greeting = gr.Textbox(label="Greeting", interactive=False)
        proceed_btn = gr.Button("Proceed to TINA", visible=False)

    with gr.Column(visible=False) as chat_section:
        gr.Markdown("### Ask TINA your tax-related questions!")
        chatbot = gr.Chatbot(label="TINA Chat", height=350)
        question = gr.Textbox(label="Your Question", placeholder="Type your tax question here and press Enter")
        submit_btn = gr.Button("Ask TINA")

    state_name = gr.State()  # For storing the user's name
    state_history = gr.State([])

    # Connect greeting step
    greet_btn.click(
        fn=greet,
        inputs=name,
        outputs=[greeting, proceed_btn, greeting]
    )

    # Proceed to chat step
    proceed_btn.click(
        fn=proceed_to_tina,
        inputs=name,
        outputs=[greet_section, proceed_btn, chat_section, state_name]
    )

    # Chatbot Q&A
    submit_btn.click(
        fn=tina_chat,
        inputs=[question, state_name, chatbot],
        outputs=[question, chatbot]
    )
    question.submit(
        fn=tina_chat,
        inputs=[question, state_name, chatbot],
        outputs=[question, chatbot]
    )

demo.launch()