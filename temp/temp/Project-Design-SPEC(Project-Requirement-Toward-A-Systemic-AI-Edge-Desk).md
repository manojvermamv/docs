## Tier 0 - Design SPEC

You're right that the **control** doesn't belong in the framework. But there's a critical difference between:

- **Controlling** the mode (flipping sandbox↔live) → **owner supervisor, external to the trading pipeline** ✅
- **Knowing** the mode (what state are we in *right now*) → **must stay in the system** ❌ if removed

If your project doesn't know its own execution mode, three things break silently. Here's the corrected split.

---

### 1. The Ownership Split

```
┌────────────────────────────────────────────────────────┐
│  OWNER SUPERVISOR (human / owner API :8002)            │
│  Calls OpenAlgo's sandbox/live switch API              │
│  Decides WHEN to change mode                           │
│  → session boundary: only between sessions, not mid-   │
│    session (same rule as prompt versions)              │
└───────────────────┬────────────────────────────────────┘
                    │ flips mode on OpenAlgo
                    ▼
┌────────────────────────────────────────────────────────┐
│  TRADING PIPELINE (your project)                       │
│  Does NOT own or set the mode                          │
│  DOES:                                                 │
│   1. DETECT current mode (query OpenAlgo / probe)      │
│   2. TAG every order + attribution row with it         │
│   3. GATE authority by it (live ⇒ trade authority)     │
│   4. RECORD mode transitions as events                 │
└────────────────────────────────────────────────────────┘
```

What gets deleted from my spec:
- ❌ `targets: {sandbox, live}` config blocks with dual base_urls/keys
- ❌ Mode as a *settable* config value in the framework
- ❌ Gateway routing logic choosing between instances

What stays (as **observed state, not config**):
- ✅ `execution_mode` as a **read-only, detected** value
- ✅ Per-order / per-attribution tagging
- ✅ Authority linkage

---

### 2. Why "Just Trust the Owner's Switch" Breaks Three Things

#### 2.1 Attribution integrity (fatal if skipped)
Every `AttributionRecord` needs `execution_mode`. If the project doesn't know the mode, sandbox and live track records **mix indistinguishably**, and the Wilson score / authority ladder loses its foundation. The tag must come from somewhere — either the owner tells the project ("I flipped it at 09:15") or the project detects it. Owner-told state drifts; detected state doesn't.

**Design:** mode is *observed*, not declared:
```
mode_probe() → calls OpenAlgo mode/status API (or a canary probe)
             → returns observed execution_mode
             → cached for the session, re-verified at session start
             → mismatch vs. last-known → event + warning
```

#### 2.2 Authority gating (safety invariant)
Your existing invariant: `authority: trade` + `execution.live` required to send real orders. If the pipeline can't observe the mode, it can't enforce *"trade authority is only exercised when the target is live."* Otherwise a mis-flipped switch means "live" orders silently going to sandbox (harmless but corrupts track record) — or worse, sandbox-intended testing suddenly hitting the real broker with no authority check in the path.

**The rule that must survive:** the execution gateway checks *observed mode* before exercising `trade` authority. The owner controls the switch; the pipeline still refuses to fire real orders unless it *confirms* it's live — and refuses to tag sandbox results as track-record-eligible unless it *confirms* sandbox.

