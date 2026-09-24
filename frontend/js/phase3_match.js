/**
 * Phase 3: Match Evaluation & Email Studio Module
 */

function populateP3JobDropdown() {
  const select = document.getElementById('p3_jobSelect');
  if (!select) return;
  select.innerHTML = '<option value="">-- Select an Analyzed Job --</option>';
  allJobs.forEach(j => {
    const opt = document.createElement('option');
    opt.value = j.id;
    opt.textContent = `${j.job_title} @ ${j.company_name}`;
    select.appendChild(opt);
  });
  if (currentJob) select.value = currentJob.id;
}

function onP3JobSelected(jobId) {
  if (!jobId) {
    const grid = document.getElementById('p3_contentGrid');
    const empty = document.getElementById('p3_emptyState');
    if (grid) grid.classList.add('hidden');
    if (empty) empty.classList.remove('hidden');
    return;
  }
  const found = allJobs.find(j => j.id == jobId);
  if (found) currentJob = found;
  loadApplicationForJob(jobId);
}

async function matchAndGenerateForActiveJob() {
  if (!currentJob) {
    showToast("Please select or analyze a job first.", "error");
    return;
  }
  const triggerBtn = document.getElementById('triggerMatchBtn');
  const triggerBtnText = document.getElementById('triggerMatchBtnText');
  if (triggerBtn) triggerBtn.disabled = true;
  if (triggerBtnText) triggerBtnText.textContent = "Matching & Drafting...";

  try {
    const res = await fetch("/api/email/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: currentJob.id })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Match generation failed");

    showToast("Candidate fit evaluated & truthful email drafted!");
    switchTab(3);
    displayMatchAndEmail(data);
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    if (triggerBtn) triggerBtn.disabled = false;
    if (triggerBtnText) triggerBtnText.textContent = "Match Candidate & Draft Email";
  }
}

async function loadApplicationForJob(jobId) {
  try {
    const res = await fetch(`/api/jobs/${jobId}/application`);
    const data = await res.json();
    if (data.status === "success" && data.application) {
      currentApplication = data.application;
      displayMatchAndEmail({
        match: currentApplication.match_summary,
        email: {
          subject: currentApplication.email_subject,
          body: currentApplication.email_body,
          grounded_facts: currentApplication.match_summary?.grounded_facts || []
        },
        attached_resume: data.attached_resume,
        application_id: currentApplication.id
      });
    } else {
      const genRes = await fetch("/api/email/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId })
      });
      const genData = await genRes.json();
      displayMatchAndEmail(genData);
    }
  } catch (err) {
    console.error("Error loading application draft:", err);
  }
}

function runMatchForSelectedP3Job() {
  const jobId = document.getElementById('p3_jobSelect')?.value;
  if (!jobId) {
    showToast("Please select a job first.", "error");
    return;
  }
  matchAndGenerateForActiveJob();
}

function regenerateEmailForSelectedP3Job() {
  runMatchForSelectedP3Job();
}

