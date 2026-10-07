import type { ReactNode } from "react";
import { REPOSITORY } from "../lib/github-config";

export function FolderIcon() {
  return <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    <path d="M3 7h7l2-3h8a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7Z" />
  </svg>;
}
export function WorkspaceShell({ section, sidebar, list, children, search, onSearch, toolbar }: {
  section: "review" | "github"; sidebar: ReactNode; list: ReactNode; children: ReactNode;
  search?: string; onSearch?: (value: string) => void; toolbar?: ReactNode;
}) {
  return <div className="workspace-shell">
    <header className="workspace-topbar">
      <a href="/" className="workspace-brand"><span className="brand-mark">VF</span><span>VessellFramework<small>Evidence workspace</small></span></a>
      {onSearch && <label className="workspace-search"><span className="search-symbol" aria-hidden="true" />
        <span className="visually-hidden">Search loaded workflows</span>
        <input type="search" value={search ?? ""} maxLength={200} placeholder="Search loaded workflows" onChange={event => onSearch(event.target.value)} />
      </label>}
      <div className="workspace-header-actions"><a href="/github">GitHub tasks</a>{toolbar}</div>
    </header>
    <div className="workspace-grid">
      <nav className="workspace-rail" aria-label="Primary navigation">
        <a href="/" className={section === "review" ? "rail-link active" : "rail-link"} aria-label="Evidence review" title="Evidence review"><FolderIcon /></a>
        <a href="/github" className={section === "github" ? "rail-link active" : "rail-link"} aria-label="GitHub runner" title="GitHub runner"><span aria-hidden="true">G</span></a>
        <a href={`https://github.com/${REPOSITORY}`} className="rail-link" aria-label="Repository" title="Repository" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">&lt;/&gt;</span></a>
        <a href={`https://github.com/${REPOSITORY}/blob/master/VISION_AND_SCOPE.md`} className="rail-link" aria-label="Vision and scope" title="Vision and scope" target="_blank" rel="noopener noreferrer"><span aria-hidden="true">V</span></a>
      </nav>
      <aside className="workspace-folders" aria-label="Workspace navigation">{sidebar}</aside>
      <section className="workspace-list" aria-label={section === "review" ? "Loaded workflow list" : "GitHub workflow runs"}>{list}</section>
      <main className="workspace-reader">{children}</main>
    </div>
  </div>;
}
