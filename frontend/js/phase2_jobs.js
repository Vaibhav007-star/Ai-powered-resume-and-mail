/**
 * Phase 2: Job Analysis & Automated Discovery Module
 */

let currentJobIngestMode = 'manual';
let discoveredJobsCache = [];

document.addEventListener('DOMContentLoaded', () => {
  const jobForm = document.getElementById('jobForm');
  if (jobForm) {
    jobForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = (document.getElementById('job_description')?.value || '').trim();
      if (!text) {
        showToast("Please provide the job description text.", "error");
        return;
      }

      const payload = {
        job_description: text,
        company_name: (document.getElementById('job_companyName')?.value || '').trim(),
        job_title: (document.getElementById('job_title')?.value || '').trim(),
        company_email: (document.getElementById('job_companyEmail')?.value || '').trim(),
        location: (document.getElementById('job_location')?.value || '').trim(),
        job_url: (document.getElementById('job_url')?.value || '').trim()
      };

      const analyzeJobBtn = document.getElementById('analyzeJobBtn');
      const analyzeJobBtnText = document.getElementById('analyzeJobBtnText');
      if (analyzeJobBtn) analyzeJobBtn.disabled = true;
      if (analyzeJobBtnText) analyzeJobBtnText.textContent = "Analyzing & Partitioning...";

      try {
        const res = await fetch("/api/jobs/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Job analysis failed");

        showToast("Job analyzed and qualifications partitioned!");
        currentJob = data.job;
        displayJobAnalysis(currentJob);
        loadJobsList();

      } catch (err) {
        showToast(err.message, "error");
      } finally {
        if (analyzeJobBtn) analyzeJobBtn.disabled = false;
        if (analyzeJobBtnText) analyzeJobBtnText.textContent = "Analyze & Extract Qualifications";
      }
    });
  }
});

function loadSampleJobPosting() {
  if (document.getElementById('job_companyName')) document.getElementById('job_companyName').value = "NeuroScale AI Labs";
  if (document.getElementById('job_title')) document.getElementById('job_title').value = "Data Science & AI Engineer Intern";
  if (document.getElementById('job_companyEmail')) document.getElementById('job_companyEmail').value = "careers@neuroscale.ai";
  if (document.getElementById('job_location')) document.getElementById('job_location').value = "Remote / Bangalore (Hybrid)";
  if (document.getElementById('job_url')) document.getElementById('job_url').value = "https://neuroscale.ai/careers/ds-ai-intern";
  if (document.getElementById('job_description')) {
    document.getElementById('job_description').value = `About NeuroScale AI Labs:
We build state-of-the-art Generative AI applications, predictive machine learning models, and intelligent automated workflows for data-driven companies.

Role Overview:
We are seeking an enthusiastic Data Science & AI Intern (3rd or 4th year student) to join our machine learning team. You will collaborate with research engineers to process multimodal datasets, train ML models, and experiment with Generative AI and Large Language Models (LLMs).

Required Qualifications (Must-Have):
- Currently pursuing a Bachelor's degree in Data Science, Artificial Intelligence, Computer Science, or related field
- Strong hands-on coding proficiency in Python and data science libraries (Pandas, NumPy, Scikit-Learn)
- Solid foundational knowledge of Machine Learning and Deep Learning algorithms
- Hands-on experience with deep learning frameworks (PyTorch or TensorFlow)
- Experience writing SQL queries and using Git for version control

Preferred Qualifications (Nice-to-Have):
- Hands-on project experience with Generative AI, LLMs, or prompt engineering
- Familiarity with LangChain, LlamaIndex, or Vector Databases (FAISS / ChromaDB)
- Exposure to Natural Language Processing (NLP) or Computer Vision techniques
- Active GitHub repository showcasing coursework or personal AI/ML projects`;
  }
  showToast("Sample Data Science & AI Intern job loaded!");
}

