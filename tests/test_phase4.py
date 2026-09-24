import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.main import app
from backend.database import init_db, save_profile, create_job, save_application, get_application
from backend.email_service import send_application_email, is_valid_email
from backend.duplicate_checker import check_duplicate_application

client = TestClient(app)

def setup_module():
    init_db()

def test_email_validation_and_dry_run(tmp_path):
    # Test email validator
    assert is_valid_email("recruiting@acme.com") is True
    assert is_valid_email("invalid-email") is False
    assert is_valid_email("") is False

    # Test safe Dry-Run email dispatch
    dummy_resume = tmp_path / "resume.pdf"
    dummy_resume.write_text("Dummy resume binary data")

    result = send_application_email(
        recipient_email="recruiting@acme.com",
        subject="Application for Senior Engineer",
        body="Dear Hiring Team,\n\nPlease review my attached resume.",
        attachment_path=str(dummy_resume),
        override_dry_run=True
    )

    assert result["success"] is True
    assert result["dry_run"] is True
    assert "preview_file" in result
    assert Path(result["preview_file"]).exists()

def test_human_approval_workflow_and_duplicate_protection():
    import uuid
    uid = uuid.uuid4().hex[:6]
    company = f"Apex Global {uid}"
    email = f"talent_{uid}@apexlogistics.com"

    # 1. Create a Job
    job_id = create_job(
        company_name=company,
        company_email=email,
        job_title="Lead Python Developer",
        location="Remote",
        job_url=f"https://apexlogistics.com/jobs/{uid}",
        raw_description="Lead backend developer role.",
        required_qualifications={"skills": ["Python", "FastAPI"], "degree": "B.S."},
        preferred_qualifications={"skills": ["Docker"]}
    )

    # 2. Create Application Draft
    app_id = save_application(
        job_id=job_id,
        company_name=company,
        job_title="Lead Python Developer",
        recipient_email=email,
        match_score=88,
        match_summary={"score": 88},
        email_subject="Application for Lead Python Developer - Alex",
        email_body="Dear Apex Team,\n\nI am applying for the role.",
        status="Draft"
    )

    # 3. Test Review Packet Endpoint
    packet_res = client.get(f"/api/applications/{app_id}/review-packet")
    assert packet_res.status_code == 200
    packet = packet_res.json()
    assert packet["status"] == "success"
    assert packet["application"]["id"] == app_id
    assert packet["duplicate_check"]["is_duplicate"] is False

    # 4. Attempt to send WITHOUT human approval -> Must Fail (HTTP 400)
    unapproved_res = client.post(f"/api/applications/{app_id}/send", json={
        "approved": False,
        "recipient_email": email,
        "email_subject": "Application",
        "email_body": "Hello",
        "attach_resume": False
    })
    assert unapproved_res.status_code == 400
    assert "approval is required" in unapproved_res.json()["detail"]

    # 5. Send WITH explicit human approval (approved = True)
    send_payload = {
        "approved": True,
        "recipient_email": email,
        "email_subject": "Application for Lead Python Developer - Alex",
        "email_body": "Dear Apex Team,\n\nI am applying for the role.",
        "attach_resume": False,
        "override_duplicate": False,
        "notes": "Reviewed and approved by user."
    }
    approved_res = client.post(f"/api/applications/{app_id}/send", json=send_payload)
    assert approved_res.status_code == 200
    send_data = approved_res.json()
    assert send_data["status"] == "success"
    assert send_data["application"]["status"] == "Sent"

    # 6. Duplicate Protection Test:
    # Attempting to send an application to the same company & email must trigger Duplicate Warning (HTTP 409)
    second_app_id = save_application(
        job_id=job_id,
        company_name=company,
        job_title="Lead Python Developer",
        recipient_email=email,
        match_score=88,
        match_summary={"score": 88},
        email_subject="Second Application Attempt",
        email_body="Attempting duplicate send",
        status="Draft"
    )

    dup_res = client.post(f"/api/applications/{second_app_id}/send", json={
        "approved": True,
        "recipient_email": email,
        "email_subject": "Second Application Attempt",
        "email_body": "Attempting duplicate send",
        "attach_resume": False,
        "override_duplicate": False
    })
    assert dup_res.status_code == 409
    dup_data = dup_res.json()
    assert dup_data["status"] == "duplicate_warning"
    assert "Possible duplicate application detected" in dup_data["message"]

    # 7. Override Duplicate Protection:
    # If the user explicitly sets override_duplicate = True, sending succeeds
    override_res = client.post(f"/api/applications/{second_app_id}/send", json={
        "approved": True,
        "recipient_email": email,
        "email_subject": "Second Application Attempt",
        "email_body": "Attempting duplicate send",
        "attach_resume": False,
        "override_duplicate": True
    })
    assert override_res.status_code == 200
    assert override_res.json()["application"]["status"] == "Sent"
