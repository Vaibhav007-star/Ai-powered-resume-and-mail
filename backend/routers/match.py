from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.core.auth import get_current_user_id
from backend.core.database import (
    get_profile,
    get_job,
    get_resume,
    save_application
)
from backend.services.matcher import evaluate_candidate_match
from backend.services.email_generator import generate_application_email
from backend.services.ats_optimizer import analyze_ats_optimization

router = APIRouter(prefix="/api", tags=["Matching & Pitch Studio"])

class JobMatchRequest(BaseModel):
    job_id: int

class ATSOptimizeRequest(BaseModel):
    job_id: int

@router.post("/match/evaluate")
def match_candidate_to_job(payload: JobMatchRequest, user_id: int = Depends(get_current_user_id)):
    """Evaluates candidate profile and active resume against a specific job."""
    profile = get_profile(user_id=user_id)
    job = get_job(payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    match_result = evaluate_candidate_match(profile, job)
    return {
        "status": "success",
        "job_id": payload.job_id,
        "match": match_result
    }

@router.post("/email/generate")
def generate_email_for_job(payload: JobMatchRequest, user_id: int = Depends(get_current_user_id)):
    """Generates personalized application email draft and saves to applications table."""
    profile = get_profile(user_id=user_id)
    job = get_job(payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    match_result = evaluate_candidate_match(profile, job)
    email_result = generate_application_email(profile, job, match_result)

    active_resume = None
    if profile.get("active_resume_id"):
        active_resume = get_resume(profile["active_resume_id"])

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
        status="Draft",
        user_id=user_id
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

@router.post("/match/ats-optimize")
def optimize_ats(payload: ATSOptimizeRequest, user_id: int = Depends(get_current_user_id)):
    """Perform semantic vector TF-IDF & ATS keyword gap analysis."""
    profile = get_profile(user_id=user_id)
    job = get_job(payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found.")

    ats_result = analyze_ats_optimization(profile, job)
    return {
        "status": "success",
        "job_id": payload.job_id,
        "ats_analysis": ats_result
    }
