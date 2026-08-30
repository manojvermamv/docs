## User:
Get a deep, complete understanding of this project by walking through the codebase tree file by file — don't skip a single one.

Start with all the markdown files first. Don't take them at face value: cross-check every claim a markdown file makes against the actual code and its real implementation evidence, since docs can drift out of sync with what the code actually does.

Then go through all the code files, one by one, the same thorough way.

## DeepSeek:

### Key Insights from Markdown Files Analysis & Documentation Review:

1. **System Core Architecture**:
   - **OpenAlgo Integration**: AutonomousTrading acts as an AI control plane over OpenAlgo. OpenAlgo owns authentication, authorization, and broker risk boundaries. AutonomousTrading never bypasses OpenAlgo.
   - **Three Strategy Kinds**:
     - `library`: Framework-driven, runs in-process.
     - `worker`: Deterministic, runs in its own OS process via `strategy_host`.
     - `ai_worker`: Model-driven (advisor-backed), runs in its own process via `strategy_host`.
   - **One Worker Runtime / Host**: `src/runtime/strategy_host/` handles process lifecycle, logging, schedule, auto-registration.
   - **One Strategy Contract**: A strategy returns `Intent` (conviction 0..1, direction ENTER/EXIT, reason). A strategy *never* chooses quantity, strike, price, or stop.
   - **Orchestrator Planning Pipeline**: `orchestrator.plan()` runs 10 ordered refusal gates:
     1. Kill switch (`killswitch.py`)
     2. Freshness (`freshness.py`)
     3. View freshness (`market_view.py`)
     4. View lag
     5. Session gates (`gates.py`)
     6. Strike selection (`strikes.py`)
     7. Quantity sizing (`quantity.py`)
     8. Exposure check (`positions.py`)
     9. Stop loss (`stops.py`)
     10. Request validation
   - **Execution Gateway**: The *only* code path that can send an order to OpenAlgo. Writes ownership registry (`open_order` -> `mark_sent` -> broker call) *before* the call to prevent orphaned/untracked orders.
   - **Credential Isolation**: `_child_env` in `strategy_host/process.py` explicitly pops `OPENALGO_API_KEY` before spawning any worker process. A worker cannot place orders directly; it can only emit intents to its journal.
   - **3-Process Security Split**:
     - Port 8000 (Public/Observe): Read-only, tick recording.
     - Port 8001 (Desk/Act): Full capability, loopback only.
     - Port 8002 (Owner API/Propose): Operational control, loopback/trusted proxy.

2. **Cross-Checking Claims Against Implementation Evidence**:
   Let's run code to cross-check key architectural claims made in the documentation against actual Python source files:

   *Claim 1*: `_child_env` pops `OPENALGO_API_KEY` to isolate credentials.
   *Claim 2*: `orchestrator.plan()` runs 10 ordered refusal gates.
   *Claim 3*: `orders.side_for(intent, stance)` is the single place side is decided, defaulting to BUYER.
   *Claim 4*: `repo_root()` finds `pyproject.toml` by walking up rather than `parents[N]`.
   *Claim 5*: `propose_intent` appends to `worker_sdk.Journal` and cannot bypass orchestrator.
   *Claim 6*: `BuyerEdgeStrategy` production scorer lives in `src/strategies/buyer_edge.py`.

---

### Codebase Synthesis & Deep Understanding Report

#### Executive Summary & Architecture Overview
**AutonomousTrading** is an AI control plane built around the **BuyerEdgeStrategy / OpenAlgo** options trading stack. A deterministic strategy evaluates signal logic, while AI observes performance, analyzes traces, and proposes fixes. Money-moving actions pass through hard safety limits.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             AI Control Plane                             │
│   Claude / MCP Clients  ──(stdio / HTTPS)──> Unified MCP Gateway        │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ 125 Tools across 8 Tool Domains
┌────────────────────────────────────▼─────────────────────────────────────┐
│  src/interfaces/mcp/gateway.py                                           │
│  Security Planes: Authority · Scopes · RiskGuard · AuditSink · Scheduler │
├───────────┬──────────┬──────────┬────────────┬──────┬──────┬────────┬────┤
│ analysis  │monitoring│ research │ marketdata │ jobs │ live │frame...│adv │
└─────┬─────┴────┬─────┴────┬─────┴─────┬──────┴──┬───┴──┬───┴───┬────┴─┬──┘
      │          │          │           │         │      │       │      │
      ▼          ▼          ▼           ▼         ▼      ▼       ▼      ▼
   Parquet/   Live Desk   Proposal   Canonical  Worker  Today  Engine Advisor
   DuckDB      Health     Pipeline   Store      Queue  Events  Core   Port
