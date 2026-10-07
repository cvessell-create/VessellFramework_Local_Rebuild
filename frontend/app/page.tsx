"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FolderIcon, WorkspaceShell } from "../components/WorkspaceShell";
import { COLORS, FOLDERS, VIEW_ENTRIES, filterJobs, folderLabel, inquiryIsStale, inquiryRevision, isColor, isFolder, jobTitle, kindLabel, matchesView, newerJob, stateLabel, stateTone, VIEWS, type FilingPatch, type Folder, type InquiryRevision, type Job, type View } from "../lib/workspace";

async function api<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...options, cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? `Request failed (${response.status})`);
  return data as T;
}

export default function Dashboard() {
  const [authenticated, setAuthenticated] = useState(false);
  const [token, setToken] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<Job | null>(null);
  const selectedId = useRef<string | null>(null);
  const [error, setError] = useState("");
  const [reason, setReason] = useState("");
  const [fieldDraft, setFieldDraft] = useState("");
  const [fieldConfirmed, setFieldConfirmed] = useState(false);
  const [fieldRevision, setFieldRevision] = useState<InquiryRevision | null>(null);
  const [busy, setBusy] = useState(false);
  const [connection, setConnection] = useState("Not connected");
  const [hasMore, setHasMore] = useState(false);
  const [view, setView] = useState<View>("all");
  const [folder, setFolder] = useState<Folder | null>("inbox");
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<"analysis" | "source" | "artifacts" | "history">("analysis");

  const refresh = useCallback(async () => {
    try {
      const data = await api<Job[]>("/api/runtime/jobs?limit=50");
      setJobs(current => data.map(job => newerJob(current.find(item => item.id === job.id) ?? null, job)));
      setHasMore(data.length === 50);
      const id = selectedId.current;
      if (id) {
        const detail = await api<Job>(`/api/runtime/jobs/${id}`);
        if (selectedId.current === id) setSelected(current => newerJob(current, detail));
      }
      setError("");
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to refresh jobs"); }
  }, []);

  useEffect(() => {
    api<{ authenticated: boolean }>("/api/session")
      .then(data => setAuthenticated(data.authenticated))
      .catch(e => setError(String(e)));
  }, []);
  useEffect(() => {
    if (!authenticated) return;
    void refresh();
    const stream = new EventSource("/api/runtime/stream");
    let pending: ReturnType<typeof setTimeout> | undefined;
    stream.onopen = () => setConnection("Live durable updates");
    stream.onmessage = () => {
      if (pending === undefined) pending = setTimeout(() => {
        pending = undefined; void refresh();
      }, 150);
    };
    stream.onerror = () => setConnection("Reconnecting; use Refresh if needed");
    return () => { stream.close(); if (pending !== undefined) clearTimeout(pending); };
  }, [authenticated, refresh]);

  async function login(e: React.FormEvent) {
    e.preventDefault(); setError(""); setBusy(true);
    try {
      await api("/api/session", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) });
      setToken(""); setAuthenticated(true);
    } catch (e) { setError(e instanceof Error ? e.message : "Login failed"); }
    finally { setBusy(false); }
  }
  async function select(job: Job) {
    selectedId.current = job.id; setSelected(null); setReason(""); setFieldDraft(""); setFieldConfirmed(false); setFieldRevision(null); setError(""); setTab("analysis"); setBusy(true);
    try {
      const detail = await api<Job>(`/api/runtime/jobs/${job.id}`);
      if (selectedId.current !== job.id) return;
      setSelected(current => newerJob(current, detail));
      setFieldDraft(JSON.stringify(detail.field_review.assessment ?? detail.field_review.template, null, 2));
      setFieldRevision(inquiryRevision(detail));
      if (!detail.filing.is_read) await saveFiling(detail, { is_read: true });
    }
    catch (e) { if (selectedId.current === job.id) setError(String(e)); }
    finally { setBusy(false); }
  }
  async function saveFiling(job: Job, patch: FilingPatch) {
    const updated = await api<Job>(`/api/runtime/jobs/${job.id}/filing`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...patch, expected_version: job.filing.version })
    });
    if (selectedId.current === job.id) setSelected(current => newerJob(current, updated));
    setJobs(current => current.map(item => item.id === job.id ? newerJob(item, updated) : item));
  }
  async function file(patch: FilingPatch) {
    if (!selected || busy) return;
    setBusy(true); setError("");
    try { await saveFiling(selected, patch); }
    catch (e) { await refresh(); setError(e instanceof Error ? e.message : "Filing failed"); }
    finally { setBusy(false); }
  }
  async function review(action: "approve" | "reject") {
    if (!selected) return;
    setBusy(true); setError("");
    try {
      const updated = await api<Job>(`/api/runtime/jobs/${selected.id}/action`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action, reason: reason.trim(), expected_version: selected.version,
          expected_field_version: action === "approve" ? selected.field_review.version : undefined
        })
      });
      if (selectedId.current === updated.id) setSelected(current => newerJob(current, updated));
      setReason(""); await refresh();
    } catch (e) { await refresh(); setError(e instanceof Error ? e.message : "Review failed"); }
    finally { setBusy(false); }
  }
  async function completeFieldInquiry() {
    if (!selected || busy || !fieldConfirmed || !fieldRevision) return;
    if (inquiryIsStale(selected, fieldRevision)) {
      setFieldConfirmed(false); setError("Inquiry changed while this draft was open. Review the current record before replacing your draft.");
      return;
    }
    const id = selected.id;
    setBusy(true); setError("");
    try {
      const assessment: unknown = JSON.parse(fieldDraft);
      const updated = await api<Job>(`/api/runtime/jobs/${id}/field-inquiry`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...fieldRevision, assessment
        })
      });
      if (selectedId.current === id) {
        setSelected(current => newerJob(current, updated)); setFieldConfirmed(false);
        setFieldRevision(inquiryRevision(updated));
      }
      await refresh();
    } catch (e) {
      await refresh();
      setError(e instanceof Error ? e.message : "Unable to record field inquiry; draft retained");
    } finally { setBusy(false); }
  }
  async function reloadFieldInquiry() {
    if (!selected || busy) return;
    const id = selected.id;
    setBusy(true); setError(""); setFieldConfirmed(false);
    try {
      const updated = await api<Job>(`/api/runtime/jobs/${id}`);
      if (selectedId.current === id) {
        setSelected(current => newerJob(current, updated));
        setFieldDraft(JSON.stringify(updated.field_review.assessment ?? updated.field_review.template, null, 2));
        setFieldRevision(inquiryRevision(updated));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load inquiry; draft retained");
    } finally { setBusy(false); }
  }
  async function logout() {
    try {
      await api("/api/session", { method: "DELETE" });
      setAuthenticated(false); setJobs([]); setSelected(null); selectedId.current = null;
    } catch (e) { setError(String(e)); }
  }
  async function more() {
    if (!jobs.length) return;
    try {
      const next = await api<Job[]>(`/api/runtime/jobs?limit=50&before=${jobs[jobs.length - 1].id}`);
      setJobs([...jobs, ...next]); setHasMore(next.length === 50);
    } catch (e) { setError(String(e)); }
  }
  function chooseView(next: View) {
    setView(next); setFolder(null); setSelected(null); selectedId.current = null; setReason("");
  }
  function chooseFolder(next: Folder) {
    setFolder(next); setView("all"); setSelected(null); selectedId.current = null; setReason("");
  }
  const visible = filterJobs(jobs, view, query, folder);
  const heading = folder ? folderLabel(folder) : VIEWS[view];
  return <WorkspaceShell section="review" search={query} onSearch={setQuery}
    toolbar={authenticated ? <button className="header-button" onClick={() => void logout()}>Sign out</button> : <span className="header-caption">Reviewer access</span>}
    sidebar={<>
      <div className="folder-heading">Intelligence workspace</div>
      <p className="folder-caption">Persistent filing</p>
      <nav className="folder-nav" aria-label="Intelligence folders">
        {FOLDERS.map(entry => <button key={entry.id} disabled={busy}
          className={`${folder === entry.id ? "folder-item selected" : "folder-item"}${entry.depth ? " nested" : ""}`}
          aria-current={folder === entry.id ? "page" : undefined} onClick={() => chooseFolder(entry.id)}>
          <FolderIcon /><span>{entry.label}</span><span className="folder-count">{jobs.filter(job => job.filing.folder === entry.id).length}</span>
        </button>)}
      </nav>
      <div className="folder-divider" />
      <p className="folder-caption">Analysis and triage views</p>
      <nav className="folder-nav" aria-label="Workflow views">
        {VIEW_ENTRIES.map(([id, label]) => <button key={id} disabled={busy}
          className={!folder && view === id ? "folder-item selected" : "folder-item"}
          aria-current={!folder && view === id ? "page" : undefined} onClick={() => chooseView(id)}>
          <FolderIcon /><span>{label}</span><span className="folder-count">{jobs.filter(job => matchesView(job, id)).length}</span>
        </button>)}
      </nav>
      <div className="folder-divider" />
      <p className="folder-caption">Execution</p>
      <a className="folder-item" href="/github"><FolderIcon /><span>GitHub task runner</span></a>
      <p className="workspace-note">The full-stack SI sub-agent is the product; this is its human control plane. Counts describe loaded items. Filing does not verify claims or approve reports.</p>
    </>}
    list={<>
      <div className="pane-heading"><h1>{heading}</h1><button className="compact-button" onClick={() => void refresh()} disabled={!authenticated}>Refresh</button></div>
      <div className="list-meta"><span>{visible.length} shown / {jobs.length} loaded</span><span className="live-label" aria-live="polite">{authenticated ? connection : "Sign-in required"}</span></div>
      <div className="list-scroll">
        {!authenticated ? <p className="pane-placeholder">Sign in to view the private evidence inbox.</p> :
          visible.length === 0 ? <p className="pane-placeholder">{jobs.length ? "No loaded workflows match this view." : "No events yet. Submit a specialist task or an authenticated event."}</p> :
            <ul className="workflow-list">{visible.map(job => <li key={job.id}><button disabled={busy}
              className={`${selected?.id === job.id ? "workflow-item selected" : "workflow-item"}${job.filing.is_read ? " read" : " unread"}`}
              aria-pressed={selected?.id === job.id} onClick={() => void select(job)}>
              <span className="workflow-kind">{kindLabel(job.event.event_type)}<span className={`state-badge ${stateTone(job.state)}`}>{stateLabel(job.state)}</span></span>
              <strong className="workflow-title">{jobTitle(job)}</strong>
              <span className="filing-summary">{job.filing.is_read ? "Read" : "Unread"}{job.filing.flagged ? " / Flagged" : ""}
                {job.filing.category_color && <span className={`category-dot ${job.filing.category_color}`} aria-label={`Category: ${job.filing.category_color}`} />}
              </span>
              <span className="workflow-source">{job.provider}: {job.event.source}</span>
              <span className="workflow-time">{new Date(job.updated_at).toLocaleString()}<span>{job.id.slice(0, 8)}</span></span>
            </button></li>)}</ul>}
      </div>
      <div className="pane-footer"><span>Stable-ID order. Live updates reload the first page.</span>{hasMore && <button onClick={() => void more()}>Load more</button>}</div>
    </>}>
    {error && <p role="alert" className="error">{error}</p>}
    {!authenticated ? <div className="reader-welcome">
      <span className="welcome-icon"><FolderIcon /></span><p className="eyebrow">Your evidence workspace</p>
      <h1>Evidence before approval.</h1><p>Inspect incoming tasks, compare source with captured output, and release reports with a traceable decision.</p>
      <form onSubmit={login} className="login-card">
        <h2>Reviewer sign-in</h2><label htmlFor="token">Configured admin token</label>
        <input id="token" type="password" autoComplete="off" value={token} onChange={e => setToken(e.target.value)} required />
        <button className="primary-button" disabled={busy}>Open review workspace</button>
        <small>Eight-hour local review session. GitHub sign-in is separate.</small>
      </form>
    </div> : !selected ? <div className="reader-welcome">
      <span className="welcome-icon"><FolderIcon /></span><p className="eyebrow">Ready for review</p>
      <h1>Select a workflow.</h1><p>The inbox holds the source, analysis, captured output and durable history together.</p>
      <div className="welcome-facts"><span>Bounded analysis</span><span>Human release</span><span>Preserved history</span></div>
      <a href="/github">Sign in with GitHub to run a named task</a>
    </div> : <article className="workflow-detail" aria-label="Workflow detail">
      <div className="detail-heading"><p className="eyebrow">{kindLabel(selected.event.event_type)}</p><h1>{jobTitle(selected)}</h1>
        <span className={`state-badge ${stateTone(selected.state)}`}>{stateLabel(selected.state)}</span>
        <p className="detail-identity">{selected.id} / version {selected.version}</p>
      </div>
      <div className="filing-controls" aria-label="Human filing controls">
        <label>Move to folder<select aria-label="Move to folder" disabled={busy} value={selected.filing.folder}
          onChange={event => {
            if (isFolder(event.target.value)) void file({ folder: event.target.value });
            else setError("Unsupported intelligence folder");
          }}>{FOLDERS.map(entry => <option key={entry.id} value={entry.id}>{entry.label}</option>)}</select></label>
        <label>Category color<select aria-label="Category color" disabled={busy} value={selected.filing.category_color ?? ""}
          onChange={event => {
            const color = event.target.value;
            if (color === "") void file({ category_color: null });
            else if (isColor(color)) void file({ category_color: color });
            else setError("Unsupported category color");
          }}><option value="">None</option>{COLORS.map(color => <option key={color} value={color}>{color}</option>)}</select></label>
        <button disabled={busy} onClick={() => void file({ is_read: !selected.filing.is_read })}>Mark {selected.filing.is_read ? "unread" : "read"}</button>
        <button disabled={busy} aria-pressed={selected.filing.flagged} onClick={() => void file({ flagged: !selected.filing.flagged })}>{selected.filing.flagged ? "Remove flag" : "Flag item"}</button>
        <small>Filing revision {selected.filing.version}. Opening an item marks it read; archive preserves it without releasing it.</small>
      </div>
      <nav className="reader-tabs" aria-label="Workflow evidence">
        {(["analysis", "source", "artifacts", "history"] as const).map(value => <button key={value}
          className={tab === value ? "selected" : ""} aria-pressed={tab === value} onClick={() => setTab(value)}>
          {value === "analysis" ? "Analysis" : value === "source" ? "Source" : value === "artifacts" ? `Artifacts (${selected.artifacts.length})` : "History"}
        </button>)}
      </nav>
      <div className="reader-content">
        {tab === "analysis" && <>
          <h2>{selected.result ? "Released report" : "Analysis preview"}</h2>
          <p className="muted">Review releases analysis, not corroboration of the underlying claims.</p>
          <p>Knowing Field: {selected.field_review.status.replaceAll("_", " ")} / revision {selected.field_review.version}.
            Human completion records inquiry, not proof of presencing or execution authority.</p>
          {selected.result || selected.preview ? <pre>{JSON.stringify(selected.result ?? selected.preview, null, 2)}</pre> :
            <p className="empty-card">No analysis preview yet. The durable worker will update this workflow.</p>}
        </>}
        {tab === "source" && <><h2>Original input</h2><p className="muted">Source content is displayed as data, never executed in this browser.</p><pre>{JSON.stringify(selected.event, null, 2)}</pre></>}
        {tab === "artifacts" && <><h2>Captured output</h2>
          {selected.artifacts.length ? <>
            <p className="muted">Offline static render. Measurements are not a model verdict or proof of intent.</p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className="capture-image" src={`/api/runtime/jobs/${selected.id}/artifacts/screenshot.png`} alt="Captured static HTML viewport" />
            <ul className="artifact-list">{selected.artifacts.map(item => <li key={item.name}>
              <a href={`/api/runtime/jobs/${selected.id}/artifacts/${item.name}`} target="_blank" rel="noopener noreferrer">{item.name}</a><span>{item.bytes.toLocaleString()} bytes</span>
            </li>)}</ul>
          </> : <p className="empty-card">This workflow has no captured artifacts.</p>}
        </>}
        {tab === "history" && <><h2>Durable decision history</h2><ol className="history-list">{selected.history.map(item => <li key={item.version}>
          <strong>{stateLabel(item.state)}</strong><small>{item.timestamp} / {item.actor}</small><p>{item.reason}</p>
        </li>)}</ol><h2>Separate human filing history</h2><ol className="history-list">{selected.filing_history.map(item => <li key={item.version}>
          <strong>{folderLabel(item.filing.folder)} / filing revision {item.version}</strong>
          <small>{item.timestamp} / {item.actor}</small>
          <p>{item.filing.is_read ? "Read" : "Unread"} / {item.filing.flagged ? "Flagged" : "Not flagged"} / category: {item.filing.category_color ?? "none"}</p>
        </li>)}</ol><h2>Knowing Field completion history</h2><ol className="history-list">{selected.field_review.history.map(item => <li key={item.version}>
          <strong>Inquiry revision {item.version}</strong><small>{item.timestamp} / {item.actor}</small>
          <pre>{JSON.stringify(item.assessment, null, 2)}</pre>
        </li>)}</ol></>}
        {selected.state === "AWAITING_APPROVAL" && <div className="review-card">
          <h2>Knowing Field: human-led fifth-pillar inquiry</h2>
          <p>Required before release. Record the observer, affected parties, four perspectives,
            dissent, blind spots, attention, intention, agency, alternatives and a test plan.
            Explicitly describe unavailable or declined accounts; do not invent experiences.</p>
          <label htmlFor="field-draft">Source-bound assessment (JSON)</label>
          <textarea id="field-draft" aria-label="Knowing Field assessment" maxLength={65536}
            value={fieldDraft} disabled={busy}
            onChange={event => { setFieldDraft(event.target.value); setFieldConfirmed(false); }} />
          {inquiryIsStale(selected, fieldRevision) && <p role="alert">This draft is based on an older inquiry or workflow revision. Copy any edits you need, then reload and review the current record.</p>}
          <button disabled={busy} onClick={() => void reloadFieldInquiry()}>Reload current inquiry (replaces draft)</button>
          <label><input type="checkbox" checked={fieldConfirmed} disabled={busy}
            onChange={event => setFieldConfirmed(event.target.checked)} />
            I have reviewed the source and preview and documented the inquiry and its limitations.</label>
          <button disabled={busy || !fieldConfirmed || inquiryIsStale(selected, fieldRevision)} onClick={() => void completeFieldInquiry()}>Record human field completion</button>
          <p>Current status: {selected.field_review.status.replaceAll("_", " ")}. Completion and release are separate decisions.</p>
          <h2>Record your decision</h2><label htmlFor="reason">Review reason (required)</label>
          <textarea id="reason" maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} />
          <button className="primary-button" disabled={busy || !reason.trim() || selected.field_review.status !== "HUMAN_COMPLETED" || inquiryIsStale(selected, fieldRevision)} onClick={() => void review("approve")}>Approve report</button>
          <button className="danger-button" disabled={busy || !reason.trim()} onClick={() => void review("reject")}>Reject</button>
        </div>}
      </div>
    </article>}
  </WorkspaceShell>;
}
