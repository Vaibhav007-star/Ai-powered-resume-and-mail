import re
from typing import Dict, Any, List, Optional
from backend.core.database import get_connection

NORM_SUFFIX_REGEX = re.compile(r"\b(inc|llc|corp|corporation|ltd|limited|technologies|company|co)\b[.]?", re.IGNORECASE)
NORM_NON_ALPHANUM_REGEX = re.compile(r"[^a-z0-9]")

def normalize_text(text: str) -> str:
    """Normalize text for fuzzy duplicate checking."""
    if not text:
        return ""
    t = text.lower().strip()
    t = NORM_SUFFIX_REGEX.sub("", t)
    t = NORM_NON_ALPHANUM_REGEX.sub("", t)
    return t

def check_duplicate_application(
    company_name: str,
    job_title: str,
    recipient_email: str,
    exclude_app_id: Optional[int] = None,
    user_id: int = 1
) -> Dict[str, Any]:
    """Checks if an application to the same company, role, or email has already been sent."""
    norm_company = normalize_text(company_name)
    norm_title = normalize_text(job_title)
    clean_email = recipient_email.strip().lower()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, job_id, company_name, job_title, recipient_email, status, created_at, updated_at
            FROM applications
            WHERE status = 'Sent' AND (user_id = ? OR user_id = 1)
            ORDER BY id DESC
        """, (user_id,))
        rows = cursor.fetchall()

    duplicates = []
    for r in rows:
        if exclude_app_id and r["id"] == exclude_app_id:
            continue
        prev_company = normalize_text(r["company_name"])
        prev_title = normalize_text(r["job_title"])
        prev_email = (r["recipient_email"] or "").strip().lower()

        if clean_email and clean_email == prev_email:
            duplicates.append({
                "id": r["id"],
                "reason": f"An application was already sent to '{r['recipient_email']}' on {r['updated_at'][:10]}.",
                "company_name": r["company_name"],
                "job_title": r["job_title"],
                "sent_date": r["updated_at"]
            })
            continue

        if norm_company and prev_company and (norm_company in prev_company or prev_company in norm_company):
            if not norm_title or not prev_title or (norm_title in prev_title or prev_title in norm_title):
                duplicates.append({
                    "id": r["id"],
                    "reason": f"An application was already sent to {r['company_name']} for '{r['job_title']}' on {r['updated_at'][:10]}.",
                    "company_name": r["company_name"],
                    "job_title": r["job_title"],
                    "sent_date": r["updated_at"]
                })

    is_duplicate = len(duplicates) > 0
    warning_message = ""
    if is_duplicate:
        warning_message = f"Possible duplicate application detected. {duplicates[0]['reason']}"

    return {
        "is_duplicate": is_duplicate,
        "warning_message": warning_message,
        "duplicates": duplicates
    }
