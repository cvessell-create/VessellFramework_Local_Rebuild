# Phase 0 restart and Phase 1 roadmap

Restarted October 14, 2026. Status: RESEARCH OBSERVATIONS / PENDING_HUMAN_REVIEW.
Phase 0 ("phase nothing") is research plus read-only contact with public
networks. No wallet, key, signature, payment, OpenTimestamps submission,
faucet request or transaction was made. Passing the Phase 0 gate does not
authorize Phase 1; the owner decides. Parent plan:
[blockchain agent economy roadmap](blockchain-agent-economy-roadmap.md).

## The loop

`python -m vessell.phase0_loop [--forever --pause 1800 --no-llm]` writes
`outputs/phase0/latest.json` and appends `outputs/phase0/report.jsonl`. The
`/loops` page of `vessell.si_chat` shows it. Each run:

1. **Re-scrapes** 11 declared primary sources (R1–R11) with GET, recording
   HTTP status, sha256 and change since the last run as a SEARCH RECORD.
2. **Touches** chains read-only (T1–T4): Base Sepolia `eth_chainId` and
   `eth_blockNumber` (other RPC methods raise `PermissionError`), Bitcoin tip
   height from two explorers, and an OpenTimestamps calendar GET.
3. **Re-reports** every loop from raw files (L1–L8) and detects stalls.
4. Builds an **unsigned, unanchored** local Merkle preview of loop outputs.
5. Optionally drafts Phase 1 steps with the local model. A step survives only
   if it cites a real research id (R/T) *and* a loop finding (L) and is not an
   echo of the evidence. Surviving steps are still generated drafts.

## Search record (Oct 14, 2026)

query: declared URLs / tool: urllib GET + curl / scope: 11 primary pages,
4 read-only probes / result: 11/11 opened, 4/4 probes ok / limit hit: no /
primary source opened: y / status: SOURCE OPENED (page contents are provider
claims, not independently verified) / not checked: terms of service, fees,
security of any provider, mainnet behaviour.

Observed: Base Sepolia chain id 84532; Bitcoin tip 971419 on both explorers
(same chain, two indexers: consistency, not independent corroboration);
the `coinbase/x402` README states the project moved to
`x402-foundation/x402`; the OpenTimestamps client README states `ots stamp`
submits to public calendars (a write, so Phase 2+ only).

## What the re-report found

- Five-level loop: 41 runs, L1–L3 up 41/41, L4/L5 up 40/41. L1/L2 checks test
  presence (a reply, a citation), not correctness or relevance.
- Sparring: 661 lessons, ~613 distinct by a word-overlap filter, but they
  repeat a few themes (be specific, concise, answer the question).
- Ideas: 104, 82 with resolvable evidence ids, **0** on the St. Louis campaign.
- Autopilot: **stall**: 113 identical timeouts on mission index 4 (0 kills).
- No loop produced signed receipts or anchors before this loop.

## Phase 1 roadmap (owner-reviewed draft, local only)

Phase 1 = local signed receipts and an offline verifier. Still no chain.

**Status 2026-10-14:** owner approved Phase 1 and chose HMAC-SHA256 (only a
holder of the same key can verify). Steps 1–5 are implemented in
`vessell/receipts.py` (`sign`, `verify --check-files`, `prove`) with the key in
git-ignored `private/`; step 6 is open. Gate rule:
[Vessell formula](vessell-formula.md).

1. **Receipt schema**: wrap existing sha256 records from
   `vessell/game_bridge.py` and `vessell/si_agent.py` plus loop outputs in a
   versioned receipt (inputs digest, outputs digest, loop id, run time).
2. **Local signing**: test key generated locally and never committed; owner
   chooses the algorithm (e.g. Ed25519) and custody before any real key.
3. **Merkle batch**: promote the Phase 0 preview root to per-run batches with
   membership proofs.
4. **Offline verifier**: CLI that checks signature, digests and membership
   with no network access.
5. **Tests**: tamper, duplicate, missing record, key rotation, correction; old
   digest contracts unchanged.
6. **Loop honesty fixes the receipts will expose**: L1/L2 correctness checks,
   autopilot timeout scoring (the mission 4 stall), St. Louis brief for ideas.

Exit to Phase 2 (OpenTimestamps) requires the owner's privacy and exposure
decision. Phase 3 (x402 on Base Sepolia) requires owner-chosen custody,
scheme and terms. Generated steps on the loops page do not change this list.
