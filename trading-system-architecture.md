# Trading System Architecture

## 1. System Overview

Two dedicated servers power the trading infrastructure:

| Server | IP | Role | OS |
| Ubuntu Control Panel | 98.85.232.152 | Management, AI agents, strategy development | Ubuntu |
| Debian OpenAlgo Production | 100.52.17.180 | Trading platform, broker connectivity, strategy execution | Debian |

The vision is a fully automated MCP-based AI trading system where an AI agent reads market data, analyzes strategy logs, generates signals, and places orders -- all through MCP tool calls. The Ubuntu server hosts the AI orchestration layer (OpenCode, Hermes AI, local analysis tools), while the Debian server runs the production trading platform (OpenAlgo) with live broker connections and strategy execution.

```
                          +-----------------------------+
                          |   Ubuntu Control Panel      |
                          |   98.85.232.152             |
                          |                             |
                          |  +-----+  +----------+     |
                          |  | MCP |  | OpenCode  |     |
                          |  | Log |  | CLI Agent |     |
                          |  | Ana |  +----------+     |
                          |  +-----+       |            |
                          |       |        | SSH        |
                          +-------+--------+------------+
                                  |        |
                                  | SSH    |
                                  v        v
                          +-----------------------------+
                          |   Debian OpenAlgo Prod      |
                          |   100.52.17.180             |
                          |                             |
                          |  +-----------+  +---------+ |
                          |  | OpenAlgo  |  | WebSocket| |
                          |  | Flask App |  | Proxy    | |
                          |  | (port 5000)| |(port 8765)| |
                          |  +-----------+  +---------+ |
                          |       |            |         |
                          |  +----------+              |
                          |  | Strategy  |              |
                          |  | Subprocess|              |
                          |  +----------+              |
                          +-----------------------------+
                                     |
                                     v
                          +-----------------------------+
                          |  34 Broker APIs             |
                          |  (Zerodha, Angel, Dhan,     |
                          |   Upstox, FYERS, Groww...)  |
                          +-----------------------------+
                                     |
                                     v
                               [Exchange]
```

---

## 2. Server Infrastructure

### Ubuntu Server (98.85.232.152) -- Control Panel

- **OS:** Ubuntu, root access via SSH
- **Coolify:** Container management platform with web UI at port 8000. Manages application containers, databases, and deployment pipelines.
- **Hermes AI:** NousResearch agent with web UI running inside Coolify. Has Docker socket access for container lifecycle management. OpenCode CLI is bind-mounted into the container for AI-assisted coding. nsenter provides host root access from within the container.
- **OpenCode:** AI agent with root-level host access (via nsenter). Workspace at `/home/ubuntu/` with skills and MCP servers configured. Operates with direct Docker socket and host namespace access -- effectively root-equivalent on the real host.
- **Local strategy workspace:** `/home/ubuntu/OA/strategies/` -- source code, tools, logs, and analysis for the BuyerEdgeStrategy.
- **Docs repository:** `/home/ubuntu/docs/` -- infrastructure documentation, SSH keys, architecture references.

### Debian Server (100.52.17.180) -- OpenAlgo Production

- **OS:** Debian
- **OpenAlgo:** Flask + React 19 trading platform. The core application that connects to brokers, executes orders, manages strategies, and exposes APIs.
- **Running services:**
  - Flask app on port 5000 (REST API + web UI)
  - WebSocket proxy on port 8765 (real-time market data streaming)
  - ZeroMQ bus on port 5555 (inter-service messaging)
- **Docker:** Single container named `openalgo-web` with named volumes for persistent data (databases, configs, logs).
- **BuyerEdgeStrategy.py:** Running in production as a Python Strategy Host subprocess, spawned and managed by OpenAlgo's APScheduler.
- **34 broker plugins configured:** zerodha, angel, dhan, upstox, fivepaisa, aliceblue, flattrade, shoonya, fyers, groww, kotak, mstock, pocketful, deltaexchange, and more.

