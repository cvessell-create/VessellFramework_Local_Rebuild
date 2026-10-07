import { createCipheriv, createDecipheriv, createHash, randomBytes, randomUUID } from "node:crypto";
import { REPOSITORY, WORKFLOW, isOperation, type Operation, type WorkflowRun } from "./github-config.ts";

export const GH_SESSION = "vessell_github_session";
export const GH_STATE = "vessell_github_state";
export class GitHubError extends Error {
  readonly status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}
export type GitHubSession = { token: string; login: string; expires: number };
export type LoginState = { state: string; verifier: string; expires: number };

function object(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new GitHubError(502, "GitHub returned an invalid response");
  }
  return value as Record<string, unknown>;
}
function text(value: unknown): string {
  if (typeof value !== "string" || !value.length) throw new GitHubError(502, "GitHub response is missing a required field");
  return value;
}
export function configured(): boolean {
  return Boolean(process.env.VESSELL_GITHUB_CLIENT_ID && process.env.VESSELL_GITHUB_CLIENT_SECRET
    && (process.env.VESSELL_GITHUB_SESSION_SECRET?.length ?? 0) >= 32
    && process.env.VESSELL_DASHBOARD_ORIGIN);
}
function config() {
  if (!configured()) throw new GitHubError(503, "GitHub App sign-in is not configured; follow the control-panel setup guide");
  const clientId = process.env.VESSELL_GITHUB_CLIENT_ID!;
  if (!/^Iv[A-Za-z0-9.]+$/.test(clientId)) throw new GitHubError(503, "A GitHub App client ID is required, not a general OAuth app");
  const origin = new URL(process.env.VESSELL_DASHBOARD_ORIGIN!);
  if (origin.pathname !== "/" || origin.search || origin.hash || origin.username || origin.password
    || (origin.protocol !== "https:" && !(origin.protocol === "http:" && ["localhost", "127.0.0.1"].includes(origin.hostname)))) {
    throw new GitHubError(503, "Control-panel origin must use HTTPS, except for loopback development");
  }
  return { clientId, clientSecret: process.env.VESSELL_GITHUB_CLIENT_SECRET!,
    origin: origin.origin, callback: `${origin.origin}/api/github/callback` };
}
function key(): Buffer {
  const value = process.env.VESSELL_GITHUB_SESSION_SECRET ?? "";
  if (value.length < 32) throw new GitHubError(503, "GitHub session encryption key is not configured");
  return createHash("sha256").update("vessell-github-session-v1:" + value).digest();
}
export function seal(value: LoginState | GitHubSession): string {
  const iv = randomBytes(12);
  const cipher = createCipheriv("aes-256-gcm", key(), iv);
  const encrypted = Buffer.concat([cipher.update(JSON.stringify(value), "utf8"), cipher.final()]);
  return [iv, encrypted, cipher.getAuthTag()].map(part => part.toString("base64url")).join(".");
}
function unseal(value: string): unknown {
  if (value.length > 4096 || !/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(value)) {
    throw new GitHubError(401, "Invalid GitHub session; sign in again");
  }
  const [iv, encrypted, tag] = value.split(".").map(part => Buffer.from(part, "base64url"));
  try {
    const decipher = createDecipheriv("aes-256-gcm", key(), iv);
    decipher.setAuthTag(tag);
    return JSON.parse(Buffer.concat([decipher.update(encrypted), decipher.final()]).toString("utf8"));
  } catch (error) {
    if (error instanceof GitHubError) throw error;
    throw new GitHubError(401, "Invalid GitHub session; sign in again");
  }
}
export function session(value: string | undefined, now = Date.now()): GitHubSession {
  if (!value) throw new GitHubError(401, "Sign in with the repository owner's GitHub account");
  const data = object(unseal(value));
  if (typeof data.expires !== "number" || data.expires <= now || data.expires > now + 3600000
    || data.login !== "cvessell-create" || typeof data.token !== "string"
    || !/^[A-Za-z0-9_]{1,512}$/.test(data.token)) {
    throw new GitHubError(401, "GitHub session expired or invalid; sign in again");
  }
  return { token: data.token, login: data.login, expires: data.expires };
}
export function beginLogin(now = Date.now()): { url: string; state: LoginState } {
  const settings = config();
  const state = { state: randomBytes(32).toString("base64url"),
    verifier: randomBytes(32).toString("base64url"), expires: now + 600000 };
  const url = new URL("https://github.com/login/oauth/authorize");
  for (const [name, value] of Object.entries({
    client_id: settings.clientId, redirect_uri: settings.callback, state: state.state,
    code_challenge: createHash("sha256").update(state.verifier).digest("base64url"),
    code_challenge_method: "S256"
  })) url.searchParams.set(name, value);
  return { url: url.toString(), state };
}
export function loginState(cookie: string | undefined, returned: string | null, now = Date.now()): LoginState {
  if (!cookie || !returned) throw new GitHubError(400, "Missing GitHub sign-in state");
  const data = object(unseal(cookie));
  if (data.state !== returned || typeof data.verifier !== "string"
    || !/^[A-Za-z0-9_-]{43}$/.test(data.verifier) || typeof data.expires !== "number"
    || data.expires <= now || data.expires > now + 600000) {
    throw new GitHubError(400, "GitHub sign-in state is expired or does not match");
  }
  return { state: returned, verifier: data.verifier, expires: data.expires };
}
async function request(token: string, path: string, options: RequestInit = {}): Promise<Response> {
  const response = await fetch(`https://api.github.com/repos/${REPOSITORY}${path}`, {
    ...options, cache: "no-store", signal: AbortSignal.timeout(15000),
    headers: { Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
      Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
  });
  if (!response.ok) throw new GitHubError(response.status === 401 ? 401 : 502,
    `GitHub request failed (${response.status}); check App permissions, installation and rate limits`);
  return response;
}
export async function finishLogin(code: string | null, state: LoginState, now = Date.now()): Promise<GitHubSession> {
  if (!code || !/^[A-Za-z0-9_-]{1,512}$/.test(code)) throw new GitHubError(400, "Invalid GitHub authorization code");
  const settings = config();
  const exchange = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: settings.clientId, client_secret: settings.clientSecret,
      code, redirect_uri: settings.callback, code_verifier: state.verifier }),
    cache: "no-store", signal: AbortSignal.timeout(15000)
  });
  if (!exchange.ok) throw new GitHubError(502, `GitHub sign-in exchange failed (${exchange.status})`);
  const tokens = object(await exchange.json());
  if (tokens.error) throw new GitHubError(401, "GitHub rejected sign-in; check App configuration");
  const token = text(tokens.access_token);
  if (!/^[A-Za-z0-9_]{1,512}$/.test(token)) throw new GitHubError(502, "Invalid GitHub token response");
  const identity = await fetch("https://api.github.com/user", {
    headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${token}` },
    cache: "no-store", signal: AbortSignal.timeout(15000)
  });
  if (!identity.ok) throw new GitHubError(401, "GitHub could not verify the signed-in identity");
  const user = object(await identity.json());
  if (text(user.login).toLowerCase() !== "cvessell-create") throw new GitHubError(403, "Only the repository owner can run these tasks");
  const repository = object(await (await request(token, "")).json());
  const permissions = object(repository.permissions);
  if (permissions.push !== true && permissions.admin !== true) throw new GitHubError(403, "Repository write access is required");
  const lifetime = tokens.expires_in;
  if (typeof lifetime !== "number" || !Number.isFinite(lifetime) || lifetime <= 0) {
    throw new GitHubError(502, "GitHub App must issue expiring user tokens");
  }
  return { token, login: "cvessell-create", expires: now + Math.min(3600, lifetime) * 1000 };
}
export async function dispatch(token: string, operation: unknown): Promise<{ request_id: string; operation: Operation; status: "accepted" }> {
  if (!isOperation(operation)) throw new GitHubError(422, "Select one of the allowlisted framework tasks");
  const request_id = randomUUID();
  const response = await request(token, `/actions/workflows/${WORKFLOW}/dispatches`, {
    method: "POST", body: JSON.stringify({ ref: "master", inputs: { operation, request_id } })
  });
  if (response.status !== 204) throw new GitHubError(502, "GitHub did not confirm workflow dispatch acceptance");
  return { request_id, operation, status: "accepted" };
}
export async function runs(token: string): Promise<WorkflowRun[]> {
  const data = object(await (await request(token,
    `/actions/workflows/${WORKFLOW}/runs?per_page=10&branch=master&event=workflow_dispatch`)).json());
  if (!Array.isArray(data.workflow_runs)) throw new GitHubError(502, "GitHub did not return a workflow run list");
  return data.workflow_runs.map((value: unknown) => {
    const run = object(value);
    if (!Number.isSafeInteger(run.id) || typeof run.id !== "number" || run.id <= 0
      || (run.conclusion !== null && typeof run.conclusion !== "string")) {
      throw new GitHubError(502, "Invalid GitHub workflow run");
    }
    return { id: run.id, title: text(run.display_title), status: text(run.status),
      conclusion: run.conclusion, created_at: text(run.created_at), sha: text(run.head_sha),
      url: `https://github.com/${REPOSITORY}/actions/runs/${run.id}` };
  });
}
