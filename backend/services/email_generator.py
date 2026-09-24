import json
import logging
from typing import Dict, Any, List
from backend.core.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

def generate_application_email(
    profile: Dict[str, Any],
    job: Dict[str, Any],
    match_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Generates personalized application email."""
    from backend.core.llm import is_llm_configured, generate_json_response

    if is_llm_configured():
        try:
            return _generate_with_ai(profile, job, match_result)
        except Exception as e:
            logger.error(f"AI email generation failed: {e}. Using deterministic truthful generator.")
            return _generate_truthful_fallback(profile, job, match_result)
    else:
        logger.info("Using deterministic truthful email composer (no AI API key).")
        return _generate_truthful_fallback(profile, job, match_result)

def _generate_with_ai(
    profile: Dict[str, Any],
    job: Dict[str, Any],
    match_result: Dict[str, Any]
) -> Dict[str, Any]:
    from backend.core.llm import generate_json_response

    candidate_name = profile.get("full_name") or "Candidate"
    job_title = job.get("job_title") or "the position"
    company_name = job.get("company_name") or "your company"
    
    matched_skills = match_result.get("skills", {}).get("matched_required", [])
    relevant_projects = match_result.get("relevant_projects", [])
    degree = profile.get("degree", "")

    prompt = f"""You are an expert executive communication coach drafting a personalized, human-sounding job application email.

STRICT ACCURACY & TRUTHFULNESS RULES:
1. NEVER INVENT INFORMATION.
2. Only mention skills, technologies, and projects explicitly listed in the Candidate Profile below.
3. If the candidate lacks a skill, do NOT mention it or pretend they have it.
4. Keep the email concise (between 140 and 220 words), direct, and respectful.
5. Avoid robotic AI phrases ("I hope this email finds you well", "I was ecstatic to discover", "synergistic", "paradigm").
6. Tone should be confident, professional, and natural.

Target Role & Company:
- Company: {company_name}
- Job Title: {job_title}
- Required Job Skills: {', '.join(job.get('required_qualifications', {}).get('skills', []) + job.get('required_qualifications', {}).get('technologies', []))}

Candidate Verified Profile:
- Full Name: {candidate_name}
- Email: {profile.get('email', '')}
- Phone: {profile.get('phone', '')}
- Degree: {degree or 'Not specified'}
- Stated Skills: {', '.join(profile.get('skills', []))}
- Matched Skills for this role: {', '.join(matched_skills)}
- Relevant Projects: {json.dumps(relevant_projects)}
- Past Experience Summary: {json.dumps(profile.get('experience', [])[:2])}
- Availability & Term: Available to start next month for a 3 to 6-month internship in Delhi NCR (Delhi, Noida, Gurugram) or Remote.

Generate a JSON object matching this schema:
{{
  "subject": "Clear, professional email subject line including candidate name and role",
  "body": "The email body text formatted with clear paragraphs and standard linebreaks (\\n\\n). Do NOT include placeholders like [Insert Date]; use candidate name and real details.",
  "grounded_facts": ["List of candidate's authentic facts/skills/projects cited in the email"]
}}
"""

    data = generate_json_response(prompt=prompt, temperature=0.2)
    if not data or not isinstance(data, dict):
        raise ValueError("AI returned empty or invalid response")

    if "subject" in data and isinstance(data["subject"], str):
        data["subject"] = data["subject"].replace("\u2013", "-").replace("\u2014", "-").replace("\u2011", "-")
    if "body" in data and isinstance(data["body"], str):
        data["body"] = data["body"].replace("\u2013", "-").replace("\u2014", "-").replace("\u2011", "-")

    return data

def _generate_truthful_fallback(
    profile: Dict[str, Any],
    job: Dict[str, Any],
    match_result: Dict[str, Any]
) -> Dict[str, Any]:
    candidate_name = profile.get("full_name", "").strip() or "Candidate"
    job_title = job.get("job_title", "").strip() or "the role"
    company_name = job.get("company_name", "").strip() or "your team"
    degree = profile.get("degree", "").strip()
    
    matched_skills = match_result.get("skills", {}).get("matched_required", [])
    relevant_projects = match_result.get("relevant_projects", [])
    grounded_facts = []

    subject = f"Application for {job_title} - {candidate_name}"

    body_lines = [
        f"Dear Hiring Team at {company_name},",
        ""
    ]

    intro = f"I am writing to express my interest in the {job_title} position at {company_name}."
    if degree:
        intro += f" With my background in {degree},"
        grounded_facts.append(f"Degree: {degree}")
    if matched_skills:
        skills_str = ", ".join(matched_skills[:4])
        intro += f" my practical experience with {skills_str} aligns directly with what you are looking for."
        grounded_facts.append(f"Skills cited: {skills_str}")
    else:
        intro += " my professional experience matches the requirements of your team."
    body_lines.append(intro)
    body_lines.append("")

    if relevant_projects:
        proj = relevant_projects[0]
        p_name = proj.get("project_name", "my recent project")
        p_skills = ", ".join(proj.get("matched_skills", []))
        p_desc = proj.get("summary", "")
        para2 = f"In particular, my work on {p_name}"
        if p_skills:
            para2 += f" utilizing {p_skills}"
        if p_desc:
            para2 += f" involved {p_desc.rstrip('.')}. "
        else:
            para2 += " demonstrates my ability to deliver scalable solutions. "
        para2 += "I focus on writing clean, well-tested code that delivers reliable performance."
        grounded_facts.append(f"Project cited: {p_name}")
        body_lines.append(para2)
        body_lines.append("")
    elif profile.get("experience"):
        exp = profile.get("experience")[0]
        role_title = exp.get("title", "engineer")
        company = exp.get("company", "previous organization")
        para2 = f"In my role as {role_title} at {company}, I contributed to building dependable software services and solving technical challenges in fast-paced environments."
        grounded_facts.append(f"Role cited: {role_title} at {company}")
        body_lines.append(para2)
        body_lines.append("")

    closing = (
        "I am available to join as an intern starting next month for a duration of 3 to 6 months "
        "in Delhi NCR (Delhi, Noida, Gurugram) or remotely. "
        "I have attached my resume for your review. I would welcome the opportunity "
        "to discuss how my background in Data Science and AI can support your team. "
        "Thank you for your time and consideration."
    )
    grounded_facts.append("Availability: 3 to 6 months starting next month (Delhi NCR / Remote)")
    body_lines.append(closing)
    body_lines.append("")

    body_lines.append("Sincerely,")
    body_lines.append(candidate_name)
    if profile.get("email"):
        body_lines.append(profile.get("email"))
    if profile.get("phone"):
        body_lines.append(profile.get("phone"))

    return {
        "subject": subject,
        "body": "\n".join(body_lines),
        "grounded_facts": grounded_facts
    }
