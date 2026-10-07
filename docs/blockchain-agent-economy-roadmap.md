# Blockchain agent economy, mining and proof-of-existence roadmap

Research checked October 7, 2026. Status: RESEARCH / PROPOSED NEXT STAGE.
No wallet creation, registration, purchase, staking, mining, payment, public
deployment or chain transaction was performed. No earnings are claimed.
Provider documentation describes provider claims, not independently audited
profitability or acceptance of this repository.

## Recommendation

**Sell useful agent work; preserve its receipt; independently timestamp the
receipt. Hashing by itself is neither payment nor mining.**

1. **First revenue experiment:** x402-paid asynchronous evidence-analysis
   service, starting on Base Sepolia with test assets. Base mainnet is a
   prospective first production choice because the official Python/FastAPI
   route fits the existing stack; Solana and other supported networks remain
   alternatives, not additional implementations promised here.
2. **Parallel existence evidence:** OpenTimestamps for permitted digest/Merkle
   commitments, with upgraded and independently verified Bitcoin-backed proofs.
   Optional EAS attestations can later bind signed operator assertions.
3. **Distribution candidates:** Olas Mech and Virtuals ACP service adapters,
   only after their task lifetime, rejection/refund and human-review SLA fit.
4. **Conditional mining:** Bittensor only if a specific live subnet's actual
   miner/validator scoring contract accepts useful work this service can supply.
   No eligible subnet, registration cost or reward rate was verified.
5. **Separate hardware business:** io.net/Golem/Akash/Render/storage providers
   sell hardware/storage/protocol work. They do not reward arbitrary framework
   report hashes. Evaluate separately, not as a prerequisite to paid agent use.

This is a broad category survey, not an exhaustive inventory of every blockchain.
Do not issue a token or buy/stake hardware/network assets merely to create an
appearance of adoption. Registration, token exposure and transaction budgets
require a separate owner decision.

## Four things that must not be called the same "credit"

| Kind | What creates it | Redemption/value boundary |
|---|---|---|
| Local usage credit | Defined internal accounting event. | Not money or transferable property unless a separate funded/legal contract makes it redeemable. |
| Buyer payment | Customer pays for a specified service. | Net realized settlement depends on delivery, costs, refunds, asset/network and actual demand. |
| Protocol emission/reward | Eligible scored work accepted by protocol rules. | Not guaranteed per invocation; token liquidity/value, stake, uptime and scoring may change. |
| Evidence receipt | Digest/signature/anchor binds a record. | Evidence product, not a currency or entitlement to any protocol reward. |

Usage may create a local record every time without generating a chain transaction
every time. Batched commitments can preserve per-use membership proofs while
reducing anchoring cost. Payment batching and evidence batching are separate
contracts and must be reconciled independently.

## Opportunity and onboarding comparison

