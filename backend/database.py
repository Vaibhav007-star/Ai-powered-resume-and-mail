import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from backend import config

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables for User Profile and Resumes."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # User Profile table (single record id=1 for the personal assistant)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY,
                full_name TEXT DEFAULT '',
                email TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                degree TEXT DEFAULT '',
                graduation_year TEXT DEFAULT '',
                skills TEXT DEFAULT '[]',
                experience TEXT DEFAULT '[]',
                projects TEXT DEFAULT '[]',
                certifications TEXT DEFAULT '[]',
                preferred_roles TEXT DEFAULT '[]',
                preferred_locations TEXT DEFAULT '[]',
                work_mode TEXT DEFAULT 'Any',
                experience_level TEXT DEFAULT 'Mid',
                other_preferences TEXT DEFAULT '',
                raw_resume_text TEXT DEFAULT '',
                active_resume_id INTEGER DEFAULT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Uploaded Resumes table (supports multiple versions: SWE, Data, AI/ML, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                label TEXT DEFAULT 'General Resume',
                raw_text TEXT DEFAULT '',
                uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Jobs table for Phase 2: Job Analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT DEFAULT '',
                company_email TEXT DEFAULT '',
                job_title TEXT DEFAULT '',
                location TEXT DEFAULT '',
                job_url TEXT DEFAULT '',
                raw_description TEXT DEFAULT '',
                required_qualifications TEXT DEFAULT '{}',
                preferred_qualifications TEXT DEFAULT '{}',
                summary TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Applications table for Phase 3 (Matching & Drafts), Phase 4 (Approval), and Phase 5 (Tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                company_name TEXT DEFAULT '',
                job_title TEXT DEFAULT '',
                recipient_email TEXT DEFAULT '',
                match_score INTEGER DEFAULT 0,
                match_summary TEXT DEFAULT '{}',
                email_subject TEXT DEFAULT '',
                email_body TEXT DEFAULT '',
                attached_resume_id INTEGER DEFAULT NULL,
                status TEXT DEFAULT 'Draft',
                notes TEXT DEFAULT '',
                follow_up_date TEXT DEFAULT '',
                response_status TEXT DEFAULT 'Pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
        """)

        # Safe migration for existing SQLite databases
        cursor.execute("PRAGMA table_info(applications)")
        existing_cols = [row["name"] for row in cursor.fetchall()]
        if "follow_up_date" not in existing_cols:
            cursor.execute("ALTER TABLE applications ADD COLUMN follow_up_date TEXT DEFAULT ''")
        if "response_status" not in existing_cols:
            cursor.execute("ALTER TABLE applications ADD COLUMN response_status TEXT DEFAULT 'Pending'")
        
        # Ensure default profile row exists (tailored for Data Science & AI student)
        cursor.execute("SELECT id FROM profiles WHERE id = 1")
        if not cursor.fetchone():
            default_skills = json.dumps(["Python", "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Scikit-Learn", "Pandas", "NumPy", "Generative AI", "LLMs", "SQL", "Git"])
            default_roles = json.dumps(["Data Science Intern", "AI Engineer Intern", "Machine Learning Intern", "Data Analyst Intern"])
            default_locations = json.dumps(["Delhi", "Noida", "Gurugram", "Delhi NCR", "Remote (India)"])
            other_pref = "College Requirement: 3 to 6 months internship starting in 1 month (minimum 3 months, up to 6 months). Minimum stipend requirement: > ₹10,000/month. Field: Data Science & AI."
            cursor.execute("""
                INSERT INTO profiles (id, full_name, email, phone, degree, graduation_year, skills, experience, projects, certifications, preferred_roles, preferred_locations, work_mode, experience_level, other_preferences, raw_resume_text, updated_at)
                VALUES (1, 'Vaibhav Lohchab', 'vaibhavlohchab1@gmail.com', '', 'B.Sc. Data Science & Artificial Intelligence (2024 - 2027)', '2027', ?, '[]', '[]', '[]', ?, ?, 'Hybrid / On-site / Remote', 'Entry', ?, '', ?)
            """, (default_skills, default_roles, default_locations, other_pref, datetime.now(timezone.utc).isoformat()))
            
        conn.commit()

def get_profile() -> Dict[str, Any]:
    """Retrieve the stored user profile."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            return {}
        
        data = dict(row)
        # Parse JSON fields safely
        for json_field in ["skills", "experience", "projects", "certifications", "preferred_roles", "preferred_locations"]:
            if data.get(json_field):
                try:
                    data[json_field] = json.loads(data[json_field])
                except Exception:
                    data[json_field] = []
            else:
                data[json_field] = []
        return data

def save_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save or update the stored user profile."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Convert list/dict fields to JSON strings
        skills_json = json.dumps(profile_data.get("skills", []))
        experience_json = json.dumps(profile_data.get("experience", []))
        projects_json = json.dumps(profile_data.get("projects", []))
        certifications_json = json.dumps(profile_data.get("certifications", []))
        preferred_roles_json = json.dumps(profile_data.get("preferred_roles", []))
        preferred_locations_json = json.dumps(profile_data.get("preferred_locations", []))
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            UPDATE profiles SET
                full_name = ?,
                email = ?,
                phone = ?,
                degree = ?,
                graduation_year = ?,
                skills = ?,
                experience = ?,
                projects = ?,
                certifications = ?,
                preferred_roles = ?,
                preferred_locations = ?,
                work_mode = ?,
                experience_level = ?,
                other_preferences = ?,
                raw_resume_text = COALESCE(?, raw_resume_text),
                active_resume_id = COALESCE(?, active_resume_id),
                updated_at = ?
            WHERE id = 1
        """, (
            profile_data.get("full_name", ""),
            profile_data.get("email", ""),
            profile_data.get("phone", ""),
            profile_data.get("degree", ""),
            profile_data.get("graduation_year", ""),
            skills_json,
            experience_json,
            projects_json,
            certifications_json,
            preferred_roles_json,
            preferred_locations_json,
            profile_data.get("work_mode", "Any"),
            profile_data.get("experience_level", "Mid"),
            profile_data.get("other_preferences", ""),
            profile_data.get("raw_resume_text"),
            profile_data.get("active_resume_id"),
            now
        ))
        conn.commit()
    return get_profile()

def add_resume(filename: str, stored_path: str, label: str, raw_text: str) -> int:
    """Record an uploaded resume."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO resumes (filename, stored_path, label, raw_text, uploaded_at)
            VALUES (?, ?, ?, ?, ?)
        """, (filename, stored_path, label, raw_text, now))
        resume_id = cursor.lastrowid
        
        # Set as active resume if it's the first or updated
        cursor.execute("UPDATE profiles SET active_resume_id = ? WHERE id = 1", (resume_id,))
        conn.commit()
        return resume_id

def list_resumes() -> List[Dict[str, Any]]:
    """List all uploaded resumes."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, stored_path, label, uploaded_at, length(raw_text) as char_count FROM resumes ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_resume(resume_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific resume by ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def set_active_resume(resume_id: int) -> bool:
    """Set the active resume version for the candidate profile."""
    init_db()
    resume = get_resume(resume_id)
    if not resume:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE profiles SET active_resume_id = ?, raw_resume_text = ? WHERE id = 1", 
                       (resume_id, resume.get("raw_text", "")))
        conn.commit()
        return True

# -------------------------------------------------------------
# Phase 2: Job Persistence & Queries
# -------------------------------------------------------------

def create_job(
    company_name: str,
    company_email: str = "",
    job_title: str = "",
    location: str = "",
    job_url: str = "",
    raw_description: str = "",
    required_qualifications: Optional[Dict[str, Any]] = None,
    preferred_qualifications: Optional[Dict[str, Any]] = None,
    summary: str = ""
) -> int:
    """Create and persist a new analyzed job."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT INTO jobs (
                company_name, company_email, job_title, location, job_url,
                raw_description, required_qualifications, preferred_qualifications,
                summary, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_name,
            company_email,
            job_title,
            location,
            job_url,
            raw_description,
            json.dumps(required_qualifications or {}),
            json.dumps(preferred_qualifications or {}),
            summary,
            now,
            now
        ))
        conn.commit()
        return cursor.lastrowid

def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a specific job by ID with parsed JSON qualifications."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return None
        data = dict(row)
        for json_field in ["required_qualifications", "preferred_qualifications"]:
            if data.get(json_field):
                try:
                    data[json_field] = json.loads(data[json_field])
                except Exception:
                    data[json_field] = {}
            else:
                data[json_field] = {}
        return data

def list_jobs() -> List[Dict[str, Any]]:
    """List all saved jobs (ordered by most recent)."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, company_name, company_email, job_title, location, job_url,
                   summary, created_at, updated_at
            FROM jobs
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def update_job(
    job_id: int,
    company_name: str,
    company_email: str,
    job_title: str,
    location: str,
    job_url: str,
    required_qualifications: Dict[str, Any],
    preferred_qualifications: Dict[str, Any],
    summary: str = ""
) -> Optional[Dict[str, Any]]:
    """Update job details and qualifications."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            UPDATE jobs SET
                company_name = ?,
                company_email = ?,
                job_title = ?,
                location = ?,
                job_url = ?,
                required_qualifications = ?,
                preferred_qualifications = ?,
                summary = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            company_name,
            company_email,
            job_title,
            location,
            job_url,
            json.dumps(required_qualifications),
            json.dumps(preferred_qualifications),
            summary,
            now,
            job_id
        ))
        conn.commit()
    return get_job(job_id)

def delete_job(job_id: int) -> bool:
    """Delete a job by ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()
        return cursor.rowcount > 0

# -------------------------------------------------------------
# Phase 3 & 4: Application Drafts & Tracking
# -------------------------------------------------------------

def save_application(
    job_id: int,
    company_name: str = "",
    job_title: str = "",
    recipient_email: str = "",
    match_score: int = 0,
    match_summary: Optional[Dict[str, Any]] = None,
    email_subject: str = "",
    email_body: str = "",
    attached_resume_id: Optional[int] = None,
    status: str = "Draft",
    notes: str = "",
    follow_up_date: str = "",
    response_status: str = "Pending"
) -> int:
    """Save or update an application draft for a specific job."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        # Check if an active un-sent application draft exists for this job
        cursor.execute("SELECT id, status FROM applications WHERE job_id = ? AND status != 'Sent'", (job_id,))
        existing = cursor.fetchone()
        
        summary_json = json.dumps(match_summary or {})
        
        if existing:
            app_id = existing["id"]
            cursor.execute("""
                UPDATE applications SET
                    company_name = ?,
                    job_title = ?,
                    recipient_email = ?,
                    match_score = ?,
                    match_summary = ?,
                    email_subject = ?,
                    email_body = ?,
                    attached_resume_id = ?,
                    status = ?,
                    notes = ?,
                    follow_up_date = ?,
                    response_status = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                company_name,
                job_title,
                recipient_email,
                match_score,
                summary_json,
                email_subject,
                email_body,
                attached_resume_id,
                status,
                notes,
                follow_up_date,
                response_status,
                now,
                app_id
            ))
            conn.commit()
            return app_id
        else:
            cursor.execute("""
                INSERT INTO applications (
                    job_id, company_name, job_title, recipient_email,
                    match_score, match_summary, email_subject, email_body,
                    attached_resume_id, status, notes, follow_up_date, response_status,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                company_name,
                job_title,
                recipient_email,
                match_score,
                summary_json,
                email_subject,
                email_body,
                attached_resume_id,
                status,
                notes,
                follow_up_date,
                response_status,
                now,
                now
            ))
            conn.commit()
            return cursor.lastrowid

def get_application_by_job(job_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve application draft for a specific job."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("match_summary"):
            try:
                data["match_summary"] = json.loads(data["match_summary"])
            except Exception:
                data["match_summary"] = {}
        return data

def get_application(app_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve application by ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        row = cursor.fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("match_summary"):
            try:
                data["match_summary"] = json.loads(data["match_summary"])
            except Exception:
                data["match_summary"] = {}
        return data

def update_application_draft(
    app_id: int,
    email_subject: str,
    email_body: str,
    recipient_email: str
) -> Optional[Dict[str, Any]]:
    """Update email draft subject and body."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            UPDATE applications SET
                email_subject = ?,
                email_body = ?,
                recipient_email = ?,
                updated_at = ?
            WHERE id = ?
        """, (email_subject, email_body, recipient_email, now, app_id))
        conn.commit()
    return get_application(app_id)

def mark_application_sent(
    app_id: int,
    recipient_email: str,
    email_subject: str,
    email_body: str,
    notes: str = ""
) -> Optional[Dict[str, Any]]:
    """Mark an application as Approved and Sent."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            UPDATE applications SET
                status = 'Sent',
                recipient_email = ?,
                email_subject = ?,
                email_body = ?,
                notes = ?,
                updated_at = ?
            WHERE id = ?
        """, (recipient_email, email_subject, email_body, notes, now, app_id))
        conn.commit()
    return get_application(app_id)

# -------------------------------------------------------------
# Phase 5: Tracking Dashboard Queries & Mutations
# -------------------------------------------------------------

def list_applications(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve applications, optionally filtered by status, ordered by most recently updated."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        if status and status.strip() and status.lower() != "all":
            cursor.execute("SELECT * FROM applications WHERE status = ? ORDER BY updated_at DESC", (status.strip(),))
        else:
            cursor.execute("SELECT * FROM applications ORDER BY updated_at DESC")
        
        rows = cursor.fetchall()
        results = []
        for r in rows:
            data = dict(r)
            if data.get("match_summary"):
                try:
                    data["match_summary"] = json.loads(data["match_summary"])
                except Exception:
                    data["match_summary"] = {}
            results.append(data)
        return results

def update_application_status(
    app_id: int,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    follow_up_date: Optional[str] = None,
    response_status: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update status, notes, follow-up date, or response status of an application."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        fields = []
        params = []
        
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if notes is not None:
            fields.append("notes = ?")
            params.append(notes)
        if follow_up_date is not None:
            fields.append("follow_up_date = ?")
            params.append(follow_up_date)
        if response_status is not None:
            fields.append("response_status = ?")
            params.append(response_status)
            
        fields.append("updated_at = ?")
        params.append(now)
        
        params.append(app_id)
        
        query = f"UPDATE applications SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        
    return get_application(app_id)

def delete_application(app_id: int) -> bool:
    """Delete an application record by ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_tracking_metrics() -> Dict[str, Any]:
    """Calculate aggregate tracking statistics for the dashboard."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT status, count(*) as count FROM applications GROUP BY status")
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
        
        cursor.execute("SELECT count(*) as total FROM applications")
        total = cursor.fetchone()["total"]
        
        # Follow-ups due: date <= today and not closed/rejected/offer
        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT count(*) as due_count FROM applications 
            WHERE follow_up_date != '' 
              AND follow_up_date <= ? 
              AND status NOT IN ('Rejected', 'Closed', 'Offer')
        """, (today_iso,))
        due_follow_ups = cursor.fetchone()["due_count"]
        
        return {
            "total": total,
            "drafts": status_counts.get("Draft", 0) + status_counts.get("Ready for Review", 0),
            "sent": status_counts.get("Sent", 0),
            "follow_up": status_counts.get("Follow-up", 0),
            "interview": status_counts.get("Interview", 0),
            "offer": status_counts.get("Offer", 0),
            "rejected": status_counts.get("Rejected", 0),
            "closed": status_counts.get("Closed", 0),
            "due_follow_ups": due_follow_ups,
            "by_status": status_counts
        }