#### 2.3 Session boundary semantics
A mode flip mid-session corrupts attribution continuity (half a stance's lifecycle in sandbox, half in live). The supervisor should flip **only between sessions**, and the pipeline should record the flip as an event (`mode_changed` in the events stream) — this is exactly your prompt-version session-boundary pattern, reused. Cheap, consistent, already understood.

---

### 3. Revised Minimal Config

```yaml
execution:
  # No mode setting. No targets. Just:
  authority_check: observed-mode-required   # gateway verifies before trade authority
  mode_probe_interval: on-session-start     # + on-demand via MCP
```

And one new small component:

```
src/runtime/execution_gateway/mode_probe.py
  - observed_mode() → "sandbox" | "live" | "unknown"
  - "unknown" is treated as the SAFE state: blocks trade authority,
    allows observation only. (Fail-closed, consistent with your gates.)
```

Owner supervisor flow:

```
Owner (Telegram / :8002) → OpenAlgo switch API → mode flipped
Owner (or scheduled job) → triggers pipeline mode re-probe
Pipeline                 → verifies, emits mode_changed event, tags session
```

---

### 4. Residual Risk to Document in `DECISIONS.md`

**Detection window:** if the owner flips the switch and the pipeline doesn't re-probe (or OpenAlgo's mode status API lags), orders in that window are tagged with the *previous* mode. Mitigations, in order of strength:
1. **Procedural:** mode flips only between sessions; first probe of a session is mandatory before any plan fires (add as gate-0 check or fold into session gates).
2. **Reconciliation:** the reconciler (§1.5) already pulls orderbook/positionbook — sandbox and live instances have distinguishable data footprints; flag mismatches between observed mode and order-source.
3. **Manual override:** owner API endpoint to force-correct the observed mode, audited like every other owner action.

---

### Bottom Line

| Concern | Owner | Your Project |
|---|---|---|
| Flip sandbox/live | ✅ via OpenAlgo API, external to pipeline | ❌ no config, no routing, no dual targets |
| Know current mode | via supervision policy | ✅ **detect + tag + gate on it** (fail-closed on "unknown") |
| Session boundary for flips | ✅ enforces timing | records the `mode_changed` event |
| Authority vs. mode | approves the policy | ✅ enforces at gateway (observed mode only) |

This makes the design *simpler* than my previous spec (one OpenAlgo instance, one connection, one API key) while keeping the two invariants that make shadow-mode track records trustworthy: **observed-mode tagging** and **authority-gated live execution**. The supervisor owns the *decision*; the pipeline owns the *proof* of which world it's trading in.

Want me to fold this into the build order (it shrinks step 3 to just the mode-probe + tagging, removing the routing layer entirely)?

---

## TIER 1 — Converting Measurement into an Edge (Design Specs)
*(Built on completed Tier-0: execution FSM, attribution schema, observed-mode probing, OpenAlgo unified API, owner-controlled mode switch)*

---

### 5. Prompt A/B Replay Harness (with Replay Engine, B5)

#### 5.1 Prerequisite: The Replay Engine

This is the single biggest lever still unpulled. It re-drives the **entire live pipeline** against the historical tape — same feed primitives, same orchestrator gates, same FSM, same advisor calls — with the only difference being *time comes from the tape, not from the wall clock*.

```
src/replay/
├── clock.py          # ReplayClock: deterministic time source (implements clock interface)
├── feed_replay.py    # reads tape parquet → emits Snapshot/History at exact seq points
├── runner.py         # orchestrates: strategy → advisor → journal → plan() → FSM(sim)
└── session_spec.py   # defines: date range, strategy, prompt version, mode, seed
```

**Design rules:**
- **Clock injection, not time mocking.** Every freshness gate, session gate, and advisor timeout reads from an injected `Clock` interface. Live = `WallClock`, replay = `ReplayClock`. If any module calls `datetime.now()` directly, replay is broken — add a CI grep-gate for direct time calls in hot-path modules.
- **Advisor replay mode:** two sub-modes:
  - `advisor=frozen`: prompts run live against the model per replayed bar (real A/B, costs tokens, is the real thing).
  - `advisor=cached`: previously-recorded advisor responses keyed by `(seq, prompt_version, context_digest)` — free, deterministic, used for regression replays after prompt *engineering* changes that shouldn't alter model behavior.
- **Context digest discipline:** the advisor's input context must be hashed. Identical digest + identical prompt version ⇒ cached response valid. This makes replays bit-reproducible.
- **Output:** replay sessions emit the *same artifacts as live* — decisions, plans, gate verdicts, FSM transitions, attribution records — tagged `origin: replay` (mirrors the `execution_mode` tagging pattern from Tier-0).

#### 5.2 The A/B Harness

