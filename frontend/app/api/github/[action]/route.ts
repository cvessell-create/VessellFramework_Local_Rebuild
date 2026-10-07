import { cookies } from "next/headers";
import { sameOrigin } from "../../../../lib/auth";
import { BodyError, boundedText } from "../../../../lib/request";
import { GH_SESSION, GH_STATE, GitHubError, beginLogin, configured, dispatch, finishLogin,
  loginState, runs, seal, session } from "../../../../lib/github";

export const dynamic = "force-dynamic";
type Context = { params: Promise<{ action: string }> };
function options(maxAge: number, lax = false) {
  return { httpOnly: true, sameSite: lax ? "lax" as const : "strict" as const,
    secure: (process.env.VESSELL_DASHBOARD_ORIGIN ?? "").startsWith("https:"),
    path: "/api/github", maxAge };
}
function failure(error: unknown): Response {
  const known = error instanceof GitHubError || error instanceof BodyError;
  console.error("GitHub control-panel request failed", known ? error.message : "Unexpected provider or configuration failure");
  return Response.json({ detail: known ? error.message : "GitHub service unavailable; inspect server configuration and logs" },
    { status: known ? error.status : 502 });
}
export async function GET(request: Request, context: Context) {
  try {
    const { action } = await context.params;
    const jar = await cookies();
    if (action === "login") {
      const login = beginLogin();
      jar.set(GH_STATE, seal(login.state), options(600, true));
      return Response.redirect(login.url, 302);
    }
    if (action === "callback") {
      const url = new URL(request.url);
      const state = loginState(jar.get(GH_STATE)?.value, url.searchParams.get("state"));
      jar.set(GH_STATE, "", options(0, true));
      const identity = await finishLogin(url.searchParams.get("code"), state);
      jar.set(GH_SESSION, seal(identity), options(Math.floor((identity.expires - Date.now()) / 1000)));
      return Response.redirect(new URL("/github", process.env.VESSELL_DASHBOARD_ORIGIN!), 302);
    }
    if (action === "session") {
      if (!configured()) throw new GitHubError(503, "GitHub App is not configured; follow the setup guide");
      const value = jar.get(GH_SESSION)?.value;
      if (!value) return Response.json({ authenticated: false }, { headers: { "Cache-Control": "no-store" } });
      const identity = session(value);
      return Response.json({ authenticated: true, login: identity.login, expires: identity.expires },
        { headers: { "Cache-Control": "no-store" } });
    }
    if (action === "runs") return Response.json(await runs(session(jar.get(GH_SESSION)?.value).token),
      { headers: { "Cache-Control": "no-store" } });
    return Response.json({ detail: "Route not found" }, { status: 404 });
  } catch (error) { return failure(error); }
}
export async function POST(request: Request, context: Context) {
  try {
    if (!sameOrigin(request)) throw new GitHubError(403, "Same-origin request required");
    const { action } = await context.params;
    const jar = await cookies();
    if (action === "logout") {
      jar.set(GH_SESSION, "", options(0)); jar.set(GH_STATE, "", options(0, true));
      return Response.json({ authenticated: false });
    }
    if (action !== "dispatch") return Response.json({ detail: "Route not found" }, { status: 404 });
    const identity = session(jar.get(GH_SESSION)?.value);
    const raw = await boundedText(request, 2048);
    let data: unknown;
    try { data = JSON.parse(raw); }
    catch (error) {
      if (error instanceof SyntaxError) throw new GitHubError(422, "Task request must be valid JSON");
      throw error;
    }
    if (typeof data !== "object" || data === null || Array.isArray(data)
      || Object.keys(data).length !== 1 || !("operation" in data)) {
      throw new GitHubError(422, "Only an allowlisted operation may be supplied");
    }
    return Response.json(await dispatch(identity.token, data.operation), { status: 202 });
  } catch (error) { return failure(error); }
}
