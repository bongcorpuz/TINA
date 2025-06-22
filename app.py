# app.py
import gradio as gr
import openai
import os
from dotenv import load_dotenv

from database import (
    init_db,
    log_query,
    view_logs,
    delete_log_by_id,
    export_logs_csv,
    view_summaries
)
from auth import login_user, signup_user, renew_subscription
from file_utils import save_file, is_valid_file

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

init_db()

# ---- Gradio functions ----

def gr_login(username, password, session_state):
    msg, err = login_user(username, password)
    if err:
        return session_state, err
    session_state["username"] = username
    return session_state, msg

def gr_signup(username, password):
    return signup_user(username, password)

def gr_upload(file, session_state):
    if "username" not in session_state:
        return "Please login first."
    path, err = save_file(file)
    return path if path else err

def gr_query(input_text, session_state):
    if "username" not in session_state:
        return "Login required."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": input_text}]
        )
        answer = response.choices[0].message.content
        log_query(session_state["username"], input_text, "", answer)
        return answer
    except Exception as e:
        return f"OpenAI Error: {str(e)}"

def gr_view_logs(session_state):
    if session_state.get("username") != "admin":
        return "Unauthorized."
    return view_logs()

def gr_delete_log(log_id, session_state):
    if session_state.get("username") != "admin":
        return "Unauthorized."
    return delete_log_by_id(log_id)

def gr_export_csv(session_state):
    if session_state.get("username") != "admin":
        return "Unauthorized."
    return export_logs_csv()

def gr_view_summaries():
    return view_summaries()

# ---- Gradio UI ----
with gr.Blocks() as demo:
    session_state = gr.State({})

    with gr.Tab("Login"):
        user = gr.Textbox(label="Username")
        pw = gr.Textbox(label="Password", type="password")
        login_btn = gr.Button("Login")
        login_out = gr.Textbox(label="Login Status")
        login_btn.click(gr_login, inputs=[user, pw, session_state], outputs=[session_state, login_out])

    with gr.Tab("Signup"):
        new_user = gr.Textbox(label="New Username")
        new_pw = gr.Textbox(label="New Password", type="password")
        signup_btn = gr.Button("Sign Up")
        signup_result = gr.Textbox(label="Signup Status")
        signup_btn.click(gr_signup, inputs=[new_user, new_pw], outputs=[signup_result])

    with gr.Tab("Upload"):
        upload_file = gr.File()
        upload_result = gr.Textbox()
        upload_file.change(fn=gr_upload, inputs=[upload_file, session_state], outputs=[upload_result])

    with gr.Tab("Ask"):
        question = gr.Textbox(label="Enter your query")
        answer = gr.Textbox(label="Answer")
        submit = gr.Button("Submit")
        submit.click(fn=gr_query, inputs=[question, session_state], outputs=[answer])

    with gr.Tab("Admin"):
        log_output = gr.Textbox(lines=10, label="Logs")
        refresh_logs = gr.Button("Refresh Logs")
        refresh_logs.click(fn=gr_view_logs, inputs=[session_state], outputs=[log_output])

        log_id = gr.Textbox(label="Log ID to delete")
        delete_btn = gr.Button("Delete Log")
        delete_result = gr.Textbox()
        delete_btn.click(fn=gr_delete_log, inputs=[log_id, session_state], outputs=[delete_result])

        export_btn = gr.Button("Export Logs as CSV")
        export_path = gr.Textbox(label="CSV Path")
        export_btn.click(fn=gr_export_csv, inputs=[session_state], outputs=[export_path])

    with gr.Tab("Summaries"):
        summary_box = gr.Textbox(lines=10, label="Summaries")
        view_sum = gr.Button("Refresh Summaries")
        view_sum.click(fn=gr_view_summaries, outputs=[summary_box])

    demo.load(lambda: {}, outputs=[session_state])

demo.launch()