```
src/eval/
├── experiment.py    # Experiment spec: baseline_prompt, challenger_prompt, session set
├── executor.py      # runs replay per arm (sequential or parallel)
├── stats.py         # comparison: Wilson, bootstrap CI on edge_bps, paired tests
└── report.py        # readable artifact → console + MCP analysis domain
```

**Experiment spec:**
```yaml
experiment: prompt-v6-vs-v7
sessions: [2025-01-06, 2025-01-07, ...]   # fixed, frozen session list
strategy: ai_breakout
baseline: config/profiles/ai_breakout/v0006.json
challenger: config/profiles/ai_breakout/v0007.json
mode: sandbox            # or replay-against-tape; never live for experiments
decision_rule:
  promote_if: challenger_wilson_lb > baseline_wilson_lb AND n >= 30 stances
  demote_if:  challenger significantly worse at alpha = 0.05
```

**Statistical honesty rules (the part most A/B harnesses skip):**
- **Paired comparison where possible:** same tape, same seq → many decisions are identical between arms; report agreement rate. Differences only exist where the prompts diverge — analyze *that subset* with paired stats, not aggregate totals.
- **Multiple-comparison guard:** if you run many experiments against the same sessions, session data gets "used up." Track a reuse counter; require fresh sessions for promotion decisions after N reuses.
- **No peeking:** promotion rule evaluated once at experiment end, not continuously (same discipline as the session-boundary prompt activation you already have).

**MCP wiring:** `eval` tools in the analysis domain: `eval_run(spec)`, `eval_status(id)`, `eval_report(id)` — scheduled via the existing jobs domain.

---

### 6. Authority Ladder Tied to Skill Scores (F3.1)

#### 6.1 The Ladder

```
src/authority/
├── tiers.py         # tier definitions + requirements (data, not code)
├── evaluator.py     # computes current tier from attribution + value.py
├── enforcer.py      # consulted by execution gateway / orchestrator / RiskGuard
└── store.py         # tier transitions log (append-only, like FSM transitions)
```

| Tier | Name | Entry requirement | Unlocks |
|---|---|---|---|
| T0 | Observe | default | read tools, proposals recorded, never planned |
| T1 | Shadow | auto | proposals flow through full orchestrator into sandbox-mode session |
| T2 | Capped Live | T1 record: ≥ N stances, Wilson lower bound > 0, sandbox→live calibration factor applied, max drawdown < cap | live execution, notional hard-capped (tighter sizing gate: reduced per-trade cap, reduced exposure cap) |
| T3 | Scaled | T2 record: ≥ M live stances, same criteria, slippage within calibration bounds | full notional caps |

#### 6.2 Mechanics — the critical design points

1. **Measurement automatic, promotion human.** `tiers.py` recomputes eligibility continuously from attribution records. Crossing a threshold emits an event + Telegram request. A human taps approve. **Demotion is automatic and instant** — reducing risk needs no human latency: score floor breach → T1 immediately, breaker fires if drawdown breaches.
2. **Score inputs are edge-based, not binary.** Feed `value.py` from attribution: `attributed_edge_bps`, MAE/MFE, *minus* the sandbox calibration discount from Tier-0. A shadow record is discounted by the measured sandbox-optimism factor before it can qualify for T2.
3. **Tier is checked at the same choke points as authority today:**
   - orchestrator: T0 proposals never reach `plan()`
   - execution gateway: T2 caps enforced *inside gate 7* (quantity) — the cap is expressed as a quantity/notional bound, so it reuses the existing gate rather than adding a parallel check
   - RiskGuard: per-tier rate limits
4. **Per-prompt-version, not per-AI.** The tier binds to `(strategy_id, prompt_version)` — v7 doesn't inherit v6's track record. This is what makes the A/B harness (item 5) and the ladder the *same system*: promotions are the payoff of winning experiments.
5. **Cold-start rule:** new prompt versions start at T1 (shadow) regardless of the AI's history. Track records are earned per version.

**DECISIONS.md entry required:** tier thresholds live in `config/authority.json`, changes are owner-audited, and the tier-transition log is a read-only contract view so the AI can always answer "what am I allowed to do right now and why."

