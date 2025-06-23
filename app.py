# app.py
import gradio as gr
import openai
import os
from dotenv import load_dotenv
from database import (
    init_db,
    log_query,
    export_logs_csv,
    view_logs,
    delete_log_by_id,
    view_summaries,
    store_file_text,
    has_uploaded_knowledge
)
from auth import login_user, signup_user, renew_subscription
from file_utils import save_file, is_valid_file, extract_text_from_file, semantic_search

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

init_db()

PH_TAX_KEYWORDS = [
    "tax", "taxes", "taxation", "philippine tax", "philippine taxation", "taxpayer", "tax return",
    "bir", "bureau of internal revenue", "nirc", "tax code", "tax law", "tax rules",
    "bir form", "bir forms", "form 2550q", "form 2551q", "form 1701", "form 1702", "form 1601e",
    "form 1601f", "form 2316", "tax forms", "file tax", "efile", "efps", "ebirforms",
    "vat", "withholding tax", "percentage tax", "income tax", "business tax", "estate tax", "donor's tax",
    "capital gains tax", "excise tax", "local tax", "tax relief", "tax exemption", "tax amnesty",
    "revenue regulation", "revenue memorandum", "rr", "rr no.", "rmc", "rmc no.",
    "bir circular", "bir issuance", "bir advisory",
    "tax audit", "tax assessment", "tax clearance", "tax refund", "tax credit", "tax evasion", "tax fraud",
    "tax penalty", "tax computation", "tax calculator", "etin", "tin", "register with bir",
    "bir website", "bir hotline", "bir branch", "bir rdo", "rdo code"
]

MAX_ANSWER_LENGTH = 1000

def is_ph_tax_query(text):
    lowered = text.lower()
    return any(keyword in lowered for keyword in PH_TAX_KEYWORDS)

def gr_login(username, password, session_state):
    msg, err = login_user(username, password)
    if err:
        return session_state, err
    session_state["username"] = username
    return session_state, msg

def gr_signup(username, password):
    return signup_user(username, password)

def gr_upload(file, session_state):
    if session_state.get("username") != "admin":
        return "Only admin can upload knowledge files."
    path, err = save_file(file)
    if not path:
        return err
    try:
        extracted_text = extract_text_from_file(path)
        store_file_text(path, extracted_text)
        return f"Uploaded and indexed: {os.path.basename(path)}"
    except Exception as e:
        return f"Failed to process file: {str(e)}"

def gr_query(input_text, session_state):
    if "username" not in session_state:
        return "Login required."
    if not is_ph_tax_query(input_text):
        return "TINA only answers questions related to Philippine taxation and BIR regulations."

    try:
        if not has_uploaded_knowledge():
            context = "No uploaded knowledge files available."
            fallback_note = "⚠️ Note: Using general GPT knowledge due to missing internal documents."
        else:
            docs = semantic_search(input_text)
            if not docs:
                context = "No relevant documents found."
                fallback_note = "⚠️ Note: No internal reference matched. Answer is based on general knowledge."
            else:
                context = "\n---\n".join(docs)
                fallback_note = ""

        system_prompt = "You are a helpful assistant expert in Philippine taxation. Use the following documents as reference if needed."

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{input_text}"}
            ]
        )
        answer = response.choices[0].message.content
        if fallback_note:
            answer = f"{fallback_note}\n\n" + answer[:MAX_ANSWER_LENGTH] + ('...' if len(answer) > MAX_ANSWER_LENGTH else '')
        log_query(session_state["username"], input_text, context, answer)
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

with gr.Blocks(title="TINA - Tax Information and Navigation Assistant (Powered by Bong Corpuz & Co. CPAs)") as demo:
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
