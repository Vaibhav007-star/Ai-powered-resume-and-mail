from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.core.auth import hash_password, verify_password, create_access_token, get_current_user_id
from backend.core.database import create_user, get_user_by_email, get_user_by_id

router = APIRouter(prefix="/api/auth", tags=["Auth"])

class RegisterModel(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = ""

class LoginModel(BaseModel):
    email: str
    password: str

@router.post("/register")
def register_user(payload: RegisterModel):
    """Register a new multi-tenant candidate user account."""
    if not payload.email.strip() or not payload.password.strip():
        raise HTTPException(status_code=400, detail="Email and password are required.")
    
    existing = get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    hashed = hash_password(payload.password)
    user = create_user(email=payload.email, password_hash=hashed, full_name=payload.full_name or "")
    token = create_access_token({"user_id": user["id"], "email": user["email"]})

    return {
        "status": "success",
        "message": "User registered successfully.",
        "token": token,
        "user": user
    }

@router.post("/login")
def login_user(payload: LoginModel):
    """Authenticate user credentials and issue JWT access token."""
    user = get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email address or password.")

    token = create_access_token({"user_id": user["id"], "email": user["email"]})
    user_info = {"id": user["id"], "email": user["email"], "full_name": user.get("full_name", "")}

    return {
        "status": "success",
        "message": "Authenticated successfully.",
        "token": token,
        "user": user_info
    }

@router.get("/me")
def get_current_user_profile(user_id: int = Depends(get_current_user_id)):
    """Get profile of current logged-in user."""
    user = get_user_by_id(user_id)
    if not user:
        return {"status": "guest", "user": {"id": 1, "email": "demo@assistant.local", "full_name": "Demo Candidate"}}
    return {"status": "success", "user": user}