### SSH Access

Two key pairs control server access:

| Key | Server | User |
| UbuntuPairKey.pem | 98.85.232.152 | root |
| DebianPairKey.pem | 100.52.17.180 | admin |

Keys are stored at `/home/ubuntu/docs/keys/` (directory is gitignored).

**Commands:**

```bash
# Ubuntu Control Panel
ssh -i /home/ubuntu/docs/keys/UbuntuPairKey.pem root@98.85.232.152

# Debian OpenAlgo Production
ssh -i /home/ubuntu/docs/keys/DebianPairKey.pem admin@100.52.17.180
```

---

## 3. OpenAlgo Platform Architecture

### Four Products in One

OpenAlgo is not a single application -- it is four integrated products sharing the same backend:

1. **Unified Broker API** (`/api/v1/`) -- REST endpoints for orders, positions, portfolio, market data, options, GTT, and account management across 34 brokers.
2. **Python Strategy Host** (`/python`) -- browser-based CodeMirror editor to write, upload, and schedule Python strategies on IST cron. Strategies run as isolated subprocesses.
3. **Flow No-Code Builder** (`/flow`) -- visual drag-and-drop strategy builder for non-programmers.
4. **Options Trading Suite** (`/tools`) -- options-specific tooling: chain viewer, Greeks calculator, strategy builder.

### Backend Stack

Flask application served through Gunicorn with eventlet workers (`-w 1`). Three real-time communication channels:

- **SocketIO** -- browser UI updates (order confirmations, position changes)
- **ZeroMQ** -- inter-service message bus (port 5555)
- **APScheduler** -- cron-based strategy scheduling with exchange-aware market-hours gating

### Database Layer

Six databases serve different concerns:

| Database | Purpose |
| openalgo.db | Core application state: orders, trades, positions, users, broker configs |
| logs.db | Strategy execution logs, system events |
| latency.db | Order-to-fill latency measurements, API response times |
| health.db | System health checks, uptime tracking |
| sandbox.db | Paper trading sandbox -- isolated broker environment for testing |
| historify.duckdb | Historical market data storage (DuckDB columnar format) |

### REST API -- 57 Endpoints at /api/v1/

