![CI](https://huggingface.co/spaces/bongcorpuz/TINA/badge.svg)

# TINA: Tax Information Navigation Assistant

TINA is your helpful assistant for Philippine tax compliance and law guidance.

## 🚀 Features
- Chatbot powered by OpenAI
- Upload and extract .txt/.pdf/.jpg for tax content
- Logs Q&A to SQLite
- Hugging Face CI/CD integration

## 🧪 Run Locally
```bash
pip install -r requirements.txt
python tina_app.py
```

## 🔐 Setup
Save your API key to `.env`:
```
OPENAI_API_KEY=your-openai-key
```

## ✅ Automated CI on Hugging Face
This app runs tests on each push via `.huggingface/huggingface.yml`
