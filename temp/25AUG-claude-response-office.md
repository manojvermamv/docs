I'll start by orienting myself across both directories, then read the Data-Sources master prompt, then check what the existing `audit/` already covers before adding to it.

No `AutonomousTrading` directory here — let me locate it and read the Data-Sources master prompt.

`AutonomousTrading` is this repo itself. Now let me read the existing audit scaffolding — 4 of 12 lenses already have results.

Now let me build the project understanding. First, the map and sizes so I read in the right order.

Strong understanding of the repo now. Let me read the Data-Sources content and the four completed audit lenses.

Now the four completed lenses — extracting the substance compactly.

Let me verify a few load-bearing claims at the source rather than trusting the docs, then I'll lay out the understanding.

I've read the repo end to end, the Data-Sources master prompt and its two analysed sources, and all four completed audit lenses. Here's the picture, then one question before I start the audit.

## What the system is

**A deterministic options desk with an AI control plane bolted alongside it — not an AI that trades.** A tick becomes an order through five stages: capture (your own market store, journalled), decide (one numbered tape → strategy → advisor opinion → framework), send (a ten-stage gate chain → execution gateway → OpenAlgo), record (files in `run/`, then Parquet), look (three MCP gateway processes, `at` CLI, admin console). OpenAlgo owns auth and the broker-facing risk boundary; one arrow in the whole system spends money.

| | |
|---|---|
| Code | 60,325 lines in `src/` (278 files) · 47,953 lines of tests (142 files) · the original strategy monolith is 12,339 lines, kept as the control |
| Surfaces | 11 MCP domains · `at` CLI · Next.js console · 3 gateway processes split by capability |
| Real money | Orders placed through OpenAlgo 14 and 17 Aug 2026. Not theoretical |
| Discipline | Findings are append-only registers; docs get deleted when wrong; a knowledge map fails the suite when it drifts |

**The engineering quality here is genuinely unusual** — layering enforced by a test, a determinism gate, a capability layer behind three presentations, refusals recorded as first-class outcomes. The honest weakness is the other axis, and both your own registers and the Data-Sources analysis land on the same one.

**One thing to know about this checkout:** `run/` holds only `market-data` (21 files). No `run/strategies/strategies.json`, no decisions, orders or advisor records. So this box is a dev checkout — the README's claim that five strategies sit at `authority: trade` cannot be checked here, and any audit finding about deployed configuration can only be checked against code, not against the live host.

## What the Data-Sources rubric adds

Two documents, and they test different things. The reading list (Aronson, Bailey PBO, Deflated Sharpe, `pypbo`, Carver, AFML ch.7) tests whether your **research method** can tell a real edge from a search artefact. The four-phase framework (GEX/Vanna/Charm regime → conviction filters → causal reasoning → async execution) tests whether your **architecture** can carry what a desk needs. The master prompt's own named gap — a Pine-style feature scratchpad that carries prior bars forward and takes arbitrary new specs without a pipeline rebuild — is the one your completed lenses have already confirmed is missing.

## Future direction, in priority order

This is my synthesis of your open items, your 52 defects, master spec §24, the Data-Sources gap map and the 42 verified audit findings. Ordered by what unblocks the most, not by size.

