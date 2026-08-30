# Architecture Gap Analysis & Required Evolution : Toward a Systemic AI-Edge Desk

## OX-Alpha AI - TURN 1 

Your control plane is strong on **safety invariants** (gates, isolation, audit). The gaps below are what separate it from a *systemic* desk — one that works as a coherent system with a durable AI edge — rather than a well-guarded single-strategy rig.

---

### 1. Cognitive / Edge Gaps (the AI edge itself)

| Gap | Evidence in Report | Why It Matters |
|---|---|---|
| **No closed-loop learning** | Advisor evaluates directional skill via Wilson scores, but nothing feeds results back into prompts/models | Skill measurement without adaptation = static edge. Need a feedback loop: eval → prompt/model version bump → A/B comparison |
| **Single-strategy conviction only** | Framework returns 0.0–1.0 conviction per signal | "Systemic" requires cross-strategy capital allocation, correlation awareness, and portfolio-level risk — not per-trade sizing |
| **No regime detection** | Gates check freshness/session only | An AI edge that doesn't condition on volatility regime / market state decays silently |
| **Prompt versioning ≠ evaluation harness** | Prompt versions are session boundaries, but no systematic backtest-of-prompts | Need replay: same historical feed through v1 vs v2 prompts with statistical comparison |

### 2. Data & Feedback Gaps

- **Attribution layer missing**: decision journal + fills exist, but no PnL attribution per decision point (which gate/conviction/AI call caused the outcome?). Without attribution, the AI observes "performance" only coarsely.
- **Post-trade telemetry is incomplete**: slippage, partial fills, latency per order leg aren't surfaced to the analysis domain. AI can't diagnose execution edge.
- **No feature store / point-in-time correctness for research**: the tape is lookahead-safe for evaluation, but research tooling likely reads it ad hoc — risk of subtle leakage in AI training/analysis.

### 3. Orchestrator / Control-Plane Gaps

1. **Gate 10 ends at `request` validation — no execution-state machine.** Order lifecycle (pending → partial → filled → rejected) needs explicit state reconciliation and re-plan triggers. The ownership registry write is pre-call, but timeout *recovery* semantics aren't specified.
2. **No portfolio-level exposure gate.** Gate 8 checks "max open positions" — flat count, not notional/greek/correlation exposure across stances.
3. **Kill switch is operator-only.** A systemic desk needs *automated circuit breakers* (daily loss, drawdown, data-anomaly) that trip without human latency.
4. **Single failure domain.** Gateway, orchestrator, feed, and MCP all appear in-process. A crash in MCP tooling can take the trading loop down. Split the *trading hot path* from the *AI plane* by process boundary + heartbeat.

### 4. Observability & Governance Gaps

- **No decision replay**: you have audit logs, but can you deterministically reconstruct *why* any past plan was refused or approved, step by step? Gates should emit structured per-gate verdicts (you likely have refusals but not a replayable trace format).
- **Shadow mode / paper-vs-live parity**: nothing indicates AI proposals can run against the real feed *without* capital as a continuous shadow book to build the track record the Wilson score needs.
- **AI action budget**: RiskGuard rate-limits tool calls, but there's no budget/quota on *AI-originated proposals per session* or proposal-quality gating (e.g., AI proposals must pass the same 10 gates — confirm `propose.py` intents actually route through `orchestrator.plan()` in live mode, not just worker journals).

### 5. Prioritized Roadmap

| Priority | Item | Effort | Impact |
|---|---|---|---|
| P0 | Execution-state machine + fill reconciliation loop | M | Prevents orphaned/partial positions |
| P0 | Automated circuit breakers (loss/data/latency) | S | Systemic safety without human latency |
| P0 | Shadow-mode continuous AI track record | M | Builds the evidence base for the edge |
| P1 | Per-decision PnL attribution pipeline | M | Makes AI analysis actionable |
| P1 | Portfolio-level exposure & correlation gate | M | True desk-level risk |
| P1 | Prompt A/B replay harness | M | Converts prompt versioning into measurable edge |
| P2 | Regime conditioning in advisor | L | Adaptive edge |
| P2 | Hot-path/AI-plane process isolation + heartbeats | M | Resilience |
| P2 | Multi-strategy capital allocator on conviction | L | "Systemic" scale-out |

