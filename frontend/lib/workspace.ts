export type History = { version: number; state: string; actor: string; reason: string; timestamp: string };
export const FOLDERS = [
  { id: "inbox", label: "Inbox", depth: 0 },
  { id: "action", label: "01 - ACTION REQUIRED", depth: 0 },
  { id: "strategic", label: "02 - STRATEGIC INTELLIGENCE", depth: 0 },
  { id: "market", label: "02A - Market Intelligence", depth: 1 },
  { id: "policy", label: "02B - Policy Intelligence", depth: 1 },
  { id: "industry", label: "02C - Industry Intelligence", depth: 1 },
  { id: "network", label: "03 - PROFESSIONAL NETWORK INTELLIGENCE", depth: 0 },
  { id: "education", label: "04 - EDUCATION & CREDENTIALS", depth: 0 },
  { id: "courses", label: "Courses", depth: 1 },
  { id: "certifications", label: "Certifications", depth: 1 },
  { id: "watchlist", label: "05 - INDICATOR WATCHLIST", depth: 0 },
  { id: "administrative", label: "06 - ADMINISTRATIVE", depth: 0 },
  { id: "archive", label: "07 - ARCHIVE", depth: 0 }
] as const;
export type Folder = typeof FOLDERS[number]["id"];
export const COLORS = ["red", "orange", "yellow", "green", "blue", "purple"] as const;
export type CategoryColor = typeof COLORS[number];
export type Filing = {
  folder: Folder; is_read: boolean; flagged: boolean; category_color: CategoryColor | null;
  version: number; updated_at: string;
};
export type FilingPatch = Partial<Pick<Filing, "folder" | "is_read" | "flagged" | "category_color">>;
export type FilingHistory = { version: number; actor: string; timestamp: string; filing: Filing };
export type Job = {
  id: string; provider: string; state: string; version: number; updated_at: string;
  event: { source: string; event_type: string; data: unknown };
  preview: unknown; result: unknown; history: History[];
  artifacts: { name: string; bytes: number }[];
  filing: Filing; filing_history: FilingHistory[];
  field_review: {
    status: "MISSING" | "HUMAN_COMPLETED" | "LEGACY_UNASSESSED"; version: number;
    policy: string; assessment: unknown; template: unknown;
    history: { version: number; actor: string; timestamp: string; assessment: unknown }[];
  };
};
export type InquiryRevision = { expected_version: number; expected_field_version: number };
export function inquiryRevision(job: Job): InquiryRevision {
  return { expected_version: job.version, expected_field_version: job.field_review.version };
}
export function inquiryIsStale(job: Job, revision: InquiryRevision | null): boolean {
  return revision === null || revision.expected_version !== job.version
    || revision.expected_field_version !== job.field_review.version;
}
export const VIEWS = {
  all: "All workflows",
  review: "Needs review",
  specialist: "Specialist requests",
  captures: "Static captures",
  active: "Queued and active",
  released: "Released reports",
  unsuccessful: "Rejected or failed",
  unread: "Unread intelligence",
  flagged: "Flagged intelligence"
} as const;
export type View = keyof typeof VIEWS;
export function isView(value: string): value is View {
  return Object.hasOwn(VIEWS, value);
}
export const VIEW_ENTRIES = Object.entries(VIEWS).filter(
  (entry): entry is [View, (typeof VIEWS)[View]] => isView(entry[0])
);
export function isFolder(value: string): value is Folder {
  return FOLDERS.some(folder => folder.id === value);
}
export function isColor(value: string): value is CategoryColor {
  return COLORS.some(color => color === value);
}
export function folderLabel(folder: Folder): string {
  return FOLDERS.find(entry => entry.id === folder)!.label;
}
export function newerJob(current: Job | null, incoming: Job): Job {
  return current?.id === incoming.id && (
    current.version > incoming.version || current.filing.version > incoming.filing.version
    || current.field_review.version > incoming.field_review.version
  ) ? current : incoming;
}
export function matchesView(job: Job, view: View): boolean {
  switch (view) {
    case "review": return job.state === "AWAITING_APPROVAL";
    case "specialist": return job.event.event_type === "agent.analysis.requested";
    case "captures": return job.event.event_type === "static.snapshot";
    case "active": return ["PENDING", "RUNNING", "APPROVED"].includes(job.state);
    case "released": return job.state === "COMPLETED";
    case "unsuccessful": return ["REJECTED", "FAILED"].includes(job.state);
    case "unread": return !job.filing.is_read;
    case "flagged": return job.filing.flagged;
    default: return true;
  }
}
export function jobTitle(job: Job): string {
  const data = job.event.data;
  if (typeof data === "object" && data !== null) {
    if ("question" in data && typeof data.question === "string") return data.question;
    if ("declared_intent" in data && typeof data.declared_intent === "string") return data.declared_intent;
    if ("summary" in data && typeof data.summary === "string") return data.summary;
  }
  return job.event.source;
}
export function kindLabel(type: string): string {
  const labels: Record<string, string> = {
    "agent.analysis.requested": "Specialist request", "static.snapshot": "Static capture",
    "vcs.push": "Repository report", "alert.triggered": "Monitoring report"
  };
  return labels[type] ?? type;
}
export function stateLabel(state: string): string {
  const labels: Record<string, string> = {
    PENDING: "Queued", RUNNING: "Analyzing", AWAITING_APPROVAL: "Needs review",
    APPROVED: "Releasing report", COMPLETED: "Released", REJECTED: "Rejected", FAILED: "Failed"
  };
  return labels[state] ?? `Unknown state: ${state}`;
}
export function stateTone(state: string): string {
  if (state === "COMPLETED") return "positive";
  if (["REJECTED", "FAILED"].includes(state)) return "negative";
  if (state === "AWAITING_APPROVAL") return "review";
  return "neutral";
}
export function filterJobs(jobs: Job[], view: View, query: string, folder: Folder | null = null): Job[] {
  const term = query.trim().toLowerCase();
  return jobs.filter(job => (!folder || job.filing.folder === folder) && matchesView(job, view) && (
    !term || `${job.id} ${job.provider} ${job.event.source} ${job.event.event_type} ${jobTitle(job)}`.toLowerCase().includes(term)
  ));
}
