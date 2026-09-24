import shutil
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.core import config
from backend.core.auth import get_current_user_id
from backend.core.database import (
    get_profile,
    save_profile,
    add_resume,
    list_resumes,
    set_active_resume
)
from backend.services.extractor import extract_text_from_file, extract_structured_profile

router = APIRouter(prefix="/api", tags=["Profile & Resume"])

class ProfileModel(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    degree: str = ""
    graduation_year: str = ""
    skills: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    work_mode: str = "Any"
    experience_level: str = "Mid"
    other_preferences: str = ""
    raw_resume_text: Optional[str] = None
    active_resume_id: Optional[int] = None

@router.get("/profile")
def get_user_profile_endpoint(user_id: int = Depends(get_current_user_id)):
    """Retrieve candidate's stored profile."""
    profile = get_profile(user_id=user_id)
    return {"status": "success", "profile": profile}

@router.post("/profile")
def update_user_profile_endpoint(payload: ProfileModel, user_id: int = Depends(get_current_user_id)):
    """Save or update candidate profile."""
    updated = save_profile(payload.model_dump(), user_id=user_id)
    return {
        "status": "success",
        "message": "Profile saved successfully.",
        "profile": updated
    }

@router.post("/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    label: str = Form("General Resume"),
    auto_extract: bool = Form(True),
    user_id: int = Depends(get_current_user_id)
):
    """Upload a resume (.pdf, .docx, or .txt) and extract text & profile."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename provided")
        
    allowed_extensions = {".pdf", ".docx", ".doc", ".txt"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(allowed_extensions)}"
        )
        
    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(file.filename).name}"
    target_path = config.UPLOADS_DIR / safe_name
    
    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        raw_text = extract_text_from_file(target_path)
        
        resume_id = add_resume(
            filename=file.filename,
            stored_path=str(target_path),
            label=label,
            raw_text=raw_text,
            user_id=user_id
        )
        
        extracted_profile = None
        if auto_extract:
            extracted_profile = extract_structured_profile(raw_text)
            
        return {
            "status": "success",
            "message": f"Resume '{file.filename}' uploaded and parsed successfully.",
            "resume": {
                "id": resume_id,
                "filename": file.filename,
                "label": label,
                "char_count": len(raw_text)
            },
            "extracted_profile": extracted_profile
        }
        
    except Exception as e:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to process resume: {str(e)}")

@router.get("/resumes")
def get_all_resumes(user_id: int = Depends(get_current_user_id)):
    """List all uploaded resumes."""
    resumes = list_resumes(user_id=user_id)
    return {"status": "success", "resumes": resumes}

@router.post("/resumes/{resume_id}/set-active")
def activate_resume(resume_id: int, user_id: int = Depends(get_current_user_id)):
    """Set the active resume version for matching."""
    success = set_active_resume(resume_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"status": "success", "message": f"Resume #{resume_id} is now active."}
