import { cookies } from "next/headers";
import { COOKIE, equal, issueSession, sameOrigin, secret, validSession } from "../../../lib/auth";

export const dynamic = "force-dynamic";

export async function GET() {
  const session = (await cookies()).get(COOKIE)?.value;
  return Response.json({ authenticated: validSession(session) }, { headers: { "Cache-Control": "no-store" } });
}

export async function POST(request: Request) {
  if (!sameOrigin(request)) return Response.json({ detail: "Same-origin request required" }, { status: 403 });
  const text = await request.text();
  if (text.length > 4096) return Response.json({ detail: "Login body too large" }, { status: 413 });
  let token: unknown;
  try { token = (JSON.parse(text) as { token?: unknown }).token; }
  catch { return Response.json({ detail: "Invalid JSON" }, { status: 400 }); }
  if (typeof token !== "string" || !equal(token, secret())) {
    return Response.json({ detail: "Invalid reviewer token" }, { status: 401 });
  }
  (await cookies()).set(COOKIE, issueSession(), {
    httpOnly: true, sameSite: "strict", secure: new URL(request.url).protocol === "https:",
    path: "/", maxAge: 8 * 60 * 60
  });
  return Response.json({ authenticated: true });
}

export async function DELETE(request: Request) {
  if (!sameOrigin(request)) return Response.json({ detail: "Same-origin request required" }, { status: 403 });
  (await cookies()).delete(COOKIE);
  return Response.json({ authenticated: false });
}
