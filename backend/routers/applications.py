from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.core.auth import get_current_user_id
from backend.core.database import (
    get_job,
    get_resume,
    get_application,
    get_application_by_job,
    update_application_draft,
    mark_application_sent,
    list_applications,
    update_application_status,
    delete_application,
    get_tracking_metrics,
    list_email_logs
)
from backend.services.email_service import send_application_email
from backend.services.duplicate_checker import check_duplicate_application

router = APIRouter(prefix="/api", tags=["Applications & Tracking Cockpit"])

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

class DraftUpdateRequest(BaseModel):
    email_subject: str
    email_body: str
    recipient_email: str

class ApproveAndSendRequest(BaseModel):
    approved: bool
    recipient_email: str
    email_subject: str
    email_body: str
    attach_resume: bool = True
    override_duplicate: bool = False
    notes: Optional[str] = ""

class ApplicationStatusUpdateRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    response_status: Optional[str] = None

@router.get("/jobs/{job_id}/application")
def get_job_application_draft(job_id: int):
    """Retrieve saved application draft for a job."""
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

@router.put("/applications/{app_id}/draft")
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

@router.get("/applications/{app_id}/review-packet")
def get_review_packet(app_id: int, user_id: int = Depends(get_current_user_id)):
    """Assembles complete review packet prior to human approval."""
    application = get_application(app_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application record not found.")

    job = get_job(application["job_id"])
    attached_resume = None
    if application.get("attached_resume_id"):
        attached_resume = get_resume(application["attached_resume_id"])

    dup_check = check_duplicate_application(
        company_name=application.get("company_name", ""),
        job_title=application.get("job_title", ""),
        recipient_email=application.get("recipient_email", ""),
        exclude_app_id=app_id,
        user_id=user_id
    )

    return {
        "status": "success",
        "application": application,
        "job": job,
        "attached_resume": attached_resume,
        "duplicate_check": dup_check
    }

@router.post("/applications/{app_id}/send")
def approve_and_send_application(app_id: int, payload: ApproveAndSendRequest, user_id: int = Depends(get_current_user_id)):
    """Executes human-approved application email dispatch."""
    if not payload.approved:
        raise HTTPException(
            status_code=400,
            detail="Explicit human approval is required before sending an application email."
        )

    application = get_application(app_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application record not found.")

    dup_check = check_duplicate_application(
        company_name=application.get("company_name", ""),
        job_title=application.get("job_title", ""),
        recipient_email=payload.recipient_email,
        exclude_app_id=app_id,
        user_id=user_id
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

    attachment_path = None
    if payload.attach_resume and application.get("attached_resume_id"):
        resume_record = get_resume(application["attached_resume_id"])
        if resume_record and resume_record.get("stored_path"):
            attachment_path = resume_record["stored_path"]

    try:
        dispatch_result = send_application_email(
            recipient_email=payload.recipient_email,
            subject=payload.email_subject,
            body=payload.email_body,
            attachment_path=attachment_path,
            user_id=user_id,
            application_id=app_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email dispatch failed: {str(e)}")

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

@router.get("/applications")
def get_all_applications(status: Optional[str] = None, user_id: int = Depends(get_current_user_id)):
    """Retrieve all tracked applications."""
    apps = list_applications(status=status, user_id=user_id)
    return {
        "status": "success",
        "count": len(apps),
        "applications": apps
    }

@router.get("/applications/metrics")
def get_dashboard_metrics(user_id: int = Depends(get_current_user_id)):
    """Retrieve aggregate statistics across all applications."""
    metrics = get_tracking_metrics(user_id=user_id)
    return {
        "status": "success",
        "metrics": metrics
    }

@router.patch("/applications/{app_id}/status")
def update_app_status(app_id: int, payload: ApplicationStatusUpdateRequest):
    """Update application status, notes, follow-up date, or response status."""
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

@router.delete("/applications/{app_id}")
def remove_application(app_id: int):
    """Delete an application record by ID."""
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

@router.get("/email/logs")
def get_email_audit_logs(user_id: int = Depends(get_current_user_id)):
    """List email dispatch audit trail logs."""
    logs = list_email_logs(user_id=user_id)
    return {"status": "success", "count": len(logs), "logs": logs}
