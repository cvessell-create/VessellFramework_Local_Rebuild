import assert from "node:assert/strict";
import test from "node:test";
import { equal, issueSession, permittedPath, sameOrigin, validSession } from "../lib/auth.ts";

process.env.VESSELL_AMBIENT_ADMIN_TOKEN = "test-admin-key-".repeat(4);

test("sessions expire and reject tampering", () => {
  const now = 1790000000000;
  const session = issueSession(now);
  assert.equal(validSession(session, now), true);
  assert.equal(validSession(session + "a", now), false);
  assert.equal(validSession(session, now + 8 * 60 * 60 * 1000), false);
  assert.equal(validSession(undefined), false);
  assert.equal(equal("abc", "abcd"), false);
});

test("proxy permits only review paths and same-origin mutations", () => {
  const id = "a".repeat(32);
  assert.equal(permittedPath(["jobs", id, "action"], "POST"), true);
  assert.equal(permittedPath(["ingress", "github"], "POST"), false);
  assert.equal(permittedPath(["jobs", "..", "action"], "POST"), false);
  assert.equal(permittedPath(["stream"], "GET"), true);
  assert.equal(sameOrigin(new Request("http://localhost:3000/api/session", {
    headers: { origin: "https://evil.example" }
  })), false);
  assert.equal(sameOrigin(new Request("http://localhost:3000/api/session", {
    headers: { origin: "http://localhost:3000" }
  })), true);
});
