**Simple plain-language explanation**  
*(with practical suggestions for a retail options buyer)*

---

### What this file is
This is the short list of things that **need a human decision**.  
Everything else is either already fixed, already decided, or just normal work.

---

### Item 1 – The signal has negative edge (and the AI does not fix it)

**In simple words**  
Both the normal rule and the AI model are **losing** compared with a very simple baseline.  
The AI is better than the rule, but it is still negative.  
Worse: the AI **never stays quiet**. It always gives a buy/sell direction, even when it has almost no confidence.

This is **not real P&L** yet (no premium, no decay, no stops), but it already shows the signal is weak.

**My suggestion for a retail options buyer**

| Option | What it means | Recommendation |
|--------|---------------|----------------|
| **A. Make the AI abstain more** (best) | Change the prompt so the AI only speaks when it is reasonably confident. Aim for it to answer only ~20% of the bars. | **Strongly recommended**. A selective AI is much safer and cheaper for retail. |
| **B. Try a stronger model** | Switch to a better/faster model. | Possible later, but first fix the “always answers” problem. |
| **C. Accept that pure direction is the wrong goal** | Stop trying to predict up/down and look for other edges (volatility, timing, etc.). | Worth considering long-term, but bigger change. |
| **D. Keep current behaviour** | Continue with a model that always has an opinion. | Not recommended for retail – too many low-quality trades. |

**Extra suggestion**  
Adopt the proposed promotion rule before giving the AI real money authority:
1. Must beat the baseline at every time horizon.
2. Must have at least 30 scored bars per horizon.
3. Must hold for at least two calendar weeks.

This protects you from promoting a lucky one-week result.

---

### Item 2 – Five measured numbers that still need a decision

**In simple words**  
There are five concrete settings that directly affect:
- Whether a trade is allowed
- How big the position is
- Where the stop-loss is placed

The measurements and proposed changes already exist, but nothing has been changed yet (on purpose).

Two earlier problems were already fixed today:
- The allowlist that was blocking almost all NIFTY orders
- The dangerous “stop = 0” case

**Remaining five (explained simply)**

| # | Problem | What it affects | Simple meaning |
|---|---------|-----------------|----------------|
| 1 | Scoring sweep missed two components | Entry scoring | Some votes that should influence entry are currently ignored |
| 2 | ATR trail step is almost always doubled | Stop placement | Trailing stops are usually twice as wide as intended |
| 3 | Spot freshness bound is too tight | Whether any decision is allowed | System sometimes rejects good decisions because data looks “too old” |
| 4 | Trail never gets the entry conviction | Trailing stop behaviour | The trail cannot tighten or loosen based on how strong the original signal was |
| 5 | Two different conviction scales | Position size | Stop distance and position size are calculated on inconsistent scales |
| 6 | EMA crossover thresholds are wrong | Whether the new strategy trades at all | The new EMA strategy currently does almost nothing |

**My suggestions for a retail options buyer**

| Priority | Item | Suggestion | Why |
|----------|------|------------|-----|
| **High** | Spot freshness bound (PART 102) | Raise it so it is comfortably above the poll cadence | Prevents good trades from being blocked for no real reason. Also linked to the 26% data-loss problem seen today. |
| **High** | ATR trail clamp (PART 43) | Review the `0.50` floor – it is doubling the trail on most cycles | Wide trails = bigger losses on options (especially short-dated). |
| **Medium** | Conviction scale mismatch | Make entry SL sizing and conviction use the **same** scale | Inconsistent sizing is dangerous for retail capital. |
| **Medium** | Dead trail adjustment (PART 125) | Make `manage()` pass `entry_conviction` | Lets the trail behave as designed. |
| **Lower** | EMA thresholds | Recalibrate or temporarily disable the strategy | No point keeping a strategy that never fires. |
| **Lower** | Missing scoring components | Add the two missing votes after the higher-priority items | Improves entry quality but is less urgent than stop and sizing issues. |

---

### Bottom-line advice for a retail options buyer

1. **Do not give the AI real-money authority yet** – force it to abstain first and meet the three promotion conditions.
2. **Fix the stop and sizing numbers next** (trail width + conviction scale) – these directly protect your capital.
3. **Raise the freshness bound** – stop rejecting good trades for technical reasons.
4. Keep the two new EMA strategies on `authority: none` (or revert them) until you are fully comfortable with the demonstration.

Would you like me to turn any of these into a short “decision brief” you can approve or reject one-by-one?
