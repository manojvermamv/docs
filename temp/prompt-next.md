## Fix Specs — All 🔴 OPEN Findings

Minimal-description format per finding: **Where / What / Why / Alternative**.

---

### F-08 — EntryConfig indicator periods unvalidated
- **Where:** `EntryConfig.validate()`, ~L757-811
- **What:** Add `if self.fast_ema_period < 1 or self.slow_ema_period < 1 or self.rsi_period < 1: errs.append(...)`; add `if self.fast_ema_period >= self.slow_ema_period: errs.append(...)`
- **Why:** Prevents an inverted or zero-period indicator config from running silently — fails fast at startup instead of producing a nonsensical trend signal for the whole session
- **Alternative:** If you don't want a hard reject (e.g. some exotic strategy variant legitimately wants fast≥slow), downgrade to a `warn()` log at startup instead of an `errs.append()` — keeps it non-blocking but visible

---

### F-09 — EntryConfig liquidity/reward fields unvalidated
- **Where:** `EntryConfig.validate()`, same method
- **What:** Add `>= 0` checks for `min_oi_filter`, `min_vol_filter`, `spot_reward_pct`
- **Why:** Negative values silently make filters permissive rather than restrictive — opposite of intended effect, no crash so it's easy to miss in testing
- **Alternative:** Since these aren't dangerous (just permissive, not crash-inducing), lowest-effort fix is a single shared helper `_non_negative(name, val, errs)` called for all three plus the similar fields in F-11, rather than three separate inline checks

---

### F-10 — TrailConfig: 9 fields unvalidated
- **Where:** `TrailConfig.validate()`, ~L940-962
- **What:** Add `> 0` checks for `atr_period`, `atr_mult`, `step_pts`, `step_pct`, `delta_itm_step_pct`, `delta_atm_step_pct`, `delta_otm_step_pct`; `>= 0` for `activate_at_pct`, `activate_at_max_pts`
- **Why:** `step_pts<=0` breaks the ratchet direction/no-op guarantee; `atr_period<=0` reaches `ta.atr()` ungated (behavior unverified against the `ta` library, but definitely not intended)
- **Alternative:** This is the one I'd prioritize actually *testing* post-fix rather than just adding checks blind — feed `atr_period=0` through in a dry run and confirm `validate()` catches it before the trail engine ever sees it, since I couldn't verify the `ta` library's failure mode myself

---

### F-11 — TrancheConfig `min_qty_per_tranche` unvalidated
- **Where:** `TrancheConfig.validate()`, ~L1062-1077
- **What:** `if self.min_qty_per_tranche < 1: errs.append(...)`
- **Why:** Feeds directly into the single-tranche collapse threshold (`_min_required` in `_build_tranches`) — a bad value could silently disable the collapse safety net
- **Alternative:** None needed — this one's unambiguous, just add the check

---

### F-12 — `exit_queue` race in `_cleanup_stale_positions`
- **Where:** `_cleanup_stale_positions`, L6985
- **What:** Wrap the discard: `with self.state.exit_lock: self.state.exit_queue.discard(pos.slot_id)`
- **Why:** Matches the lock discipline used at every other `exit_queue` mutation site; closes the cross-thread race with `_finalize_exit` (confirmed running on the separate exit-executor pool)
- **Alternative:** If you want a stronger guarantee than "same discipline as elsewhere," consider making `exit_queue` a purpose-built thread-safe wrapper class (its own internal lock) instead of a raw `set` guarded by caller discipline — removes the whole class of "forgot to wrap this mutation" bugs, at the cost of a small refactor touching 8 call sites

---

### F-13 — Basket protection bypasses tranche-aware fallback
- **Where:** `_place_protection_basket`, L6062-6153 (call site) + L6148 (gate)
- **What:** Two options, not one — this needs a design decision, not just a patch:
  1. **Gate basket protection off when tranches are active:** `if cfg.broker.use_basket_protection and hasattr(self.client, "basketorder") and not cfg.tranche.enabled:` at the call site (L6063) — falls through to the already-correct tranche-aware sequential path whenever tranches are on.
  2. **Make the basket itself tranche-aware:** loop `pos.open_tranches`, build one SL+LIMIT leg pair per tranche at `tr.qty`/`tr.tp_pts`, submit as one multi-leg basket. More correct, more work, and depends on whether your broker's basket API supports >2 legs cleanly.