function displayMatchAndEmail(data) {
  const emptyState = document.getElementById('p3_emptyState');
  const contentGrid = document.getElementById('p3_contentGrid');
  if (emptyState) emptyState.classList.add('hidden');
  if (contentGrid) contentGrid.classList.remove('hidden');

  const match = data.match || {};
  const email = data.email || {};

  const score = match.match_score || 0;
  if (document.getElementById('match_scoreValue')) document.getElementById('match_scoreValue').textContent = `${score}%`;
  const bar = document.getElementById('match_scoreBar');
  if (bar) {
    bar.style.width = `${score}%`;
    if (score >= 75) bar.className = "bg-emerald-500 h-2.5 rounded-full transition-all duration-500";
    else if (score >= 50) bar.className = "bg-amber-500 h-2.5 rounded-full transition-all duration-500";
    else bar.className = "bg-rose-500 h-2.5 rounded-full transition-all duration-500";
  }

  const edu = match.education || {};
  const exp = match.experience || {};
  const loc = match.location || {};

  const eduBadge = document.getElementById('dim_eduBadge');
  if (eduBadge) {
    eduBadge.textContent = edu.status || "PASS";
    eduBadge.className = edu.status === "PASS" ? "font-bold px-2 py-0.5 rounded text-[11px] bg-emerald-100 text-emerald-800" : "font-bold px-2 py-0.5 rounded text-[11px] bg-amber-100 text-amber-800";
  }

  const expBadge = document.getElementById('dim_expBadge');
  if (expBadge) {
    expBadge.textContent = exp.status || "PASS";
    expBadge.className = exp.status === "PASS" ? "font-bold px-2 py-0.5 rounded text-[11px] bg-emerald-100 text-emerald-800" : "font-bold px-2 py-0.5 rounded text-[11px] bg-amber-100 text-amber-800";
  }

  const locBadge = document.getElementById('dim_locBadge');
  if (locBadge) {
    locBadge.textContent = loc.status || "PASS";
    locBadge.className = loc.status === "PASS" ? "font-bold px-2 py-0.5 rounded text-[11px] bg-emerald-100 text-emerald-800" : "font-bold px-2 py-0.5 rounded text-[11px] bg-amber-100 text-amber-800";
  }

  if (document.getElementById('dim_modeBadge')) document.getElementById('dim_modeBadge').textContent = loc.job_mode || "Any";
  if (document.getElementById('match_rationaleText')) document.getElementById('match_rationaleText').textContent = match.explanation || "No rationale available.";

  const skills = match.skills || {};
  if (document.getElementById('match_skillsSummary')) document.getElementById('match_skillsSummary').textContent = skills.summary || "";

  const matchedBox = document.getElementById('matched_reqSkills');
  if (matchedBox) {
    matchedBox.innerHTML = "";
    (skills.matched_required || []).forEach(s => {
      const span = document.createElement('span');
      span.className = "text-xs font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center space-x-1";
      span.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-600 inline"></i> <span>${escapeHtml(s)}</span>`;
      matchedBox.appendChild(span);
    });
    if ((skills.matched_required || []).length === 0) {
      matchedBox.innerHTML = `<span class="text-xs text-slate-400 italic">No mandatory skills matched yet</span>`;
    }
  }

  const missingBox = document.getElementById('missing_reqSkills');
  if (missingBox) {
    missingBox.innerHTML = "";
    (skills.missing_required || []).forEach(s => {
      const span = document.createElement('span');
      span.className = "text-xs font-semibold px-2 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-200 flex items-center space-x-1";
      span.innerHTML = `<i data-lucide="x" class="w-3 h-3 text-rose-600 inline"></i> <span>${escapeHtml(s)}</span>`;
      missingBox.appendChild(span);
    });
    if ((skills.missing_required || []).length === 0) {
      missingBox.innerHTML = `<span class="text-xs text-emerald-700 italic">All mandatory skills present in your profile!</span>`;
    }
  }

  const prefBox = document.getElementById('matched_prefSkills');
  if (prefBox) {
    prefBox.innerHTML = "";
    (skills.matched_preferred || []).forEach(s => {
      const span = document.createElement('span');
      span.className = "text-xs font-semibold px-2 py-0.5 rounded bg-indigo-50 text-indigo-800 border border-indigo-200 flex items-center space-x-1";
      span.innerHTML = `<i data-lucide="star" class="w-3 h-3 text-indigo-600 inline"></i> <span>${escapeHtml(s)}</span>`;
      prefBox.appendChild(span);
    });
  }

  const projBox = document.getElementById('p3_relevantProjects');
  if (projBox) {
    projBox.innerHTML = "";
    const projs = match.relevant_projects || [];
    if (projs.length === 0) {
      projBox.innerHTML = `<p class="text-slate-400 italic">No specific projects explicitly matched the required tools.</p>`;
    } else {
      projs.forEach(p => {
        const div = document.createElement('div');
        div.className = "p-2.5 bg-slate-50 border border-slate-200 rounded-lg";
        div.innerHTML = `
          <div class="font-bold text-slate-800">${escapeHtml(p.project_name)}</div>
          <div class="text-[11px] text-indigo-600 font-medium">Demonstrates: ${escapeHtml((p.matched_skills || []).join(', '))}</div>
          <div class="text-slate-500 mt-1">${escapeHtml(p.summary)}</div>
        `;
        projBox.appendChild(div);
      });
    }
  }

  const effectiveP3Recipient = (currentJob && currentJob.company_email) || "";
  if (document.getElementById('email_recipient')) document.getElementById('email_recipient').value = effectiveP3Recipient;
  if (document.getElementById('email_subject')) document.getElementById('email_subject').value = email.subject || "";
  if (document.getElementById('email_body')) document.getElementById('email_body').value = email.body || "";
  updateP3EmailGuidance(effectiveP3Recipient);

  const factsBox = document.getElementById('email_groundedFacts');
  if (factsBox) {
    factsBox.innerHTML = "";
    const facts = email.grounded_facts || [];
    facts.forEach(f => {
      const span = document.createElement('span');
      span.className = "px-2 py-0.5 bg-white border border-slate-200 rounded text-[11px] font-medium text-slate-700";
      span.textContent = f;
      factsBox.appendChild(span);
    });
  }

  const resName = data.attached_resume?.filename || "Primary Stored Resume";
  if (document.getElementById('email_attachedResumeName')) document.getElementById('email_attachedResumeName').textContent = resName;

  currentApplication = { id: data.application_id };
  initIcons();
}

