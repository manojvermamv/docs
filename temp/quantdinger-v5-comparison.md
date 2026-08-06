# QuantDinger v5 — Deep comparison with our control plane

**Date:** 2026-08-06 · **Source:** architecture diagrams (user-supplied) + source verification of
`OpenByteInc/QuantDinger` @ `e64e1c227bf3174e441a42143620179b286387e1` (main, HEAD today;
frontend repo `QuantDinger-Vue` not inspected). Every claim below marked diagram / code-verified.

---

## 1. What the diagrams actually contain, path by path

### Diagram A (9-sector architecture)

- **S1 Clients** — web app, mobile H5, REST "Human API", plus Cursor / Claude Code / Codex /
  custom agents / MCP clients. Two surfaces: a built UI (web+mobile) *and* an agent surface.
  → source-verified: `mcp_server/…/server.py` is a thin wrapper over the Agent Gateway.
- **S2 Data** — OHLCV/quotes/order books over stocks, crypto, forex, futures; broker APIs
  (Binance, OKX, Bybit, Bitget, Gate, HTX, IBKR, Alpaca); fundamentals + news + sentiment;
  user-supplied Python strategy code. **A data platform + strategy host, not a desk overlay.**
- **S3 API/Security** — Nginx → Flask+Gunicorn; validation/auth/contracts; then an **Agent
  Gateway** `/api/agent/v1` with an MCP-tool boundary; JWT/RBAC/token scopes/rate limits;
  audit trail + idempotency + **paper-by-default**. → verified: `agent_v1/__init__.py` exact
  blueprint mount; `quick_trade.py` paper-only default + hard-gated live.
- **S4 Core** — indicator/signal layer (user-supplied Python); **Strategy Runtime v2**
  (intents, sizing, risk guards, state, reconciliation — verified: `OrderIntentService`,
  `ProtectionSpec`, `StrategyV2LiveSession`, `alpaca_activity_reconciliation`); backtest engine
  (pinned inputs, metrics, equity curves, reproducible runs — verified: `engineVersion`
  pin, `equityCurve` persistence); AI analysis/generation (multi-provider LLMs — verified:
  OpenRouter/OpenAI/Gemini/DeepSeek/Grok/AtlasCloud/MiniMax + LiteLLM); portfolios + billing.
