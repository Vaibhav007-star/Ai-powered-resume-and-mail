import os
import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.main import app, VALID_APPLICATION_STATUSES
from backend.core.database import (
    init_db,
    create_job,
    save_application,
    get_application,
    list_applications,
    update_application_status,
    delete_application,
    get_tracking_metrics
)

client = TestClient(app)

def setup_module():
    init_db()

def test_application_lifecycle_and_status_transitions():
    uid = uuid.uuid4().hex[:6]
    company = f"Phase5 Corp {uid}"
    email = f"recruiter_{uid}@phase5corp.io"

    # 1. Create a job and application
    job_id = create_job(
        company_name=company,
        company_email=email,
        job_title="Full Stack Cloud Architect",
        location="Hybrid",
        raw_description="Build scalable microservices."
    )

    app_id = save_application(
        job_id=job_id,
        company_name=company,
        job_title="Full Stack Cloud Architect",
        recipient_email=email,
        match_score=92,
        match_summary={"score": 92, "explanation": "Strong fit"},
        email_subject="Application for Cloud Architect",
        email_body="Dear Hiring Team...",
        status="Draft"
    )

    assert app_id is not None
    app_data = get_application(app_id)
    assert app_data["status"] == "Draft"

    # 2. Test status transition to 'Ready for Review'
    res = client.patch(f"/api/applications/{app_id}/status", json={"status": "Ready for Review"})
    assert res.status_code == 200
    assert res.json()["application"]["status"] == "Ready for Review"

    # 3. Test status transition to 'Sent'
    res = client.patch(f"/api/applications/{app_id}/status", json={"status": "Sent"})
    assert res.status_code == 200
    assert res.json()["application"]["status"] == "Sent"

    # 4. Test updating notes, follow-up date, and response status
    res = client.patch(f"/api/applications/{app_id}/status", json={
        "status": "Interview",
        "notes": "Completed initial recruiter phone screen on Tuesday. Technical round next.",
        "follow_up_date": "2026-10-01",
        "response_status": "Interview Scheduled"
    })
    assert res.status_code == 200
    updated = res.json()["application"]
    assert updated["status"] == "Interview"
    assert "Completed initial recruiter phone screen" in updated["notes"]
    assert updated["follow_up_date"] == "2026-10-01"
    assert updated["response_status"] == "Interview Scheduled"

    # 5. Test invalid status validation (HTTP 400)
    invalid_res = client.patch(f"/api/applications/{app_id}/status", json={"status": "NonExistentStatus"})
    assert invalid_res.status_code == 400
    assert "Invalid status" in invalid_res.json()["detail"]

def test_list_applications_and_filtering():
    uid = uuid.uuid4().hex[:6]
    company_a = f"Alpha_{uid}"
    company_b = f"Beta_{uid}"

    job_a = create_job(company_name=company_a, job_title="Engineer A", raw_description="Desc A")
    job_b = create_job(company_name=company_b, job_title="Engineer B", raw_description="Desc B")

    app_a = save_application(
        job_id=job_a,
        company_name=company_a,
        job_title="Engineer A",
        recipient_email="a@example.com",
        status="Offer"
    )
    app_b = save_application(
        job_id=job_b,
        company_name=company_b,
        job_title="Engineer B",
        recipient_email="b@example.com",
        status="Rejected"
    )

    # List all
    res_all = client.get("/api/applications")
    assert res_all.status_code == 200
    all_apps = res_all.json()["applications"]
    app_ids = [a["id"] for a in all_apps]
    assert app_a in app_ids
    assert app_b in app_ids

    # Filter by Offer
    res_offer = client.get("/api/applications?status=Offer")
    assert res_offer.status_code == 200
    offer_apps = res_offer.json()["applications"]
    assert all(a["status"] == "Offer" for a in offer_apps)
    assert any(a["id"] == app_a for a in offer_apps)

    # Filter by Rejected
    res_rejected = client.get("/api/applications?status=Rejected")
    assert res_rejected.status_code == 200
    rejected_apps = res_rejected.json()["applications"]
    assert all(a["status"] == "Rejected" for a in rejected_apps)
    assert any(a["id"] == app_b for a in rejected_apps)

def test_tracking_metrics_and_deletion():
    # Test metrics endpoint
    res_metrics = client.get("/api/applications/metrics")
    assert res_metrics.status_code == 200
    metrics = res_metrics.json()["metrics"]
    assert "total" in metrics
    assert "drafts" in metrics
    assert "sent" in metrics
    assert "interview" in metrics
    assert "offer" in metrics
    assert "due_follow_ups" in metrics
    assert metrics["total"] >= 1

    # Test application deletion
    uid = uuid.uuid4().hex[:6]
    job_id = create_job(company_name=f"DeleteCo_{uid}", job_title="Temp Role", raw_description="Temp")
    temp_app_id = save_application(
        job_id=job_id,
        company_name=f"DeleteCo_{uid}",
        job_title="Temp Role",
        recipient_email="temp@delete.com",
        status="Draft"
    )

    # Delete existing
    del_res = client.delete(f"/api/applications/{temp_app_id}")
    assert del_res.status_code == 200
    assert "deleted successfully" in del_res.json()["message"]

    # Verify deleted
    assert get_application(temp_app_id) is None

    # Delete non-existent (HTTP 404)
    del_404 = client.delete("/api/applications/999999")
    assert del_404.status_code == 404
