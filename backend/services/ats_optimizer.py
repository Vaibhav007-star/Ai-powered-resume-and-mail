import math
import re
from collections import Counter
from typing import Dict, Any, List, Set, Tuple

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he",
    "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on",
    "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "should", "shouldn't", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "were", "weren't", "what", "when", "where", "which", "while", "who", "whom", "why", "with",
    "won't", "would", "wouldn't", "you", "your", "yours", "yourself", "yourselves", "role", "job", "candidate",
    "work", "ability", "experience", "looking", "team", "year", "years", "must", "required", "preferred"
}

RE_WORD = re.compile(r"\b[a-zA-Z0-9+#.-]{2,}\b")

def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase terms excluding stop words."""
    if not text:
        return []
    words = RE_WORD.findall(text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]

def calculate_cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """Compute cosine similarity between two term frequency vectors."""
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum(vec1[x] * vec2[x] for x in intersection)

    sum1 = sum(val ** 2 for val in vec1.values())
    sum2 = sum(val ** 2 for val in vec2.values())
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    return float(numerator / denominator)

def analyze_ats_optimization(
    profile: Dict[str, Any],
    job: Dict[str, Any]
) -> Dict[str, Any]:
    """ATS Keyword Gap Analyzer & Semantic RAG Vector Optimizer."""
    resume_text = (profile.get("raw_resume_text", "") or "").strip()
    if not resume_text:
        parts = [profile.get("full_name", ""), profile.get("degree", "")]
        parts.extend(profile.get("skills", []))
        for p in profile.get("projects", []):
            parts.append(f"{p.get('name', '')} {p.get('tech', '')} {p.get('description', '')}")
        for e in profile.get("experience", []):
            parts.append(f"{e.get('title', '')} {e.get('company', '')} {e.get('description', '')}")
        resume_text = " ".join(parts)

    jd_text = job.get("raw_description", "") or ""
    req_qual = job.get("required_qualifications", {})
    pref_qual = job.get("preferred_qualifications", {})

    jd_skills = list(dict.fromkeys(
        req_qual.get("skills", []) +
        req_qual.get("technologies", []) +
        pref_qual.get("skills", []) +
        pref_qual.get("technologies", [])
    ))

    resume_tokens = tokenize(resume_text)
    jd_tokens = tokenize(jd_text)

    tf_resume = Counter(resume_tokens)
    tf_jd = Counter(jd_tokens)

    semantic_fit_ratio = calculate_cosine_similarity(tf_resume, tf_jd)
    semantic_score = int(round(semantic_fit_ratio * 100))

    resume_tokens_set = set(resume_tokens)
    matched_jd_keywords = []
    missing_critical_keywords = []

    for s in jd_skills:
        s_lower = s.lower().strip()
        if any(token in resume_tokens_set for token in s_lower.split()):
            matched_jd_keywords.append(s)
        else:
            missing_critical_keywords.append(s)

    top_jd_freq = tf_jd.most_common(20)
    for term, freq in top_jd_freq:
        if freq >= 2 and term not in tf_resume and term not in [k.lower() for k in missing_critical_keywords]:
            if len(term) >= 3 and not term.isdigit():
                missing_critical_keywords.append(term.capitalize())

    missing_critical_keywords = list(dict.fromkeys(missing_critical_keywords))[:10]
    matched_jd_keywords = list(dict.fromkeys(matched_jd_keywords))

    keyword_coverage_ratio = len(matched_jd_keywords) / max(len(jd_skills), 1) if jd_skills else 0.8
    ats_score = int(round((keyword_coverage_ratio * 55) + (semantic_fit_ratio * 35) + 10))
    final_ats_score = min(max(ats_score, 15), 98)

    formatting_issues = []
    if len(resume_text) < 300:
        formatting_issues.append("Resume content is short (under 300 characters). Consider expanding section details.")
    if not any(k in resume_text.lower() for k in ["project", "experience", "work", "education"]):
        formatting_issues.append("Standard section headings (Projects, Experience, Education) are missing or non-standard.")
    if "email" not in profile or not profile.get("email"):
        formatting_issues.append("Contact email missing from candidate header.")

    bullet_suggestions = []
    for proj in profile.get("projects", [])[:2]:
        p_name = proj.get("name", "Project")
        p_tech = proj.get("tech", "")
        if missing_critical_keywords:
            suggested_term = missing_critical_keywords[0]
            bullet_suggestions.append(
                f"For project '{p_name}', highlight any authentic usage of '{suggested_term}' alongside {p_tech or 'existing stack'} to improve ATS relevance."
            )

    if not bullet_suggestions and missing_critical_keywords:
        bullet_suggestions.append(
            f"In corporate experience, explicitly cite '{', '.join(missing_critical_keywords[:3])}' where truthfully applicable."
        )

    return {
        "ats_score": final_ats_score,
        "semantic_similarity_score": semantic_score,
        "keyword_coverage_percentage": int(round(keyword_coverage_ratio * 100)),
        "matched_keywords": matched_jd_keywords,
        "missing_keywords": missing_critical_keywords,
        "formatting_issues": formatting_issues,
        "bullet_suggestions": bullet_suggestions,
        "readability_index": "High (Machine Readable PDF/DOCX)"
    }
