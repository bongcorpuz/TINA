import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
from collections import defaultdict
import logging

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or SUPABASE_ANON_KEY

if not SUPABASE_URL:
    raise RuntimeError("❌ SUPABASE_URL is missing. Set it in environment variables or .env")
if not SUPABASE_ANON_KEY:
    raise RuntimeError("❌ SUPABASE_KEY (anon) is missing. Set it in environment variables or .env")
if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("❌ SUPABASE_SERVICE_ROLE_KEY is missing. Set it in environment variables or .env")

anon_supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
service_supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

PLAN_DURATIONS = {
    "free": 7,
    "monthly": 30,
    "quarterly": 90,
    "annual": 365
}

RESET_RATE_LIMIT = defaultdict(lambda: (0, datetime.min))
MAX_RESET_ATTEMPTS = 3
RESET_WINDOW = timedelta(minutes=15)

def register_user(username: str, email: str, password: str) -> str:
    try:
        existing = anon_supabase.auth.admin.list_users(email=email)
        if existing and existing.users:
            return "❌ Email already registered. Try logging in or use password reset."

        result = anon_supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        user = result.user

        if not user or not getattr(user, "id", None):
            logging.error(f"Signup error: Missing user or user ID. Full result: {result}")
            return "❌ Signup failed. Please try again later."

        user_id = user.id
        logging.info(f"Registering user with ID: {user_id}")

        expiry = (datetime.utcnow() + timedelta(days=PLAN_DURATIONS["free"])).isoformat()

        try:
            service_supabase.table("profiles").insert({
                "id": user_id,
                "username": username,
                "email": email,
                "role": "user",
                "subscription_level": "free",
                "subscription_expires": expiry
            }).execute()
        except Exception as e:
            logging.error(f"Profile insert error: {e}")
            return f"❌ Signup failed. {e}"

        return "✅ Signup successful. Please login."
    except Exception as e:
        logging.error(f"Signup error: {e}")
        return f"❌ Signup failed. {e}"

def authenticate_user(email: str, password: str) -> dict | None:
    try:
        result = anon_supabase.auth.sign_in_with_password({"email": email, "password": password})
        logging.info(f"Sign-in response: {result}")
        user = result.user
        if not user:
            logging.warning(f"Sign-in failed: No user returned for {email}")
            return None

        if not user.email_confirmed_at:
            return {"error": "❌ Email not confirmed. Please confirm your email to log in."}

        profile = service_supabase.table("profiles").select("*").eq("id", user.id).single().execute().data
        return {"id": user.id, "email": email, **profile} if profile else None
    except Exception as e:
        logging.warning(f"Login failed for {email}: {e}")
        return None

def renew_subscription(user_id: str, plan: str) -> str:
    duration = PLAN_DURATIONS.get(plan)
    if not duration:
        return f"❌ Invalid plan: {plan}"
    expiry = (datetime.utcnow() + timedelta(days=duration)).isoformat()
    try:
        service_supabase.table("profiles").update({
            "subscription_level": plan,
            "subscription_expires": expiry
        }).eq("id", user_id).execute()
        return f"✅ Subscription updated to {plan} until {expiry}"
    except Exception as e:
        logging.error(f"Subscription update error for user {user_id}: {e}")
        return "❌ Failed to update subscription."

def is_admin(user_id: str) -> bool:
    try:
        res = service_supabase.table("profiles").select("role").eq("id", user_id).single().execute()
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
        anon_supabase.auth.reset_password_email(email)
        RESET_RATE_LIMIT[email] = (attempts + 1, now)
        return "📧 Password reset email sent."
    except Exception as e:
        logging.warning(f"Password reset failed for {email}: {e}")
        return "❌ Failed to send reset email."

def recover_user_email(keyword: str) -> list[str]:
    try:
        res = service_supabase.table("profiles").select("username, email").ilike("username", f"%{keyword}%").execute()
        return [f"{row['username']} <{row['email']}>" for row in res.data] if res.data else []
    except Exception as e:
        logging.warning(f"Recover email failed for keyword '{keyword}': {e}")
        return []
