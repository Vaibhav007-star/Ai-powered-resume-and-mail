import html
import json
import logging
import re
import urllib.parse
import urllib.request
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.core.config import ADZUNA_APP_ID, ADZUNA_APP_KEY, RAPIDAPI_KEY

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 JobAssistant/1.0"
REQUEST_TIMEOUT = 8

FOREIGN_LOCATIONS = {
    "berlin", "germany", "usa", "united states", "uk", "london", "canada",
    "france", "paris", "latam", "ireland", "australia", "poland", "spain",
    "netherlands", "munich", "argentina", "brazil", "mexico", "peru",
    "austria", "switzerland", "italy", "sweden", "denmark", "japan", "singapore"
}

RE_HTML_BREAKS = re.compile(r'<(br|p|div|li)[^>]*>', re.IGNORECASE)
RE_HTML_TAGS = re.compile(r'<[^>]+>')
RE_HTML_NEWLINES = re.compile(r'\n\s*\n+')
RE_STIPEND_K = re.compile(r'(\d+)\s*k', re.IGNORECASE)
RE_STIPEND_NUMS = re.compile(r'([0-9,]+)')
RE_INTERNSHALA_CARDS = re.compile(r'<div[^>]*class="[^"]*individual_internship[^"]*"[^>]*id="([^"]+)"')
RE_JOB_TITLE = re.compile(r'<a[^>]*class="job-title-href"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>')
RE_COMPANY_NAME = re.compile(r'<p[^>]*class="company-name"[^>]*>([^<]+)</p>')
RE_JOB_LOC = re.compile(r'<div[^>]*class="row-1-item locations"[^>]*>.*?<span>.*?<a>([^<]+)</a>', re.DOTALL)
RE_STIPEND_RAW = re.compile(r'<span[^>]*class=[\'"]stipend[\'"][^>]*>([^<]+)</span>')
RE_DURATION = re.compile(r'([0-9]+\s+Months?)', re.IGNORECASE)

def strip_html_tags(raw_html: str) -> str:
    """Utility to clean HTML tags and unescape entities for plain-text extraction."""
    if not raw_html:
        return ""
    text = RE_HTML_BREAKS.sub('\n', raw_html)
    clean = RE_HTML_TAGS.sub(' ', text)
    clean = html.unescape(clean)
    clean = RE_HTML_NEWLINES.sub('\n\n', clean)
    return clean.strip()

def parse_stipend_amount(stipend_str: str) -> int:
    """Extract numeric stipend amount from string representations."""
    if not stipend_str:
        return 0
    k_match = RE_STIPEND_K.search(stipend_str)
    if k_match:
        return int(k_match.group(1)) * 1000
    nums = [int(n.replace(",", "")) for n in RE_STIPEND_NUMS.findall(stipend_str) if len(n.replace(",", "")) >= 4]
    return max(nums) if nums else 0

