/**
 * Phase 5: Application Tracking Dashboard Module
 */

let allTrackingApps = [];
let currentTrackingStatusFilter = 'all';

async function loadTrackingDashboard() {
  try {
    const metricsRes = await fetch("/api/applications/metrics");
    const metricsData = await metricsRes.json();
    if (metricsData.status === "success") {
      const m = metricsData.metrics || {};
      if (document.getElementById('metric_total')) document.getElementById('metric_total').textContent = m.total || 0;
      if (document.getElementById('metric_sent')) document.getElementById('metric_sent').textContent = m.sent || 0;
      if (document.getElementById('metric_drafts')) document.getElementById('metric_drafts').textContent = m.drafts || 0;
      if (document.getElementById('metric_follow_ups')) document.getElementById('metric_follow_ups').textContent = m.due_follow_ups || 0;
      if (document.getElementById('metric_interview_offer')) document.getElementById('metric_interview_offer').textContent = (m.interview || 0) + (m.offer || 0);
    }

    const appsRes = await fetch("/api/applications");
    const appsData = await appsRes.json();
    allTrackingApps = appsData.applications || [];

    renderTrackingApplications();
  } catch (err) {
    console.error("Failed to load tracking dashboard:", err);
    showToast("Failed to load tracking data", "error");
  }
}

function setStatusFilter(status) {
  currentTrackingStatusFilter = status;

  const filterKeys = ['all', 'Draft', 'Ready for Review', 'Sent', 'Follow-up', 'Interview', 'Offer', 'Rejected', 'Closed'];
  filterKeys.forEach(k => {
    const btnId = `filterBtn_${k.replace(/\s+/g, '_')}`;
    const btn = document.getElementById(btnId);
    if (btn) {
      if (k === status) {
        btn.className = "px-3 py-1 rounded-full font-medium bg-slate-900 text-white transition";
      } else {
        btn.className = "px-3 py-1 rounded-full font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 transition";
      }
    }
  });

  renderTrackingApplications();
}

function filterTrackingList() {
  renderTrackingApplications();
}

