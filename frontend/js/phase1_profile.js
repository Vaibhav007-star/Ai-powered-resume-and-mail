/**
 * Phase 1: Candidate Profile & Resume Vault Module
 */

let currentProfile = {};

document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  const resumeFileInput = document.getElementById('resumeFileInput');
  const fileNamePreview = document.getElementById('fileNamePreview');
  const uploadForm = document.getElementById('uploadForm');
  const uploadBtn = document.getElementById('uploadBtn');
  const uploadBtnText = document.getElementById('uploadBtnText');
  const resumeLabel = document.getElementById('resumeLabel');
  const autoExtractCheckbox = document.getElementById('autoExtractCheckbox');

  const addExperienceBtn = document.getElementById('addExperienceBtn');
  const addProjectBtn = document.getElementById('addProjectBtn');
  const saveProfileBtn = document.getElementById('saveProfileBtn');
  const saveProfileBtnBottom = document.getElementById('saveProfileBtnBottom');
  const reloadProfileBtn = document.getElementById('reloadProfileBtn');

  if (dropzone && resumeFileInput) {
    dropzone.addEventListener('click', () => resumeFileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('border-indigo-500'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('border-indigo-500'));
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('border-indigo-500');
      if (e.dataTransfer.files.length) {
        resumeFileInput.files = e.dataTransfer.files;
        updateFilePreview();
      }
    });
    resumeFileInput.addEventListener('change', updateFilePreview);
  }

  if (uploadForm) {
    uploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!resumeFileInput.files.length) {
        showToast("Please select a resume file (.pdf, .docx, or .txt)", "error");
        return;
      }

      const file = resumeFileInput.files[0];
      const formData = new FormData();
      formData.append("file", file);
      formData.append("label", (resumeLabel ? resumeLabel.value : "") || "General Resume");
      formData.append("auto_extract", autoExtractCheckbox ? autoExtractCheckbox.checked : true);

      if (uploadBtn) uploadBtn.disabled = true;
      if (uploadBtnText) uploadBtnText.textContent = "Processing & Extracting...";

      try {
        const res = await fetch("/api/resume/upload", { method: "POST", body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Upload failed");

        showToast(data.message || "Resume uploaded successfully!");
        if (data.extracted_profile) {
          applyExtractedDataToForm(data.extracted_profile);
          showToast("Extracted information populated into profile form!");
        }
        if (resumeFileInput) resumeFileInput.value = "";
        if (fileNamePreview) fileNamePreview.innerHTML = `Drag & drop resume or <span class="text-indigo-600 underline">browse</span>`;
        loadResumes();
      } catch (err) {
        showToast(err.message, "error");
      } finally {
        if (uploadBtn) uploadBtn.disabled = false;
        if (uploadBtnText) uploadBtnText.textContent = "Upload & Ingest";
      }
    });
  }

  if (saveProfileBtn) saveProfileBtn.addEventListener('click', saveProfile);
  if (saveProfileBtnBottom) saveProfileBtnBottom.addEventListener('click', saveProfile);
  if (reloadProfileBtn) reloadProfileBtn.addEventListener('click', () => {
    loadProfile();
    showToast("Profile reloaded from database.");
  });
  if (addExperienceBtn) addExperienceBtn.addEventListener('click', addExperienceRow);
  if (addProjectBtn) addProjectBtn.addEventListener('click', addProjectRow);
});

function updateFilePreview() {
  const resumeFileInput = document.getElementById('resumeFileInput');
  const fileNamePreview = document.getElementById('fileNamePreview');
  if (resumeFileInput && fileNamePreview) {
    if (resumeFileInput.files.length > 0) {
      const file = resumeFileInput.files[0];
      fileNamePreview.innerHTML = `<span class="font-semibold text-indigo-700">${file.name}</span> (${(file.size / 1024).toFixed(1)} KB)`;
    } else {
      fileNamePreview.innerHTML = `Drag & drop resume or <span class="text-indigo-600 underline">browse</span>`;
    }
  }
}

