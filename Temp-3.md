Yes. Both partial items are real, fixable wiring gaps. They do not require changing strategy logic, limits, or entry thresholds.

Area	| Verified state |	Can finish? |	Required work

Automatic startup proof	✅ Working. Today’s machine receipt contains current OpenAlgo funds, books, account/instance fingerprints, reconciliation, code entrypoint and all 6 configured caps.	Complete	Keep it; enrich it through the identity work below.
Continuous mid-session proof	🟡 Fresh positions, P&L, trade count, drawdown, cooldown and in-flight orders are checked each driver pass. Stable session identity is not revalidated before submission.	Yes	Add periodic integrity checkpoints and require a fresh matching checkpoint at submission.
Run/config/market identity	🟡 Runtime provenance exists, but it is not propagated through the complete lifecycle.	Yes	Create one identity envelope and carry it through decision → plan → order → fill → outcome and replay.
AI money authority	⛔ Promotion enforcement works, but no production surface can mint the promotion receipt. Required research evidence is also absent.	Technically yes, but do not enable yet	Keep disabled until locked-OOS dates, contract-note cost reconciliation and an explicit owner promotion decision exist.


Concrete live evidence:

154 decisions were recorded today, all with config_version: unversioned.

5 reconciled live outcomes exist; all 5 say code_identity: unknown and config_identity: unknown.

Runtime run_8cfa4a96b09a has 40 captured module hashes, but those hashes do not reach its outcomes.

OpenAlgo currently has 10 fills, and broker/framework reconciliation reports zero unmatched fills in either direction.

The strategy and persistent monitoring services remain running.

83 targeted attestation, session-state, provenance, live-record and replay tests passed; 2 skipped.


The smallest coherent completion is:

1. Define one versioned identity envelope containing run_id, code digest, effective config digest/version, strategy identity, market source/schema identity, input cursor/digest and—where applicable—AI lineage.


2. Put that same envelope on live and replay decisions, plans, order lifecycle records and outcomes.


3. During each live pass, produce a tamper-evident integrity checkpoint from current OpenAlgo identity, reconciliation and market-data freshness.


4. Have the execution gateway reject submission when the checkpoint is absent, stale, belongs to another run, or conflicts with the startup receipt.


5. Do not invalidate the session merely because P&L, exposure, orders or positions normally moved; validate those mutable values continuously against deterministic risk and reconciliation controls.


6. Leave AI promotion authority fail-closed.



No code was changed during this audit. AGENTS.md remains untracked and untouched.
