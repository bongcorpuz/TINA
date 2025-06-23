---
title: TINA
emoji: 📄
colorFrom: yellow
colorTo: purple
sdk: gradio
sdk_version: 5.34.2
app_file: app.py
pinned: false
license: mit
short_description: Tax Information Navigation Assistant
---

![CI](https://huggingface.co/spaces/bongcorpuz/TINA/badge.svg)

# 🇵🇭 TINA: Tax Information and Navigation Assistant

TINA is your expert chatbot assistant for Philippine tax compliance, BIR regulations, and revenue rulings—powered by OpenAI and built by Bong Corpuz & Co. CPAs.

---

## 🚀 Features

- 🤖 Smart GPT Chat tuned to Philippine taxation only
- 📂 Admin-only document upload (`.pdf`, `.txt`, `.jpg`, etc.)
- 🔍 OCR + Embeddings + Semantic search for contextual answers
- 🧠 Knowledge base from `knowledge_files/`
- 📜 Built-in PH tax keyword filtering
- 📊 Admin Q&A log viewer + CSV export
- ✅ CI + Unit test coverage with `pytest`
- 🔢 SHA256 duplicate file prevention

---

## 🤪 Run Locally

```bash
git clone https://huggingface.co/spaces/bongcorpuz/TINA
cd TINA

# Optional: Check & install system dependencies (OCR, LibreOffice, etc.)
chmod +x setup.sh && ./setup.sh

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

---

## 🔐 .env Setup

Save this in your `.env` file:

```env
OPENAI_API_KEY=your-openai-api-key
TINA_ADMIN_PASS=admin@1971

# Optional (for future features)
MAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=info@bongcorpuz.com
EMAIL_PASS=your-app-password
```

---

## 📁 File Structure

```bash
🔺 app.py               # Main app UI + logic
🔺 auth.py              # Login/signup logic
🔺 database.py          # DB operations
🔺 file_utils.py        # Uploads, OCR, embeddings
🔺 knowledge_files/     # All indexed documents
🔺 query_log.db         # SQLite DB
🔺 .env                 # API keys
🔺 test_file_utils.py   # File handling test cases
🔺 setup.sh             # System dependency installer
```

---

## ✅ CI/CD on Hugging Face

TINA supports automatic deployment via Hugging Face Spaces and `.huggingface/huggingface.yml`. All pushes are tested using `pytest` to ensure file extraction and logic integrity.
