# Blockchain on-ramp: researched plan and offline simulation

Research date: 2026-10-14. Owner-review draft, not onboarding authorization.
Primary documentation was opened; provider claims are attributed below.
This plan separates a real on-ramp from a passing simulation.

## Decision and current position

Recommended sequence:

1. Keep the local Phase 1 receipt and strict Vessell checks.
2. Rehearse failure states offline (implemented here).
3. After an explicit privacy decision, submit ONE non-sensitive aggregate
   commitment to OpenTimestamps and verify its completed Bitcoin proof.
4. Separately, choose test-only custody and receiving/payer addresses, then
   perform a bounded Base Sepolia transaction/payment experiment.
5. Only after testnet acceptance, decide whether a fiat-funded mainnet route
   is useful. It is not necessary for the existence-proof experiment.

**Not yet done:** wallet creation, faucet claim, calendar submission, EVM
transaction, x402 settlement, fiat purchase or live paid service.
Local HMAC receipts and read-only RPC success are not those actions.

There are three different meanings of "get on blockchain":

| Goal | Actual route | What a successful outcome establishes |
|---|---|---|
| Prove a commitment existed | OpenTimestamps calendars -> completed Bitcoin attestation [O1] | A verified prior-existence bound, not content truth |
| Exercise a wallet or payment service | Base Sepolia, test ETH/test USDC, verified transaction or x402 settlement [B1, B2, X1, X2] | Testnet integration behavior, not real earnings |
| Fund a production address with fiat | Owner-selected hosted exchange withdrawal or hosted on-ramp, explicitly selecting Base mainnet [B2, F1-F3] | Actual funded address after reconciled settlement; still no proven customer demand |

These routes are alternatives/complements, not mandatory prerequisites for
each other. x402 does not require an OpenTimestamps proof. The combined
simulation policy is an illustrative stricter workflow, not an x402 protocol
requirement.

## A. Implemented bounded simulation loop

Run from the project environment:

```sh
.venv/bin/python -m vessell.blockchain_simulation --rounds 2
```

The loop runs 12 fixtures per round, with 1-20 rounds allowed:
happy path, wrong network, absent owner decision, absent privacy review,
tampered receipt, pending anchor, failed anchor, invalid payment, replay,
pending settlement, failed settlement and missing human release.
Happy-path delivery is followed by a replay attempt, which must be blocked.

Each fixture has independent inputs, an expected state and an observed state.
The Vessell formula's UP result means every fixture matched its expected
behavior, INCLUDING cases that correctly blocked or failed. It does not mean
all simulated transactions succeeded or that real onboarding passed.

Results append to `outputs/blockchain_simulation/report.jsonl`; a unique
snapshot and local HMAC receipt are retained. `latest.json` and the local
`/loops` panel identify OFFLINE_SIMULATION, real onboarding NOT_PERFORMED and
the fixture gate explicitly. The module has no wallet or network adapter.

Limits: this is a reference state machine, not EVM execution, x402 wire-format
validation, real signature validation, real chain reorganization, durable
cross-process replay handling, facilitator integration or a production
security assessment. Inputs such as `payment_verified` and `anchor` are
fixture observations, not cryptographic checks. The HMAC receipt authenticates
the recorded fixture output relative to the local key; it does not turn these
observations into network evidence. Repeating deterministic fixtures does not
add independent evidence.

### Measured local result

The two-round CLI run completed 24/24 fixture cases, Vessell formula UP,
with a persisted LOCAL_RECEIPT_VERIFIED result. There were zero network calls,
wallet creations or transaction submissions in this simulation. The running
local dashboard API and browser showed the distinct simulation panel.

Focused simulation/dashboard/formula/receipt tests: 43 passed.
Full regression run: 1,080 passed, 1 skipped, 2 failed. The two failures were
`test_kev_rows_carry_provenance_tags` and
`test_pipeline_intakes_evidence_and_links_result` in
`tests/test_doctrine_reconciliation.py`, the same empty-KEV-evidence failures
recorded in earlier runs. They were not repaired in this task; no new baseline
comparison was run. New module Pylance diagnostics and syntax checks were clean;
all five existing dashboard snapshot call sites remained signature-compatible.
The refreshed distribution manifest verified 458/458 listed source files.

