# app.py
import gradio as gr
import openai
from database import init_db, log_query, view_logs, ...
from auth import login_user, signup_user, renew_subscription
from file_utils import ensure_dir, save_file, is_valid

# Initialize
init_db(); ensure_dir()
openai.api_key = os.getenv("OPENAI_API_KEY")

def gr_login(username, password, state):
    msg, err = login_user(username, password)
    if err: return gr.update(), msg
    state.update({"user": username})
    return state, msg

def gr_upload(file, state):
    if "user" not in state: return "Login required"
    path, err = save_file(file)
    return path or err

def gr_query(txt, state):
    if "user" not in state: return "Login required"
    resp = openai.ChatCompletion.create(...)
    answer = resp.choices[0].message.content
    log_query(state["user"], txt, "", answer)
    return answer

# build UI blocks: login area, file upload, query textbox, admin panel
with gr.Blocks() as demo:
    state = gr.State({})
    login_btn = gr.Button("Login")
    login_btn.click(fn=gr_login, inputs=[...], outputs=[...])
    upload = gr.File(...); upload.submit(...)
    query = gr.Textbox(...); submit.click(...)
    # conditional show admin logs if user=="admin"
demo.launch()