async function loadResumes() {
  const resumeListContainer = document.getElementById('resumeListContainer');
  const resumeCount = document.getElementById('resumeCount');
  if (!resumeListContainer) return;

  try {
    const res = await fetch("/api/resumes");
    const data = await res.json();
    const resumes = data.resumes || [];
    if (resumeCount) resumeCount.textContent = resumes.length;

    if (resumes.length === 0) {
      resumeListContainer.innerHTML = `<p class="text-xs text-slate-400 text-center py-6">No resumes uploaded yet.</p>`;
      return;
    }

    resumeListContainer.innerHTML = resumes.map(r => `
      <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs hover:border-slate-300 transition">
        <div class="truncate max-w-[200px]">
          <p class="font-semibold text-slate-800 truncate">${escapeHtml(r.filename)}</p>
          <p class="text-[11px] text-slate-500">${escapeHtml(r.label)} &bull; ${r.char_count} chars</p>
        </div>
        <button onclick="setActiveResume(${r.id})" class="px-2.5 py-1 text-[11px] font-medium rounded ${
          currentProfile.active_resume_id === r.id 
            ? 'bg-emerald-100 text-emerald-800 font-semibold' 
            : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
        }">
          ${currentProfile.active_resume_id === r.id ? 'Active' : 'Set Active'}
        </button>
      </div>
    `).join('');

  } catch (err) {
    console.error("Failed to load resumes:", err);
  }
}

async function setActiveResume(resumeId) {
  try {
    const res = await fetch(`/api/resumes/${resumeId}/set-active`, { method: "POST" });
    if (res.ok) {
      showToast(`Resume #${resumeId} is now active`);
      loadProfile();
    }
  } catch (err) {
    showToast("Failed to activate resume", "error");
  }
}

function renderExperienceRows(items = []) {
  const experienceContainer = document.getElementById('experienceContainer');
  if (!experienceContainer) return;
  experienceContainer.innerHTML = "";
  items.forEach((item, index) => {
    const div = document.createElement('div');
    div.className = "p-3 border border-slate-200 rounded-lg bg-slate-50/50 space-y-2 relative";
    div.innerHTML = `
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <div>
          <label class="block text-[11px] font-semibold text-slate-600 mb-0.5">Title / Role</label>
          <input type="text" class="exp-title w-full px-2 py-1 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-indigo-500 outline-none" value="${escapeHtml(item.title || '')}" placeholder="Software Engineer">
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-slate-600 mb-0.5">Company</label>
          <input type="text" class="exp-company w-full px-2 py-1 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-indigo-500 outline-none" value="${escapeHtml(item.company || '')}" placeholder="Acme Corp">
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-slate-600 mb-0.5">Duration</label>
          <input type="text" class="exp-duration w-full px-2 py-1 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-indigo-500 outline-none" value="${escapeHtml(item.duration || '')}" placeholder="2022 - Present">
        </div>
      </div>
      <div>
        <label class="block text-[11px] font-semibold text-slate-600 mb-0.5">Key Responsibilities / Impact</label>
        <textarea rows="2" class="exp-desc w-full px-2 py-1 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-indigo-500 outline-none">${escapeHtml(item.description || '')}</textarea>
      </div>
      <button type="button" onclick="removeExperienceRow(${index})" class="absolute top-2 right-2 text-slate-400 hover:text-red-500 p-1">
        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
      </button>
    `;
    experienceContainer.appendChild(div);
  });
  initIcons();
}

function addExperienceRow() {
  const current = gatherExperienceData();
  current.push({ title: '', company: '', duration: '', description: '' });
  renderExperienceRows(current);
}

function removeExperienceRow(index) {
  const current = gatherExperienceData();
  current.splice(index, 1);
  renderExperienceRows(current);
}