## B. Phase 2: ONE actual Bitcoin existence proof

**Owner decision first:** what aggregate commitment may leave the machine,
whether calendar metadata exposure is acceptable, retention and who may
receive the proof. Private inquiries, conversation content, addresses and
game-player records stay off public infrastructure.

Steps after that separate approval:

1. Choose one immutable, reviewed, non-sensitive local snapshot/aggregate
   root. Preserve leaf definitions, membership proofs and private verification
   material. Do not expose the HMAC key.
2. Verify the intended OpenTimestamps client version and license before
   installing; the current README demonstrates `ots stamp`, `ots upgrade`,
   `ots verify` and `ots info` [O1]. No package was installed in this task.
3. Stamp once. This contacts public calendars: it is a submission, not a
   read-only scrape. Save the `.ots` proof and exact target bytes.
4. Record PENDING_ANCHOR until a complete attestation is available. The
   README says confirmation can take hours; that is not a deadline guarantee.
5. Upgrade the pending proof if needed. Verify the completed proof against
   a separately trusted Bitcoin verification setup; document node/header
   source and trust assumptions. Calendar reachability alone is not success.
6. Confirm that altered target bytes fail verification and that the included
   membership proof corresponds to the intended receipt. Keep failed attempts.

Acceptance: complete proof + matching target digest + reviewed Bitcoin
verification result + reproducible membership verification.
The reviewed client workflow does not require an owner EVM wallet. Provider
calendar uptime and continued service availability are not guaranteed.

Privacy: the client README describes nonce-protected file commitments, but
also explicitly warns about time/linkability and calendar transport metadata
[O1]. "Only hashes" is not a complete privacy assessment.

## C. Phase 3: Base Sepolia developer on-ramp

Owner choices still required: test-only wallet custody, payer and receiving
address, provider/facilitator, test asset, max transactions/retries and privacy
exposure. Do not reuse a real funded wallet or put seed phrases in chat.

Network from official Base documentation [B1]:

```text
network: Base Sepolia
chain ID: 84532
CAIP-2 payment network: eip155:84532
test USDC contract (Circle C2): 0x036CbD53842c5426634e7929541eC2318f3dCF7e
read RPC: https://sepolia.base.org
submission endpoint: https://sepolia-sequencer.base.org
explorer: https://sepolia.basescan.org
```

The official page now distinguishes RPC reads from transaction submission.
It redirects the older connection/faucet documentation paths to Get Started.
Do not copy the mainnet example from the transaction guide unchanged [B3].

### Test-only runbook after owner decisions

1. Set up the approved isolated test-only wallet; keep the signing path
   outside the browser/game, Git, model prompts and loop logs.
2. Check chain ID 84532 before preparing any transaction. Obtain a public
   address from the owner-controlled wallet; do not infer an address.
3. Use an official linked faucet for test ETH. Base's funding guide also
   directs test USDC users to Circle's faucet and says to select Base Sepolia
   [B2, C1]. Claims, quotas and account requirements must be checked at use
   time; the current funding guide's Base faucet link points back to the
   redirected guide, so it is not a verified working ETH-faucet endpoint.
   No faucet claim was performed.
4. Confirm balances, gas estimate, destination, network and a declared test
   transaction limit. Record ETH gas units and test-asset base units
   separately. Do not assume test assets have mainnet value.
5. Owner approves ONE exact test transfer payload. Broadcast once through
   the approved signer/endpoint; retain transaction hash.
6. Check receipt status, actual sender/receiver, chain ID and balance effects
   through RPC and explorer. Define a confirmation/reorganization policy
   before describing the result as final.
7. Tamper, wrong-chain, timeout and replay tests precede expansion. A timeout
   after broadcast is indeterminate, not permission to resend blindly.

This plan does not deploy a smart contract by default; contract deployment is
not necessary just to demonstrate an EVM transaction or x402 payment.

### x402 test-payment branch

