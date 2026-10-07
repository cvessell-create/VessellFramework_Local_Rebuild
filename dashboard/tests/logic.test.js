// Copyright 2026 Christopher R. Vessell. Licensed under the Apache License, Version 2.0. See LICENSE.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const L = require(path.join(__dirname, '..', 'logic.js'));

const NOW = Date.parse('2026-10-04T12:00:00Z');

function pr(number, created, extra) {
  return Object.assign(
    { number, title: `PR ${number}`, state: 'open', draft: false, created_at: created, base: { ref: 'master' } },
    extra || {},
  );
}

test('escapeHtml escapes markup characters and handles null', () => {
  assert.equal(L.escapeHtml('<img src=x onerror="a()">&\'`'), '&lt;img src=x onerror=&quot;a()&quot;&gt;&amp;&#39;&#96;');
  assert.equal(L.escapeHtml(null), '');
  assert.equal(L.escapeHtml(undefined), '');
  assert.equal(L.escapeHtml(42), '42');
});

test('html template escapes interpolations but not nested html', () => {
  const title = '<script>alert(1)</script>';
  const inner = L.html`<b>${title}</b>`;
  const outer = L.html`<p>${inner}${[L.html`<i>${'a&b'}</i>`, '<x>']}</p>`;
  assert.equal(String(outer), '<p><b>&lt;script&gt;alert(1)&lt;/script&gt;</b><i>a&amp;b</i>&lt;x&gt;</p>');
  assert.equal(String(L.html`<a title="${'" onclick="x'}">`), '<a title="&quot; onclick=&quot;x">');
});

test('safeGithubUrl only allows https github.com links', () => {
  assert.equal(L.safeGithubUrl('https://github.com/o/r/pull/1'), 'https://github.com/o/r/pull/1');
  assert.equal(L.safeGithubUrl('javascript:alert(1)'), '#');
  assert.equal(L.safeGithubUrl('http://github.com/o/r'), '#');
  assert.equal(L.safeGithubUrl('https://github.com.evil.example/x'), '#');
  assert.equal(L.safeGithubUrl(undefined), '#');
});

test('isWip detects a leading [WIP] tag only', () => {
  assert.equal(L.isWip('[WIP] Build dashboard'), true);
  assert.equal(L.isWip('  [wip] lower case'), true);
  assert.equal(L.isWip('Build dashboard [WIP]'), false);
  assert.equal(L.isWip('Build dashboard'), false);
  assert.equal(L.isWip(undefined), false);
});

test('isCopilotAuthor marks Copilot bot logins', () => {
  assert.equal(L.isCopilotAuthor({ login: 'Copilot', type: 'Bot' }), true);
  assert.equal(L.isCopilotAuthor({ login: 'copilot-swe-agent[bot]', type: 'Bot' }), true);
  assert.equal(L.isCopilotAuthor({ login: 'cvessell-create', type: 'User' }), false);
  assert.equal(L.isCopilotAuthor(null), false);
});

test('waitingOnYou excludes WIP and closed PRs and sorts oldest first', () => {
  const list = L.waitingOnYou([
    pr(3, '2026-10-03T00:00:00Z', { draft: true }),
    pr(1, '2026-10-01T00:00:00Z', { title: '[WIP] still building' }),
    pr(2, '2026-10-02T00:00:00Z'),
    pr(4, '2026-09-01T00:00:00Z', { state: 'closed' }),
  ]);
  assert.deepEqual(list.map((item) => item.pr.number), [2, 3]);
  assert.match(list[0].reason, /review/i);
  assert.match(list[1].reason, /draft/i);
});

test('mergeOrder numbers PRs sharing a base branch oldest first', () => {
  const order = L.mergeOrder([
    pr(5, '2026-10-03T00:00:00Z'),
    pr(2, '2026-10-01T00:00:00Z'),
    pr(3, '2026-10-02T00:00:00Z'),
    pr(9, '2026-10-01T00:00:00Z', { base: { ref: 'main' } }),
  ]);
  assert.deepEqual(order[2], { position: 1, total: 3, base: 'master' });
  assert.deepEqual(order[3], { position: 2, total: 3, base: 'master' });
  assert.deepEqual(order[5], { position: 3, total: 3, base: 'master' });
  assert.equal(order[9], undefined, 'single PR on a base gets no hint');
});

