# AutonomousTrading (AT) MCP Connector — Testing Prompt Suite

A three-stage prompt sequence for testing the `OA` MCP connector (trading analysis / research / jobs / monitoring). Run in order — each stage builds on the findings of the one before it, and the final report should reconcile all three.

1. **Baseline Tester** — inventory, relationships, phased pass/fail testing
2. **"What If" Scenario Testing (v1)** — illustrative edge-case probing
3. **"What If" Scenario Testing (v2 — Deep/Systematic)** — exhaustive, dimension-based coverage
4. **Extended Focus Additions (v3)** — dedicated concurrency/race-condition depth, session data migration, and severity/impact analysis

---

## 1. Baseline Tester

Use this first to establish the tool inventory, relationships, and a phased pass/fail baseline.

```
Now assume the role of an MCP gateway tester, specifically for the 'OA' connector/plugin — the one handling trading analysis and testing. Start by listing all available tools exposed through the 'OA' MCP connector. Then cross-reference each tool against the others to identify their relationships and dependencies — which tools rely on, feed into, or interact with which others — and test them together across multiple phases, rather than testing each tool in isolation.

Structure the testing in phases: first, verify each tool in 'OA' works correctly on its own (baseline/unit-level check). Next, test tools that have direct relationships or dependencies together, in the combinations they'd realistically be used in for trading analysis workflows. Finally, test broader end-to-end flows that chain multiple 'OA' tools together, the way an AI agent actually would when handling a real trading analysis request.

For each phase, report what was tested, what passed, what failed, and why — including any tool that wasn't triggered when it should have been, or was triggered incorrectly.
```

---

## 2. "What If" Scenario Testing (v1 — Illustrative)

Run after the baseline report is available. This pass introduces targeted edge cases seeded on single and multiple sessions.

```
Now go deeper than the baseline test. Using the same 'OA' MCP connector and its full tool inventory, design and run your own step-by-step test scenarios framed as "What If" cases — seeded on a single session, and separately on multiple sessions together — to find what actually works, what's blocking, what gaps exist, and what issues or bugs are hiding beneath the surface-level pass/fail results.

For each scenario, don't just confirm the tool responds — probe how it behaves under conditions the baseline test didn't cover. For example:
- What if a session has zero entries/exits, or only partial data (mid-session crash, incomplete log)?
- What if two tools that depend on the same session are called with conflicting or stale state (e.g. `entry_list` after a session has been re-processed)?
- What if `circuit_breaker` should trigger but the underlying data is ambiguous or borderline (e.g. loss exactly at the limit)?
- What if `evidence_strength` is queried against multiple sessions with contradictory outcomes — does it still correctly withhold statistical claims?
- What if a job (`job_enqueue`) is cancelled mid-run and then its status/result is queried?
- What if `propose_config_change` is attempted when evidence is weak — does the Research chain correctly block or warn, or does it silently allow it?
- What if live tools (`live_positions`, `live_orders`, `recent_ticks`) are queried when the market is closed, or when no session is currently live?
- What if the same tool is called twice in quick succession, or with overlapping/conflicting parameters — does the gateway handle it consistently?

Chain these "What If" scenarios the way a real trading-analysis agent would — combining multiple tools per scenario, not testing them one at a time. For each scenario, explicitly state: what you tested, what you expected, what actually happened, and whether it reveals a working feature, a blocking issue, a gap in coverage, or a bug.

Conclude with a consolidated findings section: a clear list of confirmed gaps, issues, and bugs discovered — separate from what was already confirmed healthy in the baseline report — so we know exactly what still needs fixing before the OA connector is considered fully validated.
```

---

## 3. "What If" Scenario Testing (v2 — Deep/Systematic)

Run after v1. This pass removes the fixed example list and requires exhaustive, dimension-based coverage across every tool category, rather than a capped set of illustrative cases.

