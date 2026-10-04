/* Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE. */
(function () {
  'use strict';

  // ---- Config: add more repositories here ("owner/name") ----
  const REPOS = [
    'cvessell-create/VessellFramework_Local_Rebuild',
    'cvessell-create/hail-to-the-analyst',
  ];

  const API = 'https://api.github.com';
  const REFRESH_MS = 2 * 60 * 1000;
  const RESERVE = 6; // requests kept back for a manual refresh
  const LOW_THRESHOLD = 15;
  const CACHE_PREFIX = 'vf-display-mode:v1:';

  const L = window.DashboardLogic;
  const html = L.html;

  const els = {
    refresh: document.getElementById('refresh'),
    lastUpdated: document.getElementById('last-updated'),
    banner: document.getElementById('banner'),
    content: document.getElementById('content'),
  };

  const state = {
    repos: {},
    rate: { remaining: null, limit: null, reset: null },
    tick: 0,
    busy: false,
    lastRefreshAt: null,
    nextAt: null,
    timer: null,
    dueWhileHidden: false,
    problem: null,
    reserve: RESERVE,
  };

  class BudgetError extends Error {}

  // ---------- Cache ----------

  function emptyEntry() {
    return { meta: null, open: null, closed: null, runs: null, checks: {}, savedAt: null, stale: false, error: null };
  }

  function loadCache(full) {
    try {
      const raw = window.localStorage.getItem(CACHE_PREFIX + full);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === 'object' ? Object.assign(emptyEntry(), parsed) : null;
    } catch (_err) {
      return null;
    }
  }

  function saveCache(full, entry) {
    try {
      const copy = Object.assign({}, entry, { stale: false, error: null });
      window.localStorage.setItem(CACHE_PREFIX + full, JSON.stringify(copy));
    } catch (_err) {
      // Storage full or disabled (e.g. private mode): keep working in memory.
    }
  }

  // ---------- GitHub API ----------

  function repoPath(full) {
    return full.split('/').map(encodeURIComponent).join('/');
  }

  function knownRemaining() {
    const { remaining, reset } = state.rate;
    if (remaining === null) return null;
    if (reset && Date.now() > reset * 1000) return null; // window has reset
    return remaining;
  }

  function readRate(headers) {
    const resource = headers.get('x-ratelimit-resource');
    if (resource && resource !== 'core') return;
    const remaining = headers.get('x-ratelimit-remaining');
    const limit = headers.get('x-ratelimit-limit');
    const reset = headers.get('x-ratelimit-reset');
    if (remaining !== null) state.rate.remaining = Number(remaining);
    if (limit !== null) state.rate.limit = Number(limit);
    if (reset !== null) state.rate.reset = Number(reset);
  }

  async function gh(path) {
    if (!L.canSpend(knownRemaining(), 1, state.reserve)) {
      throw new BudgetError('API rate limit nearly used up');
    }
    let res;
    try {
      res = await fetch(API + path, {
        headers: { Accept: 'application/vnd.github+json' },
        cache: 'no-store',
        referrerPolicy: 'no-referrer',
      });
    } catch (_err) {
      throw new Error('network error (offline or GitHub unreachable)');
    }
    readRate(res.headers);
    if ((res.status === 403 || res.status === 429) && (state.rate.remaining === 0 || res.headers.get('retry-after'))) {
      state.rate.remaining = 0;
      throw new BudgetError('GitHub API rate limit reached');
    }
    if (!res.ok) throw new Error(`GitHub API returned ${res.status}`);
    return { data: await res.json(), headers: res.headers };
  }

  async function primeRateLimit() {
    // /rate_limit does not count against the limit.
    try {
      const res = await fetch(API + '/rate_limit', { cache: 'no-store', referrerPolicy: 'no-referrer' });
      if (!res.ok) return;
      const body = await res.json();
      const core = body && body.resources && body.resources.core;
      if (core) {
        state.rate.remaining = core.remaining;
        state.rate.limit = core.limit;
        state.rate.reset = core.reset;
      }
    } catch (_err) {
      // Ignore: the first real request will report the limit.
    }
  }

  async function refreshRepo(full, tiers) {
    const entry = state.repos[full];
    const base = `/repos/${repoPath(full)}`;
    const now = () => Date.now();

    if (tiers.meta || !entry.meta) {
      const repo = await gh(base);
      const branches = await gh(`${base}/branches?per_page=1`);
      const lastPage = L.parseLastPage(branches.headers.get('link'));
      entry.meta = {
        default_branch: repo.data.default_branch,
        branchCount: lastPage === null ? (Array.isArray(branches.data) ? branches.data.length : null) : lastPage,
        fetchedAt: now(),
      };
    }

    const open = await gh(`${base}/pulls?state=open&sort=created&direction=asc&per_page=50`);
    entry.open = { items: open.data.map(L.trimPull), fetchedAt: now() };

    if (tiers.activity || !entry.closed || !entry.runs) {
      const closed = await gh(`${base}/pulls?state=closed&sort=updated&direction=desc&per_page=10`);
      entry.closed = { items: closed.data.map(L.trimPull), fetchedAt: now() };
      const runs = await gh(`${base}/actions/runs?per_page=5`);
      entry.runs = { items: (runs.data.workflow_runs || []).map(L.trimRun), fetchedAt: now() };
    }

    const liveShas = new Set();
    for (const pr of entry.open.items) {
      const sha = pr.head && pr.head.sha;
      if (!sha) continue;
      liveShas.add(sha);
      if (L.canReuseChecks(entry.checks[sha], pr.updated_at)) continue;
      const shaPath = encodeURIComponent(sha);
      const runs = await gh(`${base}/commits/${shaPath}/check-runs?per_page=100`);
      const status = await gh(`${base}/commits/${shaPath}/status`);
      entry.checks[sha] = { state: L.rollupStatus(runs.data.check_runs, status.data), fetchedAt: now() };
    }
    for (const sha of Object.keys(entry.checks)) {
      if (!liveShas.has(sha)) delete entry.checks[sha];
    }
  }

  async function refresh(manual) {
    if (state.busy) return;
    state.busy = true;
    state.reserve = manual ? 0 : RESERVE;
    els.refresh.disabled = true;
    els.refresh.textContent = 'Refreshing…';
    const tiers = L.tiersDue(state.tick, manual);
    const problems = [];
    for (const full of REPOS) {
      const entry = state.repos[full];
      try {
        await refreshRepo(full, tiers);
        entry.stale = false;
        entry.error = null;
        entry.savedAt = Date.now();
        saveCache(full, entry);
      } catch (err) {
        entry.stale = Boolean(entry.savedAt);
        entry.error = err instanceof BudgetError ? 'rate limit: paused to save requests' : err.message;
        problems.push({ full, budget: err instanceof BudgetError, message: err.message });
      }
    }
    state.problem = problems.length ? problems : null;
    state.tick += 1;
    state.lastRefreshAt = Date.now();
    state.busy = false;
    els.refresh.disabled = false;
    els.refresh.textContent = 'Refresh';
    render();
    schedule();
  }

  // ---------- Scheduling ----------

  function checksDueNext() {
    let count = 0;
    for (const full of REPOS) {
      const entry = state.repos[full];
      if (!entry.open) continue;
      for (const pr of entry.open.items) {
        if (pr.head && pr.head.sha && !L.canReuseChecks(entry.checks[pr.head.sha], pr.updated_at)) count += 1;
      }
    }
    return count;
  }

  function schedule() {
    window.clearTimeout(state.timer);
    const cost = L.estimateRefreshCost(REPOS.length, checksDueNext());
    const delay = L.pacedIntervalMs(knownRemaining(), state.rate.reset, Date.now(), cost, REFRESH_MS, RESERVE);
    state.nextAt = Date.now() + delay;
    state.timer = window.setTimeout(autoRefresh, delay);
    renderStatus();
  }

  function autoRefresh() {
    if (document.hidden) {
      state.dueWhileHidden = true;
      return;
    }
    refresh(false);
  }

  // ---------- Rendering ----------

  function clock(ms) {
    return new Date(ms).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function iso(ms) {
    return new Date(ms).toISOString();
  }

  function renderStatus() {
    const now = Date.now();
    const parts = [];
    if (state.lastRefreshAt) {
      parts.push(`Last updated ${clock(state.lastRefreshAt)} (${L.relativeTime(iso(state.lastRefreshAt), now)})`);
    } else {
      parts.push(state.busy ? 'Loading…' : 'Not refreshed yet');
    }
    if (state.nextAt && !state.busy) parts.push(`next auto-refresh ~${clock(state.nextAt)}`);
    const remaining = knownRemaining();
    if (remaining !== null) {
      parts.push(`API ${remaining}/${state.rate.limit || 60} left, resets ${clock(state.rate.reset * 1000)}`);
    }
    els.lastUpdated.textContent = parts.join(' · ');

    const messages = [];
    let level = 'low';
    const rateLevel = L.rateLimitLevel(remaining, LOW_THRESHOLD);
    const resetAt = state.rate.reset ? clock(state.rate.reset * 1000) : 'the top of the hour';
    if (rateLevel === 'exhausted') {
      level = 'exhausted';
      messages.push(`GitHub's free API limit (60 requests/hour) is used up. Showing saved data marked STALE. It resets at ${resetAt}.`);
    } else if (rateLevel === 'low') {
      messages.push(`API requests running low: ${remaining} left until ${resetAt}. Auto-refresh has slowed down to save requests.`);
    }
    if (state.problem) {
      const nonBudget = state.problem.filter((p) => !p.budget);
      if (nonBudget.length) {
        level = level === 'exhausted' ? level : 'error';
        messages.push(`Couldn't refresh ${nonBudget.map((p) => `${p.full} (${p.message})`).join(', ')}. Showing saved data.`);
      } else if (rateLevel === 'ok' || rateLevel === 'unknown') {
        messages.push('Some data was not refreshed to stay within the API rate limit. Showing saved data.');
      }
    }
    if (messages.length) {
      els.banner.hidden = false;
      els.banner.className = `banner ${level}`;
      els.banner.textContent = messages.join(' ');
    } else {
      els.banner.hidden = true;
      els.banner.textContent = '';
    }
  }

  const CHECK_LABELS = {
    pass: '✓ Checks pass',
    fail: '✗ Checks failing',
    pending: '● Checks pending',
    none: '– No checks',
    unknown: '? Checks not loaded',
  };

  function prUrl(full, number, suffix) {
    return L.safeGithubUrl(`https://github.com/${repoPath(full)}/pull/${Number(number)}${suffix || ''}`);
  }

  function actionLink(href, label, aria) {
    return html`<a class="btn" href="${href}" target="_blank" rel="noopener noreferrer" aria-label="${aria}">${label}</a>`;
  }

  function prCard(full, pr, order, check, reason, now) {
    const status = check ? check.state : 'unknown';
    const wip = L.isWip(pr.title);
    const author = pr.user ? pr.user.login : 'unknown';
    const copilot = L.isCopilotAuthor(pr.user);
    const repoName = full.split('/')[1];
    return html`<article class="card${reason ? ' waiting' : ''}" aria-label="Pull request #${pr.number} in ${repoName}">
  <div class="card-top">
    <span class="num">#${pr.number}</span>
    ${pr.draft ? html`<span class="badge badge-draft">Draft</span>` : html`<span class="badge badge-ready">Ready</span>`}
    ${wip ? html`<span class="badge badge-wip">WIP</span>` : ''}
    <span class="badge badge-${status}">${CHECK_LABELS[status] || CHECK_LABELS.unknown}</span>
    ${order ? html`<span class="badge badge-order" title="${order.total} open PRs target ${order.base}">Merge ${L.ordinal(order.position)}</span>` : ''}
  </div>
  <h3>${pr.title}</h3>
  ${reason ? html`<p class="reason">${reason}</p>` : ''}
  <p class="meta"><span class="sr-only">Merges into </span><code>${pr.base.ref}</code> ← <span class="sr-only">from </span><code>${pr.head.label || pr.head.ref}</code></p>
  <p class="meta">${reason ? html`${repoName} · ` : ''}by ${author} ${copilot ? html`<span class="badge badge-copilot">Copilot agent</span>` : ''} · updated ${L.relativeTime(pr.updated_at, now)}</p>
  <div class="actions">
    ${actionLink(prUrl(full, pr.number), 'Open PR', `Open pull request #${pr.number} on GitHub`)}
    ${actionLink(prUrl(full, pr.number, '/files'), 'Files changed', `Files changed in #${pr.number}`)}
    ${actionLink(prUrl(full, pr.number, '/checks'), 'Checks', `Checks for #${pr.number}`)}
    ${actionLink('https://github.com/copilot', 'Ask Copilot', `Ask Copilot about #${pr.number}`)}
  </div>
</article>`;
  }

  function runBadge(run) {
    const s = L.runState(run);
    if (s === 'pass') return html`<span class="badge badge-pass">✓ Success</span>`;
    if (s === 'fail') return html`<span class="badge badge-fail">✗ ${run.conclusion === 'cancelled' ? 'Cancelled' : 'Failed'}</span>`;
    if (run.conclusion === 'action_required') return html`<span class="badge badge-pending">⚠ Needs approval</span>`;
    const label = run.status === 'in_progress' ? 'Running' : run.status === 'queued' ? 'Queued' : run.status || 'Pending';
    return html`<span class="badge badge-pending">● ${label}</span>`;
  }

  function runsList(runs, now) {
    if (!runs || !runs.items.length) return html`<p class="empty">No workflow runs.</p>`;
    return html`<ul class="list">${runs.items.map((run) => html`<li><a href="${L.safeGithubUrl(run.html_url)}" target="_blank" rel="noopener noreferrer">
  <span class="line1">${runBadge(run)} <strong>${run.name}</strong></span>
  <span class="line2">${run.display_title} · ${run.head_branch} · ${run.event} · ${L.relativeTime(run.created_at, now)}</span>
</a></li>`)}</ul>`;
  }

  function closedList(full, closed, now) {
    if (!closed || !closed.items.length) return html`<p class="empty">No recently closed pull requests.</p>`;
    return html`<ul class="list">${closed.items.map((pr) => html`<li><a href="${prUrl(full, pr.number)}" target="_blank" rel="noopener noreferrer">
  <span class="line1">${pr.merged_at ? html`<span class="badge badge-merged">Merged</span>` : html`<span class="badge badge-closed">Closed</span>`} <strong>#${pr.number}</strong> ${pr.title}</span>
  <span class="line2">by ${pr.user ? pr.user.login : 'unknown'} · ${pr.merged_at ? 'merged' : 'closed'} ${L.relativeTime(pr.merged_at || pr.closed_at, now)} · into ${pr.base.ref}</span>
</a></li>`)}</ul>`;
  }

  function repoSection(full, index, now) {
    const entry = state.repos[full];
    const headingId = `repo-${index}`;
    const repoUrl = L.safeGithubUrl(`https://github.com/${repoPath(full)}`);
    if (!entry.open) {
      return html`<section class="block repo" aria-labelledby="${headingId}">
  <div class="block-head"><h2 id="${headingId}"><a href="${repoUrl}" target="_blank" rel="noopener noreferrer">${full}</a></h2></div>
  <p class="empty">${entry.error ? `Couldn't load yet: ${entry.error}` : 'Loading…'}</p>
</section>`;
    }
    const order = L.mergeOrder(entry.open.items);
    const meta = entry.meta || {};
    const branchText = meta.branchCount === null || meta.branchCount === undefined ? '? branches' : `${meta.branchCount} branch${meta.branchCount === 1 ? '' : 'es'}`;
    return html`<section class="block repo" aria-labelledby="${headingId}">
  <div class="block-head">
    <h2 id="${headingId}"><a href="${repoUrl}" target="_blank" rel="noopener noreferrer">${full}</a></h2>
    ${entry.stale ? html`<span class="badge badge-stale">STALE</span>` : ''}
  </div>
  <p class="meta">Default branch <code>${meta.default_branch || '?'}</code> · ${branchText}</p>
  ${entry.stale && entry.savedAt ? html`<p class="meta">STALE: showing saved data from ${clock(entry.savedAt)} (${L.relativeTime(iso(entry.savedAt), now)}).</p>` : ''}
  ${entry.error ? html`<p class="meta">Last refresh problem: ${entry.error}</p>` : ''}
  <h3 class="subhead">Open pull requests (${entry.open.items.length})</h3>
  ${entry.open.items.length
    ? entry.open.items.map((pr) => prCard(full, pr, order[pr.number], entry.checks[pr.head.sha], null, now))
    : html`<p class="empty">No open pull requests.</p>`}
  <h3 class="subhead">Latest Actions runs</h3>
  ${runsList(entry.runs, now)}
  <h3 class="subhead">Recently merged / closed</h3>
  ${closedList(full, entry.closed, now)}
</section>`;
  }

  function render() {
    const now = Date.now();
    const waiting = [];
    for (const full of REPOS) {
      const entry = state.repos[full];
      if (!entry.open) continue;
      const order = L.mergeOrder(entry.open.items);
      for (const item of L.waitingOnYou(entry.open.items)) {
        waiting.push({ full, pr: item.pr, reason: item.reason, order: order[item.pr.number], check: entry.checks[item.pr.head.sha] });
      }
    }
    waiting.sort((a, b) => (Date.parse(a.pr.created_at) || 0) - (Date.parse(b.pr.created_at) || 0));
    const view = html`<section class="block" aria-labelledby="waiting-heading">
  <div class="block-head">
    <h2 id="waiting-heading">Waiting on you</h2>
    <span class="muted">${waiting.length} pull request${waiting.length === 1 ? '' : 's'}, oldest first</span>
  </div>
  ${waiting.length
    ? waiting.map((w) => prCard(w.full, w.pr, w.order, w.check, w.reason, now))
    : html`<p class="empty">Nothing is waiting on you right now.</p>`}
</section>
${REPOS.map((full, index) => repoSection(full, index, now))}`;
    // All API text has been escaped by the `html` template.
    els.content.innerHTML = view.toString();
    renderStatus();
  }

  // ---------- Pull to refresh ----------

  function setupPullToRefresh() {
    let startY = null;
    let pulling = false;
    window.addEventListener('touchstart', (event) => {
      startY = window.scrollY <= 0 && event.touches.length === 1 ? event.touches[0].clientY : null;
      pulling = false;
    }, { passive: true });
    window.addEventListener('touchmove', (event) => {
      if (startY === null) return;
      pulling = event.touches[0].clientY - startY > 80;
      document.body.classList.toggle('pulling', pulling);
    }, { passive: true });
    window.addEventListener('touchend', () => {
      document.body.classList.remove('pulling');
      if (pulling) refresh(true);
      startY = null;
      pulling = false;
    });
  }

  // ---------- Start ----------

  async function start() {
    for (const full of REPOS) {
      const cached = loadCache(full);
      state.repos[full] = cached ? Object.assign(cached, { stale: true }) : emptyEntry();
    }
    render();
    els.refresh.addEventListener('click', () => refresh(true));
    setupPullToRefresh();
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) return;
      if (state.dueWhileHidden || (state.nextAt && Date.now() >= state.nextAt)) {
        state.dueWhileHidden = false;
        refresh(false);
      } else {
        render();
      }
    });
    // Keep relative times fresh without spending API requests.
    window.setInterval(() => {
      if (document.hidden || state.busy) return;
      if (els.content.contains(document.activeElement)) renderStatus();
      else render();
    }, 30 * 1000);
    await primeRateLimit();
    await refresh(false);
  }

  start();
})();
