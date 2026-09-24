import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.main import app
from backend.core.database import init_db

client = TestClient(app)

def setup_module():
    init_db()

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "phase" in data

def test_get_and_update_profile():
    # 1. Fetch initial profile
    res1 = client.get("/api/profile")
    assert res1.status_code == 200
    assert "profile" in res1.json()

    # 2. Update profile
    payload = {
        "full_name": "Test Candidate",
        "email": "candidate@example.com",
        "phone": "+1-555-0199",
        "degree": "B.S. in Computer Science",
        "graduation_year": "2023",
        "skills": ["Python", "FastAPI", "SQLite", "Docker"],
        "experience": [
            {
                "title": "Software Engineer Intern",
                "company": "Tech Innovations",
                "duration": "2022 - 2023",
                "description": "Built automated REST endpoints and improved database query speeds."
            }
        ],
        "projects": [
            {
                "name": "Personal AI Assistant",
                "tech": "Python, SQLite",
                "description": "Created local desktop application helper."
            }
        ],
        "certifications": ["AWS Cloud Practitioner"],
        "preferred_roles": ["Software Engineer", "Backend Developer"],
        "preferred_locations": ["Remote", "New York, NY"],
        "work_mode": "Remote",
        "experience_level": "Entry",
        "other_preferences": "Seeking backend or full-stack opportunities."
    }

    res2 = client.post("/api/profile", json=payload)
    assert res2.status_code == 200
    updated_data = res2.json()
    assert updated_data["status"] == "success"
    assert updated_data["profile"]["full_name"] == "Test Candidate"
    assert "Python" in updated_data["profile"]["skills"]

    # 3. Verify persistence
    res3 = client.get("/api/profile")
    assert res3.status_code == 200
    persisted = res3.json()["profile"]
    assert persisted["full_name"] == "Test Candidate"
    assert persisted["email"] == "candidate@example.com"
    assert len(persisted["experience"]) == 1
    assert persisted["experience"][0]["company"] == "Tech Innovations"

def test_resume_upload_and_extraction(tmp_path):
    # Create sample resume text file
    sample_content = """John Doe
john.doe@example.com
(555) 987-6543
Bachelor of Technology in Information Technology

SKILLS
Python, Django, FastAPI, PostgreSQL, Git, Linux

EXPERIENCE
Junior Developer - CloudTech (2023 - Present)
- Developed microservices in Python.
- Maintained PostgreSQL database and migrations.

PROJECTS
Task Manager App
Technologies: FastAPI, Vue.js, SQLite
Built a full-stack task manager with user authentication.
"""
    resume_file = tmp_path / "john_doe_resume.txt"
    resume_file.write_text(sample_content, encoding="utf-8")

    with open(resume_file, "rb") as f:
        res = client.post(
            "/api/resume/upload",
            files={"file": ("john_doe_resume.txt", f, "text/plain")},
            data={"label": "Full-Stack Resume", "auto_extract": "true"}
        )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["resume"]["filename"] == "john_doe_resume.txt"
    assert data["resume"]["char_count"] > 50

    # Verify structured profile extraction
    extracted = data.get("extracted_profile")
    assert extracted is not None
    # Email should be extracted
    assert extracted.get("email") == "john.doe@example.com"

    # Verify resume listing
    list_res = client.get("/api/resumes")
    assert list_res.status_code == 200
    resumes = list_res.json()["resumes"]
    assert len(resumes) >= 1
    assert any(r["filename"] == "john_doe_resume.txt" for r in resumes)

if __name__ == "__main__":
    pytest.main(["-v", __file__])
