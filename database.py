# database.py
import sqlite3
from datetime import datetime

DB_PATH = "query_log.db"

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
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            hash TEXT PRIMARY KEY,
            summary TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            username TEXT PRIMARY KEY,
            password TEXT,
            subscription_level TEXT DEFAULT 'free',
            subscription_expires TEXT DEFAULT ''
        )
        """)
        conn.commit()

def log_query(username, query, context, response):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO logs (username, query, context, response) VALUES (?, ?, ?, ?)",
            (username, query, context, response)
        )
        conn.commit()

def view_logs(user_filter="", date_filter=""):
    query = "SELECT rowid, username, query, response, timestamp FROM logs"
    conditions = []
    params = []
    if user_filter:
        conditions.append("username = ?")
        params.append(user_filter)
    if date_filter:
        conditions.append("date(timestamp) = ?")
        params.append(date_filter)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY timestamp DESC LIMIT 100"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return "\n\n".join([f"[ID {r[0]}] [{r[4]}] {r[1]}: Q: {r[2]}\nA: {r[3]}" for r in rows]) or "No logs found."

def delete_log_by_id(log_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM logs WHERE rowid = ?", (log_id,))
        conn.commit()
    return f"Log entry ID {log_id} deleted."

def export_logs_csv():
    import csv
    import os
    UPLOAD_DIR = "knowledge_files"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    csv_path = os.path.join(UPLOAD_DIR, "logs_export.csv")
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs")
        rows = cursor.fetchall()
        headers = [d[0] for d in cursor.description]
        with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
    return csv_path

def view_summaries():
    with get_conn() as conn:
        rows = conn.execute("SELECT hash, summary FROM summaries ORDER BY ROWID DESC LIMIT 100").fetchall()
    return "\n\n".join([f"{r[0][:10]}...: {r[1]}" for r in rows]) or "No summaries found."