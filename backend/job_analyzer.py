import re
import json
import logging
from typing import Dict, Any, List, Optional
from backend.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

def analyze_job_posting(
    raw_text: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyzes a job posting text and categorizes requirements strictly into
    Required vs. Preferred qualifications.
    """
    metadata = metadata or {}
    company_name = metadata.get("company_name", "").strip()
    job_title = metadata.get("job_title", "").strip()
    company_email = metadata.get("company_email", "").strip()
    location = metadata.get("location", "").strip()

    if not raw_text.strip():
        return _empty_job_analysis(company_name, job_title, company_email, location)

    from backend.llm import is_llm_configured, generate_json_response

    if is_llm_configured():
        try:
            return _analyze_with_ai(raw_text, company_name, job_title, company_email, location)
        except Exception as e:
            logger.error(f"AI job analysis failed: {e}. Falling back to heuristic parsing.")
            return _analyze_heuristically(raw_text, company_name, job_title, company_email, location)
    else:
        logger.info("Using heuristic job parsing (no AI API key set).")
        return _analyze_heuristically(raw_text, company_name, job_title, company_email, location)

def _analyze_with_ai(
    raw_text: str,
    company_name: str,
    job_title: str,
    company_email: str,
    location: str
) -> Dict[str, Any]:
    from backend.llm import generate_json_response

    prompt = f"""You are an expert technical recruiter and job requirement parser.

Analyze the following job posting text. Your most important duty is to CLEARLY SEPARATE:
1. REQUIRED QUALIFICATIONS (Must-have, mandatory, basic requirements)
from
2. PREFERRED QUALIFICATIONS (Nice-to-have, bonus, plus, preferred, good-to-have)

Do NOT treat preferred requirements as mandatory unless the job explicitly says so.
If metadata (company name, job title, location, or recruiter email) was not provided by the user, extract or infer it from the text if clearly present.

Job Posting Text:
---
{raw_text}
---

Provided Metadata:
- Company Name: {company_name or 'Not provided'}
- Job Title: {job_title or 'Not provided'}
- Recruiter Email: {company_email or 'Not provided'}
- Location: {location or 'Not provided'}

Respond strictly with a JSON object matching this schema:
{{
  "company_name": "Company Name (use provided if set, otherwise extract from text)",
  "job_title": "Job Title (use provided if set, otherwise extract from text)",
  "company_email": "Recruiter / Application email if found in text or provided, else empty string",
  "location": "Location stated in job posting or provided, else empty string",
  "work_mode": "Remote | Hybrid | On-site | Unspecified",
  "summary": "2-3 sentence clear summary of the role and key mission",
  "required_qualifications": {{
    "degree": "Required education/degree or 'Not specified'",
    "experience": "Explicit minimum experience required (e.g., '3+ years of professional backend development') or 'Not specified'",
    "skills": ["List of explicitly mandatory technical skills"],
    "technologies": ["List of explicitly mandatory technologies / tools / frameworks"],
    "certifications": ["List of explicitly mandatory certifications"],
    "location_work_mode": "Mandatory location or residency constraints, or 'Open'"
  }},
  "preferred_qualifications": {{
    "skills": ["List of preferred / nice-to-have skills"],
    "technologies": ["List of preferred technologies / tools"],
    "experience": "Bonus or preferred domain experience if mentioned",
    "certifications": ["List of preferred / bonus certifications"],
    "other": ["Other bonus points, e.g. open source contributions, specific industry experience"]
  }}
}}
"""

    data = generate_json_response(prompt=prompt, temperature=0.0)
    if not data or not isinstance(data, dict):
        raise ValueError("AI returned empty or invalid response")

    # Ensure fields are sanitized
    if company_name: data["company_name"] = company_name
    if job_title: data["job_title"] = job_title
    if company_email: data["company_email"] = company_email
    if location: data["location"] = location

    return data

def _analyze_heuristically(
    raw_text: str,
    company_name: str,
    job_title: str,
    company_email: str,
    location: str
) -> Dict[str, Any]:
    """Fallback rule-based parser that partitions text into Required vs Preferred."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # Infer email if not provided
    if not company_email:
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", raw_text)
        if email_match:
            company_email = email_match.group(0)

    # Infer Title/Company from first lines if empty
    if not job_title and lines:
        job_title = lines[0][:80]
    if not company_name and len(lines) > 1 and len(lines[1]) < 50:
        company_name = lines[1]

    # Detect work mode
    work_mode = "Unspecified"
    if re.search(r"\bremote\b", raw_text, re.IGNORECASE):
        work_mode = "Remote"
    elif re.search(r"\bhybrid\b", raw_text, re.IGNORECASE):
        work_mode = "Hybrid"
    elif re.search(r"\bon-?site\b", raw_text, re.IGNORECASE):
        work_mode = "On-site"

    # Detect experience requirement (e.g. 3+ years, 5 years)
    exp_match = re.search(r"(\d+\+?\s*(?:to\s*\d+\+?)?\s*years?(?:\s+of)?(?:\s+experience)?)", raw_text, re.IGNORECASE)
    required_exp = exp_match.group(1) if exp_match else "Not specified"

    # Detect degree requirement
    degree = "Not specified"
    for d in ["Bachelor's degree", "Master's degree", "B.S.", "B.Tech", "M.S.", "Computer Science degree"]:
        if re.search(r"\b" + re.escape(d) + r"\b", raw_text, re.IGNORECASE):
            degree = d
            break

    # Split into sections: Required vs Preferred
    required_skills = []
    required_tech = []
    preferred_skills = []
    preferred_tech = []

    # Common tech keywords to look for
    tech_catalog = [
        "python", "fastapi", "django", "flask", "react", "typescript", "javascript",
        "node.js", "docker", "kubernetes", "aws", "gcp", "azure", "postgresql",
        "sql", "nosql", "mongodb", "redis", "graphql", "rest", "ci/cd", "git",
        "linux", "c++", "java", "golang", "rust", "terraform", "kafka"
    ]

    # Identify whether lines fall under preferred or required blocks
    current_section = "required"
    for line in lines:
        lower_line = line.lower()
        if any(h in lower_line for h in ["preferred", "nice to have", "bonus", "plus", "desired", "good to have"]):
            current_section = "preferred"
            continue
        elif any(h in lower_line for h in ["required", "basic qualification", "must have", "minimum qualification", "requirements"]):
            current_section = "required"
            continue

        # Check for tech catalog items in this line
        for tech in tech_catalog:
            if re.search(r"\b" + re.escape(tech) + r"\b", lower_line):
                cap_tech = tech.capitalize() if tech not in ["aws", "gcp", "ci/cd", "sql"] else tech.upper()
                if current_section == "preferred":
                    if cap_tech not in preferred_tech:
                        preferred_tech.append(cap_tech)
                else:
                    if cap_tech not in required_tech:
                        required_tech.append(cap_tech)

    return {
        "company_name": company_name or "Company Not Specified",
        "job_title": job_title or "Job Title Not Specified",
        "company_email": company_email,
        "location": location or "Not specified",
        "work_mode": work_mode,
        "summary": f"Position for {job_title or 'engineer'} at {company_name or 'target organization'}.",
        "required_qualifications": {
            "degree": degree,
            "experience": required_exp,
            "skills": required_skills or ["Problem Solving", "Software Engineering"],
            "technologies": required_tech or ["Python"],
            "certifications": [],
            "location_work_mode": work_mode
        },
        "preferred_qualifications": {
            "skills": preferred_skills,
            "technologies": preferred_tech,
            "experience": "Relevant industry experience preferred",
            "certifications": [],
            "other": []
        }
    }

def _empty_job_analysis(
    company_name: str,
    job_title: str,
    company_email: str,
    location: str
) -> Dict[str, Any]:
    return {
        "company_name": company_name,
        "job_title": job_title,
        "company_email": company_email,
        "location": location,
        "work_mode": "Unspecified",
        "summary": "",
        "required_qualifications": {
            "degree": "Not specified",
            "experience": "Not specified",
            "skills": [],
            "technologies": [],
            "certifications": [],
            "location_work_mode": "Unspecified"
        },
        "preferred_qualifications": {
            "skills": [],
            "technologies": [],
            "experience": "",
            "certifications": [],
            "other": []
        }
    }