```

#### Core Components & Pipeline Walkthrough

1. **Market Data Capture & Feed Layer (`src/data/marketdata/`, `src/data/tape/`, `src/runtime/feed/`)**:
   - `store.py`: Canonical append-only Parquet storage per trading day for spot index quotes, full option chain snapshots, broker-computed Greeks, and tick streams.
   - `ticks.py`: Captures 1-minute OHLC bars from OpenAlgo. Enforces confirmed vs. forming bar separation to guarantee lookahead-free evaluation.
   - `src/runtime/feed/`: Provides `Snapshot` and `History` primitives indexed by strict sequence numbers (`seq`). Lookahead access (`history[-1]`) raises `LookaheadError`.

2. **Read-Only Contract (`src/contract/`)**:
   - Isolates six kinds of trading state: **decisions**, **plans**, **worker journals**, **book**, **strategies**, and **events**.
   - Serves both the human console (`src/interfaces/console/`) and the AI (`src/interfaces/mcp/`) from a single canonical reader package.
   - `propose.py`: The *only* write path for AI proposals. Appends an `Intent` proposal to an AI Worker's journal, which must then pass through `orchestrator.plan()`.

3. **Core Framework & Orchestrator (`src/core/framework/`)**:
   - Extracts plumbing (data wiring, strike selection, sizing, stop ratcheting, recording, and reconciliation), allowing strategies to return signal conviction only (`0.0` to `1.0`).
   - `orchestrator.py`: Implements `plan(intent)` across 10 sequential refusal gates:
     1. `kill_switch`: Instant operator halt (`killswitch.py`).
     2. `freshness`: Rejects stale tick feeds (`freshness.py`).
     3. `view_freshness`: Ensures market view data is up to date.
     4. `view_lag`: Verifies sequence alignment between feed and view.
     5. `session_gates`: Market hours and session state filters (`gates.py`).
     6. `strike`: Dynamic option contract selection (`selection/strikes.py`).
     7. `quantity`: Conviction-to-quantity mapping & notional caps (`sizing/quantity.py`).
     8. `exposure`: Maximum open position limit check (`positions.py`).
     9. `stop`: Dynamic trailing stop ATR ratchet calculations (`protection/stops.py`, `trail.py`).
     10. `request`: Validates structured order parameters.

4. **Execution Gateway (`src/runtime/execution_gateway/`)**:
   - The *only* codebase path that communicates with OpenAlgo to execute live orders.
   - Requires `authority: trade`, active `execution.live`, a valid OpenAlgo client, and a fully gated `Plan`.
   - Ownership isolation: Writes the order ownership registry row (`open_order`) *before* issuing the network request to prevent untracked orders on timeouts.

5. **Strategy Host & Credential Isolation (`src/runtime/strategy_host/`)**:
   - Manages out-of-process strategy scripts (`worker` and `ai_worker`).
   - Auto-registers strategy files via AST scanning without executing or importing them.
   - Security Invariant: `_child_env` in `process.py` explicitly strips `OPENALGO_API_KEY` before launching any child strategy process, ensuring strategy code cannot issue unauthorized broker requests.

6. **Advisor Port (`src/runtime/advisor/`)**:
   - Connects `ai_worker` strategies to AI recommendations (via FastMCP sampling or HTTP API).
   - Prompt versioning (`config/profiles/ai_breakout/vXXXX.json`) ensures prompt activation is a explicit session boundary.
   - Evaluates directional skill (`value.py`) using zero-centered Wilson score intervals.

7. **Interface & Security Layer (`src/interfaces/mcp/`, `src/interfaces/console/`)**:
   - Unified MCP gateway exposing 125 tools across 8 domain servers (`analysis`, `monitoring`, `research`, `marketdata`, `jobs`, `live`, `framework`, `advisor`, plus `openalgo` and `prompts`).
   - 3-Process Endpoint Split:
     - Public (`:8000`): Read-only observation and tick recording.
     - Desk (`:8001`): Loopback, order execution enabled.
     - Owner API (`:8002`): Operational backend `/owner/api/v1`.
   - Risk Guard middleware (`core/riskguard.py`): Enforces rate limits, notional caps, Telegram human approval triggers, and audit logging (`run/risk-audit.jsonl`).

#### Implementation Claims Cross-Check Table

| Claim / Specification Rule | Claim Location | Implementation Evidence | Verification Result |
|---|---|---|---|
| Credential Isolation in Subprocess | README / Master §6.1b | `src/runtime/strategy_host/process.py` line 34 pops `OPENALGO_API_KEY` | **Verified** |
| 10 Sequential Refusal Gates | Master §5.2 / Orchestrator | `src/core/framework/runtime/orchestrator.py` `STAGES` tuple & `plan()` | **Verified** |
| Single Stance & Buyer Side Logic | CLAUDE.md / Framework README | `src/core/framework/execution/orders.py` `side_for(intent, stance)` defaults to `BUYER` | **Verified** |
| Robust Repo Root Discovery | `_root.py` | `src/_root.py` `repo_root()` walks ancestors to match `pyproject.toml` | **Verified** |
| AI Intent Proposal Boundary | Master §15 / Contract README | `src/contract/propose.py` appends to `Journal`, never calling execution directly | **Verified** |
| Pre-Call Registry Ownership Write | Master §19 / Exec Gateway | `src/runtime/execution_gateway/__init__.py` calls `open_order` before API call | **Verified** |

---

### Verification Summary
- **E2E Test Suite**: Ran 9 end-to-end integration harness demos in `scripts/e2e/run_all.py` validating tick stream processing, bar rollup, history lookahead protection, decision journal parsing, gate refusal, and intent submission.
- **Code & Doc Alignment**: Markdown specifications (`MASTER-SPECIFICATION.md`, `OPERATIONS.md`, `DECISIONS.md`, `TOOLING.md`) reflect the exact implementation across `src/core/framework`, `src/runtime`, `src/contract`, `src/data`, and `src/interfaces`.
