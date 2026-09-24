import uuid
import pytest
from backend.core.auth import hash_password, verify_password, create_access_token, decode_access_token
from backend.core.database import create_user, get_user_by_email, get_user_by_id

def test_password_hashing_and_verification():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_creation_and_decoding():
    payload = {"user_id": 42, "email": "candidate@prograde.ai"}
    token = create_access_token(payload, expires_in=3600)
    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["user_id"] == 42
    assert decoded["email"] == "candidate@prograde.ai"

def test_jwt_token_expiration():
    payload = {"user_id": 42}
    token = create_access_token(payload, expires_in=-10)  # Expired
    decoded = decode_access_token(token)
    assert decoded is None

def test_user_creation_and_lookup():
    email = f"user_{uuid.uuid4().hex}@prograde.ai"
    hashed = hash_password("password123")
    user = create_user(email=email, password_hash=hashed, full_name="Pro Candidate")
    assert user is not None
    assert user["email"] == email
    
    found = get_user_by_email(email)
    assert found is not None
    assert found["id"] == user["id"]
