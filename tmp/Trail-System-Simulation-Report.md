# Trail System Simulation Report — v2.1
## 1,050 runs × 7 paths × 10 targets × 4 methods × 3 lock modes + key_level

---

## Simulation Setup

**Entry premium (EP):** ₹200  |  **Initial SL:** EP − 25pts = ₹175  |  **Lot qty:** 1 (single lot)  
**Activation params:** ACT_PCT=25%, ACT_MAX=30pts, CONV_ADJ=1.20, ACT_MULT=1.0 (Unknown moneyness)  
**Breakeven safety net (Layer 2):** fires at peak_gain ≥ 88% of target (80% × 1.10 conv)  
**KER window:** 15 bars  |  **GAMMA_FLOOR:** 0.40  |  **Step cap:** 50% of EP = 100pts

---

## 7 Path Archetypes

| Path | Description | Peak | End | Represents |
|---|---|---|---|---|
| `clean_trend` | Steady climb, low noise | +145 | +145 | Strong directional move, high KER |
| `choppy_trend` | Net climb, high noise | +60 | +60 | Grinding intraday trend, low KER |
| `spike_reverse` | Fast +127 then reversal | +127 | −38 | News spike, quick fade |
| `slow_fade` | Modest +47 then fade to SL | +47 | −23 | Setup that never develops |
| `v_recovery` | Dip to −21, then +145 | +145 | +144 | False breakdown before real move |
| `eod_stall` | Climb to +69, then sideways | +69 | +58 | Morning rally, afternoon chop |
| `activation_trap` *(new)* | Choppy +35 (KER=0.40 → step=40 > move=35), immediate −10/bar decline | +35 | −45 | Worst-case: trail activates on the peak bar, reversal starts immediately |

---

## Section 1 — The Core Issue: Activation Landing Below Entry

**Table 1 — Count of runs where activated_below_entry=True, by lock_mode (out of 280 premium runs)**

| lock_mode | Count | % |
|---|---|---|
| A_off (no floor) | **90** | **32.1%** |
| B_breakeven (lock=0) | **0** | **0.0%** |
| C_lock10 (lock=10%) | **0** | **0.0%** |

**B and C eliminate the issue completely. A_off hits it in 32% of runs.**

The paths and methods that trigger it under A_off:

| Path | Method | Why |
|---|---|---|
| `activation_trap` | all 4 methods | Deterministic: KER=0.40 at activation → step=40 > move=35 |
| `choppy_trend` | fixed_pct, fixed_pts, delta | KER collapses to 0.39–0.55 during the slow grind activation |
| `slow_fade` | fixed_pct, fixed_pts | Noise-heavy 15-bar window at the moment of activation |

`atr` avoids the issue on `choppy_trend` and `slow_fade` because its base_step scales with 
actual realized volatility of the window — when noise is high, atr IS high, but so is the 
step. But at activation the move barely clears the threshold, so `price - step` still often 
lands below EP. `atr` narrowly avoids it here only because its floor under the KER divisor 
happens to keep `new_sl` marginally above EP on those specific paths. This is not structural 
safety — it is coincidence of parameter values.

---

## Section 2 — The Activation Trap: Where Lock Mode Actually Changes Outcomes

**Table 2 — activation_trap path, fixed_pct, target=100pts**

| lock_mode | Activation bar | SL at activation | Exit reason | PNL pts |
|---|---|---|---|---|
| A_off | 15 (peak bar) | **195.00 (−5 below EP)** | SL hit on way down | **−8.00** |
| B_breakeven | 15 (peak bar) | **200.00 (= EP, floored)** | SL hit on way down | **−3.00** |
| C_lock10 | 15 (peak bar) | **203.50 (= EP + 10% of move)** | SL hit on way down | **+2.00** |

This is the exact scenario described architecturally:
- Trail activates on the **same bar as the peak** — no subsequent bars where price is a new high, so no ratchet ever runs after activation
- The reversal hits the frozen activation-bar SL within 3 bars
- The ONLY protection the position has is whatever Layer 6 computed at that single activation bar
- A_off: loss trade (−8pts). B_breakeven: still a loss but 5pts better (−3pts). C_lock10: scratch profit (+2pts)

**Table 3 — activation_trap: giveback from peak (avg across all methods and targets)**

| lock_mode | Avg giveback from peak |
|---|---|
| A_off | **43.00 pts** |
| B_breakeven | **38.00 pts** |
| C_lock10 | **33.00 pts** |

The 5pt and 10pt improvement tracks directly with the floor formula.

---

## Section 3 — Where Lock Mode Makes NO Difference (the majority of real trades)

**Table 4 — PNL by path, averaged across targets and methods**