test('mergeOrder breaks timestamp ties by PR number', () => {
  const order = L.mergeOrder([pr(8, '2026-10-01T00:00:00Z'), pr(7, '2026-10-01T00:00:00Z')]);
  assert.equal(order[7].position, 1);
  assert.equal(order[8].position, 2);
});

test('ordinal produces English ordinals', () => {
  assert.deepEqual([1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 101, 111].map(L.ordinal),
    ['1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd', '23rd', '101st', '111th']);
});

test('runState maps check/workflow runs', () => {
  assert.equal(L.runState({ status: 'in_progress', conclusion: null }), 'pending');
  assert.equal(L.runState({ status: 'queued' }), 'pending');
  assert.equal(L.runState({ status: 'completed', conclusion: 'success' }), 'pass');
  assert.equal(L.runState({ status: 'completed', conclusion: 'skipped' }), 'pass');
  assert.equal(L.runState({ status: 'completed', conclusion: 'failure' }), 'fail');
  assert.equal(L.runState({ status: 'completed', conclusion: 'timed_out' }), 'fail');
  assert.equal(L.runState({ status: 'completed', conclusion: 'action_required' }), 'pending');
});

test('rollupStatus combines check runs and commit statuses', () => {
  const ok = { status: 'completed', conclusion: 'success' };
  const bad = { status: 'completed', conclusion: 'failure' };
  const running = { status: 'in_progress', conclusion: null };
  assert.equal(L.rollupStatus([], { state: 'pending', statuses: [] }), 'none');
  assert.equal(L.rollupStatus(undefined, undefined), 'none');
  assert.equal(L.rollupStatus([ok, ok], { statuses: [] }), 'pass');
  assert.equal(L.rollupStatus([ok, running], { statuses: [] }), 'pending');
  assert.equal(L.rollupStatus([running, bad], { statuses: [] }), 'fail');
  assert.equal(L.rollupStatus([ok], { statuses: [{ state: 'error' }] }), 'fail');
  assert.equal(L.rollupStatus([], { statuses: [{ state: 'success' }] }), 'pass');
  assert.equal(L.rollupStatus([ok], { statuses: [{ state: 'pending' }] }), 'pending');
});

test('canReuseChecks keeps final results and re-polls pending ones', () => {
  const updated = '2026-10-04T11:00:00Z';
  assert.equal(L.canReuseChecks(null, updated), false);
  assert.equal(L.canReuseChecks({ state: 'pass', fetchedAt: NOW }, updated), true);
  assert.equal(L.canReuseChecks({ state: 'fail', fetchedAt: NOW }, updated), true);
  assert.equal(L.canReuseChecks({ state: 'pending', fetchedAt: NOW }, updated), false);
  assert.equal(L.canReuseChecks({ state: 'none', fetchedAt: Date.parse(updated) + 60000 }, updated), false);
  assert.equal(L.canReuseChecks({ state: 'none', fetchedAt: Date.parse(updated) + 16 * 60000 }, updated), true);
});

test('relativeTime renders compact relative times', () => {
  const ago = (ms) => new Date(NOW - ms).toISOString();
  assert.equal(L.relativeTime(ago(10 * 1000), NOW), 'just now');
  assert.equal(L.relativeTime(ago(60 * 1000), NOW), '1 min ago');
  assert.equal(L.relativeTime(ago(5 * 60 * 1000), NOW), '5 min ago');
  assert.equal(L.relativeTime(ago(3 * 3600 * 1000), NOW), '3 h ago');
  assert.equal(L.relativeTime(ago(2 * 86400 * 1000), NOW), '2 d ago');
  assert.equal(L.relativeTime(ago(65 * 86400 * 1000), NOW), '2 mo ago');
  assert.equal(L.relativeTime(ago(800 * 86400 * 1000), NOW), '2 y ago');
  assert.equal(L.relativeTime(new Date(NOW + 3600 * 1000).toISOString(), NOW), 'in the future');
  assert.equal(L.relativeTime('not a date', NOW), 'unknown');
});