The x402 Foundation describes a public `x402.org` facilitator for development
and testnet use, not a default mainnet production route [X2]. Evaluate it for
the first isolated test. The CDP managed alternative currently documents
Base Sepolia support, an authenticated API key and a receiving `payTo` address
[X1, X3]. Provider support must be rechecked before running; no supported-
networks API was queried here.

Concrete sequence:

1. Select facilitator, `exact` scheme, the test asset contract documented by
   Circle [C2], receiving address and a synthetic test job. Recheck the
   contract/network, onchain code and decimals before constructing amounts;
   this task opened the official table but did not inspect onchain token code.
2. Pin/validate SDK versions and inspect licenses before adding packages.
   Keep the pure evidence worker and game outside the payment adapter.
3. A request obtains 402 requirements; a test payer supplies the protocol's
   payment signature; verify against those exact requirements [X2].
4. Prepare work but hold delivery while settlement is pending or failed.
   Log a unique job/payment association, expiry and network. Maintain
   durable idempotency and reconciliation across restarts.
5. Reconcile a broadcast-pending transaction before retrying. The Foundation
   describes `settlement_pending` and a store-backed reconciliation path;
   an in-memory store alone does not establish multi-instance safety [X2].
6. Require human source/preview-bound review separately for any report
   release. Payment success cannot approve a report. Use synthetic content
   for the first paid-route fixture.

Acceptance: valid test payment + confirmed settlement evidence + no duplicate
delivery/charge under retries and restart + separately approved release.
This is not implemented by the fixture simulation.

## D. Actual fiat on-ramp (later, not executed)

Two practical alternatives supported by the reviewed provider documentation:

- For the owner's own funding: withdraw ETH or USDC from an existing eligible
  Coinbase account and explicitly choose **Base** as the destination network
  [B2]. This avoids building an on-ramp service merely to fund a test project.
- For a product-facing funding flow: Coinbase-hosted Onramp. Its quickstart
  calls for a CDP account with email verification/2FA, a server-side Secret API
  Key, an owner-chosen destination and a generated session token; users finish
  purchases on hosted pages [F1, F2]. This is a prospective integration, not
  an account created here.

Before either: owner declares country/state, eligibility, custody, verified
destination, asset/network, maximum fiat spend/loss/fees, recovery plan and
whether this serves only the owner or external users. All are NOT_SUPPLIED
for this task. Do not collect financial identity documents in this repository.

Use Config/Options APIs to establish location-specific availability and
supported asset/network, then obtain an actual quote [F3]. The documentation's
example currency limits are examples, not the owner's limits. A quote must
show fiat amount, fees, delivered asset, network and expiry. Approval binds to
the exact quote/destination; expired quotes need another review.

No fiat budget is inferred. Default spending authority is zero. Reconcile
completed purchase/withdrawal against the destination chain balance before
calling it funded. No profit or customer demand is predicted.

## E. Costs, boundaries and stop conditions

| Route | Cost/exposure to establish before execution |
|---|---|
| Local simulation | Local computation and storage; no funds moved |
| OpenTimestamps | Calendar terms/availability, commitment metadata and trusted verification resources |
| Base Sepolia | Faucet eligibility/quota, test balances, signing custody and test gas |
| Managed x402 | Provider terms/support/account approval and actual scheme/settlement costs |
| Fiat/mainnet | Location eligibility, quote spread/fees, asset/network gas, fiat budget and recovery |

CDP's facilitator page advertises 1,000 free onchain transactions/month then
$0.001 each, with verification free [X3]. This is a provider-published pricing
snapshot, not a quote, signed agreement, total gas estimate or guaranteed
future price. No account eligibility or invoice was checked.

Stop on wrong chain, exposed key, unauthorized destination, insufficient gas,
missing privacy/release approval, unknown settlement, replay or exceeded
owner limits. Never promote pending or failed results by retrying until green.
Keep operation integrity, existence proofs, evidence truth and permission
separate. Local formula UP certifies only its declared checks.

## Opened primary sources and access

