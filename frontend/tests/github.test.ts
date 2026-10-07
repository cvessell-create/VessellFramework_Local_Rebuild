import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";
import { beginLogin, configured, dispatch, finishLogin, GitHubError, loginState, runs, seal, session } from "../lib/github.ts";

process.env.VESSELL_GITHUB_CLIENT_ID = "Iv1.UnitTestOnly";
process.env.VESSELL_GITHUB_CLIENT_SECRET = "synthetic-app-secret-not-a-live-credential";
process.env.VESSELL_GITHUB_SESSION_SECRET = "synthetic-session-key-for-tests-only-".repeat(2);
process.env.VESSELL_DASHBOARD_ORIGIN = "https://control.example";
const TOKEN = "synthetic_github_token_for_tests";

test("GitHub App login binds state, PKCE and exact callback", () => {
  const now = Date.now();
  const login = beginLogin(now);
  const url = new URL(login.url);
  assert.equal(url.origin, "https://github.com");
  assert.equal(url.searchParams.get("redirect_uri"), "https://control.example/api/github/callback");
  assert.equal(url.searchParams.get("code_challenge"), createHash("sha256").update(login.state.verifier).digest("base64url"));
  assert.equal(url.searchParams.get("code_challenge_method"), "S256");
  assert.equal(url.searchParams.has("scope"), false);
  assert.deepEqual(loginState(seal(login.state), login.state.state, now), login.state);
  assert.throws(() => loginState(seal(login.state), "wrong", now), GitHubError);
  assert.throws(() => loginState(seal(login.state), login.state.state, now + 600001), GitHubError);
});

test("sealed credentials are authenticated, expire and reject another owner", () => {
  const now = Date.now();
  const identity = { token: TOKEN, login: "cvessell-create", expires: now + 3600000 };
  const cookie = seal(identity);
  assert.equal(cookie.includes(TOKEN), false);
  assert.deepEqual(session(cookie, now), identity);
  const parts = cookie.split(".");
  parts[1] = (parts[1][0] === "A" ? "B" : "A") + parts[1].slice(1);
  assert.throws(() => session(parts.join("."), now), GitHubError);
  assert.throws(() => session(cookie, now + 3600001), GitHubError);
  assert.throws(() => session(seal({ ...identity, login: "someone-else" }), now), GitHubError);
  assert.throws(() => session(undefined, now), GitHubError);
});

test("missing and broader OAuth configuration is explicitly rejected", () => {
  const key = process.env.VESSELL_GITHUB_SESSION_SECRET;
  delete process.env.VESSELL_GITHUB_SESSION_SECRET;
  assert.equal(configured(), false);
  assert.throws(() => beginLogin(), GitHubError);
  process.env.VESSELL_GITHUB_SESSION_SECRET = key;
  const client = process.env.VESSELL_GITHUB_CLIENT_ID;
  process.env.VESSELL_GITHUB_CLIENT_ID = "general-oauth-client";
  assert.throws(() => beginLogin(), GitHubError);
  process.env.VESSELL_GITHUB_CLIENT_ID = client;
});

test("owner authorization checks identity and repository permissions", async context => {
  const calls: { url: string; options?: RequestInit }[] = [];
  const responses = [
    { access_token: TOKEN, expires_in: 28800 },
    { login: "cvessell-create" },
    { permissions: { push: true } }
  ];
  context.mock.method(globalThis, "fetch", async (url: string | URL | Request, options?: RequestInit) => {
    calls.push({ url: String(url), options });
    return Response.json(responses.shift());
  });
  const login = beginLogin();
  const identity = await finishLogin("synthetic_code", login.state);
  assert.equal(identity.login, "cvessell-create");
  const exchange = JSON.parse(String(calls[0].options?.body));
  assert.equal(exchange.code_verifier, login.state.verifier);
  assert.equal(exchange.redirect_uri, "https://control.example/api/github/callback");
  assert.equal(calls[2].url, "https://api.github.com/repos/cvessell-create/VessellFramework_Local_Rebuild");
});

test("a different GitHub identity cannot gain owner execution authority", async context => {
  const responses = [{ access_token: TOKEN, expires_in: 28800 }, { login: "uninvited-user" }];
  context.mock.method(globalThis, "fetch", async () => Response.json(responses.shift()));
  await assert.rejects(finishLogin("synthetic_code", beginLogin().state),
    (error: unknown) => error instanceof GitHubError && error.status === 403);
});

test("dispatch allows only named tasks on master and reports acceptance", async context => {
  let posted: RequestInit | undefined;
  context.mock.method(globalThis, "fetch", async (url: string | URL | Request, options?: RequestInit) => {
    assert.equal(String(url), "https://api.github.com/repos/cvessell-create/VessellFramework_Local_Rebuild/actions/workflows/run-framework.yml/dispatches");
    posted = options;
    return new Response(null, { status: 204 });
  });
  await assert.rejects(dispatch(TOKEN, "run-arbitrary-command"), GitHubError);
  const receipt = await dispatch(TOKEN, "claim-correction-study");
  assert.equal(receipt.status, "accepted");
  const payload = JSON.parse(String(posted?.body));
  assert.equal(payload.ref, "master");
  assert.deepEqual(Object.keys(payload.inputs).sort(), ["operation", "request_id"]);
  assert.equal(payload.inputs.request_id, receipt.request_id);
});

test("provider errors and malformed runs never become successful empty results", async context => {
  context.mock.method(globalThis, "fetch", async () => new Response(null, { status: 403 }));
  await assert.rejects(dispatch(TOKEN, "validate-framework"), GitHubError);
  context.mock.restoreAll();
  context.mock.method(globalThis, "fetch", async () => Response.json({ workflow_runs: "invalid" }));
  await assert.rejects(runs(TOKEN), GitHubError);
});
