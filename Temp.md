Our current system already covers much of the SPEC's intent: canonical market data, shared live/replay contracts, deterministic planning, execution boundary, reconciliation, append-only evidence, and fail-closed controls. Your current README explicitly says the architecture is retained rather than replaced with parallel `bus`, `supervisor`, `risk`, `authority`, `portfolio`, or `replay` subsystems. 

### What should be cleared before future deeper AI work

```text
                 FINAL ARCHITECTURE RECONCILIATION
                               │
        ┌──────────────────────┼──────────────────────┐
        ↓                      ↓                      ↓
   Architecture           Contracts               Wiring
   boundaries             + identity              + runtime
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ↓
                    Freeze the core foundation
                               ↓
                    AI / Research evolution
```

Specifically, make sure these are settled:

**Replay:** same strategy-facing contracts and deterministic clock/input seams, with evidence-bounded outcomes. Your current design already does this. 

**Authority:** distinguish **tool permission**, **strategy authority**, and future **earned AI autonomy**. Do not let these collapse into one field.

**Risk/breakers:** confirm that all true hard limits are deterministic and outside AI-tunable space.

**Portfolio truth:** keep reconciled book as truth; don't add a portfolio optimizer unless the system actually needs one.

**Eventing:** keep the existing append-only event surface unless scale proves it insufficient. Don't add Kafka/Redis just because the external SPEC mentions buses.

**Supervision:** ensure service health, reconciliation, recovery and runtime ownership are actually wired consistently; this is more important than adding a new supervisor package.

**AI research lifecycle:** this is where the real remaining architectural work begins.

### What I would *not* do

Do **not** do this:

```text
Current system
      +
new SPEC bus
      +
new SPEC supervisor
      +
new SPEC replay
      +
new SPEC risk
      +
new SPEC authority
      ↓
two competing architectures
```

That would create duplicate sources of truth—the exact problem your previous work has repeatedly exposed.

### The real checkpoint

I would consider the architecture “cleared” when this is true:

```text
Market observation
      ↓
Strategy / AI
      ↓
Intent
      ↓
Deterministic planning
      ↓
Risk / breakers / authority
      ↓
Execution
      ↓
OpenAlgo
      ↓
Broker result
      ↓
Reconciliation
      ↓
Research evidence
      ↺
Future strategy / AI
```

and **every box has exactly one authoritative implementation and one clear owner**.

Your current README already states the key ownership boundary: strategies don't open broker connections, all intents pass through the same planning gates, and only the live execution adapter reaches OpenAlgo. 

### Bottom line

**Yes: Do one final architecture-surface cleanup/reconciliation, also pass against the SPEC, then freeze the core architecture and work only on genuine gaps before deep-diving into AI.**

But the objective should be:

**“prove the current architecture satisfies the needed parts of the SPEC and identify only real missing contracts/wiring”**

—not:

**“implement the SPEC.”**

After that, I would freeze the execution/core architecture and move almost entirely upward into the **AI research → experiment → validation → promotion → outcome → learning loop**, because that is now the largest gap between your current system and a genuinely systemic AI edge desk. The README itself says the current AI can observe and propose, but automatic promotion remains disabled and the model has not yet demonstrated an edge. 

---

One thing I would do during the architecture cleanup is make sure the architecture has a clear place for future promotion:
```
Research Evidence
      ↓
Candidate
      ↓
Evaluation
      ↓
Promotion Decision
      ↓
Authority / deployment
```

You don't need to enable it yet. You only need to make sure the architecture can support it cleanly later without redesigning the execution core.

