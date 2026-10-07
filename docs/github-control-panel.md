# HTML owner control panel and GitHub App

The HTML/Next.js panel at `/github` signs the repository owner into a
repository-scoped GitHub App and dispatches only three named tasks to
`run-framework.yml` on master. Python executes in GitHub Actions, **not** in
GitHub Pages. Logs and result artifacts remain on the GitHub run.

## Configure the App

1. Create a GitHub App owned by `cvessell-create` in GitHub developer settings.
   Set its homepage to your control server and its user-authorization callback
   to `http://localhost:3000/api/github/callback` for local deployment, or the
   exact HTTPS control-server origin plus that path for a hosted deployment.
2. Enable expiring user access tokens. Set repository permissions to
   **Actions: read and write** and **Metadata: read**; do not grant contents
   write, administration or all-repository installation.
3. Install it for **only VessellFramework_Local_Rebuild**. The selected first
   release permits the owner `cvessell-create`, not arbitrary GitHub users.
4. Put its **client ID** (not numeric App ID), client secret and a new random
   session-encryption secret in private frontend server configuration:

   ```sh
   export VESSELL_GITHUB_CLIENT_ID="REPLACE_WITH_APP_CLIENT_ID"
   export VESSELL_GITHUB_CLIENT_SECRET="REPLACE_WITH_APP_CLIENT_SECRET"
   export VESSELL_GITHUB_SESSION_SECRET="$(openssl rand -hex 32)"
   export VESSELL_DASHBOARD_ORIGIN="http://localhost:3000"
   cd frontend
   npm ci
   npm run dev
   ```

   Alternatively export these variables before starting the existing Compose
   stack, which forwards them only to the frontend server. Preserve the same
   random session secret across restarts if sessions should remain valid.
   Never put actual credentials in tracked files, public HTML, browser
   localStorage or URLs. Private `.env.local` files are ignored.
5. Open http://localhost:3000/github, select **Sign in with GitHub**, authorize
   the App and choose a task. GitHub Pages links to this local panel; it is not
   itself a credential broker. A hosted panel requires its own Node server,
   HTTPS, appropriate ingress/rate controls and operational review.

The authorization flow uses a ten-minute encrypted state/verifier cookie and
PKCE. Expiring GitHub user tokens are AES-256-GCM sealed in a separate
HttpOnly cookie with a maximum one-hour local session. Cookies use Secure on
HTTPS; callback state uses SameSite=Lax and the session uses SameSite=Strict.
There is no automatic refresh token persistence. Re-sign-in is required after
expiry. A signed-in user's owner identity and repository write access are
checked; GitHub independently enforces installed App permissions on dispatch.

## Tasks, outcomes and authority

- **Validate the framework**: regression suite and source manifest.
- **Claim-correction study**: existing source-pinned comparative study.
- **Static-capture study**: offline fixture rendering, script blocking,
  overflow/visibility measurements and durable evidence checks.

The browser can supply only a listed operation. It cannot supply command text,
a branch, a workflow name, a repository or an arbitrary case/build payload.
Each dispatch has a random correlation ID in the workflow's run name.
HTTP 202 means GitHub accepted dispatch, not that a run completed or passed.
The panel polls recent matching runs and links to their logs/artifacts and
actual source SHA. Runs can take time to appear; do not duplicate a request
merely because it is not visible immediately.

This uses normal GitHub Actions quota/billing, not paid model APIs. No
autonomous scheduling is added. The remote results are stored on GitHub, not
silently copied into ambient SQLite or independently corroborated.

Sign out removes the local encrypted cookie; it does not revoke the App's
GitHub grant. Revoke that grant in GitHub settings if needed. Rotating the
session secret invalidates all local sessions. This is a single-owner
integration, not a PostgreSQL password/identity service, GitLab OAuth,
email-linked account system or public multiuser login. Passwords supplied in
chat are not used as credentials and should be replaced before deployment.

## Validation boundary

State/PKCE, encrypted-cookie tampering/expiry, owner rejection, operation/ref
allowlisting and provider errors have automated tests. A live GitHub App
handshake requires the operator's actual installed App and credentials;
synthetic tests or CLI workflow dispatch cannot establish that it has worked.
Missing configuration returns an explicit unavailable state.
