import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.main import app
from backend.database import init_db, save_profile, create_job

client = TestClient(app)

def setup_module():
    init_db()
    # Setup candidate profile
    save_profile({
        "full_name": "Jordan Lee",
        "email": "jordan.lee@example.com",
        "phone": "+1 (555) 345-6789",
        "degree": "B.S. in Computer Science",
        "graduation_year": "2023",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "REST APIs"],
        "experience": [
            {
                "title": "Backend Developer",
                "company": "NextGen Systems",
                "duration": "2023 - Present",
                "description": "Architected low-latency REST endpoints with FastAPI and optimized PostgreSQL database queries."
            }
        ],
        "projects": [
            {
                "name": "Cloud Microservice API",
                "tech": "Python, FastAPI, Docker",
                "description": "Implemented containerized microservices architecture with automated CI/CD."
            }
        ],
        "certifications": ["AWS Certified Cloud Practitioner"],
        "preferred_roles": ["Backend Engineer", "Software Engineer"],
        "preferred_locations": ["Remote", "San Francisco, CA"],
        "work_mode": "Remote",
        "experience_level": "Mid",
        "other_preferences": "Interested in distributed cloud systems."
    })

def test_match_evaluation_and_truthfulness():
    # 1. Create target job
    job_id = create_job(
        company_name="FinStream Tech",
        company_email="recruiting@finstream.io",
        job_title="Senior Python Backend Engineer",
        location="Remote",
        job_url="https://finstream.io/jobs/1",
        raw_description="Backend role requiring Python, FastAPI, and Kubernetes.",
        required_qualifications={
            "degree": "Bachelor's degree in Computer Science",
            "experience": "2+ years of professional backend experience",
            "skills": ["REST APIs"],
            "technologies": ["Python", "FastAPI", "Kubernetes"],
            "certifications": [],
            "location_work_mode": "Remote"
        },
        preferred_qualifications={
            "skills": ["Event-driven design"],
            "technologies": ["Apache Kafka", "Redis"],
            "experience": "Fintech background is a plus",
            "certifications": [],
            "other": []
        },
        summary="Building scalable fintech microservices."
    )

    # 2. Call Match Endpoint
    res = client.post("/api/match/evaluate", json={"job_id": job_id})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    match = data["match"]

    # Verify score is reasonable
    assert 40 <= match["match_score"] <= 95

    # Verify Education
    assert match["education"]["status"] == "PASS"

    # Verify Skills Match Accuracy
    skills = match["skills"]
    matched_req = [s.lower() for s in skills["matched_required"]]
    missing_req = [s.lower() for s in skills["missing_required"]]

    # Jordan Lee HAS Python and FastAPI and REST APIs
    assert "python" in matched_req
    assert "fastapi" in matched_req

    # Jordan Lee DOES NOT have Kubernetes in profile
    assert "kubernetes" in missing_req

    # Verify Explanation is transparent and honest
    assert "Overall match score" in match["explanation"]
    assert "Kubernetes" in match["explanation"] or "kubernetes" in match["explanation"]

def test_personalized_email_generation_and_accuracy():
    # Fetch job list to get the job
    jobs = client.get("/api/jobs").json()["jobs"]
    assert len(jobs) > 0
    job_id = jobs[0]["id"]

    # Generate personalized email
    res = client.post("/api/email/generate", json={"job_id": job_id})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    
    email = data["email"]
    assert "subject" in email
    assert "body" in email
    assert "Jordan Lee" in email["subject"] or "Jordan Lee" in email["body"]
    assert "FinStream Tech" in email["body"] or "Senior Python Backend Engineer" in email["subject"]
    
    # Critical zero-hallucination check: Jordan does NOT know Kubernetes, so the email must NOT falsely claim mastery of Kubernetes
    # It must focus on Python, FastAPI, or genuine projects
    assert "Python" in email["body"] or "FastAPI" in email["body"]

    # Verify application persistence
    app_id = data["application_id"]
    res_app = client.get(f"/api/jobs/{job_id}/application")
    assert res_app.status_code == 200
    saved_app = res_app.json()["application"]
    assert saved_app["id"] == app_id
    assert saved_app["status"] == "Draft"
    assert saved_app["email_subject"] == email["subject"]

    # Verify user can update the draft
    update_res = client.put(f"/api/applications/{app_id}/draft", json={
        "email_subject": "Updated Application: Senior Python Backend Engineer - Jordan Lee",
        "email_body": "Updated body content after user manual review.",
        "recipient_email": "recruiting@finstream.io"
    })
    assert update_res.status_code == 200
    updated_draft = update_res.json()["application"]
    assert updated_draft["email_subject"] == "Updated Application: Senior Python Backend Engineer - Jordan Lee"
    assert updated_draft["email_body"] == "Updated body content after user manual review."