- **S5 Execution** — paper OR live; **explicit promotion + operator opt-in** (verified: dual
  gate — token `paper_only=false` AND server env `AGENT_LIVE_TRADING_ENABLED=true`); order
  limits / kill switches / reconciliation; venue execution; alerts (Telegram/email/SMS/
  Discord/webhooks); operator UX (dashboards, snapshots, strategy health.
- **S6 Process plane** — migration, trading worker, scheduler worker, Celery, Beat. Verified:
  `migrate.py` (fail-fast), `trading_worker.py` (lease owner), `scheduler.py` (PG leader
  election), `celery_app.py` beat schedule, `qd_worker_heartbeats` health table.
- **S7 Observability** — JSON logs, request IDs, metrics → Prometheus/Grafana/Alertmanager.
- **S8 Foundation** — PostgreSQL 18 system of record, Redis cache (disposable) + Redis jobs
  (durable), secret/credential encryption, Docker Compose/GHCR, Python 3.12, CI gates.
- **S9 Closed loop** — Research → Build → Backtest → Validate → Promote → Execute → Monitor →
  Feedback. **Partial claim:** docs show a 5-stage loop ("AI research → strategy code →
  backtest → paper/live → monitoring"); the 8-stage phrasing is the diagram's, not the repo's.

### Diagram B2 (data/control flow)

- Clients → nginx → Flask API → **PostgreSQL (system of record)** + Redis cache + durable
  Redis job queues.
- Workers lease work from PG (`claim_next(owner_id, lease_seconds)`, `renew_process_lease`,
  heartbeats); Celery Beat enqueues to Celery. API also writes **durable commands** to PG —
  commands survive restarts. Every layer (API, PG, cache, jobs) exports metrics to
  Prometheus → Grafana + Alertmanager.

---

## 2. Deep comparison, axis by axis

| Axis | QuantDinger v5 | Our control plane | Verdict |
|---|---|---|---|
| **Client surface** | Web + mobile H5 + REST + MCP (all MCP-branded agents) | MCP only (any client via stdio or HTTPS+OAuth) | QD wins breadth; we win nothing here |
| **UI panel** | Dashboards, snapshots, strategy health, billing UI | **None** — MCP tools only | Our biggest gap |
| **Data scope** | Crypto+stocks+Fx+futures, 8 broker/exchange APIs, fundamentals,news,sentiment | One desk: NSE options, single OpenAlgo row, recorder captures | Different scope, both fit for purpose |
| **AI surface** | Serially multi-provider LLMs, skills, reviews, reports inside platform | No LLM inside gateway; client-side (Claude/ChatGPT) | Architectural choice, not an advantage either way; ours = not holding tokens |
| **Order runtime** | Strategy runtime v2 (intents, sizing, guards, state, reconciliation, spot/derivatives) | No order runtime — **read:market permanently** (rung 4 dropped) | Constraint vs breadth; by design |
| **Backtest engine** | StrategyV2BacktestRunner, engineVersion pin, equity curve storage, **OOS 70/30 split**, PIT data | Sim, replay tape, sweep jobs; **no OOS holdout**, no version-pinned backtests | QD wins; OOS is on our roadmap |
| **Evidence gating** | Advisory only — `sample_small` diagnostic **<5 trades**, recommend "5.0-20 trades"; **no hard refusal, no significance test** | **Hard gate:** <30 trades → statistical claim refused; mechanical-cited-mechanism alternative; out-of-sample checks. Source — register | **We are ahead; verified their gate is advisory** |
| **Risk guards** | Risk guards on intents = live-order risk; paper default; kill switch — `AGENT_LIVE_TRADING_ENABLED` | Risk Guard — hard caps, fail-closed, kill switch, approval-only orders | Parity; we fail closed on config, they on scope |
| **Audit / commands** | Audit trail + **idempotency keys** + durable paper-gated | Full audit trail (identity per call, off-box sink) + fail-closed, no idempotency needed (no writes/money) | Parity, different due to read-only scope |
| **Observability** | JSON logs + **request IDs** + Prometheus/Grafana/Alertmanager per-received exporters | at doctor / drift canary / audit sink; **no metrics stack, no request-ID correlation** | QD wins clearly; this is our #2 gap |
| **Workers / queues** | PG-ledged workers with leases/heartbeats + Celery, durable Redis jobs | Jobs queue (allowlist, 3 backends, idempotent-enqueue), in-process scheduler, drift-canary   | Parity in class, QD finer granularity |
| **Storage** | PostgreSQL SoR (operational), Redis (cache/jobs) | Parquet + DuckDB warehouse (analytics), append-only files+audit (design), recorder | Different choices, both deliberate |
| **Multi-tenant / billing** | credits, membership, USDT payment watch-ers | Single desk, no multi-tenant | Out of scope by design |
| **Deployment** | Docker Compose + GHCR, Python 3.12, self-hosted | systemd/launchd/pidfile, single script, atomic deploys | Parity |

---

## 3. Honest verdict

**What we are not "beating":** as a *platform*, QuantDinger v5 is broader: UI+panel, turn-key
backtest engine with out-of-sample check, multi-provider LLM, working plane with leases, and
their agent-gateway had a true operator opt-in + real model-free architecture with paper
default + reconciliation across venues.

**The one axis where the verified record favors ours:** **hard statistical evidence gating.
QuantDinger's gate is advisory (<5 trades diagnostic, "treat conclusions as directional") and
not a refusal; **no significance tests exist.** Ours refuses the claim entirely above a
30-trade bar and requires cited mechanism to pass. That is the difference between "the AI can
write a proposal" and "the AI cannot get a proposal through without measured proof." Source
(from-wave-1: Jesse's <30-trades rule matches our bar).

**Correction to my earlier claim.** "they don't combine X+Y+Z" was right but read as "we beat
them everywhere" — this deep-dive shows operators (dashboard, alerting, backtest pins/OOS,
request IDs, idempotency) where they are ahead and we should absorb, not dismiss.

---

## 4. Adoption proposals (respecting read:market-only on the broker)

1. **Out-of-sample holdout** — QD's `_out_of_sample()` 70/30 split + separate-halo split. We
   list "out-of-sample holdout" on the roadmap; their pattern (point-in-time only, confirm
   on close / fill next open) is a concrete starting weight for our replay harness. *No money
   gates touched.*
2. **Request-ID correlation + health alerting** — structured logs + `request-id` correlation
   + a minimal Prometheus/Alertmanager-style threshold surface for the desk (they ship it; we
   list "not to health alerting" as a not-code-do-first). *Additive only.*
3. **Backtest reproducibility pin** — their `engineVersion` + `execution_count` on every
   backtest result; ours stamps warehouse answers with build time; backtest runs should carry
   code + data version and an equity curve hash. *Pure reporting, no gates.*
4. **Idempotency keys on job enqueue** — their intent service keeps the idempotency key; our
   job queue is allowlisted and registered (same). Worth copy only if a job retry can double:
   proposal.
5. **Advisory sample-size diagnostics** (not a replacement for our hard gate — a rich
   supplement): QD's `sample_small` at <5 / "target 10-20" is weak next to our ≥30, but the
   cap-expansion caution (`reduce_risk_until_retested`) is a nice research-domain output.
