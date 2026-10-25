"""
Authentication and security module for Personal Expense Tracker.
Implements PBKDF2-HMAC-SHA256 password hashing with salt and HMAC session tokens.
"""

import hashlib
import hmac
import os
import secrets
import time
import base64
import json

SECRET_KEY = os.environ.get("TRACKER_SECRET_KEY", "moneymap-finance-secret-key-prod")
ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """Hashes a password with a random 16-byte salt using PBKDF2-HMAC-SHA256."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        ITERATIONS
    )
    return f"{salt}${key.hex()}"


def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verifies a plain password against the stored salt$hash string."""
    try:
        salt, key_hex = stored_hash.split('$')
        new_key = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt.encode('utf-8'),
            ITERATIONS
        )
        return hmac.compare_digest(new_key.hex(), key_hex)
    except Exception:
        return False


def generate_session_token(user_id: int, duration_seconds: int = 86400 * 7) -> str:
    """Generates an HMAC-signed session token containing user_id and expiration."""
    payload = {
        "uid": user_id,
        "exp": int(time.time()) + duration_seconds,
        "rnd": secrets.token_hex(8)
    }
    payload_str = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_str.encode('utf-8')).decode('utf-8')
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_session_token(token: str) -> int | None:
    """Verifies signature and expiration of session token. Returns user_id if valid."""
    if not token or '.' not in token:
        return None
    try:
        payload_b64, signature = token.split('.', 1)
        expected_sig = hmac.new(
            SECRET_KEY.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            return None

        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode('utf-8'))
        payload = json.loads(payload_bytes.decode('utf-8'))

        if time.time() > payload.get("exp", 0):
            return None

        return payload.get("uid")
    except Exception:
        return None
