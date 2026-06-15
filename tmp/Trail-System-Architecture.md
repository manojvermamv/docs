# Trail System Architecture v2.1

## Changelog from v2

v2 established the layer separation and the fixed `max(new_sl, ep)` activation
floor (Invariant 1). v2.1 generalizes that floor into a single tunable parameter,
`trail_activation_lock_pct`, spanning "off" (legacy, no floor), "breakeven"
(v2's behavior, `lock_pct=0`), and "partial profit lock" (`lock_pct>0`) as one
continuous knob instead of three discrete modes. No layer boundaries change —
the generalization is entirely inside Layer 6.

## Design principle

Separate **when** (activation timing), **how wide** (step sizing), and **what guarantee**
(invariant enforcement) into independent layers. No layer's formula may reference
another layer's output in a way that creates a contradiction. Where two layers must
interact, the interaction happens through the *result* of one layer feeding the
*enforcement* of another — never through one layer's *threshold* depending on the
other's *threshold*.

This is the architectural lesson from the live trade (`NIFTY23JUN2623600CE`,
12-Jun-2026): `activate_pts` and `step_pts` come from genuinely different questions
("has this moved enough to bother?" vs "how wide should the stop be given current
trend quality?"). Forcing a relationship between the two thresholds (`activate_pts
>= step_pts`) breaks under exactly the conditions where protection matters most —
when KER collapses, `step_pts` can widen faster than `move` grows, and a threshold-
level coupling would defer activation indefinitely. The fix lives at the *output*
level instead.

---

## Layer stack

Executed in this order, every `check_trailing_stops` cycle, per position.

### Layer 0 — Snapshot read (unchanged)

- `confirmed_close = snapshot_cache.get(underlying).option_ltp`
- `spot_ltp` for spot-mode positions
- Skip entirely if `not snap.has_both_prices`

### Layer 1 — Peak tracking (unchanged, unconditional)

```python
prior_peak = pos.trail_peak_close if pos.trail_peak_close is not None else pos.entry_premium
is_new_high = confirmed_close > prior_peak
if is_new_high:
    pos.trail_peak_close = confirmed_close
```

Runs every cycle regardless of trail state. Peak tracking is pure observation —
never gated by activation or mode.

### Layer 2 — Breakeven safety net (unchanged, mode-independent)

Runs every cycle while `not pos.breakeven_moved`:

```python
_be_conv_adj   = CONV_BE_BASE - pos.entry_conviction * CONV_BE_RANGE
_be_trigger    = (cfg.breakeven_at_gain_pct / 100.0) * _be_conv_adj
target_gain    = pos.tgt - ep
gain_pts       = (pos.trail_peak_close or ep) - ep

if target_gain > 0 and gain_pts >= target_gain * _be_trigger and ep > pos.sl:
    # broker-confirm modify(ep) -> pos.sl = ep, pos.breakeven_moved = True
```

This is a **coarse backstop**, not the primary breakeven mechanism. With the
default `breakeven_at_gain_pct=80` and `CONV_BE_BASE=1.10`, it fires at 88% of
target gain — late enough that fast moves can jump past it between scan cycles
(exactly what happened in the live trade: peak reached 78.1% of target gain,
needed 88%, then jumped straight to target fill). Layer 6's activation floor
(below) provides the precise, early guarantee that this layer can't.

### Layer 3 — Mode dispatch (unchanged)

- `key_level` → exclusive path, own internal breakeven + ratchet, ephemeral state
- `premium` (default) → Layers 4–6 below
- `spot` → simpler spot-distance ratchet, no Gamma Speed-X step sizing

Everything below describes the `premium` path.

### Layer 4 — Activation gate (TIMING ONLY)

**Question: has this position moved enough that we should start actively managing
the stop?**

```python
activate_pts = ep * (cfg.trail_activate_at_pct / 100.0) * conv_adj * pos.trail_act_mult
activate_pts = min(activate_pts, cfg.trail_activate_at_max_pts)   # global ceiling (30pts default)

_tgt_gain = pos.tgt - ep
if _tgt_gain > 0:
    activate_pts = min(activate_pts, _tgt_gain * 0.8)             # per-position ceiling

if not pos.premium_trail_active and move < activate_pts:
    return   # too early
```

**Invariant:** this formula is a pure function of `(ep, conviction, moneyness,
target_gain)` — all known at entry time, all stable. It never references
`step_pts`, KER, or trend efficiency. It answers *when*, never *how much*.

The `_tgt_gain * 0.8` ceiling is what makes activation reachable for every
moneyness bucket (it was previously possible for `activate_pts` to exceed the
target's own gain on Deep-OTM entries — see "Issue 1" below).

### Layer 5 — Step sizing (WIDTH ONLY, Gamma Speed-X)

**Question: given current trend quality, how wide should the trailing distance
be?**

```python
base_step   = ep * (cfg.trail_step_pct / 100.0)
trail_speed = tier_speed(roi_pct) * KER_factor(option_candles)
step_pts    = clamp(base_step / trail_speed,
                     floor=base_step * GAMMA_SPEED_STEP_FLOOR,
                     ceil=ep * 0.5)
```

**Invariant:** this formula never references `activate_pts` or
`pos.premium_trail_active`. It answers *how wide*, never *when*. It can be —
and routinely is — larger than `activate_pts`. That's expected and handled by
Layer 6, not prevented here.

### Layer 6 — Ratchet execution (GUARANTEE ENFORCEMENT)

**Question: what SL value results, and does it satisfy the invariants?**

This is the *only* layer where Layer 4's gate and Layer 5's width interact —
through the computed `new_sl`, never through their thresholds.

```python
new_sl = confirmed_close - step_pts

if not pos.premium_trail_active:
    # ACTIVATION — first ratchet
    new_sl = max(new_sl, ep)              # Invariant 1: never activate below cost
    if new_sl > pos.sl:
        broker_ok = modify_callback(...) if broker_sl_orders else True   # Invariant 3
        if broker_ok:
            pos.premium_trail_active = True
            pos.sl = new_sl
        # else: retry next cycle, flag stays False
    # else: not yet beneficial, retry next cycle

else:
    # RATCHET — subsequent new highs
    if is_new_high and new_sl > pos.sl:   # Invariant 2: monotonic
        broker_ok = modify_callback(...) if broker_sl_orders else True
        if broker_ok:
            pos.sl = new_sl
        # else: retry next cycle
```

---

## The three invariants, stated precisely

1. **Activation guarantee** — `pos.premium_trail_active == True` implies
   `pos.sl >= ep` at all times, regardless of market conditions. Enforced by
   `max(new_sl, ep)` in the activation branch of Layer 6. Independent of how
   Layers 4 and 5 relate to each other.

2. **Monotonicity guarantee** — `pos.sl` never decreases. Enforced by the
   `new_sl > pos.sl` check, present in both branches. This is the existing
   one-directional ratchet, unchanged. It also makes Invariant 1 self-sustaining:
   once `pos.sl >= ep`, every future `pos.sl` is `>= ep` too, so no per-cycle
   floor is needed after activation.

3. **Broker-truth guarantee** — local `pos.sl` only advances after the broker
   confirms the modify, and `pos.premium_trail_active` flips to `True` in the
   same gated step as `pos.sl`'s first advance. State and flag move together,
   gated on `broker_ok`.

None of these three requires `activate_pts` and `step_pts` to be related. Each is
enforced where state actually *changes* (Layer 6), not where eligibility is
*checked* (Layer 4) or width is *computed* (Layer 5).

---

## Why this composition is robust

- **Layer 4 is tunable in isolation.** Conviction curves, moneyness multipliers,
  target-relative caps — none of it touches Layer 5.
- **Layer 5 is tunable in isolation.** KER weighting, ROI tiers, floor/ceiling —
  none of it touches Layer 4.
- **New step-sizing modes are free.** A future "IV-based" step only needs a new
  Layer 5 formula. Layer 6's guarantees apply automatically — no new invariant
  code per mode.
- **The pathological case is absorbed, not special-cased.** KER collapsing
  exactly when `move` crosses `activate_pts` (the live trade) is handled by
  `max(new_sl, ep)` in Layer 6. Layer 4 never needs to "know" that KER exists.

---

## Consolidated implementation

`_process_premium_trail`, with Issue 1 (`_tgt_gain` cap), Issue 2 (broker-confirm
before flag), and the new activation floor (`max(new_sl, ep)`) integrated. Also adds
symmetric `BLOCKED` / `not yet beneficial` / `step too wide` debug logging to the
ratchet branch, mirroring what the activation branch already has — so every
non-advance has a visible reason in the logs.

```python
def _process_premium_trail(
    self,
    underlying: str,
    pos: OptionPosition,
    confirmed_close: float,
    conv_adj: float,
    is_new_confirmed_close_high: bool,
) -> None:
    cfg = self._config
    ep = pos.entry_premium
    move = confirmed_close - ep
    ltp = confirmed_close

    # ── Layer 4: Activation gate (timing only) ─────────────────────────────
    activate_pts = ep * (cfg.trail_activate_at_pct / 100.0) * conv_adj * pos.trail_act_mult
    if cfg.trail_activate_at_max_pts > 0:
        activate_pts = min(activate_pts, cfg.trail_activate_at_max_pts)

    # Issue 1 fix: never require more than 80% of this position's own target gain.
    # Self-scales per moneyness bucket — removes the Deep-OTM activation/target conflict.
    _tgt_gain = pos.tgt - ep
    if _tgt_gain > 0:
        activate_pts = min(activate_pts, _tgt_gain * 0.8)

    if not pos.premium_trail_active and move < activate_pts:
        return  # not activated yet

    # ── Layer 5: Step sizing (width only, Gamma Speed-X) ────────────────────
    current_delta = None
    df = None
    if cfg.trail_sl_method == "delta":
        greeks = self._fetcher._fetch_option_greeks_cached(underlying, pos.symbol)
        if greeks and "delta" in greeks:
            current_delta = greeks["delta"]
    elif cfg.trail_sl_method == "atr":
        df = self._fetcher.fetch_option_candles(pos.symbol)

    _base_step_pts = self._get_step_pts(pos, ep, df, current_delta)

    _roi_pct = ((confirmed_close - ep) / ep * 100.0) if ep > 0 else 0.0
    if _roi_pct >= 150:
        _trail_speed, _gamma_tier = 2.5, "TIER_3_150PLUS"
    elif _roi_pct >= 100:
        _trail_speed, _gamma_tier = 2.0, "TIER_2_100_150"
    elif _roi_pct >= 50:
        _trail_speed, _gamma_tier = 1.5, "TIER_1_50_100"
    else:
        _trail_speed, _gamma_tier = 1.0, "TIER_0_0_50"

    if df is None:
        df = self._fetcher.fetch_option_candles(pos.symbol)

    trend_efficiency = 1.0
    _net_move = 0.0
    _path_length = 0.0
    if df is not None and not df.empty:
        if isinstance(df.index, pd.DatetimeIndex):
            today_date = get_ist_now().date()
            df_today_opt = df[df.index.normalize() == pd.Timestamp(today_date)]
            recent = df_today_opt.tail(15) if len(df_today_opt) >= 2 else df.tail(15)
        else:
            recent = df.tail(15)
        if len(recent) > 1:
            closes = recent["close"].values
            _net_move = abs(closes[-1] - closes[0])
            _path_length = sum(abs(closes[i] - closes[i-1]) for i in range(1, len(closes)))
            if _path_length > 0:
                trend_efficiency = _net_move / _path_length

    trend_efficiency_factor = max(0.50, min(1.0, trend_efficiency))
    _trail_speed *= trend_efficiency_factor

    step_pts = max(_base_step_pts * GAMMA_SPEED_STEP_FLOOR, _base_step_pts / max(0.1, _trail_speed))
    step_pts = min(step_pts, ep * 0.50)

    # ── Logging (unchanged) ──────────────────────────────────────────────
    _unrealized_pnl_pts = confirmed_close - ep
    _unrealized_pnl_pct = (_unrealized_pnl_pts / ep * 100.0) if ep > 0 else 0.0
    _unrealized_pnl_abs = _unrealized_pnl_pts * pos.qty
    inf(
        f"[TRAIL] {underlying} | ROI={_roi_pct:.1f}% ({_gamma_tier}) | "
        f"KER={trend_efficiency:.3f} (net={_net_move:.2f}/path={_path_length:.2f}) → "
        f"KER_factor={trend_efficiency_factor:.3f} | "
        f"Speed={_trail_speed:.2f}x | BaseStep={_base_step_pts:.2f} → "
        f"FinalStep={step_pts:.2f} | Cap={ep*0.50:.2f} | "
        f"UnrealPnL={_unrealized_pnl_pts:.2f}pts ({_unrealized_pnl_pct:.1f}%) "
        f"\u20b9{_unrealized_pnl_abs:.0f} | "
        f"PeakClose={pos.trail_peak_close:.2f} | LTP={confirmed_close:.2f}"
    )

    # ── Layer 6: Ratchet execution (invariant enforcement) ──────────────────
    if not pos.premium_trail_active:
        new_sl = confirmed_close - step_pts

        # Invariant 1: activation always guarantees at-least-breakeven.
        new_sl = max(new_sl, ep)

        if new_sl > pos.sl:
            _broker_ok = True
            if cfg.broker_sl_orders and pos.sl_order_id and self.modify_callback:
                _broker_ok = self.modify_callback(underlying, new_sl)   # Invariant 3
            if _broker_ok:
                pos.premium_trail_active = True
                pos.premium_trail_peak = pos.trail_peak_close
                pos.premium_trail_sl = new_sl
                pos.sl = new_sl
                inf(f"[TRAIL] Premium ACTIVATED {underlying}: peak {ltp:.2f} SL\u2192{new_sl:.2f} (speed={_trail_speed:.1f}x)")
            else:
                inf(f"[TRAIL] Premium activation BLOCKED {underlying}: broker rejected new_sl={new_sl:.2f} \u2014 retrying next cycle")
        else:
            dbg(f"[TRAIL] {underlying}: new_sl={new_sl:.2f} <= current sl={pos.sl:.2f} \u2014 not yet beneficial, retry next cycle")

    else:
        if is_new_confirmed_close_high:
            pos.premium_trail_peak = pos.trail_peak_close
            new_sl = confirmed_close - step_pts   # Invariant 1 not needed here \u2014
                                                    # pos.sl >= ep already (Invariant 2
                                                    # makes it self-sustaining)
            if new_sl > pos.sl:
                _broker_ok = True
                if cfg.broker_sl_orders and pos.sl_order_id and self.modify_callback:
                    _broker_ok = self.modify_callback(underlying, new_sl)
                if _broker_ok:
                    pos.premium_trail_sl = new_sl
                    pos.sl = new_sl
                    inf(f"[TRAIL] Premium RATCHET {underlying}: peak {ltp:.2f} SL\u2192{new_sl:.2f} (speed={_trail_speed:.1f}x)")
                else:
                    inf(f"[TRAIL] Premium ratchet BLOCKED {underlying}: broker rejected new_sl={new_sl:.2f} \u2014 retrying next cycle")
            else:
                dbg(f"[TRAIL] {underlying}: new high (peak={pos.trail_peak_close:.2f}) but new_sl={new_sl:.2f} <= "
                    f"current sl={pos.sl:.2f} \u2014 step too wide for this move, no ratchet")
```

---

## Mapping the live trade through this architecture

| Layer | Live trade value | Result |
|---|---|---|
| 4. Activation gate | `activate_pts = min(64.52, 30, 40.0) = 30` | fires at move=32.45 |
| 5. Step sizing | `step_pts = 35.81` (KER=0.601) | wider than `move` |
| 6. Activation | `new_sl = max(247.50-35.81, 215.05) = max(211.69, 215.05) = 215.05` | **SL = breakeven**, not 211.69 |
| 6. Next ratchet | peak=254.10, `step_pts=43.01` → `new_sl=211.09` | `211.09 > 215.05`? no → `dbg("step too wide for this move")` |
| Exit | target hit at 268.20 | unchanged — exits at target either way |

With the consolidated version, this trade's worst-case outcome (price reversing
from 254.10) changes from **a small loss at SL=211.69** to **a breakeven exit at
SL=215.05** — the floor holds regardless of how KER behaves afterward, because
Invariant 2 keeps it pinned at-or-above `ep` for the rest of the trade's life.

---

## Simulation-Validated Decisions (from v2.1 simulation report)

The following conclusions are derived from 1,050 simulation runs across 7 premium
path archetypes, 10 target levels, 4 step-sizing methods, and 3 lock modes. All
numbers are for EP=₹200, Initial SL=EP−25pts, single-lot position.

### SIM-1: Lock mode recommendation — B_breakeven as default

`trail_activation_lock_pct=0.0` (Mode B) eliminates the activated-below-entry
condition in 100% of simulated scenarios at zero P&L cost on all normal paths.
Mode C (`lock_pct=0.10`) provides an additional +2pts on the worst-case
activation_trap scenario (converting a −8pt loss under A_off to +2pts), at no
cost elsewhere. Recommend B as default, C as documented user option.

### SIM-2: Step-sizing method recommendation — ATR

`trail_sl_method="atr"` produces 9.27pts avg giveback vs 11.76pts for fixed_pct
across all paths and targets. It adapts to actual realized volatility (not
KER-scaled theoretical width), giving structurally tighter trailing in all regimes.
It also avoids the activated-below-entry condition on choppy_trend and slow_fade
paths where fixed_pct fails.

### SIM-3: Layer 2 (breakeven safety net) — dead branch under current params

Layer 2 fires at `peak_gain >= 88% of target_gain`. Layer 6 fires at `move >= 30pts`.
Since 30pts < 88% of any target ≥50pts, Layer 6 always fires first. Layer 2 never
activates in any of 700 premium simulation runs. Two options:
- Remove Layer 2 to simplify
- Lower its threshold to e.g. 50% of target to give it a real independent role

### SIM-4: key_level vs premium

key_level wins on activation_trap (+5pts) and avoids activated-below-entry entirely
(level-based ratchet doesn't use KER). Premium wins on spike_reverse (+19pts) and
slow_fade (+11.75pts) because it tracks the peak more tightly than the fixed spacing.
Long-term enhancement: auto-select mode based on KER regime detection.

### SIM-5: Partial booking

Unreachable for qty=1 or qty=2 lots (25%/33% rounds to 0). In scope only when
qty >= 4 per trade, requiring a separate PartialExit module with per-tranche
journal entries and remaining_qty tracking in OptionPosition. Orthogonal to trail
math — defer.


These sit at Layer 3 as sibling dispatch branches, not as variations of Layers
4–6:

- **`_process_spot_trail`** — purely local, no broker modify in the activation
  sense described here (spot trail moves `pos.trail_sl_spot`, a WS-side trigger
  for `_check_spot_trail`, not the broker SL-M order). Issue 2 / broker-confirm
  doesn't apply. If a future revision adds broker-side spot-trail protection,
  the same three-invariant pattern from Layer 6 applies directly.

- **`_process_key_level_trail`** — has its own breakeven (`kl_levels_completed`
  count) and its own one-directional ratchet (`new_sl > pos.sl`), already
  satisfying Invariant 2. It does not currently have an equivalent to Invariant 1
  (no `max(new_sl, ep)` floor on its first ratchet after `kl_levels_completed`
  reaches the breakeven threshold) — worth a follow-up pass using the same
  pattern if key_level sees live use.
