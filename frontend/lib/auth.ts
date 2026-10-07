import { createHmac, timingSafeEqual } from "node:crypto";

export const COOKIE = "vessell_review";

export function secret(): string {
  const value = process.env.VESSELL_AMBIENT_ADMIN_TOKEN ?? "";
  if (value.length < 32) throw new Error("Admin token must contain at least 32 characters");
  return value;
}

export function equal(a: string, b: string): boolean {
  const left = Buffer.from(a);
  const right = Buffer.from(b);
  return left.length === right.length && timingSafeEqual(left, right);
}

export function issueSession(now = Date.now()): string {
  const expires = String(now + 8 * 60 * 60 * 1000);
  return `${expires}.${createHmac("sha256", secret()).update(expires).digest("hex")}`;
}

export function validSession(value: string | undefined, now = Date.now()): boolean {
  if (!value || !/^\d{13}\.[a-f0-9]{64}$/.test(value)) return false;
  const [expires, signature] = value.split(".");
  return Number(expires) > now && Number(expires) <= now + 8 * 60 * 60 * 1000
    && equal(signature, createHmac("sha256", secret()).update(expires).digest("hex"));
}

export function sameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  const expected = process.env.VESSELL_DASHBOARD_ORIGIN ?? new URL(request.url).origin;
  return origin === expected;
}

export function permittedPath(path: string[], method: string): boolean {
  if (method === "GET") {
    return (path.length === 1 && ["jobs", "stream"].includes(path[0]))
      || (path.length === 2 && path[0] === "jobs" && /^[a-f0-9]{32}$/.test(path[1]))
      || (path.length === 4 && path[0] === "jobs" && /^[a-f0-9]{32}$/.test(path[1])
        && path[2] === "artifacts" && ["screenshot.png", "checks.json", "capture.log"].includes(path[3]));
  }
  return method === "POST" && path.length === 3 && path[0] === "jobs"
    && /^[a-f0-9]{32}$/.test(path[1]) && ["action", "filing", "field-inquiry"].includes(path[2]);
}