```
Now go even deeper than the previous "What If" pass — that round was illustrative but limited in scenario count. This time, generate a comprehensive, systematic scenario matrix across every tool category in the 'OA' inventory (Analysis, Research, Jobs, Monitoring) — not just a sample of examples, but exhaustive coverage of the realistic edge cases within each category.

For each tool category, systematically test:
- **Boundary conditions** — empty data, single data point, maximum/extreme values, exact threshold hits (e.g. loss exactly at the circuit-breaker limit, zero trades, a single-tick session).
- **Malformed or unexpected input** — missing required parameters, invalid session IDs, out-of-range parameter values, wrong data types where applicable.
- **State conflicts and race conditions** — two tools reading the same session while it's being modified/reprocessed, a job being queried mid-transition between states, live tools called during a state change (order filling, position closing).
- **Cross-session consistency** — the same tool run across multiple sessions with contradictory results (e.g. one profitable, one at max drawdown) to see if aggregation/evidence tools handle contradiction correctly rather than averaging it away silently.
- **Dependency violations** — calling a dependent tool before its prerequisite has run or with a prerequisite that failed/returned empty (e.g. `entry_list` on a session with no `list_sessions` lookup done first, `propose_config_change` with no prior `evidence_strength` check).
- **Repeated/concurrent calls** — the same tool called multiple times rapidly, or two tools that touch the same underlying data called simultaneously, to check for inconsistent or non-idempotent results.
- **Silent failure modes** — cases where a tool doesn't error but returns technically valid, misleading, or incomplete data without flagging it as such.

Do not limit yourself to a fixed number of scenarios — continue systematically until each tool category has been stress-tested across all of the above dimensions, using both single-session and multi-session seeding throughout.

For every scenario tested, report: what was tested, what was expected, what actually happened, and classify the result as a working feature, a blocking issue, a coverage gap, or a bug.

Conclude with a full consolidated findings report, organized by tool category, clearly separating: (1) what was already confirmed healthy in the baseline report, (2) what was newly confirmed in the first "What If" pass, and (3) new findings from this deeper systematic pass — so the three reports together give a complete, non-overlapping picture of the OA connector's real-world readiness.
```

---

## 4. Extended Focus Additions (v3)

Run after v2. This pass goes deeper on three specific areas that the earlier stages only touched briefly or not at all: dedicated concurrency/race-condition testing, session data migration behavior, and severity/impact classification for every finding across all stages.

```
Now extend the testing with three focused additions that go beyond what the previous passes covered.

First, concurrency and race conditions: v2 covered this briefly as one dimension among several — now make it a dedicated focus. Systematically test what happens when multiple tools, or multiple calls to the same tool, execute concurrently against the same session or the same underlying data — for example, two analysis tools reading a session while a job is actively reprocessing it, a live-monitoring tool and a session-analysis tool touching overlapping data at the same time, or rapid duplicate calls to the same tool with no delay between them. Identify any inconsistent results, partial writes, stale reads, or non-deterministic behavior this produces.

Second, session data migration: explore how the 'OA' tools behave when session data isn't in a single, stable, current format. Test scenarios such as: a session logged in an older format/schema being read by current tools, a session that's only partially migrated or upgraded, a session referencing parameters or fields that have since been renamed, removed, or changed type, and any tool that assumes a schema version without explicitly checking it. Identify where migration gaps cause silent misreads, errors, or incorrect analysis rather than a clear compatibility failure.

Third, severity and impact analysis: for every finding across the baseline report, the v1 "What If" pass, the v2 systematic pass, and this extended pass, add a severity and business-impact classification. For each issue, gap, or bug already found — plus anything new found here — classify it as Critical, High, Medium, or Low, and explain the real-world impact: what a trading-analysis agent or end user would actually experience if this issue occurred in production (e.g. wrong trading signal reaches the agent, silent data corruption, a blocked-but-recoverable action, or a cosmetic/non-blocking inconsistency). Do not just restate the technical description — translate each finding into what breaks, for whom, and how badly.

Conclude with a single consolidated severity-ranked findings table covering all four passes (baseline, v1, v2, v3), sorted from Critical to Low, so the most impactful issues are immediately visible at the top.
```

---

## Usage Notes

- Run all four prompts **in sequence**, feeding each prior report's output back into context before running the next.
- The **v2 findings must reconcile against both prior reports** — nothing should be re-flagged as new if it was already confirmed healthy or already found in v1.
- Session seeding should include **both single-session and multi-session** runs at every stage where applicable, as specified in each prompt.
- **v3 is additive, not repetitive** — it deepens concurrency and adds session-migration coverage that the earlier stages didn't dedicate focus to, and it retroactively classifies severity/impact for every finding across all prior stages rather than re-testing them.
- The **final consolidated table from v3** should be the single source of truth for prioritizing fixes — Critical/High findings first.