| | What | Why it's here | Status |
|---|---|---|---|
| **1** | **The model is being judged on a prompt that contains almost nothing.** `render()` transmits 7 of 34 chain fields, zero greeks, and `ctx.bars` is a plain list with no `close[1]` semantics. `AdvisorContext.extra`'s filter is set-equal to its only two producers, so "Strategy evidence:" is structurally dead code | Open item 1 ("negative edge at every horizon") is your headline finding — and it was measured on a 934-character prompt. It tells you a model shown almost nothing can't help. It does not tell you the thing you think it tells you | Verified by two lenses |
| **2** | **Contract-spec risk.** BANKNIFTY weeklies were discontinued Nov 2024; NIFTY weekly moved Thursday→Tuesday Sept 2025 | If any expiry assumption is baked in, every signal on that underlying is wrong. Cheap to check, catastrophic if wrong. Both Data-Sources documents flag it independently | **Unverified** — this is the pending `expiry-specs` lens |
| **3** | **Session caps bind nothing, and setting them stops the desk.** `run_framework_live.py:460` passes a blank `Session()`, so all eight `MCP_LIMITS__*` caps evaluate against zeros and pass; setting the one value `.sample.env` documents refuses *every* entry because `capital=0.0` | Touches entry, so the number is yours. The `capital <= 0` half is a plain bug and is correctness work | Verified |
| **4** | **Research method.** `deflate()` is `t − √(2·ln trials)` with `trials` defaulting to 1; the holdout is a chronological split with no purge or embargo; the evidence screens are diagnostic and feed nothing | You cannot tell a real edge from a search artefact today, which makes every future tuning decision unfalsifiable | **Unverified** — pending `research-method` lens |
| **5** | **Structural OCP fixes**, in dependency order: a stage registry for `plan()`, a needs registry to replace five hardcoded enumerations, a renderer port, an execution-client Protocol | The composable ordered rule registry you need **already exists** in `riskguard.py` and nothing on the money path uses it. Reuse it; don't build a second one | Verified |
| **6** | **Regime layer** — GEX, Vanna, Charm, gamma flip, call/put wall, IV rank | Worth building *after* #1, not before. Today nothing computed would reach the model anyway, and `greeks_legs` has been 0 on all 3,850 recorded scans | Partly unverified — pending `greeks-regime` lens |

**The four items marked unverified are exactly what the pending audit lenses cover**, which is why finishing the audit is the right next step rather than acting on the priority order as it stands.

## The question

The remaining 8 lenses (batches 3–6) are `duplicate-generations`, `research-method`, `expiry-specs`, `greeks-regime`, `closed-enumerations`, `layering`, `completeness`, `refute`. `audit/README.md` documents the entry point as a Workflow, and each lens commits its own result so a partial run resumes anywhere. But that spawns 8+ agents and is the expensive path, and my session instructions say not to reach for workflows unless you've asked for one — so I'd rather confirm than assume.

Understood — full outputs of the four completed lenses into one document first, then the workflow. Let me look at how `audit_status.py` already reads the results so the document can be regenerated when the other 8 land.

Extending `audit_status.py` with a `--markdown` mode rather than a separate script — it already derives everything from `results/`, so the document regenerates when the other 8 lenses land.

Three lenses returned fields beyond the documented shape — let me see what the renderer caught rather than dropped.

These are per-lens verdicts the documented result shape never declared. Let me check whether the workflow asks for them before promoting the field.

Two defects in the audit's own harness, worth fixing before 8 more lenses inherit them:

Now promote `summary` and `rubric_source` in the renderer so they read as first-class rather than as leftover JSON:

Now the README must match — otherwise it's the same two-place drift the audit hunts:

`findings` mode appears to have produced no "ok" line — let me check it.

All modes work — `--json` and `--findings` exit 1 (pending lenses), which is why the `&&` chain skipped their echo. Committing this before the workflow.

The consolidated doc is committed. Now the workflow for the 8 remaining lenses. Let me read the resume protocol and the full workflow before launching, so I pass the right pending slugs.

Let me check how the workflow consumes `args` before launching, and fix the stale count in the resume prompt.

The resume machinery handles the partial run correctly. Fixing the stale "Nine lenses" count in the resume prompt, then launching.

Now launching the workflow with the 8 pending slugs.

The 8 remaining lenses are running in batches of two (B3 → B6), and each commits its own `results/<slug>.json`, so it survives an interruption.

**What landed while you were reading:**

`audit/LENS-OUTPUTS.md` — 759 lines, every one of the 42 findings from the four completed lenses in full, unedited: claim, both verification methods, and the named-module fix for each. Plus the corrections (claims in `CLAUDE.md`, `docs/` and the advisor docstrings found to be **wrong**) and the flatters (things that look capable and are not). It's generated, not written:

```bash
python3 scripts/audit_status.py --markdown
```

It lists the 8 not-yet-run lenses as not-yet-run rather than omitting them, so it can't read as complete while the audit isn't.

**Two defects in the audit's own harness, fixed before the 8 inherited them.** `summary` wasn't in the result schema at all — three of the four lenses wrote one anyway, and it was the single most useful line each produced. And `rubric_source` was optional, so `feature-layer` left all nine of its findings with no source attributed, which is fatal for a gap map whose whole purpose is saying which source exposed which gap. Both are now required, and the schema stays open to undeclared keys on purpose.

Progress from any terminal while it runs:

```bash
python3 scripts/audit_status.py
```
