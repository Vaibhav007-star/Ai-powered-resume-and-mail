import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.job_fetcher import (
    strip_html_tags,
    fetch_from_jobicy,
    fetch_from_remotive,
    fetch_from_arbeitnow,
    fetch_from_internshala,
    fetch_open_jobs,
    is_eligible_for_india,
    parse_stipend_amount
)

def test_strip_html_tags():
    raw = "<p>We are hiring a <strong>Data Scientist</strong>!<br>Key skills: &amp; Python</p>"
    cleaned = strip_html_tags(raw)
    assert "Data Scientist" in cleaned
    assert "Key skills: & Python" in cleaned
    assert "<p>" not in cleaned
    assert "<strong>" not in cleaned

@patch("backend.services.job_fetcher._make_http_request")
def test_fetch_from_jobicy(mock_request):
    mock_request.return_value = {
        "jobs": [
            {
                "id": "101",
                "jobTitle": "Junior AI Engineer",
                "companyName": "DeepTech AI",
                "jobGeo": "Worldwide",
                "url": "https://example.com/job1",
                "jobDescription": "<p>Build ML pipelines with Python and PyTorch.</p>",
                "jobIndustry": ["AI", "Machine Learning"],
                "pubDate": "2026-09-24"
            }
        ]
    }
    jobs = fetch_from_jobicy("ai engineer", limit=5)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Junior AI Engineer"
    assert jobs[0]["company_name"] == "DeepTech AI"
    assert jobs[0]["source"] == "Jobicy"
    assert "Python and PyTorch" in jobs[0]["description"]
    assert "AI" in jobs[0]["tags"]

@patch("backend.services.job_fetcher._make_http_request")
def test_fetch_from_remotive(mock_request):
    mock_request.return_value = {
        "jobs": [
            {
                "id": 202,
                "title": "Data Science Intern",
                "company_name": "DataWorks Inc",
                "candidate_required_location": "Remote",
                "url": "https://remotive.com/job2",
                "description": "<p>Analyze data sets using Pandas, scikit-learn, and SQL.</p>",
                "tags": ["python", "data science"],
                "publication_date": "2026-09-23"
            }
        ]
    }
    jobs = fetch_from_remotive("data science", limit=5)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Data Science Intern"
    assert jobs[0]["company_name"] == "DataWorks Inc"
    assert jobs[0]["source"] == "Remotive"
    assert "Pandas" in jobs[0]["description"]

@patch("backend.services.job_fetcher._make_http_request")
def test_fetch_from_arbeitnow(mock_request):
    mock_request.return_value = {
        "data": [
            {
                "slug": "arbeitnow-303",
                "title": "Machine Learning Engineer",
                "company_name": "Visionary Labs",
                "location": "Berlin / Remote",
                "url": "https://arbeitnow.com/job3",
                "description": "<p>Deploy Computer Vision and NLP models.</p>",
                "tags": ["ML", "NLP"],
                "created_at": 1727100000
            }
        ]
    }
    jobs = fetch_from_arbeitnow("machine learning", limit=5)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Machine Learning Engineer"
    assert jobs[0]["company_name"] == "Visionary Labs"
    assert jobs[0]["source"] == "Arbeitnow"


def test_is_eligible_for_india():
    # Should reject foreign locations
    assert not is_eligible_for_india("Berlin, Germany", "delhi_ncr")
    assert not is_eligible_for_india("San Francisco, USA", "delhi_ncr")
    assert not is_eligible_for_india("London, UK", "delhi_ncr")
    # Should accept Delhi NCR and India
    assert is_eligible_for_india("Delhi (Delhi NCR)", "delhi_ncr")
    assert is_eligible_for_india("Noida (Delhi NCR)", "delhi_ncr")
    assert is_eligible_for_india("Gurugram (Delhi NCR)", "delhi_ncr")
    assert is_eligible_for_india("Remote (India)", "delhi_ncr")
    assert is_eligible_for_india("Worldwide", "delhi_ncr")

def test_parse_stipend_amount():
    assert parse_stipend_amount("INR 12,000 - 15,000 /month") == 15000
    assert parse_stipend_amount("INR 10,000 /month") == 10000
    assert parse_stipend_amount("20k/month") == 20000
    assert parse_stipend_amount("Unpaid") == 0

@patch("backend.services.job_fetcher.fetch_from_internshala")
@patch("backend.services.job_fetcher.fetch_from_remotive")
@patch("backend.services.job_fetcher.fetch_from_jobicy")
@patch("backend.services.job_fetcher.fetch_from_arbeitnow")
def test_fetch_open_jobs_aggregation_and_dedup(mock_arbeit, mock_jobicy, mock_remotive, mock_internshala):
    mock_internshala.return_value = []
    mock_remotive.return_value = [
        {
            "id": "rem_1",
            "title": "Data Scientist",
            "company_name": "Acme",
            "location": "Worldwide",
            "job_url": "https://remotive.com/1",
            "description": "Python, ML",
            "tags": ["Python"],
            "source": "Remotive",
            "published_at": ""
        }
    ]
    mock_jobicy.return_value = [
        # Duplicate job should be deduplicated
        {
            "id": "job_1",
            "title": "Data Scientist",
            "company_name": "Acme",
            "location": "Worldwide",
            "job_url": "https://jobicy.com/1",
            "description": "Python, ML",
            "tags": ["Python"],
            "source": "Jobicy",
            "published_at": ""
        },
        {
            "id": "job_2",
            "title": "NLP Researcher",
            "company_name": "Beta AI",
            "location": "Remote",
            "job_url": "https://jobicy.com/2",
            "description": "Transformers, NLP",
            "tags": ["NLP"],
            "source": "Jobicy",
            "published_at": ""
        }
    ]
    mock_arbeit.return_value = []

    results = fetch_open_jobs(query="data scientist", location="delhi_ncr", limit=10)
    assert len(results) == 2  # Deduplicated from 3
    companies = [r["company_name"] for r in results]
    assert "Acme" in companies
    assert "Beta AI" in companies

@patch("backend.main.fetch_open_jobs")
def test_api_jobs_search_endpoint(mock_fetch):
    mock_fetch.return_value = [
        {
            "id": "test_1",
            "title": "AI Intern",
            "company_name": "Cognitive Inc",
            "location": "Remote",
            "job_url": "https://example.com/ai",
            "description": "Develop LLM features",
            "tags": ["Python", "AI"],
            "source": "Jobicy",
            "published_at": "2026-09-24"
        }
    ]
    client = TestClient(app)
    response = client.get("/api/jobs/search?query=AI+Intern&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["count"] == 1
    assert data["jobs"][0]["title"] == "AI Intern"

def test_api_jobs_import_and_analyze_endpoint():
    client = TestClient(app)
    payload = {
        "job_title": "Data Science Intern",
        "company_name": "AutomatedTestCorp",
        "company_email": "jobs@autotestcorp.com",
        "location": "Remote",
        "job_url": "https://example.com/autotest",
        "job_description": "We require Python, scikit-learn, and SQL. Preferred qualifications include Docker and AWS."
    }
    response = client.post("/api/jobs/import-and-analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["job"]["company_name"] == "AutomatedTestCorp"
    assert data["job"]["job_title"] == "Data Science Intern"
    assert "required_qualifications" in data["job"]