def _make_http_request(url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Helper to perform safe HTTP GET requests."""
    import sys
    target_mod = sys.modules.get("backend.job_fetcher")
    if target_mod and hasattr(target_mod, "_make_http_request"):
        target_fn = getattr(target_mod, "_make_http_request")
        if target_fn is not _make_http_request:
            return target_fn(url, headers)

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
    """Fetch verified student internships in Delhi NCR with duration and stipend filters."""
    jobs: List[Dict[str, Any]] = []

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

            card_ids = RE_INTERNSHALA_CARDS.findall(html_text)
            city_count = 0

            for cid in card_ids:
                if city_count >= per_city_limit:
                    break
                pos = html_text.find(f'id="{cid}"')
                if pos == -1:
                    continue
                chunk = html_text[pos:pos + 3500]

                t_m = RE_JOB_TITLE.search(chunk)
                if not t_m:
                    continue
                job_url = "https://internshala.com" + t_m.group(1).strip()
                title = t_m.group(2).strip()

                c_m = RE_COMPANY_NAME.search(chunk)
                company = c_m.group(1).strip() if c_m else "Company"

                l_m = RE_JOB_LOC.search(chunk)
                job_loc = l_m.group(1).strip() if l_m else city.capitalize()
                if "gurgaon" in job_loc.lower():
                    job_loc = "Gurugram (Delhi NCR)"
                elif "delhi" in job_loc.lower():
                    job_loc = "Delhi (Delhi NCR)"
                elif "noida" in job_loc.lower():
                    job_loc = "Noida (Delhi NCR)"

                s_m = RE_STIPEND_RAW.search(chunk)
                stipend_raw = s_m.group(1).strip() if s_m else "Unspecified"
                clean_stipend = stipend_raw.replace("\u20b9", "INR ").strip()
                stipend_amt = parse_stipend_amount(clean_stipend)

                d_m = RE_DURATION.search(chunk)
                duration = d_m.group(1).strip() if d_m else "3-6 Months"

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
    """Fetch roles from Adzuna API if configured."""
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
    """Check if job location aligns with Indian / Delhi NCR preferences."""
    loc_lower = job_location.lower().strip()
    target_lower = target_location.lower().strip()

    for foreign in FOREIGN_LOCATIONS:
        if foreign in loc_lower and "india" not in loc_lower and "worldwide" not in loc_lower:
            return False

    if any(k in target_lower for k in ["delhi", "noida", "gurugram", "gurgaon", "ncr", "india"]):
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
    """Unified job aggregator prioritizing India & Delhi NCR."""
    import sys
    target_mod = sys.modules.get("backend.job_fetcher", sys.modules[__name__])
    fn_internshala = getattr(target_mod, "fetch_from_internshala", fetch_from_internshala)
    fn_remotive = getattr(target_mod, "fetch_from_remotive", fetch_from_remotive)
    fn_jobicy = getattr(target_mod, "fetch_from_jobicy", fetch_from_jobicy)
    fn_arbeitnow = getattr(target_mod, "fetch_from_arbeitnow", fetch_from_arbeitnow)
    fn_adzuna = getattr(target_mod, "fetch_from_adzuna", fetch_from_adzuna)

    clean_query = query.strip() or "data science"
    loc_str = (location or "delhi_ncr").strip()
    per_source_limit = max(6, limit // 2)

    aggregated: List[Dict[str, Any]] = []

    def run_internshala():
        try:
            return fn_internshala(
                query=clean_query,
                location=loc_str,
                min_stipend=min_stipend,
                limit=per_source_limit * 2
            )
        except Exception as e:
            logger.warning(f"Internshala search error: {e}")
            return []

    def run_adzuna():
        if ADZUNA_APP_ID and ADZUNA_APP_KEY:
            try:
                return fn_adzuna(clean_query, loc_str, limit=per_source_limit)
            except Exception as e:
                logger.warning(f"Adzuna search error: {e}")
        return []

    def run_remotive():
        try:
            remotive_jobs = fn_remotive(clean_query, limit=per_source_limit)
            return [r for r in remotive_jobs if is_eligible_for_india(r["location"], loc_str)]
        except Exception as e:
            logger.warning(f"Remotive search error: {e}")
            return []

    def run_jobicy():
        try:
            jobicy_jobs = fn_jobicy(clean_query, limit=per_source_limit)
            return [j for j in jobicy_jobs if is_eligible_for_india(j["location"], loc_str)]
        except Exception as e:
            logger.warning(f"Jobicy search error: {e}")
            return []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(run_internshala),
            executor.submit(run_adzuna),
            executor.submit(run_remotive),
            executor.submit(run_jobicy)
        ]
        for future in as_completed(futures):
            res = future.result()
            if res:
                aggregated.extend(res)

    seen_keys = set()
    deduped: List[Dict[str, Any]] = []

    for job in aggregated:
        key = f"{job['title'].lower().strip()}_{job['company_name'].lower().strip()}"
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(job)

    query_tokens = [t.lower() for t in clean_query.split() if len(t) > 2]
    
    def score_job(j: Dict[str, Any]) -> int:
        score = 0
        loc_l = j["location"].lower()
        title_l = j["title"].lower()
        desc_l = j["description"].lower()

        if any(c in loc_l for c in ["delhi", "noida", "gurugram", "gurgaon", "ncr"]):
            score += 20
        elif "india" in loc_l:
            score += 10

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
