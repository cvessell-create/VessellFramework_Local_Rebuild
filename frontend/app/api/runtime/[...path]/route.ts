import { cookies } from "next/headers";
import { COOKIE, permittedPath, sameOrigin, secret, validSession } from "../../../../lib/auth";

export const dynamic = "force-dynamic";
type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, context: Context) {
  const session = (await cookies()).get(COOKIE)?.value;
  if (!validSession(session)) return Response.json({ detail: "Reviewer login required" }, { status: 401 });
  if (request.method === "POST" && !sameOrigin(request)) {
    return Response.json({ detail: "Same-origin request required" }, { status: 403 });
  }
  const { path } = await context.params;
  if (!permittedPath(path, request.method)) return Response.json({ detail: "Route not permitted" }, { status: 404 });
  const backend = process.env.VESSELL_AMBIENT_API_URL ?? "http://127.0.0.1:8000";
  const incoming = new URL(request.url);
  const url = new URL(`/api/v1/${path.join("/")}`, backend);
  for (const name of ["limit", "before", "after"]) {
    const value = incoming.searchParams.get(name);
    if (value !== null) url.searchParams.set(name, value);
  }
  const headers: Record<string, string> = { Authorization: `Bearer ${secret()}` };
  const last = request.headers.get("last-event-id");
  if (last) headers["Last-Event-ID"] = last;
  let body: string | undefined;
  if (request.method === "POST") {
    body = await request.text();
    if (body.length > 4096) return Response.json({ detail: "Review body too large" }, { status: 413 });
    headers["Content-Type"] = "application/json";
  }
  const expires = Number(session!.split(".")[0]);
  const signal = AbortSignal.any([request.signal, AbortSignal.timeout(Math.max(1, expires - Date.now()))]);
  try {
    const upstream = await fetch(url, { method: request.method, headers, body, cache: "no-store", signal });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store", "X-Accel-Buffering": "no"
      }
    });
  } catch {
    return Response.json({ detail: "Analysis service unavailable; check backend logs" }, { status: 502 });
  }
}
export const GET = proxy;
export const POST = proxy;