function setJobIngestMode(mode) {
  currentJobIngestMode = mode;
  const tabManual = document.getElementById('tabMode_manual');
  const tabAutomated = document.getElementById('tabMode_automated');
  const secManual = document.getElementById('section_manualIngest');
  const secAutomated = document.getElementById('section_automatedSearch');

  if (mode === 'manual') {
    if (tabManual) tabManual.className = "flex-1 py-1.5 px-3 rounded-md bg-white text-slate-900 shadow-xs flex items-center justify-center space-x-1.5 transition cursor-pointer";
    if (tabAutomated) tabAutomated.className = "flex-1 py-1.5 px-3 rounded-md text-slate-600 hover:text-slate-900 flex items-center justify-center space-x-1.5 transition cursor-pointer";
    if (secManual) secManual.classList.remove('hidden');
    if (secAutomated) secAutomated.classList.add('hidden');
  } else {
    if (tabAutomated) tabAutomated.className = "flex-1 py-1.5 px-3 rounded-md bg-white text-slate-900 shadow-xs flex items-center justify-center space-x-1.5 transition cursor-pointer";
    if (tabManual) tabManual.className = "flex-1 py-1.5 px-3 rounded-md text-slate-600 hover:text-slate-900 flex items-center justify-center space-x-1.5 transition cursor-pointer";
    if (secManual) secManual.classList.add('hidden');
    if (secAutomated) secAutomated.classList.remove('hidden');

    const queryInput = document.getElementById('liveSearchQuery');
    if (queryInput && (!queryInput.value || queryInput.value === 'Data Science Intern') && typeof currentProfile !== 'undefined' && currentProfile?.preferred_roles?.length) {
      queryInput.value = currentProfile.preferred_roles[0];
    }
  }
  initIcons();
}

