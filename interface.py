import gradio as gr
# Import your AI logic here. For example, from app import ask_tina
# from app import ask_tina

def greet(name):
    return f"Hello, {name}! Welcome to TINA."

def ask_tina(question, username):
    # Replace with your actual AI logic
    # For demonstration, echo the question
    answer = f"TINA's answer to '{question}' for {username}."
    return answer

def show_ai_interface(name):
    # This function renders the main AI interface
    with gr.Blocks() as ai_app:
        gr.Markdown(f"### Hi {name}! Ask your tax questions below.")
        with gr.Row():
            question = gr.Textbox(label="Your Question", placeholder="Type your tax-related question here...")
        answer = gr.Textbox(label="TINA's Response", interactive=False)
        ask_btn = gr.Button("Ask TINA")
        ask_btn.click(fn=ask_tina, inputs=[question, gr.State(name)], outputs=answer)
    return ai_app

with gr.Blocks() as demo:
    gr.Markdown("# TINA: Tax Information Navigation Assistance")
    name = gr.Textbox(label="Enter your name")
    greet_btn = gr.Button("Greet Me")
    greeting = gr.Textbox(label="Greeting", interactive=False)
    proceed_btn = gr.Button("Proceed to TINA", visible=False)
    
    # Step 1: Greet user
    def greet_and_show_proceed(name):
        return greet(name), gr.update(visible=True)
    
    greet_btn.click(fn=greet_and_show_proceed, inputs=name, outputs=[greeting, proceed_btn])
    
    # Step 2: Show AI interface after greeting
    def launch_ai_app(name):
        return gr.update(visible=False), gr.update(visible=False), show_ai_interface(name)
    
    proceed_btn.click(fn=launch_ai_app, inputs=name, outputs=[name, greet_btn, gr.Column()])

demo.launch()