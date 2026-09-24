/**
 * Phase 4: Human Review & Approval Station Module
 */

let currentReviewPacket = null;

function getActiveJobDetails() {
  const job = currentJob || (currentReviewPacket && currentReviewPacket.job) || {};
  const app = (currentReviewPacket && currentReviewPacket.application) || currentApplication || {};
  const company = job.company_name || app.company_name || "Company";
  const jobUrl = job.job_url || (currentReviewPacket?.job?.job_url) || "";
  return { job, app, company, jobUrl };
}

function generateDomainEmailSuggestions(companyName) {
  if (!companyName) return [];
  let clean = companyName.toLowerCase();
  clean = clean.replace(/\b(private\s+limited|pvt\.?\s*ltd\.?|limited|ltd\.?|inc\.?|llc|corporation|technologies|solutions|services|capital|group|india)\b/gi, ' ');
  clean = clean.replace(/[^a-z0-9]/g, '').trim();
  if (!clean || clean.length < 2) return [];
  return [
    `careers@${clean}.com`,
    `hr@${clean}.com`
  ];
}

async function goToPhase4Review() {
  if (!currentApplication || !currentApplication.id) {
    if (currentJob) {
      const res = await fetch(`/api/jobs/${currentJob.id}/application`);
      const data = await res.json();
      if (data.status === "success" && data.application) {
        currentApplication = data.application;
      }
    } else {
      try {
        const appsRes = await fetch('/api/applications');
        const appsData = await appsRes.json();
        if (appsData.applications && appsData.applications.length > 0) {
          currentApplication = appsData.applications[0];
        }
      } catch (e) {
        console.warn("Could not auto-fetch latest application for review", e);
      }
    }
  }

  const grid = document.getElementById('p4_contentGrid');
  const empty = document.getElementById('p4_emptyState');

  if (!currentApplication || !currentApplication.id) {
    if (grid) grid.classList.add('hidden');
    if (empty) empty.classList.remove('hidden');
    return;
  }

  if (empty) empty.classList.add('hidden');
  if (grid) grid.classList.remove('hidden');

  try {
    const res = await fetch(`/api/applications/${currentApplication.id}/review-packet`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to load review packet");

    currentReviewPacket = data;
    renderReviewPacket(data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function renderReviewPacket(packet) {
  const app = packet.application || {};
  const job = packet.job || {};
  const resume = packet.attached_resume || {};
  const dup = packet.duplicate_check || {};

  if (document.getElementById('p4_companyName')) document.getElementById('p4_companyName').textContent = app.company_name || job.company_name || "Company";
  if (document.getElementById('p4_jobTitle')) document.getElementById('p4_jobTitle').textContent = app.job_title || job.job_title || "Job Title";
  if (document.getElementById('p4_recipientEmailDisplay')) document.getElementById('p4_recipientEmailDisplay').textContent = app.recipient_email || job.company_email || "Not specified";
  if (document.getElementById('p4_matchScoreBadge')) document.getElementById('p4_matchScoreBadge').textContent = `${app.match_score || 0}% Match`;

  if (document.getElementById('p4_attachedResumeFile')) document.getElementById('p4_attachedResumeFile').textContent = resume.filename || "No resume file attached";
  if (document.getElementById('p4_attachedResumeLabel')) document.getElementById('p4_attachedResumeLabel').textContent = resume.label || "General Resume";

  const safeNotice = document.getElementById('p4_dupSafeNotice');
  const warnNotice = document.getElementById('p4_dupWarningNotice');
  const warnDetails = document.getElementById('p4_dupWarningDetails');

  if (dup.is_duplicate) {
    if (safeNotice) safeNotice.classList.add('hidden');
    if (warnNotice) warnNotice.classList.remove('hidden');
    if (warnDetails) warnDetails.textContent = dup.warning_message;
  } else {
    if (safeNotice) safeNotice.classList.remove('hidden');
    if (warnNotice) warnNotice.classList.add('hidden');
  }

  const effectiveRecipient = app.recipient_email || job.company_email || "";
  if (document.getElementById('p4_recipientInput')) document.getElementById('p4_recipientInput').value = effectiveRecipient;
  if (document.getElementById('p4_subjectInput')) document.getElementById('p4_subjectInput').value = app.email_subject || "";
  if (document.getElementById('p4_bodyInput')) document.getElementById('p4_bodyInput').value = app.email_body || "";

  updateP4EmailGuidance(effectiveRecipient);

  if (document.getElementById('p4_humanApprovalCheckbox')) document.getElementById('p4_humanApprovalCheckbox').checked = false;
  if (document.getElementById('p4_overrideDupCheckbox')) document.getElementById('p4_overrideDupCheckbox').checked = false;
  checkApprovalState();
  initIcons();
}

function checkApprovalState() {
  const approved = document.getElementById('p4_humanApprovalCheckbox')?.checked || false;
  const sendBtn = document.getElementById('p4_sendBtn');
  const isDup = currentReviewPacket?.duplicate_check?.is_duplicate;
  const dupOverride = document.getElementById('p4_overrideDupCheckbox')?.checked || false;
  const recipient = (document.getElementById('p4_recipientInput')?.value || "").trim();

  if (sendBtn) {
    if (approved && (!isDup || dupOverride) && recipient.length > 0) {
      sendBtn.disabled = false;
      sendBtn.className = "w-full sm:w-auto px-6 py-3 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm flex items-center justify-center space-x-2 transition cursor-pointer";
    } else {
      sendBtn.disabled = true;
      sendBtn.className = "w-full sm:w-auto px-6 py-3 text-sm font-bold text-white bg-slate-300 rounded-lg cursor-not-allowed flex items-center justify-center space-x-2 transition";
    }
  }
}

async function executeApprovedDispatch() {
  if (!currentApplication || !currentApplication.id) return;
  const sendBtn = document.getElementById('p4_sendBtn');
  const sendBtnText = document.getElementById('p4_sendBtnText');
  const recipient = (document.getElementById('p4_recipientInput')?.value || "").trim();

  if (!recipient) {
    showToast("Please enter a valid recruiter email address, or click 'Copy Pitch & Open Portal' to apply on the job board.", "error");
    return;
  }

  if (sendBtn) sendBtn.disabled = true;
  if (sendBtnText) sendBtnText.textContent = "Dispatching Application...";

  const payload = {
    approved: true,
    recipient_email: recipient,
    email_subject: (document.getElementById('p4_subjectInput')?.value || "").trim(),
    email_body: (document.getElementById('p4_bodyInput')?.value || "").trim(),
    attach_resume: document.getElementById('p4_attachResumeCheckbox')?.checked || true,
    override_duplicate: document.getElementById('p4_overrideDupCheckbox')?.checked || false,
    notes: "Approved and dispatched by candidate"
  };

  try {
    const res = await fetch(`/api/applications/${currentApplication.id}/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    
    if (res.status === 409) {
      showToast(data.message, "error");
      if (document.getElementById('p4_dupSafeNotice')) document.getElementById('p4_dupSafeNotice').classList.add('hidden');
      if (document.getElementById('p4_dupWarningNotice')) document.getElementById('p4_dupWarningNotice').classList.remove('hidden');
      if (document.getElementById('p4_dupWarningDetails')) document.getElementById('p4_dupWarningDetails').textContent = data.message;
      return;
    }

    if (!res.ok) throw new Error(data.detail || "Dispatch failed");

    showToast(data.message || "Application dispatched successfully!");

    const receipt = document.getElementById('p4_successReceipt');
    if (receipt) receipt.classList.remove('hidden');
    if (document.getElementById('p4_receiptTimestamp')) document.getElementById('p4_receiptTimestamp').innerHTML = `<strong>Timestamp:</strong> ${data.dispatch?.sent_at || new Date().toISOString()}`;
    if (document.getElementById('p4_receiptRecipient')) document.getElementById('p4_receiptRecipient').innerHTML = `<strong>Recipient:</strong> ${data.dispatch?.recipient}`;
    if (document.getElementById('p4_receiptPreview')) document.getElementById('p4_receiptPreview').innerHTML = `<strong>Mode:</strong> ${data.dispatch?.dry_run ? 'Safe Dry-Run Preview (' + data.dispatch?.preview_file + ')' : 'Dispatched via SMTP'}`;

    if (sendBtn) sendBtn.classList.add('hidden');

  } catch (err) {
    showToast(err.message, "error");
  } finally {
    if (sendBtnText) sendBtnText.textContent = "Approve & Dispatch Application";
  }
}

function updateP4EmailGuidance(val) {
  const email = (val !== undefined ? val : (document.getElementById('p4_recipientInput') ? document.getElementById('p4_recipientInput').value : "")).trim();
  const tag = document.getElementById('p4_emailStatusTag');
  const helper = document.getElementById('p4_emailHelperCard');
  const display = document.getElementById('p4_recipientEmailDisplay');
  const chipsBox = document.getElementById('p4_domainChips');
  const { company, jobUrl } = getActiveJobDetails();

  const urlRow = document.getElementById('p4_jobUrlRow');
  const urlLink = document.getElementById('p4_jobUrlLink');
  const urlText = document.getElementById('p4_jobUrlText');
  if (urlRow && urlLink && urlText) {
    if (jobUrl) {
      urlRow.classList.remove('hidden');
      urlLink.href = jobUrl;
      urlText.textContent = `${company.substring(0, 18)}... Portal`;
    } else {
      urlRow.classList.add('hidden');
    }
  }

  if (chipsBox) {
    chipsBox.innerHTML = "";
    const suggestions = generateDomainEmailSuggestions(company);
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
          const el = document.getElementById('p4_recipientInput');
          if (el) el.value = s;
          updateP4EmailGuidance(s);
          checkApprovalState();
          showToast(`Filled recipient: ${s}`);
        };
        chipsBox.appendChild(btn);
      });
    }
  }

  if (email && email.includes('@')) {
    if (tag) {
      tag.textContent = "Verified";
      tag.className = "text-[11px] font-semibold text-emerald-600";
    }
    if (display) {
      display.textContent = email;
      display.className = "font-semibold text-indigo-600";
    }
    if (helper) helper.classList.add('hidden');
  } else {
    if (tag) {
      tag.textContent = "Not specified";
      tag.className = "text-[11px] font-semibold text-amber-600";
    }
    if (display) {
      display.textContent = "Not specified (Job board protected)";
      display.className = "font-semibold text-amber-600 italic";
    }
    if (helper) helper.classList.remove('hidden');
  }
}

function onP4RecipientInput(val) {
  updateP4EmailGuidance(val);
  checkApprovalState();
}

function openOriginalJobPortal() {
  const { jobUrl } = getActiveJobDetails();
  if (jobUrl) {
    window.open(jobUrl, '_blank');
  } else {
    showToast("No external job portal link recorded for this job. You can enter the recruiter email directly.", "info");
  }
}

function searchRecruiterOnLinkedIn() {
  const { company } = getActiveJobDetails();
  let cleanComp = company.replace(/\b(private\s+limited|pvt\.?\s*ltd\.?|limited|ltd\.?|inc\.?|llc|corporation)\b/gi, '').trim();
  if (!cleanComp) cleanComp = company;
  const query = encodeURIComponent(`HR recruiter "${cleanComp}"`);
  const url = `https://www.linkedin.com/search/results/people/?keywords=${query}`;
  window.open(url, '_blank');
}

function copyPitchAndOpenPortal() {
  let bodyText = "";
  const p4Input = document.getElementById('p4_bodyInput');
  const p3Input = document.getElementById('email_body');
  if (p4Input && p4Input.value) {
    bodyText = p4Input.value;
  } else if (p3Input && p3Input.value) {
    bodyText = p3Input.value;
  }
  if (!bodyText) {
    showToast("No email pitch text found to copy.", "warning");
    return;
  }
  navigator.clipboard.writeText(bodyText).then(() => {
    showToast("Pitch copied to clipboard! Opening job portal so you can paste it into the application form.");
    const { jobUrl } = getActiveJobDetails();
    if (jobUrl) {
      setTimeout(() => window.open(jobUrl, '_blank'), 400);
    }
  }).catch(() => {
    showToast("Could not copy automatically. Please copy the text manually.", "error");
  });
}
