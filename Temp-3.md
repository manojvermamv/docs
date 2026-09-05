# Turn 1

### Prompt
> Built In Framework (Risk & Reward, Guards , SL, TP, Trail, multi leg ) + Strategy Work - Check the openalgo upstream mirror (update from upstream first) at route strategy/new/ in deep how, we also have built-in framework system to applies by default on each strategies, but can fully managable as like openalgo upstream & even more advanced because our project have too much more potential/power from 'opealgo', First Research & Review our-self With our repo Ai + Strategy than plan & implementation  everything end to end for end-users.

### Response
OpenAlgo is updated to upstream d043d8e. The review proves our framework already owns the stronger deterministic execution foundation, but configurable per-strategy risk and true multi-leg lifecycle are not wired end to end yet.

Area	Current state

SL, target, sizing, guards	Implemented in our planner
Trailing stop	Implemented, broker-modifiable, replayable
Protective basket	One entry with SL/target children
True multi-leg strategy	Missing as a canonical intent/position lifecycle
Strategy profiles	Versioned, but arbitrary and unvalidated
Runtime policy wiring	Missing: live planning still uses global defaults
AI boundary	Correct: AI returns a directional view; framework controls money
End-user control	Lifecycle exists; risk configuration is read-only/incomplete


OpenAlgo’s /strategy/new supplies useful configuration concepts—legs, per-leg SL/target/trailing, aggregate MTM limits, profit locking, schedules, and lifecycle management—but its strategy runtime must not be copied into ours. That would create a second planner, risk engine, position book, and reconciliation authority. Relevant source: strategy validator, risk adapter, and runtime engine.

The central defect is visible in run_framework_live.py: every plan creates its Desk from global defaults instead of the strategy’s bound profile. Meanwhile session_config.py binds only the version identity. Thus a staged risk setting can be recorded without controlling runtime behaviour.

One scope decision is required before I design and implement the contract:

Should “multi-leg” mean real coordinated option structures with multiple executable entry legs, including optional short legs, or only the existing single option entry plus SL/TP protective orders?

I recommend real coordinated structures, with short-leg live authority remaining fail-closed until margin, hedge sequencing, partial-fill, and orphan-leg protection pass replay and OpenAlgo validation.

---

# Turn 2

### Prompt
> Yes your recommendation is my decision, we should “multi-leg” mean real coordinated option structures with multiple executable entry legs, including optional short legs

### Response
For multi-leg authoring, should each strategy’s versioned profile predeclare its allowed structures, with strategy/AI selecting only a structure name, direction, and conviction?

Recommended example:

Strategy profile:
  bullish_debit_spread:
    BUY  CE ATM
    SELL CE ATM+100
    max_loss, target, trail, expiry rules

AI/strategy output:
  structure = bullish_debit_spread
  conviction = 0.72

The deterministic framework would resolve contracts, quantities, margin, sequencing, protection, and exits. This keeps AI unable to invent legs or unbounded exposure.

The alternative is allowing strategy code to emit an arbitrary leg list on each decision, which is more flexible but materially harder to validate, replay, and govern.

---


# Turn 3

### Prompt
> Yes go with ai usable way, but include the all end-users adjustments features/system what exposed for frontend in future...

### Response
Three implementation approaches fit the decision:

1. Versioned strategy policy contract — recommended

Each strategy references a validated StrategyPolicy containing:

Allowed named structures and legs

Buyer/seller classification

Strike, expiry and DTE rules

Sizing and capital allocation

Per-leg SL, target and trailing rules

Structure-level risk/reward and MTM limits

Margin, hedge and maximum-loss requirements

Entry sequencing and partial-fill recovery

Session guards and square-off policy

Required market evidence

Authority and activation boundaries


AI or deterministic strategy selects a named structure. The framework resolves and executes it. One machine-readable schema exposes every adjustment to CLI, MCP, owner API, replay, and a future frontend.


2. Extend every StrategySpec/WorkerSpec directly

Simpler initially, but static source declarations and runtime adjustments become mixed. Editing risk settings would effectively mean editing strategy code, making versioning, activation, rollback, and frontend support awkward.


3. Use OpenAlgo’s strategy module as the configuration/runtime owner

Fastest path to a browser form, but it creates competing planners, risk engines, position books, and lifecycle records. It would weaken our attribution and shared live/replay contracts.



I recommend approach 1. The resulting boundary is:

End user / AI proposal
          ↓
Versioned StrategyPolicy
          ↓
Named structure selection
          ↓
Deterministic leg resolution
          ↓
Margin + risk + evidence guards
          ↓
Coordinated execution FSM
          ↓
OpenAlgo basket/order APIs
          ↓
Broker
          ↓
Leg + structure reconciliation

The future frontend will consume the same schema and capability APIs; no separate frontend-specific risk rules will exist.

Approve approach 1 as the architecture basis?

---

# Turn 4

### Prompt
> I Approved the approach 1

### Response
Architecture section 1: one versioned StrategyPolicy becomes the authoritative configuration for both deterministic and AI strategies.

Strategy code / AI
       ↓
Intent(structure_id, direction, conviction)
       ↓
Session-bound StrategyPolicy
       ↓
Deterministic StructurePlan

Core contracts:

StrategyPolicy

Schema version and strategy identity

Supported strategy family

Named structure templates

Capital, risk, evidence and execution policies

Immutable version, digest, author, reason and evidence


StructureTemplate

Stable ID and description

Allowed direction

One or more LegTemplate records

Defined/undefined-risk classification

Aggregate protection and exit rules


LegTemplate

BUY or SELL position role

CE/PE, strike-selection rule, expiry/DTE rule

Ratio or lots

Per-leg SL, target and trail

Hedge/entry/adjustment/exit role


Intent

Adds only structure_id

It never contains arbitrary symbols, strikes, quantities, prices, stops, or legs


StructurePlan

Contains fully resolved executable legs

Records every gate and refusal

Carries policy version, market evidence, AI lineage and deterministic identity



Existing single-option strategies automatically use a built-in single_long_option structure, preserving current behaviour.

Important ownership boundaries:

Registry authority remains separately managed as none, plan, or trade.

Strategy policy cannot grant itself execution authority.

AI may select only a structure allowed by the active policy.

AI may propose policy changes, but cannot activate them.

Session binding stores the complete validated policy version and digest.

Live and replay resolve the same policy and produce the same intent, plan, lifecycle, and outcome contracts.


The existing arbitrary profile storage remains the version store, but values become schema-validated and the live/replay planners must consume the bound version. This closes the current “recorded but not applied” configuration defect.

Approve this contract and ownership section?