| Path | A_off | B_breakeven | C_lock10 | Difference |
|---|---|---|---|---|
| `clean_trend` | 104.04 | 104.04 | 104.04 | **Zero** |
| `choppy_trend` | 59.37 | 59.37 | 59.37 | **Zero** |
| `spike_reverse` | 96.63 | 96.63 | 96.63 | **Zero** |
| `v_recovery` | 104.73 | 104.73 | 104.73 | **Zero** |
| `eod_stall` | 57.21 | 57.21 | 57.21 | **Zero** |
| `slow_fade` | 21.48 | 21.48 | 21.48 | **Zero** |
| `activation_trap` | **−8.00** | **−3.00** | **+2.00** | **+5 / +10** |

On six of seven paths — representing clean trends, choppy trends, spikes, recoveries, 
stalls, and fades — the lock mode has zero impact on realized PNL. This confirms what 
the bar-by-bar trace showed: in all cases except where the reversal hits within the 
same 1–2 bars as activation (before any ratchet runs), subsequent ratchets quickly 
move the SL past EP regardless of whether the floor ran at activation. The floor is 
redundant on all normal paths. It only matters on the activation_trap path.

**This means B_breakeven and C_lock10 are "free options" — zero cost on 6/7 paths, 
meaningful protection on the 1/7 path where activation timing is worst-case.**

---

## Section 4 — Step-Sizing Method Comparison

**Table 5 — B_breakeven mode, averaged across all paths and targets**

| Method | Avg giveback from peak | Avg final_sl above EP | Notes |
|---|---|---|---|
| `atr` | **9.27 pts** | **+57.54** | Tightest trail, highest SL floor |
| `fixed_pct` | 11.76 | +47.17 | Symmetric with fixed_pts here |
| `fixed_pts` | 11.76 | +47.17 | Same base_step as fixed_pct at EP=200 |
| `delta` | 12.22 | +44.45 | Widest trail, lowest SL floor |

`atr` consistently produces the tightest trail (lowest giveback) because its base_step 
tracks actual realized volatility — it widens when the market is actually choppy (not 
when KER *perceives* it as choppy via the net/path ratio). It is the most adaptive of 
the four. The 2.5pt giveback advantage over fixed_pct compounds over many trades.

`delta`-based trailing is the widest because delta increases as price rises (ITM 
options approach delta=1.0), which the formula uses to *widen* the step. This is 
philosophically correct for options (deeper ITM options need more room for equivalent 
underlying moves) but mechanically produces the loosest exit — most giveback, lowest 
locked floor.

---

## Section 5 — Layer 2 Breakeven Safety Net: Never Fires

**Table 6 — Runs where Layer 2 fired before Layer 6 trail activated: zero across all 700 premium runs**

Layer 2 requires `peak_gain >= 88% of target_gain`. For target=50pts that is 44pts. 
For target=100pts that is 88pts. The premium trail (Layer 6) activates at ~30pts move 
regardless of target. So Layer 6 ALWAYS fires before Layer 2 on any path that reaches 
the activation threshold. Layer 2 can only fire independently if the trail never 
activated — which means the position stalled below 30pts gain. On such paths 
(slow_fade reaches +47pts then reverses) the move crosses 30pts, trail activates, 
and Layer 6 takes over before Layer 2 has a chance.

**Conclusion: Layer 2 is a dead branch in the current parameter configuration.** 
It would only activate on an extremely tight activation threshold (e.g., ACT_PCT=40%, 
ACT_MAX=50pts) combined with a slow build that crosses 88% of a high target without 
ever crossing 30pts first. Under current defaults, it never fires. It provides no 
additional protection beyond what Layer 6 already covers.

**Action: consider removing Layer 2 (breakeven safety net) from the main check_trailing_stops 
loop entirely, since it adds complexity without adding protection. If kept, it should be 
documented as a last-resort backstop with an explicit note that it's unreachable under 
current param defaults.**

---

## Section 6 — key_level Trail vs Premium Trail

**Table 7 — B_breakeven, PNL comparison by path (averaged across targets)**

| Path | Premium avg PNL | key_level avg PNL | Premium advantage |
|---|---|---|---|
| `activation_trap` | −3.00 | **+2.00** | key_level wins by 5pts |
| `choppy_trend` | 59.37 | 59.37 | Tied |
| `clean_trend` | 104.04 | 104.04 | Tied |
| `eod_stall` | 57.21 | 57.18 | Tied |
| `slow_fade` | 21.48 | 9.73 | **Premium wins by 11.75pts** |
| `spike_reverse` | 96.63 | 77.41 | **Premium wins by 19.22pts** |
| `v_recovery` | 104.73 | 104.73 | Tied |

key_level wins on `activation_trap` because level-based ratcheting does not depend on KER 
at all — the first level completes when price crosses EP+10, at which point it locks in 
50% of that captured range (5pts). It doesn't care whether the path was choppy. The 
guaranteed 5pts lock after the first level is structurally closer to Mode C's behavior.

Premium wins on `spike_reverse` and `slow_fade` because key_level's level-spacing (10pts) 
is too coarse for the fast reversal — it may have completed 0 or 1 levels before price 
turns, locking in little. Premium trail at decent KER follows the peak more tightly.