---

### 7. Automated Circuit Breakers + AI Proposal Budgets (B2)

#### 7.1 Breakers

```
src/risk/breakers/
├── base.py          # Breaker interface: check(events, state) → Trip | None
├── loss.py          # daily loss, rolling drawdown, per-strategy loss
├── data.py          # feed staleness, seq gaps, price-sanity violations (spikes, chain anomalies)
├── execution.py     # FSM: CLOSED_UNRESOLVED count, reconciler drift, send failure rate
├── ai.py            # advisor score floor breach, refusal rate spike, proposal budget exhaustion
└── engine.py        # evaluates all breakers each tick + on events; trips are latching
```

**Design rules:**
- **Latching:** a tripped breaker requires explicit owner reset (existing kill-switch path + Telegram). Auto-retry after a breaker is how small incidents become big ones.
- **Tiered severity:** `SOFT` (stop new entries, manage existing stops/exits normally), `HARD` (kill-switch equivalent, flatten via existing EXIT path), `FREEZE` (data-integrity: no orders *or* cancels until reconciler is clean — cancelling on corrupt state is dangerous).
- **Breakers feed the same registry as the kill switch** — orchestrator gate 1 needs no change; the kill switch becomes *multi-source* (human + engine).
- **All inputs come from artifacts you already have post-Tier-0:** FSM transitions, reconciliation reports, attribution rows, tape sanity. No new data collection.
- **Every trip emits an event** (see item 9) with the full evidence chain — the AI must be able to query *"why are we flat?"* and get the breaker's reasoning, not guess.

#### 7.2 AI Proposal Budgets

Extends RiskGuard from *tool-call* limits to *decision-quality* limits:

```
per session, per (prompt_version):
  max_proposals: N                    # raw volume cap
  max_consecutive_refusals: K         # after K, advisor is cooled down (no advisor calls for X bars)
  max_net_exposure_committed: notional cap across the session
  penalty_score: refusals + repeated similar refusals feed the AI-tier score (item 6)
```

Key nuance: refusals are **signal, not just spam**. Persist refusal reasons (Tier-0 gate-verdict traces) and feed a "which gates reject you most" digest back into advisor context. The budget isn't punishment — it converts gate refusals into a learning channel. An advisor that keeps failing gate 7 (sizing) is over-confident; that's a measurable, coachable behavior.

---

### 8. Portfolio-Level Risk Gate + `src/risk/` (Trader Context)

**Scope note respected:** this is *trader* risk — exposure, greeks, correlation of concurrent open stances, capital budget per strategy — not investment-portfolio theory. The "portfolio" is the open book of stances at 10:30am, not a retirement allocation.

```
src/risk/
├── portfolio.py     # PortfolioState: aggregate view of the open book
├── exposures.py     # net delta/theta/vega from broker-greeks already in tape store
├── correlation.py   # concurrent-stance correlation on the same underlying / same expiry
├── budget.py        # per-strategy capital budgets (limits, not optimization)
├── gate.py          # gate 8 replacement: portfolio-level refusal
└── limits.py        # declarative config: config/risk_limits.json
```

#### 8.1 `PortfolioState` — one aggregate object, rebuilt from truth
Built from: current book view + FSM-filled orders + broker-greeks from the tape store + OpenAlgo positionbook (reconciler cross-check). Nothing computes exposure from memory — always from persisted, reconciled state.

#### 8.2 The Portfolio Gate (evolves gate 8, doesn't bypass the pattern)

```yaml
# config/risk_limits.json
limits:
  max_open_stances: 5                 # existing gate 8, kept
  max_gross_notional: 500000
  max_net_delta_notional: 150000      # directional exposure, not per-position
  max_daily_theta_burn: 8000          # buyer-side decay bleed, trader-specific
  max_same_expiry_stances: 3          # event clustering (same expiry = same event risk)
  max_correlated_stances: 2           # same underlying direction
  per_strategy:
    buyer_edge:   {max_notional: 250000, max_stances: 3}
    ai_breakout:  {max_notional: 150000, max_stances: 2}   # tighter while AI tier < T3
  session_loss_floor: -15000          # feeds breaker (item 7)
```

