import os
import sqlite3
from datetime import datetime, timedelta
import bcrypt
import logging
from dotenv import load_dotenv
from PIL import Image
import pytesseract
import pdfplumber
import openai

# Load environment variables
load_dotenv()

DB_NAME = "tina_users.db"
KNOWLEDGE_FOLDER = "knowledge_files"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Ensure knowledge folder exists
os.makedirs(KNOWLEDGE_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            email_confirmed INTEGER DEFAULT 0,
            subscription_level TEXT CHECK(subscription_level IN ('monthly', 'quarterly', 'yearly')) NOT NULL,
            subscription_expires TEXT NOT NULL,
            role TEXT DEFAULT 'user' CHECK(role IN ('user', 'admin', 'premium')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS qna_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            source TEXT DEFAULT 'chatGPT',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_update_timestamp
        AFTER UPDATE ON users
        BEGIN
            UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_username ON users(username)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_email ON users(email)")
    conn.commit()
    conn.close()
    logging.info("Database initialized successfully.")
    create_default_admin()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def add_user(username: str, password: str, email: str, subscription_level: str) -> bool:
    days = {"monthly": 30, "quarterly": 90, "yearly": 365}
    if subscription_level not in days:
        logging.warning("Invalid subscription level provided.")
        return False
    expires = (datetime.now() + timedelta(days=days[subscription_level])).strftime("%Y-%m-%d")
    hashed_pw = hash_password(password)
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, password, email, subscription_level, subscription_expires) VALUES (?, ?, ?, ?, ?)",
            (username, hashed_pw, email, subscription_level, expires)
        )
        conn.commit()
        conn.close()
        logging.info(f"User {username} added successfully.")
        return True
    except sqlite3.IntegrityError as e:
        logging.error(f"Failed to add user {username}: {e}")
        return False

def get_user(username: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "username": row[1],
            "password": row[2],
            "email": row[3],
            "email_confirmed": bool(row[4]),
            "subscription_level": row[5],
            "subscription_expires": row[6],
            "role": row[7],
            "created_at": row[8],
            "updated_at": row[9]
        }
    return None

def update_subscription(username: str, new_level: str) -> bool:
    days = {"monthly": 30, "quarterly": 90, "yearly": 365}
    if new_level not in days:
        logging.warning("Invalid subscription level provided for update.")
        return False
    # Extend from current expiry if in the future, else from now
    user = get_user(username)
    if not user:
        logging.error(f"User {username} not found for subscription update.")
        return False
    expiry_date = datetime.strptime(user["subscription_expires"], "%Y-%m-%d")
    start_date = max(datetime.now(), expiry_date)
    new_expires = (start_date + timedelta(days=days[new_level])).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "UPDATE users SET subscription_level = ?, subscription_expires = ? WHERE username = ?",
        (new_level, new_expires, username)
    )
    conn.commit()
    conn.close()
    logging.info(f"Subscription updated for {username} to {new_level}.")
    return True

def confirm_email(username: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET email_confirmed = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    logging.info(f"Email confirmed for user {username}.")
    return True

def create_default_admin():
    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    user = get_user(admin_username)
    if user is None:
        success = add_user(admin_username, admin_password, admin_email, "yearly")
        if success:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("UPDATE users SET role = 'admin' WHERE username = ?", (admin_username,))
            conn.commit()
            conn.close()
            logging.info("Default admin account created.")

def process_uploaded_file(upload_path: str):
    try:
        filename = os.path.basename(upload_path)
        name, ext = os.path.splitext(filename)
        output_path = os.path.join(KNOWLEDGE_FOLDER, f"{name}.txt")
        ext = ext.lower()
        if ext in [".jpg", ".jpeg", ".png"]:
            image = Image.open(upload_path)
            text = pytesseract.image_to_string(image)
        elif ext == ".pdf":
            text = ""
            with pdfplumber.open(upload_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        elif ext in [".txt", ".md"]:
            with open(upload_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            logging.warning(f"Unsupported file type: {ext}")
            return None
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        logging.info(f"Processed and saved: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Error processing file {upload_path}: {e}")
        return None

def is_valid_tax_question(text: str) -> bool:
    tax_keywords = [
        k.strip() for k in os.getenv(
            "TAX_KEYWORDS",
            "tax,vat,bir,rdo,tin,withholding,income tax,1701,1702,2550,0605,0619,form,return,compliance,Philippine taxation,CREATE law,TRAIN law,ease of paying taxes"
        ).split(",")
    ]
    return any(keyword.lower() in text.lower() for keyword in tax_keywords)

def save_qna(question: str, answer: str, source: str = "chatGPT"):
    if not is_valid_tax_question(question):
        logging.warning("Skipped saving non-tax question.")
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO qna_log (question, answer, source) VALUES (?, ?, ?)",
        (question, answer, source)
    )
    conn.commit()
    conn.close()
    logging.info(f"QnA stored: {question} → {source}")

if __name__ == "__main__":
    init_db()
    try:
        import interface  # launches Gradio interface
    except ImportError:
        logging.warning("Optional 'interface' module not found. Gradio UI will not be launched.")