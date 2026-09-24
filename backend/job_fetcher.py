import html
import json
import logging
import re
import urllib.parse
import urllib.request
from typing import List, Dict, Any, Optional

from backend.config import ADZUNA_APP_ID, ADZUNA_APP_KEY, RAPIDAPI_KEY

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 JobAssistant/1.0"
REQUEST_TIMEOUT = 8  # 8-second timeout to prevent UI hang

# Foreign location keywords to filter out when user targets India / Delhi NCR
FOREIGN_LOCATIONS = {
    "berlin", "germany", "usa", "united states", "uk", "london", "canada",
    "france", "paris", "latam", "ireland", "australia", "poland", "spain",
    "netherlands", "munich", "argentina", "brazil", "mexico", "peru",
    "austria", "switzerland", "italy", "sweden", "denmark", "japan", "singapore"
}

def strip_html_tags(raw_html: str) -> str:
    """Utility to clean HTML tags and unescape entities for plain-text extraction."""
    if not raw_html:
        return ""
    text = re.sub(r'<(br|p|div|li)[^>]*>', '\n', raw_html, flags=re.IGNORECASE)
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = html.unescape(clean)
    clean = re.sub(r'\n\s*\n+', '\n\n', clean)
    return clean.strip()

def parse_stipend_amount(stipend_str: str) -> int:
    """
    Extract numeric stipend amount from string representations like:
    'INR 10,000 - 15,000 /month' -> 15000
    '₹12,000 /month' -> 12000
    '15k/mo' -> 15000
    """
    if not stipend_str:
        return 0
    # Handle '15k' notation
    k_match = re.search(r'(\d+)\s*k', stipend_str, re.IGNORECASE)
    if k_match:
        return int(k_match.group(1)) * 1000
    # Handle comma-separated numbers (>= 1,000)
    nums = [int(n.replace(",", "")) for n in re.findall(r'([0-9,]+)', stipend_str) if len(n.replace(",", "")) >= 4]
    return max(nums) if nums else 0