**Key behaviors:**
- Refusal verdicts are structured (Tier-0 pattern): `{gate: portfolio, verdict: refuse, reason: net_delta_exceeded, headroom: 42000}` — so the AI learns *how much room* exists, not just "no."
- **Budgets, not optimization:** `budget.py` enforces caps; it does *not* allocate. Allocation intelligence is the AI's/advisor's job at Tier-2; the gate only refuses. Keep risk mechanical, keep judgment in the loop.
- AI-tier coupling: AI-strategy budgets scale with authority tier (T2 = 50% of full budget), tying items 6→8 into one coherent risk surface.

**Tests:** concurrent stances on same underlying/expiry refuse at threshold; delta aggregation matches reconciled book after partial fills (FSM join); per-strategy budgets independent; correlation refusal message includes headroom.

---

## TIER 2 — Systemic Desk Scale-Out (Design Specs)
*(Built on completed Tier-0: execution FSM, attribution schema, observed-mode probing, OpenAlgo unified API, owner-controlled mode switch)*

---

### 9. Event Bus + Supervisor Wiring (B6, E)

#### 9.1 Event Bus — typed, append-first, boring on purpose

```
src/bus/
├── events.py        # typed event schemas (dataclasses, versioned)
├── stream.py        # append-only JSONL per day, same discipline as tape/audit logs
├── pub.py           # emit(event) — the ONLY write API
└── sub.py           # tail-follow readers; in-process subscribers + file watchers for other processes
```

**Deliberate design choice: file-backed JSONL, not Kafka/Redis.** Reasons: (a) your infra is fully self-owned, single machine scale is fine for one desk; (b) events double as the audit artifact — append-only file *is* the log, no dual-write problem; (c) every process already reads/writes shared `run/` artifacts, so subscription = tailing. Upgrade path documented, not built: the `emit()` API is the seam — swap the backend later, zero caller changes.

**Event catalog (minimum):**
```
mode_changed, order_transition, fill_recorded, gate_refused, plan_created,
breaker_tripped, breaker_reset, tier_changed, reconciliation_report,
advisor_call, advisor_verdict, regime_changed, supervisor_health, owner_action
```
Everything already produced by Tier-0/1 (FSM transitions, breaker trips, attribution builds, tier changes, mode probes) becomes an event emission — the bus is mostly *wiring existing outputs together*, not new state.

#### 9.2 Supervisor — the missing lifecycle owner

```
src/supervisor/
├── manifest.py      # declares processes: feed, strategy_host, gateway(:8000/1/2), fsm driver, jobs
├── health.py        # heartbeat expectation per process; staleness = incident
├── restart.py       # restart policy per process class; escalation after N failures
└── startorder.py    # dependency-ordered boot: bus → feed → gateway → host → jobs
```

- **Heartbeats:** every long-running process appends to the bus (`supervisor_health` every 30s). The supervisor detects *absence* of heartbeats — this is the cheap, reliable liveness signal that also survives the file-based bus choice.
- **Restart safety:** a restarting execution gateway must re-probe mode (Tier-0) and re-run the reconciler against OpenAlgo orderbook before re-enabling trade authority. Restart ≠ trust.
- **Boot sequence as events:** full startup/shutdown is event-recorded, so "what was running when this happened" is always answerable.
- Console + MCP `monitoring` gain `desk_health()` — one tool answering "is every process alive, in what mode, what tier, any latched breakers."

---

### 10. Hot-Path / AI-Plane Process Isolation (B3)

#### 10.1 The Split

```
HOT PATH (process "desk-core"):                    AI PLANE (processes):
  feed capture                                        MCP gateway (all ports)
  orchestrator.plan()                                 analysis / research tools
  execution gateway + FSM driver                      advisor HTTP endpoint
  reconciler + breakers                               jobs scheduler
  event emission                                      console backend

  → no MCP imports, no model calls,                   → never calls OpenAlgo directly,
  → minimal dependency surface                          never touches journals' write path
  → communicates ONLY via: bus files + contract dir   → reads contract, writes proposals
```