async function saveDraftEdits() {
  if (!currentApplication || !currentApplication.id) {
    showToast("No active application draft to save.", "error");
    return;
  }
  const payload = {
    email_subject: (document.getElementById('email_subject')?.value || '').trim(),
    email_body: (document.getElementById('email_body')?.value || '').trim(),
    recipient_email: (document.getElementById('email_recipient')?.value || '').trim()
  };

  try {
    const res = await fetch(`/api/applications/${currentApplication.id}/draft`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to save draft");
    showToast("Draft changes saved to SQLite successfully!");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function copyEmailToClipboard() {
  const subject = document.getElementById('email_subject')?.value || '';
  const body = document.getElementById('email_body')?.value || '';
  const full = `Subject: ${subject}\n\n${body}`;
  navigator.clipboard.writeText(full).then(() => {
    showToast("Email draft copied to clipboard!");
  }).catch(() => {
    showToast("Could not access clipboard", "error");
  });
}

function updateP3EmailGuidance(val) {
  const email = (val !== undefined ? val : (document.getElementById('email_recipient') ? document.getElementById('email_recipient').value : "")).trim();
  const tag = document.getElementById('p3_emailStatusTag');
  const helper = document.getElementById('p3_emailHelperCard');
  const chipsBox = document.getElementById('p3_domainChips');
  const details = typeof getActiveJobDetails === 'function' ? getActiveJobDetails() : { company: '', jobUrl: '' };

  const portalBtn = document.getElementById('p3_openPortalBtn');
  if (portalBtn) {
    if (details.jobUrl) {
      portalBtn.classList.remove('hidden');
      portalBtn.title = `Apply on ${details.jobUrl}`;
    } else {
      portalBtn.classList.add('hidden');
    }
  }

  if (chipsBox) {
    chipsBox.innerHTML = "";
    const suggestions = typeof generateDomainEmailSuggestions === 'function' ? generateDomainEmailSuggestions(details.company) : [];
    if (suggestions.length === 0) {
      chipsBox.innerHTML = `<span class="text-slate-400 italic">None generated</span>`;
    } else {
      suggestions.forEach(s => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = "px-2 py-0.5 rounded bg-amber-100 hover:bg-amber-200 text-amber-900 border border-amber-300 font-mono text-[10.5px] transition cursor-pointer";
        btn.textContent = s;
        btn.title = `Click to autofill ${s}`;
        btn.onclick = () => {
          const el = document.getElementById('email_recipient');
          if (el) el.value = s;
          updateP3EmailGuidance(s);
          showToast(`Filled recipient: ${s}`);
        };
        chipsBox.appendChild(btn);
      });
    }
  }

  if (email && email.includes('@')) {
    if (tag) {
      tag.textContent = "Recipient Provided";
      tag.className = "text-[11px] font-semibold text-emerald-600";
    }
    if (helper) helper.classList.add('hidden');
  } else {
    if (tag) {
      tag.textContent = "Not specified (Job board protected)";
      tag.className = "text-[11px] font-semibold text-amber-600";
    }
    if (helper) helper.classList.remove('hidden');
  }
}

function onP3RecipientInput(val) {
  updateP3EmailGuidance(val);
}