---

**Bottom line:** the architecture currently guarantees *an AI can't do damage* — verified thoroughly. What's missing is the machinery to prove and compound *an AI adds value*: closed-loop learning, shadow track records, attribution, portfolio-level risk, and automated breakers. Those five close the gap from "guarded rig" to "systemic desk with AI edge."

----

## OX-Alpha AI - TURN 2

**Full-Stack Gap Analysis: Plan · Architecture · Structure · Implementation · Wiring**  
**Plus: Current AI Working Style vs. Required Future AI Capability**  

---

### A. PLAN-LEVEL GAPS (What the roadmap itself is missing)

| Gap | Detail |
|---|---|
| **No edge hypothesis statement** | The plan documents *safety* exhaustively but never states *where the edge is supposed to come from* (directional skill? timing? execution?). Without a falsifiable edge thesis, "AI edge" can't be measured as achieved or failed. |
| **No promotion ladder defined** | There's an implicit path (proposal → shadow → live) but no formal stages with entry/exit criteria: `observe-only → shadow proposals → capped live → scaled live`. The Wilson score exists but nothing defines *what score unlocks what authority*. |
| **No AI capability roadmap in the plan** | The plan assumes the AI is a stationary assistant (observe, analyze, propose). Nothing anticipates agentic AI that plans multi-step, holds context across sessions, or self-modifies prompts/strategies. This is a plan-level omission, not just an implementation one. |
| **Success metrics absent** | No defined KPIs: hit-rate vs. baseline, Sharpe of AI-modified vs. deterministic-only, prompt-version lift, gate-refusal intelligence (is AI learning which proposals pass?). |
| **Single-strategy dependency** | Entire plan is BuyerEdge-centric. A "desk" implies a book of strategies with a capital allocation layer — absent from planning docs, not just code. |

---

### B. ARCHITECTURE GAPS

#### B1. Structural architecture
1. **No portfolio/risk layer.** Gate 8 is position-count based. Missing: aggregate notional, greek exposure (net delta/theta on the option book), correlation between concurrent stances, and per-strategy capital budgets.
2. **No execution state machine.** After `open_order → mark_sent → broker call`, there is no explicit FSM for `pending → partial → filled / rejected / timeout-unknown` with reconciliation and re-plan triggers. The pre-call registry write solves *tracking*, not *recovery*.
3. **Hot path ≠ AI plane.** Feed → orchestrator → execution should be an isolated process with a heartbeat; MCP gateway, research, and analysis are crash-prone companions and currently appear to share the failure domain.
4. **No regime/context layer.** Gates check freshness and session, but nothing conditions behavior on volatility regime, event calendar, or market state. The advisor receives directional questions without context conditioning.
5. **Time-travel / replay engine missing.** The tape is append-only and lookahead-safe (excellent), but there is no component that can *re-drive* the full pipeline (feed → strategy → advisor → gates) against historical tape. This single component unlocks backtests, prompt evaluation, and incident replay — its absence is the biggest architectural lever un-pulled.
6. **No event bus.** Communication is via files/journals/direct calls. A systemic desk needs a typed event stream (fills, gate refusals, advisor calls, regime changes) that all planes subscribe to — this is also what makes future AI agents observable.

#### B2. Safety architecture (mostly strong, residual gaps)
- ✅ Credential isolation, single write path, 10 gates, ownership registry — verified.
- ❌ **Automated circuit breakers**: kill switch is human-only. Need loss-rate, drawdown, data-anomaly, latency-anomaly breakers that trip autonomously.
- ❌ **AI proposal budget**: RiskGuard rate-limits tool calls, but no per-session quota on AI-originated proposals, no penalty for repeatedly-refused proposals, no "cooldown" on an advisor whose Wilson score dips negative.
- ❌ **Ambiguity**: do AI worker journal intents *actually route through* `orchestrator.plan()` in live mode, or only when the worker is scheduled? The propose→plan linkage should be an architectural invariant with a test proving it.

---

### C. STRUCTURE GAPS (code organization)

