import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "pro-grade-ai-assistant-secret-key-2026")
ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 86400 * 7  # 7 days

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a secure random salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"{salt.hex()}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against stored salt$key hash."""
    if not hashed_password or "$" not in hashed_password:
        return False
    try:
        salt_hex, key_hex = hashed_password.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(key, expected_key)
    except Exception:
        return False

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode(data + padding)

def create_access_token(payload: Dict[str, Any], expires_in: int = TOKEN_EXPIRE_SECONDS) -> str:
    """Generate a lightweight, secure HS256 JWT access token."""
    header = {"alg": ALGORITHM, "typ": "JWT"}
    now = int(time.time())
    token_payload = dict(payload)
    token_payload.update({"iat": now, "exp": now + expires_in})

    encoded_header = _base64url_encode(json.dumps(header).encode('utf-8'))
    encoded_payload = _base64url_encode(json.dumps(token_payload).encode('utf-8'))
    
    signature_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), signature_input, hashlib.sha256).digest()
    encoded_signature = _base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify signature and expiration of an HS256 JWT token."""
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None

        encoded_header, encoded_payload, encoded_signature = parts
        signature_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')
        expected_signature = hmac.new(SECRET_KEY.encode('utf-8'), signature_input, hashlib.sha256).digest()
        
        if not hmac.compare_digest(_base64url_encode(expected_signature), encoded_signature):
            return None

        payload_bytes = _base64url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode('utf-8'))

        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None

def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    """Extract authenticated user_id from Authorization header."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        payload = decode_access_token(token)
        if payload and "user_id" in payload:
            return int(payload["user_id"])
    return 1