| Category | Endpoints | Key Examples |
| Orders | 10 | placeorder, placesmartorder, basketorder, splitorder, optionsorder |
| Positions | 2 | closeposition, openposition |
| Portfolio | 6 | orderbook, tradebook, positionbook, holdings, funds, margin |
| Market Data | 4 | quotes, multiquotes, depth, history |
| Options | 5 | optionchain, optionsymbol, optiongreeks, multioptiongreeks, syntheticfuture |
| Search | 5 | symbol, search, expiry, intervals, instruments |
| GTT | 4 | placegttorder, modifygttorder, cancelgttorder, gttorderbook |
| Account | 3 | ping, pnl/symbols, analyzer |
| Notifications | 8 | telegram/*, whatsapp/notify |

### MCP Integration -- 32 Tools in mcp/mcpserver.py (2,187 Lines)

Two transport modes available:

1. **Stdio (local):** `python -m mcp.mcpserver <api_key> <host>` -- for Claude Desktop, Cursor, and local AI agents.
2. **HTTP/SSE (remote):** POST `/mcp` + GET `/mcp` with OAuth 2.1 -- for ChatGPT, Claude.ai, and cloud-based AI agents.

| Category | Count | Examples |
| Order Management | 9 | place_order, place_smart_order, place_basket_order, modify_order, cancel_order |
| Position Management | 2 | close_all_positions, get_open_position |
| Order Tracking | 6 | get_order_status, get_order_book, get_trade_book, get_funds |
| Market Data | 5 | get_quote, get_multi_quotes, get_option_chain, get_historical_data |
| Instruments | 9 | search_instruments, get_expiry_dates, get_option_greeks |
| Technical Analysis | 10 | calculate_indicator (80+ TA functions), get_trend_snapshot, detect_signals |
| Utilities | 6 | get_holidays, get_timings, analyzer_toggle, send_telegram_alert |

### Order Execution Pipeline

```
AI Agent / MCP Client
  -> mcp/mcpserver.py (@mcp.tool functions)
    -> openalgo SDK client
      -> POST /api/v1/placeorder
        -> services/place_order_service.py
          -> validate -> auth -> route (sandbox/live) -> broker module
            -> broker/{name}/api/order_api.py
              -> Broker REST API -> Exchange
```

Each stage adds validation, authorization, sandbox routing, broker-specific transformation, and error handling before the order reaches the exchange.

### Broker Plugin Architecture

34 brokers are supported through a plugin architecture. Each broker module contains:

| File | Purpose |
| api/order_api.py | Place, smart, modify, cancel order functions |
| api/auth_api.py | Authentication and session management |
| api/data.py | Historical and real-time market data fetching |
| mapping/transform_data.py | Broker-specific data format transformations |
| streaming/{broker}_adapter.py | WebSocket adapter for real-time tick streaming |

Broker modules are loaded dynamically at runtime:

```python
importlib.import_module(f"broker.{broker_name}.api.order_api")
```

### WebSocket Proxy (Port 8765)

The WebSocket proxy provides real-time market data streaming:

**Connection flow:**
1. Client connects to WS proxy (port 8765)
2. Client authenticates with `api_key`
3. Client subscribes with action: `subscribe` (symbols, mode: LTP/Quote/Depth)
4. Client receives streaming ticks

**Data pipeline:**
```
Broker WebSocket -> adapter -> ZeroMQ PUB (5555) -> WS Proxy SUB -> Client WS (8765)
```

**Order updates** are delivered via the `subscribe_orders` action.

**Connection pooling:** 3 connections x 1,000 symbols = 3,000 symbols maximum across all active connections.

### Python Strategy Host (/python)

The strategy host lets users run Python scripts directly on the server:

1. Write strategy code in the browser CodeMirror editor
2. Upload the script to the server
3. Schedule execution on IST cron with exchange-aware market-hours gating

**Process isolation:** Each strategy runs as a `subprocess.Popen`, preventing one strategy from crashing another.

**Environment variables injected into each subprocess:**
- `OPENALGO_API_KEY` -- authentication for API calls
- `HOST_SERVER` -- the OpenAlgo server address
- `STRATEGY_ID` -- unique identifier for the strategy instance
- `STRATEGY_EXCHANGE` -- target exchange for market-hours gating

**Live logs** are streamed via Server-Sent Events (SSE) to the browser UI.

### Event System

An internal EventBus dispatches typed events throughout the platform:

| Event | Subscribers |
| OrderPlacedEvent | SocketIO (UI), Telegram, log tables |
| OrderFailedEvent | SocketIO (UI), Telegram, log tables |
| (Additional events follow the same dispatch pattern) |

---

## 4. BuyerEdgeStrategy -- The Options Buyer

### Overview

- **File:** `/home/ubuntu/OA/strategies/examples/BuyerEdgeStrategy.py` (9,305 lines)
- **Production status:** Running on the Debian server as a Python Strategy Host subprocess, scheduled via APScheduler with IST market-hours gating.
- **GitHub auto-sync:** A systemd service with inotifywait pushes changes to the `manojvermamv/docs` repository automatically.

### V2 Architecture

The strategy is structured around 9 sub-configurations and 6 position state sub-objects:

**Configuration classes:**
| Config | Purpose |
| EntryConfig | Entry trigger conditions, thresholds, and signal requirements |
| TrailConfig | Trailing stop-loss parameters and adjustment logic |
| RiskConfig | Per-trade and session risk limits, max exposure |
| SignalConfig | Signal scoring weights and minimum confidence thresholds |
| ExecutionConfig | Order type, exchange routing, execution timing |
| ExitConfig | Profit target, stop-loss, time-based exit rules |
| LoggingConfig | Log verbosity, detail level, output targets |
| SessionConfig | Trading session start/end times, market hours |
| StrikeConfig | Strike selection logic, ATM/OTM/ITM filters |

**Position management:** 6 position state objects stored in a `PositionBook` with slot-keyed storage. Each slot holds the full lifecycle of a single trade from entry to exit.

**Concurrency model:** `state_lock` -> `exit_lock` using nested locking. This prevents race conditions between signal evaluation, stop-loss updates, and exit decisions while ensuring no deadlocks from lock-order inversion.

### 5-Layer Signal Scoring

Signals are generated by scoring across five independent analysis layers. Each layer produces a sub-score that is weighted and combined into a composite signal.

| Layer | What It Analyzes |
| Technical | Price action, momentum, trend direction and strength |
| OI Flow | Open interest changes, put/call OI ratio shifts |
| Greeks | Delta, gamma, theta exposure and risk metrics |
| Straddle/IV | Implied volatility levels, straddle premium pricing |
| Synthetic Futures | Synthetic future premium vs spot price divergence |

### Trailing SL Engine

Four trailing methodologies run simultaneously, each adjusting the stop-loss based on different inputs:

1. **ATR-based trailing** -- average true range determines stop distance
2. **Fixed-point trailing** -- absolute price level increments
3. **Delta-based trailing** -- option delta determines stop sensitivity
4. **Key-level-based trailing** -- support/resistance levels as stop references

A **signal-aware trail** adjusts the trailing aggressiveness based on the composite signal direction and strength. When the signal weakens, trailing tightens. When it strengthens, trailing loosens to let winners run.

A **tranche partial-exit framework** allows scaling out of positions in stages rather than a single exit, locking in profits while maintaining exposure.

### Risk Controls

| Control | Behavior |
| Circuit breaker | Halts all new entries when triggered. Resets after configured cooldown or manual intervention. |
| Drawdown limits | Soft and hard drawdown limits at both per-trade and session level. Soft triggers warning, hard triggers shutdown. |
| Streak tracking | Consecutive wins/losses are tracked. Streak-based adjustments modify position sizing. |
| Per-trade risk caps | Maximum loss per trade, configurable in absolute and percentage terms. |
| Session-level risk caps | Maximum total loss per trading session. |
| Kill switch | Emergency stop that closes all positions and prevents new entries. Can be triggered remotely. |

### Audit History

The strategy has undergone extensive auditing:

- 60+ audit findings closed (F1-F64, F71-F77) -- covering logic errors, edge cases, performance bottlenecks, risk gaps
- Deep audit protocol documented in `/home/ubuntu/OA/strategies/docs/protocols/`
- Log analysis: 24 raw log session files analyzed, producing 7 analysis reports

---

## 5. Local Development Workspace

### Directory Structure

```
/home/ubuntu/OA/strategies/
├── examples/
│   ├── BuyerEdgeStrategy.py          # 9,305 lines, V2 architecture
│   └── tests/                        # Test scripts
├── tools/
│   ├── mcp/
│   │   ├── server.py                 # V3 MCP server -- 32 tools (log analysis)
│   │   └── client.py                 # Test client
│   ├── core/                         # log_core.py, patterns.py
│   ├── signals/                      # s3_signals, confluence, signal_accuracy
│   ├── trades/                       # entries, exits, trail_analysis, mfe_analysis
│   ├── execution/                    # fills, slippage, order_lifecycle
│   ├── risk/                         # streaks, drawdown, circuit_breaker
│   ├── kpis/                         # summary, per_trade, ratios
│   ├── analysis/                     # time, symbol, options_metrics, risk_adjusted, journal_export
│   └── cli/                          # scan, kpis, report
└── docs/
    ├── logs_raw/                     # 24 raw log session files
    ├── logs_analysis/                # 7 analysis reports
    └── protocols/                    # audit, deep audit, log analysis protocols
```

### Tools Framework (20+ Modules)

The tools framework is a collection of Python modules for analyzing strategy logs and extracting actionable insights:

| Package | Modules | Purpose |
| signals/ | s3_signals, confluence, signal_accuracy | Signal extraction from logs and multi-timeframe confluence analysis |
| trades/ | entries, exits, trail_analysis, mfe_analysis | Trade lifecycle analysis from entry to exit, max favorable excursion |
| execution/ | fills, slippage, order_lifecycle | Order execution quality metrics -- fill rates, slippage analysis |
| risk/ | streaks, drawdown, circuit_breaker | Risk management metrics and streak/drawdown tracking |
| kpis/ | summary, per_trade, ratios | Performance dashboards, per-trade P&L, win/loss ratios |
| analysis/ | time, symbol, options_metrics, risk_adjusted, journal_export | Deep analysis by time bucket, symbol, options-specific metrics |

### MCP Evolution (3 Iterations)

The local MCP server for log analysis has evolved through three versions:

| Version | File | Lines | Tools | Architecture |
| V2 standalone | tools/mcp_server.py | 531 | 13 | Flat imports, single file |
| Package refactoring | tools/mcp/server.py (restructured) | - | - | Modular: core/, signals/, trades/, execution/, risk/, kpis/, analysis/ |
| V3 production | tools/mcp/server.py (current) | 170 | 32 | Clean package imports, organized tool registry |

### Critical Finding

The local MCP server is log-analysis only. It has zero tools for live trading, order placement, strategy control, or broker interaction. It reads historical log files and produces analysis reports. All live trading capability lives on the OpenAlgo MCP server on the Debian machine.

---

## 6. MCP Integration -- Current State vs. Vision

### Current State -- Two Separate MCP Servers

| Dimension | OpenAlgo MCP (Debian) | Local MCP (Ubuntu) |
| Location | /home/ubuntu/openalgo/mcp/mcpserver.py | /home/ubuntu/OA/strategies/tools/mcp/server.py |
| Tools | 32 (orders, positions, market data, indicators) | 32 (log scan, trade KPIs, risk summary, signals) |
| Transport | Stdio + HTTP/SSE (OAuth 2.1) | Stdio only |
| Purpose | Live trading via broker | Log analysis of past sessions |
| Status | Production-ready | Production-ready |
| Integration | Calls OpenAlgo REST API | Standalone, no platform integration |

Right now, a human sits between the two systems. The analysis results from the local MCP must be manually fed into decisions that the OpenAlgo MCP executes. There is no automated bridge.

### The Vision -- Bridging the Gap

```
Current: Two disconnected systems
  [Local MCP: log analysis] <--> [Human] <--> [OpenAlgo MCP: trading]

Target: Unified AI trading pipeline
  [AI Agent] -> [Unified MCP] -> [Analysis + Trading] -> [Broker -> Exchange]
                ^              ^
           Local tools    OpenAlgo platform
           (signals,      (orders, positions,
            risk, KPIs)    market data)
```

### What Needs to Be Built

1. **Unified MCP server** -- Combines all 32 log analysis tools from the local MCP with all 32 trading tools from the OpenAlgo MCP into a single MCP server. A single AI agent can then call both analysis and trading tools in the same session.

2. **Strategy control tools** -- MCP tools to start, stop, pause, and reconfigure the BuyerEdgeStrategy remotely. Currently requires manual SSH or web UI interaction.

3. **Real-time monitoring tools** -- MCP resources and tools for live position feeds, P&L streams, and strategy health checks. Currently limited to WebSocket proxy (port 8765) without MCP integration.

4. **AI agent pipeline** -- An automated pipeline where the AI agent reads logs, runs analysis, generates signals, and places orders in a continuous loop. Requires the unified MCP server as the foundation.

5. **Autonomous trading agent** -- The end state: an AI agent that acts as a trading desk, with built-in risk management, performance tracking, and adaptive parameter tuning.

---

## 7. Automation & DevOps

### GitHub Auto-Sync

A systemd service combined with inotifywait provides automatic version control for the production strategy:

- **Mechanism:** systemd service triggers on file changes, with a 60-second debounce to prevent rapid-fire commits on frequent saves.
- **Watched path:** `/home/ubuntu/OA/strategies/examples/BuyerEdgeStrategy.py`
- **Target repository:** `manojvermamv/docs`
- **Purpose:** Version control and backup of the production strategy. Every change to BuyerEdgeStrategy.py is automatically committed and pushed.

### Log Download Workflow

Logs are downloaded from the Debian production server to the local analysis workspace:

```bash
# Step 1: List log files on Debian server, get the most recent
ssh -i /home/ubuntu/docs/keys/DebianPairKey.pem admin@100.52.17.180 \
  "ls -t ~/openalgo/logs/Logs-*.txt | head -1" \
  | xargs -I{} scp -i /home/ubuntu/docs/keys/DebianPairKey.pem \
    admin@100.52.17.180:~/openalgo/logs/{} \
    /home/ubuntu/OA/strategies/docs/logs_raw/
```

**Naming convention:** `Logs-{DDMMMYYYY}.txt` (e.g., `Logs-21JUL2026.txt`). When the strategy process restarts multiple times in a single day, version suffixes are appended: `Logs-21JUL2026-1.txt`, `Logs-21JUL2026-2.txt`, etc.

### Deployment Procedure

When updating the production strategy:

1. Edit `BuyerEdgeStrategy.py` in the local workspace at `/home/ubuntu/OA/strategies/examples/`
2. GitHub auto-sync pushes the change to `manojvermamv/docs` (automatic backup)
3. SSH to the Debian server: `ssh -i /home/ubuntu/docs/keys/DebianPairKey.pem admin@100.52.17.180`
4. Copy the updated strategy to OpenAlgo's `strategies/scripts/` directory
5. Restart the strategy through the /python web UI or the restart API

### Hermes AI Integration

The Ubuntu Control Panel runs Hermes AI on Coolify:

- **Model:** NousResearch Hermes agent with a web UI
- **Communication:** Paired with Telegram for chat-based interaction
- **Docker access:** Full Docker socket access for container lifecycle management
- **OpenCode CLI:** Bind-mounted into the Hermes container, enabling AI-driven code editing through nsenter
- **Host access:** nsenter provides root-level access to the host Ubuntu system from within the container

---

## 8. The Vision -- Fully Automated AI Trading

### What "Fully Automated" Means

A fully automated AI trading system does not mean a black box that trades without oversight. It means an AI agent performs the complete trading workflow autonomously, with human supervision at the oversight level rather than the execution level:

1. **AI agent monitors market conditions in real-time** -- subscribing to market data feeds, tracking instrument movements, watching for opportunities.
2. **AI agent reads and analyzes strategy logs automatically** -- pulling logs from the production server, running them through the analysis tools, identifying patterns, and measuring performance.
3. **AI agent generates trading signals based on multi-factor analysis** -- combining the 5-layer scoring system with historical performance data to produce entry and exit signals with confidence scores.
4. **AI agent places orders through MCP tool calls** -- converting signals into orders via the unified MCP server, handling order types, routing, and error recovery.
5. **AI agent manages positions** -- trailing stop-losses, executing partial exits, enforcing risk limits, and adjusting strategy parameters based on market conditions.
6. **AI agent reports performance via Telegram/WhatsApp** -- sending end-of-day summaries, alerting on anomalies, and providing on-demand status reports.

### Pipeline Architecture

The pipeline connects all components into a continuous autonomous loop:

```
[Market Data Feed] -> [AI Agent Brain]
                           |
                      [Analysis Layer]
                      - Log analysis (current local MCP tools)
                      - Signal generation (confluence, S3)
                      - Risk assessment (drawdown, streaks, circuit breaker)
                      - KPI tracking (per-trade, ratios)
                           |
                      [Decision Layer]
                      - Entry/exit decisions
                      - Position sizing
                      - Strike selection
                      - Risk-reward evaluation
                           |
                      [Execution Layer]
                      - Place orders (OpenAlgo MCP tools)
                      - Monitor fills
                      - Manage trailing SL
                      - Handle partial exits
                           |
                      [Reporting Layer]
                      - Telegram alerts
                      - Performance dashboards
                      - Journal entries
                           |
                      [Feedback Loop]
                      - Performance data feeds back into analysis
                      - Strategy parameters adapt based on results
                      - Logs are ingested for the next analysis cycle
```

### Priority Roadmap

| Priority | Task | Effort | Impact |
| P0 | Unified MCP server (merge local + OpenAlgo tools) | Medium | Enables single AI interface for both analysis and trading |
| P1 | Strategy control tools (start/stop/config via MCP) | Low | AI can manage strategy lifecycle without SSH or web UI |
| P2 | Real-time monitoring (position/P&L streams via MCP resources) | Medium | AI has live visibility into running positions |
| P3 | Autonomous signal generation (AI reads logs -> generates signals) | High | Core AI trading capability -- the analysis-to-signal bridge |
| P4 | Risk-managed execution (AI places orders with risk limits) | High | Safe autonomous trading with guardrails |
| P5 | Performance optimization (AI tunes strategy parameters) | Very High | Adaptive AI trading that improves over time |

Each priority builds on the previous one. P0 is the foundation -- without a unified MCP server, no automated pipeline can exist. P1 and P2 add basic control and visibility. P3 and P4 deliver the core autonomous trading loop. P5 is the long-term optimization layer.

---

## 9. Quick Reference

### Key File Paths

| What | Path |
| OpenAlgo source | /home/ubuntu/openalgo/ |
| MCP server (trading) | /home/ubuntu/openalgo/mcp/mcpserver.py |
| BuyerEdgeStrategy | /home/ubuntu/OA/strategies/examples/BuyerEdgeStrategy.py |
| Local MCP server (analysis) | /home/ubuntu/OA/strategies/tools/mcp/server.py |
| Tools framework | /home/ubuntu/OA/strategies/tools/ |
| Log files | /home/ubuntu/OA/strategies/docs/logs_raw/ |
| Analysis reports | /home/ubuntu/OA/strategies/docs/logs_analysis/ |
| SSH keys | /home/ubuntu/docs/keys/ |
| Infrastructure handbook | /home/ubuntu/docs/infrastructure-handbook.md |

### Common Operations

```bash
# SSH to OpenAlgo production server
ssh -i /home/ubuntu/docs/keys/DebianPairKey.pem admin@100.52.17.180

# SSH to Ubuntu control panel
ssh -i /home/ubuntu/docs/keys/UbuntuPairKey.pem root@98.85.232.152

# Download the latest production log file
ssh admin@100.52.17.180 "ls -t ~/openalgo/logs/Logs-*.txt | head -1"

# Check strategy status by tailing container logs
ssh admin@100.52.17.180 "docker logs openalgo-web --tail 50"

# Run local MCP server for log analysis
cd /home/ubuntu/OA/strategies && python -m tools.mcp.server

# Run OpenAlgo MCP server (for trading)
python -m mcp.mcpserver <api_key> <host>

# View all running containers on Debian
ssh admin@100.52.17.180 "docker ps --format 'table {{.Names}}\t{{.Status}}'"

# List available log files on Debian
ssh admin@100.52.17.180 "ls -lh ~/openalgo/logs/"
```
