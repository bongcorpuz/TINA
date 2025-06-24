# UI with login/register and Ask tab
with gr.Blocks() as interface:
    gr.Markdown("# 🇵🇭 TINA: Tax Info Navigation Assistant")
    login_state = gr.State("")

    with gr.Tabs() as tabs:
        with gr.Tab("Login", id=0):
            login_user = gr.Textbox(label="Username")
            login_pass = gr.Textbox(label="Password", type="password")
            login_result = gr.Textbox(label="Login Result")

            def handle_login(u, p):
                role = authenticate_user(u, p)
                if not role:
                    return "❌ Login failed.", ""
                return f"✅ Logged in as {role}", u

            login_btn = gr.Button("Login")
            login_btn.click(handle_login, [login_user, login_pass], [login_result, login_state])

            logout_btn = gr.Button("Logout")
            def handle_logout():
                return "Logged out.", ""
            logout_btn.click(fn=handle_logout, inputs=None, outputs=[login_result, login_state])

        with gr.Tab("Ask TINA", id=1):
            q = gr.Textbox(label="Ask a Tax Question")
            a = gr.Textbox(label="Answer")
            q.submit(fn=handle_ask, inputs=q, outputs=a)

        with gr.Tab("Admin Upload", id=2):
            file_upload = gr.File(label="Upload File", file_types=['.pdf', '.txt', '.jpg', '.png', '.docx'])
            upload_result = gr.Textbox(label="Upload Status")

            def handle_upload(file, user):
                if not is_admin(user):
                    return "❌ Only admin can upload."
                if not is_valid_file(file.name):
                    return "❌ Invalid file type."
                path, _ = save_file(file)
                extracted = extract_text_from_file(path)
                index_document(extracted)
                store_file_text(file.name, extracted)
                return f"✅ Uploaded and indexed: {file.name}"

            upload_btn = gr.Button("Upload")
            upload_btn.click(fn=handle_upload, inputs=[file_upload, login_state], outputs=upload_result)

# Required for Hugging Face Spaces
def launch():
    return interface

if __name__ == "__main__":
    interface.launch()