async function searchLiveJobs() {
  const queryInput = document.getElementById('liveSearchQuery');
  const searchBtn = document.getElementById('executeLiveSearchBtn');
  const searchBtnText = document.getElementById('executeLiveSearchBtnText');
  const resultsContainer = document.getElementById('liveSearchResultsContainer');
  const resultsHeader = document.getElementById('liveSearchResultsHeader');
  const resultsCount = document.getElementById('liveResultsCount');

  const query = (queryInput?.value || "data science").trim();
  const location = (document.getElementById('liveSearchLocation')?.value || "delhi_ncr").trim();
  const minStipend = document.getElementById('liveSearchMinStipend')?.value || "10000";
  const limit = 25;

  if (searchBtn) searchBtn.disabled = true;
  if (searchBtnText) searchBtnText.textContent = "Querying Delhi NCR Internships...";
  if (resultsContainer) {
    resultsContainer.innerHTML = `
      <div class="p-8 text-center text-xs text-slate-500 space-y-2">
        <div class="inline-block animate-spin w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full mb-2"></div>
        <p>Finding Data Science & AI internships in Delhi, Noida, Gurugram (>= ₹10k/mo)...</p>
      </div>
    `;
  }

  try {
    const url = `/api/jobs/search?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}&min_stipend=${minStipend}&limit=${limit}`;
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to fetch live jobs");

    discoveredJobsCache = data.jobs || [];
    if (resultsHeader) resultsHeader.classList.remove('hidden');
    if (resultsCount) resultsCount.textContent = `${discoveredJobsCache.length} Delhi NCR Openings Found`;

    if (discoveredJobsCache.length === 0) {
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="p-8 text-center text-xs text-slate-500 border border-dashed border-slate-200 rounded-lg">
            No live openings found for "${escapeHtml(query)}" in ${escapeHtml(location)} with stipend >= ₹${minStipend}/mo. Try broadening your search keywords.
          </div>
        `;
      }
      return;
    }

    if (resultsContainer) {
      resultsContainer.innerHTML = discoveredJobsCache.map((job, idx) => {
        const stipendBadge = job.stipend 
          ? `<span class="text-[10px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded flex items-center space-x-1"><i data-lucide="circle-dollar-sign" class="w-3 h-3"></i><span>${escapeHtml(job.stipend)}</span></span>` 
          : '';
        const durationBadge = job.duration 
          ? `<span class="text-[10px] font-bold text-sky-800 bg-sky-50 border border-sky-200 px-2 py-0.5 rounded flex items-center space-x-1"><i data-lucide="calendar" class="w-3 h-3"></i><span>${escapeHtml(job.duration)}</span></span>` 
          : '';
        const locBadge = `<span class="text-[10px] font-semibold text-slate-700 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded flex items-center space-x-1"><i data-lucide="map-pin" class="w-3 h-3"></i><span>${escapeHtml(job.location)}</span></span>`;

        const descSnippet = (job.description || '').replace(/\s+/g, ' ').slice(0, 140) + '...';

        return `
          <div class="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-2 hover:border-indigo-300 transition" id="jobCard_${idx}">
            <div class="flex items-start justify-between gap-2">
              <div>
                <h4 class="font-bold text-slate-900 text-xs leading-snug">${escapeHtml(job.title)}</h4>
                <p class="text-indigo-600 font-semibold text-[11px]">${escapeHtml(job.company_name)}</p>
              </div>
              <span class="text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded shrink-0">
                ${escapeHtml(job.source)}
              </span>
            </div>
            <div class="flex flex-wrap items-center gap-1.5 pt-0.5">
              ${locBadge}
              ${durationBadge}
              ${stipendBadge}
            </div>
            <p class="text-[11px] text-slate-600 line-clamp-2 leading-relaxed">
              ${escapeHtml(descSnippet)}
            </p>
            <div class="flex items-center justify-between pt-1 border-t border-slate-200/60">
              <span class="text-[10px] text-slate-400 font-medium">College Criteria: 3-6 mo &bull; &gt;= ₹10k/mo</span>
              <button type="button" onclick="importDiscoveredJob(${idx})" id="importBtn_${idx}" class="px-2.5 py-1 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-md shadow-2xs flex items-center space-x-1 transition cursor-pointer">
                <i data-lucide="sparkles" class="w-3 h-3"></i>
                <span>Import & Analyze</span>
              </button>
            </div>
          </div>
        `;
      }).join('');
    }

    initIcons();

  } catch (err) {
    showToast(err.message, "error");
    if (resultsContainer) {
      resultsContainer.innerHTML = `
        <div class="p-6 text-center text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-lg">
          Error searching jobs: ${escapeHtml(err.message)}
        </div>
      `;
    }
  } finally {
    if (searchBtn) searchBtn.disabled = false;
    if (searchBtnText) searchBtnText.textContent = "Find Delhi NCR Internships";
  }
}

async function importDiscoveredJob(index) {
  const job = discoveredJobsCache[index];
  if (!job) return;

  const btn = document.getElementById(`importBtn_${index}`);
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>Importing...</span>`;
  }

  const fullDesc = `Job Title: ${job.title}\nCompany: ${job.company_name}\nLocation: ${job.location}\n\nJob Description:\n${job.description}`;

  const payload = {
    job_description: fullDesc,
    company_name: job.company_name || "",
    job_title: job.title || "",
    location: job.location || "",
    job_url: job.job_url || "",
    company_email: ""
  };

  try {
    const res = await fetch("/api/jobs/import-and-analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Import & analysis failed");

    showToast(`Imported "${job.title}" & partitioned qualifications!`);
    currentJob = data.job;
    displayJobAnalysis(currentJob);
    loadJobsList();

    if (btn) {
      btn.className = "px-2.5 py-1 text-xs font-semibold text-emerald-800 bg-emerald-100 rounded-md flex items-center space-x-1";
      btn.innerHTML = `<i data-lucide="check" class="w-3 h-3"></i><span>Imported!</span>`;
      initIcons();
    }

  } catch (err) {
    showToast(err.message, "error");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="sparkles" class="w-3 h-3"></i><span>Import & Analyze</span>`;
      initIcons();
    }
  }
}

function displayJobAnalysis(job) {
  if (!job) return;
  const noJobState = document.getElementById('noJobSelectedState');
  const activeCard = document.getElementById('activeJobDisplayCard');
  if (noJobState) noJobState.classList.add('hidden');
  if (activeCard) activeCard.classList.remove('hidden');

  if (document.getElementById('display_jobTitle')) document.getElementById('display_jobTitle').textContent = job.job_title || "Job Title";
  if (document.getElementById('display_companyName')) document.getElementById('display_companyName').textContent = job.company_name || "Company";
  if (document.getElementById('display_locationText')) document.getElementById('display_locationText').textContent = job.location || "Location not specified";
  if (document.getElementById('display_workModeBadge')) document.getElementById('display_workModeBadge').textContent = job.required_qualifications?.location_work_mode || "Any Mode";
  if (document.getElementById('display_summary')) document.getElementById('display_summary').textContent = job.summary || "No summary available.";

  const req = job.required_qualifications || {};
  const pref = job.preferred_qualifications || {};

  if (document.getElementById('req_degreeBadge')) document.getElementById('req_degreeBadge').textContent = req.degree || "Not specified";
  if (document.getElementById('req_expBadge')) document.getElementById('req_expBadge').textContent = req.experience || "Not specified";

  const reqSkillsBox = document.getElementById('req_skillsContainer');
  if (reqSkillsBox) {
    reqSkillsBox.innerHTML = "";
    const allReqSkills = [...(req.skills || []), ...(req.technologies || [])];
    allReqSkills.forEach(s => {
      const badge = document.createElement('span');
      badge.className = "text-xs font-semibold px-2.5 py-1 rounded-md bg-rose-50 text-rose-800 border border-rose-200 flex items-center space-x-1";
      badge.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-rose-600 inline"></i> <span>${escapeHtml(s)}</span>`;
      reqSkillsBox.appendChild(badge);
    });
  }

  const prefSkillsBox = document.getElementById('pref_skillsContainer');
  if (prefSkillsBox) {
    prefSkillsBox.innerHTML = "";
    const allPrefSkills = [...(pref.skills || []), ...(pref.technologies || [])];
    allPrefSkills.forEach(s => {
      const badge = document.createElement('span');
      badge.className = "text-xs font-semibold px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-800 border border-indigo-200 flex items-center space-x-1";
      badge.innerHTML = `<i data-lucide="star" class="w-3 h-3 text-indigo-600 inline"></i> <span>${escapeHtml(s)}</span>`;
      prefSkillsBox.appendChild(badge);
    });
  }

  if (document.getElementById('pref_expBadge')) document.getElementById('pref_expBadge').textContent = pref.experience || "None mentioned";

  const otherBox = document.getElementById('pref_otherContainer');
  if (otherBox) {
    const otherList = pref.other || [];
    otherBox.innerHTML = otherList.map(o => `<div>&bull; ${escapeHtml(o)}</div>`).join('');
  }

  initIcons();
}