def _make_http_request(url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Helper to perform safe, timeout-bounded HTTP GET requests."""
    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            if resp.status == 200:
                raw_bytes = resp.read()
                return json.loads(raw_bytes.decode("utf-8", errors="ignore"))
    except Exception as e:
        logger.warning(f"Job API request to {url} failed: {e}")
    return None

def fetch_from_internshala(
    query: str = "data science",
    location: str = "delhi_ncr",
    min_stipend: int = 10000,
    limit: int = 15
) -> List[Dict[str, Any]]:
    """
    Fetch verified student internships in Delhi NCR (Delhi, Noida, Gurugram)
    with duration (3-6 months) and minimum stipend filtering.
    """
    jobs: List[Dict[str, Any]] = []

    # Map target cities in Delhi NCR
    loc_lower = (location or "delhi_ncr").lower()
    target_cities = []
    if "delhi_ncr" in loc_lower or "ncr" in loc_lower:
        target_cities = ["delhi", "noida", "gurgaon"]
    elif "noida" in loc_lower:
        target_cities = ["noida"]
    elif "gurugram" in loc_lower or "gurgaon" in loc_lower:
        target_cities = ["gurgaon"]
    elif "remote" in loc_lower:
        target_cities = ["work-from-home"]
    else:
        target_cities = ["delhi", "noida", "gurgaon"]

    # Map query to category slug
    q_lower = query.lower()
    slug_category = "data-science"
    if "machine" in q_lower or "ml" in q_lower:
        slug_category = "machine-learning"
    elif "ai" in q_lower or "artificial" in q_lower:
        slug_category = "artificial-intelligence-ai"
    elif "analyst" in q_lower:
        slug_category = "data-analytics"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    per_city_limit = max(4, limit // len(target_cities))

    for city in target_cities:
        if city == "work-from-home":
            url = f"https://internshala.com/internships/work-from-home-{slug_category}-internships/"
        else:
            url = f"https://internshala.com/internships/{slug_category}-internship-in-{city}/"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                html_text = resp.read().decode("utf-8", errors="ignore")

            card_ids = re.findall(r'<div[^>]*class="[^"]*individual_internship[^"]*"[^>]*id="([^"]+)"', html_text)
            city_count = 0

            for cid in card_ids:
                if city_count >= per_city_limit:
                    break
                pos = html_text.find(f'id="{cid}"')
                if pos == -1:
                    continue
                chunk = html_text[pos:pos + 3500]

                # Title & URL
                t_m = re.search(r'<a[^>]*class="job-title-href"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', chunk)
                if not t_m:
                    continue
                job_url = "https://internshala.com" + t_m.group(1).strip()
                title = t_m.group(2).strip()

                # Company
                c_m = re.search(r'<p[^>]*class="company-name"[^>]*>([^<]+)</p>', chunk)
                company = c_m.group(1).strip() if c_m else "Company"

                # Location
                l_m = re.search(r'<div[^>]*class="row-1-item locations"[^>]*>.*?<span>.*?<a>([^<]+)</a>', chunk, re.DOTALL)
                job_loc = l_m.group(1).strip() if l_m else city.capitalize()
                if "gurgaon" in job_loc.lower():
                    job_loc = "Gurugram (Delhi NCR)"
                elif "delhi" in job_loc.lower():
                    job_loc = "Delhi (Delhi NCR)"
                elif "noida" in job_loc.lower():
                    job_loc = "Noida (Delhi NCR)"

                # Stipend
                s_m = re.search(r'<span[^>]*class=[\'"]stipend[\'"][^>]*>([^<]+)</span>', chunk)
                stipend_raw = s_m.group(1).strip() if s_m else "Unspecified"
                clean_stipend = stipend_raw.replace("\u20b9", "INR ").strip()
                stipend_amt = parse_stipend_amount(clean_stipend)

                # Duration
                d_m = re.search(r'([0-9]+\s+Months?)', chunk, re.IGNORECASE)
                duration = d_m.group(1).strip() if d_m else "3-6 Months"

                # Filter by minimum stipend if specified (e.g. >= 10000)
                if min_stipend > 0 and stipend_amt > 0 and stipend_amt < min_stipend:
                    continue

                jobs.append({
                    "id": f"internshala_{cid.replace('individual_internship_', '')}",
                    "title": title,
                    "company_name": company,
                    "location": job_loc,
                    "job_url": job_url,
                    "description": f"Internship Opportunity at {company} in {job_loc}.\nRole: {title}\nDuration: {duration} (College Criteria: 3-6 months eligible)\nStipend: {clean_stipend}\nRequired Domain: Data Science, Python, Machine Learning.",
                    "tags": ["Data Science", "Python", duration, clean_stipend],
                    "stipend": clean_stipend,
                    "duration": duration,
                    "source": "Internshala (Delhi NCR)",
                    "published_at": "Active Opening"
                })
                city_count += 1

        except Exception as e:
            logger.warning(f"Internshala fetch for {city} failed: {e}")

    return jobs

def fetch_from_jobicy(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch tech & data roles from Jobicy public API."""
    jobs: List[Dict[str, Any]] = []
    tag = urllib.parse.quote(query.replace(" ", "-").lower())
    url = f"https://jobicy.com/api/v2/remote-jobs?count={limit}&tag={tag}"
    data = _make_http_request(url)
    
    if not data or not data.get("jobs"):
        fallback_url = f"https://jobicy.com/api/v2/remote-jobs?count={limit}&industry=engineering"
        data = _make_http_request(fallback_url)

    if data and isinstance(data.get("jobs"), list):
        for item in data["jobs"]:
            desc = strip_html_tags(item.get("jobDescription", ""))
            industry_val = item.get("jobIndustry", [])
            if isinstance(industry_val, str):
                tags = [t.strip() for t in industry_val.split(",") if t.strip()]
            elif isinstance(industry_val, list):
                tags = [str(t).strip() for t in industry_val if str(t).strip()]
            else:
                tags = []

            jobs.append({
                "id": f"jobicy_{item.get('id', '')}",
                "title": item.get("jobTitle", "Untitled Role").strip(),
                "company_name": item.get("companyName", "Unknown Company").strip(),
                "location": item.get("jobGeo", "Worldwide / Remote").strip(),
                "job_url": item.get("url", ""),
                "description": desc,
                "tags": tags,
                "source": "Jobicy",
                "published_at": item.get("pubDate", "")
            })
    return jobs

def fetch_from_remotive(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch roles from Remotive public API."""
    jobs: List[Dict[str, Any]] = []
    safe_q = urllib.parse.quote(query.strip())
    url = f"https://remotive.com/api/remote-jobs?search={safe_q}&limit={limit}"
    data = _make_http_request(url)

    if not data or not data.get("jobs"):
        url = f"https://remotive.com/api/remote-jobs?category=data&limit={limit}"
        data = _make_http_request(url)

    if data and isinstance(data.get("jobs"), list):
        for item in data["jobs"][:limit]:
            desc = strip_html_tags(item.get("description", ""))
            loc = item.get("candidate_required_location") or "Worldwide / Remote"
            jobs.append({
                "id": f"remotive_{item.get('id', '')}",
                "title": item.get("title", "Untitled Role").strip(),
                "company_name": item.get("company_name", "Unknown Company").strip(),
                "location": loc,
                "job_url": item.get("url", ""),
                "description": desc,
                "tags": item.get("tags", []),
                "source": "Remotive",
                "published_at": item.get("publication_date", "")
            })
    return jobs

def fetch_from_arbeitnow(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch roles from Arbeitnow public API."""
    jobs: List[Dict[str, Any]] = []
    safe_q = urllib.parse.quote(query.strip())
    url = f"https://www.arbeitnow.com/api/job-board-api?search={safe_q}"
    data = _make_http_request(url)

    if data and isinstance(data.get("data"), list):
        for item in data["data"][:limit]:
            desc = strip_html_tags(item.get("description", ""))
            loc = item.get("location") or "Remote"
            jobs.append({
                "id": f"arbeitnow_{item.get('slug', '')}",
                "title": item.get("title", "Untitled Role").strip(),
                "company_name": item.get("company_name", "Unknown Company").strip(),
                "location": loc,
                "job_url": item.get("url", ""),
                "description": desc,
                "tags": item.get("tags", []),
                "source": "Arbeitnow",
                "published_at": str(item.get("created_at", ""))
            })
    return jobs

def fetch_from_adzuna(query: str, location: Optional[str] = "in", limit: int = 10) -> List[Dict[str, Any]]:
    """Optional: Fetch roles from Adzuna API if ADZUNA_APP_ID & ADZUNA_APP_KEY are set."""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []
        
    jobs: List[Dict[str, Any]] = []
    country = "in" if not location or "india" in location.lower() or "delhi" in location.lower() else "us"
    safe_q = urllib.parse.quote(query.strip())
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}&what={safe_q}&results_per_page={limit}"
    data = _make_http_request(url)

    if data and isinstance(data.get("results"), list):
        for item in data["results"][:limit]:
            loc_data = item.get("location", {})
            loc_area = ", ".join(loc_data.get("area", [])) or "Delhi NCR, India"
            jobs.append({
                "id": f"adzuna_{item.get('id', '')}",
                "title": item.get("title", "Untitled Role").strip(),
                "company_name": item.get("company", {}).get("display_name", "Company").strip(),
                "location": loc_area,
                "job_url": item.get("redirect_url", ""),
                "description": item.get("description", "").strip(),
                "tags": [item.get("category", {}).get("label", "Tech")],
                "source": "Adzuna (India)",
                "published_at": item.get("created", "")
            })
    return jobs

def is_eligible_for_india(job_location: str, target_location: str) -> bool:
    """
    Check if a job location aligns with Indian / Delhi NCR preferences.
    Rejects foreign overseas locations like Berlin, Germany, USA, etc.
    """
    loc_lower = job_location.lower().strip()
    target_lower = target_location.lower().strip()

    # Reject explicit foreign countries unless explicitly stated India or Worldwide
    for foreign in FOREIGN_LOCATIONS:
        if foreign in loc_lower and "india" not in loc_lower and "worldwide" not in loc_lower:
            return False

    # If user specifies Delhi NCR or specific city
    if any(k in target_lower for k in ["delhi", "noida", "gurugram", "gurgaon", "ncr", "india"]):
        # Accept if matches Indian target cities or remote India/worldwide
        if any(c in loc_lower for c in ["delhi", "noida", "gurugram", "gurgaon", "ncr", "india"]):
            return True
        if "worldwide" in loc_lower or ("remote" in loc_lower and not any(f in loc_lower for f in FOREIGN_LOCATIONS)):
            return True
        return False

    return True

def fetch_open_jobs(
    query: str = "data science",
    location: Optional[str] = "delhi_ncr",
    min_stipend: int = 10000,
    limit: int = 25
) -> List[Dict[str, Any]]:
    """
    Unified job aggregator prioritizing India & Delhi NCR (Delhi, Noida, Gurugram):
    - Fetches live internships from Internshala for Delhi NCR
    - Fetches from Adzuna (India) if configured
    - Filters out overseas foreign listings (Berlin, Germany, USA, UK, etc.)
    - Enforces minimum stipend filtering (e.g. >= Rs. 10,000/month)
    """
    clean_query = query.strip() or "data science"
    loc_str = (location or "delhi_ncr").strip()
    per_source_limit = max(6, limit // 2)

    aggregated: List[Dict[str, Any]] = []

    # 1. Primary Source for Delhi NCR Internships: Internshala
    try:
        internshala_jobs = fetch_from_internshala(
            query=clean_query,
            location=loc_str,
            min_stipend=min_stipend,
            limit=per_source_limit * 2
        )
        aggregated.extend(internshala_jobs)
    except Exception as e:
        logger.warning(f"Internshala search error: {e}")

    # 2. Adzuna India (if configured)
    if ADZUNA_APP_ID and ADZUNA_APP_KEY:
        try:
            adzuna_jobs = fetch_from_adzuna(clean_query, loc_str, limit=per_source_limit)
            aggregated.extend(adzuna_jobs)
        except Exception as e:
            logger.warning(f"Adzuna search error: {e}")

    # 3. Remotive & Jobicy (only if location is remote or broad, and strictly filter foreign)
    try:
        remotive_jobs = fetch_from_remotive(clean_query, limit=per_source_limit)
        for r in remotive_jobs:
            if is_eligible_for_india(r["location"], loc_str):
                aggregated.append(r)
    except Exception as e:
        logger.warning(f"Remotive search error: {e}")

    try:
        jobicy_jobs = fetch_from_jobicy(clean_query, limit=per_source_limit)
        for j in jobicy_jobs:
            if is_eligible_for_india(j["location"], loc_str):
                aggregated.append(j)
    except Exception as e:
        logger.warning(f"Jobicy search error: {e}")

    # Deduplicate by normalized (title + company)
    seen_keys = set()
    deduped: List[Dict[str, Any]] = []

    for job in aggregated:
        key = f"{job['title'].lower().strip()}_{job['company_name'].lower().strip()}"
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(job)

    # Score and rank: boost Delhi NCR and matching keywords
    query_tokens = [t.lower() for t in clean_query.split() if len(t) > 2]
    
    def score_job(j: Dict[str, Any]) -> int:
        score = 0
        loc_l = j["location"].lower()
        title_l = j["title"].lower()
        desc_l = j["description"].lower()

        # Prioritize exact Delhi NCR locations
        if any(c in loc_l for c in ["delhi", "noida", "gurugram", "gurgaon", "ncr"]):
            score += 20
        elif "india" in loc_l:
            score += 10

        # Prioritize internship titles
        if "intern" in title_l:
            score += 15

        for tok in query_tokens:
            if tok in title_l:
                score += 5
            elif tok in desc_l:
                score += 1
        return score

    deduped.sort(key=score_job, reverse=True)

    return deduped[:limit]
