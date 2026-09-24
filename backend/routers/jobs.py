from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from backend.core.auth import get_current_user_id
from backend.core.database import (
    create_job,
    get_job,
    list_jobs,
    update_job,
    delete_job
)
from backend.services.job_analyzer import analyze_job_posting
from backend.services.job_fetcher import fetch_open_jobs

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

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

@router.post("/analyze")
def analyze_job(payload: JobAnalyzeRequest, user_id: int = Depends(get_current_user_id)):
    """Ingest job description and partition qualifications strictly into Required vs. Preferred."""
    if not payload.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description text is required.")

    analysis = analyze_job_posting(
        raw_text=payload.job_description,
        metadata={
            "company_name": payload.company_name,
            "job_title": payload.job_title,
            "company_email": payload.company_email,
            "location": payload.location
        }
    )

    job_id = create_job(
        company_name=analysis.get("company_name", payload.company_name or "Company"),
        company_email=analysis.get("company_email", payload.company_email or ""),
        job_title=analysis.get("job_title", payload.job_title or "Job Title"),
        location=analysis.get("location", payload.location or ""),
        job_url=payload.job_url or "",
        raw_description=payload.job_description,
        required_qualifications=analysis.get("required_qualifications", {}),
        preferred_qualifications=analysis.get("preferred_qualifications", {}),
        summary=analysis.get("summary", ""),
        user_id=user_id
    )

    persisted_job = get_job(job_id)
    return {
        "status": "success",
        "message": "Job posting analyzed and persisted successfully.",
        "job": persisted_job
    }

@router.get("/search")
def search_jobs(
    query: str = "data science",
    location: Optional[str] = "delhi_ncr",
    min_stipend: int = 10000,
    limit: int = 20
):
    """Search live open job openings across Indian internship boards (Delhi NCR) and open APIs."""
    import sys
    try:
        main_mod = sys.modules.get("backend.main")
        fetch_fn = getattr(main_mod, "fetch_open_jobs", fetch_open_jobs)
        results = fetch_fn(
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

@router.post("/import-and-analyze")
def import_and_analyze_job(payload: JobAnalyzeRequest, user_id: int = Depends(get_current_user_id)):
    """Directly import and analyze a discovered job posting."""
    return analyze_job(payload, user_id=user_id)

@router.get("")
def get_jobs(user_id: int = Depends(get_current_user_id)):
    """List all saved jobs."""
    jobs = list_jobs(user_id=user_id)
    return {"status": "success", "jobs": jobs}

@router.get("/{job_id}")
def get_single_job(job_id: int):
    """Get full details and structured requirements of a specific job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "success", "job": job}

@router.put("/{job_id}")
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

@router.delete("/{job_id}")
def delete_single_job(job_id: int):
    """Delete a saved job."""
    success = delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "success", "message": f"Job #{job_id} deleted successfully."}
