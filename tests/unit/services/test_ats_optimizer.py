import pytest
from backend.services.ats_optimizer import analyze_ats_optimization, calculate_cosine_similarity, tokenize

def test_tokenize_and_cosine_similarity():
    text1 = "Python Machine Learning PyTorch Data Science SQL"
    text2 = "Python Deep Learning PyTorch Data Science PostgreSQL"
    
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    assert "python" in tokens1
    assert "pytorch" in tokens2
    
    from collections import Counter
    vec1 = Counter(tokens1)
    vec2 = Counter(tokens2)
    similarity = calculate_cosine_similarity(vec1, vec2)
    assert similarity > 0.5

def test_analyze_ats_optimization():
    profile = {
        "full_name": "Vaibhav",
        "degree": "B.Sc Data Science",
        "skills": ["Python", "PyTorch", "SQL", "Pandas"],
        "projects": [{"name": "AI Assistant", "tech": "Python, FastAPI", "description": "Built AI assistant"}]
    }
    job = {
        "raw_description": "We are seeking a Data Scientist skilled in Python, PyTorch, Kubernetes, Docker, and SQL.",
        "required_qualifications": {
            "skills": ["Python", "PyTorch", "SQL"],
            "technologies": ["Kubernetes", "Docker"]
        }
    }
    result = analyze_ats_optimization(profile, job)
    assert "ats_score" in result
    assert result["ats_score"] > 0
    assert "matched_keywords" in result
    assert "missing_keywords" in result
    assert any("Kubernetes" in k or "Docker" in k for k in result["missing_keywords"])
