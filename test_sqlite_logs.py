import sqlite3
import os
import pytest

DB_PATH = "query_log.db"

def setup_module(module):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE logs (query TEXT, response TEXT)")
    conn.commit()
    conn.close()

def log_query_response(query, response):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO logs (query, response) VALUES (?, ?)", (query, response))
    conn.commit()
    conn.close()

def fetch_all_logs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM logs")
    rows = c.fetchall()
    conn.close()
    return rows

def test_logging():
    sample_query = "What is tax?"
    sample_response = "Tax is a compulsory contribution to state revenue."
    log_query_response(sample_query, sample_response)
    logs = fetch_all_logs()
    assert len(logs) == 1
    assert logs[0][0] == sample_query
    assert logs[0][1] == sample_response

def test_logging_multiple():
    entries = [
        ("What is VAT?", "VAT is a value-added tax."),
        ("What is income tax?", "Income tax is levied on income.")
    ]
    for q, r in entries:
        log_query_response(q, r)
    logs = fetch_all_logs()
    assert len(logs) == 3  # including previous test
    assert logs[1] == entries[0]
    assert logs[2] == entries[1]