- **Why:** Confirmed the basket places a single full-`qty` LIMIT order at the runner's price — oversized relative to what the runner will actually hold once tp1/tp2 split off, and non-runner tranches get zero broker-side protection
- **Alternative:** Option 1 is the minimal, low-risk fix (one line, no new order logic). Option 2 is the "actually fixes the feature" fix. I'd do Option 1 now to eliminate the silent-gap risk immediately, and treat Option 2 as a `DEF-` (deferred) item if per-tranche baskets matter enough to justify the broker-API investigation

---

### F-14 — Startup restore corrupts `pos.tgt` / can't map multi-tranche orders
- **Where:** `_check_open_positions_on_startup`, L6898-6910
- **What:** Replace the blind overwrite loop with quantity-matched assignment: build a list of unmatched `open_orders` for the symbol, then for each `tr in pos.tranches` (sorted by qty or by tp_pts), match against the order whose `quantity` field equals `tr.qty`, assign `tr.sl_order_id`/`tr.tgt_order_id` accordingly instead of the flat `pos.sl_order_id`/`pos.tgt_order_id`. Drop the unconditional `pos.tgt = _order_price` entirely, or restrict it to only fire when `len(pos.tranches) == 1`.
- **Why:** Current loop overwrites down to whichever order is iterated last, and corrupts the position-level target with a tp1/tp2 price in multi-tranche restores
- **Alternative:** If exact qty-matching feels fragile (partial fills could make quantities not line up perfectly), a looser fallback is matching by **price proximity** to each tranche's `tp_pts` instead of exact qty — less precise but more tolerant of broker-side quantity drift. I'd only reach for this if qty-matching turns out to fail in practice; start with the exact-match version since it's more auditable.

---

### F-15 — `_cleanup_stale_positions` has no accounting safety net
- **Where:** `_cleanup_stale_positions`, L6963-6985
- **What:** Add `_advance_stage(pos, LifecycleStage.CLOSED)` before the pop (cheap, always correct). For the accounting concern, add a guard: track a small `set`/`dict` of slot_ids written to the journal in the last N minutes (or check `pos.exit_pending` was set by a code path that already called `_write_journal`); if a stale position is being force-removed **without** evidence it was journaled, log a loud `[JOURNAL] ⚠ unaccounted force-removal` warning rather than silently dropping it.
- **Why:** Closes the silent-loss risk if a future code path (or an untraced existing one) reaches "stuck" status without going through `_finalize_exit` first — currently there's no way to even detect that this happened
- **Alternative:** Lower-effort version: just add the `CLOSED` transition and a warning log unconditionally on every force-removal (not conditional on missing-journal-evidence) — you lose the "only warn if actually unaccounted" precision, but it's a 2-line change vs. building tracking state, and a human reviewing logs can judge from the PnL fields already logged in the cleanup message whether it looks concerning

---

### F-16 — Journal write crashes on non-runner tranche exit (highest priority)
- **Where:** `TradeRecord.to_row()`, L1773
- **What:** `f"{self.max_favorable_excursion:.2f}" if self.max_favorable_excursion is not None else ""`
- **Why:** `build_tranche()` explicitly sets this field to `None` for every non-runner tranche (`L1925`); the format call has no guard unlike its 5 sibling optional fields — confirmed reproducible `TypeError` on every non-runner tranche exit, silently swallowing that journal row
- **Alternative:** None needed — this is a one-line, unambiguous fix matching the existing pattern used elsewhere in the same method. Only secondary suggestion: also wrap `row = record.to_row()` in `JournalWriter.write()` (L1811) in a `try/except Exception` alongside the existing `OSError` handler, so that *any* future field with the same class of bug degrades to a logged warning instead of an uncaught exception bubbling up to the strategy thread's generic error handler

---

Want these applied as a batch, or one at a time with re-verification between each — given F-13's decision point (Option 1 vs 2) probably needs your call before I'd log it as a patch either way?
