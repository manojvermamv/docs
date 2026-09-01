I think the AI agent is being too manual here.

### Why the agent asks for this every day

The receipt is basically a **daily safety acknowledgment**:

> “Before today's strategy starts, verify the account state and confirm today's configured limits are based on current facts.”

It checks:

```text
capital
+ P&L
+ exposure
+ broker state
+ session limits
        ↓
daily receipt
        ↓
strategy allowed to start
```

It exists because those values can change from one session to another, and the system does not want yesterday's approval silently reused.

Also, it is **not an order approval**. It is a check that the strategy's daily operating assumptions are still valid.

### But the current implementation is unnecessarily manual

The current model is:

```text
Every day
   ↓
Human reviews
   ↓
runs governance_evidence.py manually
   ↓
strategy starts
```

For a real autonomous desk, this should become:

```text
Session start
      ↓
Auto-read current capital/P&L/exposure/broker state/config
      ↓
Validate against configured rules
      ↓
Generate signed/recorded receipt automatically
      ↓
Strategy starts
```

Then:

```text
Anything changed?
   YES → invalidate receipt → re-check
   NO  → existing receipt remains valid for this session
```

That is much better than asking a human to manually run a command every morning.

### The important distinction

I would **not remove the safety check**.

I would remove only the **manual ceremony**.

So the desired behavior is:

```text
MANUAL TODAY
human must create receipt

TARGET
system creates receipt automatically
          ↓
if checks pass → READY
if checks fail → BLOCKED
```

The human should only be required when the system detects something that genuinely needs judgment, such as:

```text
capital changed unexpectedly
broker position mismatch
risk limit changed
P&L state abnormal
configuration changed
data unavailable
```

### Best architecture

I'd make it **session-scoped**, not simply “expires every 24 hours.”

```text
New session
    ↓
governance check
    ↓
receipt(session_id, strategy, config_hash, broker_state_hash, reviewed_at)
    ↓
START
```

And invalidate it when material inputs change:

```text
capital changed        ┐
P&L state changed       │
exposure changed        ├──→ receipt invalid
broker state changed    │
risk/session caps changed
                        ┘
```

This is more precise than a blunt daily expiration.

### Bottom line

**Keep the governance concept. Automate the receipt generation and validation.**

The ideal rule is:

> **The strategy must prove its current operating state is valid before starting; a human should not have to manually produce that proof every day when the system can verify it itself.**

That would be a meaningful improvement toward your autonomous-desk goal without weakening the safety boundary.