#### 10.2 Rules that make the isolation real

1. **Dependency-direction CI gate:** `desk-core` package must not import `interfaces.*` or any LLM SDK. One import-linter rule; enforced in CI. The existing credential-stripping pattern (`_child_env`) extends naturally: the AI plane's process env has *no* OpenAlgo key at all — not even via the gateway.
2. **Crash containment:** MCP gateway crash → hot path keeps trading, AI plane restarts under supervisor. Feed stall → AI plane keeps analyzing the last good tape while breakers (item 7) handle trading safety. Neither can take the other down.
3. **The only shared surfaces:** the contract directory (read) and the bus (write/read). Both already exist and are already cross-process by design — this is *formalizing* the boundary you already imply, not a rewrite.
4. **AI-plane restart is cheap and frequent-safe:** it holds no authoritative state. Everything it knows is reconstructible from contract + bus. This property is what makes it safe to iterate on the AI plane aggressively (new tools, new prompts, new agents) without ever risking the money path.
5. Deployment unit: supervisor (item 9) manages both process groups; hot-path restart policy is *more* conservative (restart only after reconciler-clean) than AI-plane (restart freely).

---

### 11. Regime Layer + Richer Advisory Channel (B4, F3.3)

#### 11.1 Regime Layer

```
src/regime/
├── features.py      # realized vol, IV rank (chain greeks/IV from tape), gap behavior, trend state, event calendar
├── classifier.py    # rule-based first (transparent), ML later — never the reverse
├── store.py         # regime labels as events + parquet, point-in-time safe
└── hooks.py         # where regime feeds: gates, advisor context, breakers, budgets
```

- **Start rule-based** (e.g., IV-rank terciles × realized-vol state × event-proximity). Every regime label is *explainable* — critical because it appears in AI context and audit trails. ML regime models come later, behind the same interface.
- **Consumers (the actual value):**
  1. **Advisor context:** every advisor call includes a regime block + the AI's per-regime skill history ("your directional calls in high-IV-gap regimes: negative edge, n=12"). This is item 6's skill data made *situational*.
  2. **Gates:** optional regime-conditioned sizing multipliers / exposure caps (e.g., halve caps in event-eve regimes).
  3. **Breakers:** data-anomaly thresholds vary by regime (vol spike ≠ data fault).
  4. **Attribution:** every record gains `regime` → the A/B harness can answer "does v7 beat v6 *in trending regimes*?" — the sharpest questions become simple filters.
- Regime changes emit `regime_changed` events → AI plane can trigger analysis jobs on shifts.

#### 11.2 Richer Advisory Channel — "AI writes code; code trades"

This is the scale-out for AI capability that keeps your safety model intact:

```
AI (via MCP research domain) → drafts a library-kind strategy file
        ↓
static validation suite (AST checks, contract conformance, gate-coverage tests required)
        ↓
REPLAY against historical tape (item 5's engine) → evaluation report
        ↓
SHADOW: runs as a worker in sandbox-mode sessions under authority ladder T1
        ↓
human reviews report + code diff → approves → promoted like any strategy
        ↓
runs deterministically thereafter — the AI's involvement ends at promotion
```

**Why this shape:**
- The **Intent funnel stays the money boundary, unchanged.** Live trading is still conviction → 10 gates → FSM. No AI in the money path at runtime, ever.
- But the AI's *capability* now scales: a good model can express a whole strategy (logic, filters, exits) rather than one scalar per bar — the ceiling of the `Intent(conviction, direction)` interface is bypassed *at authoring time*, not at runtime.
- Reuses every piece you've built: the strategy-host AST auto-registration (extend validation, don't replace), the replay engine for evaluation, the attribution + ladder for promotion evidence.
- `Intent` schema gains optional richness (`uncertainty`, `horizon`, `invalidation`) as **advisory fields the framework may use** (e.g., invalidation triggers early exit evaluation) — additive, versioned, backward-compatible with deterministic strategies.