function renderTrackingApplications() {
  const container = document.getElementById('trackingApplicationsContainer');
  const emptyState = document.getElementById('trackingEmptyState');
  const query = (document.getElementById('trackingSearchInput')?.value || '').toLowerCase().trim();

  if (!container) return;

  let filtered = allTrackingApps;

  if (currentTrackingStatusFilter !== 'all') {
    filtered = filtered.filter(a => a.status === currentTrackingStatusFilter);
  }

  if (query) {
    filtered = filtered.filter(a => {
      const comp = (a.company_name || '').toLowerCase();
      const role = (a.job_title || '').toLowerCase();
      const email = (a.recipient_email || '').toLowerCase();
      const notes = (a.notes || '').toLowerCase();
      return comp.includes(query) || role.includes(query) || email.includes(query) || notes.includes(query);
    });
  }

  if (filtered.length === 0) {
    container.innerHTML = '';
    if (emptyState) emptyState.classList.remove('hidden');
    const emptyMsg = document.getElementById('trackingEmptyMessage');
    if (emptyMsg) {
      if (currentTrackingStatusFilter !== 'all') {
        emptyMsg.textContent = `No applications found with status "${currentTrackingStatusFilter}".`;
      } else if (query) {
        emptyMsg.textContent = `No applications match your search for "${query}".`;
      } else {
        emptyMsg.textContent = `You don't have any applications tracked yet. Start by analyzing a job!`;
      }
    }
    return;
  }

  if (emptyState) emptyState.classList.add('hidden');

  const todayIso = new Date().toISOString().split('T')[0];

  container.innerHTML = filtered.map(app => {
    const score = app.match_score || 0;
    let scoreColor = "bg-rose-100 text-rose-800 border-rose-200";
    if (score >= 75) scoreColor = "bg-emerald-100 text-emerald-800 border-emerald-200";
    else if (score >= 50) scoreColor = "bg-amber-100 text-amber-800 border-amber-200";

    const isFollowUpDue = app.follow_up_date && app.follow_up_date <= todayIso && !['Rejected', 'Closed', 'Offer'].includes(app.status);

    const statusOptions = [
      'Draft', 'Ready for Review', 'Sent', 'Follow-up', 'Interview', 'Rejected', 'Offer', 'Closed'
    ].map(st => `<option value="${st}" ${app.status === st ? 'selected' : ''}>${st}</option>`).join('');

    const responseStatusOptions = [
      'Pending', 'Acknowledged', 'Screening Scheduled', 'Technical Round', 'Final Round', 'Offer Received', 'Declined'
    ].map(rs => `<option value="${rs}" ${(app.response_status || 'Pending') === rs ? 'selected' : ''}>${rs}</option>`).join('');

    const isDraftOrReview = ['Draft', 'Ready for Review'].includes(app.status);

    return `
      <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4 hover:border-slate-300 transition" id="appCard_${app.id}">
        <!-- Header Row -->
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-3">
          <div>
            <div class="flex items-center space-x-2">
              <h3 class="text-base font-bold text-slate-900">${escapeHtml(app.job_title || 'Position')}</h3>
              <span class="text-xs font-semibold px-2 py-0.5 rounded-full border ${scoreColor}">
                ${score}% Match
              </span>
              ${isFollowUpDue ? '<span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-orange-100 text-orange-800 border border-orange-200 animate-pulse font-medium">Follow-up Due!</span>' : ''}
            </div>
            <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 mt-1">
              <span class="font-medium text-slate-700 flex items-center">
                <i data-lucide="building" class="w-3.5 h-3.5 mr-1 text-slate-400"></i> ${escapeHtml(app.company_name || 'Company')}
              </span>
              <span>&bull;</span>
              <span class="flex items-center">
                <i data-lucide="mail" class="w-3.5 h-3.5 mr-1 text-slate-400"></i> ${escapeHtml(app.recipient_email || 'No recipient')}
              </span>
              <span>&bull;</span>
              <span class="flex items-center text-slate-400">
                <i data-lucide="calendar" class="w-3.5 h-3.5 mr-1 text-slate-400"></i> Updated: ${app.updated_at ? app.updated_at.split('T')[0] : 'N/A'}
              </span>
            </div>
          </div>

          <!-- Quick Status Selector -->
          <div class="flex items-center space-x-2">
            <span class="text-xs text-slate-500 font-medium">Status:</span>
            <select onchange="quickUpdateAppStatus(${app.id}, this.value)" class="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-slate-300 bg-slate-50 text-slate-800 focus:ring-2 focus:ring-indigo-500 outline-none cursor-pointer">
              ${statusOptions}
            </select>
          </div>
        </div>

        <!-- Tracking Controls Grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
          
          <!-- Response Status -->
          <div>
            <label class="block text-xs font-medium text-slate-600 mb-1">Recruiter Response Stage</label>
            <select id="respStatus_${app.id}" class="w-full text-xs px-2.5 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none bg-white">
              ${responseStatusOptions}
            </select>
          </div>

          <!-- Follow-Up Date -->
          <div>
            <label class="block text-xs font-medium text-slate-600 mb-1">Follow-up Target Date</label>
            <div class="relative">
              <input type="date" id="followUp_${app.id}" value="${app.follow_up_date || ''}" class="w-full text-xs px-2.5 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none bg-white">
            </div>
          </div>

          <!-- Application Actions -->
          <div class="flex items-end space-x-2">
            <button onclick="saveAppDetails(${app.id})" class="flex-1 flex items-center justify-center space-x-1.5 bg-slate-800 hover:bg-slate-900 text-white text-xs font-medium py-2 px-3 rounded-lg transition shadow-xs">
              <i data-lucide="save" class="w-3.5 h-3.5"></i>
              <span>Save Details</span>
            </button>
            ${isDraftOrReview ? `
              <button onclick="openInReview(${app.job_id}, ${app.id})" class="flex items-center justify-center space-x-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium py-2 px-3 rounded-lg transition shadow-xs" title="Open in Tab 4 to approve and send">
                <i data-lucide="send" class="w-3.5 h-3.5"></i>
                <span>Review</span>
              </button>
            ` : ''}
            <button onclick="deleteAppRecord(${app.id}, '${escapeHtml(app.company_name || 'this application')}')" class="flex items-center justify-center p-2 text-rose-600 hover:bg-rose-50 border border-slate-200 rounded-lg transition" title="Delete application record">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
          </div>

        </div>

        <!-- Notes Section -->
        <div>
          <label class="block text-xs font-medium text-slate-600 mb-1">Notes & Follow-up Log</label>
          <textarea id="notes_${app.id}" rows="2" placeholder="Record interview notes, recruiter questions, follow-up conversation details..." class="w-full text-xs p-2.5 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none text-slate-800 bg-slate-50/50">${escapeHtml(app.notes || '')}</textarea>
        </div>

      </div>
    `;
  }).join('');

  initIcons();
}

async function quickUpdateAppStatus(appId, newStatus) {
  try {
    const res = await fetch(`/api/applications/${appId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to update status");

    showToast(`Status updated to "${newStatus}"!`);
    const app = allTrackingApps.find(a => a.id === appId);
    if (app) app.status = newStatus;
    loadTrackingDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function saveAppDetails(appId) {
  const followUpInput = document.getElementById(`followUp_${appId}`);
  const respStatusSelect = document.getElementById(`respStatus_${appId}`);
  const notesInput = document.getElementById(`notes_${appId}`);

  const payload = {
    follow_up_date: followUpInput ? followUpInput.value : '',
    response_status: respStatusSelect ? respStatusSelect.value : 'Pending',
    notes: notesInput ? notesInput.value.trim() : ''
  };

  try {
    const res = await fetch(`/api/applications/${appId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to save details");

    showToast("Application notes & details saved!");
    const app = allTrackingApps.find(a => a.id === appId);
    if (app) {
      app.follow_up_date = payload.follow_up_date;
      app.response_status = payload.response_status;
      app.notes = payload.notes;
    }
    loadTrackingDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteAppRecord(appId, companyName) {
  if (!confirm(`Are you sure you want to delete the application record for ${companyName}? This cannot be undone.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/applications/${appId}`, {
      method: "DELETE"
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to delete application");

    showToast(`Application deleted successfully.`);
    allTrackingApps = allTrackingApps.filter(a => a.id !== appId);
    loadTrackingDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function openInReview(jobId, appId) {
  const foundJob = allJobs.find(j => j.id == jobId);
  if (foundJob) currentJob = foundJob;
  
  const app = allTrackingApps.find(a => a.id === appId);
  if (app) currentApplication = app;

  switchTab(4);
}
