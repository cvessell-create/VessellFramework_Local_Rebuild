import assert from "node:assert/strict";
import test from "node:test";
import { FOLDERS, filterJobs, folderLabel, inquiryIsStale, inquiryRevision, isColor, isFolder, isView, matchesView, newerJob, type Job } from "../lib/workspace.ts";

function job(id: string, folder: Job["filing"]["folder"] = "inbox"): Job {
  return {
    id, provider: "agent", state: "AWAITING_APPROVAL", version: 2, updated_at: "2026-10-07T12:00:00Z",
    event: { source: "caller", event_type: "agent.analysis.requested", data: { question: "Market evidence?" } },
    preview: {}, result: null, history: [], artifacts: [], filing_history: [],
    filing: { folder, is_read: false, flagged: false, category_color: null, version: 0, updated_at: "2026-10-07T12:00:00Z" },
    field_review: { status: "MISSING", version: 0, policy: "knowing-field-v1", assessment: null, template: {}, history: [] }
  };
}
test("fixed intelligence hierarchy and categories reject unsupported destinations", () => {
  assert.equal(FOLDERS.length, 13);
  assert.equal(new Set(FOLDERS.map(entry => entry.id)).size, 13);
  assert.equal(folderLabel("market"), "02A - Market Intelligence");
  assert.equal(isFolder("archive"), true);
  assert.equal(isFolder("trash"), false);
  assert.equal(isColor("purple"), true);
  assert.equal(isColor("pink"), false);
  assert.equal(isView("review"), true);
  assert.equal(isView("toString"), false);
});
test("manual filing and analysis views are independent and search covers only loaded items", () => {
  const inbox = job("1"), market = job("2", "market"), strategic = job("3", "strategic");
  assert.deepEqual(filterJobs([inbox, market, strategic], "all", "", "inbox"), [inbox]);
  assert.deepEqual(filterJobs([market, strategic], "all", "", "strategic"), [strategic]);
  assert.deepEqual(filterJobs([inbox, market], "review", " MARKET "), [inbox, market]);
  assert.equal(filterJobs([inbox], "all", "not loaded").length, 0);
  market.filing.flagged = true;
  market.filing.is_read = true;
  assert.equal(matchesView(market, "flagged"), true);
  assert.equal(matchesView(market, "unread"), false);
  assert.equal(matchesView(market, "released"), false);
});
test("stale responses cannot undo newer filing or newer analysis", () => {
  const initial = job("1"), filed = { ...initial, filing: { ...initial.filing, version: 1, is_read: true } };
  assert.equal(newerJob(filed, initial), filed);
  const released = { ...filed, version: 5, state: "COMPLETED" };
  assert.equal(newerJob(released, filed), released);
  assert.equal(newerJob(initial, released), released);
  const completed: Job = { ...released, field_review: { ...released.field_review, version: 1, status: "HUMAN_COMPLETED" } };
  assert.equal(newerJob(completed, released), completed);
  assert.equal(newerJob(released, completed), completed);
  const different = job("2");
  assert.equal(newerJob(released, different), different);
  assert.equal(newerJob(null, different), different);
});
test("live updates never silently rebase a human inquiry draft", () => {
  const initial = job("1"), revision = inquiryRevision(initial);
  const filed = { ...initial, filing: { ...initial.filing, version: 1 } };
  assert.equal(inquiryIsStale(filed, revision), false);
  const revised: Job = { ...initial, field_review: { ...initial.field_review, version: 1, status: "HUMAN_COMPLETED" } };
  assert.equal(inquiryIsStale(revised, revision), true);
  assert.equal(inquiryIsStale({ ...initial, version: 3 }, revision), true);
  assert.equal(inquiryIsStale(initial, null), true);
  assert.equal(inquiryIsStale(revised, inquiryRevision(revised)), false);
  assert.deepEqual(revision, { expected_version: 2, expected_field_version: 0 });
});
