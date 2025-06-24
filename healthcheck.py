# File: healthcheck.py
import os
import sqlite3
import importlib

REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "TINA_ADMIN_PASS"
]

OPTIONAL_ENV_VARS = [
    "MAIL_HOST", "EMAIL_PORT", "EMAIL_USER", "EMAIL_PASS"
]

REQUIRED_MODULES = [
    "gradio", "openai", "bcrypt", "pytesseract", "PIL", "pdfplumber",
    "PyMuPDF", "sentence_transformers", "faiss", "numpy",
    "torch", "transformers", "textract"
]

def check_env():
    print("\n🔍 Checking .env variables...")
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            print(f"❌ Missing required env var: {var}")
        else:
            print(f"✅ {var} is set")
    for var in OPTIONAL_ENV_VARS:
        if os.getenv(var):
            print(f"🟡 Optional {var} is set")

def check_modules():
    print("\n📦 Checking Python dependencies...")
    for mod in REQUIRED_MODULES:
        try:
            importlib.import_module(mod)
            print(f"✅ {mod}")
        except ImportError:
            print(f"❌ Missing: {mod}")

def check_db_connection():
    print("\n🧠 Checking database connection...")
    try:
        conn = sqlite3.connect("query_log.db")
        conn.execute("SELECT 1")
        print("✅ Connected to query_log.db")
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")

def check_knowledge_dir():
    print("\n📁 Checking knowledge_files/ directory...")
    if os.path.isdir("knowledge_files"):
        print("✅ knowledge_files/ exists")
        files = os.listdir("knowledge_files")
        print(f"🗂 Found {len(files)} files")
    else:
        print("❌ knowledge_files/ directory missing")

def run_all_checks():
    check_env()
    check_modules()
    check_db_connection()
    check_knowledge_dir()

if __name__ == "__main__":
    print("\n🚦 Running TINA health checks...")
    run_all_checks()
