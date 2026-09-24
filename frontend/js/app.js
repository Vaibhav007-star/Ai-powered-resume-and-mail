/**
 * AI Job Application Assistant - Core Application & Global State
 */

let currentTab = 5; // Default to Phase 5 Tracking Dashboard
let currentJob = null;
let currentApplication = null;
let allJobs = [];

// Initialize Lucide Icons
function initIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// Switch Tabs
function switchTab(tabNum) {
  currentTab = tabNum;
  const v1 = document.getElementById('viewPhase1');
  const v2 = document.getElementById('viewPhase2');
  const v3 = document.getElementById('viewPhase3');
  const v4 = document.getElementById('viewPhase4');
  const v5 = document.getElementById('viewPhase5');
  const t1 = document.getElementById('navTab1');
  const t2 = document.getElementById('navTab2');
  const t3 = document.getElementById('navTab3');
  const t4 = document.getElementById('navTab4');
  const t5 = document.getElementById('navTab5');

  [v1, v2, v3, v4, v5].forEach(v => { if (v) v.classList.add('hidden'); });
  [t1, t2, t3, t4, t5].forEach(t => { 
    if (t) t.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-slate-600 hover:text-indigo-600 hover:bg-white transition"; 
  });

  if (tabNum === 1) {
    if (v1) v1.classList.remove('hidden');
    if (t1) t1.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg border bg-white text-indigo-700 border-indigo-200 shadow-xs transition";
  } else if (tabNum === 2) {
    if (v2) v2.classList.remove('hidden');
    if (t2) t2.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg border bg-white text-indigo-700 border-indigo-200 shadow-xs transition";
  } else if (tabNum === 3) {
    if (v3) v3.classList.remove('hidden');
    if (t3) t3.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg border bg-white text-indigo-700 border-indigo-200 shadow-xs transition";
    if (typeof populateP3JobDropdown === 'function') populateP3JobDropdown();
    if (currentJob && typeof loadApplicationForJob === 'function') {
      const select = document.getElementById('p3_jobSelect');
      if (select) select.value = currentJob.id;
      loadApplicationForJob(currentJob.id);
    }
  } else if (tabNum === 4) {
    if (v4) v4.classList.remove('hidden');
    if (t4) t4.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg border bg-white text-indigo-700 border-indigo-200 shadow-xs transition";
    if (typeof goToPhase4Review === 'function') goToPhase4Review();
  } else if (tabNum === 5) {
    if (v5) v5.classList.remove('hidden');
    if (t5) t5.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg border bg-white text-indigo-700 border-indigo-200 shadow-xs transition";
    if (typeof loadTrackingDashboard === 'function') loadTrackingDashboard();
  }
  initIcons();
}

// Toast Notification
function showToast(message, type = 'success') {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.className = `fixed bottom-5 right-5 z-50 transform transition-all duration-300 translate-y-0 opacity-100 flex items-center space-x-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
    type === 'success' ? 'bg-slate-900 text-white' : 'bg-red-600 text-white'
  }`;
  setTimeout(() => {
    toast.className = toast.className.replace('translate-y-0 opacity-100', 'translate-y-20 opacity-0 pointer-events-none');
  }, 3500);
}

// System Health Check
async function checkHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    const aiStatusBadge = document.getElementById('aiStatusBadge');
    const aiStatusText = document.getElementById('aiStatusText');
    if (aiStatusBadge && aiStatusText) {
      if (data.ai_configured) {
        aiStatusBadge.className = 'flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200';
        aiStatusText.textContent = `AI: ${data.model || 'Ready'}`;
      } else {
        aiStatusBadge.className = 'flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200';
        aiStatusText.textContent = 'Heuristic Mode (No API Key)';
      }
    }
  } catch (err) {
    console.error(err);
  }
}

// HTML Escaper
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