| Route | What is paid/proved | Onboarding and prerequisites from official sources | Fit/limitations |
|---|---|---|---|
| [x402/CDP](https://docs.cdp.coinbase.com/x402/welcome) | Buyer-paid HTTP service; facilitator verifies/settles payments. | [Python seller quickstart](https://docs.cdp.coinbase.com/x402/seller/quickstart): operator-controlled receiving destination, CDP API authentication for its hosted facilitator, supported network/asset, priced route and buyer test. [Discovery](https://docs.cdp.coinbase.com/x402/seller/get-discovered): publish schema/metadata; successful paid settlement enables indexing under documented conditions. | Best initial API fit. No buyer means no revenue. Payment does not authorize human release. Hosted facilitator screening/terms apply. |
| [Olas Mech](https://build.olas.network/api/ai-guide/monetize) | Paid tool jobs; incentive programs have separate eligibility. | Guide: Python >=3.10,<3.15, Poetry >=1.4,<2, Docker; create workspace/onchain mech, scaffold tool, implement run function, prepare/update metadata, launch. [Tool docs](https://stack.olas.network/mech-tools-dev/). Confirm current chain, gas/registration, funding and delivery rules first. | Python tool adapter candidate. Marketplace listings show a service category, not demonstrated demand for this project. Human-review latency must fit request lifecycle. |
| [Virtuals ACP](https://whitepaper.virtuals.io/builders-hub/acp-tech-playbook.md) | Contracted agent/API service jobs. | Official playbook permits API-only sellers. Register offering, smart wallet/developer-wallet allowlist, sandbox buyer/seller, define SLA and test lifecycle; [Python SDK](https://github.com/Virtual-Protocol/acp-python), [platform](https://app.virtuals.io/acp). | Service adapter candidate. Guide's sandbox uses funded USDC and advertises sponsored gas; do not assume free testnet funds or universal gas sponsorship. Confirm chain, graduation, escrow and timeouts. |
| [Bittensor](https://www.bittensor.com/llms.mdx/docs/guides/mining/content.md) | Subnet-defined commodity scored by validators; emissions under current chain/subnet rules. | Choose actual subnet/code/scoring benchmark; configure hotkey/coldkey, register UID, expose compatible service and sustain uptime. [Registration/burn](https://www.bittensor.com/llms.mdx/docs/guides/mining/burn/content.md), [emissions](https://www.bittensor.com/llms.mdx/docs/concepts/emissions/content.md). | Conditional feasibility only. Floating registration price, burn/collateral, pruning/eviction, stake/liquidity and validator competition; no fixed tokens per report hash. Burned portion is not refundable. |
| [Fetch.ai uAgents](https://github.com/fetchai/uAgents) | Agent discovery/cryptographic messaging; a separate payment contract is needed. | Python SDK/agent identity, Almanac/Agentverse discovery and typed messages; [current docs](https://uagents.fetch.ai/docs). | Interoperability watchlist. Registration/messages do not themselves establish paid jobs or redeemable credits; exact current payment fit unverified. |
| [Gensyn](https://docs.gensyn.ai/) | Reproducible execution receipts and decentralized ML research. | [REE receipts](https://docs.gensyn.ai/tech/ree/receipts) bind model/config/prompt/tools/output. Current homepage reports no official swarms; legacy swarms are paused/unmaintained archive. | Receipt design research, not a verified active earning route. Hash validation differs from re-execution; neither validates input truth or actual tool performance by itself. |
| [Ritual](https://docs.ritualfoundation.org/) | Chain/external-compute/agent infrastructure described by provider. | Follow [official index](https://docs.ritualfoundation.org/llms.txt) for current worker/protocol pathways. | Watchlist only: production worker onboarding and redeemable-reward route not verified here. |
| [Golem](https://docs.golem.network/docs/golem/overview) | Provider CPU/resources rented by requestors, paid in GLM. | Supported Linux provider installation, payment configuration and available capacity; check current network/job requirements. | Separate compute-provider business. Renting compute to run the agent is an expense, not an agent reward. Demand required. |
| [Akash](https://akash.network/docs/providers/getting-started/) | Compute-provider leases. | Linux/network/domain/hardware plus provider/Kubernetes operation and lease/payment setup. | Hosting marketplace, not reward per analysis hash. Deploying as a tenant costs money. |
| [io.net](https://io.net/docs/guides/workers/device-onboarding.md) | Eligible verified/hired device work and conditional block rewards. | Account/device onboarding, readiness/PoW checks, staking, supported hardware and uptime. [Supported devices](https://io.net/docs/guides/workers/supported-devices.md) currently includes listed Apple M3/M4 variants as well as listed NVIDIA devices. | Do not presume this Mac is eligible. Exact model, memory/OS, stake and cluster checks still required; simultaneous other mining/GPU load may block eligibility. Hardware rewards, not SHA receipts. |
| [Render](https://know.rendernetwork.com/general-render-network/what-role-am-i/how-to-get-started-1.md) | Accepted rendering/compute node work. | [Node interest form](https://renderfoundation.com/gpu), onboarding queue, supported NVIDIA/CUDA/driver/VRAM and workload conditions. | Not automatic enrollment or arbitrary Python-agent mining; hardware and demand gate. |
| [Filecoin](https://docs.filecoin.io/provide-storage/filecoin-economics/storage-proving.md) | Storage provider work and continuous proofs. | Provider infrastructure/data, collateral, proof/deadline operation and protocol economics; check live parameters. | Client storage/receipt fees do not make the client a rewarded provider. Missed proofs can trigger penalties/slashing. Older documented deal-duration values are not current guarantees. |
| [Arweave](https://docs.arweave.org/developers/mining/overview/mining.md) | Protocol-valid storage/mining work and accepted blocks. | Sync/pack network data, hardware/network/VDF and mining configuration; guide describes multi-terabyte partitions. | Actual protocol mining, not submitting a report digest for rewards. Publishing data costs and can create permanent privacy exposure. |
| [Bitcoin](https://developer.bitcoin.org/devguide/mining.html) | Valid block-header proof of work; accepted block/pool work. | Specialized competitive hardware, energy, software/pool setup and protocol-valid shares/blocks. | An ordinary SHA-256 report hash is not a valid mining share/block; Bitcoin can anchor existence through a separate service. |
| [OpenTimestamps](https://opentimestamps.org/) | Commitment existed before a verified Bitcoin anchor bound. | Create detached proof, submit to calendar, later upgrade and independently verify completed proof. Public calendars document free submission without registration/API key. | Best parallel existence candidate. Pending calendar submission is not confirmed proof. Not exact creation time, authorship, ownership, truth or automatic patent priority. |
| [EAS](https://github.com/ethereum-attestation-service/eas-contracts) | Schema-bound signed assertions, optional onchain records/resolvers. | Select chain/deployment/schema/attestor identity; sign offchain or pay gas for onchain attestation; define independent verification and revocation/supersession. | Optional identity/claim layer. Open protocol is not gas-free. An attestation proves an assertion was made, not its scientific correctness. |

### x402 network/cost snapshot

The checked [facilitator documentation](https://docs.cdp.coinbase.com/x402/seller/facilitator)
lists Base (8453)/Base Sepolia (84532), Polygon (137), Arbitrum (42161),
World (480)/World Sepolia (4801), and Solana mainnet/devnet.
Supported schemes vary by network: EVM exact/upto/batch-settlement and Solana
exact/upto are documented. Recheck asset/network/scheme support at implementation.

Its published pricing at research time: first 1,000 onchain transactions per
month free, then $0.001 per transaction; verification free. This is a provider
price snapshot, not zero total service cost or a permanent quote. Buyer gas,
hosting, analysis, human review, retries, refunds, compliance and asset conversion
must be accounted for. The documented dollar-price default uses network USDC;
verify token address/decimals and receiving destination on the exact network.
Testnet assets/points are not realized revenue.

## Service design that preserves the existing fifth pillar

Current [specialist contract](specialist-agent.md) deduplicates caller task
submission and returns a preview. An authorized human completes source-bound
inquiry and separately approves release. A fast paid HTTP response cannot
pretend this asynchronous work is already released.

Proposed paid contract:

1. Define the purchasable item clearly: an accepted bounded analysis job and
   expected review SLA, **not** a guaranteed favorable conclusion.
2. Authenticate caller ownership and scope; validate input and quote before
   charge where the payment scheme permits. Do not charge malformed/rejected
   requests without explicit disclosed terms.
3. Bind payment intent to caller/job/idempotency key and authorized amount.
   Settlement failure must be explicit; accepted-but-unsettled, refunded,
   rejected, pending review and released states remain distinct.
4. Return honest accepted/pending status with a retrieval capability scoped to
   that caller. Do not repeatedly charge retries/polling or double-deliver.
5. Keep previews marked unreviewed; paid buyers cannot self-complete inquiry,
   approve release or execute external actions.
6. Define timeout/rejection/cancellation and refund terms. Payment settlement
   and job writes require crash/replay reconciliation; no success-shaped fallback.
7. Release only after current inquiry/approval checks, returning the selected
   release-bound receipt and authorized content. Marketplace timeouts must
   accommodate this or the adapter is not suitable.

Before public deployment, add independently tested identity/tenant isolation,
abuse/rate/body controls, scoped credentials, key custody, TLS, audit/recovery,
payment replay defenses and supply-chain hardening. The current single-operator
local stack is not a production multiuser commerce service.

## Proposed per-invocation receipt contract

**Not implemented:** Existing ambient local chains do not cover every direct
CLI/library/sub-agent invocation and are not signed/externally anchored.
New receipt coverage must explicitly enumerate all supported entry points.
An invocation counter must not count replay retries as new billable work.

Record schema/domain/version, operator key ID and verified identity binding,
caller/task identifiers (private/pseudonymous as appropriate), idempotency,
request and terminal outcome, source/analysis/software/policy hashes,
environment/model/config where applicable, output digest, previous receipt,
human inquiry revision/hash and release status, correction/supersession,
payment intent/settlement/refund references and distinct charge status.
Operator timestamps are local claims, not independent time proofs.

Use a versioned deterministic encoding and explicit domain separation; publish
cross-language test vectors. Existing sorted Python JSON is **not RFC 8785
JCS**. Do not change old hashes to retrofit a new contract. Reject ambiguous
numbers, duplicate keys and unsupported encodings per the chosen contract.
Separate source-content hashes from receipt hashes.

For an optional Merkle batch, specify leaf/node prefixes, ordering, tree size,
index and proof algorithm. [RFC 9162 section 2.1](https://www.rfc-editor.org/rfc/rfc9162.txt)
provides a reviewed reference for domain-separated membership/consistency
concepts, not a claim of application conformance. Membership under a trusted
root does not prove all uses were logged, the input was true or the analysis useful.
Omission monitoring and independent witnesses are separate requirements.

Keep signature state, identity verification and anchor state separate:
`NOT_SUBMITTED`, `PENDING`, `CONFIRMED`, `VERIFIED`, `FAILED`, `SUPERSEDED`
must have defined transitions/evidence. Transaction presence alone is not
independent verification. Record chain/network, proof version, anchor/finality
policy, block references and verification results; handle reorganizations.

Publish only permitted commitments, preferably aggregate roots. Keep inquiries,
PII, prompts, source contents, private URLs and buyer identities off public
chains. Hashes can be linked or guessed; random nonces/salted commitments need
retained private verification material and explicit consent/retention policies.
Do not promise erasure of public immutable data. Key rotation/revocation,
compromise recovery and correction receipts must not erase historical evidence.

## Where the actual value could arise

Prospective products: source/claim trace dossiers, versioned audit exports,
bounded analysis with disclosed limitations, independently verifiable existence
receipts, and review-supported corrections. Buyer utility/demand must be
demonstrated; no customer, exchange listing or protocol acceptance is implied.

Estimate in a declared currency:

```text
net contribution per accepted job =
  realized payment - refunds - analysis/hosting - human review
  - facilitator/chain fees - allocated recovery/compliance costs
```

Measure rejected/failed/unpaid jobs too. For hardware/mining, also include energy,
depreciation, network/storage, registration burn, collateral opportunity cost,
slashing and price/liquidity risk. A token balance, emitted testnet credit or
gross settlement is not net profit. No investment-return forecast is made.

## Phases and acceptance gates

| Phase | Deliverable | Required evidence before advancing |
|---|---|---|
| 0: research (this update) | Source-checked alternatives, science/evidence boundaries, scope/onboarding plan. | Persistent docs/skills and manifest; no economic action. |
| 1: local receipt prototype | Versioned deterministic fixtures, signed receipts and offline verifier, invocation/replay coverage. | Tamper, duplicate, failure, correction, key-rotation and missing-record tests; old digest contracts unchanged. |
| 2: existence experiment | Detached OpenTimestamps proofs and optional private Merkle batch. | Independently verified completed anchor and membership; pending/failure explicitly represented; privacy review. |
| 3: payment testnet | x402 Base Sepolia adapter with fake/test assets and asynchronous jobs. | Owner-selected wallet/key custody, payment scheme and terms; replay/crash/refund/isolation tests; no paid self-approval. |
| 4: marketplace feasibility | One Olas/ACP sandbox adapter, or a specific Bittensor subnet benchmark. | Verified current terms/chain/cost/scoring, task TTL and human SLA; owner approves any funded sandbox/registration. No automatic launch. |
| 5: limited production | Owner-approved public service and tightly bounded mainnet budget. | Hardening/security review, legal/tax/asset considerations, identities/isolation, backups/monitoring, reconciled accounting and stop limits. |
| 6: comparative case studies | Held-out scientific and operational outcomes. | Predeclared study, consent, uncertainty/null/adverse results and measured buyer demand/costs, not token-price narratives. |

No phase authorizes spending, installing a miner or exposing this local service.
Before phases 2-5, the owner chooses privacy exposure, receiving destination,
custody, network, maximum fees/loss and service/refund terms. Documentation is
not onboarding completion or an execution grant.

## Scientific and author-source boundary

Follow [five-pillar scientific foundations](pillar-scientific-foundations.md)
and the [scientific evidence skill](../VesselFramework_Scientific_Evidence_SKILL_v0.1.md).
A verified prior-existence anchor supports a historical bound, a signature
supports a key assertion, and a reproducible calculation supports procedural
repeatability. A theorem needs assumptions/proof; efficacy needs empirical
evaluation. No combination automatically proves the complete theory.
Do not revise the original author's source document to make later software,
cryptographic or economic proposals appear historically established.
