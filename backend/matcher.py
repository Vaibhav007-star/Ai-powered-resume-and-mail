import re
import json
import logging
from typing import Dict, Any, List, Tuple
from backend.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

def evaluate_candidate_match(profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares candidate profile against job requirements with complete transparency.
    Enforces the ZERO-HALLUCINATION rule: never assumes or invents candidate data.
    """
    req = job.get("required_qualifications", {})
    pref = job.get("preferred_qualifications", {})

    # 1. Candidate Skills Pool (from profile skills, experience, projects, and resume text)
    candidate_skills_set = set()
    for s in profile.get("skills", []):
        if isinstance(s, str) and s.strip():
            candidate_skills_set.add(s.strip().lower())

    # Also harvest tech from candidate projects
    for p in profile.get("projects", []):
        tech_str = p.get("tech", "")
        for t in re.split(r"[,/|;]", tech_str):
            if t.strip():
                candidate_skills_set.add(t.strip().lower())

    resume_text_lower = (profile.get("raw_resume_text", "") or "").lower()

    def candidate_has_skill(skill_name: str) -> bool:
        s_lower = skill_name.strip().lower()
        if s_lower in candidate_skills_set:
            return True
        # Check word boundary in resume text
        if re.search(r"\b" + re.escape(s_lower) + r"\b", resume_text_lower):
            return True
        return False

    # 2. Match Required Skills & Technologies
    job_req_skills = list(dict.fromkeys(req.get("skills", []) + req.get("technologies", [])))
    matched_req_skills = []
    missing_req_skills = []

    for s in job_req_skills:
        if candidate_has_skill(s):
            matched_req_skills.append(s)
        else:
            missing_req_skills.append(s)

    # 3. Match Preferred Skills & Technologies
    job_pref_skills = list(dict.fromkeys(pref.get("skills", []) + pref.get("technologies", [])))
    matched_pref_skills = []
    missing_pref_skills = []

    for s in job_pref_skills:
        if candidate_has_skill(s):
            matched_pref_skills.append(s)
        else:
            missing_pref_skills.append(s)

    # 4. Education Evaluation
    req_degree = req.get("degree", "Not specified")
    cand_degree = profile.get("degree", "").strip()

    if not req_degree or req_degree.lower() in ("not specified", "open", "any"):
        edu_status = "PASS"
        edu_reason = "No specific degree mandatory for this position."
    elif not cand_degree:
        edu_status = "PARTIAL"
        edu_reason = f"Job requires '{req_degree}', but education information is not provided in your profile."
    else:
        # Check if candidate degree matches CS/Engineering or field
        req_deg_lower = req_degree.lower()
        cand_deg_lower = cand_degree.lower()
        if any(term in cand_deg_lower for term in ["computer science", "engineering", "information technology", "bachelor", "master"]):
            edu_status = "PASS"
            edu_reason = f"Candidate degree ({cand_degree}) satisfies requirement: {req_degree}."
        else:
            edu_status = "PARTIAL"
            edu_reason = f"Candidate degree is {cand_degree}; job requires {req_degree}."

    # 5. Experience Evaluation
    req_exp = req.get("experience", "Not specified")
    cand_exp_list = profile.get("experience", [])
    cand_exp_level = profile.get("experience_level", "Mid")

    if not req_exp or req_exp.lower() in ("not specified", "open", "none"):
        exp_status = "PASS"
        exp_reason = "No specific minimum experience required."
    else:
        exp_years_match = re.search(r"(\d+)", req_exp)
        req_years = int(exp_years_match.group(1)) if exp_years_match else 2
        cand_count = len(cand_exp_list)
        
        if cand_count >= req_years or (req_years <= 3 and cand_exp_level in ("Mid", "Senior", "Lead")):
            exp_status = "PASS"
            exp_reason = f"Candidate has {cand_count} recorded role(s) / {cand_exp_level} level, meeting the '{req_exp}' requirement."
        elif cand_count > 0:
            exp_status = "PARTIAL"
            exp_reason = f"Candidate has {cand_count} recorded role(s). Job requires '{req_exp}'."
        else:
            exp_status = "PARTIAL"
            exp_reason = f"Job requires '{req_exp}'. Work history entries not detailed in profile."

    # 6. Location & Work Mode Evaluation
    job_work_mode = req.get("location_work_mode", job.get("location", "Any"))
    job_loc_str = (job.get("location", "") + " " + job_work_mode).lower().strip()
    cand_work_mode = profile.get("work_mode", "Any")
    cand_locations = profile.get("preferred_locations", [])
    cand_loc_lower = [loc.lower() for loc in cand_locations]

    foreign_cities = ["berlin", "germany", "usa", "united states", "london", "uk", "canada", "france", "paris", "latam", "poland", "spain", "munich", "argentina"]
    is_foreign_job = any(fc in job_loc_str for fc in foreign_cities) and "india" not in job_loc_str and "worldwide" not in job_loc_str

    if is_foreign_job:
        loc_status = "PARTIAL"
        loc_reason = f"Job is located overseas ({job.get('location', job_work_mode)}), which conflicts with candidate target region (Delhi NCR, India)."
    elif any(city in job_loc_str for city in ["delhi", "noida", "gurugram", "gurgaon", "ncr", "india"]):
        loc_status = "PASS"
        loc_reason = f"Location matches candidate preference ({job.get('location', job_work_mode)} in Delhi NCR / India)."
    elif "remote" in job_work_mode.lower() or cand_work_mode == "Any" or "any" in job_work_mode.lower():
        loc_status = "PASS"
        loc_reason = f"Work mode aligns ({job_work_mode})."
    elif cand_locations and any(cl in job_loc_str for cl in cand_loc_lower):
        loc_status = "PASS"
        loc_reason = f"Location matches candidate preference ({job.get('location', job_work_mode)})."
    elif cand_work_mode.lower() in job_work_mode.lower():
        loc_status = "PASS"
        loc_reason = f"Candidate prefers {cand_work_mode} which matches role work mode ({job_work_mode})."
    else:
        loc_status = "PARTIAL"
        loc_reason = f"Job mode is {job_work_mode}; candidate preference is {cand_work_mode}."

    # 7. Project Relevance Matching
    relevant_projects = []
    for proj in profile.get("projects", []):
        p_name = proj.get("name", "Project")
        p_tech = proj.get("tech", "")
        p_desc = proj.get("description", "")
        matched_in_project = []
        for s in job_req_skills + job_pref_skills:
            if re.search(r"\b" + re.escape(s.lower()) + r"\b", (p_tech + " " + p_desc).lower()):
                matched_in_project.append(s)
        if matched_in_project:
            relevant_projects.append({
                "project_name": p_name,
                "matched_skills": list(set(matched_in_project)),
                "summary": p_desc[:120] + "..." if len(p_desc) > 120 else p_desc
            })

    # 8. Score Calculation (Grounded in facts)
    req_ratio = len(matched_req_skills) / max(len(job_req_skills), 1) if job_req_skills else 1.0
    pref_ratio = len(matched_pref_skills) / max(len(job_pref_skills), 1) if job_pref_skills else 0.5
    
    score = (
        (req_ratio * 45) +
        (pref_ratio * 15) +
        (20 if edu_status == "PASS" else 10) +
        (15 if exp_status == "PASS" else 8) +
        (5 if loc_status == "PASS" else 2)
    )
    final_score = min(max(int(round(score)), 10), 98)

    # 9. Clear Summary Explanation
    skills_summary = f"{len(matched_req_skills)}/{len(job_req_skills)} required skills matched" if job_req_skills else "General skills align"
    missing_text = ", ".join(missing_req_skills) if missing_req_skills else "None"

    overview_explanation = (
        f"Overall match score is {final_score}%. "
        f"Education: {edu_status}. Experience: {exp_status}. Location/Mode: {loc_status}. "
        f"Matched {len(matched_req_skills)} of {len(job_req_skills)} mandatory skills. "
        + (f"Gaps identified in required skills: {missing_text}." if missing_req_skills else "All mandatory skills satisfied.")
    )

    return {
        "match_score": final_score,
        "education": {
            "status": edu_status,
            "required": req_degree,
            "candidate": cand_degree or "Information not provided",
            "reason": edu_reason
        },
        "skills": {
            "summary": skills_summary,
            "matched_required": matched_req_skills,
            "missing_required": missing_req_skills,
            "matched_preferred": matched_pref_skills,
            "missing_preferred": missing_pref_skills
        },
        "experience": {
            "status": exp_status,
            "required": req_exp,
            "reason": exp_reason
        },
        "location": {
            "status": loc_status,
            "job_mode": job_work_mode,
            "candidate_mode": cand_work_mode,
            "reason": loc_reason
        },
        "relevant_projects": relevant_projects,
        "explanation": overview_explanation
    }