---

### 12. Multi-Agent Identity/Scoping + Context-Indexing (F3.4–5)

#### 12.1 Agent Identity & Scoping

```
src/identity/
├── agent.py         # AgentIdentity: {agent_id, role, owner, key}
├── scopes.py        # role→scope mapping: analyst | risk_officer | executor | observer
└── attribution.py   # every journal entry, tool call, proposal tagged with agent_id
```

- **Today:** one Claude = one implicit identity. Change nothing user-facing; just stamp a default `agent_id` everywhere — this makes every existing artifact agent-attributable *from now on*, so history exists when the second agent arrives.
- **Tomorrow:** roles with distinct authorities:
  - `analyst` — read + research tools, proposes prompt amendments
  - `risk_officer` — read + breaker-adjacent visibility, cannot propose trades
  - `executor` — proposal path only, gated by the authority ladder
- Enforcement points already exist — identity plugs into RiskGuard (scopes per agent, not per endpoint) and the journal write path (every `Intent` carries `agent_id`). The authority ladder (item 6) binds per `(agent_id, prompt_version)`.
- **Audit upgrade:** the forensic-reconstruction requirement (prompt version + context digest + tool calls + resulting intent) becomes per-agent — multi-agent blame/credit is queryable, and agent interactions become training/eval data.

#### 12.2 Context-Indexing Layer

125 tools × growing tape will drown any model's context. Build the retrieval layer the AI *reads through*, not around:

```
src/context/
├── digest.py        # session digests: PnL, refusals, regimes, incidents, breaker events → one artifact
├── views.py         # materialized views over attribution/journals (per-strategy, per-regime, per-prompt rollups)
├── retrieval.py     # as-of-safe lookup over decision journal + events ("what happened around 10:42 on Jan 7")
└── tool_guide.py    # curated tool routing: task-type → recommended tool sequence (shrinks exploration cost)
```

- **Digests are the AI's morning brief:** one compact artifact replacing dozens of tool calls; written by scheduled jobs, stored in the contract as a read-only view, delivered via MCP `prompts`/`analysis`.
- **Retrieval is point-in-time enforced** — same as-of discipline as the tape; no "future-leaking" lookups in AI context (a research-leak bug here would corrupt every judgment downstream).
- **The rule for tool growth:** new capabilities should prefer *fewer, richer* tools over more tools (e.g., one `desk_brief()` beats ten query tools). Cap total tool count; retire tools with zero usage (track tool usage in RiskGuard audit — you already log every call).

---

## Build Order (Dependency-Correct, Cross-Tier)

```
Tier 1:
  1. replay engine core (item 5)          ← biggest lever, unblocks 5/11/strat-authoring
  2. authority tiers (item 6)             ← needs only Tier-0 attribution (done)
  3. breakers + budgets (item 7)          ← feeds tier demotion (6) — build together
  4. src/risk/ portfolio gate (item 8)    ← mechanical, independent
  5. A/B harness on top of replay         ← completes item 5

Tier 2:
  6. event bus + supervisor (item 9)      ← formalizes existing artifacts
  7. process isolation (item 10)          ← reorganizes, doesn't rewrite; bus makes it clean
  8. regime layer (item 11a)              ← needs replay for validation of regime rules
  9. advisory authoring channel (item 11b)← needs replay + ladder + attribution (all prior)
 10. identity + context indexing (item 12)← last: retroactive tagging is cheap, prevention is better but early value is low until multi-agent is real
```

**Sequencing logic:** items 2+3 together give you a self-limiting AI (earn authority, lose it on failure, halt on tail risk) — that's the *edge-with-brakes* milestone. Item 5's replay engine is the single highest-leverage build in the whole program: it converts every subsequent change (prompts, regimes, AI-authored strategies) from "try it live and hope" into "replay, compare, promote."

Want the detailed spec for the replay engine alone next? It's the keystone — everything in Tier 2's learning loop inherits its determinism guarantees.