| ID | Primary source opened | Reviewed scope |
|---|---|---|
| B1 | [Base Connect to Base](https://docs.base.org/get-started/connect-to-base.md) | Network/read/submission endpoints and explorers |
| B2 | [Base Get Funds](https://docs.base.org/get-started/get-funds.md) | Mainnet funding alternatives and testnet faucet pointers |
| B3 | [Base Make a Transaction](https://docs.base.org/get-started/make-a-transaction.md) | Mainnet example and key-handling warning; code not executed |
| O1 | [OpenTimestamps client README](https://raw.githubusercontent.com/opentimestamps/opentimestamps-client/master/README.md) | Stamp/pending/upgrade/verify and Privacy Security sections |
| C1 | [Circle Faucet](https://faucet.circle.com/) | Testnet explanation; interactive quotas/claim flow not accessed |
| C2 | [Circle USDC contract addresses](https://developers.circle.com/stablecoins/usdc-contract-addresses.md) | Base Sepolia address and testnet no-financial-value warning |
| X1 | [CDP x402 seller quickstart](https://docs.cdp.coinbase.com/x402/seller/quickstart.md) | Prerequisites, payTo, SDK choices and development-network example |
| X2 | [x402 Foundation facilitator](https://docs.x402.org/core-concepts/facilitator) | Verify/settle flow, testnet-vs-production and pending reconciliation |
| X3 | [CDP Facilitator](https://docs.cdp.coinbase.com/x402/seller/facilitator.md) | Pricing, auth and provider-reported supported networks |
| F1 | [Coinbase Onramp overview](https://docs.cdp.coinbase.com/onramp/introduction/welcome.md) | Hosted/headless paths, trial/full-access boundary |
| F2 | [Coinbase Onramp quickstart](https://docs.cdp.coinbase.com/onramp/introduction/quickstart.md) | Account, secret key, session and hosted flow |
| F3 | [Countries and currencies](https://docs.cdp.coinbase.com/onramp/coinbase-hosted-onramp/countries-&-currencies.md) | Config/Options APIs, country/state dependency |

Documentation fetched live on the research date; no credentials sent.
Some fetches returned bounded excerpts; only the sections above support
claims here. Base/Coinbase/CDP sources are related provider sources, not
independent corroboration. Documentation describes intended APIs, not tested
service availability. The Base index was opened as a discovery aid.

## Search records and limits

`query / tool / scope / result count / limit hit / primary opened / status / not checked`

- Base Sepolia, OTS, x402 on-ramp overview / web_search / public web /
  8 distinct returned citation URLs / tool total/cap unavailable / yes,
  applicable Base sources opened / SOURCE-ESTABLISHED for documentation /
  accounts, quotas, real transactions, service behavior not checked.
- OTS security/privacy/pending verification / web_search / public web /
  8 distinct returned citation URLs / tool total/cap unavailable / yes,
  official client README / SOURCE-ESTABLISHED for client documentation /
  independent completed proof and calendar privacy not tested.
- x402 v2 Base Sepolia verify/settle/replay / web_search / public web /
  5 distinct returned citation URLs / tool total/cap unavailable / yes,
  Foundation and CDP pages / SOURCE-ESTABLISHED for documented flow /
  wire conformance, supported-networks endpoint and live settlement not tested.
- Onramp/country requirements / web_fetch / F1-F3 official pages /
  3 opened / quickstart excerpt bounded at 6,500 characters / yes /
  SOURCE-ESTABLISHED for documentation / user-specific eligibility, quote,
  country/state and account not checked.
- Circle token documentation and Base fee-detail attempted URLs / web_fetch /
  2 specific URLs / 0 successful opens (404) / no / UNAVAILABLE IN THIS SCOPE /
  these old paths did not establish a token address, fee schedule or ETH faucet.
- Official Circle/Base address/fee search / web_search / public web /
  0 returned results / tool total/cap unavailable / no /
  NOT FOUND IN THIS SEARCH SCOPE / absence does not show docs do not exist.
- Circle canonical token-address discovery / web_fetch + scoped rg /
  official documentation index -> C2 / 1 applicable address table opened /
  index bounded at 20,000 characters; address section read explicitly / yes /
  SOURCE-ESTABLISHED for publisher-listed test address /
  onchain code, decimals, live transfers and current faucet quotas not checked.

Search summaries were used as leads only. Corrected canonical paths are
recorded above; no summary supplied a wallet, token contract or deployment.
