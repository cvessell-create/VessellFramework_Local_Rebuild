"use client";

import { useCallback, useEffect, useState } from "react";
import { OPERATIONS, REPOSITORY, isOperation, type Operation, type WorkflowRun } from "../../lib/github-config";
import { FolderIcon, WorkspaceShell } from "../../components/WorkspaceShell";

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/github/${path}`, { ...options, cache: "no-store" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail ?? `Request failed (${response.status})`);
  return data as T;
}
export default function GitHubControlPanel() {
  const [authenticated, setAuthenticated] = useState(false);
  const [error, setError] = useState("");
  const [operation, setOperation] = useState<Operation>("validate-framework");
  const [busy, setBusy] = useState(false);
  const [receipt, setReceipt] = useState("");
  const [history, setHistory] = useState<WorkflowRun[]>([]);
  const refresh = useCallback(async () => {
    try { setHistory(await api<WorkflowRun[]>("runs")); setError(""); }
    catch (error) { setError(error instanceof Error ? error.message : "Unable to load GitHub runs"); }
  }, []);
  useEffect(() => {
    api<{ authenticated: boolean }>("session").then(data => setAuthenticated(data.authenticated))
      .catch(error => setError(String(error)));
  }, []);
  useEffect(() => {
    if (!authenticated) return;
    void refresh();
    const timer = setInterval(() => void refresh(), 15000);
    return () => clearInterval(timer);
  }, [authenticated, refresh]);
  async function run() {
    setBusy(true); setError(""); setReceipt("");
    try {
      const result = await api<{ request_id: string }>("dispatch", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ operation })
      });
      setReceipt(`GitHub accepted request ${result.request_id}. Acceptance is not completion; locate its ID in the run list.`);
      await refresh();
    } catch (error) { setError(error instanceof Error ? error.message : "Dispatch failed"); }
    finally { setBusy(false); }
  }
  async function logout() {
    try { await api("logout", { method: "POST" }); setAuthenticated(false); setHistory([]); setReceipt(""); }
    catch (error) { setError(String(error)); }
  }
  return <WorkspaceShell section="github"
    toolbar={authenticated ? <button className="header-button" onClick={() => void logout()}>Sign out</button> : <span className="header-caption">Repository owner access</span>}
    sidebar={<>
      <div className="folder-heading">Execution control</div>
      <a className="folder-item" href="/"><FolderIcon /><span>Intelligence workspace</span></a>
      <p className="folder-caption">Named operations</p>
      {Object.entries(OPERATIONS).map(([id, label]) => <button key={id}
        className={operation === id ? "folder-item selected" : "folder-item"} disabled={busy}
        onClick={() => {
          if (isOperation(id)) setOperation(id);
          else setError("Unsupported task selected");
        }}><FolderIcon /><span>{label}</span></button>)}
      <p className="workspace-note">Execution is separate from specialist intake and human report release. Only owner-authorized, allowlisted tasks run.</p>
    </>}
    list={<>
      <div className="pane-heading"><h1>GitHub workflow runs</h1><button className="compact-button" disabled={!authenticated} onClick={() => void refresh()}>Refresh</button></div>
      <div className="list-scroll">{!authenticated ? <p className="pane-placeholder">Owner sign-in is required to view runs.</p> :
        history.length === 0 ? <p className="pane-placeholder">No matching runs yet. Accepted requests can take time to appear.</p> :
          <ul className="workflow-list">{history.map(run => <li key={run.id}>
            <a className="workflow-item" href={run.url} target="_blank" rel="noopener noreferrer">
              <strong className="workflow-title">{run.title}</strong><span>{run.status} / {run.conclusion ?? "No final conclusion"}</span>
              <small>{run.created_at}</small><small>Source commit {run.sha}</small>
            </a>
          </li>)}</ul>}</div>
    </>}>
    <div className="control-panel">
    <header><h1>Run VessellFramework on GitHub</h1><p>{REPOSITORY}</p></header>
    <p><a href="/">Local evidence review</a> · <a href={`https://github.com/${REPOSITORY}/blob/master/docs/github-control-panel.md`}>Setup guide</a></p>
    <p>Sign in as the repository owner. Only the listed tasks on master can be started; no arbitrary commands or branches.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {!authenticated ? <a className="button" href="/api/github/login">Sign in with GitHub</a> : <>
      <nav><span>Signed in as cvessell-create</span><button onClick={() => void refresh()}>Refresh runs</button><button onClick={() => void logout()}>Sign out</button></nav>
      <label htmlFor="operation">Task</label>
      <select id="operation" value={operation} onChange={event => {
        if (isOperation(event.target.value)) setOperation(event.target.value);
        else setError("Unsupported task selected");
      }}>
        {Object.entries(OPERATIONS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
      </select>
      <p>This uses your GitHub Actions quota. Inspect the selected task before starting it.</p>
      <button disabled={busy} onClick={() => void run()}>Start selected task</button>
      {receipt && <p role="status">{receipt}</p>}
      <p>Open a run from the list for its logs and downloadable artifacts. A run conclusion, not dispatch acceptance, establishes execution completion.</p>
    </>}
    </div>
  </WorkspaceShell>;
}