async function loadJobsList() {
  const jobsListContainer = document.getElementById('jobsListContainer');
  const jobsCount = document.getElementById('jobsCount');
  try {
    const res = await fetch("/api/jobs");
    const data = await res.json();
    allJobs = data.jobs || [];
    if (jobsCount) jobsCount.textContent = allJobs.length;

    if (!jobsListContainer) return;

    if (allJobs.length === 0) {
      jobsListContainer.innerHTML = `<p class="text-xs text-slate-400 text-center py-6">No jobs analyzed yet.</p>`;
      return;
    }

    jobsListContainer.innerHTML = allJobs.map(j => `
      <div onclick="selectJob(${j.id})" class="p-3 rounded-lg border text-xs cursor-pointer transition ${
        currentJob && currentJob.id === j.id
          ? 'bg-sky-50 border-sky-300 shadow-xs'
          : 'bg-slate-50 border-slate-200 hover:border-slate-300'
      }">
        <div class="flex items-center justify-between">
          <span class="font-bold text-slate-900 truncate">${escapeHtml(j.job_title)}</span>
          <span class="text-[10px] text-slate-400">${new Date(j.created_at).toLocaleDateString()}</span>
        </div>
        <p class="text-indigo-600 font-medium text-[11px] truncate">${escapeHtml(j.company_name)}</p>
      </div>
    `).join('');

    if (typeof populateP3JobDropdown === 'function') populateP3JobDropdown();

  } catch (err) {
    console.error("Failed to load jobs:", err);
  }
}

async function selectJob(jobId) {
  try {
    const res = await fetch(`/api/jobs/${jobId}`);
    const data = await res.json();
    currentJob = data.job;
    displayJobAnalysis(currentJob);
    loadJobsList();
  } catch (err) {
    showToast("Failed to fetch job", "error");
  }
}

async function deleteCurrentJob() {
  if (!currentJob) return;
  if (!confirm(`Delete ${currentJob.job_title} at ${currentJob.company_name}?`)) return;

  try {
    const res = await fetch(`/api/jobs/${currentJob.id}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Job removed.");
      currentJob = null;
      const activeCard = document.getElementById('activeJobDisplayCard');
      const noJobState = document.getElementById('noJobSelectedState');
      if (activeCard) activeCard.classList.add('hidden');
      if (noJobState) noJobState.classList.remove('hidden');
      loadJobsList();
    }
  } catch (err) {
    showToast("Failed to delete job", "error");
  }
}
