import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory is the project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

# App configurations
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", 8000))

# Storage paths
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
UPLOADS_DIR = BASE_DIR / os.getenv("UPLOADS_DIR", "uploads/resumes")
DB_PATH = BASE_DIR / os.getenv("DB_PATH", "data/assistant.db")

# Ensure required directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip().strip("'\"")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip().strip("'\"")
GROQ_API_KEY = (os.getenv("GROQ_API_KEY", "") or os.getenv("GROK_API_KEY", "")).strip().strip("'\"")
GROK_API_KEY = GROQ_API_KEY  # Alias for grok/groq compatibility
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip().strip("'\"") or None
LLM_MODEL = os.getenv("LLM_MODEL", "").strip().strip("'\"")

# If Groq key is present, default to Groq's OpenAI-compatible endpoint and gpt-oss-120b
if GROQ_API_KEY:
    if not OPENAI_BASE_URL:
        OPENAI_BASE_URL = "https://api.groq.com/openai/v1"
    if not LLM_MODEL:
        LLM_MODEL = "openai/gpt-oss-120b"

# Email Configuration
DRY_RUN = os.getenv("DRY_RUN", "True").lower() in ("true", "1", "yes")

# Optional Job Search Provider Credentials
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "").strip().strip("'\"")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "").strip().strip("'\"")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "").strip().strip("'\"")

