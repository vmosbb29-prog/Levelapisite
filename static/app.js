/* ════════════════════════════════════════════════════════
   Level-Up Bot Dashboard — v10
   ════════════════════════════════════════════════════════ */
'use strict';

/* ════════════════════════════════════════════════════════
   API LAYER
   ════════════════════════════════════════════════════════ */
async function apiPost(url, data) {
  const body = (data instanceof FormData) ? data : (() => {
    const fd = new FormData();
    for (const [k, v] of Object.entries(data)) fd.append(k, String(v));
    return fd;
  })();
  const res = await fetch(url, { method: 'POST', body });
  if (!res.ok) {
    let msg = `Server error ${res.status}`;
    try { msg = (await res.json()).error || msg; } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}
async function apiGet(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Server error ${res.status}`);
  return res.json();
}

/* ════════════════════════════════════════════════════════
   UTILITIES
   ════════════════════════════════════════════════════════ */
function esc(s) {
  return String(s ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function num(n) {
  return (n === null || n === undefined || n === '') ? '—' : Number(n).toLocaleString();
}
function dur(s) {
  if (!s || s < 1)   return '—';
  if (s < 60)         return `${s}s`;
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}
function uptime(s) {
  if (!s || s < 1)   return '0s';
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s % 60}s`;
  return `${s}s`;
}
function $id(id) { return document.getElementById(id); }
function setText(id, v) { const e = $id(id); if (e) e.textContent = v; }

/* ════════════════════════════════════════════════════════
   TOAST
   ════════════════════════════════════════════════════════ */
const _toast = (() => {
  let t = null;
  return { show(msg, type = 'info') {
    const el = $id('toast');
    if (!el) return;
    el.textContent = msg;
    el.className = `toast ${type} show`;
    clearTimeout(t);
    t = setTimeout(() => el.classList.remove('show'), 4000);
  }};
})();
function showToast(msg, type) { _toast.show(msg, type); }

/* ════════════════════════════════════════════════════════
   ANIMATED COUNTER + RING CHART
   ════════════════════════════════════════════════════════ */
function animateVal(el, to) {
  if (!el) return;
  const from = parseInt(el.dataset.v ?? el.textContent) || 0;
  el.dataset.v = to;
  if (from === to) { el.textContent = to; return; }
  const dur = 420, t0 = performance.now();
  const tick = t => {
    const p = Math.min((t - t0) / dur, 1);
    el.textContent = Math.round(from + (to - from) * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
function setRing(id, pct) {
  const e = $id(id);
  if (e) e.style.strokeDashoffset =
    (314.16 * (1 - Math.min(Math.max(pct, 0), 100) / 100)).toFixed(2);
}

/* ════════════════════════════════════════════════════════
   SIDEBAR TOGGLE  (mobile only)
   ════════════════════════════════════════════════════════ */
$id('hamburger-btn')?.addEventListener('click', () =>
  document.body.classList.toggle('menu-open'));
$id('sb-overlay')?.addEventListener('click', () =>
  document.body.classList.remove('menu-open'));

/* ════════════════════════════════════════════════════════
   TAB NAVIGATION
   ════════════════════════════════════════════════════════ */
function switchTab(name) {
  document.querySelectorAll('.nav-link[data-tab]').forEach(l =>
    l.classList.toggle('active', l.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach(p =>
    p.classList.toggle('active', p.id === `tab-${name}`));
  document.body.classList.remove('menu-open');
}
document.querySelectorAll('.nav-link[data-tab]').forEach(l =>
  l.addEventListener('click', e => { e.preventDefault(); switchTab(l.dataset.tab); }));

/* ════════════════════════════════════════════════════════
   TOPBAR STATUS UPDATE
   ════════════════════════════════════════════════════════ */
let _lastActive = -1;
function setTopbarStatus(active) {
  if (active === _lastActive) return;
  _lastActive = active;
  setText('status-text', `${active} online`);
  const led = $id('status-led');
  if (led) led.className = `status-led ${active > 0 ? 'online' : ''}`;
  const badge = $id('nav-bot-count');
  if (badge) { badge.style.display = active > 0 ? '' : 'none'; badge.textContent = active; }
}

/* ════════════════════════════════════════════════════════
   BOT CARD HELPERS
   ════════════════════════════════════════════════════════ */
function _setBadgeStatus(id, status) {
  [`badge-${id}`, `tbl-badge-${id}`].forEach(bid => {
    const b = $id(bid);
    if (!b) return;
    b.className = `bot-badge ${status}`;
    const dot = b.querySelector('.badge-dot');
    if (!dot) {
      const d = document.createElement('span');
      d.className = 'badge-dot';
      b.prepend(d);
    }
    const txt = $id(`badge-txt-${id}`);
    if (txt) txt.textContent = status.toUpperCase();
  });
}

function setOnline(id, displayName) {
  const card = $id(`card-${id}`);
  if (card) { card.classList.remove('offline'); card.classList.add('online'); }
  $id(`fstart-${id}`)?.style.setProperty('display', 'none');
  $id(`octrl-${id}`)?.style.removeProperty('display');
  _setBadgeStatus(id, 'online');
  if (displayName) { const d = $id(`dname-${id}`); if (d) d.textContent = displayName; }
}
function setOffline(id) {
  const card = $id(`card-${id}`);
  if (card) { card.classList.remove('online'); card.classList.add('offline'); }
  $id(`fstart-${id}`)?.style.removeProperty('display');
  $id(`octrl-${id}`)?.style.setProperty('display', 'none');
  $id(`stats-${id}`)?.style.setProperty('display', 'none');
  _setBadgeStatus(id, 'offline');
  stopAutoIndicator(id);
}
function setStats(id, cycles, uptimeSec) {
  const s = $id(`stats-${id}`);
  if (s) s.style.removeProperty('display');
  const c = $id(`cycles-${id}`); if (c) c.textContent = cycles || 0;
  const u = $id(`uptime-${id}`); if (u) u.textContent = uptime(uptimeSec || 0);
}
function startAutoIndicator(id) {
  $id(`brun-${id}`)?.style.setProperty('display', 'none');
  $id(`bstopauto-${id}`)?.style.removeProperty('display');
  $id(`autoind-${id}`)?.style.removeProperty('display');
}
function stopAutoIndicator(id) {
  $id(`brun-${id}`)?.style.removeProperty('display');
  $id(`bstopauto-${id}`)?.style.setProperty('display', 'none');
  $id(`autoind-${id}`)?.style.setProperty('display', 'none');
}

/* ════════════════════════════════════════════════════════
   BOT CONTROLS
   ════════════════════════════════════════════════════════ */
async function startBot(e, id) {
  e.preventDefault();
  const btn = $id(`bstart-${id}`);
  if (btn) { btn.disabled = true; btn.textContent = 'Connecting…'; }
  try {
    const d = await apiPost('/bot/start', new FormData(e.target));
    if (d.ok) {
      showToast(d.message, 'success');
      setOnline(id, d.bot?.display_name || '');
      setStats(id, d.bot?.cycles_completed || 0, d.bot?.uptime_seconds || 0);
    } else {
      showToast(d.error || 'Failed to start', 'error');
      if (btn) { btn.disabled = false; btn.textContent = '▶ Start Bot'; }
    }
  } catch (err) {
    showToast(err.message || 'Network error', 'error');
    if (btn) { btn.disabled = false; btn.textContent = '▶ Start Bot'; }
  }
}
async function stopBot(id) {
  const btn = $id(`bstop-${id}`);
  if (btn) { btn.disabled = true; btn.textContent = 'Stopping…'; }
  try {
    const d = await apiPost('/bot/stop', { account_id: id });
    if (d.ok) { showToast(d.message || 'Stopped', 'info'); setOffline(id); }
    else showToast(d.error || 'Failed to stop', 'error');
  } catch (err) { showToast(err.message || 'Network error', 'error'); }
  finally { const b = $id(`bstop-${id}`); if (b) { b.disabled = false; b.textContent = '■ Stop Bot'; } }
}
async function runTeamcode(e, id) {
  e.preventDefault();
  const btn = $id(`brun-${id}`);
  if (btn) { btn.disabled = true; btn.textContent = '⏳'; }
  try {
    const d = await apiPost('/bot/run', new FormData(e.target));
    if (d.ok) { showToast(d.message, 'success'); startAutoIndicator(id); }
    else showToast(d.error || 'Failed', 'error');
  } catch (err) { showToast(err.message || 'Network error', 'error'); }
  finally { const b = $id(`brun-${id}`); if (b) { b.disabled = false; b.textContent = '🚀'; } }
}
async function stopAuto(id) {
  const btn = $id(`bstopauto-${id}`);
  if (btn) btn.disabled = true;
  try {
    const d = await apiPost('/bot/stop-auto', { account_id: id });
    if (d.ok) { showToast(d.message || 'Auto stopped', 'info'); stopAutoIndicator(id); }
    else showToast(d.error || 'Failed', 'error');
  } catch (err) { showToast(err.message || 'Network error', 'error'); }
  finally { const b = $id(`bstopauto-${id}`); if (b) b.disabled = false; }
}

$id('form-add-account')?.addEventListener('submit', async e => {
  e.preventDefault();
  const btn = e.target.querySelector('[type="submit"]');
  if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }
  try {
    const d = await apiPost('/bot/accounts/add', new FormData(e.target));
    if (d.ok) { showToast('Account saved! Reloading…', 'success'); setTimeout(() => location.reload(), 900); }
    else { showToast(d.error || 'Failed to save', 'error'); if (btn) { btn.disabled = false; btn.textContent = 'Save Account'; } }
  } catch (err) {
    showToast(err.message || 'Network error', 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Save Account'; }
  }
});

async function deleteAccount(id) {
  if (!confirm('Delete this account? Running bot will be stopped.')) return;
  try {
    const d = await apiPost('/bot/accounts/delete', { account_id: id });
    if (d.ok) {
      $id(`card-${id}`)?.remove();
      document.querySelectorAll(`tr[data-id="${id}"]`).forEach(r => r.remove());
      window.ACCOUNTS = (window.ACCOUNTS || []).filter(a => a.id !== id);
      window.TOTAL_BOTS = Math.max(0, (window.TOTAL_BOTS || 1) - 1);
      showToast('Account removed', 'info');
    } else showToast(d.error || 'Failed to delete', 'error');
  } catch (err) { showToast(err.message || 'Network error', 'error'); }
}

/* ════════════════════════════════════════════════════════
   POLLING — BOT STATUS  (every 4s)
   ════════════════════════════════════════════════════════ */
async function pollBotStatus() {
  if (document.hidden) return;
  try {
    const d = await apiGet('/bot/all-status');
    if (!d.ok) return;
    const map = Object.fromEntries((d.bots || []).map(b => [b.account_id, b]));
    let active = 0;
    (window.ACCOUNTS || []).forEach(acc => {
      const b = map[acc.id];
      if (b?.status === 'online') {
        active++;
        setOnline(acc.id, b.display_name);
        setStats(acc.id, b.cycles_completed, b.uptime_seconds);
        b.auto_running ? startAutoIndicator(acc.id) : stopAutoIndicator(acc.id);
        const tc = $id(`tc-${acc.id}`);
        if (tc && !tc.value && b.last_teamcode) tc.value = b.last_teamcode;
        _updatePerfRow(acc.id, b);
      } else {
        setOffline(acc.id);
        if (b) _updatePerfRow(acc.id, b);
      }
    });
    setTopbarStatus(active);
  } catch (_) {}
}
function _updatePerfRow(id, b) {
  const cyc = $id(`pt-cyc-${id}`); if (cyc) cyc.textContent = b.cycles_completed || 0;
  const upt = $id(`pt-upt-${id}`); if (upt) upt.textContent = uptime(b.uptime_seconds || 0);
  const rte = $id(`pt-rte-${id}`); if (rte) rte.textContent = b.status === 'online' ? `${b.cycles_per_hour || 0}/hr` : '—';
  const cod = $id(`pt-cod-${id}`); if (cod) cod.textContent = b.last_teamcode || '—';
}
pollBotStatus();
setInterval(pollBotStatus, 4000);

/* ════════════════════════════════════════════════════════
   POLLING — GLOBAL STATS  (every 6s)
   ════════════════════════════════════════════════════════ */
async function pollGlobalStats() {
  if (document.hidden) return;
  try {
    const d = await apiGet('/bot/global-stats');
    if (!d.ok) return;
    animateVal($id('s-active'), d.active_bots);
    animateVal($id('s-cycles'), d.total_cycles);
    setText('s-uptime', uptime(d.total_uptime_seconds || 0));
    setText('s-rate',   `${d.cycles_per_hour || 0}/h`);
    const total   = window.TOTAL_BOTS || 1;
    const actPct  = total > 0 ? Math.round(d.active_bots / total * 100) : 0;
    const cycPct  = Math.min(d.total_cycles > 0 ? Math.log10(d.total_cycles + 1) * 33 : 0, 100);
    const ratePct = Math.min((d.cycles_per_hour || 0) / 10 * 100, 100);
    setRing('ring-active', actPct);  setText('rval-active', actPct + '%');
    setText('rdesc-active', `${d.active_bots} of ${total} running`);
    setRing('ring-cycles', cycPct);  setText('rval-cycles', d.total_cycles);
    setText('rdesc-cycles', `${d.total_cycles} total`);
    setRing('ring-rate', ratePct);   setText('rval-rate', d.cycles_per_hour || 0);
    setText('rdesc-rate', `${d.cycles_per_hour || 0}/hr`);
  } catch (_) {}
}
pollGlobalStats();
setInterval(pollGlobalStats, 6000);

/* ════════════════════════════════════════════════════════
   LIVE LOGS
   ════════════════════════════════════════════════════════ */
let _logAccId  = null;
let _evtSource = null;
let _hasLogs   = false;
let _logFilter = '';

const _logPanel    = $id('log-panel');
const _autoScroll  = $id('auto-scroll');

function _updateLogCount() {
  const n = _logPanel?.querySelectorAll('.log-entry').length || 0;
  setText('log-entry-count', `${n} lines`);
}
function _appendLog(entry) {
  if (!_logPanel) return;
  if (!_hasLogs) { _logPanel.innerHTML = ''; _hasLogs = true; }
  const div = document.createElement('div');
  div.className = 'log-entry';
  const lvl = (entry.level || 'info').toLowerCase();
  div.innerHTML =
    `<span class="log-ts">${esc(entry.time)}</span>` +
    `<span class="log-lv ${lvl}">${lvl.toUpperCase().padEnd(4,' ').slice(0,4)}</span>` +
    `<span class="log-tx ${lvl}">${esc(entry.msg)}</span>`;
  if (_logFilter && !entry.msg?.toLowerCase().includes(_logFilter))
    div.classList.add('filtered');
  _logPanel.appendChild(div);
  if (_autoScroll?.checked && !_logFilter)
    _logPanel.scrollTop = _logPanel.scrollHeight;
  while (_logPanel.children.length > 500)
    _logPanel.removeChild(_logPanel.firstChild);
  _updateLogCount();
}

function switchLogBot() {
  const id = parseInt($id('log-bot-select')?.value);
  if (id) openLogs(id);
}
function openLogs(id) {
  switchTab('logs');
  const sel = $id('log-bot-select');
  if (sel) sel.value = id;
  if (_logAccId === id) return;
  _logAccId = id;
  _evtSource?.close(); _evtSource = null;
  const acc = (window.ACCOUNTS || []).find(a => a.id === id);
  setText('log-bot-label', acc ? (acc.label || `Bot ${acc.uid}`) : `Bot ${id}`);
  if (_logPanel) { _logPanel.innerHTML = '<span class="log-hint">Connecting…</span>'; _hasLogs = false; }
  const es = new EventSource(`/bot/${id}/logs`);
  _evtSource = es;
  es.onmessage = e => { try { _appendLog(JSON.parse(e.data)); } catch (_) {} };
  es.onerror = () => {
    if (!_hasLogs && _logPanel)
      _logPanel.innerHTML = '<span class="log-hint">Stream disconnected. Bot may be offline.</span>';
  };
}
$id('btn-clear-logs')?.addEventListener('click', () => {
  if (_logPanel) { _logPanel.innerHTML = '<span class="log-hint">Cleared.</span>'; _hasLogs = false; _updateLogCount(); }
});
$id('log-search')?.addEventListener('input', e => {
  _logFilter = e.target.value.trim().toLowerCase();
  _logPanel?.querySelectorAll('.log-entry').forEach(row => {
    const msg = row.querySelector('.log-tx')?.textContent || '';
    row.classList.toggle('filtered', !!_logFilter && !msg.toLowerCase().includes(_logFilter));
  });
});

/* ════════════════════════════════════════════════════════
   EXP TRACKER
   ════════════════════════════════════════════════════════ */
const _trackerCardMap = {};   // accountId → uid being tracked

/* Start from bot card */
async function startTrackerFromCard(accountId) {
  const input = $id(`track-uid-${accountId}`);
  const uid   = input?.value?.trim();
  if (!uid) { showToast('Enter a UID to track', 'warn'); return; }
  const btn = $id(`btn-track-${accountId}`);
  if (btn) { btn.disabled = true; btn.textContent = '⏳'; }
  try {
    const d = await apiPost('/tracker/start', { tracking_uid: uid });
    if (d.ok) {
      _trackerCardMap[accountId] = uid;
      _showTrackerActive(accountId, uid);
      showToast(d.already ? `Already tracking ${uid}` : `Tracking ${uid}`, 'success');
      renderTrackerGrid(await _fetchTrackers());
    } else showToast(d.error || 'Failed', 'error');
  } catch (err) { showToast(err.message || 'Network error', 'error'); }
  finally { const b = $id(`btn-track-${accountId}`); if (b) { b.disabled = false; b.textContent = '📡'; } }
}
async function stopTrackerFromCard(accountId) {
  const uid = _trackerCardMap[accountId];
  if (!uid) return;
  try { await apiPost('/tracker/stop', { tracking_uid: uid }); } catch (_) {}
  delete _trackerCardMap[accountId];
  _hideTrackerActive(accountId);
  renderTrackerGrid(await _fetchTrackers());
  showToast(`Stopped tracking ${uid}`, 'info');
}
function _showTrackerActive(accId, uid) {
  $id(`track-uid-${accId}`)?.style.setProperty('display','none');
  $id(`btn-track-${accId}`)?.style.setProperty('display','none');
  const disp = $id(`trackuid-disp-${accId}`); if (disp) disp.textContent = uid;
  $id(`trackind-${accId}`)?.style.removeProperty('display');
}
function _hideTrackerActive(accId) {
  $id(`track-uid-${accId}`)?.style.removeProperty('display');
  $id(`btn-track-${accId}`)?.style.removeProperty('display');
  $id(`trackind-${accId}`)?.style.setProperty('display','none');
}

/* Add tracker from main input */
async function addTracker() {
  const input = $id('new-track-uid');
  const uid   = input?.value?.trim();
  if (!uid) { showToast('Enter a UID', 'warn'); return; }
  const btn = document.querySelector('.btn-cyan[onclick="addTracker()"]');
  if (btn) { btn.disabled = true; btn.textContent = '⏳'; }
  try {
    const d = await apiPost('/tracker/start', { tracking_uid: uid });
    if (d.ok) {
      if (input) input.value = '';
      showToast(d.already ? `Already tracking ${uid}` : `Now tracking ${uid}`, 'success');
      renderTrackerGrid(await _fetchTrackers());
    } else showToast(d.error || 'Failed', 'error');
  } catch (err) { showToast(err.message || 'Network error', 'error'); }
  finally { if (btn) { btn.disabled = false; btn.textContent = '+ Track'; } }
}

async function refreshTracker(uid) {
  const btn = document.querySelector(`.tcard-btn-ref[data-uid="${uid}"]`);
  if (btn) { btn.disabled = true; btn.textContent = '⏳'; }
  try {
    const d = await apiPost('/tracker/refresh', { tracking_uid: uid });
    if (d.ok && d.data) {
      const card = document.querySelector(`.tcard[data-uid="${uid}"]`);
      if (card) _updateTCard(card, d.data);
      showToast('Refreshed', 'success');
    } else showToast(d.error || 'Refresh failed', 'error');
  } catch (err) { showToast(err.message || 'Network error', 'error'); }
  finally { const b = document.querySelector(`.tcard-btn-ref[data-uid="${uid}"]`); if (b) { b.disabled = false; b.textContent = '↻'; } }
}

async function stopTrackerCard(uid) {
  try { await apiPost('/tracker/stop', { tracking_uid: uid }); } catch (_) {}
  for (const [accId, tuid] of Object.entries(_trackerCardMap)) {
    if (tuid === uid) { delete _trackerCardMap[accId]; _hideTrackerActive(parseInt(accId)); }
  }
  renderTrackerGrid(await _fetchTrackers());
  showToast(`Stopped tracking ${uid}`, 'info');
}

async function _fetchTrackers() {
  try {
    const d = await apiGet('/tracker/all');
    return d.ok ? (d.trackers || []) : [];
  } catch (_) { return []; }
}

/* Render grid */
function renderTrackerGrid(trackers) {
  const grid  = $id('tracker-grid');
  const empty = $id('tracker-empty');
  if (!grid) return;
  if (!trackers.length) {
    empty?.style.removeProperty('display');
    grid.querySelectorAll('.tcard').forEach(c => c.remove());
    return;
  }
  empty && (empty.style.display = 'none');

  const existing = new Set([...grid.querySelectorAll('.tcard')].map(c => c.dataset.uid));
  const incoming  = new Set(trackers.map(t => t.uid));

  // Remove stale
  existing.forEach(uid => {
    if (!incoming.has(uid)) grid.querySelector(`.tcard[data-uid="${uid}"]`)?.remove();
  });

  // Add or update
  const frag = document.createDocumentFragment();
  trackers.forEach(t => {
    const card = grid.querySelector(`.tcard[data-uid="${t.uid}"]`);
    if (card) { _updateTCard(card, t); }
    else {
      const tmp = document.createElement('div');
      tmp.innerHTML = _buildTCard(t);
      frag.appendChild(tmp.firstElementChild);
    }
  });
  grid.appendChild(frag);
}

/* ── Build tracker card ──────────────────────────────── */
function _stateInfo(t) {
  const s = t.tracking_state || (t.tracker_status === 'grinding' ? 'tracking' : 'idle');
  const labels = { tracking:'⚔️ Grinding', grinding:'⚔️ Grinding', idle:'😴 Idle', collecting:'📊 Collecting', max_level:'🏆 Max Level' };
  return { cls: s === 'tracking' ? 'grinding' : s, lbl: labels[s] || '😴 Idle' };
}
function _stateBadgeHtml(t) {
  const { cls, lbl } = _stateInfo(t);
  return `<span class="state-badge ${cls}">${lbl}</span>`;
}
function _confBadgeHtml(t) {
  const c  = t.confidence || 'low';
  const sc = t.confidence_score ?? 0;
  return `<span class="conf-badge conf-${c}" title="Confidence: ${sc}/100">${c.charAt(0).toUpperCase() + c.slice(1)}</span>`;
}

function _buildTCard(t) {
  const pct   = t.progress_pct ?? 0;
  const maxLv = t.max_level;
  const state = t.tracking_state || 'idle';
  const uid   = esc(t.uid);
  const collecting = (state === 'collecting');
  const smooth = t.smoothed_exp_per_hour ?? 0;
  const raw    = t.exp_per_hour ?? 0;
  const peak   = t.peak_exp_per_hour ?? 0;

  const progFill = maxLv
    ? `<div class="tcard-prog-fill" style="width:100%;background:var(--yellow)"></div>`
    : `<div class="tcard-prog-fill" style="width:${pct}%"></div>`;
  const expLbl = maxLv
    ? `<span class="tcard-exp-lbl" style="color:var(--yellow)">MAX LEVEL</span>`
    : `<span class="tcard-exp-lbl">${num(t.completed_exp)} / ${num(t.next_level_exp)} XP</span>`;
  const clan = t.clan_name ? `<span class="tcard-chip">⚔️ ${esc(t.clan_name)}</span>` : '';
  const hint = collecting
    ? `<div class="tcard-collecting">📊 Collecting… (${t.samples_count || 0}/3 samples)</div>`
    : '';

  return `<div class="tcard" data-uid="${uid}">
  <div class="tcard-head">
    <div class="tcard-id">
      <div class="tcard-name">${esc(t.nickname || t.uid)}</div>
      <div class="tcard-uid">${uid}</div>
    </div>
    <div class="tcard-badges">
      <span class="tag-region">${esc(t.region || '?')}</span>
      ${_stateBadgeHtml(t)}
      ${_confBadgeHtml(t)}
    </div>
    <div class="tcard-actions">
      <button class="tcard-btn-ref" data-uid="${uid}"
              onclick="refreshTracker('${uid}')" title="Refresh">↻</button>
      <button class="tcard-btn-close" onclick="stopTrackerCard('${uid}')" title="Stop">✕</button>
    </div>
  </div>
  <div class="tcard-level-row">
    <span class="tcard-lv">Lv <strong>${t.level}</strong></span>
    ${expLbl}
    <span class="tcard-pct">${pct}%</span>
  </div>
  <div class="tcard-prog-wrap">
    <div class="tcard-prog-track">${progFill}</div>
  </div>
  <div class="tcard-rate-row">
    <div class="tcard-rate-cell">
      <div class="tcard-rate-val smoothed" id="ts-smooth-${uid}">${num(smooth)}</div>
      <div class="tcard-rate-lbl">Smoothed / hr</div>
    </div>
    <div class="tcard-rate-cell">
      <div class="tcard-rate-val" id="ts-raw-${uid}">${num(raw)}</div>
      <div class="tcard-rate-lbl">Raw / hr</div>
    </div>
  </div>
  <div class="tcard-stats-row">
    <div class="tcard-stat">
      <div class="tcard-sv" id="ts-gain-${uid}">${num(t.exp_gain)}</div>
      <div class="tcard-sl">Gained</div>
    </div>
    <div class="tcard-stat">
      <div class="tcard-sv" id="ts-rem-${uid}">${num(t.remaining_exp)}</div>
      <div class="tcard-sl">Remaining</div>
    </div>
    <div class="tcard-stat">
      <div class="tcard-sv" id="ts-eta-${uid}">${esc(t.estimated_levelup || '—')}</div>
      <div class="tcard-sl">ETA</div>
    </div>
    <div class="tcard-stat">
      <div class="tcard-sv" id="ts-peak-${uid}">${num(peak)}</div>
      <div class="tcard-sl">Peak/hr</div>
    </div>
  </div>
  ${hint}
  <div class="tcard-footer">
    ${clan}
    <span class="tcard-chip">🏆 Rank ${t.rank ?? '?'}</span>
    <span class="tcard-chip">❤️ ${num(t.liked)}</span>
    <span class="tcard-chip tcard-chip-dur" id="ts-dur-${uid}">⏱ ${dur(t.session_duration_secs)}</span>
    <span class="tcard-chip tcard-chip-time">🕐 ${esc(t.last_checked || '—')}</span>
  </div>
  ${t.error ? `<div class="tcard-error">⚠️ ${esc(t.error)}</div>` : ''}
</div>`.trim();
}

/* Update tracker card in-place */
function _updateTCard(card, t) {
  const uid   = t.uid;
  const pct   = t.progress_pct ?? 0;
  const maxLv = t.max_level;
  const state = t.tracking_state || 'idle';

  // State badge
  const sb = card.querySelector('.state-badge');
  if (sb) { const tmp = document.createElement('div'); tmp.innerHTML = _stateBadgeHtml(t); sb.replaceWith(tmp.firstElementChild); }
  // Conf badge
  const cb = card.querySelector('.conf-badge');
  if (cb) { const tmp = document.createElement('div'); tmp.innerHTML = _confBadgeHtml(t); cb.replaceWith(tmp.firstElementChild); }

  // Progress
  const fill = card.querySelector('.tcard-prog-fill');
  if (fill) { fill.style.width = maxLv ? '100%' : `${pct}%`; fill.style.background = maxLv ? 'var(--yellow)' : ''; }
  const pctEl = card.querySelector('.tcard-pct'); if (pctEl) pctEl.textContent = pct + '%';
  const expEl = card.querySelector('.tcard-exp-lbl');
  if (expEl) {
    if (maxLv) { expEl.textContent = 'MAX LEVEL'; expEl.style.color = 'var(--yellow)'; }
    else { expEl.textContent = `${num(t.completed_exp)} / ${num(t.next_level_exp)} XP`; expEl.style.color = ''; }
  }
  const lvEl = card.querySelector('.tcard-lv strong'); if (lvEl) lvEl.textContent = t.level;
  const nmEl = card.querySelector('.tcard-name'); if (nmEl && t.nickname) nmEl.textContent = t.nickname;

  // Rates + stats
  const se = $id(`ts-smooth-${uid}`); if (se) se.textContent = num(t.smoothed_exp_per_hour ?? 0);
  const re = $id(`ts-raw-${uid}`);    if (re) re.textContent = num(t.exp_per_hour ?? 0);
  const ge = $id(`ts-gain-${uid}`);   if (ge) ge.textContent = num(t.exp_gain);
  const rm = $id(`ts-rem-${uid}`);    if (rm) rm.textContent = num(t.remaining_exp);
  const et = $id(`ts-eta-${uid}`);    if (et) et.textContent = t.estimated_levelup || '—';
  const pk = $id(`ts-peak-${uid}`);   if (pk) pk.textContent = num(t.peak_exp_per_hour ?? 0);
  const dd = $id(`ts-dur-${uid}`);    if (dd) dd.textContent = `⏱ ${dur(t.session_duration_secs)}`;

  // Collecting hint
  let hint = card.querySelector('.tcard-collecting');
  if (state === 'collecting') {
    if (!hint) {
      const h = document.createElement('div');
      h.className = 'tcard-collecting';
      card.querySelector('.tcard-stats-row')?.after(h);
      hint = h;
    }
    hint.textContent = `📊 Collecting… (${t.samples_count || 0}/3 samples)`;
  } else if (hint) hint.remove();

  // Error
  const errEl = card.querySelector('.tcard-error');
  if (t.error) {
    if (errEl) errEl.textContent = `⚠️ ${t.error}`;
    else card.insertAdjacentHTML('beforeend', `<div class="tcard-error">⚠️ ${esc(t.error)}</div>`);
  } else errEl?.remove();
}

/* Tracker poll every 10s */
async function pollTrackers() {
  if (document.hidden) return;
  renderTrackerGrid(await _fetchTrackers());
}
pollTrackers();
setInterval(pollTrackers, 10000);

/* ════════════════════════════════════════════════════════
   PAGE VISIBILITY — pause polls when tab hidden
   ════════════════════════════════════════════════════════ */
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    pollBotStatus();
    pollGlobalStats();
    pollTrackers();
  }
});

/* ════════════════════════════════════════════════════════
   CYCLE HISTORY CHART
   ════════════════════════════════════════════════════════ */
async function loadCycleHistory() {
  const days = $id('history-days')?.value || 7;
  try {
    const d = await apiGet(`/bot/cycle-history?days=${days}`);
    if (!d.ok) return;
    drawCycleChart(d.history || []);
  } catch (_) {}
}

function drawCycleChart(data) {
  const canvas = $id('cycle-chart');
  const empty  = $id('chart-empty');
  if (!canvas) return;

  if (!data.length) {
    canvas.style.display = 'none';
    if (empty) empty.style.display = '';
    return;
  }
  canvas.style.display = '';
  if (empty) empty.style.display = 'none';

  const dpr  = window.devicePixelRatio || 1;
  const W    = canvas.offsetWidth  || 600;
  const H    = canvas.offsetHeight || 200;
  canvas.width  = W * dpr;
  canvas.height = H * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const PAD   = { top: 20, right: 16, bottom: 48, left: 48 };
  const inner = { w: W - PAD.left - PAD.right, h: H - PAD.top - PAD.bottom };
  const max   = Math.max(...data.map(d => d.total_cycles), 1);
  const BAR   = Math.max(8, Math.min(40, (inner.w / data.length) * 0.6));
  const GAP   = inner.w / data.length;

  ctx.clearRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = 'rgba(255,255,255,.06)';
  ctx.lineWidth   = 1;
  const STEPS = 4;
  for (let i = 0; i <= STEPS; i++) {
    const y = PAD.top + inner.h - (i / STEPS) * inner.h;
    ctx.beginPath();
    ctx.moveTo(PAD.left, y);
    ctx.lineTo(PAD.left + inner.w, y);
    ctx.stroke();
    ctx.fillStyle = 'rgba(132,147,168,.7)';
    ctx.font      = '10px Inter, system-ui';
    ctx.textAlign = 'right';
    ctx.fillText(Math.round((i / STEPS) * max), PAD.left - 6, y + 3.5);
  }

  // Bars
  const grad = ctx.createLinearGradient(0, PAD.top, 0, PAD.top + inner.h);
  grad.addColorStop(0,   'rgba(0,212,255,.85)');
  grad.addColorStop(1,   'rgba(124,58,237,.4)');

  data.forEach((row, i) => {
    const bh   = (row.total_cycles / max) * inner.h;
    const x    = PAD.left + i * GAP + (GAP - BAR) / 2;
    const y    = PAD.top  + inner.h - bh;
    const r    = Math.min(4, BAR / 2);

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + BAR - r, y);
    ctx.quadraticCurveTo(x + BAR, y, x + BAR, y + r);
    ctx.lineTo(x + BAR, y + bh);
    ctx.lineTo(x, y + bh);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
    ctx.fill();

    // Cycle count label
    if (bh > 18) {
      ctx.fillStyle = 'rgba(255,255,255,.9)';
      ctx.font      = 'bold 10px Inter, system-ui';
      ctx.textAlign = 'center';
      ctx.fillText(row.total_cycles, x + BAR / 2, y + (bh < 30 ? -4 : 13));
    }

    // X-axis date label
    const label = row.date ? row.date.slice(5) : '';
    ctx.fillStyle = 'rgba(132,147,168,.85)';
    ctx.font      = '10px Inter, system-ui';
    ctx.textAlign = 'center';
    ctx.fillText(label, x + BAR / 2, H - PAD.bottom + 16);
  });
}

// Auto-load chart when Analytics tab opens
document.querySelectorAll('.nav-link[data-tab="analytics"]').forEach(l =>
  l.addEventListener('click', () => setTimeout(loadCycleHistory, 80))
);

/* ════════════════════════════════════════════════════════
   NOTIFICATION SETTINGS
   ════════════════════════════════════════════════════════ */
$id('form-notif')?.addEventListener('submit', async e => {
  e.preventDefault();
  const btn = e.target.querySelector('[type="submit"]');
  if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }
  try {
    const d = await apiPost('/settings/notifications', new FormData(e.target));
    if (d.ok) showToast('Notification settings saved!', 'success');
    else showToast(d.error || 'Failed to save', 'error');
  } catch (err) {
    showToast(err.message || 'Network error', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Save Settings'; }
  }
});

async function testNotification() {
  const btn = document.querySelector('.btn-outline[onclick="testNotification()"]');
  if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }
  try {
    const d = await apiPost('/settings/notifications/test', {});
    if (d.ok) showToast(d.message || 'Test sent!', 'success');
    else showToast(d.error || 'No channels configured', 'error');
  } catch (err) {
    showToast(err.message || 'Network error', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Send Test'; }
  }
}