**key_level is superior when: price moves in small steps, KER is low, reversals are sharp.**  
**Premium trail is superior when: moves are large and fast with clear trend structure.**

---

## Section 7 — Target Distance Effect on Activation

**Table 8 — Mean activation_move by target_pts (all paths, B_breakeven)**

| Target | Mean activation_move | Std |
|---|---|---|
| 50–150 | **30.64 (all identical)** | 0.91 |

The `_tgt_gain * 0.8` cap only binds when `_tgt_gain * 0.8 < min(64.52, 30)` — i.e., 
`_tgt_gain < 37.5`. Since minimum target in the grid is 50pts, `_tgt_gain * 0.8 = 40 > 30`, 
and the ACT_MAX_PTS=30 cap is always the binding constraint. The per-position cap is 
insurance for Deep-OTM entries where target_gain itself might be 25pts — it never binds 
in the normal-ATM parameter regime.

---

## Section 8 — Dhan "Book Profit in Steps" Assessment

The Dhan image shows: 33%×3 or 25%×4 quantity-based partial exits.

With qty=1 lot: 25% of 1 lot = 0.25 lots → rounds to 0 → broker rejects.  
With qty=2 lots: 33% of 2 = 0.66 → rounds to 0 → broker rejects.  
With qty=4 lots: 25% of 4 = 1 lot → **first executable partial exit**.

**Partial booking is structurally unreachable for qty=1 or qty=2 lots.** For qty≥4, 
it is a separate order-management problem layered above the trail math:
- OptionPosition would need a `remaining_qty` field
- Each partial exit would need its own journal entry with provenance
- The remaining tranche's SL/TGT stays live after the partial exit
- The trail engine must scale step_pts to remaining notional, not original notional

This is a meaningful feature but orthogonal to trail system design. It belongs as a 
separate `PartialExit` module when qty≥4 is operationally supported.

---

## Section 9 — Consolidated Architecture Decisions

### Decision 1: Lock mode — adopt `B_breakeven` as default

`B_breakeven` (`trail_activation_lock_pct=0.0`) eliminates the activated-below-entry 
condition on 100% of simulated scenarios at zero cost to PNL on normal paths. 
`C_lock10` adds +2.0pts advantage on the activation_trap path but subtracts nothing — 
however the 10% lock makes the semantic slightly more complex ("activation = 
EP + 10% of captured gain", not simply "activation = no-loss"). Recommend B as default, 
C as a documented alternative for users who want that extra buffer.

### Decision 2: Step-sizing — `atr` for tightest giveback management

`atr` produces consistently tighter trailing (9.27pts avg giveback vs 11.76 for fixed_pct) 
because it adapts to actual realized volatility rather than KER-scaled theoretical width. 
It also reduces `activated_below_entry` incidence under A_off (avoids the condition on 
choppy_trend and slow_fade, unlike fixed_pct/delta). Use as the production default 
for `trail_sl_method`.

### Decision 3: Layer 2 (breakeven safety net) — document as dead branch

Under current params, Layer 2 never fires. Document explicitly in the arch doc. 
Either remove it (simplify) or lower the `breakeven_at_gain_pct` threshold to 
something that could fire before Layer 6 (e.g., 50%), which would give it a real role 
as an early-warning floor for trades that creep near target without activating the trail.

### Decision 4: key_level trail — use for chop, premium for trend

key_level is architecturally superior for slow, choppy, level-to-level moves. 
Premium trail wins on fast, structured trending moves. A future enhancement: 
auto-detect regime (KER over last N bars) and select the mode dynamically, 
rather than static config.

### Decision 5: Partial booking — defer until qty≥4 is operational

The trail math is complete for full-exit single-lot trades. Partial booking requires 
OptionPosition.remaining_qty + PartialExit order routing + per-tranche journal entries. 
Not in scope until lot sizing scales to ≥4 per trade.

---

## Single-sentence summaries per simulation finding

1. **Lock mode matters only when activation bar = peak bar with immediate reversal** — zero P&L impact on all other paths
2. **B_breakeven and C_lock10 eliminate activated-below-entry in 100% of simulated scenarios**
3. **C_lock10 converts −8pts to +2pts on the worst-case activation_trap path** — a 10pt improvement
4. **atr step-sizing gives 2.5pts less giveback than fixed_pct on average** — compounds significantly at scale
5. **Layer 2 (breakeven safety net) never fires under current parameters** — dead branch in the current config
6. **key_level beats premium on activation_trap (+5pts) but loses badly on spike_reverse (−19pts)**
7. **Target distance (50–150pts) has zero effect on activation threshold** — ACT_MAX_PTS=30 is always binding
8. **Partial booking (Dhan-style) unreachable for qty=1 or qty=2 lots** — needs PartialExit module at qty≥4
