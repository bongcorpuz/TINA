# app.py
import gradio as gr
from file_utils import (
    save_file,
    is_valid_file,
    extract_text_from_file,
    semantic_search,
    index_document,
    load_or_create_faiss_index,
    fallback_to_chatgpt
)

load_or_create_faiss_index()

def handle_upload(file):
    path, error = save_file(file)
    if error:
        return error
    text = extract_text_from_file(path)
    index_document(text)
    return "File uploaded and indexed."

def handle_ask(question):
    try:
        results = semantic_search(question)
    except Exception as e:
        print(f"[Fallback to ChatGPT] Error during semantic search: {e}")
        results = [fallback_to_chatgpt(question)]
    return "\n\n---\n\n".join(results)

with gr.Blocks(title="TINA - Tax Information Navigation Assistant") as demo:
    gr.Markdown("# 🇵🇭 TINA: Tax Information & Navigation Assistant")
    with gr.Tab("Login"):
        gr.Textbox(label="Username")
        gr.Textbox(label="Password", type="password")
        gr.Button("Login")
    with gr.Tab("Signup"):
        gr.Textbox(label="Username")
        gr.Textbox(label="Password", type="password")
        gr.Button("Signup")
    with gr.Tab("Upload"):
        file_input = gr.File()
        upload_btn = gr.Button("Upload")
        upload_output = gr.Textbox()
        upload_btn.click(fn=handle_upload, inputs=file_input, outputs=upload_output)
    with gr.Tab("Ask"):
        query_input = gr.Textbox(label="Enter your query")
        ask_btn = gr.Button("Submit")
        answer_output = gr.Textbox(label="Answer")
        ask_btn.click(fn=handle_ask, inputs=query_input, outputs=answer_output)
    with gr.Tab("Admin"):
        gr.Textbox(label="Admin commands here...")
    with gr.Tab("Summaries"):
        gr.Textbox(label="Document summaries will appear here")

if __name__ == "__main__":
    demo.launch()