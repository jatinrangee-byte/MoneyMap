"""
Supabase client helper and authentication module for MoneyMap.
Enforces Row Level Security (RLS) by passing the authenticated user's JWT to PostgREST.
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.environ.get("TESTING"):
    load_dotenv(os.path.join(BASE_DIR, ".env"))
    load_dotenv(os.path.join(BASE_DIR, ".env.local"), override=True)


DEFAULT_SUPABASE_URL = "https://arhfznmlbjxevsqstkcp.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_EBri7mpKhoWGtj3Angz1og_mu70Oauh"


def get_supabase_url() -> str:
    if os.environ.get("TESTING"):
        return ""
    return (
        os.environ.get("SUPABASE_URL")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        or DEFAULT_SUPABASE_URL
    ).strip()


def get_supabase_key() -> str:
    if os.environ.get("TESTING"):
        return ""
    return (
        os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
        or DEFAULT_SUPABASE_KEY
    ).strip()


def is_supabase_enabled() -> bool:
    """Returns True if Supabase configuration is present in environment."""
    return bool(get_supabase_url() and get_supabase_key())


def get_supabase_client(jwt: Optional[str] = None):
    """
    Returns an authenticated Supabase client.
    When a user JWT is provided, it is set on PostgREST so queries execute
    under that user's identity and PostgreSQL Row Level Security (RLS) is enforced.
    """
    if not is_supabase_enabled():
        return None

    from supabase import create_client

    client = create_client(get_supabase_url(), get_supabase_key())
    if jwt:
        client.postgrest.auth(jwt)
    return client


def verify_supabase_token(jwt_token: str) -> Optional[Dict[str, Any]]:
    """
    Validates a Supabase JWT access token using the Supabase Auth API
    with a payload decode fallback.
    Returns user dictionary if valid, None if invalid or expired.
    """
    if not is_supabase_enabled() or not jwt_token:
        return None

    import time
    import jwt as pyjwt

    # 1. Primary verification via Supabase Auth API
    try:
        client = get_supabase_client()
        if client:
            res = client.auth.get_user(jwt_token)
            if res and res.user:
                user = res.user
                meta = getattr(user, "user_metadata", {}) or {}
                name = meta.get("name") or (user.email.split("@")[0] if user.email else "User")
                currency = meta.get("currency", "₹")
                return {
                    "id": str(user.id),
                    "email": user.email,
                    "name": name,
                    "currency": currency
                }
    except Exception:
        pass

    # NOTE: Fallback without signature verification has been intentionally removed
    # to prevent JWT forgery attacks. If the Supabase Auth API is unavailable,
    # we return None so require_auth returns a proper 401.
    return None


def sign_up_user(email: str, password: str, name: str, currency: str = "₹") -> Dict[str, Any]:
    """Signs up a new user via Supabase Auth."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase is not configured.")

    res = client.auth.sign_up({
        "email": email,
        "password": password,
        "options": {
            "data": {
                "name": name,
                "currency": currency
            }
        }
    })
    return res


def sign_in_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticates a user via Supabase Auth."""
    client = get_supabase_client()
    if not client:
        raise RuntimeError("Supabase is not configured.")

    res = client.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
    return res
