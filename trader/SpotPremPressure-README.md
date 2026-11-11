I re-read your current [`SpotPremPressure.pine`](c:\Users\Manoj\OneDrive\Desktop\Trader\pinescripts\SpotPremPressure.pine). Right now it is a good first-layer dominance model:

- It measures each leg relative to `spot` using premium mean, z-score, and ROC at [`SpotPremPressure.pine:12`](c:\Users\Manoj\OneDrive\Desktop\Trader\pinescripts\SpotPremPressure.pine#L12).
- It converts that into side scores:
  - bull side = `CE strength + PE weakness`
  - bear side = `PE strength + CE weakness`
  at [`SpotPremPressure.pine:47`](c:\Users\Manoj\OneDrive\Desktop\Trader\pinescripts\SpotPremPressure.pine#L47).
- So the current script is already a directional pressure/dominance detector, not yet a clean buyer-only execution-quality filter.

Your two new functions are useful because they answer a different question:

- `meanPremiumStrength()` asks: which side is expanding more efficiently?
- `meanPremiumMelt()` asks: which side is being structurally decayed/trapped?

That is exactly why they should not replace the current logic. They should sit on top of it as regime filters.

**Best mental model**
Use 3 layers:

1. `Pressure`
   Current script.
   Tells us which side is dominant relative to spot-premium behavior.

2. `Strength`
   Your `meanPremiumStrength()`.
   Tells us whether that dominance is actually translating into premium expansion that benefits a buyer.

3. `Melt`
   Your `meanPremiumMelt()`.
   Tells us whether one side is being harvested in compression / failed move conditions.

For a retail option buyer, `Strength` is pro-entry and `Melt` is mostly anti-entry / trap-detection.

**Most correct way to integrate**
I’d suggest these 4 implementation paths.

1. **Separate Regime Overlay**
   Keep current `bullPressure` / `bearPressure` untouched.
   Add:
   - `strengthBias > threshold` = CE expansion regime
   - `strengthBias < -threshold` = PE expansion regime
   - `meltBias > threshold` = CE trap / CE decay regime
   - `meltBias < -threshold` = PE trap / PE decay regime

   Then show 3 outputs:
   - `Pressure`: current directional side
   - `Expansion`: buyer-friendly or not
   - `Trap`: avoid or fade

   This is the cleanest first step because it lets you visually study interaction before combining them.

2. **Buyer-Only Confirmation Filter**
   Use current pressure only as setup, then allow a buyer signal only if strength agrees and melt does not oppose.

   Example logic:
   - CE buy candidate:
     - `bullPressure == true`
     - `meanPremiumStrength > +x`
     - `meanPremiumMelt <= smallPositiveLimit`
   - PE buy candidate:
     - `bearPressure == true`
     - `meanPremiumStrength < -x`
     - `meanPremiumMelt >= smallNegativeLimit`

   Meaning:
   - pressure says direction
   - strength says premiums are actually expanding
   - melt says don’t buy into a trap/compression harvest

   This is probably the best retail-buyer implementation.

3. **Composite Score**
   Build one final score per side instead of boolean filters.

   Example idea:
   - `finalBullScore = currentBullPressureScore + strengthComponent - meltPenalty`
   - `finalBearScore = currentBearPressureScore + bearStrengthComponent - bearMeltPenalty`

   Mapping:
   - positive `meanPremiumStrength` helps bull side
   - negative `meanPremiumStrength` helps bear side
   - positive `meanPremiumMelt` penalizes CE-buy quality
   - negative `meanPremiumMelt` penalizes PE-buy quality

   This gives smoother ranking, but it is harder to tune and easier to overfit.

4. **State Machine**
   This is the most advanced and likely the most robust.

   States:
   - `Compression`
   - `Expansion Bull`
   - `Expansion Bear`
   - `Bull Trap`
   - `Bear Trap`
   - `Neutral`

   Example:
   - `bullPressure + positive strength + low melt against CE` => `Expansion Bull`
   - `bullPressure but weak strength + positive CE melt` => `Bull Trap`
   - `bearPressure + negative strength + low melt against PE` => `Expansion Bear`
   - `bearPressure but weak strength + negative PE melt` => `Bear Trap`

   This fits your comment very well: the new functions are noisy in consolidation, but powerful when used to classify regime.

**What I would not do**
I would not directly mix `meanPremiumStrength()` and `meanPremiumMelt()` into the base `premiumStats()` formula yet. They are slower, more structural signals. Your current pressure engine is a fast local detector; the new functions are better as higher-level confirmation.

**How to handle the “noise in consolidation” problem**
This is the key part. Before using `Strength` or `Melt`, gate them with a non-consolidation filter.

Good gating ideas:
- only evaluate them when `abs(pressureSpread)` is above a threshold
- only evaluate them when one side z-score is stretched enough
- only evaluate them when premium range/ATR is expanding
- only evaluate them when CE and PE are diverging, not both flat
- only evaluate when current bar premium displacement exceeds rolling premium volatility

Very practical version:
- `regimeActive = abs(pressureSpread) > spreadThreshold and (abs(ceRoc) + abs(peRoc)) > rocThreshold`

Then:
- if `regimeActive == false`, treat strength/melt as informational only
- if `regimeActive == true`, allow them to influence signals

**Best combined design for retail buyers**
If the goal is “buyers profit only when premium moves up”, then the strongest framework is:

- Current script = directional setup
- `meanPremiumStrength()` = must-confirm entry quality
- `meanPremiumMelt()` = block low-quality / trap entries
- Add a `regimeActive` filter so these only matter during displacement, not consolidation

That gives:

- CE Buy:
  - bull pressure
  - positive strength bias
  - no strong CE melt trap
  - regime active

- PE Buy:
  - bear pressure
  - negative strength bias
  - no strong PE melt trap
  - regime active

**Best way to introduce it gradually**
1. Add `Strength` and `Melt` as separate hidden plots first.
2. Add regime labels only, no signal logic.
3. Add filter-only mode:
   - “confirm current pressure”
   - “block current pressure”
4. Only after visual testing, build composite or state machine.

My recommendation:
Start with `Separate Regime Overlay` plus `Buyer-Only Confirmation Filter`. That will give the most signal improvement with the least confusion.

If you want, next I can design the exact logic table for:
- `current-only`
- `current + strength`
- `current + melt`
- `current + strength + melt`
- `state-machine mode`

without coding yet, so we can choose the cleanest architecture first.
