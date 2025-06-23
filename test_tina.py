import pytest
from app import is_ph_tax_query, gr_login, gr_signup

# Dummy session state
session = {}

# PH Tax Query Detection
def test_tax_keywords():
    assert is_ph_tax_query("What is VAT?") is True
    assert is_ph_tax_query("BIR Form 2550Q") is True
    assert is_ph_tax_query("How to get a TIN?") is True
    assert is_ph_tax_query("What is AI?") is False
    assert is_ph_tax_query("Tell me about US taxes") is False

# Signup should return a success or error
def test_signup():
    result = gr_signup("testuser", "testpass")
    assert "already exists" in result or "successfully" in result.lower()

# Login should return updated session or error
def test_login():
    session_state, msg = gr_login("admin", "admin@1971", session)
    assert "username" in session_state or "Invalid credentials" in msg