test('parseLastPage reads rel="last" from Link headers', () => {
  const link = '<https://api.github.com/repositories/1/branches?per_page=1&page=2>; rel="next", '
    + '<https://api.github.com/repositories/1/branches?per_page=1&page=7>; rel="last"';
  assert.equal(L.parseLastPage(link), 7);
  assert.equal(L.parseLastPage(null), null);
  assert.equal(L.parseLastPage('<https://x?page=2>; rel="next"'), null);
});

test('rateLimitLevel and canSpend guard the 60/hour budget', () => {
  assert.equal(L.rateLimitLevel(60), 'ok');
  assert.equal(L.rateLimitLevel(10), 'low');
  assert.equal(L.rateLimitLevel(0), 'exhausted');
  assert.equal(L.rateLimitLevel(null), 'unknown');
  assert.equal(L.canSpend(null, 5, 4), true);
  assert.equal(L.canSpend(10, 5, 4), true);
  assert.equal(L.canSpend(8, 5, 4), false);
  assert.equal(L.canSpend(1, 1, 0), true);
});

test('tiersDue staggers expensive sections', () => {
  assert.deepEqual(L.tiersDue(0, false), { pulls: true, activity: true, meta: true });
  assert.deepEqual(L.tiersDue(1, false), { pulls: true, activity: false, meta: false });
  assert.deepEqual(L.tiersDue(5, false), { pulls: true, activity: true, meta: false });
  assert.deepEqual(L.tiersDue(30, false), { pulls: true, activity: true, meta: true });
  assert.deepEqual(L.tiersDue(7, true), { pulls: true, activity: true, meta: true });
});

test('estimateRefreshCost counts lists and check fetches', () => {
  const base = L.estimateRefreshCost(2, 0);
  assert.ok(base > 2 && base < 4, `base cost ${base}`);
  assert.equal(L.estimateRefreshCost(2, 3), base + 6);
});

test('pacedIntervalMs slows refreshes to fit the hourly budget', () => {
  const base = 2 * 60 * 1000;
  const resetIn1h = NOW / 1000 + 3600;
  assert.equal(L.pacedIntervalMs(null, null, NOW, 5, base, 6), base);
  // Plenty of budget: keep the 2-minute cadence.
  assert.equal(L.pacedIntervalMs(5000, resetIn1h, NOW, 5, base, 6), base);
  // 36 usable / 6 per refresh = 6 refreshes in 60 min -> every 10 min.
  assert.equal(L.pacedIntervalMs(42, resetIn1h, NOW, 6, base, 6), 10 * 60 * 1000);
  // Budget used up: wait until the reset.
  assert.equal(L.pacedIntervalMs(3, resetIn1h, NOW, 6, base, 6), 3600 * 1000);
  // Reset already passed: fall back to the base interval.
  assert.equal(L.pacedIntervalMs(0, NOW / 1000 - 10, NOW, 6, base, 6), base);
});

test('trimPull keeps display fields and labels fork heads', () => {
  const full = {
    number: 4, title: 'T', state: 'open', draft: true, html_url: 'https://github.com/o/r/pull/4',
    created_at: 'c', updated_at: 'u', user: { login: 'Copilot', type: 'Bot', id: 1 },
    base: { ref: 'master', repo: { full_name: 'o/r' } },
    head: { ref: 'feat', sha: 'abc', label: 'fork:feat', repo: { full_name: 'fork/r' } },
    body: 'large body not cached',
  };
  const trimmed = L.trimPull(full);
  assert.equal(trimmed.body, undefined);
  assert.deepEqual(trimmed.user, { login: 'Copilot', type: 'Bot' });
  assert.equal(trimmed.head.label, 'fork:feat');
  full.head.repo.full_name = 'o/r';
  assert.equal(L.trimPull(full).head.label, 'feat');
});
