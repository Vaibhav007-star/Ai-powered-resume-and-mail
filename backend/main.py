import os
import shutil
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import config
from backend.config import BASE_DIR, GEMINI_API_KEY
from backend.database import (
    init_db,
    get_profile,
    save_profile,
    add_resume,
    list_resumes,
    get_resume,
    set_active_resume,
    create_job,
    get_job,
    list_jobs,
    update_job,
    delete_job,
    save_application,
    get_application_by_job,
    get_application,
    update_application_draft,
    mark_application_sent,
    list_applications,
    update_application_status,
    delete_application,
    get_tracking_metrics
)
from backend.extractor import extract_text_from_file, extract_structured_profile
from backend.job_analyzer import analyze_job_posting
from backend.job_fetcher import fetch_open_jobs
from backend.matcher import evaluate_candidate_match
from backend.email_generator import generate_application_email
from backend.email_service import send_application_email, is_valid_email
from backend.duplicate_checker import check_duplicate_application

# Initialize database schema
init_db()

app = FastAPI(
    title="AI-Powered Personalized Job Application Assistant",
    description="Local, reliable, and truth-preserving assistant for job seekers.",
    version="1.0.0"
)

# Enable CORS for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend directories
FRONTEND_DIR = BASE_DIR / "frontend"
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

# Mount frontend directory for static assets
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Pydantic models for validation
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

@app.get("/", response_class=FileResponse)
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
    return FileResponse(index_path)

@app.get("/api/health")
def health_check():
    from backend.llm import is_llm_configured, get_active_model
    return {
        "status": "healthy",
        "phase": "Complete 5-Phase Environment",
        "ai_configured": is_llm_configured(),
        "model": get_active_model()
    }

@app.get("/api/profile")
def get_user_profile():
    """Retrieve candidate's stored profile."""
    profile = get_profile()
    return {"status": "success", "profile": profile}

@app.post("/api/profile")
def update_user_profile(payload: ProfileModel):
    """Save or update candidate profile."""
    updated = save_profile(payload.model_dump())
    return {
        "status": "success",
        "message": "Profile saved successfully.",
        "profile": updated
    }

