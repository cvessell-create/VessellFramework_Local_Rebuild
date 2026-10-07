"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type History = { version: number; state: string; actor: string; reason: string; timestamp: string };
type Job = {
  id: string; provider: string; state: string; version: number;
  event: { source: string; event_type: string; data: unknown };
  preview: unknown; result: unknown; history: History[];
};

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
  const [busy, setBusy] = useState(false);
  const [connection, setConnection] = useState("Not connected");
  const [hasMore, setHasMore] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await api<Job[]>("/api/runtime/jobs?limit=50");
      setJobs(data); setHasMore(data.length === 50);
      if (selectedId.current) {
        setSelected(await api<Job>(`/api/runtime/jobs/${selectedId.current}`));
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
    selectedId.current = job.id; setReason(""); setError("");
    try { setSelected(await api<Job>(`/api/runtime/jobs/${job.id}`)); }
    catch (e) { setError(String(e)); }
  }
  async function review(action: "approve" | "reject") {
    if (!selected) return;
    setBusy(true); setError("");
    try {
      const updated = await api<Job>(`/api/runtime/jobs/${selected.id}/action`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, reason: reason.trim(), expected_version: selected.version })
      });
      setSelected(updated); setReason(""); await refresh();
    } catch (e) { await refresh(); setError(e instanceof Error ? e.message : "Review failed"); }
    finally { setBusy(false); }
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

  return <main>
    <header><h1>Vessell Ambient Review</h1><p>Review incoming events, approve reports, and inspect their history.</p></header>
    {error && <p role="alert" className="error">{error}</p>}
    {!authenticated ? <form onSubmit={login}>
      <h2>Reviewer login</h2>
      <label htmlFor="token">Configured admin token</label>
      <input id="token" type="password" autoComplete="off" value={token} onChange={e => setToken(e.target.value)} required />
      <button disabled={busy}>Sign in</button>
      <p>Your session expires after eight hours.</p>
    </form> : <>
      <nav><span aria-live="polite">{connection}</span><button onClick={() => void refresh()}>Refresh</button><button onClick={() => void logout()}>Sign out</button></nav>
      <h2>Persisted workflows</h2>
      <p>Showing {jobs.length} jobs, ordered by stable ID. New events refresh the first page.</p>
      {jobs.length === 0 ? <p>No events yet. Submit an authenticated event using the documented API.</p> :
        <div className="scroll"><table><thead><tr><th>Event</th><th>Source</th><th>State</th><th>Review</th></tr></thead><tbody>
          {jobs.map(job => <tr key={job.id}><td>{job.event.event_type}<small>{job.id}</small></td><td>{job.provider}: {job.event.source}</td><td>{job.state}</td><td><button onClick={() => void select(job)}>Inspect</button></td></tr>)}
        </tbody></table></div>}
      {hasMore && <button onClick={() => void more()}>Load more</button>}
      {selected && <section aria-label="Workflow detail">
        <h2>Workflow detail</h2><p>{selected.id} · {selected.state} · version {selected.version}</p>
        <h3>Provider input</h3><pre>{JSON.stringify(selected.event, null, 2)}</pre>
        <h3>{selected.result ? "Released report" : "Analysis preview"}</h3><pre>{JSON.stringify(selected.result ?? selected.preview, null, 2)}</pre>
        <h3>Persisted history</h3><ol>{selected.history.map(h => <li key={h.version}>{h.timestamp} — {h.state} — {h.actor}: {h.reason}</li>)}</ol>
        {selected.state === "AWAITING_APPROVAL" && <div>
          <label htmlFor="reason">Review reason (required)</label>
          <textarea id="reason" maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} />
          <button disabled={busy || !reason.trim()} onClick={() => void review("approve")}>Approve report</button>
          <button disabled={busy || !reason.trim()} onClick={() => void review("reject")}>Reject</button>
        </div>}
      </section>}
    </>}
    <footer>History is preserved by default. Pruning and reset are explicit CLI operations.</footer>
  </main>;
}
