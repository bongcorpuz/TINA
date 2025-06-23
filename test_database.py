# test_database.py
import os
import pytest
from database import (
    init_db, get_conn, log_query, view_logs, view_summaries,
    store_file_text, export_logs_csv, delete_log_by_id
)

def test_log_query():
    log_query("test", "What is VAT?", "semantic", "Value Added Tax")
    logs = view_logs()
    assert any("VAT" in row[1] for row in logs)

def test_store_file_text():
    content = "Sample tax document content"
    filename = "sample.txt"
    path = store_file_text(filename, content)
    assert os.path.exists(path)
    summaries = view_summaries()
    assert any("sample.txt" in row[1] for row in summaries)

def test_export_logs_csv():
    path = export_logs_csv()
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        assert "Username" in f.readline()

def test_delete_log_by_id():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO logs(username, query, context, response) VALUES (?,?,?,?)", ("test", "delete me", "ctx", "bye"))
        rowid = c.lastrowid
        conn.commit()
    msg = delete_log_by_id(rowid)
    assert f"Log ID {rowid} deleted." in msg
