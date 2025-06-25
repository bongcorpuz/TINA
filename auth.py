# ------------------ auth.py ------------------
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
from collections import defaultdict
import logging

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PLAN_DURATIONS = {
    "free": 7,
    "monthly": 30,
    "quarterly": 90,
    "annual": 365
}

RESET_RATE_LIMIT = defaultdict(lambda: (0, datetime.min))
MAX_RESET_ATTEMPTS = 3
RESET_WINDOW = timedelta(minutes=15)

def register_user(email: str, password: str) -> str:
    try:
        result = supabase.auth.sign_up({"email": email, "password": password})
        user = result.user
        if not user:
            return "❌ Signup failed."

        expiry = (datetime.utcnow() + timedelta(days=PLAN_DURATIONS["free"])).date()
        supabase.table("profiles").insert({
            "id": user.id,
            "username": email,
            "role": "user",
            "subscription_level": "free",
            "subscription_expires": expiry
        }).execute()
        return "✅ Signup successful. Please login."
    except Exception as e:
        logging.error(f"Signup error: {e}")
        return "❌ Signup failed."

def authenticate_user(email: str, password: str) -> dict | None:
    try:
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = result.user
        if not user:
            return None
        profile = supabase.table("profiles").select("*", count='exact').eq("id", user.id).single().execute().data
        return {"id": user.id, "email": email, **profile} if profile else None
    except Exception as e:
        logging.warning(f"Login failed for {email}: {e}")
        return None

def renew_subscription(user_id: str, plan: str) -> str:
    duration = PLAN_DURATIONS.get(plan)
    if not duration:
        return f"❌ Invalid plan: {plan}"
    expiry = (datetime.utcnow() + timedelta(days=duration)).date()
    try:
        supabase.table("profiles").update({
            "subscription_level": plan,
            "subscription_expires": expiry
        }).eq("id", user_id).execute()
        return f"✅ Subscription updated to {plan} until {expiry}"
    except Exception as e:
        logging.error(f"Subscription update error for user {user_id}: {e}")
        return "❌ Failed to update subscription."

def is_admin(user_id: str) -> bool:
    try:
        res = supabase.table("profiles").select("role").eq("id", user_id).single().execute()
        return res.data.get("role") == "admin"
    except Exception as e:
        logging.warning(f"Admin check failed for {user_id}: {e}")
        return False

def send_password_reset(email: str) -> str:
    now = datetime.utcnow()
    attempts, last_reset = RESET_RATE_LIMIT[email]

    if now - last_reset > RESET_WINDOW:
        attempts = 0

    if attempts >= MAX_RESET_ATTEMPTS:
        return "❌ Too many reset attempts. Try again later."

    try:
        supabase.auth.reset_password_email(email)
        RESET_RATE_LIMIT[email] = (attempts + 1, now)
        return "📧 Password reset email sent."
    except Exception as e:
        logging.warning(f"Password reset failed for {email}: {e}")
        return "❌ Failed to send reset email."

def recover_user_email(keyword: str) -> list[str]:
    try:
        res = supabase.table("profiles").select("username, email").ilike("username", f"%{keyword}%").execute()
        return [row["username"] for row in res.data] if res.data else []
    except Exception as e:
        logging.warning(f"Recover email failed for keyword '{keyword}': {e}")
        return []
