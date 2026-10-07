# Display Mode dashboard

The owner can open the linked server-backed
[GitHub control panel](../docs/github-control-panel.md) to sign in with the
repository-scoped GitHub App and start named GitHub Actions tasks. This static
page still stores no credential and performs no execution itself. dashboard

A phone-friendly, **read-only** page for watching Copilot agent work while you're away from a computer. It shows open pull requests, check status, merge order, recent merges and Actions runs for:

- `cvessell-create/VessellFramework_Local_Rebuild`
- `cvessell-create/hail-to-the-analyst`

**Live URL (after the one-time setup below):** https://cvessell-create.github.io/VessellFramework_Local_Rebuild/

The page is plain HTML, CSS and JavaScript, with no build step or framework. It calls the public GitHub REST API without a token and never asks for or stores one. Merging, approving and marking pull requests ready all happen in GitHub, either in the **GitHub Mobile** app or the browser. Each card's buttons open the right GitHub page.

## One-time setup (GitHub Pages)

1. In the repository go to **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Open **Actions → Dashboard Pages → Run workflow** once. After that, it redeploys automatically whenever a push to `master` changes `dashboard/`.
   The workflow (`.github/workflows/dashboard-pages.yml`) runs the dashboard tests and then deploys only the `dashboard/` folder.

## Add it to your iPhone home screen

1. Open https://cvessell-create.github.io/VessellFramework_Local_Rebuild/ in **Safari**.
2. Tap the **Share** button (square with an up arrow).
3. Tap **Add to Home Screen**, then **Add**.

It then opens full screen like an app. Android (Chrome): **⋮ menu → Add to Home screen**.

## What's on the page

- **Waiting on you** (top): open PRs whose title no longer starts with `[WIP]`. Drafts are labelled "mark ready for review" and ready PRs "review and merge". Oldest first.
- **Per repository:** default branch and branch count; open PR cards (number, title, Draft/Ready badge, base ← head, author with a Copilot agent badge, last updated, and a combined check status of pass, fail, pending or none built from check runs and commit statuses); the latest 5 Actions runs; the last 10 merged or closed PRs.
- **Merge order hints:** when several open PRs target the same base branch, they're numbered oldest first ("Merge 1st / 2nd / 3rd").
- **Steering buttons** on each card: Open PR · Files changed · Checks · Ask Copilot (`https://github.com/copilot`). The top link opens agent tasks at `https://github.com/copilot/agents`.

## Refresh and rate limit

- Auto-refresh every 2 minutes while the page is visible. Tap **Refresh** or pull down from the top of the page to refresh now (at most once every 20 seconds).
- Unauthenticated GitHub API calls are limited to **60 per hour** per network. The page reads `x-ratelimit-remaining` and `x-ratelimit-reset` and saves requests in these ways:
  - Open PRs are fetched on every refresh, Actions runs and closed PRs on every 5th, and repository details on every 30th.
  - A PR's check status is fetched again only while it's pending or its head commit changes.
  - Auto-refresh slows down when the budget wouldn't last until the reset. A small reserve is kept for manual refreshes.
- A banner appears when requests are low or used up. The last good data is cached in `localStorage` and shown with a **STALE** label and its time.

## Adding repositories

Edit the `REPOS` array at the top of `app.js`:

```js
const REPOS = [
  'cvessell-create/VessellFramework_Local_Rebuild',
  'cvessell-create/hail-to-the-analyst',
  'owner/another-public-repo',
];
```

Each extra repository uses more of the 60-requests-per-hour budget.

## Run locally

```bash
cd dashboard
python -m http.server 8000
# open http://localhost:8000/
```

## Tests

The pure logic is in `logic.js`: status rollup, merge order, WIP detection, relative time, escaping and rate-limit pacing. Its tests use Node's built-in test runner:

```bash
node --test dashboard/tests/*.test.js
```

## Security notes

- Every piece of API text goes through the escaping `html` template in `logic.js` before it reaches the page. Links are limited to `https://github.com/...`.
- A Content-Security-Policy allows scripts and styles only from this site and network calls only to `https://api.github.com`.
- No token, no write access, and no data sent anywhere except read-only GET requests to the GitHub API.