function gatherExperienceData() {
  const experienceContainer = document.getElementById('experienceContainer');
  if (!experienceContainer) return [];
  const rows = experienceContainer.querySelectorAll('div.relative');
  const data = [];
  rows.forEach(r => {
    const title = r.querySelector('.exp-title')?.value || '';
    const company = r.querySelector('.exp-company')?.value || '';
    const duration = r.querySelector('.exp-duration')?.value || '';
    const description = r.querySelector('.exp-desc')?.value || '';
    if (title || company || description) data.push({ title, company, duration, description });
  });
  return data;
}

function renderProjectRows(items = []) {
  const projectsContainer = document.getElementById('projectsContainer');
  if (!projectsContainer) return;
  projectsContainer.innerHTML = "";
  items.forEach((item, index) => {
    const div = document.createElement('div');
    div.className = "p-3 border border-slate-200 rounded-lg bg-slate-50/50 space-y-2 relative";
    div.innerHTML = `
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <div>
          <label class="block text-[11px] font-semibold text-slate-600 mb-0.5">Project Name</label>
          <input type="text" class="proj-name w-full px-2 py-1 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-indigo-500 outline-none" value="${escapeHtml(item.name || '')}" placeholder="E-Commerce API">
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-slate-600 mb-0.5">Technologies Used</label>
          <input type="text" class="proj-tech w-full px-2 py-1 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-indigo-500 outline-none" value="${escapeHtml(item.tech || '')}" placeholder="Python, FastAPI, Redis">
        </div>
      </div>
      <div>
        <label class="block text-[11px] font-semibold text-slate-600 mb-0.5">Description & Contributions</label>
        <textarea rows="2" class="proj-desc w-full px-2 py-1 text-xs border border-slate-300 rounded focus:ring-1 focus:ring-indigo-500 outline-none">${escapeHtml(item.description || '')}</textarea>
      </div>
      <button type="button" onclick="removeProjectRow(${index})" class="absolute top-2 right-2 text-slate-400 hover:text-red-500 p-1">
        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
      </button>
    `;
    projectsContainer.appendChild(div);
  });
  initIcons();
}

function addProjectRow() {
  const current = gatherProjectData();
  current.push({ name: '', tech: '', description: '' });
  renderProjectRows(current);
}

function removeProjectRow(index) {
  const current = gatherProjectData();
  current.splice(index, 1);
  renderProjectRows(current);
}

function gatherProjectData() {
  const projectsContainer = document.getElementById('projectsContainer');
  if (!projectsContainer) return [];
  const rows = projectsContainer.querySelectorAll('div.relative');
  const data = [];
  rows.forEach(r => {
    const name = r.querySelector('.proj-name')?.value || '';
    const tech = r.querySelector('.proj-tech')?.value || '';
    const description = r.querySelector('.proj-desc')?.value || '';
    if (name || tech || description) data.push({ name, tech, description });
  });
  return data;
}

function applyExtractedDataToForm(data) {
  if (!data) return;
  if (data.full_name && document.getElementById('prof_fullName')) document.getElementById('prof_fullName').value = data.full_name;
  if (data.email && document.getElementById('prof_email')) document.getElementById('prof_email').value = data.email;
  if (data.phone && document.getElementById('prof_phone')) document.getElementById('prof_phone').value = data.phone;
  if (data.degree && document.getElementById('prof_degree')) document.getElementById('prof_degree').value = data.degree;
  if (data.graduation_year && document.getElementById('prof_gradYear')) document.getElementById('prof_gradYear').value = data.graduation_year;
  if (data.experience_level && document.getElementById('prof_expLevel')) document.getElementById('prof_expLevel').value = data.experience_level;
  if (data.skills && Array.isArray(data.skills) && document.getElementById('prof_skills')) document.getElementById('prof_skills').value = data.skills.join(', ');
  if (data.certifications && Array.isArray(data.certifications) && document.getElementById('prof_certifications')) document.getElementById('prof_certifications').value = data.certifications.join(', ');
  if (data.experience && Array.isArray(data.experience)) renderExperienceRows(data.experience);
  if (data.projects && Array.isArray(data.projects)) renderProjectRows(data.projects);
}

