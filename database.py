# database.py
import sqlite3
from datetime import datetime

DB_PATH = "query_log.db"

def get_conn():
    return sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS logs (... )""")
        c.execute("""CREATE TABLE IF NOT EXISTS summaries (...)""")
        c.execute("""CREATE TABLE IF NOT EXISTS subscribers (...)""")
        conn.commit()

def log_query(username, query, context, response):
    sql = "INSERT INTO logs(username, query, context, response) VALUES (?,?,?,?)"
    with get_conn() as conn:
        conn.execute(sql, (username, query, context, response))

# ... other DB functions for logs, summaries, subscribers
