# Structural Analysis Prompt — BuyerEdgeStrategy.py
### Oh-My-Opencode / Codegraph · Complete Combined Prompt

---

## Paths (locked — do not substitute)

| Role | Path |
|---|---|
| Primary target | `/home/ubuntu/OA/strategies/examples/BuyerEdgeStrategy.py` |
| Infra reference (primary) | `/home/ubuntu/openalgo/restx_api/` |
| Infra reference (fallback) | `/home/ubuntu/openalgo/...` — expand only if call-site cannot be validated within `restx_api/` alone |
| Knowledge store | `/home/ubuntu/OA/` |
| Report output | `/home/ubuntu/OA/reports/YYYY-MM-DD_BuyerEdgeStrategy_StructuralAudit.md` |

---

## Prompt

```
Act as a compiler engineer. Run exhaustive multi-layer structural analysis on
`/home/ubuntu/OA/strategies/examples/BuyerEdgeStrategy.py`, grounded against
the OpenAlgo infra at `/home/ubuntu/openalgo/restx_api/` (expand to
`/home/ubuntu/openalgo/...` only if a call-site cannot be validated within
`restx_api/` alone). All findings, indexes, graphs, and report output persist
to `/home/ubuntu/OA/`. Strict rules follow — execute all, skip none.

────────────────────────────────────────────
ANALYSIS RULES
────────────────────────────────────────────

1. TRUNCATE NOTHING.
   Index every node in BuyerEdgeStrategy.py — class, function, decorator,
   control-flow, assign, call, return, raise, await, yield, lambda,
   comprehension — assigned sequential IDs (Node000001…). Flag these domain
   node types inline wherever they appear:
     [STATE-TRANSITION]     state-machine transition points
     [BROKER-API-CALL]      broker API call sites
     [RISK-GATE]            risk gate checkpoints
     [THREAD-BOUNDARY]      threading boundaries
     [INDICATOR-REGISTRY]   IndicatorSpec / StatisticSpec registry entries
     [STOPMODE-DISPATCH]    StopMode variant dispatch points

2. MULTI-REPRESENTATION PARSE.
   AST (structure) + LibCST (comments / exact positions) + symtable (scope
   resolution) on the primary target. Never trust docstrings or inline comments
   as ground truth in either BuyerEdgeStrategy.py or the OpenAlgo infra —
   validate all behavior from actual code paths only.

3. BUILD LAYERED GRAPHS IN ORDER.
   Call Graph
     → per-function CFG (execution paths, unreachable branches, exception flows)
     → DFG (variable definition / mutation / consumption chains).
   Taint any value sourced from broker API responses, os.environ, or config
   dicts and propagate the taint label downstream until sanitized or discarded.

4. TYPED KNOWLEDGE GRAPH.
   Entities:
     Module, Class, Function, Variable, Import, Decorator, Exception,
     AsyncTask, Thread, BrokerAPICall, RiskGate, StateMachineState
   Edges:
     calls, imports, inherits, mutates, raises, returns, reads, writes,
     catches, transitions_to, guards

5. CROSS-REFERENCE EVERY BROKER API CALL SITE.
   For every BuyerEdgeStrategy.py broker API call, trace to its handler in
   `/home/ubuntu/openalgo/restx_api/` and confirm endpoint, request schema,
   and response contract from infra source code — not SDK docstrings. Where
   the strategy call-site contract diverges from the infra handler, flag:
     [SCHEMA_MISMATCH: Node{id} ↔ infra:{file}:{line}]

6. TRACE EVERY CALL PATH.
   Step-by-step including dynamic dispatch, callbacks, decorators, StopMode
   variant dispatch, and SmartOrder vs PlaceOrder branching paths end-to-end.
   Flag runtime-only resolution points as [DYNAMIC_DISPATCH_BOUNDARY].

7. DETECT SMELLS.
   Standard:  God Objects/Functions, cyclic imports, tight coupling, deep
              nesting (> 4), mutable globals, hidden side effects.
   Domain:    State mutations outside designated state-machine transition
              functions. Indicator scoring logic leaking outside
              IndicatorSpec/StatisticSpec registry boundaries. Unhandled
              StopMode variant paths in CFG. Shared mutable state crossing
              thread boundaries.

8. SECURITY PASS.
   Flag every instance of: eval, exec, compile, __import__, os.system,
   subprocess(shell=True), pickle.loads/load, marshal.loads, yaml.load
   (without SafeLoader), jsonpickle.decode, SQL string concatenation,
   hardcoded secrets (password=, secret=, api_key=, token= followed by a
   string literal), open(user_input), requests.get(user_input),
   shutil.rmtree(user_input).
   Output: [SECURITY:{severity}] Node{id} ({name}, line {n}):
           {pattern} — taint_source: {source or UNKNOWN}
   Severity: CRITICAL | HIGH | MEDIUM | LOW

9. MAP FULL STRUCTURAL BLAST RADIUS.
   For every flagged node: upstream callers (all levels) + downstream callees
   (all levels) through the complete dependency chain.
   Classify: ISOLATED | LOCAL | MODULE-WIDE | CROSS-MODULE | SYSTEM-WIDE

────────────────────────────────────────────
PERSISTENCE & REPORT RULES
────────────────────────────────────────────

10. REPORT FILE — DATE-STAMPED.
    Write the full audit report to:
      `/home/ubuntu/OA/reports/YYYY-MM-DD_BuyerEdgeStrategy_StructuralAudit.md`
    using the actual run date. If a report for the same date already exists,
    append a run counter: `…_StructuralAudit_r2.md`. Never overwrite a prior
    run's report.

11. REPORT MUST BE SELF-CONTAINED AND READER-INDEPENDENT.
    A reader with no access to the original conversation, prior session context,
    or source files must be able to fully understand every finding, trace every
    cited node to a file and line number, and apply every patch candidate
    without additional lookup. Every node reference uses the format:
      Node{id} ({name}, {file}:{line})

12. MANDATORY REPORT SECTIONS — EMIT ALL, NEVER SKIP ANY.

    ┌─────────────────────────────────────────────────────────────────┐
    │  # BuyerEdgeStrategy Structural Audit — YYYY-MM-DD              │
    │                                                                 │
    │  ## 0. Run Metadata                                             │
    │     Date, primary target path, infra reference path,           │
    │     knowledge store path, Python version, tool versions         │
    │     (libcst, radon, bandit, networkx, pylint, astroid),         │
    │     total nodes indexed, total knowledge-graph edges,           │
    │     run duration.                                               │
    │                                                                 │
    │  ## 1. Executive Summary                                        │
    │     ≤ 10 lines. Total findings by severity (CRITICAL / HIGH /   │
    │     MEDIUM / LOW), top 3 structural risks, top 3 recommended    │
    │     patches, overall blast-radius classification of the file.   │
    │                                                                 │
    │  ## 2. Node Index (complete)                                    │
    │     Node{id} | type | name | file:line | parent_id | scope      │
    │     Every node — no truncation. Domain-type flags inline.       │
    │                                                                 │
    │  ## 3. Call Graph                                               │
    │     Adjacency list: Node{id} (name) → [Node{id} (name), ...]   │
    │     Annotate cross-file edges (strategy → infra) with           │
    │     target file:line. Flag [DYNAMIC_DISPATCH_BOUNDARY].         │
    │                                                                 │
    │  ## 4. CFG Summary per Function                                 │
    │     Node{id} (name): entry_block → ... → exit_blocks            │
    │     Unreachable blocks: [Node{id}:block{n}, ...]                │
    │     Swallowed exceptions: [Node{id}:line {n} — pattern]         │
    │                                                                 │
    │  ## 5. DFG Findings                                             │
    │     Variable | Scope | DEF:line | MOD:lines | USE:lines |       │
    │     Tainted | Taint source                                      │
    │     Flag every value from broker API responses or config dicts. │
    │                                                                 │
    │  ## 6. Complexity Table                                         │
    │     Node{id} | Function | CC | Cognitive | SLOC | MI |          │
    │     Max Depth | Fan-In | Fan-Out                                │
    │     Bold rows exceeding any threshold.                          │
    │     Thresholds: CC > 10, Cognitive > 15, SLOC > 50,            │
    │     Max Depth > 4 → flag HIGH.                                  │
    │                                                                 │
    │  ## 7. Schema Cross-Reference: Strategy ↔ OpenAlgo Infra        │
    │     For every broker API call site:                             │
    │     Node{id} (strategy call) | endpoint | strategy schema |     │
    │     infra schema (file:line) | status                           │
    │     Status: MATCH | SCHEMA_MISMATCH | UNRESOLVED                │
    │                                                                 │
    │  ## 8. Smell Findings                                           │
    │     [SMELL:{type}:{severity}] Node{id} ({name}, line {n}):      │
    │     description                                                 │
    │     Ordered: CRITICAL → HIGH → MEDIUM → LOW.                    │
    │                                                                 │
    │  ## 9. Security Findings                                        │
    │     [SECURITY:{severity}] Node{id} ({name}, line {n}):          │
    │     pattern — taint_source                                      │
    │     Ordered: CRITICAL → HIGH → MEDIUM → LOW.                    │
    │                                                                 │
    │  ## 10. Domain-Specific Findings                                │
    │      State-machine violations (mutations outside transition      │
    │      functions). Indicator/statistic logic outside registry.    │
    │      StopMode dispatch gaps (unhandled variant paths in CFG).   │
    │      Threading boundary violations (shared mutable state        │
    │      across thread calls).                                      │
    │                                                                 │
    │  ## 11. Findings Registry (F-numbers)                           │
    │      F-{NNN} | severity | Node{id} | line | description |       │
    │      status: OPEN / PATCHED / DEFERRED                          │
    │                                                                 │
    │  ## 12. Patch Candidates (PATCH-numbers)                        │
    │      PATCH-{NNN} | targets F-{NNN} | Node{id} | line range |    │
    │      description | blast-radius class                           │
    │      Each entry format (strict):                                │
    │        Current ({file}:{line_start}–{line_end}):                │
    │        <exact current code block>                               │
    │        Proposed:                                                │
    │        <exact replacement code block>                           │
    │        Rationale: <one sentence grounded in source evidence>    │
    │        Blast radius: <classification>                           │
    │        Status: UNVERIFIED                                       │
    │                                                                 │
    │  ## 13. Blast Radius Map                                        │
    │      For every HIGH / CRITICAL finding:                         │
    │      Node{id} upstream callers (all levels) +                   │
    │      downstream callees (all levels).                           │
    │      Impact surface list sorted by Node{id}.                    │
    │      Classification per finding.                                │
    │                                                                 │
    │  ## 14. Knowledge Graph Edge Dump                               │
    │      src_Node{id} | edge_type | dst_Node{id} | file:line        │
    │      All edges — no truncation.                                 │
    │                                                                 │
    │  ## 15. Open Questions & Deferred Items                         │
    │      Anything unresolvable from source alone: UNRESOLVED        │
    │      symbols, runtime-only dispatch paths, infra endpoints       │
    │      not found in restx_api/.                                   │
    │      Format: [UNRESOLVED:{id}] description — reason.            │
    │                                                                 │
    │  ## 16. Appendix — Tool Outputs                                 │
    │      Raw radon CC table, radon MI table, bandit scan output     │
    │      (severity ≥ MEDIUM), pyflakes output.                      │
    │      Verbatim — no truncation.                                  │
    └─────────────────────────────────────────────────────────────────┘

13. SECTION COMPLETENESS RULE.
    If a section produces zero findings, emit:
      [SECTION {N}: 0 findings — not skipped]
    A missing section is a report defect, not a clean result.

14. PATCH SNIPPET FORMAT — STRICT.
    No patch is marked VERIFIED until the user confirms against uploaded
    source with explicit line-number citation in the same session.
    Status field must read UNVERIFIED on every initial output.

15. INCREMENTAL RE-RUN BEHAVIOUR.
    Before starting, check `/home/ubuntu/OA/reports/` for any prior dated
    report. If found, load its F-number and PATCH-number registries. Carry
    forward all OPEN findings with their original F-numbers. New findings in
    this run receive the next available F-number continuing the prior sequence.
    Never reset registry numbering across runs.
```