async function loadProfile() {
  try {
    const res = await fetch("/api/profile");
    const data = await res.json();
    currentProfile = data.profile || {};

    if (document.getElementById('prof_fullName')) document.getElementById('prof_fullName').value = currentProfile.full_name || '';
    if (document.getElementById('prof_email')) document.getElementById('prof_email').value = currentProfile.email || '';
    if (document.getElementById('prof_phone')) document.getElementById('prof_phone').value = currentProfile.phone || '';
    if (document.getElementById('prof_degree')) document.getElementById('prof_degree').value = currentProfile.degree || '';
    if (document.getElementById('prof_gradYear')) document.getElementById('prof_gradYear').value = currentProfile.graduation_year || '';
    if (document.getElementById('prof_workMode')) document.getElementById('prof_workMode').value = currentProfile.work_mode || 'Any';
    if (document.getElementById('prof_expLevel')) document.getElementById('prof_expLevel').value = currentProfile.experience_level || 'Mid';

    const skills = currentProfile.skills || [];
    if (document.getElementById('prof_skills')) document.getElementById('prof_skills').value = Array.isArray(skills) ? skills.join(', ') : '';

    const certs = currentProfile.certifications || [];
    if (document.getElementById('prof_certifications')) document.getElementById('prof_certifications').value = Array.isArray(certs) ? certs.join(', ') : '';

    const roles = currentProfile.preferred_roles || [];
    if (document.getElementById('prof_targetRoles')) document.getElementById('prof_targetRoles').value = Array.isArray(roles) ? roles.join(', ') : '';

    const locs = currentProfile.preferred_locations || [];
    if (document.getElementById('prof_targetLocations')) document.getElementById('prof_targetLocations').value = Array.isArray(locs) ? locs.join(', ') : '';

    renderExperienceRows(currentProfile.experience || []);
    renderProjectRows(currentProfile.projects || []);
    loadResumes();

  } catch (err) {
    console.error("Failed to load profile:", err);
  }
}

async function saveProfile() {
  const skillsRaw = document.getElementById('prof_skills')?.value || '';
  const certsRaw = document.getElementById('prof_certifications')?.value || '';
  const rolesRaw = document.getElementById('prof_targetRoles')?.value || '';
  const locsRaw = document.getElementById('prof_targetLocations')?.value || '';

  const payload = {
    full_name: (document.getElementById('prof_fullName')?.value || '').trim(),
    email: (document.getElementById('prof_email')?.value || '').trim(),
    phone: (document.getElementById('prof_phone')?.value || '').trim(),
    degree: (document.getElementById('prof_degree')?.value || '').trim(),
    graduation_year: (document.getElementById('prof_gradYear')?.value || '').trim(),
    work_mode: document.getElementById('prof_workMode')?.value || 'Any',
    experience_level: document.getElementById('prof_expLevel')?.value || 'Mid',
    skills: skillsRaw.split(',').map(s => s.trim()).filter(Boolean),
    certifications: certsRaw.split(',').map(s => s.trim()).filter(Boolean),
    preferred_roles: rolesRaw.split(',').map(s => s.trim()).filter(Boolean),
    preferred_locations: locsRaw.split(',').map(s => s.trim()).filter(Boolean),
    experience: gatherExperienceData(),
    projects: gatherProjectData(),
    active_resume_id: currentProfile.active_resume_id || null
  };

  try {
    const res = await fetch("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to save profile");

    currentProfile = data.profile;
    showToast("Profile saved to SQLite successfully!");
  } catch (err) {
    showToast(err.message, "error");
  }
}
