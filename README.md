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

---

## 🧪 Run Locally

```bash
git clone https://huggingface.co/spaces/bongcorpuz/TINA
cd TINA

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
