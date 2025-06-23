# database.py
import sqlite3
import os
import hashlib
from datetime import datetime

DB_PATH = os.getenv("DATABASE_PATH", "query_log.db")
KNOWLEDGE_DIR = "knowledge_files"
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

def get_conn():
    return sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            username TEXT,
            query TEXT,
            context TEXT,
            response TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            hash TEXT PRIMARY KEY,
            summary TEXT
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            username TEXT PRIMARY KEY,
            password TEXT,
            subscription_level TEXT DEFAULT 'free',
            subscription_expires TEXT DEFAULT ''
        )""")
        conn.commit()

def log_query(username, query, context, response):
    sql = "INSERT INTO logs(username, query, context, response) VALUES (?,?,?,?)"
    with get_conn() as conn:
        conn.execute(sql, (username, query, context, response))

def store_file_text(filename: str, content: str):
    hash_digest = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
    path = os.path.join(KNOWLEDGE_DIR, filename)

    # Check if file with same hash already exists
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM summaries WHERE hash = ?", (hash_digest,))
        if c.fetchone():
            return path  # Skip storing duplicate

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        c.execute("INSERT OR IGNORE INTO summaries (hash, summary) VALUES (?, ?)", (hash_digest, filename))
        conn.commit()

    return path