---

## Quick Reference — Domain Node Type Flags

| Flag | Meaning |
|---|---|
| `[STATE-TRANSITION]` | State-machine transition point |
| `[BROKER-API-CALL]` | OpenAlgo broker API call site |
| `[RISK-GATE]` | Risk gate / entry guard checkpoint |
| `[THREAD-BOUNDARY]` | Threading boundary / shared-state crossing |
| `[INDICATOR-REGISTRY]` | IndicatorSpec / StatisticSpec registry entry |
| `[STOPMODE-DISPATCH]` | StopMode variant dispatch point |
| `[SCHEMA_MISMATCH]` | Strategy call schema ≠ infra handler schema |
| `[DYNAMIC_DISPATCH_BOUNDARY]` | Runtime-only resolution — cannot be statically traced |
| `[UNRESOLVED:{id}]` | Symbol or endpoint not resolvable from source alone |

---

## Quick Reference — Severity & Blast Radius Scales

| Severity | Meaning |
|---|---|
| `CRITICAL` | Immediate correctness or safety risk |
| `HIGH` | Significant structural or runtime risk |
| `MEDIUM` | Degraded maintainability or latent bug |
| `LOW` | Style, minor smell, or future risk |

| Blast Radius Class | Meaning |
|---|---|
| `ISOLATED` | Affects only the flagged node |
| `LOCAL` | Affects the containing function/class |
| `MODULE-WIDE` | Affects the entire BuyerEdgeStrategy.py file |
| `CROSS-MODULE` | Affects BuyerEdgeStrategy.py + OpenAlgo infra |
| `SYSTEM-WIDE` | Affects broker execution, order state, or live PnL |

---

## Quick Reference — Complexity Thresholds

| Metric | Tool | Flag threshold |
|---|---|---|
| Cyclomatic Complexity | `radon cc` | > 10 → HIGH |
| Cognitive Complexity | `pylint.extensions.cognitive_complexity` | > 15 → HIGH |
| SLOC per function | `radon raw` | > 50 → REVIEW |
| Max nesting depth | AST | > 4 → HIGH |
| Parameter count | AST | > 5 → REVIEW |

---

## Quick Reference — Report File Naming

```
/home/ubuntu/OA/reports/
  YYYY-MM-DD_BuyerEdgeStrategy_StructuralAudit.md       ← first run of the day
  YYYY-MM-DD_BuyerEdgeStrategy_StructuralAudit_r2.md    ← second run same day
  YYYY-MM-DD_BuyerEdgeStrategy_StructuralAudit_r3.md    ← third run same day
```

Registry numbering (F-numbers, PATCH-numbers) is **never reset** across runs or dates — sequences accumulate across the full development lifecycle.
