"""SKINSIGHT v2 — Auth Service"""
import os, hashlib, hmac, json, base64, time
from typing import Optional

SECRET_KEY   = os.getenv("SECRET_KEY", "skinsight-v2-secret-change-in-production")
TOKEN_EXPIRY = 86400 * 7

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    h    = hashlib.sha256((salt + password + SECRET_KEY).encode()).hexdigest()
    return f"{salt}:{h}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":")
        return hmac.compare_digest(h, hashlib.sha256((salt + password + SECRET_KEY).encode()).hexdigest())
    except Exception:
        return False

def create_token(user_id: int, email: str) -> str:
    payload = {"user_id": user_id, "email": email, "exp": int(time.time()) + TOKEN_EXPIRY}
    p64  = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig  = hmac.new(SECRET_KEY.encode(), p64.encode(), hashlib.sha256).hexdigest()
    return f"{p64}.{sig}"

def verify_token(token: str) -> Optional[dict]:
    try:
        p64, sig = token.rsplit(".", 1)
        if not hmac.compare_digest(sig, hmac.new(SECRET_KEY.encode(), p64.encode(), hashlib.sha256).hexdigest()):
            return None
        payload = json.loads(base64.urlsafe_b64decode(p64).decode())
        return None if payload.get("exp", 0) < int(time.time()) else payload
    except Exception:
        return None
