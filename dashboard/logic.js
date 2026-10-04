/* Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE. */
/*
 * Pure, DOM-free logic for the Display Mode dashboard.
 * Loaded as a classic <script> in the browser (exposes window.DashboardLogic)
 * and via require() in `node --test`.
 */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) {
    module.exports = api;
  } else {
    root.DashboardLogic = api;
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ---------- Escaping ----------

  const ESCAPES = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
    '`': '&#96;',
  };

  function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value).replace(/[&<>"'`]/g, (ch) => ESCAPES[ch]);
  }

  /** Marker for markup that has already been escaped by `html`. */
  class SafeHtml {
    constructor(text) {
      this.text = text;
    }
    toString() {
      return this.text;
    }
  }

  function interpolate(value) {
    if (value instanceof SafeHtml) return value.text;
    if (Array.isArray(value)) return value.map(interpolate).join('');
    return escapeHtml(value);
  }

  /**
   * Tagged template: every interpolated value is HTML-escaped unless it is
   * itself the result of `html` (SafeHtml). Arrays are joined.
   */
  function html(strings, ...values) {
    let out = strings[0];
    for (let i = 0; i < values.length; i += 1) {
      out += interpolate(values[i]) + strings[i + 1];
    }
    return new SafeHtml(out);
  }

  /** Only allow https links to github.com (or a subdomain); otherwise '#'. */
  function safeGithubUrl(url) {
    try {
      const parsed = new URL(String(url));
      const host = parsed.hostname.toLowerCase();
      if (parsed.protocol === 'https:' && (host === 'github.com' || host.endsWith('.github.com'))) {
        return parsed.href;
      }
    } catch (_err) {
      // fall through
    }
    return '#';
  }

  // ---------- PR helpers ----------

  function isWip(title) {
    return /^\s*\[WIP\]/i.test(String(title || ''));
  }

  function isCopilotAuthor(user) {
    if (!user || typeof user.login !== 'string') return false;
    return /copilot/i.test(user.login);
  }

  function compareOldestFirst(a, b) {
    const ta = Date.parse(a.created_at) || 0;
    const tb = Date.parse(b.created_at) || 0;
    if (ta !== tb) return ta - tb;
    return (a.number || 0) - (b.number || 0);
  }

  /**
   * "Waiting on you": open PRs that are no longer WIP and are either draft
   * (needs "Ready for review") or ready (needs review / merge). Oldest first.
   */
  function waitingOnYou(prs) {
    return (prs || [])
      .filter((pr) => pr && (pr.state === undefined || pr.state === 'open') && !isWip(pr.title))
      .map((pr) => ({
        pr,
        reason: pr.draft ? 'Draft: mark ready for review' : 'Ready: review and merge',
      }))
      .sort((a, b) => compareOldestFirst(a.pr, b.pr));
  }

  /**
   * When several open PRs share a base branch, number them oldest first.
   * Returns { [prNumber]: { position, total, base } } for PRs in such groups.
   */
  function mergeOrder(prs) {
    const groups = new Map();
    for (const pr of prs || []) {
      const base = pr && pr.base && pr.base.ref;
      if (!base) continue;
      if (!groups.has(base)) groups.set(base, []);
      groups.get(base).push(pr);
    }
    const result = {};
    for (const [base, group] of groups) {
      if (group.length < 2) continue;
      group.slice().sort(compareOldestFirst).forEach((pr, idx) => {
        result[pr.number] = { position: idx + 1, total: group.length, base };
      });
    }
    return result;
  }

  function ordinal(n) {
    const num = Math.trunc(Number(n));
    const mod100 = num % 100;
    if (mod100 >= 11 && mod100 <= 13) return `${num}th`;
    switch (num % 10) {
      case 1:
        return `${num}st`;
      case 2:
        return `${num}nd`;
      case 3:
        return `${num}rd`;
      default:
        return `${num}th`;
    }
  }

  // ---------- Status rollup ----------

  const FAIL_CONCLUSIONS = new Set(['failure', 'timed_out', 'cancelled', 'startup_failure', 'stale']);
  const PASS_CONCLUSIONS = new Set(['success', 'neutral', 'skipped']);

  /** Check run or workflow run -> 'pass' | 'fail' | 'pending'. */
  function runState(run) {
    if (!run || run.status !== 'completed') return 'pending';
    if (PASS_CONCLUSIONS.has(run.conclusion)) return 'pass';
    if (FAIL_CONCLUSIONS.has(run.conclusion)) return 'fail';
    // action_required (e.g. awaiting approval) or unknown conclusions.
    return 'pending';
  }

  /** Legacy commit status -> 'pass' | 'fail' | 'pending'. */
  function commitStatusState(status) {
    const state = status && status.state;
    if (state === 'success') return 'pass';
    if (state === 'failure' || state === 'error') return 'fail';
    return 'pending';
  }

  /**
   * Combine check runs and the combined commit status into one state:
   * any fail -> 'fail'; else any pending -> 'pending'; else any pass -> 'pass';
   * nothing reported -> 'none'.
   */
  function rollupStatus(checkRuns, combinedStatus) {
    const states = [];
    for (const run of checkRuns || []) states.push(runState(run));
    const statuses = (combinedStatus && combinedStatus.statuses) || [];
    for (const status of statuses) states.push(commitStatusState(status));
    if (states.includes('fail')) return 'fail';
    if (states.includes('pending')) return 'pending';
    if (states.includes('pass')) return 'pass';
    return 'none';
  }

  /**
   * Decide whether a cached check result for a head SHA can be reused.
   * pass/fail are final for a given SHA. 'none' is reused once we looked at
   * least 15 minutes after the PR's last update (CI would have started).
   */
  function canReuseChecks(cached, prUpdatedAt) {
    if (!cached) return false;
    if (cached.state === 'pass' || cached.state === 'fail') return true;
    if (cached.state === 'none') {
      const updated = Date.parse(prUpdatedAt) || 0;
      return cached.fetchedAt - updated >= 15 * 60 * 1000;
    }
    return false;
  }

  // ---------- Time ----------

  function relativeTime(iso, nowMs) {
    const then = Date.parse(iso);
    if (Number.isNaN(then)) return 'unknown';
    const now = nowMs === undefined ? Date.now() : nowMs;
    const seconds = Math.round((now - then) / 1000);
    if (seconds < -60) return 'in the future';
    if (seconds < 45) return 'just now';
    const minutes = Math.max(1, Math.round(seconds / 60));
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} d ago`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months} mo ago`;
    return `${Math.floor(days / 365)} y ago`;
  }

  // ---------- Rate limit & API helpers ----------

  /** Parse the page number of rel="last" from a GitHub Link header. */
  function parseLastPage(linkHeader) {
    if (!linkHeader) return null;
    for (const part of String(linkHeader).split(',')) {
      if (!/rel="last"/.test(part)) continue;
      const match = part.match(/[?&]page=(\d+)/);
      if (match) return Number(match[1]);
    }
    return null;
  }

  /** 'ok' | 'low' | 'exhausted' | 'unknown' */
  function rateLimitLevel(remaining, lowThreshold) {
    if (remaining === null || remaining === undefined || Number.isNaN(Number(remaining))) return 'unknown';
    const left = Number(remaining);
    if (left <= 0) return 'exhausted';
    if (left <= (lowThreshold === undefined ? 10 : lowThreshold)) return 'low';
    return 'ok';
  }

  /** True when `cost` requests can be spent while keeping `reserve` in hand. */
  function canSpend(remaining, cost, reserve) {
    if (remaining === null || remaining === undefined) return true;
    return Number(remaining) - cost >= (reserve || 0);
  }

  const ACTIVITY_EVERY = 5;
  const META_EVERY = 30;

  /**
   * Which data tiers to fetch on this refresh. Open PRs (and their checks)
   * every refresh; Actions runs and closed PRs every 5th; repo metadata
   * (default branch, branch count) every 30th. Manual refreshes and the
   * first refresh fetch everything.
   */
  function tiersDue(tick, manual) {
    const all = Boolean(manual) || tick === 0;
    return {
      pulls: true,
      activity: all || tick % ACTIVITY_EVERY === 0,
      meta: all || tick % META_EVERY === 0,
    };
  }

  /**
   * Average requests per automatic refresh: 1 open-PR list per repo, the
   * amortised activity (2 requests) and metadata (2 requests) tiers, plus
   * 2 requests (check runs + statuses) per PR whose checks must be fetched.
   */
  function estimateRefreshCost(repoCount, checksToFetch) {
    const perRepo = 1 + 2 / ACTIVITY_EVERY + 2 / META_EVERY;
    return repoCount * perRepo + 2 * (checksToFetch || 0);
  }

  /**
   * Spread the remaining unauthenticated budget until the reset time:
   * never refresh faster than `baseIntervalMs`, slow down when the budget
   * would not last, and wait for the reset when it is used up.
   */
  function pacedIntervalMs(remaining, resetEpochSec, nowMs, cost, baseIntervalMs, reserve) {
    if (remaining === null || remaining === undefined || !resetEpochSec) return baseIntervalMs;
    const windowMs = Math.max(0, resetEpochSec * 1000 - nowMs);
    const usable = Number(remaining) - (reserve || 0);
    if (usable < cost) return Math.max(windowMs, baseIntervalMs);
    const affordable = Math.max(1, Math.floor(usable / Math.max(cost, 1)));
    return Math.max(baseIntervalMs, Math.ceil(windowMs / affordable));
  }

  /** Keep only the PR fields the dashboard uses (small localStorage cache). */
  function trimPull(pr) {
    const head = pr.head || {};
    const headRepo = head.repo && head.repo.full_name;
    const baseRepo = pr.base && pr.base.repo && pr.base.repo.full_name;
    return {
      number: pr.number,
      title: pr.title,
      state: pr.state,
      draft: Boolean(pr.draft),
      html_url: pr.html_url,
      created_at: pr.created_at,
      updated_at: pr.updated_at,
      closed_at: pr.closed_at || null,
      merged_at: pr.merged_at || null,
      user: pr.user ? { login: pr.user.login, type: pr.user.type } : null,
      base: { ref: pr.base && pr.base.ref },
      head: {
        ref: head.ref,
        sha: head.sha,
        label: headRepo && baseRepo && headRepo !== baseRepo ? head.label : head.ref,
      },
    };
  }

  function trimRun(run) {
    return {
      id: run.id,
      name: run.name,
      display_title: run.display_title,
      status: run.status,
      conclusion: run.conclusion,
      event: run.event,
      head_branch: run.head_branch,
      html_url: run.html_url,
      created_at: run.created_at,
      updated_at: run.updated_at,
    };
  }

  return {
    escapeHtml,
    SafeHtml,
    html,
    safeGithubUrl,
    isWip,
    isCopilotAuthor,
    waitingOnYou,
    mergeOrder,
    ordinal,
    runState,
    commitStatusState,
    rollupStatus,
    canReuseChecks,
    relativeTime,
    parseLastPage,
    rateLimitLevel,
    canSpend,
    tiersDue,
    estimateRefreshCost,
    pacedIntervalMs,
    trimPull,
    trimRun,
  };
});
