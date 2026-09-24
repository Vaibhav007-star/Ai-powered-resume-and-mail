# AI-Powered Resume Matcher & Cold Email Assistant 🚀

An end-to-end, human-in-the-loop AI platform designed to evaluate candidate qualifications honestly against job postings, extract structured skills from resumes, match opportunities (including live automated internship discovery), craft truthful cold application emails with zero hallucinations, and manage the full application lifecycle.

---

## 🌟 Key Highlights & Architectural Flow

The platform strictly adheres to a **5-Phase Human Gatekeeper Architecture**:

```
Phase 1: Resume & Profile Grounding
   │
   ▼
Phase 2: Job Analysis & Live Discovery (Delhi NCR / Remote)
   │
   ▼
Phase 3: Transparent Fit Scorecard & Grounded Pitch Studio
   │
   ▼
Phase 4: Human Review & Approval Station (Dry-Run Safe Mode)
   │
   ▼
Phase 5: Application Lifecycle & Tracking Dashboard
```

1. **Phase 1 — Candidate Profile & Resume Hub**:
   - Multi-format resume parsing (`.pdf`, `.docx`, `.txt`).
   - Grounded skill, experience, and project extraction stored in local SQLite database.
   - Preserves authentic candidate identity with zero invented credentials.

2. **Phase 2 — Dual-Mode Job Intake & Live Discovery**:
   - **Manual Mode**: Paste raw job descriptions from any career portal or email.
   - **Automated Discovery**: Real-time aggregator querying live internships across **Delhi**, **Noida**, and **Gurugram** (Delhi NCR) or Remote India.
   - **College Criteria Enforcement**: Filters listings to 3–6 month duration and minimum stipends &ge; ₹10,000/month (INR 10k+).
   - Strict qualification decomposition separating **Mandatory** vs. **Preferred/Bonus** requirements.

3. **Phase 3 — Transparent Fit Scorecard & Pitch Studio**:
   - Multi-dimensional qualification evaluation: Education, Experience, Location, and Skills.
   - Transparent fit score (0–100%) highlighting matched skills, bonus skills, and qualification gaps.
   - Grounded email generator that cites real projects and truthful achievements.
   - Includes **Recruiter Email Guidance**: 1-click LinkedIn HR search, corporate domain suggestions, and 1-click job portal application links.

4. **Phase 4 — Strict Human Approval & Dispatch**:
   - Human-in-the-loop gatekeeper: no email is ever sent without explicit candidate approval.
   - Built-in duplicate application protection guarding against accidental double submissions.
   - Default **Dry-Run Safe Mode**: outputs `.eml` preview files locally to inspect exact formatting without dispatching real emails.

5. **Phase 5 — Application Lifecycle Cockpit**:
   - Real-time application tracking across statuses: `Draft`, `Ready for Review`, `Sent`, `Follow-up`, `Interview`, `Offer`, `Rejected`, `Closed`.
   - Metrics KPI cards and status timeline management.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, [FastAPI](https://fastapi.tiangolo.com/), Uvicorn, SQLite3, PyPDF, python-docx
- **LLM Engine**: OpenAI / Groq (`openai/gpt-oss-120b`, Groq LLaMA models) / Google Gemini API support with heuristic rule-based fallbacks
- **Frontend**: Clean Vanilla JavaScript SPA with [Tailwind CSS](https://tailwindcss.com/) & [Lucide Icons](https://lucide.dev/)
- **Testing**: Pytest with automated coverage for all 5 phases (24/24 unit tests)

---

## 🚀 Quickstart Guide

### 1. Clone the Repository
```bash
git clone https://github.com/Vaibhav007-star/Ai-powered-resume-and-mail.git
cd Ai-powered-resume-and-mail
```

### 2. Set Up Virtual Environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your API keys:
```env
# Choose your preferred provider (Groq, OpenAI, or Gemini):
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=openai/gpt-oss-120b

# App Configurations
APP_HOST=127.0.0.1
APP_PORT=8000
DRY_RUN=True
```

### 5. Launch the Application
```bash
python run.py
```
Open your browser at `http://127.0.0.1:8000`.

---

## 🧪 Running Automated Tests

Run the full automated test suite verifying all 5 phases:
```bash
pytest tests/ -v
```

---

## 🛡️ Privacy & Safety Principles

- **Zero Hallucination Guarantee**: The application generator strictly grounds pitches in resume facts extracted in Phase 1.
- **Dry-Run by Default**: Safeguards against unintentional emails during testing or setup.
- **Human Gatekeeper**: Automated email sending without explicit human checkbox review is strictly disabled at the backend API level.

---

## 📄 License

MIT License. Designed and engineered for authentic, high-impact job and internship applications.
