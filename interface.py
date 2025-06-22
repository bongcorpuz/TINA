import gradio as gr

def greet(name):
    return f"Hello, {name}! Welcome to TINA."

with gr.Blocks() as demo:
    gr.Markdown("# TINA: Tax Information Navigation Assistance")
    with gr.Row():
        name_input = gr.Textbox(label="Enter your name")
        greet_button = gr.Button("Greet Me")
    output = gr.Textbox(label="Greeting", interactive=False)
    greet_button.click(fn=greet, inputs=name_input, outputs=output)

demo.launch()