| Gap | Detail |
|---|---|
| **No `src/risk/portfolio.py`** | Sizing/exposure logic is per-position; there's no home for portfolio-level risk objects. |
| **No `src/learning/` or `src/eval/`** | Skill evaluation lives in `advisor/value.py`, but prompt evaluation, A/B harness, and attribution have no structural home — so they'll be bolted onto MCP tools ad hoc. |
| **Attribution has no module** | Decision journal + fills exist; nothing joins `decision → plan → order → fill → PnL` into an attributed record. Needs a first-class artifact, not a query. |
| **Contract is read-only by design — but no write-side schema versioning** | Journals/parquet are append-only, but there's no schema-evolution story; adding fields to `Intent` or gate verdicts will break readers. |
| **Strategy↔framework interface too narrow for future AI** | `Intent(conviction, direction, reason)` cannot express: multi-leg structures, conditional orders, time-based exits, or *uncertainty*. Future AI needs a richer proposal vocabulary (or the AI will be forced through a deterministic funnel that discards its information). |

---

### D. IMPLEMENTATION GAPS

1. **Reconciliation loop**: no evidence of an order-state reconciler polling OpenAlgo against the ownership registry (drift detection, unknown-fill detection).
2. **Shadow mode**: nothing implements continuous AI-proposal-against-live-feed-without-capital. The Wilson score has no data source until this exists.
3. **Prompt A/B harness**: prompt versioning is a session boundary only — no tooling replays the same tape through two prompt versions and compares outcomes statistically.
4. **Gate verdicts not replayable**: refusals presumably log a reason, but not a structured, per-gate, timestamped verdict trace that can be re-assembled into "why did this plan die" — required for AI self-analysis and incident forensics.
5. **Slippage/latency telemetry**: fills aren't annotated with decision-to-send latency, send-to-fill latency, and slippage vs. expected — the AI literally cannot see execution quality.
6. **Feature point-in-time discipline for research**: tape is safe for evaluation; research tooling reading parquet directly has no enforcement of as-of joins. One leaked feature silently invalidates all analysis.
7. **Testing gaps beyond E2E**: 9 harness demos cover happy paths. Missing: chaos tests (broker timeout mid-order, feed stall, journal corruption), property tests on the lookahead guarantee, and a test proving credential stripping.

---

### E. WIRING GAPS (how pieces connect end-to-end)

```
Market data → Strategy → Advisor → Journal → Orchestrator → Exec Gateway → Broker → Fills → PnL
     ✅           ✅         ⚠️        ✅         ✅            ✅           ⚠️      ❌      ❌
```

- ✅ **Wired well**: data capture → feed primitives → strategy conviction → intent journal → gates → execution.
- ⚠️ **Partially wired**: Advisor talks to ai_worker via sampling/HTTP, but nothing closes the loop *back* — advisor outcomes don't update advisor behavior, profiles, or authority.
- ❌ **Unwired segments**:
  - **Fills → attribution → analysis domain**: no pipeline from broker fills to attributed PnL records the AI can query.
  - **Skill score → authority**: nothing programmatically connects `value.py` output to what the AI is *allowed* to do.
  - **Gate refusals → AI learning signal**: AI sees refusals as log text, not as a structured feedback channel.
  - **Console ↔ MCP**: both read the contract, but operator actions (kill switch, approvals) don't emit events the AI plane subscribes to — human and AI act in parallel with no shared situational stream.
  - **Multi-process orchestration**: who owns the full lifecycle (start feed, start host, start gateway, health-check all, restart policy)? No supervisor/wiring layer is described.

---

### F. AI BEHAVIOR — TODAY vs. REQUIRED EVOLUTION

#### F1. Current AI working style (as the system implies it)
The system is built for an AI that is a **reactive, single-turn analyst**:
- Observes via read-only MCP tools.
- Emits one Intent at a time through a narrow funnel.
- Gets evaluated by a scalar Wilson score.
- Human approves anything consequential (Telegram).
- Prompts are static artifacts swapped at session boundaries.

This is a sound design for today's models — and the isolation (no keys, single write path) is exactly right for an AI that might hallucinate or be prompt-injected.

