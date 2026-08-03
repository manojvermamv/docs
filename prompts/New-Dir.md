Paste-ready prompt — branch base: claude/openalgo-trading-architecture-uu1bxn
---
You have read/write access to https://github.com/manojvermamv/AutonomousTrading on branch claude/openalgo-trading-architecture-uu1bxn.

Goal
- Add core features and infra needed to scale the gateway + analysis into a production-capable, largely automated AI trading framework (automated proposals, simulation, scheduling, analytics, distributed workers, model tracking, and safe rollout primitives). Implement each feature as a single focused branch/PR with tests and a brief README snippet.

Deliverables (high-level)
- Work split into small PRs; each PR must include code, tests, a defaults.yaml snippet if config is added, and run instructions. Keep changes minimal & focused per PR.

Priority feature list (implement in order)

3) Shadow / dry-run & progressive rollout framework
- What: A shadow mode where AI proposals (or model-driven changes) execute in parallel but do not affect real config or orders (observes hypothetical outcomes). Add a rollout mechanism to move proposal → staged apply → full apply with canary windows.
- Why: safely validate automated changes at scale before they touch real trading.
- Acceptance:
  - research.propose(...) generates a proposal with id and simulated outcome (from sim runner) when `simulate: true`.
  - Add endpoints/tools: proposal_list(), proposal_simulate(id), proposal_apply_canary(id, percentage), proposal_rollout(id).
  - Persist proposals in run/proposals/ and optionally in a small Postgres/SQLite table for indexing.
- Files: mcp_gateway/domains/research/*, mcp_tools/sim integration
- Test: simulated proposal includes expected metrics and stored proposal metadata.

4) High-throughput log parsing & incremental indexing (performance)
- What: Make analysis parse logs in parallel and optionally pre-index parsed log rows to DuckDB/Parquet so queries and metrics are fast. Cache pattern matches and reuse across runs.
- Why: large log volumes need fast scanning and repeated queries.
- Acceptance:
  - Add a log parser pipeline that accepts a directory and writes parsed rows into run/parsed/<session>-YYYY.parquet.
  - analysis tools read from parsed store if present; fallback to streaming parse otherwise.
  - Use multiprocessing or thread pool; ensure deterministic ordering where required.
- Files: mcp_tools/core/log_ingest.py, mcp_tools/core/parsed_store.py
- Test: parse many small test logs in parallel and assert parsed row counts match serial parser.

5) Scalable data storage & archiving (Parquet + object store)
- What: Add support to write Parquet artifacts to S3/MinIO (configurable). Add retention and lifecycle policies.
- Why: long retention, partitioning, and cheap queries at scale.
- Acceptance:
  - config keys for storage endpoint (e.g., S3 endpoint, bucket).
  - ingest script can target local (filesystem) or S3 backend.
  - Example docker-compose with MinIO for local testing.
- Files: scripts/ingest_to_s3.py, config/defaults.yaml additions
- Test: ingest sample parquet to MinIO and read back.

6) Model registry, experiment tracking & governance (MLflow or similar)
- What: Track model versions and evaluation results for any agent/model that proposes changes. Record model metadata: name, version, prompt, temperature, embeddings used, evaluation metrics, and proposal IDs it influenced.
- Why: reproduceability and rollbacks for model-driven automation.
- Acceptance:
  - Integrate an MLflow backend or a minimal SQLite-backed model registry.
  - Each proposal must reference model_version and evaluation metrics (in proposal JSON).
  - Provide a CLI script to list models and their proposal history.
- Files: mcp_gateway/ml/registry.py, integration hook in research.propose
- Test: register a dummy model and assert proposals include model reference.

7) Automated validation & retraining triggers (data-driven)
- What: Add retraining triggers when drift or performance drops below thresholds. Use existing drift canary and trade_kpis reliability bands to trigger retrain jobs into worker queue.
- Why: keep models and heuristics current as market regime shifts.
- Acceptance:
  - Add config thresholds like research.retrain_on_drift=true and research.retrain_thresholds.
  - Canary job can enqueue model retrain when thresholds met; record the trigger event in audit store.
- Files: scheduler rules, mcp_tools/core/drift.py hooks
- Test: simulate drift event and assert retrain job enqueued.

8) Live-sim & offline test harness (replay & shadow trading)
- What: Provide easy way to replay historical ticks and run both strategy and AI proposals against them in a sandbox that simulates fills and slippage using configurable models.
- Why: validate proposals and automated tuning before live rollouts.
- Acceptance:
  - Provide a replay CLI that runs an OpenAlgo-like environment in-memory and returns per-trade metrics.
  - Integrate with research.simulate_proposal() to provide evidence.
- Files: mcp_tools/tape/ (extend), scripts/replay_session.py
- Test: replay a recorded session and assert metrics output consistent.

9) Metrics, alerting, and dashboards (Prometheus + Grafana)
- What: Export metrics for request volume, queue/backlog size, risk-guard allow/block counts, proposal simulation success/failure, worker task durations, ingest throughput. Provide sample Grafana dashboards JSON.
- Acceptance:
  - /metrics endpoint when MCP_TRANSPORT=http and instrumentation counters added.
  - docs/grafana/sample-dashboard.json
- Files: mcp_gateway/observability/metrics.py, docs/observability.md
- Test: unit test that counters increment for synthetic calls.

10) Backtest / parameter-sweep automation + A/B evaluation
- What: Provide automated param-sweep runners using the sim runner and store results to DuckDB/Parquet with statistical summaries and A/B comparison utilities.
- Acceptance:
  - A sweep tool that outputs a ranked list of parameter sets with sample-size-aware confidence intervals and reliability verdicts (use reliability_bands).
  - Save results into run/sweeps/<id>/results.parquet.
- Files: mcp_tools/sim/sweep.py, mcp_gateway/domains/research/sweep_tool
- Test: run a small sweep and assert results file exists and stats computed.

Implementation guidance & constraints
- Keep gateway responsive: offload heavy work to workers.
- Preserve existing tests where possible; add tests for new features.
- Make all new storage paths configurable in mcp_gateway/config/defaults.yaml with sensible defaults under run/.
- Keep dry-run/approval semantics available; even fully automated systems should support shadow/dry-run/staging flows.
- Use existing mcp_tools.sim and tape replay code where possible rather than reimplementing.

Branching & PR rules
- Create one branch per feature: task/<short>-<n> (e.g., task/audit-pipeline-01).
- Each PR title: "<feature>: <short description>" and include Acceptance & How to test locally.
- Include sample commands in PR to run the feature locally (start worker, ingest sample, run a replay).

Example minimal local test commands to include
- pip install -e ".[dev]"
- Start gateway (http transport): MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8000 python mcp_gateway/gateway.py
- Start worker (if used): python -m mcp_gateway.worker --redis redis://localhost:6379
- Enqueue a job, wait and check run/tasks/<id>.json or run/audit.duckdb

Do the first PR now: implement the Production audit + analytics pipeline (JSONL -> Parquet/DuckDB). Create branch task/audit-pipeline-01, add tests and an ingest script, and open a draft PR.


If you want, I can now:
- generate the exact code patch for the first PR (audit emitter + ingest script + tests), or
- reduce the list further to only 3 highest-priority features for a rapid MVP. Which do you want me to do?
