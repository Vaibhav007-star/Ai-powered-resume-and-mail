import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.main import app
from backend.core.database import init_db

client = TestClient(app)

def setup_module():
    init_db()

def test_analyze_job_and_partition():
    job_posting_text = """
Software Engineer - Backend
Acme Cloud Systems
Location: San Francisco, CA (Hybrid)
Contact: jobs@acmecloud.com

About the Role:
We are looking for a Backend Engineer to build robust distributed microservices.

Requirements:
- Bachelor's degree in Computer Science or related field
- 3+ years of experience with Python and FastAPI
- Strong understanding of PostgreSQL and relational databases
- Experience building REST APIs
- Familiarity with Docker and Linux environments

Preferred Qualifications:
- Experience with Kubernetes and AWS
- Familiarity with Redis caching and Kafka
- Knowledge of GraphQL
- Prior experience in SaaS startups is a plus
"""

    payload = {
        "job_description": job_posting_text,
        "company_name": "Acme Cloud Systems",
        "job_title": "Software Engineer - Backend",
        "company_email": "jobs@acmecloud.com",
        "location": "San Francisco, CA",
        "job_url": "https://acmecloud.com/careers/backend"
    }

    res = client.post("/api/jobs/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    job = data["job"]
    assert job["company_name"] == "Acme Cloud Systems"
    assert job["job_title"] == "Software Engineer - Backend"
    assert job["company_email"] == "jobs@acmecloud.com"
    
    # Verify strict separation of Required vs Preferred
    req = job["required_qualifications"]
    pref = job["preferred_qualifications"]
    
    assert "degree" in req
    assert "experience" in req
    assert "skills" in req or "technologies" in req
    assert "technologies" in pref

    # Required should not be empty
    assert len(req.get("technologies", [])) > 0 or len(req.get("skills", [])) > 0

    job_id = job["id"]

    # Verify listing
    res_list = client.get("/api/jobs")
    assert res_list.status_code == 200
    jobs = res_list.json()["jobs"]
    assert any(j["id"] == job_id for j in jobs)

    # Verify single fetch
    res_single = client.get(f"/api/jobs/{job_id}")
    assert res_single.status_code == 200
    assert res_single.json()["job"]["id"] == job_id

    # Verify update
    update_payload = {
        "company_name": "Acme Cloud Systems Inc.",
        "company_email": "careers@acmecloud.com",
        "job_title": "Senior Backend Engineer",
        "location": "Remote",
        "job_url": "https://acmecloud.com/careers/backend",
        "required_qualifications": req,
        "preferred_qualifications": pref,
        "summary": "Updated role summary."
    }
    res_update = client.put(f"/api/jobs/{job_id}", json=update_payload)
    assert res_update.status_code == 200
    updated_job = res_update.json()["job"]
    assert updated_job["company_name"] == "Acme Cloud Systems Inc."
    assert updated_job["job_title"] == "Senior Backend Engineer"

    # Verify delete
    res_delete = client.delete(f"/api/jobs/{job_id}")
    assert res_delete.status_code == 200
    
    # Confirm deletion
    res_verify = client.get(f"/api/jobs/{job_id}")
    assert res_verify.status_code == 404

def test_analyze_empty_job_error():
    res = client.post("/api/jobs/analyze", json={"job_description": "   "})
    assert res.status_code == 400
