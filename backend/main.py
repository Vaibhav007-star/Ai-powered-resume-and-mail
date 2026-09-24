from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.core.config import BASE_DIR
from backend.core.database import init_db
from backend.routers import auth, profile, jobs, match, applications
from backend.routers.applications import VALID_APPLICATION_STATUSES
from backend.services.job_fetcher import fetch_open_jobs

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="AI-Powered Personalized Job Application Assistant",
    description="Local, reliable, and truth-preserving assistant for job seekers.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = BASE_DIR / "frontend"
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Include Modular FastAPI Routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(match.router)
app.include_router(applications.router)

@app.get("/", response_class=FileResponse)
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
    return FileResponse(index_path)

@app.get("/pages/{page_name}", response_class=FileResponse)
def serve_page(page_name: str):
    page_path = FRONTEND_DIR / "pages" / page_name
    if not page_path.exists():
        raise HTTPException(status_code=404, detail=f"Page {page_name} not found")
    return FileResponse(page_path)

@app.get("/api/health")
def health_check():
    from backend.core.llm import is_llm_configured, get_active_model
    return {
        "status": "healthy",
        "phase": "Enterprise Pro-Grade Modular 5-Phase Environment",
        "ai_configured": is_llm_configured(),
        "model": get_active_model()
    }

@app.exception_handler(Exception)
async def user_friendly_exception_handler(request, exc):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "detail": exc.detail}
        )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "detail": "An unexpected error occurred while processing your request. Please verify inputs or consult system logs."
        }
    )
