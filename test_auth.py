# test_auth.py
import pytest
from auth import register_user, authenticate_user, is_admin, renew_subscription
from database import init_db, get_conn
from datetime import datetime

USERNAME = "testuser"
PASSWORD = "testpass"

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()
    with get_conn() as conn:
        conn.execute("DELETE FROM subscribers WHERE username=?", (USERNAME,))


def test_register_user():
    assert register_user(USERNAME, PASSWORD) is True
    assert register_user(USERNAME, PASSWORD) is False  # duplicate


def test_authenticate_user():
    assert authenticate_user(USERNAME, PASSWORD) == "user"
    assert authenticate_user(USERNAME, "wrong") is None


def test_is_admin():
    assert is_admin("admin") is True
    assert is_admin("user") is False


def test_renew_subscription():
    result = renew_subscription(USERNAME, "monthly")
    assert "renewed to monthly" in result
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT subscription_level FROM subscribers WHERE username=?", (USERNAME,))
        row = cur.fetchone()
        assert row and row[0] == "monthly"