#### F2. Gaps between current AI behavior and what a genuine edge requires

| Current behavior | Gap | Required evolution |
|---|---|---|
| One-shot proposals | No iteration: AI proposes, gets refused or filled, and learns nothing within the session | **Within-session closed loop**: AI sees gate verdict + fill + slippage and revises. Requires structured feedback channels (E-wiring items above) |
| Scalar conviction only | AI's actual uncertainty/reasoning is discarded at the contract boundary | Richer proposal schema: conviction + uncertainty + horizon + invalidation condition + reasoning trace |
| Static prompts per session | No learning between sessions beyond manual prompt edits | **Evidence-driven prompt evolution**: attribution data → analysis tool auto-drafts prompt amendments → A/B replay harness validates → version bump. Human still approves |
| Skill measured post-hoc (Wilson) | Feedback arrives too late to matter | Rolling skill metrics *fed into* the advisor context ("your last 20 directional calls on gap-days were negative") |
| AI analyzes on demand | No continuous awareness | Scheduled analysis jobs (jobs domain exists!) that wake the AI on events: regime shift, repeated refusals, drawdown threshold |
| Single strategy context | No desk-level reasoning | Multi-strategy context: the AI should reason about *which strategy deserves capital*, not just one signal |

#### F3. Designing now for future AI capability

The system must be built so that *better models become more valuable without architectural rework*:

1. **Graduated autonomy must be an architectural primitive, not a policy.** An `authority_level` bound to measurable performance (Wilson score thresholds, drawdown record) that unlocks: propose-only → propose-with-auto-pass-lower-gates → self-executing within caps. Design the gates to accept "advisory vs. binding" AI input now.
2. **Every AI action must be forensically reconstructible** — prompt version, context snapshot, tool calls, reasoning trace, resulting intent. Today's audit covers orders; tomorrow's needs model-decision audit. This also becomes your training/eval data.
3. **The narrow Intent funnel is both a shield and a ceiling.** Keep it as the money boundary, but add a parallel *advisory channel* through which future AI can express richer strategy logic (e.g., generating `library`-kind strategies) that humans review once and then run deterministically. AI writes code; code, not the AI, trades — this scales AI capability while preserving the safety model you've already proven.
4. **Multi-agent readiness**: domain servers are already split; add identity/scoping so multiple AI agents (analyst, risk-officer, executor roles) can hold distinct authorities. Today it's one Claude; tomorrow it's a team, and the current gateway has no notion of *which* AI is asking.
5. **Context economics**: 125 tools × growing tape will exceed any model's practical context. The research/analysis domain needs a summarization/indexing layer (daily digests, materialized views, semantic retrieval over the decision journal) so future AI spends context on decisions, not data plumbing.
6. **Adversarial robustness**: as AI gains autonomy, treat its inputs as attack surface — market data anomalies, injected text in analysis artifacts. Data validation gates should exist not just for freshness but for sanity (price spikes, chain anomalies).

---

### G. PRIORITIZED SYNTHESIS

**Tier 0 — without these, "AI edge" is unprovable:**
1. Fills→attribution→PnL pipeline (D5, E)
2. Shadow-mode continuous proposal track record (D2)
3. Execution state machine + broker reconciliation (B2, D1)
4. Structured gate-verdict traces as AI feedback (D4, E)

**Tier 1 — converts measurement into an edge:**
5. Prompt A/B replay harness (needs the replay engine, B5)
6. Authority ladder tied to skill scores (F3.1)
7. Automated circuit breakers + AI proposal budgets (B2)
8. Portfolio-level risk gate + `src/risk/` module (B1, C)

**Tier 2 — systemic desk scale-out:**
9. Event bus + supervisor wiring (B6, E)
10. Hot-path/AI-plane process isolation (B3)
11. Regime layer + richer advisory channel for AI-authored strategies (B4, F3.3)
12. Multi-agent identity/scoping and context-indexing layer (F3.4–5)

**One-line verdict:** the system has verified *containment* of AI risk end-to-end, but the loop that turns AI output into measured, compounding edge — attribution → evaluation → adaptation → graduated authority — is unwired. Build the loop first; everything else is scope.

----