@app.post("/api/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    label: str = Form("General Resume"),
    auto_extract: bool = Form(True)
):
    """
    Upload a resume (.pdf, .docx, or .txt), extract text,
    optionally extract structured fields, and persist to database.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename provided")
        
    allowed_extensions = {".pdf", ".docx", ".doc", ".txt"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file_ext}'. Allowed formats: {', '.join(allowed_extensions)}"
        )
        
    # Generate unique safe filename
    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(file.filename).name}"
    target_path = config.UPLOADS_DIR / safe_name
    
    try:
        # Save file to disk
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Extract raw text from file
        raw_text = extract_text_from_file(target_path)
        
        # Save resume record to SQLite
        resume_id = add_resume(
            filename=file.filename,
            stored_path=str(target_path),
            label=label,
            raw_text=raw_text
        )
        
        # Optionally perform structured extraction
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
        # Cleanup temporary file if extraction failed
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to process resume: {str(e)}")

@app.get("/api/resumes")
def get_all_resumes():
    """List all uploaded resumes."""
    resumes = list_resumes()
    return {"status": "success", "resumes": resumes}

@app.post("/api/resumes/{resume_id}/set-active")
def activate_resume(resume_id: int):
    """Set the active resume version for matching."""
    success = set_active_resume(resume_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {"status": "success", "message": f"Resume #{resume_id} is now active."}

# -------------------------------------------------------------
# Phase 2: Job Analysis Models & Endpoints
# -------------------------------------------------------------

class JobAnalyzeRequest(BaseModel):
    job_description: str
    company_name: Optional[str] = ""
    job_title: Optional[str] = ""
    company_email: Optional[str] = ""
    location: Optional[str] = ""
    job_url: Optional[str] = ""

class JobUpdateRequest(BaseModel):
    company_name: str
    company_email: str = ""
    job_title: str
    location: str = ""
    job_url: str = ""
    required_qualifications: Dict[str, Any] = Field(default_factory=dict)
    preferred_qualifications: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""

@app.post("/api/jobs/analyze")
def analyze_job(payload: JobAnalyzeRequest):
    """
    Ingest job description and partition qualifications strictly into
    Required vs. Preferred. Persists analysis to SQLite.
    """
    if not payload.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description text is required.")

    # Run AI/Heuristic requirement extraction
    analysis = analyze_job_posting(
        raw_text=payload.job_description,
        metadata={
            "company_name": payload.company_name,
            "job_title": payload.job_title,
            "company_email": payload.company_email,
            "location": payload.location
        }
    )

    # Save to SQLite database
    job_id = create_job(
        company_name=analysis.get("company_name", payload.company_name or "Company"),
        company_email=analysis.get("company_email", payload.company_email or ""),
        job_title=analysis.get("job_title", payload.job_title or "Job Title"),
        location=analysis.get("location", payload.location or ""),
        job_url=payload.job_url or "",
        raw_description=payload.job_description,
        required_qualifications=analysis.get("required_qualifications", {}),
        preferred_qualifications=analysis.get("preferred_qualifications", {}),
        summary=analysis.get("summary", "")
    )

    persisted_job = get_job(job_id)
    return {
        "status": "success",
        "message": "Job posting analyzed and persisted successfully.",
        "job": persisted_job
    }

@app.get("/api/jobs/search")
def search_jobs(
    query: str = "data science",
    location: Optional[str] = "delhi_ncr",
    min_stipend: int = 10000,
    limit: int = 20
):
    """
    Search live open job openings across Indian internship boards (Delhi NCR) and open APIs.
    """
    try:
        results = fetch_open_jobs(
            query=query,
            location=location,
            min_stipend=min_stipend,
            limit=limit
        )
        return {
            "status": "success",
            "count": len(results),
            "jobs": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job search failed: {str(e)}")

@app.post("/api/jobs/import-and-analyze")
def import_and_analyze_job(payload: JobAnalyzeRequest):
    """
    Directly import and analyze a discovered job posting into the Phase 2
    qualifications decomposition and persist to SQLite.
    """
    return analyze_job(payload)

@app.get("/api/jobs")
def get_jobs():
    """List all saved jobs."""
    jobs = list_jobs()
    return {"status": "success", "jobs": jobs}

@app.get("/api/jobs/{job_id}")
def get_single_job(job_id: int):
    """Get full details and structured requirements of a specific job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "success", "job": job}

@app.put("/api/jobs/{job_id}")
def update_single_job(job_id: int, payload: JobUpdateRequest):
    """Update or refine extracted job requirements."""
    updated = update_job(
        job_id=job_id,
        company_name=payload.company_name,
        company_email=payload.company_email,
        job_title=payload.job_title,
        location=payload.location,
        job_url=payload.job_url,
        required_qualifications=payload.required_qualifications,
        preferred_qualifications=payload.preferred_qualifications,
        summary=payload.summary
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "status": "success",
        "message": "Job requirements updated successfully.",
        "job": updated
    }

@app.delete("/api/jobs/{job_id}")
def delete_single_job(job_id: int):
    """Delete a saved job."""
    success = delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "success", "message": f"Job #{job_id} deleted successfully."}

# -------------------------------------------------------------
# Phase 3: Candidate Matching & Email Generation Models & Endpoints
# -------------------------------------------------------------

class JobMatchRequest(BaseModel):
    job_id: int

class DraftUpdateRequest(BaseModel):
    email_subject: str
    email_body: str
    recipient_email: str

@app.post("/api/match/evaluate")
def match_candidate_to_job(payload: JobMatchRequest):
    """
    Evaluates candidate profile and active resume against a specific job.
    Returns transparent match breakdown and honest explanation.
    """
    profile = get_profile()
    job = get_job(payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    match_result = evaluate_candidate_match(profile, job)
    return {
        "status": "success",
        "job_id": payload.job_id,
        "match": match_result
    }

@app.post("/api/email/generate")
def generate_email_for_job(payload: JobMatchRequest):
    """
    Generates a personalized, truthful application email draft
    and saves it to the applications table.
    """
    profile = get_profile()
    job = get_job(payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Perform transparent match
    match_result = evaluate_candidate_match(profile, job)

    # Generate personalized email
    email_result = generate_application_email(profile, job, match_result)

    # Get active resume info if set
    active_resume = None
    if profile.get("active_resume_id"):
        active_resume = get_resume(profile["active_resume_id"])

    # Persist draft to SQLite applications table
    app_id = save_application(
        job_id=job["id"],
        company_name=job.get("company_name", ""),
        job_title=job.get("job_title", ""),
        recipient_email=job.get("company_email", ""),
        match_score=match_result.get("match_score", 0),
        match_summary=match_result,
        email_subject=email_result.get("subject", ""),
        email_body=email_result.get("body", ""),
        attached_resume_id=profile.get("active_resume_id"),
        status="Draft"
    )

    return {
        "status": "success",
        "message": "Personalized application email generated successfully.",
        "application_id": app_id,
        "job": job,
        "match": match_result,
        "email": email_result,
        "attached_resume": active_resume
    }

@app.get("/api/jobs/{job_id}/application")
def get_job_application_draft(job_id: int):
    """Retrieve saved application draft for a job if available."""
    app_data = get_application_by_job(job_id)
    if not app_data:
        return {"status": "none", "application": None}
    
    active_resume = None
    if app_data.get("attached_resume_id"):
        active_resume = get_resume(app_data["attached_resume_id"])

    return {
        "status": "success",
        "application": app_data,
        "attached_resume": active_resume
    }

@app.put("/api/applications/{app_id}/draft")
def update_email_draft(app_id: int, payload: DraftUpdateRequest):
    """Update email draft subject, body, or recipient before approval."""
    updated = update_application_draft(
        app_id=app_id,
        email_subject=payload.email_subject,
        email_body=payload.email_body,
        recipient_email=payload.recipient_email
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found")
    return {
        "status": "success",
        "message": "Draft updated successfully.",
        "application": updated
    }

# -------------------------------------------------------------
# Phase 4: Review, Approval & Sending Models & Endpoints
# -------------------------------------------------------------

class ApproveAndSendRequest(BaseModel):
    approved: bool
    recipient_email: str
    email_subject: str
    email_body: str
    attach_resume: bool = True
    override_duplicate: bool = False
    notes: Optional[str] = ""

@app.get("/api/applications/{app_id}/review-packet")
def get_review_packet(app_id: int):
    """
    Assembles the complete packet required for human review prior to approval:
    Recipient, Company, Job Title, Email Subject, Email Body, Resume Attachment,
    Match Analysis, and Duplicate Check Warning.
    """
    application = get_application(app_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application record not found.")

    job = get_job(application["job_id"])
    attached_resume = None
    if application.get("attached_resume_id"):
        attached_resume = get_resume(application["attached_resume_id"])

    # Run duplicate check
    dup_check = check_duplicate_application(
        company_name=application.get("company_name", ""),
        job_title=application.get("job_title", ""),
        recipient_email=application.get("recipient_email", ""),
        exclude_app_id=app_id
    )

    return {
        "status": "success",
        "application": application,
        "job": job,
        "attached_resume": attached_resume,
        "duplicate_check": dup_check
    }

@app.post("/api/applications/{app_id}/send")
def approve_and_send_application(app_id: int, payload: ApproveAndSendRequest):
    """
    Executes the human-approved dispatch:
    Generate → Review → Approve → Send.
    Validates approval, guards against duplicates, sends email via email service,
    and updates application status to 'Sent'.
    """
    # 1. Strict Human Approval Enforcement (Master Prompt Section 11)
    if not payload.approved:
        raise HTTPException(
            status_code=400,
            detail="Explicit human approval is required before sending an application email."
        )

    application = get_application(app_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application record not found.")

    # 2. Duplicate Application Protection (Master Prompt Section 13)
    dup_check = check_duplicate_application(
        company_name=application.get("company_name", ""),
        job_title=application.get("job_title", ""),
        recipient_email=payload.recipient_email,
        exclude_app_id=app_id
    )

    if dup_check["is_duplicate"] and not payload.override_duplicate:
        return JSONResponse(
            status_code=409,
            content={
                "status": "duplicate_warning",
                "message": dup_check["warning_message"],
                "duplicates": dup_check["duplicates"]
            }
        )

    # 3. Locate Attachment
    attachment_path = None
    if payload.attach_resume and application.get("attached_resume_id"):
        resume_record = get_resume(application["attached_resume_id"])
        if resume_record and resume_record.get("stored_path"):
            attachment_path = resume_record["stored_path"]

    # 4. Dispatch Email via Decoupled Email Service
    try:
        dispatch_result = send_application_email(
            recipient_email=payload.recipient_email,
            subject=payload.email_subject,
            body=payload.email_body,
            attachment_path=attachment_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email dispatch failed: {str(e)}")

    # 5. Transition Application Status to 'Sent' in SQLite
    updated_app = mark_application_sent(
        app_id=app_id,
        recipient_email=payload.recipient_email,
        email_subject=payload.email_subject,
        email_body=payload.email_body,
        notes=payload.notes or ("Sent via Dry-Run Preview" if dispatch_result.get("dry_run") else "Sent via SMTP")
    )

    return {
        "status": "success",
        "message": dispatch_result.get("message", "Application successfully dispatched."),
        "dispatch": dispatch_result,
        "application": updated_app
    }

# -------------------------------------------------------------
# Phase 5: Tracking Dashboard & Application Status Endpoints
# -------------------------------------------------------------

VALID_APPLICATION_STATUSES = [
    "Draft",
    "Ready for Review",
    "Sent",
    "Follow-up",
    "Interview",
    "Rejected",
    "Offer",
    "Closed"
]

class ApplicationStatusUpdateRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    response_status: Optional[str] = None

@app.get("/api/applications")
def get_all_applications(status: Optional[str] = None):
    """
    Retrieve all tracked applications, optionally filtered by status.
    Ordered by most recently updated.
    """
    apps = list_applications(status=status)
    return {
        "status": "success",
        "count": len(apps),
        "applications": apps
    }

@app.get("/api/applications/metrics")
def get_dashboard_metrics():
    """
    Retrieve aggregate statistics across all applications for dashboard summary cards.
    """
    metrics = get_tracking_metrics()
    return {
        "status": "success",
        "metrics": metrics
    }

@app.patch("/api/applications/{app_id}/status")
def update_app_status(app_id: int, payload: ApplicationStatusUpdateRequest):
    """
    Update application status, notes, follow-up date, or response status.
    Enforces valid status transitions according to Master Prompt Section 12.
    """
    app_record = get_application(app_id)
    if not app_record:
        raise HTTPException(status_code=404, detail="Application record not found.")

    if payload.status is not None:
        if payload.status not in VALID_APPLICATION_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{payload.status}'. Valid statuses: {', '.join(VALID_APPLICATION_STATUSES)}"
            )

    updated = update_application_status(
        app_id=app_id,
        status=payload.status,
        notes=payload.notes,
        follow_up_date=payload.follow_up_date,
        response_status=payload.response_status
    )

    return {
        "status": "success",
        "message": f"Application #{app_id} updated.",
        "application": updated
    }

@app.delete("/api/applications/{app_id}")
def remove_application(app_id: int):
    """
    Delete an application record by ID.
    """
    app_record = get_application(app_id)
    if not app_record:
        raise HTTPException(status_code=404, detail="Application record not found.")

    success = delete_application(app_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete application.")

    return {
        "status": "success",
        "message": f"Application #{app_id} deleted successfully."
    }

# -------------------------------------------------------------
# Security & Hardening: User-Friendly Error Handler (Master Prompt Section 19)
# -------------------------------------------------------------

@app.exception_handler(Exception)
async def user_friendly_exception_handler(request, exc):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "detail": exc.detail}
        )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "detail": "An unexpected error occurred while processing your request. Please verify inputs or consult system logs."
        }
    )





