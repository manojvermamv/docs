"""
OPTIONS BUYER-EDGE STRATEGY  ·  Multi-Layer Confirmation  ·  OpenAlgo NSE F&O Options Trading Bot

Buys NSE F&O options (CE / PE) only when five independent signal layers agree:

  Layer 1 — Technical Trend        (EMA, VWAP, RSI, MACD on spot candles)
  Layer 2 — OI Flow Intelligence   (PCR, Call/Put Flow, OI Wall)
  Layer 3 — Greeks Engine          (Delta Imbalance, Gamma Regime)
  Layer 4 — Straddle & IV          (IV Regime, Straddle Velocity)
  Layer 5 — Synthetic Futures      (spot-SF co-movement)

Composite score: −100 → +100.  Order placed when:
  abs(score) ≥ MIN_SCORE  and  trap_score <= MAX_TRAP  and  signal == "EXECUTE"

Market data flows through MarketSnapshot authority layer:
  WebSocket ticks → SnapshotCache → trail / PNL / alerts / risk
  Quote API fallback when WS stale → SnapshotCache
  OptionChain enrichment → SnapshotCache

Snapshot is authority for market data only.
Position state (fills, protection orders) comes from broker APIs — independent reconciliation.

Run: export OPENALGO_API_KEY="your-key" && python BuyerEdgeStrategy.py
     Inside OpenAlgo Python Runner: injected automatically.

⚠  Long options carry unlimited theta decay — always set PREMIUM_STOP_PTS.
"""

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PRODUCTION AUDIT STATUS  ·  BuyerEdgeStrategy.py                            ║
# ║  Architecture V2 · Long Options (Buyer Only) · Multi-Position Ready          ║
# ║  Audit State: Production Stable · Structural Findings Closed                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# Audit Version      : V2
# Architecture       : Long Options (Buyer Only) · Multi-Layer Confirmation
# Deployment State   : Production
# Structural Risk    : None Known
# Research Status    : Active Calibration
# Closed Findings    : F1–F64, F71–F77 (F28, F49–F51 reserved; F65–F70 unused) · External Audit: F-A1 ✓ F-A2 ⬇ F-A3 ✓
# Runtime Pending    : F53 (multi-tranche signal-deterioration — awaiting live session)
#
#
# AUDIT SCOPE
# ------------------------------------------------------------------------------
# Architecture:
#   ✓ Long-options execution engine (Buyer only)
#   ✓ Multi-position (CE / PE / same-side) via PositionBook + SlotId routing
#   ✓ Tranche partial-exit framework
#   ✓ Basket protection (SL-M + LIMIT)
#   ✓ Premium confirmed-close trail (fixed / ATR / delta step methods)
#   ✓ Spot trail (synchronized snapshot-based)
#   ✓ Key-level structure trail (strike-level capture / fixed-pts)
#   ✓ Startup recovery & broker position reconstruction
#   ✓ Broker order reconciliation (pending entries/exits, SL self-heal)
#   ✓ Exit attribution & R-multiple journal analytics
#
# Flows validated:
#   ✓ Startup flow (positionbook restore, orphan cancel, WS resubscribe)
#   ✓ Runtime flow (strategy loop ordering, trail engine, signal scan)
#   ✓ Recovery flow (stale-snapshot quote API fallback, WS reconnect)
#   ✓ Restart flow (broker position reconstruction, protection reconciliation)
#   ✓ Exit flow (WS tick trigger → place_exit → poll → _finalize_exit cleanup)
#   ✓ Reconciliation flow (check_pending_entries/exits, stale position cleanup)
#   ✓ Order-stream flow (event dispatcher → polling safety net; 4-priority dispatch)
#   ✓ Concurrency (state_lock → exit_lock hierarchy, thread pool bounds)
#
#
# FINDING STATUS
# ------------------------------------------------------------------------------
# Closed Findings:               F1–F64, F71–F77 (F28, F49–F51 reserved; F65–F70 unused)
# Runtime Verification Pending:  F53 (live multi-tranche signal-deterioration)
# External Audit Findings:       F-A1 ✓ Fixed · F-A2 ⬇ Accepted · F-A3 ✓ Fixed
# Structural Defects:            None known
# Production Blockers:           None known
# Remaining Work:                Calibration + expectancy research only
#
# OpenAlgo SDK audit: all strategy= params migrated to cfg.broker.strategy_name.
# telegram() correctly omits strategy= (SDK has no such param).
# basketorder() now passes strategy=cfg.broker.strategy_name.
#
# ⚠ KNOWN PLATFORM GAP (paused, not fixable here): OpenAlgo server does not enforce `strategy`
# on orderbook/positionbook (returns account-wide data) or cancelorder (no ownership check before
# cancel) — confirmed via server source, not SDK docs. On a shared multi-strategy account, this bot's
# startup orphan-order cleanup (L7396) can see and cancel ANOTHER strategy's live orders. No client-side
# fix possible; requires upstream OpenAlgo fix. Full trace: @strategies/docs/openalgo_strategy_orders_isolation_gap.md.
#
#
# ==============================================================================
# CLOSED FINDINGS
# ==============================================================================
#
# F1  ✓ Fixed: Journal column count mismatch — pnl_pts missing from to_row.
# F2  ✓ Fixed: Opposite-side exit never fired — signal gate corrected.
# F3  ✓ Fixed: Basket protection getattr always True — guard corrected.
# F4  ✓ Fixed: record_exit not called on partial tranche exits — added.
# F5  ✓ Fixed: AlertConfig never read telegram_token/chat_id — class removed.
# F6  ✓ Fixed: PositionBook.__setitem__ accumulated duplicates — slot_id key.
# F7  ✓ Fixed: _trigger_exit fallback used wrong position in multi-position mode.
# F8  ✓ Fixed: TrailConfig.from_env() omitted 3 env vars — added.
# F9  ✓ Fixed: check_broker_order_fills double-checked orders in multi-tranche mode.
# F10 ✓ Fixed: update_from_option_chain only handled one symbol — per-symbol now.
# F11 ✓ Fixed: RiskManager.record_exit() not thread-safe — state_lock.
# F12 ✓ Fixed: BrokerConfig hardcoded manojv097 default — empty string with validation.
# F13 ✓ Fixed: JournalConfig ignored analytics_enabled env var — parsed correctly.
# F14 ✓ Fixed: _build_tranches called before sl set on position — reordered.
# F15 ✓ Verified: _check_max_hold lock ordering (HR-1) — exit_lock nested correctly.
# F16 ✓ Fixed: RiskConfig 0.0 defaults — validation warns if all loss limits off.
# F17 ✓ Fixed: TrailConfig.validate() missing gamma_speed_step_floor range check.
# F18 ✓ (merged with F2)
# F19 ✓ Design choice: WS exit pool max_workers=5 (HR-2) — documented in AGENTS.md.
# F20 ✓ Fixed: Restart tgt reconstructed without tgt_mult — now fetches option greeks.
# F21 ✓ Fixed: 7 × datetime.now() → get_ist_now() + dataclass default_factory.
# F22 ✓ Fixed: PositionBook.pop() ambiguous underlying-first → slot_id-only.
# F23 ✓ Fixed: WS _trigger_exit drops slot_id — passes pos.slot_id to exit_callback.
# F24 ✓ Fixed: Trail SL modify callback drops slot context — slot_id threaded through.
# F25 ✓ Fixed: modify_broker_sl TOCTOU exit-retrigger omits slot_id — chained.
# F26 ✓ Fixed: Post-cutoff entry exit passes slot_id — resolves correct position.
# F27 ✓ Fixed: Startup restore skips 2nd broker position per underlying — guard removed.
# F28 ✓ (reserved)
# F29 ✓ Fixed: Stale invariant text — SnapshotCache labelled per-symbol, not singular.
# F30 ✓ Fixed: Self-contradictory WS tick header text — cleaned.
# F31 ✓ Fixed: pending_exits keyed by slot_id (removed underlying collision in CE+PE).
# F32 ✓ Fixed: pending_entries keyed by order_id (removed underlying collision).
# F33 ✓ Fixed: SIGTERM handler for OpenAlgo /python hosted graceful shutdown.
# F34 ✓ Fixed: _check_max_hold exited first slot only — slot_id threaded through.
# F35 ✓ Fixed: V2-A6 fired on WATCH signals — gated to EXECUTE only (entry replacement invariant).
# F36 ✓ Fixed: Trail engine read primary _option_map only — get_for_symbol(pos.symbol) now.
# F37 ✓ Fixed: can_enter() blocked on exit_pending opposite slots — has_active_opposite().
# F38 ✓ Fixed: _refresh_stale_snapshots refreshed only first slot per underlying — iterate get_all(ul) instead of get_one for quote-fallback; WS/SL-modify/startup paths already slot-aware.
# F39 ✓ Fixed: OPENALGO_STRATEGY_EXCHANGE single-value passthrough set spot_exchange="NFO", breaking index/spot quote fetching — mapped via _STRATEGY_EXCHANGE_MAP (NFO→NFO,NSE,NSE_INDEX; BFO→BFO,BSE,BSE_INDEX; MCX/CDS/BCD→same-for-all-three).
# F40 ✓ Fixed: check_pending_entries already_open guard blocked legitimate 2nd-slot fills in CE+PE mode — now checks at symbol-level instead of any-slot-per-underlying.
# F41 ✓ Fixed: Dead _sl_modify_callback on WebSocketManager declared but never invoked — removed attribute, setter, and wiring (3 lines); real path is trail_engine.modify_callback.
# F42 ✓ Fixed: Startup restore skipped _build_tranches, leaving pos.tranches=[] and TGT order ID silently dropped — _build_tranches(pos, qty, cfg) inserted before protection-order reconciliation.
# F43 ✓ Fixed: Post-cutoff entry exit marked wrong slot as exit_pending in CE+PE mode — now resolves by exact symbol match instead of get_one(underlying).
# F44 ✓ Fixed: Fast-path entry gate made V2 signal-management unreachable for position lifetime — _needs_signal_for_management flag bypasses the gate when any management feature is enabled.
# F45 ✓ Fixed: Spot unsubscribe killed sibling's spot feed in CE+PE mode — has_siblings() guard added at all exit-cleanup paths.
# F46 ✓ Fixed: Tranche collapse threshold hardcoded ×2 regardless of number_of_tranches, producing 0-qty runner — equal-split now uses min_qty × n, ladder uses min_qty × 3; tq ≤ 0 guard added.
# F47 ✓ Fixed: Multi-tranche order loop had no qty > 0 guard — zero-qty tranche would attempt quantity=0 broker order; added tr.qty <= 0: continue.
# F48 ✓ Fixed: verify_sl_orders_active never checked LIMIT orders — externally cancelled TP1/TP2 targets went unreissued; refactored into _verify_one_order helper that checks both SL and LIMIT at position and per-tranche level.
# F49 ✓ (reserved)
# F50 ✓ (reserved)
# F51 ✓ (reserved)
# F52 ✓ Fixed: V2-A2 escalation violated monotonicity (min() could reduce SL) and bypassed broker confirm — removed entirely; V2-A6, opposite_side_exit_on_signal, V2-A1 handle same scenario.
# F53 ◐ Pending: V2-A5 tranche signal-deterioration exit (L6937-6949) — code structure verified but awaiting live multi-position session; exits one non-runner tranche via _exit_non_runner_tranche on opposing signal.
# F54 ✓ Fixed: modify_broker_sl sent pos.qty instead of remaining_qty — multi-tranche runner SL-M inflates to original qty after TP fill; fixed with quantity=pos.remaining_qty.
# F55 ✓ Fixed: VWAP had 3 bugs — iloc[-5:] slice before ta.vwap destroyed Session anchor, ndarray .iloc[-1] raised AttributeError, zero-volume NSE_INDEX blocked all VWAP; fixed with full df_today, ta_value ndarray-safe indexing, np.ones volume fallback.
# F56 ✓ Fixed: Unavailable specs inflated MAX_RAW_SCORE denominator — ScoreComponent gained available flag; IndicatorSpec/StatisticSpec set False on None returns; aggregator filters sum by c.available.
# F57 ✓ Fixed: Missing PCR (None from _compute_pcr) false-triggered trap-score alarm at pcr=0 — _intermediates.get("pcr") with no default + is not None guard before threshold comparison.
# F58 ✓ Fixed: _refresh_stale_snapshots write-gates skipped is_stale() check — fetched quote overwrote cache even when WS tick arrived during fetch; added or snap2.is_stale(timeout) to both write-gates.
# F59 ✓ Fixed: Reentrant state_lock deadlock on strategy thread — not a slow API call. check_entry_gates() acquired state_lock then accessed daily_pnl, which called _maybe_reset_daily_state() which tried to acquire the same non-reentrant Lock — same thread blocked on itself. Fixed by reading daily_pnl before the lock block.
# F60 ✓ Fixed: snapshot_stale_timeout=5s triggered Upstox UDAPI10005 rate limit on every scan — stale snapshot → DATA-MISS → trail blind; increased default to 30.0, overridable via SNAPSHOT_STALE_TIMEOUT env var.
# F61 ✓ Fixed: check_pending_entries cancel-after-cutoff path used bare cancelorder instead of _cancel_three_outcome — cancel-race fill popped pending entry without orderstatus re-check, orphaned position. Swapped to _cancel_three_outcome.
# F62 ✓ Fixed: _cancel_tranche_orders cleared per-tranche order IDs but not pos.sl_order_id flat alias — stale after restart for multi-tranche positions; modify_broker_sl proceeded on dead order ID. Added pos.sl_order_id = None after per-tranche clear loop.
# F63 ✓ Fixed: _handle_broker_order_fill non-runner path — SL fill cancelled TGT but ID never cleared, next loop re-queried stale ID and could fire duplicate exit. Fixed with tr.is_exit_placed guard + setattr(tr, other_name, None) in finally.
#
# F-A1 ✓ Fixed: _exit_non_runner_tranche placed SELL then blocked on poll (~30s) without registering in-flight qty — WS-triggered place_exit could oversell from stale remaining_qty. Fixed by registering into _pending_tranche_exits before poll under lock, _sellable_qty() helper + 0-qty defer in place_exit.
#
# F-A2 ⬇ Accepted: poll_order_status stalls strategy loop ~30s during tranche exit. F-A1 removed the overselling risk from this window; reduced to performance/UX concern. Not patched.
#
# F-A3 ✓ Fixed: warnings() hook was dead code — no config class defined it. EntryConfig.validate() treated a soft warning as fatal SystemExit. Fixed by adding warnings() to EntryConfig.
#
# F64 ✓ Fixed: check_entry_gates() drawdown-rate check read _pnl_history outside state_lock as two unlocked statements — concurrent record_exit() popleft() could raise IndexError. Fixed by snapshotting guard inside existing locked block.
#
# F72 ✓ Fixed: TrancheConfig.validate() checked sum == 100 but never that each field is within [0, 100] — out-of-range values summing to 100 passed validation and could cause >qty allocation in ladder mode. Fixed with per-field range check loop.
#
# F73 ✓ Fixed: Basket-order leg identification used multi-key lookup (pricetype/price_type/ordertype) but response schema has none of these — only orderid, status, symbol per entry. Relied on positional fallback (i==0) by accident. Made positional assumption explicit with count-mismatch guard.
#
# F74 ✓ Fixed: poll_order_status partial-fill branch reads filled_quantity from orderstatus() REST endpoint — confirmed endpoint never populates this for 27+ of 32+ brokers. Order-update stream completes pending entries via order_stream_complete_entries flag, preserving polling fallback.
#
# F75 ✓ Fixed: fetch_candles() type annotation claimed `-> pd.DataFrame | None` but SDK's history() returns dict on error (empty data, processing failure, API error) — len(dict) returns key count, passing length check by coincidence. Added isinstance(result, pd.DataFrame) guard.
#
# F76 ✓ Fixed: REST API filled_quantity empty for 27+ brokers — six call sites with fq>0 guard silently skipped order confirmation. Fixed by substituting pending.qty in cancellation paths and avg_price>0 as primary exit-fill signal.
#
# F77 ✓ Fixed: Order-stream dispatcher only handled entry completions — LIMIT fills, SL-M triggers, and exit completions silently dropped. Fixed with 4-priority universal dispatch covering pending_entries, pending_exits, protection-fill immediate action, and shadow inf().

# ==============================================================================
# CODING CONVENTIONS
# ==============================================================================
#
# Attribute initialization: All instance attributes MUST be declared in __init__
# with a type annotation. No lazy hasattr(self, '_x') patterns — they bypass type
# checkers, hide init-order dependencies, and complicate refactoring.

# ==============================================================================
# AUDIT STATUS
# (PositionBook · SlotId · Execution Engine · Trailing · Market Data ·
#  Protection · Recovery · Journal · Broker Integration)
# ==============================================================================
#
# ==============================================================================
# VERIFIED ARCHITECTURE
# ==============================================================================
#
# 1. PositionBook & SlotId Routing
#    Current: Slot-keyed position store; default single-position, supports multi-position (CE+PE, same-side) via env.
#    Verified: SlotId threaded through exits, modify-callbacks, pending maps, exit cleanup, stale-snapshot refresh.
#    Policy:
#        slot_id = f"{underlying}_{option_type}_{timestamp_us}"
#
# 2. Tranche Partial-Exit Framework
#    Current: Equal/ladder modes with per-tranche SL/LIMIT order IDs. TGT order ID preserved via runner_tranche.
#            Non-runner TP targets auto-distributed from 50% → tp_ceiling_pct based on number_of_tranches.
#            tp1_pts/tp2_pts removed; tp_ceiling_pct (default 85%) controls last non-runner ceiling.
#    Verified: Auto-tier TP formula (0.5 + spread × i / (n−2)), spread = tp_ceiling_pct/100 − 0.5.
#             Collapse threshold mode-aware (min_qty × n). qty ≤ 0 guard. LIMIT re-issue on external cancellation.
#
# 3. Premium Trail (Confirmed-Close)
#    Current: Fixed/ATR/delta-step sizing. ATR activation gated by atr_activation_buffer_pts; first SL at confirmed_close - step_pts (no breakeven floor). Non-ATR uses profit-lock breakeven floor at activation. Monotonic max-based ratchet applies to all methods.
#            atr_min_ratchet_improvement_pct (default 0.5) requires SL to improve by at least N% of the current confirmed close — at ratchet time this is equivalent to N% of peak, since ratchets only fire on new confirmed-close highs where confirmed_close == pos.trail_peak_close that cycle. At activation (ungated, runs every tick pre-activation) it's deliberately anchored to live price rather than a stale peak, so a spike-and-fade doesn't delay arming the trail.
#            Composition with atr_activation_buffer_pts: buffer is the first gate (premium must exceed EP by buffer pts before SL is even considered), improvement_pct is the second gate (SL must beat current SL by N% of confirmed_close before it's accepted). Both must pass; one is about when to try, the other about whether the result is good enough.
#    Verified: Gamma speed tiers at 50/100/150% ROI. Step cap at ep × 0.50. ATR first SL constrained by monotonic new_sl > pos.sl + atr_min_ratchet_improvement_pct × peak/100 guard. atr_activation_buffer_pts and atr_min_ratchet_improvement_pct are orthogonal: buffer defers first consideration, improvement gates whether the resulting SL is good enough (== peak/100 at ratchet time by construction; activation intentionally uses live price, not peak).
#    Policy:
#        non-ATR activation: new_sl = max(confirmed_close - step_pts, lock_floor)
#        ATR activation:     new_sl = confirmed_close - step_pts          (no floor, but gate requires > pos.sl + peak × pct/100)
#
# 4. Spot Trail & Key-Level Trail
#    Current: Synchronized snapshot-based spot trail. Key-level trail with strike-level capture and fixed-pts steps.
#    Verified: Shared-spot feed protected via has_siblings() guard in CE+PE mode. Key-level state ephemeral across restart.
#
# 5. MarketSnapshot & SnapshotCache
#    Current: WS ticks → SnapshotCache → trail/PNL/alerts. Quote API fallback on stale. OptionChain enrichment.
#    Verified: Per-symbol isolation. Write-gate preserves stale cache when WS tick arrives during fetch.
#    Policy:
#        overwrite = new_ltp is not None or snap.is_stale(timeout)
#
# 6. Basket Protection Architecture
#    Current: Entry SL-M + LIMIT via basket orders. Partial acceptance recovery. Legacy single-order fallback.
#    Verified: Protection-order reconciliation across all paths (skip-if-exists, startup restore, basket fallback).
#
# 7. WebSocket Infrastructure
#    Current: Persistent client with subscription reconciliation, reconnect restoration, watchdog self-healing, health telemetry.
#    Verified: Circuit-breaker alerting, subscription drift detection, thread-leak visibility, auth notification deduplication.
#
# 8. Recovery & Reconciliation
#    Current: Startup broker position reconstruction, orphan-order cancellation, tranche rebuild. Broker SL-M independent of WS. Order-stream event dispatcher runs before polling safety net in every cycle.
#    Verified: Pending dicts keyed by slot_id/order_id. Multi-slot stale-snapshot quote-fallback. Symbol-level already_open guard. Stream dispatcher handles entry completions, exit completions, protection-fill immediate action (sl_order_id/tgt_order_id), and shadow logging for all unmatched events.
#
# 9. Exit Attribution & Journal
#    Current: N-column CSV with record_type discriminator (full_exit / partial_exit). SlotId + tranche_id tracking.
#    Verified: Exit-type normalization (BROKER_SL, TARGET, PREMIUM_TRAIL, SPOT_TRAIL, MAX_HOLD, EOD, etc.). R-multiple journaling. Schema migration auto-archives on column mismatch.
#
# 10. Broker Integration
#     Current: Exchange mapping via _STRATEGY_EXCHANGE_MAP for hosted-mode compatibility.
#     Verified: NFO→(NFO,NSE,NSE_INDEX), BFO→(BFO,BSE,BSE_INDEX), MCX/CDS/BCD→same-for-all-three.
#     Constraint: Retail API idempotency keys unavailable; residual duplicate-order tail-risk accepted.
#
# 11. Execution & Signal Engine
#     Current: Five-layer confirmation composite score (-100 to +100). SignalEngine with INDICATOR_REGISTRY (4 specs) and STATISTIC_REGISTRY (10 specs). StrikeSelector with delta-band primary / OTM hard-sl fallback.
#     Verified: Entry gating (max positions, opposite-side, same-direction conviction gate, strike cumulative-loss guard). Session time gates (morning/normal/power hour). Signal-aware position management — V2-A6 parallel exit on opposing signal, V2-A1 diagnostic logging, V2-A5 tranche deterioration exit. Post-cutoff slot resolution.
#
# ==============================================================================
# CALIBRATION / RESEARCH
# ==============================================================================
#
# 1. Gamma Speed-X Thresholds
#    Current:
#        ROI >=  50% → 1.5× speed
#        ROI >= 100% → 2.0× speed
#        ROI >= 150% → 2.5× speed
#    Research: Validate thresholds against live ROI distributions and realized premium expansion behavior.
#
# 2. Conviction Scaling
#    Current:
#        `conviction = abs(score) / 100`
#    Research: Larger sample needed before modification. Candidates — `conviction**1.5` (compress low), `sqrt(conviction)` (expand low).
#
# 3. Delta Target Curve
#    Current: STRIKE_DELTA_BASE, STRIKE_DELTA_RANGE
#    Research: Expectancy-driven tuning from live trade-distribution analysis.
#
# 4. Deep-ITM Stop Sizing
#    Current: Moneyness-aware stop sizing.
#    Research: Compare Deep-ITM vs ATM expectancy, capital efficiency, premium retention, realized R-multiples.
#
# 5. Exit-Type Expectancy Database
#    Current: Exit categories captured (BROKER_SL, TARGET, PREMIUM_TRAIL, SPOT_TRAIL, MAX_HOLD, EOD, FORCE_UNTRACK_*, MANUAL, OTHER).
#    Research: Measure expectancy and average R-multiple by exit type. Identify negative-expectancy mechanisms.
#
# 6. KER (Profit Acceleration Compression Engine)
#    Current: Rolling 15-bar window on 1-min candles. Discretionary: early→normal, gamma→compress, high-ROI chop→relax.
#    Research: Evaluate EMA smoother or decay floor for abrupt KER transitions.
#
# 7. ATR Activation Buffer
#    Current: atr_activation_buffer_pts default 0.0 (breakeven activation). Configurable buffer defers ATR trail activation until price crosses BE + buffer.
#    Research: Optimal buffer value by underlying volatility regime. Relationship between buffer width and activation rate across ATR step methods.
#
# 8. Strike Cumulative-Loss Ceiling
#    Current: max_strike_cum_loss_pts default 60.0 (2 × premium_stop_pts). Cumulative loss accumulated per strike+direction on exit; exceeding ceiling blocks re-entry.
#    Research: Validate 2× ceiling ratio against realized loss distributions. Tune for strike-level vs portfolio-level loss tolerance.
#
# ==============================================================================
# DESIGN INVARIANTS
# ==============================================================================
#
# 1. Snapshot is authority for market data only. Position state (fills, protection orders) comes from broker APIs via independent reconciliation.
#
# 2. Broker SL-M is the source of truth for protection. Trail state reinitializes from live market data after every restart.
#
# 3. WS is operationally optional — stale-snapshot quote-API fallback re-populates SnapshotCache when ticks go stale.
#
# 4. Broker SL modify failure → SL not advanced (retry on next tick). No escalation path — intentional.
#
# 5. Default runtime policy: 1 active position per underlying. Architecture supports multi-position (CE+PE, same-side) via configuration.
#
# 6. Retail API idempotency externally constrained. Residual tail-risk: network timeout after broker acceptance may create duplicate orders during fallback recovery. Accepted operational risk.
#
# 7. SL Ceiling — Three configs, three different questions, compose via min():
#    premium_stop_pts (X points)  =  "What's my simple default SL when no data?"
#    max_sl_pts (0 = premium_stop_pts) =  "What's my absolute never-exceed cap?"
#    max_sl_premium_ratio (0 = disabled) = "What's my proportional-to-premium ceiling?"
#    Chain: base → sl_factor → floor(5) → min(abs_ceiling, premium × ratio/100) — applied LAST.
#
# ==============================================================================
# PRODUCTION READINESS
# ==============================================================================
#
#   PositionBook & SlotId        : Stable
#   Tranche Framework            : Stable
#   Premium Trail                : Stable
#   Spot Trail                   : Stable
#   Key-Level Trail              : Stable
#   Market Data Pipeline         : Stable
#   Basket Protection            : Stable
#   WebSocket Infrastructure     : Stable
#   Recovery & Reconciliation    : Stable
#   Exit Attribution & Journal   : Stable
#   Broker Integration           : Stable
#   Broker SL Sync               : Stable
#
# Remaining work is calibration, expectancy research,
# trade-distribution analysis, and statistical optimization.
#
# ===============================================================================


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 1 — IMPORTS & LOGGING                                       ║
# ╚══════════════════════════════════════════════════════════════════════╝

import csv
import copy
import ast
import concurrent.futures
import math
import os
import re
import sys
import signal
import threading
import time as _time_mod
time = _time_mod   # single canonical alias — use time.sleep / time.time / _time_mod.mktime interchangeably
import traceback
import queue
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import ClassVar,  Any, Callable
import numpy as np
import pandas as pd
import openalgo
from openalgo import api, ta

# Ensure UTF-8 output on Windows (cp1252 console cannot encode ₹ and other Unicode chars).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 2 — CONSTANTS & MODULE-LEVEL STATE       ExitReason         ║
# ╚══════════════════════════════════════════════════════════════════════╝

# Logging — global toggle constants
DEBUG_ENABLED = True
INFO_ENABLED  = True

def dbg(*args, **kwargs):
    if DEBUG_ENABLED:
        print(f"{get_ist_now():%H:%M:%S}", *args, **kwargs, flush=True)

def inf(*args, **kwargs):
    if INFO_ENABLED:
        print(f"{get_ist_now():%H:%M:%S}", *args, **kwargs, flush=True)

def err(msg: str, exc: BaseException | None = None, *, always: bool = True):
    if always:
        ts = f"{get_ist_now():%H:%M:%S}"
        if exc is not None:
            print(f"{ts} [ERROR] {msg}: {exc}", flush=True)
        else:
            print(f"{ts} [ERROR] {msg}", flush=True)


# ===============================================================================
# GLOBAL CONSTANTS
# ===============================================================================

# Market hours (IST): 9:15 AM – 3:30 PM
MARKET_HOURS_START = 915   # 09:15 IST
MARKET_HOURS_END   = 1530  # 15:30 IST

# ── Layer 1: Score Generation ──────────────────────────────────────────────────
# PRACTICAL_ALIGNMENT_FACTOR: defines what fraction of MAX_RAW_SCORE is treated as
# the "practical ceiling" for a 100-point conviction score. Market signals rarely
# achieve 100% component alignment; this factor acknowledges that reality.
#
# Calibration guide — run a distribution audit across N scans and observe:
#   If 95th percentile raw_score ≈ 0.50 × MAX_RAW_SCORE → set to 0.50
#   If 95th percentile raw_score ≈ 0.75 × MAX_RAW_SCORE → set to 0.75
#   Until confirmed by live data, keep at 1.00 (no compression, full gradient).
PRACTICAL_ALIGNMENT_FACTOR = 1.00

# ── Layer 2: Trade Selection ────────────────────────────────────────────────────
# WATCH_FACTOR: the score band below EXECUTE that marks a setup worth monitoring.
# watch_threshold = effective_min_score × WATCH_FACTOR
#
# Session thresholds (set via BotConfig / ENV):
#   morning_gate  → typically 45  (stricter pre-market discipline)
#   normal_hours  → typically 30  (baseline execution bar)
#   power_hour    → typically 20  (relaxed, momentum-driven)
#
# Example at normal_hours (effective_min_score=30):
#   abs_score >= 30  → EXECUTE
#   abs_score >= 22  → WATCH  (30 × 0.75 = 22.5 → 22)
#   abs_score  < 22  → NO_TRADE
WATCH_FACTOR = 0.75

# ── Layer 3: Strike Selection (conviction-driven) ──────────────────────────────
# All strike-selection parameters are driven by a single `conviction` scalar
# derived from (abs(signal_score) - min_score) / (100 - min_score).  This
# eliminates hard regime jumps and maps the tradeable score range [min→100]
# continuously to [0.0, 1.0].
#
# Delta targeting — piecewise continuous mapping:
#   Score < 50   → [STRIKE_DELTA_BASE, STRIKE_DELTA_PIVOT] (near-OTM → ATM)
#   Score >= 50  → [STRIKE_DELTA_PIVOT, STRIKE_DELTA_MAX]  (ATM → Mild ITM)
#
# Calibration change (2026-06-04):
#   STRIKE_DELTA_BASE:  raised 0.15 → 0.25: even the weakest signal now targets
#     a near-OTM strike (Δ≈0.25) instead of a deep-OTM (Δ≈0.15), reducing
#     SL width and preventing systematic qty=0 risk-cap rejections.
#   STRIKE_SCORE_PIVOT: lowered 60 → 50: ATM targeting is reached at a lower
#     score, so today's typical 42–52 signals get meaningfully better strikes.
STRIKE_DELTA_BASE  = 0.25   # min delta at min_score (near-OTM floor) — raised from 0.15 to reduce SL width on weak signals
STRIKE_DELTA_PIVOT = 0.50   # delta at SCORE_PIVOT (ATM) — crossover between OTM and mild-ITM targeting zones
STRIKE_DELTA_MAX   = 0.70   # max delta at score 100 (mild ITM) — prevents over-leveraged deep-ITM selection
STRIKE_SCORE_PIVOT = 50.0   # score where ATM is targeted — lowered from 60 so typical 42–52 signals reach ATM-ish strikes

# Delta band half-width — how wide to search around the target delta.
# e.g. 0.08 means [target-0.08, target+0.08].
STRIKE_DELTA_BAND = 0.08    # search band around target_delta — wider band tolerates illiquid chains with sparse delta coverage

# Maximum acceptable delta gap in the fallback strike selection.
# If the nearest available delta is farther than this from the target, the
# fallback is considered pathological and the delta filter is bypassed entirely,
# falling back to pure liquidity ranking instead of picking a wildly OTM strike.
MAX_DELTA_GAP = 0.15        # fallback gap ceiling — exceeding this bypasses delta filter entirely and uses liquidity rank only

# Dynamic asym_score weighting — delta vs liquidity tradeoff:
#   conviction=0.0 → delta_weight = STRIKE_DELTA_WEIGHT_BASE          (favour liquidity)
#   conviction=1.0 → delta_weight = STRIKE_DELTA_WEIGHT_BASE + RANGE  (favour delta fit)
STRIKE_DELTA_WEIGHT_BASE  = 0.10   # delta fit weight at zero conviction — low conviction defers to OI/volume liquidity signals
STRIKE_DELTA_WEIGHT_RANGE = 0.20   # additional delta weight at max conviction — total 0.30 at high conviction (max delta precision)

# Maximum strike search window as a fraction of spot price (each side).
# e.g. 0.05 = ±5% → CE: [spot, spot*1.05]; PE: [spot*0.95, spot].
STRIKE_RANGE_PCT = 0.05     # strike search radius — ±5% of spot; wider = more candidates but lower quality floor

# ── Conviction Risk Engine — global tuning constants ──────────────────────────
# These constants are shared by SL sizing, breakeven, and all trail functions
# to ensure a single consistent model drives all risk parameters.
#
# Breakeven trigger adjustment:
#   adj = CONV_BE_BASE - conviction * CONV_BE_RANGE
#   conviction=0.0 → 1.10× (need 110% of normal trigger)
#   conviction=1.0 → 0.90× (trigger at 90% — protect earlier)
#   Narrow range intentional: avoids killing winners via premature BE on strong setups.
CONV_BE_BASE  = 1.10
CONV_BE_RANGE = 0.20

# Live PNL alert interval in seconds (0 = disabled)
LIVE_PNL_ALERT_INTERVAL = 60


class ExitReason:
    """Normalized exit reason codes for expectancy database."""
    BROKER_SL           = "BROKER_SL"
    BROKER_TARGET       = "BROKER_TARGET"
    PREMIUM_TRAIL       = "PREMIUM_TRAIL"
    SPOT_TRAIL          = "SPOT_TRAIL"
    MAX_HOLD            = "MAX_HOLD"
    EOD                 = "EOD"
    FORCE_UNTRACK_EST   = "FORCE_UNTRACK_EST"
    FORCE_UNTRACK_UNKNOWN = "FORCE_UNTRACK_UNKNOWN"
    MANUAL              = "MANUAL"
    SIGNAL_FLIP         = "SIGNAL_FLIP"
    BROKER_FILLED       = "BROKER_FILLED"
    OTHER               = "OTHER"
    
    # Internal mapping from raw reason strings to normalized enum
    _RAW_TO_ENUM = {
        "premium_sl_hit": PREMIUM_TRAIL,
        "premium_target_hit": BROKER_TARGET,
        "spot_trail_sl_hit": SPOT_TRAIL,
        "broker_sl_filled": BROKER_SL,
        "broker_sl_filled_on_modify": BROKER_SL,
        "broker_target_filled": BROKER_TARGET,
        "EOD-SquareOff": EOD,
        "EOD-ForceUntrack-Estimated": FORCE_UNTRACK_EST,
        "EOD-ForceUntrack-NoBrokerPrice": FORCE_UNTRACK_UNKNOWN,
        "PostCutoffEntry": EOD,
        "MaxHoldTime": MAX_HOLD,
        "Bot Shutdown": MANUAL,
        "manual": MANUAL,
        "opposite_signal_sync": SIGNAL_FLIP,
        "signal_reversal": SIGNAL_FLIP,
    }
    
    @classmethod
    def normalize(cls, raw_reason: str) -> str:
        """Map raw exit reason to normalized enum value."""
        return cls._RAW_TO_ENUM.get(raw_reason, cls.OTHER)
    
    @classmethod
    def all_values(cls) -> list[str]:
        """Return all normalized enum values."""
        return [
            cls.BROKER_SL, cls.BROKER_TARGET, cls.SIGNAL_FLIP, cls.PREMIUM_TRAIL, cls.SPOT_TRAIL,
            cls.MAX_HOLD, cls.EOD, cls.FORCE_UNTRACK_EST, cls.FORCE_UNTRACK_UNKNOWN,
            cls.MANUAL, cls.OTHER
        ]


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 3 — CONFIGURATION          8 sub-configs + BotConfig        ║
# ║    BrokerConfig / MarketConfig / EntryConfig / RiskConfig            ║
# ║    TrailConfig / JournalConfig / PositionConfig / TrancheConfig      ║
# ╚══════════════════════════════════════════════════════════════════════╝

# ── 3a — BrokerConfig ─────────────────────────────────────────────────────
@dataclass
class BrokerConfig:
    """OpenAlgo API connection, paper trade, basket protection."""
    api_key:              str   = "openalgo-apikey"
    api_host:             str   = "http://127.0.0.1:5000"
    ws_url:               str   = ""
    strategy_name:        str   = "OptionsBuyerEdgeBot"
    openalgo_username:    str   = "manojv097"
    broker_sl_orders:     bool  = True
    use_basket_protection: bool = True
    paper_trade:          bool  = False
    order_status_max_retries:   int   = 15
    order_poll_interval: float = 5.0
    quote_api_rps:        float = 30.0
    quote_api_burst:      int   = 10
    snapshot_stale_timeout: float = 30.0
    order_stream_enabled: bool = True
    order_stream_complete_entries: bool = True
    order_updates_enabled: bool = True

    @classmethod
    def from_env(cls) -> "BrokerConfig":
        return cls(
            api_key=os.getenv("OPENALGO_API_KEY", cls.api_key),
            api_host=os.getenv('HOST_SERVER') or os.getenv('OPENALGO_HOST') or cls.api_host,
            ws_url=os.getenv("WEBSOCKET_URL", cls.ws_url),
            strategy_name=os.getenv("STRATEGY_NAME", cls.strategy_name),
            openalgo_username=os.getenv("OPENALGO_USERNAME", cls.openalgo_username),
            use_basket_protection=os.getenv("BASKET_PROTECTION", str(cls.use_basket_protection)).lower() in ("1", "true", "yes"),
            broker_sl_orders=os.getenv("BROKER_SL_ORDERS", str(cls.broker_sl_orders)).lower() in ("1", "true", "yes"),
            paper_trade=os.getenv("PAPER_TRADE", str(cls.paper_trade)).lower() in ("1", "true", "yes"),
            order_status_max_retries=int(os.getenv("ORDER_STATUS_MAX_RETRIES", str(cls.order_status_max_retries))),
            order_poll_interval=float(os.getenv("ORDER_POLL_INTERVAL", str(cls.order_poll_interval))),
            quote_api_rps=float(os.getenv("QUOTE_API_RPS", str(cls.quote_api_rps))),
            quote_api_burst=int(os.getenv("QUOTE_API_BURST", str(cls.quote_api_burst))),
            snapshot_stale_timeout=float(os.getenv("SNAPSHOT_STALE_TIMEOUT", str(cls.snapshot_stale_timeout))),
            # ORDER_STREAM_ENABLED / ORDER_STREAM_COMPLETE_ENTRIES are script-config
            # values managed via defaults (not read from os.environ).
            order_updates_enabled=os.getenv("ORDER_UPDATES_ENABLED", "FALSE").upper() == "TRUE",
        )

    def validate(self) -> list[str]:
        errs: list[str] = []
        if self.order_status_max_retries < 1:
            errs.append(f"ORDER_STATUS_MAX_RETRIES={self.order_status_max_retries} must be >= 1")
        if self.order_poll_interval < 0:
            errs.append(f"ORDER_POLL_INTERVAL={self.order_poll_interval} must be >= 0")
        if not self.openalgo_username:
            errs.append("OPENALGO_USERNAME is still the empty string — set it to your own OpenAlgo username")
        if self.quote_api_rps <= 0:
            errs.append(f"QUOTE_API_RPS={self.quote_api_rps} must be > 0")
        if self.quote_api_burst <= 0:
            errs.append(f"QUOTE_API_BURST={self.quote_api_burst} must be > 0")
        if not self.strategy_name:
            errs.append("STRATEGY_NAME must not be empty")
        return errs


# ── Strategy exchange map (OpenAlgo /python hosted mode) ──────────────
# OPENALGO_STRATEGY_EXCHANGE (host-injected, /python only) gives ONE value —
# the F&O leg the user picked at upload. The bot needs three exchange roles
# derived from it: fno, spot, index.
_STRATEGY_EXCHANGE_MAP: dict[str, tuple[str, str, str]] = {
    # STRATEGY_EXCHANGE : (fno_exchange, spot_exchange, index_exchange)
    "NFO": ("NFO", "NSE", "NSE_INDEX"),
    "BFO": ("BFO", "BSE", "BSE_INDEX"),
    "MCX": ("MCX", "MCX", "MCX"),
    "CDS": ("CDS", "CDS", "CDS"),
    "BCD": ("BCD", "BCD", "BCD"),
}

# ── 3b — MarketConfig ─────────────────────────────────────────────────────
@dataclass
class MarketConfig:
    """Exchange routing, instruments, timing, candles."""

    # ── Universe & Exchange Routing ──
    underlyings:           list[str]      = field(default_factory=list)
    index_underlyings:     frozenset[str] = field(default_factory=frozenset)
    spot_exchange:         str   = "NSE"
    fno_exchange:          str   = "NFO"
    index_exchange:        str   = "NSE_INDEX"

    # ── Timing ──
    candle_interval:       str   = "1m"
    signal_check_interval: int   = 60
    dte_min:               int   = 7
    dte_max:               int   = 30
    otm_offset:            int   = 1
    strike_count:          int   = 8
    no_new_trade_after:    str   = "15:10"
    square_off_time:       str   = "15:13"
    max_hold_minutes:      int   = 0
    morning_session_end:   str   = "09:30"
    afternoon_power_start: str   = "14:00"

    # ── Data ──
    lookback_days:         int   = 5
    chain_smooth_bars:     int   = 5
    greeks_smooth_max_age: float = 180.0

    @classmethod
    def from_env(cls) -> "MarketConfig":
        underlyings_csv = os.getenv("UNDERLYINGS", "BANKNIFTY")
        index_csv = os.getenv("INDEX_UNDERLYINGS", "BANKNIFTY")
        underlyings = sorted(set(u.strip() for u in underlyings_csv.split(",") if u.strip()))
        index_underlyings: frozenset[str] = frozenset(
            u.strip() for u in index_csv.split(",") if u.strip()
        )
        defaults = cls()
        strategy_exch = os.getenv("OPENALGO_STRATEGY_EXCHANGE", "").upper().strip()
        mapped = _STRATEGY_EXCHANGE_MAP.get(strategy_exch)
        if strategy_exch and not mapped:
            inf(f"[CONFIG] OPENALGO_STRATEGY_EXCHANGE={strategy_exch!r} has no "
                f"options segment this bot supports (needs NFO/BFO/MCX/CDS/BCD) — "
                f"falling back to EXCHANGE/FNO_EXCHANGE/INDEX_EXCHANGE env vars.")
        fno_default = mapped[0] if mapped else defaults.fno_exchange
        spot_default = mapped[1] if mapped else defaults.spot_exchange
        index_default = mapped[2] if mapped else defaults.index_exchange
        return cls(
            underlyings=underlyings,
            index_underlyings=index_underlyings,
            spot_exchange=os.getenv("EXCHANGE", spot_default),
            fno_exchange=os.getenv("FNO_EXCHANGE", fno_default),
            index_exchange=os.getenv("INDEX_EXCHANGE", index_default),
            candle_interval=os.getenv("CANDLE_INTERVAL", defaults.candle_interval),
            lookback_days=int(os.getenv("LOOKBACK_DAYS", str(defaults.lookback_days))),
            dte_min=int(os.getenv("DTE_MIN", str(defaults.dte_min))),
            dte_max=int(os.getenv("DTE_MAX", str(defaults.dte_max))),
            otm_offset=int(os.getenv("OTM_OFFSET", str(defaults.otm_offset))),
            strike_count=int(os.getenv("STRIKE_COUNT", str(defaults.strike_count))),
            signal_check_interval=int(os.getenv("SIGNAL_CHECK_INTERVAL", str(defaults.signal_check_interval))),
            chain_smooth_bars=int(os.getenv("CHAIN_SMOOTH_BARS", str(defaults.chain_smooth_bars))),
            greeks_smooth_max_age=float(os.getenv("GREEKS_SMOOTH_MAX_AGE", str(defaults.greeks_smooth_max_age))),
            no_new_trade_after=os.getenv("NO_NEW_TRADE_AFTER", defaults.no_new_trade_after),
            square_off_time=os.getenv("SQUARE_OFF_TIME", defaults.square_off_time),
            max_hold_minutes=int(os.getenv("MAX_HOLD_MINUTES", str(defaults.max_hold_minutes))),
            morning_session_end=os.getenv("MORNING_SESSION_END", defaults.morning_session_end),
            afternoon_power_start=os.getenv("AFTERNOON_POWER_START", defaults.afternoon_power_start),
        )

    def validate(self) -> list[str]:
        _hhmm = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
        errs: list[str] = []
        if self.dte_min < 0 or self.dte_max < self.dte_min:
            errs.append(f"DTE_MIN={self.dte_min} / DTE_MAX={self.dte_max}: must satisfy 0 <= DTE_MIN <= DTE_MAX")
        for fname, val in (("MORNING_SESSION_END", self.morning_session_end),
                           ("AFTERNOON_POWER_START", self.afternoon_power_start),
                           ("NO_NEW_TRADE_AFTER", self.no_new_trade_after),
                           ("SQUARE_OFF_TIME", self.square_off_time)):
            if val and not _hhmm.match(val):
                errs.append(f"{fname}={val!r} must be in HH:MM format")
        if self.max_hold_minutes < 0:
            errs.append(f"MAX_HOLD_MINUTES={self.max_hold_minutes} must be >= 0 (0=disabled)")
        if self.signal_check_interval <= 0:
            errs.append(f"SIGNAL_CHECK_INTERVAL={self.signal_check_interval} must be > 0")
        if self.lookback_days < 1:
            errs.append(f"LOOKBACK_DAYS={self.lookback_days} must be >= 1")
        return errs


# ── 3c — EntryConfig ──────────────────────────────────────────────────────
@dataclass
class EntryConfig:
    """Signal scoring, strike selection, sizing, spread gate."""

    # ── Scoring ──
    min_score:                    int   = 40
    max_trap:                     int   = 60
    power_hour_score_factor:      float = 0.80
    morning_score_factor:         float = 1.50
    asym_score_threshold:         float = 0.35

    # ── Direction ──
    long_only_mode:               bool  = True

    # ── Sizing ──
    lot_multiplier:               int   = 1
    risk_based_sizing_enabled:    bool  = False
    risk_percent:                 float = 2.0
    adaptive_sizing_enabled:      bool  = False
    adaptive_max_lot_mult:        int   = 3
    adaptive_win_streak_trigger:  int   = 2
    adaptive_win_streak_step:     int   = 1

    # ── Target ──
    premium_target_pts:           float = 50.0
    spot_reward_pct:              float = 0.05

    # ── Indicators ──
    fast_ema_period:              int   = 9
    slow_ema_period:              int   = 21
    rsi_period:                   int   = 14

    # ── IV Filters ──
    iv_rank_max_entry:            float = 40.0
    iv_52w_low:                   float = 0.0
    iv_52w_high:                  float = 100.0

    # ── Liquidity Filters ──
    min_oi_filter:                float = 50_000.0
    min_vol_filter:               float = 10_000.0

    # ── Delta ──
    delta_target_low:             float = 0.25
    delta_target_high:            float = 0.45
    delta_exit_threshold:         float = 0.10

    # ── OI Velocity ──
    oi_velocity_enabled:          bool  = True
    oi_velocity_threshold:        float = 0.05

    # ── Spread Gate ──
    max_entry_spread_pct:         float = 8.0

    # ── GEX ──
    gex_enabled:                  bool  = True

    # ── Strike Loss Guard ──
    strike_loss_guard_enabled:    bool  = True
    max_strike_cum_loss_pts:      float = 60.0

    # ── Preflight Checks ──
    preflight_spread_check:       bool  = True
    preflight_max_spread_pct:     float = 10.0
    preflight_min_bid:            float = 5.0

    # ── Phase A SL Ceiling (compose via min()) ──
    premium_stop_pts:             float = 30.0   # Fallback SL width (SL = entry_price - X pts)
    max_sl_pts:                   float = 0.0    # Absolute never-exceed cap (0 = use premium_stop_pts)
    max_sl_premium_ratio:         float = 0.0    # Premium-proportional cap (0 = disabled; 20 = 20% of premium)

    @classmethod
    def from_env(cls) -> "EntryConfig":
        defaults = cls()
        return cls(
            min_score=int(os.getenv("MIN_SCORE", str(defaults.min_score))),
            max_trap=int(os.getenv("MAX_TRAP", str(defaults.max_trap))),
            power_hour_score_factor=float(os.getenv("POWER_HOUR_SCORE_FACTOR", str(defaults.power_hour_score_factor))),
            morning_score_factor=float(os.getenv("MORNING_SCORE_FACTOR", str(defaults.morning_score_factor))),
            long_only_mode=os.getenv("LONG_ONLY_MODE", str(defaults.long_only_mode)).lower() in ("1", "true", "yes"),
            lot_multiplier=int(os.getenv("LOT_MULTIPLIER", str(defaults.lot_multiplier))),
            risk_based_sizing_enabled=os.getenv("RISK_BASED_SIZING", str(defaults.risk_based_sizing_enabled)).lower() in ("1", "true", "yes"),
            risk_percent=float(os.getenv("RISK_PERCENT", str(defaults.risk_percent))),
            adaptive_sizing_enabled=os.getenv("ADAPTIVE_SIZING_ENABLED", str(defaults.adaptive_sizing_enabled)).lower() in ("1", "true", "yes"),
            adaptive_max_lot_mult=int(os.getenv("ADAPTIVE_MAX_LOT_MULT", str(defaults.adaptive_max_lot_mult))),
            adaptive_win_streak_trigger=int(os.getenv("ADAPTIVE_WIN_STREAK_TRIGGER", str(defaults.adaptive_win_streak_trigger))),
            adaptive_win_streak_step=int(os.getenv("ADAPTIVE_WIN_STREAK_STEP", str(defaults.adaptive_win_streak_step))),
            premium_target_pts=float(os.getenv("PREMIUM_TARGET_PTS", str(defaults.premium_target_pts))),
            fast_ema_period=int(os.getenv("FAST_EMA_PERIOD", str(defaults.fast_ema_period))),
            slow_ema_period=int(os.getenv("SLOW_EMA_PERIOD", str(defaults.slow_ema_period))),
            rsi_period=int(os.getenv("RSI_PERIOD", str(defaults.rsi_period))),
            iv_rank_max_entry=float(os.getenv("IV_RANK_MAX_ENTRY", str(defaults.iv_rank_max_entry))),
            iv_52w_low=float(os.getenv("IV_52W_LOW", str(defaults.iv_52w_low))),
            iv_52w_high=float(os.getenv("IV_52W_HIGH", str(defaults.iv_52w_high))),
            min_oi_filter=float(os.getenv("MIN_OI_FILTER", str(defaults.min_oi_filter))),
            min_vol_filter=float(os.getenv("MIN_VOL_FILTER", str(defaults.min_vol_filter))),
            asym_score_threshold=float(os.getenv("ASYM_SCORE_THRESHOLD", str(defaults.asym_score_threshold))),
            delta_target_low=float(os.getenv("DELTA_TARGET_LOW", str(defaults.delta_target_low))),
            delta_target_high=float(os.getenv("DELTA_TARGET_HIGH", str(defaults.delta_target_high))),
            delta_exit_threshold=float(os.getenv("DELTA_EXIT_THRESHOLD", str(defaults.delta_exit_threshold))),
            oi_velocity_enabled=os.getenv("OI_VELOCITY_ENABLED", str(defaults.oi_velocity_enabled)).lower() in ("1", "true", "yes"),
            oi_velocity_threshold=float(os.getenv("OI_VELOCITY_THRESHOLD", str(defaults.oi_velocity_threshold))),
            max_entry_spread_pct=float(os.getenv("MAX_ENTRY_SPREAD_PCT", str(defaults.max_entry_spread_pct))),
            strike_loss_guard_enabled=os.getenv("STRIKE_LOSS_GUARD_ENABLED", str(defaults.strike_loss_guard_enabled)).lower() in ("1", "true", "yes"),
            max_strike_cum_loss_pts=float(os.getenv("MAX_STRIKE_CUM_LOSS_PTS", str(defaults.max_strike_cum_loss_pts))),
            gex_enabled=os.getenv("GEX_ENABLED", str(defaults.gex_enabled)).lower() in ("1", "true", "yes"),
            preflight_spread_check=os.getenv("PREFLIGHT_SPREAD_CHECK", str(defaults.preflight_spread_check)).lower() in ("1", "true", "yes"),
            preflight_max_spread_pct=float(os.getenv("PREFLIGHT_MAX_SPREAD_PCT", str(defaults.preflight_max_spread_pct))),
            preflight_min_bid=float(os.getenv("PREFLIGHT_MIN_BID", str(defaults.preflight_min_bid))),
            spot_reward_pct=float(os.getenv("SPOT_REWARD_PCT", str(defaults.spot_reward_pct))),
            premium_stop_pts=float(os.getenv("PREMIUM_STOP_PTS", str(defaults.premium_stop_pts))),
            max_sl_pts=float(os.getenv("MAX_SL_PTS", str(defaults.max_sl_pts))),
            max_sl_premium_ratio=float(os.getenv("MAX_SL_PREMIUM_RATIO", str(defaults.max_sl_premium_ratio))),
        )

    def validate(self) -> list[str]:
        errs: list[str] = []
        if not (1 <= self.min_score <= 100):
            errs.append(f"MIN_SCORE={self.min_score} must be in [1, 100]")
        if not (0 <= self.max_trap <= 100):
            errs.append(f"MAX_TRAP={self.max_trap} must be in [0, 100]")
        if self.power_hour_score_factor <= 0:
            errs.append(f"POWER_HOUR_SCORE_FACTOR={self.power_hour_score_factor} must be > 0")
        if self.morning_score_factor <= 0:
            errs.append(f"MORNING_SCORE_FACTOR={self.morning_score_factor} must be > 0")
        if self.lot_multiplier < 1:
            errs.append(f"LOT_MULTIPLIER={self.lot_multiplier} must be >= 1")
        if not isinstance(self.gex_enabled, bool):
            errs.append(f"GEX_ENABLED={self.gex_enabled!r} must be boolean")
        if self.premium_stop_pts <= 0:
            errs.append(f"PREMIUM_STOP_PTS={self.premium_stop_pts} must be > 0")
        if self.max_sl_pts < 0:
            errs.append(f"MAX_SL_PTS={self.max_sl_pts} must be >= 0 (0 = use PREMIUM_STOP_PTS)")
        if self.max_sl_premium_ratio < 0 or self.max_sl_premium_ratio >= 100:
            errs.append(f"MAX_SL_PREMIUM_RATIO={self.max_sl_premium_ratio} must be in [0, 100)")
        if self.risk_percent <= 0:
            errs.append(f"RISK_PERCENT={self.risk_percent} must be > 0")
        if not (0 < self.delta_target_low < self.delta_target_high < 1):
            errs.append(f"DELTA_TARGET_LOW={self.delta_target_low} / DELTA_TARGET_HIGH={self.delta_target_high}: must satisfy 0 < low < high < 1")
        if self.iv_rank_max_entry <= 0 or self.iv_rank_max_entry > 100:
            errs.append(f"IV_RANK_MAX_ENTRY={self.iv_rank_max_entry} must be in (0, 100]")
        if self.iv_52w_low >= self.iv_52w_high:
            errs.append(f"IV_52W_LOW={self.iv_52w_low} must be < IV_52W_HIGH={self.iv_52w_high}")
        if self.asym_score_threshold <= 0 or self.asym_score_threshold >= 1:
            errs.append(f"ASYM_SCORE_THRESHOLD={self.asym_score_threshold} must be in (0, 1)")
        if self.delta_exit_threshold < 0 or self.delta_exit_threshold >= 1:
            errs.append(f"DELTA_EXIT_THRESHOLD={self.delta_exit_threshold} must be in [0, 1)")
        if self.oi_velocity_threshold < 0:
            errs.append(f"OI_VELOCITY_THRESHOLD={self.oi_velocity_threshold} must be >= 0")
        if self.max_entry_spread_pct < 0:
            errs.append(f"MAX_ENTRY_SPREAD_PCT={self.max_entry_spread_pct} must be >= 0")
        if self.max_strike_cum_loss_pts < 0:
            errs.append(f"MAX_STRIKE_CUM_LOSS_PTS={self.max_strike_cum_loss_pts} must be >= 0")
        if self.preflight_max_spread_pct < 0:
            errs.append(f"PREFLIGHT_MAX_SPREAD_PCT={self.preflight_max_spread_pct} must be >= 0")
        if self.preflight_min_bid < 0:
            errs.append(f"PREFLIGHT_MIN_BID={self.preflight_min_bid} must be >= 0")
        if self.adaptive_max_lot_mult < 1:
            errs.append(f"ADAPTIVE_MAX_LOT_MULT={self.adaptive_max_lot_mult} must be >= 1")
        if self.adaptive_win_streak_trigger < 1:
            errs.append(f"ADAPTIVE_WIN_STREAK_TRIGGER={self.adaptive_win_streak_trigger} must be >= 1")
        if self.adaptive_win_streak_step < 1:
            errs.append(f"ADAPTIVE_WIN_STREAK_STEP={self.adaptive_win_streak_step} must be >= 1")

        # ── Group 3: Indicator periods — zero = ta.* crash ──
        if self.fast_ema_period < 1 or self.slow_ema_period < 1 or self.rsi_period < 1:
            errs.append(f"Indicator periods must be >= 1 "
                        f"(fast_ema={self.fast_ema_period}, slow_ema={self.slow_ema_period}, "
                        f"rsi={self.rsi_period})")
        if self.fast_ema_period >= self.slow_ema_period:
            errs.append(f"FAST_EMA_PERIOD={self.fast_ema_period} must be < "
                        f"SLOW_EMA_PERIOD={self.slow_ema_period}")

        # ── Group 4: Filter/reward — 0 = sentinel (filter off / no LIMIT profit) ──
        if self.min_oi_filter < 0:
            errs.append(f"MIN_OI_FILTER={self.min_oi_filter} must be >= 0")
        if self.min_vol_filter < 0:
            errs.append(f"MIN_VOL_FILTER={self.min_vol_filter} must be >= 0")
        if self.spot_reward_pct < 0:
            errs.append(f"SPOT_REWARD_PCT={self.spot_reward_pct} must be >= 0")

        return errs

    def warnings(self) -> list[str]:
        """Soft warnings for non-fatal configuration edge cases."""
        ws: list[str] = []
        if self.max_sl_pts > 0 and self.max_sl_pts < self.premium_stop_pts:
            ws.append(
                f"MAX_SL_PTS={self.max_sl_pts} < PREMIUM_STOP_PTS={self.premium_stop_pts} — "
                f"adaptive ceiling would be TIGHTER than the no-data fallback, which is almost "
                f"certainly not intended. If deliberate, this warning can be ignored."
            )
        return ws

# ── 3d — RiskConfig ────────────────────────────────────────────────────────
@dataclass
class RiskConfig:
    """Session gates, loss limits, drawdown, capital. Set according to your strategy and risk appetite."""

    # ── Session Gates ──
    max_trades_per_session:  int   = 10
    max_consecutive_losses:  int   = 8
    entry_cooldown_secs:     int   = 300

    # ── Daily Limits ──
    max_daily_loss_pct:      float = 0.0
    max_daily_loss_amount:   float = 3600.0
    max_daily_profit_amount: float = 0.0

    # ── Drawdown ──
    drawdown_rate_enabled:    bool  = False
    drawdown_rate_window_mins: int  = 30
    drawdown_rate_max_loss:   float = 1000.0

    @classmethod
    def from_env(cls) -> "RiskConfig":
        defaults = cls()
        return cls(
            max_trades_per_session=int(os.getenv("MAX_TRADES_PER_SESSION", str(defaults.max_trades_per_session))),
            max_consecutive_losses=int(os.getenv("MAX_CONSECUTIVE_LOSSES", str(defaults.max_consecutive_losses))),
            entry_cooldown_secs=int(os.getenv("ENTRY_COOLDOWN_SECS", str(defaults.entry_cooldown_secs))),
            max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", str(defaults.max_daily_loss_pct))),
            max_daily_loss_amount=float(os.getenv("MAX_DAILY_LOSS_AMOUNT", str(defaults.max_daily_loss_amount))),
            max_daily_profit_amount=float(os.getenv("MAX_DAILY_PROFIT_AMOUNT", str(defaults.max_daily_profit_amount))),
            drawdown_rate_enabled=os.getenv("DRAWDOWN_RATE_ENABLED", str(defaults.drawdown_rate_enabled)).lower() in ("1", "true", "yes"),
            drawdown_rate_window_mins=int(os.getenv("DRAWDOWN_RATE_WINDOW_MINS", str(defaults.drawdown_rate_window_mins))),
            drawdown_rate_max_loss=float(os.getenv("DRAWDOWN_RATE_MAX_LOSS", str(defaults.drawdown_rate_max_loss))),
        )

    def validate(self) -> list[str]:
        errs: list[str] = []
        if self.drawdown_rate_window_mins < 1:
            errs.append(f"DRAWDOWN_RATE_WINDOW_MINS={self.drawdown_rate_window_mins} must be >= 1")
        if self.drawdown_rate_max_loss < 0:
            errs.append(f"DRAWDOWN_RATE_MAX_LOSS={self.drawdown_rate_max_loss} must be >= 0")
        if self.drawdown_rate_enabled and self.drawdown_rate_max_loss <= 0:
            errs.append("DRAWDOWN_RATE_ENABLED=True but DRAWDOWN_RATE_MAX_LOSS <= 0 — no effective limit")
        if self.max_daily_loss_amount <= 0 and self.max_daily_loss_pct <= 0:
            errs.append("All daily loss limits disabled (MAX_DAILY_LOSS_AMOUNT and "
                        "MAX_DAILY_LOSS_PCT are both ≤ 0) — no loss limit will be enforced")
        if self.max_trades_per_session < 0:
            errs.append(f"MAX_TRADES_PER_SESSION={self.max_trades_per_session} must be >= 0 (0 = unlimited)")
        if self.entry_cooldown_secs < 0:
            errs.append(f"ENTRY_COOLDOWN_SECS={self.entry_cooldown_secs} must be >= 0")
        if self.max_daily_profit_amount < 0:
            errs.append(f"MAX_DAILY_PROFIT_AMOUNT={self.max_daily_profit_amount} must be >= 0 (0 = disabled)")
        return errs


# ── 3e — TrailConfig ──────────────────────────────────────────────────────
@dataclass
class TrailConfig:
    """All trail modes, step sizing, activation, key-level, KER constants."""

    # ── Mode / Method ──
    tracking_mode:              str   = "premium"
    sl_method:                  str   = "atr"

    # ── Activation (When trail fires) ──
    activation_lock_pct:        float = 0.0     # 0 = breakeven only; >0 = floor X% above entry
    activate_at_pct:            float = 25.0    # trail fires when premium gains X% from entry
    activate_at_max_pts:        float = 30.0    # cap that `activate_at_pct`% at Xpts max

    # ── Generic Step Sizing (How tight is the ratchet?) ──
    step_pct:                   float = 10.0    # SL ratchets up every X% of entry premium
    step_pts:                   float = 15.0    # SL ratchets up every fixed X pts above activation

    # ── ATR ──
    atr_period:                      int   = 14
    atr_mult:                        float = 1.5
    atr_activation_buffer_pts:       float = 0.0
    atr_min_ratchet_improvement_pct: float = 0.5   # % of current peak premium

    # ── Delta ──
    delta_itm_step_pct:         float = 5.0
    delta_atm_step_pct:         float = 10.0
    delta_otm_step_pct:         float = 15.0

    # ── Key Level ──
    key_level_spacing: dict  = field(default_factory=lambda: {
        "NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50,
        "MIDCPNIFTY": 50, "SENSEX": 100, "BANKEX": 100,
    })
    key_level_trail_style:          str   = "capture_pct"
    key_level_capture_pct:          float = 25.0
    key_level_fixed_pts:            float = 15.0
    key_level_breakeven_after_levels: int = 1

    # ── Conviction / Gamma ──
    conv_trail_act_base:        float = 1.20
    conv_trail_act_range:       float = 0.40
    gamma_speed_step_floor:     float = 0.40

    @classmethod
    def from_env(cls) -> "TrailConfig":
        defaults = cls()
        return cls(
            # Mode / Method
            tracking_mode=os.getenv("TRAIL_TRACKING_MODE", defaults.tracking_mode).strip().lower(),
            sl_method=os.getenv("TRAIL_SL_METHOD", defaults.sl_method).strip().lower(),
            # Activation
            activation_lock_pct=float(os.getenv("TRAIL_ACTIVATION_LOCK_PCT", str(defaults.activation_lock_pct))),
            activate_at_pct=float(os.getenv("TRAIL_ACTIVATE_AT_PCT", str(defaults.activate_at_pct))),
            activate_at_max_pts=float(os.getenv("TRAIL_ACTIVATE_AT_MAX_PTS", str(defaults.activate_at_max_pts))),
            # Step Sizing
            step_pct=float(os.getenv("TRAIL_STEP_PCT", str(defaults.step_pct))),
            step_pts=float(os.getenv("TRAIL_STEP_PTS", str(defaults.step_pts))),
            # ATR
            atr_period=int(os.getenv("TRAIL_ATR_PERIOD", str(defaults.atr_period))),
            atr_mult=float(os.getenv("TRAIL_ATR_MULT", str(defaults.atr_mult))),
            atr_activation_buffer_pts=float(os.getenv("ATR_ACTIVATION_BUFFER_PTS", str(defaults.atr_activation_buffer_pts))),
            atr_min_ratchet_improvement_pct=float(os.getenv("ATR_MIN_RATCHET_IMPROVEMENT_PCT", str(defaults.atr_min_ratchet_improvement_pct))),
            # Delta
            delta_itm_step_pct=float(os.getenv("TRAIL_DELTA_ITM_STEP_PCT", str(defaults.delta_itm_step_pct))),
            delta_atm_step_pct=float(os.getenv("TRAIL_DELTA_ATM_STEP_PCT", str(defaults.delta_atm_step_pct))),
            delta_otm_step_pct=float(os.getenv("TRAIL_DELTA_OTM_STEP_PCT", str(defaults.delta_otm_step_pct))),
            # Key Level
            key_level_spacing=ast.literal_eval(os.getenv("KEY_LEVEL_SPACING", str(defaults.key_level_spacing))),
            key_level_trail_style=os.getenv("KEY_LEVEL_TRAIL_STYLE", defaults.key_level_trail_style).strip().lower(),
            key_level_capture_pct=float(os.getenv("KEY_LEVEL_CAPTURE_PCT", str(defaults.key_level_capture_pct))),
            key_level_fixed_pts=float(os.getenv("KEY_LEVEL_FIXED_PTS", str(defaults.key_level_fixed_pts))),
            key_level_breakeven_after_levels=int(os.getenv("KEY_LEVEL_BE_AFTER_LEVELS", str(defaults.key_level_breakeven_after_levels))),
            # Conviction / Gamma
            conv_trail_act_base=float(os.getenv("CONV_TRAIL_ACT_BASE", str(defaults.conv_trail_act_base))),
            conv_trail_act_range=float(os.getenv("CONV_TRAIL_ACT_RANGE", str(defaults.conv_trail_act_range))),
            gamma_speed_step_floor=float(os.getenv("GAMMA_SPEED_STEP_FLOOR", str(defaults.gamma_speed_step_floor))),
        )

    def validate(self) -> list[str]:
        errs: list[str] = []
        if self.tracking_mode not in ("premium", "spot"):
            errs.append(f"TRAIL_TRACKING_MODE={self.tracking_mode!r} must be 'premium' or 'spot'")
        if self.sl_method not in ("fixed_pct", "fixed_pts", "atr", "delta", "key_level"):
            errs.append(f"TRAIL_SL_METHOD={self.sl_method!r} must be 'fixed_pct', 'fixed_pts', 'atr', 'delta', or 'key_level'")
        if not (0.0 <= self.activation_lock_pct < 1.0):
            errs.append(f"TRAIL_ACTIVATION_LOCK_PCT={self.activation_lock_pct} must be in [0.0, 1.0)")
        if self.key_level_trail_style not in ("fixed", "capture_pct"):
            errs.append(f"KEY_LEVEL_TRAIL_STYLE={self.key_level_trail_style!r} must be 'fixed' or 'capture_pct'")
        if self.key_level_capture_pct < 0 or self.key_level_capture_pct > 100:
            errs.append(f"KEY_LEVEL_CAPTURE_PCT={self.key_level_capture_pct} must be [0, 100]")
        if self.key_level_fixed_pts <= 0:
            errs.append(f"KEY_LEVEL_FIXED_PTS={self.key_level_fixed_pts} must be > 0")
        if self.key_level_breakeven_after_levels < 0:
            errs.append(f"KEY_LEVEL_BE_AFTER_LEVELS={self.key_level_breakeven_after_levels} must be >= 0")
        if not (0.0 < self.gamma_speed_step_floor <= 1.0):
            errs.append(f"GAMMA_SPEED_STEP_FLOOR={self.gamma_speed_step_floor} must be in (0.0, 1.0]")
        if self.atr_activation_buffer_pts < 0:
            errs.append(f"ATR_ACTIVATION_BUFFER_PTS={self.atr_activation_buffer_pts} must be >= 0")
        if self.atr_min_ratchet_improvement_pct < 0:
            errs.append(f"ATR_MIN_RATCHET_IMPROVEMENT_PCT={self.atr_min_ratchet_improvement_pct} must be >= 0")

        # ── Group 1: ATR/step/delta sizing — zero always degenerate ──
        if self.atr_period < 1:
            errs.append(f"TRAIL_ATR_PERIOD={self.atr_period} must be >= 1")
        if self.atr_mult <= 0:
            errs.append(f"TRAIL_ATR_MULT={self.atr_mult} must be > 0")
        if self.step_pts <= 0:
            errs.append(f"TRAIL_STEP_PTS={self.step_pts} must be > 0")
        if self.step_pct <= 0:
            errs.append(f"TRAIL_STEP_PCT={self.step_pct} must be > 0")
        if self.delta_itm_step_pct <= 0:
            errs.append(f"TRAIL_DELTA_ITM_STEP_PCT={self.delta_itm_step_pct} must be > 0")
        if self.delta_atm_step_pct <= 0:
            errs.append(f"TRAIL_DELTA_ATM_STEP_PCT={self.delta_atm_step_pct} must be > 0")
        if self.delta_otm_step_pct <= 0:
            errs.append(f"TRAIL_DELTA_OTM_STEP_PCT={self.delta_otm_step_pct} must be > 0")

        # ── Group 2: Activation — 0 is valid for pct (immediate), NOT for max_pts ──
        if self.activate_at_pct < 0:
            errs.append(f"TRAIL_ACTIVATE_AT_PCT={self.activate_at_pct} must be >= 0")
        if self.activate_at_max_pts <= 0:
            errs.append(f"TRAIL_ACTIVATE_AT_MAX_PTS={self.activate_at_max_pts} must be > 0")

        return errs

# ── 3f — JournalConfig ────────────────────────────────────────────────────
@dataclass
class JournalConfig:
    """Trade journal file path and analytics flags."""
    trade_journal_path: str  = "/app/strategies/data/trades.csv"
    analytics_enabled:  bool = True

    @classmethod
    def from_env(cls) -> "JournalConfig":
        defaults = cls()
        return cls(
            trade_journal_path=os.getenv("TRADE_JOURNAL_PATH", defaults.trade_journal_path),
            analytics_enabled=os.getenv("ANALYTICS_ENABLED", str(defaults.analytics_enabled)).lower() in ("1", "true", "yes"),
        )

    @staticmethod
    def validate() -> list[str]:
        return []


# ── 3h — PositionConfig ─────────────────────────────────────────────────
@dataclass
class PositionConfig:
    """Controls multi-position behaviour per underlying.
    Default = current 1:1 single-position behaviour.
    Activate via env vars for multi-position, opposite-side, same-direction add."""
    max_positions_per_underlying:  int   = 1
    allow_simultaneous_ce_pe:      bool  = False
    opposite_side_exit_on_signal:  bool  = False
    same_direction_add_on_signal:  bool  = False
    same_direction_min_conviction: float = 0.0
    signal_parallel_exit:          bool  = True
    max_total_positions:           int   = 1

    @classmethod
    def from_env(cls) -> "PositionConfig":
        defaults = cls()
        return cls(
            max_positions_per_underlying=int(
                os.getenv("MAX_POSITIONS_PER_UNDERLYING", str(defaults.max_positions_per_underlying))),
            allow_simultaneous_ce_pe=os.getenv("ALLOW_SIMULTANEOUS_CE_PE", str(defaults.allow_simultaneous_ce_pe)).lower() in ("1", "true", "yes"),
            opposite_side_exit_on_signal=os.getenv("OPPOSITE_SIDE_EXIT_ON_SIGNAL", str(defaults.opposite_side_exit_on_signal)).lower() in ("1", "true", "yes"),
            same_direction_add_on_signal=os.getenv("SAME_DIRECTION_ADD_ON_SIGNAL", str(defaults.same_direction_add_on_signal)).lower() in ("1", "true", "yes"),
            same_direction_min_conviction=float(
                os.getenv("SAME_DIRECTION_MIN_CONVICTION", str(defaults.same_direction_min_conviction))),
            signal_parallel_exit=os.getenv("SIGNAL_PARALLEL_EXIT", str(defaults.signal_parallel_exit)).lower() in ("1", "true", "yes"),
            max_total_positions=int(
                os.getenv("MAX_TOTAL_POSITIONS", str(defaults.max_total_positions))),
        )

    def validate(self) -> list[str]:
        errs: list[str] = []
        if self.max_positions_per_underlying < 1:
            errs.append("MAX_POSITIONS_PER_UNDERLYING must be >= 1")
        if self.max_total_positions < self.max_positions_per_underlying:
            errs.append("MAX_TOTAL_POSITIONS must be >= MAX_POSITIONS_PER_UNDERLYING")
        if self.allow_simultaneous_ce_pe and self.max_positions_per_underlying < 2:
            errs.append(
                "ALLOW_SIMULTANEOUS_CE_PE=True requires MAX_POSITIONS_PER_UNDERLYING >= 2"
            )
        return errs


# ── 3i — TrancheConfig ───────────────────────────────────────────────────
@dataclass
class TrancheConfig:
    """Controls partial-exit ladder. Disabled by default (full exit = current behaviour).
    Meaningful only when qty >= min_qty_per_tranche * number_of_tranches."""

    # ── Mode ──
    enabled:              bool  = False
    mode:                 str   = "equal"

    # ── Structure ──
    number_of_tranches:   int   = 3
    min_qty_per_tranche:  int   = 1

    # ── Quantity Split ──
    tp1_pct:              float = 33.0
    tp2_pct:              float = 33.0
    runner_pct:           float = 34.0

    # ── Target Ceiling ──
    tp_ceiling_pct:       float = 85.0    # last non-runner TP as % of full target gain

    @classmethod
    def from_env(cls) -> "TrancheConfig":
        defaults = cls()
        return cls(
            enabled=os.getenv("TRANCHE_ENABLED", str(defaults.enabled)).lower() in ("1", "true", "yes"),
            mode=os.getenv("TRANCHE_MODE", defaults.mode).strip().lower(),
            number_of_tranches=int(os.getenv("TRANCHE_NUMBER_OF_TRANCHES", str(defaults.number_of_tranches))),
            tp1_pct=float(os.getenv("TRANCHE_TP1_PCT", str(defaults.tp1_pct))),
            tp2_pct=float(os.getenv("TRANCHE_TP2_PCT", str(defaults.tp2_pct))),
            runner_pct=float(os.getenv("TRANCHE_RUNNER_PCT", str(defaults.runner_pct))),
            min_qty_per_tranche=int(os.getenv("TRANCHE_MIN_QTY", str(defaults.min_qty_per_tranche))),
            tp_ceiling_pct=float(os.getenv("TRANCHE_TP_CEILING_PCT", str(defaults.tp_ceiling_pct))),
        )

    def validate(self) -> list[str]:
        errs: list[str] = []
        if self.min_qty_per_tranche < 1:
            errs.append(f"TRANCHE_MIN_QTY={self.min_qty_per_tranche} must be >= 1")
        if self.tp_ceiling_pct < 50 or self.tp_ceiling_pct > 100:
            errs.append(f"TRANCHE_TP_CEILING_PCT={self.tp_ceiling_pct} must be in [50, 100]")
        if self.enabled:
            for _name, _val in (("TRANCHE_TP1_PCT", self.tp1_pct),
                                 ("TRANCHE_TP2_PCT", self.tp2_pct),
                                 ("TRANCHE_RUNNER_PCT", self.runner_pct)):
                if _val < 0 or _val > 100:
                    errs.append(f"{_name}={_val} must be in [0, 100]")
            total = self.tp1_pct + self.tp2_pct + self.runner_pct
            if abs(total - 100.0) > 0.1:
                errs.append(
                    f"TRANCHE_TP1_PCT + TRANCHE_TP2_PCT + TRANCHE_RUNNER_PCT "
                    f"must sum to 100 (got {total:.1f})"
                )
            if self.mode not in ("equal", "ladder"):
                errs.append(f"TRANCHE_MODE must be 'equal' or 'ladder' (got {self.mode!r})")
            if self.mode == "equal" and self.number_of_tranches < 2:
                errs.append(f"TRANCHE_NUMBER_OF_TRANCHES must be >= 2 for equal mode (got {self.number_of_tranches})")
        return errs


# ── 3j — SignalConfig ──────────────────────────────────────────────────
@dataclass
class SignalConfig:
    """Controls signal-generation layer parameters.
    All env vars optional; defaults produce backward-compatible behaviour.
    Shadow mode = new specs score_max=0 so they log but don't affect score."""

    # ── RVOL-Simple ──
    rvol_lookback:              int   = 14

    # ── OI Z-score ──
    oi_z_buffer_maxlen:         int   = 30

    # ── OI Rejection Zone ──
    oi_zone_z_threshold:        float = 1.0
    oi_zone_z_climax:           float = 2.0
    oi_zone_min_touch:          int   = 2
    wall_reject_pct:            float = 0.3
    oi_zone_wall_proximity_pts: float = 50.0
    oi_zone_lookback_scans:     int   = 10

    # ── Shadow mode ──
    shadow_mode_enabled:        bool  = True

    @classmethod
    def from_env(cls) -> "SignalConfig":
        defaults = cls()
        return cls(
            rvol_lookback=int(
                os.getenv("RVOL_LOOKBACK", str(defaults.rvol_lookback))),
            oi_z_buffer_maxlen=int(
                os.getenv("OI_Z_BUFFER_MAXLEN", str(defaults.oi_z_buffer_maxlen))),
            oi_zone_z_threshold=float(
                os.getenv("OI_ZONE_Z_THRESHOLD", str(defaults.oi_zone_z_threshold))),
            oi_zone_z_climax=float(
                os.getenv("OI_ZONE_Z_CLIMAX", str(defaults.oi_zone_z_climax))),
            oi_zone_min_touch=int(
                os.getenv("OI_ZONE_MIN_TOUCH", str(defaults.oi_zone_min_touch))),
            wall_reject_pct=float(
                os.getenv("WALL_REJECT_PCT", str(defaults.wall_reject_pct))),
            oi_zone_wall_proximity_pts=float(
                os.getenv("OI_ZONE_WALL_PROXIMITY_PTS", str(defaults.oi_zone_wall_proximity_pts))),
            oi_zone_lookback_scans=int(
                os.getenv("OI_ZONE_LOOKBACK_SCANS", str(defaults.oi_zone_lookback_scans))),
            shadow_mode_enabled=os.getenv("SHADOW_MODE_ENABLED",
                str(defaults.shadow_mode_enabled)).lower() in ("1", "true", "yes"),
        )

    def validate(self) -> list[str]:
        errs: list[str] = []
        if self.rvol_lookback < 2:
            errs.append("RVOL_LOOKBACK must be >= 2")
        if self.oi_z_buffer_maxlen < 5:
            errs.append("OI_Z_BUFFER_MAXLEN must be >= 5")
        if self.oi_zone_z_threshold <= 0:
            errs.append("OI_ZONE_Z_THRESHOLD must be > 0")
        if self.oi_zone_z_climax <= self.oi_zone_z_threshold:
            errs.append("OI_ZONE_Z_CLIMAX must be > OI_ZONE_Z_THRESHOLD")
        if self.oi_zone_min_touch < 1:
            errs.append("OI_ZONE_MIN_TOUCH must be >= 1")
        if not 0 < self.wall_reject_pct <= 1.0:
            errs.append("WALL_REJECT_PCT must be in (0, 1.0]")
        if self.oi_zone_wall_proximity_pts <= 0:
            errs.append("OI_ZONE_WALL_PROXIMITY_PTS must be > 0")
        if self.oi_zone_lookback_scans < self.oi_zone_min_touch:
            errs.append("OI_ZONE_LOOKBACK_SCANS must be >= OI_ZONE_MIN_TOUCH")
        return errs


# ── BotConfig (thin container — no __getattr__, explicit accessors) ────────
@dataclass
class BotConfig:
    """Thin container holding the 9 sub-config dataclasses.
    Access fields via cfg.broker.xxx, cfg.market.xxx, cfg.entry.xxx, etc."""
    broker:   BrokerConfig   = field(default_factory=BrokerConfig)
    market:   MarketConfig   = field(default_factory=MarketConfig)
    entry:    EntryConfig    = field(default_factory=EntryConfig)
    risk:     RiskConfig     = field(default_factory=RiskConfig)
    trail:    TrailConfig    = field(default_factory=TrailConfig)
    journal:  JournalConfig  = field(default_factory=JournalConfig)
    position: PositionConfig = field(default_factory=PositionConfig)
    tranche:  TrancheConfig  = field(default_factory=TrancheConfig)
    signal:   SignalConfig   = field(default_factory=SignalConfig)

    @classmethod
    def from_env(cls) -> "BotConfig":
        broker   = BrokerConfig.from_env()
        market   = MarketConfig.from_env()
        entry    = EntryConfig.from_env()
        risk     = RiskConfig.from_env()
        trail    = TrailConfig.from_env()
        journal  = JournalConfig.from_env()
        position = PositionConfig.from_env()
        tranche  = TrancheConfig.from_env()
        signal   = SignalConfig.from_env()

        # ── Cross-config: WebSocket URL auto-correction ──────────────────────
        _ws_domain = broker.api_host[8:].split("/")[0] if broker.api_host.startswith("https://") else ""
        _is_plain_ws_for_https = (
            broker.ws_url
            and _ws_domain
            and broker.ws_url.startswith("ws://")
            and "127.0.0.1" not in broker.ws_url
            and "localhost" not in broker.ws_url
        )
        if _is_plain_ws_for_https:
            _corrected = f"wss://{_ws_domain}/ws"
            inf(
                f"[CONFIG] WARNING: WEBSOCKET_URL='{broker.ws_url}' auto-corrected to '{_corrected}'."
                f"\n[CONFIG]          Update your .env: WEBSOCKET_URL={_corrected}"
            )
            broker.ws_url = _corrected
        if not broker.ws_url:
            broker.ws_url = "ws://127.0.0.1:8765"

        # ── Cross-config: unclassified underlying warning ────────────────────
        _known_equity = {"RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN", "INFY", "TCS"}
        _unclassified = [s for s in market.underlyings if s not in market.index_underlyings and s not in _known_equity]
        if _unclassified:
            inf(
                f"[CONFIG] WARNING: {_unclassified} are in UNDERLYINGS but not in "
                "INDEX_UNDERLYINGS. If these are index symbols they will be routed via "
                f"SPOT_EXCHANGE ({market.spot_exchange}) which may cause bad data. "
                "Add them to INDEX_UNDERLYINGS if they are indices."
            )

        return cls(broker=broker, market=market, entry=entry, risk=risk,
                   trail=trail, journal=journal,
                   position=position, tranche=tranche,
                   signal=signal)

    def validate(self) -> None:
        """Aggregate validation from all sub-configs. Raises SystemExit on errors."""
        errors: list[str] = []
        for sc in (self.broker, self.market, self.entry, self.risk,
                   self.trail, self.journal,
                   self.position, self.tranche, self.signal):
            try:
                errors.extend(sc.validate())
            except Exception as e:
                errors.append(f"[{type(sc).__name__}] validate() raised: {e}")
        if errors:
            inf("[CONFIG] Startup validation failed:")
            for e in errors:
                inf(f"  \u2717 {e}")
            raise SystemExit(
                "Fix the configuration errors above before running. "
                "See env-var comments at the top of the file."
            )
        inf("[CONFIG] All configuration values validated OK")
        for sc in (self.broker, self.market, self.entry, self.risk,
                   self.trail, self.journal,
                   self.position, self.tranche, self.signal):
            for w in (getattr(sc, "warnings", lambda: [])()):
                inf(f"[CONFIG] WARNING: {w}")

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 4 — POSITION STATE        ScoreComponent / SignalResult /   ║
# ║    PositionCore / PositionBroker / TrailState / KeyLevelState        ║
# ║    OptionPosition / PendingEntry / PendingExit / TradeRecord         ║
# ╚══════════════════════════════════════════════════════════════════════╝

class RollingZ:
    __slots__ = ("_buf", "_maxlen")
    def __init__(self, maxlen: int = 30):
        self._buf: deque = deque(maxlen=maxlen)
        self._maxlen = maxlen
    def add(self, v: float) -> None:
        self._buf.append(v)
    def z_score(self, v: float) -> float | None:
        if len(self._buf) < self._maxlen:
            return None
        s = sorted(self._buf)
        n = len(s)
        q25, q75 = s[n // 4], s[n * 3 // 4]
        iqr = q75 - q25
        mh = (q25 + q75) / 2.0
        if iqr < 1e-12:
            sigma = (sum((x - mh) ** 2 for x in s) / (n - 1)) ** 0.5
        else:
            sigma = iqr / 1.349
        return (v - mh) / sigma if sigma > 1e-12 else 0.0
    def __len__(self) -> int:
        return len(self._buf)


@dataclass
class ScoreComponent:
    label:     str
    score:     float
    score_max: float
    direction: str
    note:      str
    available: bool = True


@dataclass
class IndicatorSpec:
    """One self-contained technical indicator for the scoring registry."""
    name:      str
    min_bars:  int | Callable = 5
    compute:   Callable[[pd.DataFrame, Any], dict[str, Any] | None] = lambda df, cfg: None
    score:     Callable[[dict[str, Any], Any], tuple[float, str]] = lambda raw, cfg: (0, "")
    score_max: float = 1.0

    def evaluate(self, df_spot: pd.DataFrame, cfg: Any) -> ScoreComponent:
        n_bars = self.min_bars(cfg) if callable(self.min_bars) else self.min_bars
        if df_spot is None or len(df_spot) < n_bars:
            return ScoreComponent(self.name, 0, self.score_max, "neutral", f"{self.name} unavailable", available=False)
        raw = self.compute(df_spot, cfg)
        if raw is None:
            return ScoreComponent(self.name, 0, self.score_max, "neutral", f"{self.name} unavailable", available=False)
        s, note = self.score(raw, cfg)
        direction = "bullish" if s > 0 else "bearish" if s < 0 else "neutral"
        return ScoreComponent(self.name, s, self.score_max, direction, note)


@dataclass
class StatisticSpec:
    """One self-contained market statistic for the scoring registry.
    Unlike IndicatorSpec, statistics are point-in-time (not bar-series).
    compute() accepts a context dict (all score params) and an intermediates
    dict shared across the spec chain for cross-spec values (pcr, s6, s7, …).
    """
    name:      str
    compute:   Callable[[dict, Any, dict], tuple[float, str] | None]
    score_max: float = 1.0

    def evaluate(self, ctx: dict, cfg: Any, intermediates: dict) -> ScoreComponent:
        result = self.compute(ctx, cfg, intermediates)
        if result is None:
            return ScoreComponent(self.name, 0, self.score_max, "neutral", f"{self.name} unavailable", available=False)
        s, note = result
        direction = "bullish" if s > 0 else "bearish" if s < 0 else "neutral"
        return ScoreComponent(self.name, s, self.score_max, direction, note)


@dataclass
class SignalResult:
    score:        int
    label:        str
    signal:       str
    direction:    str | None
    trap_score:   int
    trap_reasons: list[str]
    reasons:      list[str]
    components:   list[ScoreComponent]


def get_ist_now() -> datetime:
    """Return current IST datetime, works regardless of system timezone.
    Uses _time_mod to compute offset if system is not IST.
    """
    try:
        # Compute offset between local time and UTC
        _tz_off = (_time_mod.mktime(_time_mod.localtime()) - _time_mod.mktime(_time_mod.gmtime())) / 3600
        if abs(_tz_off - 5.5) < 0.1:
            return datetime.now()
        else:
            return datetime.utcnow() + timedelta(hours=5.5)
    except Exception:
        return datetime.now()

@dataclass
class PositionCore:
    """Entry-level position data — immutable post-creation."""
    slot_id:         str
    underlying:      str
    symbol:          str
    entry_premium:   float
    qty:             int
    option_type:     str
    spot_symbol:     str
    spot_entry:      float
    reward_dist:     float
    entry_delta:     float | None  = None
    moneyness:       str           = "Unknown"
    initial_sl:      float         = 0.0
    tgt:             float         = 0.0
    entry_time:      datetime      = field(default_factory=get_ist_now)
    entry_conviction: float        = 0.0
    trail_act_mult:  float         = 1.0
    entry_bucket:    int           = 0
    entry_sl_source: str           = ""


@dataclass
class PositionBroker:
    """Broker-level order handles and exit state."""
    sl_order_id:      str | None = None
    tgt_order_id:     str | None = None
    broker_protection: bool      = False
    exit_pending:     bool      = False


class LifecycleStage(Enum):
    """Formal lifecycle stages for a long-options position."""
    ENTRY = "entry"
    INITIAL_PROTECTED = "initial_protected"
    ACTIVATED = "activated"
    LOCKED = "locked"
    RATCHETING = "ratcheting"
    PROFIT_LOCK = "profit_lock"
    KEY_LEVEL = "key_level"
    EXIT_PENDING = "exit_pending"
    CLOSED = "closed"


_TRANSITIONS: dict[LifecycleStage, set[LifecycleStage]] = {
    LifecycleStage.ENTRY:             {LifecycleStage.INITIAL_PROTECTED, LifecycleStage.EXIT_PENDING, LifecycleStage.CLOSED},
    LifecycleStage.INITIAL_PROTECTED: {LifecycleStage.ACTIVATED, LifecycleStage.EXIT_PENDING, LifecycleStage.CLOSED},
    LifecycleStage.ACTIVATED:         {LifecycleStage.LOCKED, LifecycleStage.RATCHETING, LifecycleStage.PROFIT_LOCK,
                                        LifecycleStage.KEY_LEVEL, LifecycleStage.EXIT_PENDING, LifecycleStage.CLOSED},
    LifecycleStage.LOCKED:            {LifecycleStage.RATCHETING, LifecycleStage.PROFIT_LOCK,
                                        LifecycleStage.KEY_LEVEL, LifecycleStage.EXIT_PENDING, LifecycleStage.CLOSED},
    LifecycleStage.RATCHETING:        {LifecycleStage.PROFIT_LOCK, LifecycleStage.KEY_LEVEL,
                                        LifecycleStage.EXIT_PENDING, LifecycleStage.CLOSED},
    LifecycleStage.PROFIT_LOCK:       {LifecycleStage.KEY_LEVEL, LifecycleStage.EXIT_PENDING, LifecycleStage.CLOSED},
    LifecycleStage.KEY_LEVEL:         {LifecycleStage.EXIT_PENDING, LifecycleStage.CLOSED},
    LifecycleStage.EXIT_PENDING:      {LifecycleStage.CLOSED},
}


def _safe_transition(current: LifecycleStage, target: LifecycleStage) -> bool:
    """Returns True if the transition is allowed by the state machine."""
    allowed = _TRANSITIONS.get(current)
    if allowed is None or target not in allowed:
        err(f"[LIFECYCLE] Illegal transition: {current.value} -> {target.value}")
        return False
    return True


def _advance_stage(pos: "OptionPosition", target: LifecycleStage) -> bool:
    """Idempotent, validated stage transition. No-op (no error log) if already
    at target; otherwise delegates to _safe_transition for legality and stamps
    stage_entered_at on success. Returns True iff the stage actually changed."""
    inf(f"[LIFECYCLE] Attempting to transition {pos.trail.stage.value} -> {target.value}")
    if pos.trail.stage == target or not _safe_transition(pos.trail.stage, target):
        return False
    pos.trail.stage = target
    pos.trail.stage_entered_at = time.monotonic()
    return True


def _calc_pnl(pos: "OptionPosition", price: float, qty: int | None = None) -> float:
    """Compute PnL = (price - entry_premium) * qty, defaulting to remaining_qty.
    Pure formula extraction — used by all 12 PnL formula sites and the
    _finalize_exit helper. Zero risk: same math, no side effects."""
    return (price - pos.entry_premium) * (qty if qty is not None else pos.remaining_qty)


@dataclass
class TrailState:
    """Active trail state — modified by TrailSLEngine and WS breach checks."""
    sl:                   float         = 0.0
    trail_active:         bool          = False
    trail_peak:           float | None  = None
    trail_sl_spot:        float | None  = None
    premium_trail_active: bool          = False
    premium_trail_peak:   float | None  = None
    premium_trail_sl:     float | None  = None
    trail_activation_sl:  float | None  = None
    trail_peak_close:     float | None  = None
    breakeven_moved:      bool          = False
    activation_price:     float | None  = None
    stage:                LifecycleStage = LifecycleStage.ENTRY
    stage_entered_at:     float         = 0.0


@dataclass
class KeyLevelState:
    """Key-level trail state — split from TrailState per V1 plan."""
    kl_active:           bool          = False
    kl_next_level:       float | None  = None
    kl_levels_completed: int           = 0
    kl_level_premium:    float | None  = None


@dataclass
class PositionAnalytics:
    """Post-trade and intra-trade analytics — updated by trail engine."""
    activation_time:       datetime | None = None
    activation_bucket:     int | None    = None
    exit_bucket:           int | None    = None
    peak_after_activation: float | None  = None
    mfe:                   float         = 0.0
    mae_after_activation:  float | None  = None


@dataclass
class Tranche:
    """One slice of a position — allocated qty, broker order handles, fill state."""
    tranche_id:     str
    qty:            int
    sl:             float
    initial_sl:     float
    sl_order_id:    str | None  = None
    tgt_order_id:   str | None  = None
    is_exit_placed: bool        = False
    exit_price:     float | None = None
    exit_reason:    str | None  = None
    is_runner:      bool        = False
    tp_pts:         float | None = None



class OptionPosition:
    """Explicit delegation container with 5 sub-objects.  Access via pos.sub.xxx.
    @property pass-throughs provided for backward compatibility with pos.xxx notation."""

    def __init__(self, core: PositionCore, broker: PositionBroker,
                 trail: TrailState, kl: KeyLevelState,
                 analytics: PositionAnalytics,
                 tranches: list[Tranche] | None = None):
        self.core      = core
        self.broker    = broker
        self.trail     = trail
        self.kl        = kl
        self.analytics = analytics
        self.tranches  = tranches or []

    @classmethod
    def build(cls, *, underlying, symbol, entry_premium, qty, option_type,
              spot_symbol, spot_entry, reward_dist,
              entry_delta=None, moneyness="Unknown",
              sl=0.0, initial_sl=0.0, tgt=0.0,
              entry_time=None, entry_conviction=0.0, trail_act_mult=1.0,
              entry_bucket=0, slot_id=None,
              entry_sl_source="") -> "OptionPosition":
        _ts = int(time.time() * 1_000_000)
        _sid = slot_id or f"{underlying}_{option_type}_{_ts}"
        _ep = entry_premium
        return cls(
            core=PositionCore(
                slot_id=_sid, underlying=underlying, symbol=symbol,
                entry_premium=_ep, qty=qty, option_type=option_type,
                spot_symbol=spot_symbol, spot_entry=spot_entry, reward_dist=reward_dist,
                entry_delta=entry_delta, moneyness=moneyness,
                initial_sl=initial_sl, tgt=tgt,
                entry_time=entry_time or get_ist_now(),
                entry_conviction=entry_conviction, trail_act_mult=trail_act_mult,
                entry_bucket=entry_bucket, entry_sl_source=entry_sl_source,
            ),
            broker=PositionBroker(),
            trail=TrailState(sl=sl),
            kl=KeyLevelState(),
            analytics=PositionAnalytics(),
        )

    # ── @property pass-throughs ─────────────────────────────────────────────
    # PositionCore
    @property
    def underlying(self) -> str: return self.core.underlying
    @property
    def slot_id(self) -> str: return self.core.slot_id
    @property
    def symbol(self) -> str: return self.core.symbol
    @property
    def entry_premium(self) -> float: return self.core.entry_premium
    @property
    def qty(self) -> int: return self.core.qty
    @property
    def option_type(self) -> str: return self.core.option_type
    @property
    def spot_symbol(self) -> str: return self.core.spot_symbol
    @property
    def spot_entry(self) -> float: return self.core.spot_entry
    @property
    def reward_dist(self) -> float: return self.core.reward_dist
    @property
    def entry_delta(self) -> float | None: return self.core.entry_delta
    @entry_delta.setter
    def entry_delta(self, val): self.core.entry_delta = val
    @property
    def moneyness(self) -> str: return self.core.moneyness
    @moneyness.setter
    def moneyness(self, val): self.core.moneyness = val
    @property
    def initial_sl(self) -> float: return self.core.initial_sl
    @property
    def tgt(self) -> float: return self.core.tgt
    @tgt.setter
    def tgt(self, val): self.core.tgt = val
    @property
    def entry_time(self): return self.core.entry_time
    @property
    def entry_conviction(self) -> float: return self.core.entry_conviction
    @entry_conviction.setter
    def entry_conviction(self, val): self.core.entry_conviction = val
    @property
    def trail_act_mult(self) -> float: return self.core.trail_act_mult
    @trail_act_mult.setter
    def trail_act_mult(self, val): self.core.trail_act_mult = val
    # PositionBroker
    @property
    def sl_order_id(self) -> str | None: return self.broker.sl_order_id
    @sl_order_id.setter
    def sl_order_id(self, val): self.broker.sl_order_id = val
    @property
    def tgt_order_id(self) -> str | None:
        rt = self.runner_tranche
        return rt.tgt_order_id if rt else None
    @tgt_order_id.setter
    def tgt_order_id(self, val):
        rt = self.runner_tranche
        if rt:
            rt.tgt_order_id = val
    @property
    def broker_protection(self) -> bool: return self.broker.broker_protection
    @broker_protection.setter
    def broker_protection(self, val): self.broker.broker_protection = val
    @property
    def exit_pending(self) -> bool: return self.broker.exit_pending
    @exit_pending.setter
    def exit_pending(self, val): self.broker.exit_pending = val
    # TrailState
    @property
    def sl(self) -> float: return self.trail.sl
    @sl.setter
    def sl(self, val): self.trail.sl = val
    @property
    def trail_active(self) -> bool: return self.trail.trail_active
    @trail_active.setter
    def trail_active(self, val): self.trail.trail_active = val
    @property
    def trail_peak(self) -> float | None: return self.trail.trail_peak
    @trail_peak.setter
    def trail_peak(self, val): self.trail.trail_peak = val
    @property
    def trail_sl_spot(self) -> float | None: return self.trail.trail_sl_spot
    @trail_sl_spot.setter
    def trail_sl_spot(self, val): self.trail.trail_sl_spot = val
    @property
    def premium_trail_active(self) -> bool: return self.trail.premium_trail_active
    @premium_trail_active.setter
    def premium_trail_active(self, val): self.trail.premium_trail_active = val
    @property
    def premium_trail_peak(self) -> float | None: return self.trail.premium_trail_peak
    @premium_trail_peak.setter
    def premium_trail_peak(self, val): self.trail.premium_trail_peak = val
    @property
    def premium_trail_sl(self) -> float | None: return self.trail.premium_trail_sl
    @premium_trail_sl.setter
    def premium_trail_sl(self, val): self.trail.premium_trail_sl = val
    @property
    def trail_activation_sl(self) -> float | None: return self.trail.trail_activation_sl
    @trail_activation_sl.setter
    def trail_activation_sl(self, val): self.trail.trail_activation_sl = val
    @property
    def trail_peak_close(self) -> float | None: return self.trail.trail_peak_close
    @trail_peak_close.setter
    def trail_peak_close(self, val): self.trail.trail_peak_close = val
    @property
    def breakeven_moved(self) -> bool: return self.trail.breakeven_moved
    @breakeven_moved.setter
    def breakeven_moved(self, val): self.trail.breakeven_moved = val
    @property
    def activation_price(self) -> float | None: return self.trail.activation_price
    @activation_price.setter
    def activation_price(self, val): self.trail.activation_price = val
    # KeyLevelState
    @property
    def kl_active(self) -> bool: return self.kl.kl_active
    @kl_active.setter
    def kl_active(self, val): self.kl.kl_active = val
    @property
    def kl_next_level(self) -> float | None: return self.kl.kl_next_level
    @kl_next_level.setter
    def kl_next_level(self, val): self.kl.kl_next_level = val
    @property
    def kl_levels_completed(self) -> int: return self.kl.kl_levels_completed
    @kl_levels_completed.setter
    def kl_levels_completed(self, val): self.kl.kl_levels_completed = val
    @property
    def kl_level_premium(self) -> float | None: return self.kl.kl_level_premium
    @kl_level_premium.setter
    def kl_level_premium(self, val): self.kl.kl_level_premium = val
    # PositionAnalytics
    @property
    def activation_time(self): return self.analytics.activation_time
    @activation_time.setter
    def activation_time(self, val): self.analytics.activation_time = val
    @property
    def entry_bucket(self) -> int: return self.core.entry_bucket
    @property
    def entry_sl_source(self) -> str: return self.core.entry_sl_source
    @entry_sl_source.setter
    def entry_sl_source(self, val): self.core.entry_sl_source = val
    @property
    def activation_bucket(self) -> int | None: return self.analytics.activation_bucket
    @activation_bucket.setter
    def activation_bucket(self, val): self.analytics.activation_bucket = val
    @property
    def exit_bucket(self) -> int | None: return self.analytics.exit_bucket
    @exit_bucket.setter
    def exit_bucket(self, val): self.analytics.exit_bucket = val
    @property
    def peak_after_activation(self) -> float | None: return self.analytics.peak_after_activation
    @peak_after_activation.setter
    def peak_after_activation(self, val): self.analytics.peak_after_activation = val
    @property
    def mfe(self) -> float: return self.analytics.mfe
    @mfe.setter
    def mfe(self, val): self.analytics.mfe = val
    @property
    def mae_after_activation(self) -> float | None: return self.analytics.mae_after_activation
    @mae_after_activation.setter
    def mae_after_activation(self, val): self.analytics.mae_after_activation = val
    # Tranche helpers
    @property
    def runner_tranche(self) -> "Tranche | None":
        for t in self.tranches:
            if t.is_runner:
                return t
        return None

    @property
    def remaining_qty(self) -> int:
        if not self.tranches:
            return self.core.qty
        return sum(t.qty for t in self.tranches if not t.is_exit_placed)

    @property
    def open_tranches(self) -> list["Tranche"]:
        return [t for t in self.tranches if not t.is_exit_placed]


def _build_tranches(pos: OptionPosition, qty: int, cfg: BotConfig) -> list[Tranche]:
    """Build tranche list from config. Single-tranche collapse when disabled or qty too small."""
    tc = cfg.tranche
    _min_required = (tc.min_qty_per_tranche * tc.number_of_tranches if tc.mode == "equal"
                     else tc.min_qty_per_tranche * 3)
    if not tc.enabled or qty < _min_required:
        return [Tranche(
            tranche_id=f"{pos.slot_id}_0", qty=qty,
            sl=pos.sl, initial_sl=pos.initial_sl, is_runner=True,
            tp_pts=pos.tgt,
        )]
    if tc.mode == "equal":
        n = tc.number_of_tranches
        base = qty // n
        rem  = qty % n
        result = []
        _full_gain = pos.tgt - pos.entry_premium
        _last_frac = tc.tp_ceiling_pct / 100.0
        _spread = _last_frac - 0.5
        _non_runner_slots = max(1, n - 1)  # how many non-runner steps to 100%
        for i in range(n):
            tq = base + (1 if i < rem else 0)
            if tq <= 0:
                continue
            if i == n - 1:
                _tp = pos.tgt  # runner — full target
            else:
                # Distribute non-runner targets evenly from 50% → tp_ceiling_pct
                _frac = 0.5 + _spread * i / max(0.001, _non_runner_slots - 1)
                _tp = pos.entry_premium + _full_gain * min(_frac, 1.0)
            result.append(Tranche(
                tranche_id=f"{pos.slot_id}_{i}", qty=tq,
                sl=pos.sl, initial_sl=pos.initial_sl,
                is_runner=(i == n - 1),
                tp_pts=_tp,
            ))
        if result and not any(t.is_runner for t in result):
            result[-1].is_runner = True
        return result
    if tc.mode == "ladder":
        tp1_qty = int(qty * tc.tp1_pct / 100)
        tp2_qty = int(qty * tc.tp2_pct / 100)
        runner_qty = qty - tp1_qty - tp2_qty
        result = []
        _full_gain = pos.tgt - pos.entry_premium
        _last_frac = tc.tp_ceiling_pct / 100.0
        # Ladder: fixed tp1/tp2/runner slots, distribute targets dynamically
        _tier_slots = [(tp1_qty, "tp1", 0.5), (tp2_qty, "tp2", _last_frac)]
        _active_non_runner = sum(1 for q, _, _ in _tier_slots if q > 0)
        for _qty, _name, _base_frac in _tier_slots:
            if _qty <= 0:
                continue
            _frac = _base_frac  # 0.5 for first, tp_ceiling_pct for second
            if _active_non_runner == 1:
                _frac = 0.5  # single non-runner → 50%
            result.append(Tranche(
                tranche_id=f"{pos.slot_id}_{_name}", qty=_qty,
                sl=pos.sl, initial_sl=pos.initial_sl,
                tp_pts=pos.entry_premium + _full_gain * _frac,
            ))
        if runner_qty > 0:
            result.append(Tranche(
                tranche_id=f"{pos.slot_id}_runner", qty=runner_qty,
                sl=pos.sl, initial_sl=pos.initial_sl, is_runner=True,
                tp_pts=pos.tgt,
            ))
        return result
    return []

@dataclass
class PendingEntry:
    underlying:       str
    order_id:         str
    symbol:           str
    qty:              int
    spot:             float
    direction:        str
    sl_pts:           float
    created_at:       datetime
    entry_delta:      float | None = None  # Preserved for moneyness-adapted tgt/trail on async fill
    entry_conviction: float = 0.0          # Conviction at entry for adaptive risk on async fill
    entry_sl_source:  str = ""             # SL source label (moneyness_adapted_XXX / hard_sl_pts_fallback)


@dataclass
class PendingExit:
    order_id:   str
    reason:     str
    created_at: datetime
    exit_qty:   int = 0  # requested exit quantity — used for partial-fill reconciliation


# ── TradeRecord / JournalWriter ──────────────────────────────────────────
@dataclass
class TradeRecord:
    """One row of the trade journal.  header is a ClassVar list of column names.
    record_type discriminates 'full_exit' (full position closed) from 'partial_exit'
    (single tranche closed)."""
    timestamp: str
    underlying: str
    option_symbol: str
    direction: str
    qty: int
    entry: float
    exit: float
    pnl_pts: float
    pnl_abs: float
    exit_reason: str
    mode: str
    r_multiple: float
    entry_conviction: float
    moneyness: str
    exit_price_source: str
    trail_peak_close: float
    giveback_pts: float
    trail_activated: bool
    trail_activation_sl: float | None
    sl_at_exit: float
    trail_method_used: str
    lock_mode_used: str
    activation_gain_pts: float | None
    activation_gain_pct: float | None
    activation_time: str | None
    bars_to_activation: str | None
    peak_after_activation: float | None
    bars_after_activation: str | None
    max_favorable_excursion: float | None
    max_adverse_excursion_after_activation: float | None
    record_type: str = "full_exit"
    slot_id: str = ""
    tranche_id: str = ""
    entry_sl_source: str = ""

    header: ClassVar[list[str]] = [
        "timestamp", "underlying", "option_symbol", "direction", "qty",
        "entry", "exit", "pnl_pts", "pnl_abs", "exit_reason", "mode",
        "r_multiple", "entry_conviction", "moneyness",
        "exit_price_source",
        "trail_peak_close", "giveback_pts", "trail_activated", "trail_activation_sl",
        "sl_at_exit", "trail_method_used", "lock_mode_used",
        "activation_gain_pts", "activation_gain_pct", "activation_time",
        "bars_to_activation", "peak_after_activation", "bars_after_activation",
        "max_favorable_excursion", "max_adverse_excursion_after_activation",
        "record_type", "slot_id", "tranche_id", "entry_sl_source",
    ]

    def to_row(self) -> list[str]:
        return [
            self.timestamp,
            self.underlying,
            self.option_symbol,
            self.direction,
            str(self.qty),
            f"{self.entry:.2f}",
            f"{self.exit:.2f}",
            f"{self.pnl_pts:.2f}",
            f"{self.pnl_abs:.2f}",
            self.exit_reason,
            self.mode,
            f"{self.r_multiple:.2f}",
            f"{self.entry_conviction:.2f}",
            self.moneyness,
            self.exit_price_source,
            f"{self.trail_peak_close:.2f}",
            f"{self.giveback_pts:.2f}",
            str(self.trail_activated),
            f"{self.trail_activation_sl:.2f}" if self.trail_activation_sl is not None else "",
            f"{self.sl_at_exit:.2f}",
            self.trail_method_used,
            self.lock_mode_used,
            f"{self.activation_gain_pts:.2f}" if self.activation_gain_pts is not None else "",
            f"{self.activation_gain_pct:.1f}" if self.activation_gain_pct is not None else "",
            self.activation_time or "",
            self.bars_to_activation or "",
            f"{self.peak_after_activation:.2f}" if self.peak_after_activation is not None else "",
            self.bars_after_activation or "",
            f"{self.max_favorable_excursion:.2f}" if self.max_favorable_excursion is not None else "",
            f"{self.max_adverse_excursion_after_activation:.2f}" if self.max_adverse_excursion_after_activation is not None else "",
            self.record_type,
            self.slot_id,
            self.tranche_id,
            self.entry_sl_source,
        ]


class JournalWriter:
    """Opens/appends CSV rows to the trade journal file.  Handles schema migration (archive + re-header)."""

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def _ensure_schema(self) -> bool:
        """Check existing file schema against TradeRecord.header.  Archive + re-header on mismatch.
        Returns True if a new header is needed.  Raises OSError on migration failure (caller skips write)."""
        if not os.path.exists(self.path):
            return True
        with open(self.path, "r") as f:
            _existing_cols = len(f.readline().split(","))
        if _existing_cols != len(TradeRecord.header):
            _base, _ext = os.path.splitext(self.path)
            _archive = f"{_base}_v{_existing_cols}col{_ext or '.csv'}"
            inf(f"[JOURNAL] Column mismatch ({_existing_cols} vs {len(TradeRecord.header)}) — archiving to {_archive}")
            os.rename(self.path, _archive)
            return True
        return False

    def write(self, record: TradeRecord) -> None:
        if not self.path:
            return
        try:
            write_header = self._ensure_schema()
        except OSError as exc:
            err(f"[JOURNAL] Schema migration failed — skipping write: {exc}")
            return
        row = record.to_row()
        try:
            with open(self.path, "a", newline="") as f:
                w = csv.writer(f)
                if write_header:
                    w.writerow(TradeRecord.header)
                w.writerow(row)
        except OSError as exc:
            err(f"[JOURNAL] Write error", exc)


class TradeAnalytics:
    """Post-trade analytics computation, decoupled from the TradeRecord dataclass."""

    @staticmethod
    def build(
        underlying: str,
        pos: OptionPosition,
        exit_price: float,
        pnl_abs: float,
        exit_reason: str,
        exit_price_source: str,
        paper_trade: bool,
        sl_method: str,
        activation_lock_pct: float,
        tranche: Tranche | None = None,
        record_type: str | None = None,
    ) -> "TradeRecord":
        pnl_pts = exit_price - pos.entry_premium
        risk_pts = max(0.01, pos.entry_premium - pos.initial_sl)
        _risk_qty = tranche.qty if tranche else pos.remaining_qty
        risk_amt = risk_pts * _risk_qty
        r_multiple = pnl_abs / risk_amt if risk_amt > 0 else 0.0
        _peak = pos.trail_peak_close or pos.entry_premium
        _giveback = max(0.0, _peak - exit_price)
        _act_gain = (pos.activation_price or pos.entry_premium) - pos.entry_premium
        _activated = pos.premium_trail_active or pos.kl_active or pos.trail_active
        _act_time = pos.activation_time
        return TradeRecord(
            timestamp=get_ist_now().strftime("%Y-%m-%d %H:%M:%S"),
            underlying=underlying,
            option_symbol=pos.symbol,
            direction=pos.option_type,
            qty=pos.remaining_qty,
            entry=pos.entry_premium,
            exit=exit_price,
            pnl_pts=pnl_pts,
            pnl_abs=pnl_abs,
            exit_reason=exit_reason,
            mode="PAPER" if paper_trade else "LIVE",
            r_multiple=r_multiple,
            entry_conviction=pos.entry_conviction,
            moneyness=pos.moneyness,
            exit_price_source=exit_price_source,
            trail_peak_close=_peak,
            giveback_pts=_giveback,
            trail_activated=_activated,
            trail_activation_sl=pos.trail_activation_sl,
            sl_at_exit=pos.sl,
            trail_method_used=sl_method,
            lock_mode_used=f"{activation_lock_pct:.0%}",
            activation_gain_pts=_act_gain if _activated else None,
            activation_gain_pct=_act_gain / max(0.01, pos.entry_premium) * 100 if _activated else None,
            activation_time=_act_time.strftime("%H:%M:%S") if _act_time else None,
            bars_to_activation=str(pos.activation_bucket - pos.entry_bucket) if pos.activation_bucket is not None else None,
            peak_after_activation=pos.peak_after_activation,
            bars_after_activation=str(pos.exit_bucket - pos.activation_bucket) if (pos.activation_bucket is not None and pos.exit_bucket is not None) else None,
            max_favorable_excursion=pos.mfe,
            max_adverse_excursion_after_activation=pos.mae_after_activation,
            record_type=record_type or ("partial_exit" if tranche else "full_exit"),
            slot_id=pos.slot_id,
            tranche_id=tranche.tranche_id if tranche else "",
            entry_sl_source=pos.entry_sl_source,
        )

    @staticmethod
    def build_tranche(
        underlying: str,
        pos: OptionPosition,
        tr: Tranche,
        paper_trade: bool = False,
    ) -> "TradeRecord":
        """Build a TradeRecord for a single tranche partial exit."""
        pnl_abs = _calc_pnl(pos, tr.exit_price, qty=tr.qty) if tr.exit_price else 0.0
        risk_pts = max(0.01, pos.entry_premium - pos.initial_sl)
        risk_amt = risk_pts * tr.qty
        r_multiple = pnl_abs / risk_amt if risk_amt > 0 else 0.0
        return TradeRecord(
            timestamp=get_ist_now().strftime("%Y-%m-%d %H:%M:%S"),
            underlying=underlying,
            option_symbol=pos.symbol,
            direction=pos.option_type,
            qty=tr.qty,
            entry=pos.entry_premium,
            exit=tr.exit_price or 0.0,
            pnl_pts=(tr.exit_price or 0.0) - pos.entry_premium,
            pnl_abs=pnl_abs,
            exit_reason=tr.exit_reason or "partial_exit",
            mode="PAPER" if paper_trade else "LIVE",
            r_multiple=r_multiple,
            entry_conviction=pos.entry_conviction,
            moneyness=pos.moneyness,
            exit_price_source="broker_fill",
            trail_peak_close=pos.trail_peak_close or pos.entry_premium,
            giveback_pts=max(0.0, (pos.trail_peak_close or pos.entry_premium) - (tr.exit_price or 0.0)),
            trail_activated=pos.premium_trail_active or pos.kl_active or pos.trail_active,
            trail_activation_sl=pos.trail_activation_sl,
            sl_at_exit=pos.sl,
            trail_method_used="",
            lock_mode_used="",
            activation_gain_pts=None,
            activation_gain_pct=None,
            activation_time=None,
            bars_to_activation=None,
            peak_after_activation=None,
            bars_after_activation=None,
            max_favorable_excursion=pos.mfe if tr.is_runner else None,
            max_adverse_excursion_after_activation=pos.mae_after_activation if tr.is_runner else None,
            record_type="partial_exit",
            slot_id=pos.slot_id,
            tranche_id=tr.tranche_id,
            entry_sl_source=pos.entry_sl_source,
        )


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 5 — MARKET DATA / BOT STATE     MarketSnapshot /            ║
# ║                                        SnapshotCache / BotState      ║
# ╚══════════════════════════════════════════════════════════════════════╝

@dataclass
class MarketSnapshot:
    """Timestamped snapshot of all market data for one underlying.

    Every consumer (trail, PNL, alerts, risk) reads from the same snapshot
    so there is zero drift between premium/spot/greeks at a given instant.
    """
    underlying:    str
    timestamp:     float            = 0.0   # time.time() when this was built
    spot_ltp:      float | None     = None
    option_symbol: str | None       = None   # The active position's option symbol
    option_ltp:    float | None     = None
    option_delta:  float | None     = None
    option_theta:  float | None     = None
    option_iv:     float | None     = None
    chain_oi:      float | None     = None   # Total OI for the active option
    chain_volume:  float | None     = None

    def is_stale(self, max_age: float = 5.0) -> bool:
        return (time.time() - self.timestamp) > max_age if self.timestamp else True

    @property
    def has_both_prices(self) -> bool:
        return self.spot_ltp is not None and self.option_ltp is not None


class SnapshotCache:
    """Thread-safe cache of MarketSnapshot per symbol. Per-symbol storage with
    backward-compat merged view when querying by underlying.

    V2: Each symbol (underlying or option) gets its own MarketSnapshot.
    get(underlying) returns a merged snapshot with spot_ltp from the underlying
    + option_ltp from the registered option symbol.  New methods
    get_for_symbol() / get_for_position() expose raw per-symbol data.

    Usage:
        cache = SnapshotCache()
        cache.set_option_symbol("NIFTY", "NIFTY24JUN2423000CE")
        cache.update("NIFTY24JUN2423000CE", option_ltp=244)
        cache.update("NIFTY", spot_ltp=23100)

        snap = cache.get("NIFTY")        # merged: spot + option
        opt  = cache.get_for_position("NIFTY")  # just the option snapshot
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._snapshots: dict[str, MarketSnapshot] = {}
        self._option_map: dict[str, str] = {}       # underlying → primary option_symbol
        self._option_set: dict[str, set[str]] = {}  # underlying → {all option_symbols}
        self._by_underlying: dict[str, str] = {}    # option_symbol → underlying

    def _merged(self, underlying: str) -> MarketSnapshot | None:
        """Build merged snapshot from underlying + its primary option symbol."""
        base = self._snapshots.get(underlying)
        if base is None:
            return None
        opt_sym = self._option_map.get(underlying)
        opt = self._snapshots.get(opt_sym) if opt_sym else None
        merged = copy.copy(base)
        if opt:
            merged.option_symbol = opt.option_symbol
            merged.option_ltp = opt.option_ltp
            merged.option_delta = opt.option_delta
            merged.option_theta = opt.option_theta
            merged.option_iv = opt.option_iv
            merged.chain_oi = opt.chain_oi
            merged.chain_volume = opt.chain_volume
            # Use freshest timestamp
            merged.timestamp = max(base.timestamp, opt.timestamp)
        return merged

    def get(self, symbol: str) -> MarketSnapshot | None:
        """Return snapshot for any symbol.
        If symbol is an underlying with a registered option, returns a merged
        view containing both spot and option data (backward compat)."""
        with self._lock:
            if symbol in self._option_map:
                return self._merged(symbol)
            snap = self._snapshots.get(symbol)
            return copy.copy(snap) if snap else None

    def get_for_symbol(self, symbol: str) -> MarketSnapshot | None:
        """Get the raw snapshot keyed by exact symbol, no merging."""
        with self._lock:
            snap = self._snapshots.get(symbol)
            return copy.copy(snap) if snap else None

    def get_for_position(self, underlying: str) -> MarketSnapshot | None:
        """Get the option snapshot for the primary position's registered option symbol."""
        with self._lock:
            opt_sym = self._option_map.get(underlying)
            if opt_sym:
                opt = self._snapshots.get(opt_sym)
                return copy.copy(opt) if opt else None
            return None

    def get_stale_underlyings(self, max_age: float) -> list[str]:
        """Return list of underlyings whose merged snapshot is stale or missing."""
        now = time.time()
        stale: list[str] = []
        with self._lock:
            checked: set[str] = set()
            for _, ul in self._by_underlying.items():
                if ul in checked:
                    continue
                checked.add(ul)
                merged = self._merged(ul)
                if merged is None:
                    stale.append(ul)
                else:
                    age = now - merged.timestamp if merged.timestamp else float("inf")
                    if age > max_age or merged.option_ltp is None or merged.spot_ltp is None:
                        stale.append(ul)
            # Also check underlyings in _option_map that weren't covered
            for ul in self._option_map:
                if ul not in checked:
                    checked.add(ul)
                    merged = self._merged(ul)
                    if merged is None:
                        stale.append(ul)
                    else:
                        age = now - merged.timestamp if merged.timestamp else float("inf")
                        if age > max_age or merged.option_ltp is None or merged.spot_ltp is None:
                            stale.append(ul)
        return stale

    def get_or_create(self, underlying: str) -> MarketSnapshot:
        with self._lock:
            if underlying not in self._snapshots:
                self._snapshots[underlying] = MarketSnapshot(underlying=underlying)
            snap = self._snapshots[underlying]
            return copy.copy(snap)

    def update(self, symbol: str, **fields: Any) -> None:
        """Atomically update a snapshot for the given symbol (underlying or option)."""
        with self._lock:
            if symbol not in self._snapshots:
                self._snapshots[symbol] = MarketSnapshot(underlying=symbol)
            snap = self._snapshots[symbol]
            for k, v in fields.items():
                if hasattr(snap, k):
                    setattr(snap, k, v)
            snap.timestamp = time.time()

    def set_option_symbol(self, underlying: str, symbol: str) -> None:
        """Register an option symbol as the primary one for an underlying.
        Creates both snapshots and sets up the mapping."""
        with self._lock:
            self._option_map[underlying] = symbol
            self._option_set.setdefault(underlying, set()).add(symbol)
            self._by_underlying[symbol] = underlying
            # Ensure both snapshots exist
            if underlying not in self._snapshots:
                self._snapshots[underlying] = MarketSnapshot(underlying=underlying)
            if symbol not in self._snapshots:
                self._snapshots[symbol] = MarketSnapshot(underlying=underlying, option_symbol=symbol)

    def add_option_symbol(self, underlying: str, symbol: str) -> None:
        """Register an additional option symbol for an underlying (multi-position)."""
        with self._lock:
            self._option_set.setdefault(underlying, set()).add(symbol)
            self._by_underlying[symbol] = underlying
            if symbol not in self._snapshots:
                self._snapshots[symbol] = MarketSnapshot(underlying=underlying, option_symbol=symbol)

    def update_from_ws_tick(self, underlying: str, symbol: str, spot_ltp: float, option_ltp: float) -> None:
        """Convenience: update both spot and option LTP from a WS tick.
        Writes to per-symbol snapshots (spot data to underlying, option data to option symbol)."""
        with self._lock:
            # Spot snapshot
            if underlying not in self._snapshots:
                self._snapshots[underlying] = MarketSnapshot(underlying=underlying)
            spot_snap = self._snapshots[underlying]
            spot_snap.spot_ltp = spot_ltp
            spot_snap.timestamp = time.time()
            # Option snapshot
            if symbol not in self._snapshots:
                self._snapshots[symbol] = MarketSnapshot(underlying=underlying, option_symbol=symbol)
            opt_snap = self._snapshots[symbol]
            opt_snap.option_ltp = option_ltp
            opt_snap.timestamp = time.time()
            # Ensure mapping exists
            self._option_map.setdefault(underlying, symbol)
            self._option_set.setdefault(underlying, set()).add(symbol)
            self._by_underlying[symbol] = underlying

    def update_from_option_chain(self, underlying: str, chain_data: dict) -> None:
        """Populate from a fetched option-chain row for all tracked symbols."""
        symbols: list[str] = []
        with self._lock:
            symbols = list(self._option_set.get(underlying, []))
        if not symbols:
            return
        for symbol in symbols:
            if "ce_symbol" in chain_data and chain_data["ce_symbol"] == symbol:
                prefix = "ce"
            elif "pe_symbol" in chain_data and chain_data["pe_symbol"] == symbol:
                prefix = "pe"
            else:
                continue
            oi    = float(chain_data.get(f"{prefix}_oi", 0) or 0)
            vol   = float(chain_data.get(f"{prefix}_volume", 0) or 0)
            ltp   = float(chain_data.get(f"{prefix}_ltp", 0) or 0)
            delta = float(chain_data.get("ce_delta" if prefix == "ce" else "pe_delta", 0) or 0)
            self.update(underlying, option_ltp=ltp, chain_oi=oi, chain_volume=vol, option_delta=delta if delta else None)

    def update_from_greeks(self, underlying: str, greeks: dict) -> None:
        """Populate greeks data from the optiongreeks API."""
        delta = greeks.get("delta")
        theta = greeks.get("theta")
        iv    = greeks.get("iv")
        self.update(
            underlying,
            option_delta=float(delta) if delta is not None else None,
            option_theta=float(theta) if theta is not None else None,
            option_iv=float(iv) if iv is not None else None,
        )

    def get_all(self) -> list[MarketSnapshot]:
        """Return all non-stale snapshots."""
        now = time.time()
        with self._lock:
            return [copy.copy(s) for s in self._snapshots.values() if now - s.timestamp < 10.0]


class PositionBook:
    """Replaces dict[str, OptionPosition].  Slot-keyed storage with backward-compat shims.
    Thread safety: callers must hold state_lock for mutations."""

    def __init__(self) -> None:
        self._by_slot: dict[str, OptionPosition] = {}
        self._by_underlying: dict[str, list[str]] = {}

    # ── Write operations (require state_lock at call site) ────────────────
    def add(self, pos: OptionPosition) -> None:
        sid = pos.slot_id
        existing = self._by_slot.get(sid)
        self._by_slot[sid] = pos
        ul = pos.core.underlying
        if existing is None:
            self._by_underlying.setdefault(ul, []).append(sid)
        elif sid not in self._by_underlying.get(ul, []):
            self._by_underlying.setdefault(ul, []).append(sid)

    def remove(self, slot_id: str) -> OptionPosition | None:
        pos = self._by_slot.pop(slot_id, None)
        if pos:
            ul = pos.core.underlying
            slots = self._by_underlying.get(ul, [])
            if slot_id in slots:
                slots.remove(slot_id)
        return pos

    # ── Read operations ───────────────────────────────────────────────────
    def get_one(self, underlying: str) -> OptionPosition | None:
        slots = self._by_underlying.get(underlying, [])
        return self._by_slot.get(slots[0]) if slots else None

    def get_all(self, underlying: str) -> list[OptionPosition]:
        return [self._by_slot[s] for s in self._by_underlying.get(underlying, [])
                if s in self._by_slot]

    def all_positions(self) -> list[OptionPosition]:
        return list(self._by_slot.values())

    def all_items(self) -> list[tuple[str, OptionPosition]]:
        return [(p.core.underlying, p) for p in self._by_slot.values()]

    def slot(self, slot_id: str) -> OptionPosition | None:
        return self._by_slot.get(slot_id)

    def count(self, underlying: str | None = None) -> int:
        if underlying:
            return len(self._by_underlying.get(underlying, []))
        return len(self._by_slot)

    def underlyings(self) -> list[str]:
        """Return list of underlyings with active positions."""
        return [ul for ul, slots in self._by_underlying.items() if slots]

    # ── Guard helpers ─────────────────────────────────────────────────────
    def has_siblings(self, slot_id: str) -> bool:
        """True if other slots for the same underlying still exist (excluding this slot_id)."""
        pos = self._by_slot.get(slot_id)
        if not pos:
            return False
        slots = self._by_underlying.get(pos.core.underlying, [])
        return any(s != slot_id for s in slots)

    def has_opposite(self, underlying: str, direction: str) -> bool:
        return any(p.core.option_type != direction for p in self.get_all(underlying))

    def has_active_opposite(self, underlying: str, direction: str) -> bool:
        return any(
            p.core.option_type != direction and not p.exit_pending
            for p in self.get_all(underlying)
        )

    def has_same_direction(self, underlying: str, direction: str) -> bool:
        return any(p.core.option_type == direction for p in self.get_all(underlying))

    def can_enter(self, underlying: str, direction: str, cfg: BotConfig) -> tuple[bool, str]:
        total = self.count()
        if total >= cfg.position.max_total_positions:
            return False, f"max_total_positions={cfg.position.max_total_positions} reached"
        per_ul = self.count(underlying)
        if per_ul >= cfg.position.max_positions_per_underlying:
            return False, (f"max_positions_per_underlying={cfg.position.max_positions_per_underlying} "
                           f"reached for {underlying}")
        if self.has_active_opposite(underlying, direction):
            if cfg.position.opposite_side_exit_on_signal:
                return True, "opposite_exit_pending"
            if cfg.position.allow_simultaneous_ce_pe:
                return True, "ok"
            return False, f"opposite side active for {underlying}"
        if self.has_same_direction(underlying, direction):
            if cfg.position.same_direction_add_on_signal:
                return True, "ok"
            return False, f"same direction position exists for {underlying}"
        return True, "ok"

    # ── Backward compat shims ─────────────────────────────────────────────
    def __contains__(self, underlying: str) -> bool:
        return self.count(underlying) > 0

    def get(self, underlying: str, default=None) -> OptionPosition | None:
        return self.get_one(underlying) or default

    def items(self):
        return self.all_items()

    def pop(self, slot_id: str, default=None):
        return self.remove(slot_id) if slot_id in self._by_slot else default

    def __setitem__(self, underlying: str, pos: OptionPosition) -> None:
        self.add(pos)

    def __len__(self) -> int:
        return len(self._by_slot)


class BotState:
    """Thread-safe shared state owned by the orchestrator, passed to all components."""

    def __init__(self, chain_smooth_bars: int = 5):
        self.position_book: PositionBook = PositionBook()
        self.positions = self.position_book  # backward-compat alias
        self.ltp_map:         dict[str, float] = {}
        self.snapshot_cache:  SnapshotCache = SnapshotCache()
        self.exit_queue:      set[str] = set()
        self.exit_lock        = threading.Lock()
        self.state_lock       = threading.Lock()
        self.pending_entries: dict[str, PendingEntry] = {}
        self.pending_exits:   dict[str, PendingExit]  = {}
        self.prev_straddle:   dict[str, dict]  = {}
        self.prev_spot:       dict[str, float] = {}
        self.prev_sf:         dict[str, float] = {}
        self.chain_history:   dict[str, deque] = {}
        self.greeks_history:  dict[str, dict[float, deque]] = {}   # {symbol: {strike: deque(maxlen=5)}}
        self.spot_price_history: dict[str, deque] = {} # underlying → deque of (timestamp, ltp)
        self._chain_smooth_bars = chain_smooth_bars
        self.entry_in_flight: dict[str, int] = {}
        self._strike_loss_pts: dict[str, float] = {}
        self.bucket_counter: int = 0
        self.pending_opposite_exit: set[str] = set()
        self.latest_signals: dict[str, tuple[SignalResult, float]] = {}

    def get_chain_history(self, symbol: str) -> deque:
        if symbol not in self.chain_history:
            self.chain_history[symbol] = deque(maxlen=max(1, self._chain_smooth_bars))
        return self.chain_history[symbol]

    def get_greeks_history(self, symbol: str, strike: float, maxlen: int = 5) -> deque:
        per_symbol = self.greeks_history.setdefault(symbol, {})
        if strike not in per_symbol:
            per_symbol[strike] = deque(maxlen=maxlen)
        return per_symbol[strike]

    def record_spot_price(self, underlying: str, ltp: float, maxlen: int = 10) -> None:
        if underlying not in self.spot_price_history:
            self.spot_price_history[underlying] = deque(maxlen=maxlen)
        self.spot_price_history[underlying].append((time.time(), ltp))

    def smoothed_spot(self, underlying: str, lookback: int | None = None) -> float | None:
        """Average spot LTP across last `lookback` ticks. None = all available."""
        hist = self.spot_price_history.get(underlying)
        if not hist:
            return None
        if lookback is not None and lookback <= 0:
            return None
        vals = [ltp for _, ltp in (list(hist)[-lookback:] if lookback else list(hist))]
        return sum(vals) / len(vals) if vals else None

    def reset_market_caches(self):
        self.prev_straddle.clear()
        self.prev_spot.clear()
        self.prev_sf.clear()
        self.chain_history.clear()
        self.greeks_history.clear()
        self.spot_price_history.clear()

    def record_strike_loss(self, option_symbol: str, direction: str, pts_loss: float) -> None:
        """Accumulate a losing trade's point loss against this exact strike+direction.
        Winning/breakeven trades are not recorded — this is cumulative pain, not net PnL."""
        if pts_loss <= 0:
            return
        key = f"{option_symbol}|{direction}"
        with self.state_lock:
            self._strike_loss_pts[key] = self._strike_loss_pts.get(key, 0.0) + pts_loss

    def strike_cum_loss_pts(self, option_symbol: str, direction: str) -> float:
        key = f"{option_symbol}|{direction}"
        with self.state_lock:
            return float(self._strike_loss_pts.get(key, 0.0))

    def reset_strike_loss_pts(self) -> None:
        self._strike_loss_pts.clear()


def _smooth_greeks(history: deque, lookback: int | None = None,
                    max_age_secs: float | None = None) -> dict:
    """Average delta and IVR across THIS strike's own history.
    max_age_secs drops entries older than this. Returns {} on empty."""
    snaps = list(history)
    if not snaps:
        return {}
    if lookback is not None and lookback <= 0:
        return {}
    snaps = snaps[-lookback:] if lookback else snaps

    if max_age_secs is not None:
        now = time.time()
        snaps = [s for s in snaps if (now - s.get("timestamp", 0)) <= max_age_secs]
    if not snaps:
        return {}

    def _avg(key):
        vals = [s[key] for s in snaps if s.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    return {
        "ce_delta":   _avg("ce_delta"),
        "pe_delta":   _avg("pe_delta"),
        "ce_iv_rank": _avg("ce_iv_rank"),
        "pe_iv_rank": _avg("pe_iv_rank"),
    }


def _effective_min_score(now: datetime, cfg: "BotConfig") -> tuple[int, str]:
    """Return the session-adjusted minimum composite score and a reason label.

    Implements U-C (Session-Aware Min Score):
      • Morning  (09:15 – morning_session_end)  : score threshold raised by morning_score_factor
        — higher bar because early-session volatility is noisy and traps are common.
      • Power-hour (afternoon_power_start – no_new_trade_after): threshold eased by power_hour_score_factor
        — institutional momentum flows are cleaner; lower bar improves participation.
      • Mid-session: standard min_score applies.

    Args:
        now: Current IST datetime (use get_ist_now()).
        cfg: Resolved BotConfig instance.

    Returns:
        (effective_score, session_label) tuple.
    """
    now_hm = now.strftime("%H:%M")
    if cfg.market.morning_session_end and now_hm < cfg.market.morning_session_end:
        score = max(1, int(cfg.entry.min_score * cfg.entry.morning_score_factor))
        return score, f"morning-gate(raised→{score})"
    if (
        cfg.market.afternoon_power_start
        and cfg.market.no_new_trade_after
        and cfg.market.afternoon_power_start <= now_hm < cfg.market.no_new_trade_after
    ):
        score = max(1, int(cfg.entry.min_score * cfg.entry.power_hour_score_factor))
        return score, f"power-hour(eased→{score})"
    return cfg.entry.min_score, "mid-session"


def _ewa(values: list[float], alpha: float = 0.4) -> float:
    """Exponentially weighted average. alpha=0.4: most recent→40%, one back→24%, etc."""
    if not values:
        return 0.0
    result = values[0]
    for v in values[1:]:
        result = alpha * v + (1 - alpha) * result
    return result


def _series_slope(values: list[float]) -> int:
    """Linear trend across series. +1 rising, -1 falling, 0 flat. Uses regression slope sign."""
    n = len(values)
    if n < 2:
        return 0
    if n == 2:
        diff = values[-1] - values[0]
        return 1 if diff > 0 else (-1 if diff < 0 else 0)
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    numerator = sum((i - mean_x) * (values[i] - mean_y) for i in range(n))
    if numerator > 1e-9:
        return 1
    elif numerator < -1e-9:
        return -1
    return 0


class OIFlowAnalyzer:
    """Static helpers for OI-flow analysis and chain smoothing."""

    @staticmethod
    def smooth_chain_rows(history: list, lookback: int | None = None) -> list[dict]:
        """
        EWA-smooth per-strike OI/Volume/Premium across N snapshots (oldest-first).
        lookback: None = all available, >0 = last N snapshots, ≤0 = return raw chain.
        Appends six direction fields per row for the 3-factor classifier.
        Returns single-bar snapshot unchanged (with zero trend flags).
        """
        if not history:
            return []
        # Invalid lookback → return raw latest snapshot with zero trend flags
        if lookback is not None and lookback <= 0:
            result = []
            for row in history[-1]:
                r = dict(row)
                r["ce_ltp_dir"] = 0; r["ce_vol_dir"] = 0; r["ce_oi_dir"] = 0
                r["pe_ltp_dir"] = 0; r["pe_vol_dir"] = 0; r["pe_oi_dir"] = 0
                result.append(r)
            return result
        # Apply lookback window
        snaps_src = history[-lookback:] if lookback else history
        if len(snaps_src) == 1:
            result = []
            for row in snaps_src[0]:
                r = dict(row)
                r["ce_ltp_dir"] = 0; r["ce_vol_dir"] = 0; r["ce_oi_dir"] = 0
                r["pe_ltp_dir"] = 0; r["pe_vol_dir"] = 0; r["pe_oi_dir"] = 0
                result.append(r)
            return result

        snaps = []
        for snap in snaps_src:
            d = {}
            for row in snap:
                k = row.get("strike")
                if k is not None:
                    d[k] = row
            snaps.append(d)

        all_strikes = sorted({k for s in snaps for k in s})
        # Only smooth absolute values — deltas and bid/ask handled separately
        SMOOTH_FIELDS = [
            "ce_oi", "pe_oi", "ce_volume", "pe_volume", "ce_ltp", "pe_ltp",
        ]

        smoothed = []
        for strike in all_strikes:
            rows = [s[strike] for s in snaps if strike in s]
            if not rows:
                continue
            # base = most recent snapshot (for non-smoothed fields like symbol, lotsize)
            base = None
            for s in reversed(snaps):
                if strike in s:
                    base = dict(s[strike])
                    break
            row_out = dict(base)

            # EWA-smooth absolute fields (recent scans weighted more)
            for fld in SMOOTH_FIELDS:
                vals = [float(r.get(fld) or 0) for r in rows]
                row_out[fld] = _ewa(vals, alpha=0.4)

            # Derived change fields from smoothed absolutes (not raw scan deltas)
            oldest_row = rows[0]
            row_out["ce_oi_chg"]  = row_out["ce_oi"]  - float(oldest_row.get("ce_oi",  0) or 0)
            row_out["pe_oi_chg"]  = row_out["pe_oi"]  - float(oldest_row.get("pe_oi",  0) or 0)
            row_out["ce_ltp_chg"] = row_out["ce_ltp"] - float(oldest_row.get("ce_ltp", 0) or 0)
            row_out["pe_ltp_chg"] = row_out["pe_ltp"] - float(oldest_row.get("pe_ltp", 0) or 0)

            # Bid/ask: always raw current (real-time liquidity gate)
            row_out["ce_bid"] = float(base.get("ce_bid", 0) or 0)
            row_out["ce_ask"] = float(base.get("ce_ask", 0) or 0)
            row_out["pe_bid"] = float(base.get("pe_bid", 0) or 0)
            row_out["pe_ask"] = float(base.get("pe_ask", 0) or 0)

            # Direction: linear slope across full series (not just endpoints)
            def _collect(col, _rows=rows):
                return [float(r.get(col) or 0) for r in _rows]
            row_out["ce_ltp_dir"] = _series_slope(_collect("ce_ltp"))
            row_out["ce_vol_dir"] = _series_slope(_collect("ce_volume"))
            row_out["ce_oi_dir"]  = _series_slope(_collect("ce_oi"))
            row_out["pe_ltp_dir"] = _series_slope(_collect("pe_ltp"))
            row_out["pe_vol_dir"] = _series_slope(_collect("pe_volume"))
            row_out["pe_oi_dir"]  = _series_slope(_collect("pe_oi"))

            smoothed.append(row_out)
        return smoothed

    @staticmethod
    def compute_pcr(chain_rows: list[dict]) -> float:
        ce_oi = sum(r.get("ce_oi", 0) or 0 for r in chain_rows)
        pe_oi = sum(r.get("pe_oi", 0) or 0 for r in chain_rows)
        return (pe_oi / ce_oi) if ce_oi else 1.0

    @staticmethod
    def call_wall(chain_rows: list[dict]) -> float | None:
        return max(chain_rows, key=lambda r: r.get("ce_oi", 0))["strike"] if chain_rows else None

    @staticmethod
    def put_wall(chain_rows: list[dict]) -> float | None:
        return max(chain_rows, key=lambda r: r.get("pe_oi", 0))["strike"] if chain_rows else None

    @staticmethod
    def classify_ce_flow(chain_rows: list[dict]) -> tuple[float, str]:
        """3-factor CE flow classifier (8-state matrix). Falls back to 2-factor on single bar."""
        def _agg(fld: str) -> int:
            raw = sum(r.get(fld, 0) or 0 for r in chain_rows)
            return 1 if raw > 0 else (-1 if raw < 0 else 0)

        l, v, o = _agg("ce_ltp_dir"), _agg("ce_vol_dir"), _agg("ce_oi_dir")
        if v != 0:
            if   l ==  1 and v ==  1 and o ==  1: return  2.0, "Call Buying — strong bullish conviction"
            elif l ==  1 and v ==  1 and o == -1: return  1.0, "CE Short Covering — moderately bullish"
            elif l ==  1 and v == -1 and o ==  1: return  0.5, "CE accumulation low volume — cautiously bullish"
            elif l ==  1 and v == -1 and o == -1: return  0.0, "CE fading interest — weakening"
            elif l == -1 and v ==  1 and o ==  1: return -2.0, "Call Writing — strong bearish signal"
            elif l == -1 and v ==  1 and o == -1: return -1.0, "CE Long Unwinding — moderately bearish"
            elif l == -1 and v == -1 and o ==  1: return -0.5, "Call writing low volume — cautiously bearish"
            elif l == -1 and v == -1 and o == -1: return  0.0, "CE pressure fading — weakening bearish"
            return 0.0, "CE Neutral"
        # 2-factor fallback
        oi_chg  = sum(r.get("ce_oi_chg", 0) or 0 for r in chain_rows)
        ltp_chg = sum(r.get("ce_ltp_chg", 0) or 0 for r in chain_rows)
        if oi_chg > 0 and ltp_chg > 0.5:  return  2, "Call Buying"
        if oi_chg < 0 and ltp_chg > 0.5:  return  1, "CE Short Covering"
        if oi_chg > 0 and ltp_chg < -0.5: return -2, "Call Writing"
        if oi_chg < 0 and ltp_chg < -0.5: return -1, "CE Long Unwinding"
        return 0, "CE Neutral"

    @staticmethod
    def classify_pe_flow(chain_rows: list[dict]) -> tuple[float, str]:
        """3-factor PE flow classifier (8-state matrix). Falls back to 2-factor on single bar."""
        def _agg(fld: str) -> int:
            raw = sum(r.get(fld, 0) or 0 for r in chain_rows)
            return 1 if raw > 0 else (-1 if raw < 0 else 0)

        l, v, o = _agg("pe_ltp_dir"), _agg("pe_vol_dir"), _agg("pe_oi_dir")
        if v != 0:
            if   l ==  1 and v ==  1 and o ==  1: return -2.0, "Put Buying — strong bearish for underlying"
            elif l ==  1 and v ==  1 and o == -1: return -1.0, "PE Short Covering — moderately bearish"
            elif l ==  1 and v == -1 and o ==  1: return -0.5, "Put accumulation low volume — cautiously bearish"
            elif l ==  1 and v == -1 and o == -1: return  0.0, "PE demand fading — weakening bearish"
            elif l == -1 and v ==  1 and o ==  1: return  2.0, "Put Writing — strong bullish for underlying"
            elif l == -1 and v ==  1 and o == -1: return  1.0, "PE Long Unwinding — moderately bullish"
            elif l == -1 and v == -1 and o ==  1: return  0.5, "Put writing low volume — cautiously bullish"
            elif l == -1 and v == -1 and o == -1: return  0.0, "PE pressure fading — weakening bullish"
            return 0.0, "PE Neutral"
        # 2-factor fallback
        oi_chg  = sum(r.get("pe_oi_chg", 0) or 0 for r in chain_rows)
        ltp_chg = sum(r.get("pe_ltp_chg", 0) or 0 for r in chain_rows)
        if oi_chg > 0 and ltp_chg < -0.5: return  2, "Put Writing"
        if oi_chg > 0 and ltp_chg > 0.5:  return -2, "Put Buying"
        if oi_chg < 0 and ltp_chg > 0.5:  return  1, "PE Short Covering"
        if oi_chg < 0 and ltp_chg < -0.5: return -1, "PE Long Unwinding"
        return 0, "PE Neutral"


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 5-B — TECHNICAL INDICATOR REGISTRY                          ║
# ╚══════════════════════════════════════════════════════════════════════╝
#
# Each spec is a self-contained unit: compute returns raw values,
# score maps them to a (score, note) tuple. The orchestrator in
# SignalEngine.score() calls spec.evaluate() for each entry.

def ta_value(result, idx: int = -1) -> float | None:
    """
    Extract a scalar from any openalgo ta.* return value, regardless of
    whether the library echoed back a Series (input was Series) or an
    ndarray (input was ndarray/list). Verified against openalgo 2.0.2:
    Series requires .iloc; ndarray requires bracket index.
    """
    if result is None:
        return None
    try:
        val = result.iloc[idx] if hasattr(result, "iloc") else result[idx]
    except (IndexError, KeyError, TypeError):
        return None
    if val is None or not math.isfinite(float(val)):
        return None
    return float(val)


# ── EMA Trend ─────────────────────────────────────────────────────────
def _compute_ema_trend(df_spot, cfg):
    fast = ta.ema(df_spot["close"], period=cfg.entry.fast_ema_period)
    slow = ta.ema(df_spot["close"], period=cfg.entry.slow_ema_period)
    f2, f3 = ta_value(fast, -2), ta_value(fast, -3)
    s2, s3 = ta_value(slow, -2), ta_value(slow, -3)
    if None in (f2, f3, s2, s3):
        return None
    return {"fast_2": f2, "fast_3": f3, "slow_2": s2, "slow_3": s3}

def _score_ema_trend(raw, cfg):
    f2, f3, s2, s3 = raw["fast_2"], raw["fast_3"], raw["slow_2"], raw["slow_3"]
    fp, sp = cfg.entry.fast_ema_period, cfg.entry.slow_ema_period
    if f2 > s2 and f3 <= s3:
        return 1, f"Bullish EMA crossover ({fp}/{sp})"
    if f2 < s2 and f3 >= s3:
        return -1, f"Bearish EMA crossover ({fp}/{sp})"
    if f2 > s2:
        return 0.5, "Fast EMA above Slow EMA (bullish)"
    if f2 < s2:
        return -0.5, "Fast EMA below Slow EMA (bearish)"
    return 0, "Insufficient candles"

EMA_TREND = IndicatorSpec(name="EMA Trend", min_bars=lambda cfg: cfg.entry.slow_ema_period + 3, compute=_compute_ema_trend, score=_score_ema_trend)


# ── RSI Momentum ──────────────────────────────────────────────────────
def _compute_rsi_momentum(df_spot, cfg):
    rsi = ta.rsi(df_spot["close"], period=cfg.entry.rsi_period)
    rv = ta_value(rsi, -2)
    if rv is None:
        return None
    return {"rsi": rv}

def _score_rsi_momentum(raw, cfg):
    rv = raw["rsi"]
    if rv > 53:
        return 1, f"RSI {rv:.1f} — bullish momentum"
    if rv > 50:
        return 0.5, f"RSI {rv:.1f} — mild bullish tilt"
    if rv < 47:
        return -1, f"RSI {rv:.1f} — bearish momentum"
    if rv < 50:
        return -0.5, f"RSI {rv:.1f} — mild bearish tilt"
    return 0, f"RSI {rv:.1f} — exactly neutral (50)"

RSI_MOMENTUM = IndicatorSpec(name="RSI Momentum", min_bars=lambda cfg: cfg.entry.rsi_period + 2, compute=_compute_rsi_momentum, score=_score_rsi_momentum)



# ── Spot vs VWAP ──────────────────────────────────────────────────────
def _compute_spot_vs_vwap(df_spot, cfg):
    spot_val = float(df_spot["close"].iloc[-1])
    if "volume" not in df_spot.columns or len(df_spot) < 5:
        return None
    df_today = (
        df_spot[df_spot.index.tz_localize(None).normalize() == pd.Timestamp(get_ist_now().date())]
        if isinstance(df_spot.index, pd.DatetimeIndex)
        else df_spot
    )
    if len(df_today) < 5:
        return None
    _vol = pd.to_numeric(df_today["volume"], errors='coerce').values
    _has_volume = (_vol > 0).any()
    _vol_feed = _vol if _has_volume else np.ones(len(_vol))
    source = "today" if _has_volume else "today(price-only)"
    try:
        vwap_arr = ta.vwap(
            df_today["high"], df_today["low"], df_today["close"],
            _vol_feed, anchor="Session", source="hlc3",
        )
        vv = ta_value(vwap_arr, -1)
        if vv is None or vv <= 0:
            return None
        return {"vwap": vv, "spot": spot_val, "n_bars": len(df_today), "source": source}
    except Exception:
        return None

def _score_spot_vs_vwap(raw, cfg):
    spot_val, vv = raw["spot"], raw["vwap"]
    source, n = raw["source"], raw["n_bars"]
    if spot_val > vv:
        return 1, f"Spot {spot_val:.1f} above VWAP {vv:.1f} ({source}, {n} bars)"
    return -1, f"Spot {spot_val:.1f} below VWAP {vv:.1f} ({source}, {n} bars)"

SPOT_VS_VWAP = IndicatorSpec(name="Spot vs VWAP", min_bars=5, compute=_compute_spot_vs_vwap, score=_score_spot_vs_vwap)


# ── RVOL-Simple ────────────────────────────────────────────────────────
def _compute_rvol_simple(df_spot, cfg):
    vol = pd.to_numeric(df_spot["volume"], errors="coerce")
    if (vol <= 0).all():
        return None
    lb = cfg.signal.rvol_lookback
    if len(vol) < lb + 1:
        return None
    current = float(vol.iloc[-1] or 0)
    sma = float(vol.iloc[-lb:].mean() or 1)
    return {"rvol": current / sma, "close": float(df_spot["close"].iloc[-1])}

def _score_rvol_simple(raw, cfg):
    r = raw["rvol"]
    if r > 2.0:
        return 1, f"RVOL {r:.2f}x — heavy volume surge, strong conviction"
    if r > 1.5:
        return 0.75, f"RVOL {r:.2f}x — elevated volume, buying conviction"
    if r > 1.0:
        return 0.5, f"RVOL {r:.2f}x — above-average volume, mild bullish"
    if r < 0.4:
        return -1, f"RVOL {r:.2f}x — dead volume, weak participation"
    if r < 0.7:
        return -0.5, f"RVOL {r:.2f}x — below-average volume, low interest"
    return 0, f"RVOL {r:.2f}x — neutral volume"

RVOL_SIMPLE = IndicatorSpec(name="RVOL-Simple", min_bars=lambda cfg: cfg.signal.rvol_lookback + 1, compute=_compute_rvol_simple, score=_score_rvol_simple)


INDICATOR_REGISTRY: list[IndicatorSpec] = [
    EMA_TREND,
    RSI_MOMENTUM,
    SPOT_VS_VWAP,
]


# ── PCR OI Level ──────────────────────────────────────────────────────
def _compute_pcr(ctx, cfg, intermediates):
    chain_rows = ctx.get("chain_rows")
    if not chain_rows:
        return None
    pcr = OIFlowAnalyzer.compute_pcr(chain_rows)
    intermediates["pcr"] = pcr
    if pcr <= 0.6:   return 1, f"PCR OI {pcr:.2f}"
    if pcr <= 0.9:   return 0.5, f"PCR OI {pcr:.2f}"
    if pcr <= 1.1:   return 0, f"PCR OI {pcr:.2f}"
    if pcr <= 1.3:   return -0.5, f"PCR OI {pcr:.2f}"
    return -1, f"PCR OI {pcr:.2f}"

PCR_LEVEL = StatisticSpec(name="PCR OI Level", compute=_compute_pcr)


# ── Call OI Flow ───────────────────────────────────────────────────────
def _compute_call_flow(ctx, cfg, intermediates):
    chain_rows = ctx.get("chain_rows")
    if not chain_rows:
        return None
    s, label = OIFlowAnalyzer.classify_ce_flow(chain_rows)
    intermediates["call_flow_score"] = s
    return s, label

CALL_OI_FLOW = StatisticSpec(name="Call OI Flow", compute=_compute_call_flow, score_max=2)


# ── Put OI Flow ────────────────────────────────────────────────────────
def _compute_put_flow(ctx, cfg, intermediates):
    chain_rows = ctx.get("chain_rows")
    if not chain_rows:
        return None
    s, label = OIFlowAnalyzer.classify_pe_flow(chain_rows)
    intermediates["put_flow_score"] = s
    return s, label

PUT_OI_FLOW = StatisticSpec(name="Put OI Flow", compute=_compute_put_flow, score_max=2)


# ── OI Wall Position ──────────────────────────────────────────────────
def _compute_oi_wall(ctx, cfg, intermediates):
    chain_rows = ctx.get("chain_rows")
    spot = ctx.get("spot")
    if not chain_rows or not spot:
        return None
    cw = OIFlowAnalyzer.call_wall(chain_rows)
    pw = OIFlowAnalyzer.put_wall(chain_rows)
    if not cw or not pw:
        return None
    if spot < cw and spot > pw:
        if (cw - spot) > (spot - pw):
            return 0.5, f"Spot between walls, near put support {pw:.0f} (call wall {cw:.0f} far) — mild bullish"
        return -0.5, f"Spot between walls, near call resistance {cw:.0f} (put wall {pw:.0f} far) — mild bearish"
    if spot >= cw:
        return -1, f"Spot {spot:.0f} at/above call wall {cw:.0f} — overhead resistance, bearish"
    if spot <= pw:
        return -1, f"Spot {spot:.0f} below put wall {pw:.0f} — support broken, put writers hedging (bearish)"
    return 0, "OI walls unavailable"

OI_WALL = StatisticSpec(name="OI Wall Position", compute=_compute_oi_wall)


# ── Greeks Bias (Delta) ───────────────────────────────────────────────
def _compute_delta_bias(ctx, cfg, intermediates):
    ce_delta = ctx.get("ce_delta")
    pe_delta = ctx.get("pe_delta")
    atm_ce_ltp = ctx.get("atm_ce_ltp")
    atm_pe_ltp = ctx.get("atm_pe_ltp")

    if ce_delta is not None and pe_delta is not None:
        di = ce_delta + pe_delta
        if di >= 0.05:
            return 1, f"ATM Δ sum {di:+.3f} — CE ITM, net bullish  (CE {ce_delta:+.3f} / PE {pe_delta:+.3f})"
        if di >= 0.02:
            return 0.5, f"ATM Δ sum {di:+.3f} — mild CE dominance   (CE {ce_delta:+.3f} / PE {pe_delta:+.3f})"
        if di <= -0.05:
            return -1, f"ATM Δ sum {di:+.3f} — PE ITM, net bearish  (CE {ce_delta:+.3f} / PE {pe_delta:+.3f})"
        if di <= -0.02:
            return -0.5, f"ATM Δ sum {di:+.3f} — mild PE dominance   (CE {ce_delta:+.3f} / PE {pe_delta:+.3f})"
        return 0, f"ATM Δ sum {di:+.3f} — balanced (CE {ce_delta:+.3f} / PE {pe_delta:+.3f})"
    if atm_ce_ltp and atm_pe_ltp and atm_pe_ltp > 0:
        di = (atm_ce_ltp - atm_pe_ltp) / ((atm_ce_ltp + atm_pe_ltp) / 2)
        if di >= 0.10:
            return 1, f"LTP proxy Δ {di:+.3f} — CE premium heavy (bullish)"
        if di >= 0.05:
            return 0.5, f"LTP proxy Δ {di:+.3f} — mild CE premium"
        if di <= -0.10:
            return -1, f"LTP proxy Δ {di:+.3f} — PE premium heavy (bearish)"
        if di <= -0.05:
            return -0.5, f"LTP proxy Δ {di:+.3f} — mild PE premium"
        return 0, f"LTP proxy Δ {di:+.3f} — balanced"
    return None

DELTA_BIAS = StatisticSpec(name="Greeks Bias (Δ)", compute=_compute_delta_bias)


# ── Gamma Regime ──────────────────────────────────────────────────────
def _compute_gamma_regime(ctx, cfg, intermediates):
    gex_levels = ctx.get("gex_levels")
    spot = ctx.get("spot")
    if not gex_levels:
        return None

    total_net_gex = float(gex_levels.get("total_net_gex") or 0)
    gamma_flip = gex_levels.get("gamma_flip")
    upside_punch = gex_levels.get("upside_punch_target")
    downside_punch = gex_levels.get("downside_punch_target")
    s10 = 0
    gamma_note = ""

    if total_net_gex < 0:
        chosen_side = None
        chosen_target = None
        chosen_dist = None

        if upside_punch is not None and downside_punch is not None:
            up_dist = abs(float(upside_punch) - spot)
            dn_dist = abs(spot - float(downside_punch))
            if up_dist < dn_dist:
                chosen_side, chosen_target, chosen_dist = "upside", float(upside_punch), up_dist
            elif dn_dist < up_dist:
                chosen_side, chosen_target, chosen_dist = "downside", float(downside_punch), dn_dist
        elif upside_punch is not None:
            chosen_side, chosen_target, chosen_dist = "upside", float(upside_punch), abs(float(upside_punch) - spot)
        elif downside_punch is not None:
            chosen_side, chosen_target, chosen_dist = "downside", float(downside_punch), abs(spot - float(downside_punch))

        if chosen_side == "upside":
            s10 = 1
        elif chosen_side == "downside":
            s10 = -1

        if chosen_dist is not None and spot > 0 and chosen_dist <= spot * 0.0025 and s10 != 0:
            s10 = 2 if s10 > 0 else -2

        if chosen_side and chosen_target is not None:
            gamma_note = (
                f"Short gamma (Net GEX {total_net_gex:+.0f}); nearest {chosen_side} punch "
                f"{chosen_target:.0f} from spot {spot:.0f}"
            )
        else:
            gamma_note = (
                f"Short gamma (Net GEX {total_net_gex:+.0f}) but no nearby punch target "
                "resolved — neutral"
            )

    elif total_net_gex > 0:
        gamma_note = (
            f"Long gamma (Net GEX {total_net_gex:+.0f}) — dealer hedging tends to dampen "
            "directional follow-through"
        )
        s10 = 0
    else:
        gamma_note = "Net GEX near zero — no clear gamma regime"

    if gamma_flip is not None:
        gamma_note += f" | gamma flip {float(gamma_flip):.0f}"

    return s10, gamma_note

GAMMA_REGIME = StatisticSpec(name="Gamma Regime", compute=_compute_gamma_regime, score_max=2)


# ── OI Velocity ───────────────────────────────────────────────────────
def _compute_oi_velocity(ctx, cfg, intermediates):
    if not cfg.entry.oi_velocity_enabled:
        return 0, "OI velocity disabled"
    chain_rows = ctx.get("chain_rows")
    if not chain_rows:
        return None
    s6 = intermediates.get("call_flow_score", 0)
    s7 = intermediates.get("put_flow_score", 0)
    ce_oi_chg = sum(float(r.get("ce_oi_chg", 0) or 0) for r in chain_rows)
    pe_oi_chg = sum(float(r.get("pe_oi_chg", 0) or 0) for r in chain_rows)
    ce_oi_tot = sum(float(r.get("ce_oi", 0) or 0) for r in chain_rows)
    pe_oi_tot = sum(float(r.get("pe_oi", 0) or 0) for r in chain_rows)
    ce_vel = (ce_oi_chg / ce_oi_tot * 100) if ce_oi_tot > 0 else 0.0
    pe_vel = (pe_oi_chg / pe_oi_tot * 100) if pe_oi_tot > 0 else 0.0
    th = cfg.entry.oi_velocity_threshold

    if ce_vel > th and s6 > 0:
        return 1, (
            f"CE OI building {ce_vel:+.2%} + call buying — institutional accumulation"
        )
    if ce_vel > th and s6 < 0:
        return -1, (
            f"CE OI building {ce_vel:+.2%} + call writing — institutional writer trap"
        )
    if ce_vel < -th and s6 > 0:
        return 0.5, f"CE OI unwinding {ce_vel:+.2%} — short covering"
    if pe_vel > th and s7 < 0:
        return -1, (
            f"PE OI building {pe_vel:+.2%} + put buying — bearish accumulation"
        )
    if pe_vel > th and s7 > 0:
        return 1, (
            f"PE OI building {pe_vel:+.2%} + put writing — institutional support"
        )
    if pe_vel < -th and s7 < 0:
        return -0.5, f"PE OI unwinding {pe_vel:+.2%} — put covering"
    return 0, f"OI velocity below threshold (CE {ce_vel:+.2%}, PE {pe_vel:+.2%})"

OI_VELOCITY = StatisticSpec(name="OI Velocity", compute=_compute_oi_velocity, score_max=1)


# ── IV Regime ─────────────────────────────────────────────────────────
def _compute_iv_regime(ctx, cfg, intermediates):
    ce_iv_rank = ctx.get("ce_iv_rank")
    pe_iv_rank = ctx.get("pe_iv_rank")
    iv_rank = ctx.get("iv_rank")
    best_ivr = None
    iv_note = "IVR unavailable"

    if ce_iv_rank is not None and pe_iv_rank is not None:
        best_ivr = min(ce_iv_rank, pe_iv_rank)
        best_side = "CE" if ce_iv_rank <= pe_iv_rank else "PE"
        iv_note = f"IVR: CE={ce_iv_rank:.1f}% / PE={pe_iv_rank:.1f}% → best={best_side}({best_ivr:.1f}%)"
    elif ce_iv_rank is not None:
        best_ivr = ce_iv_rank
        iv_note = f"IVR: CE={ce_iv_rank:.1f}% (PE unavailable)"
    elif pe_iv_rank is not None:
        best_ivr = pe_iv_rank
        iv_note = f"IVR: PE={pe_iv_rank:.1f}% (CE unavailable)"
    elif iv_rank is not None:
        best_ivr = iv_rank
        iv_note = f"IVR {iv_rank:.1f}% (legacy single-rank)"

    intermediates["best_ivr"] = best_ivr

    if best_ivr is None:
        return None
    if best_ivr < 20:
        return 1, iv_note + " — structurally cheap, full buyer edge"
    if best_ivr < 40:
        return 0.5, iv_note + " — moderate, mild buyer edge"
    if best_ivr > 60:
        return -1, iv_note + " — structurally expensive, buyer disadvantage"
    if best_ivr > 50:
        return -0.5, iv_note + " — elevated, mild seller edge"
    return 0, iv_note + " — neutral zone (40–50%)"

IV_REGIME = StatisticSpec(name="IV Regime (IVR)", compute=_compute_iv_regime)


# ── Straddle Velocity ─────────────────────────────────────────────────
def _compute_straddle_velocity(ctx, cfg, intermediates):
    straddle_price = ctx.get("straddle_price")
    prev_straddle_price = ctx.get("prev_straddle_price")
    straddle_vel = "Flat"
    if not straddle_price or not prev_straddle_price or prev_straddle_price <= 0:
        return None
    chg_pct = (straddle_price - prev_straddle_price) / prev_straddle_price * 100
    if chg_pct >= 1.5:
        straddle_vel = "Expanding"
        intermediates["straddle_vel"] = straddle_vel
        return 2, f"Straddle expanding {chg_pct:+.1f}% — real directional move, buyer edge"
    if chg_pct >= 0.5:
        straddle_vel = "Mild Expansion"
        intermediates["straddle_vel"] = straddle_vel
        return 1, f"Straddle mild expansion {chg_pct:+.1f}% — modest premium growth"
    if chg_pct <= -1.5:
        straddle_vel = "Contracting"
        intermediates["straddle_vel"] = straddle_vel
        return -2, f"Straddle contracting {chg_pct:+.1f}% — IV crush, avoid naked buying"
    if chg_pct <= -0.5:
        straddle_vel = "Mild Contraction"
        intermediates["straddle_vel"] = straddle_vel
        return -1, f"Straddle mild contraction {chg_pct:+.1f}% — premium fading"
    intermediates["straddle_vel"] = "Flat"
    return 0, f"Straddle flat ({chg_pct:+.1f}%)"

STRADDLE_VELOCITY = StatisticSpec(name="Straddle Velocity", compute=_compute_straddle_velocity, score_max=2)


# ── Synthetic Futures ─────────────────────────────────────────────────
def _compute_synthetic_futures(ctx, cfg, intermediates):
    sf_ltp = ctx.get("sf_ltp")
    spot = ctx.get("spot")
    ce_bid = ctx.get("ce_bid")
    ce_ask = ctx.get("ce_ask")
    prev_spot = ctx.get("prev_spot")
    prev_sf_ltp = ctx.get("prev_sf_ltp")

    if not sf_ltp or not spot:
        return None
    spread_pct = None
    if ce_bid and ce_ask and ce_bid > 0:
        spread_pct = (ce_ask - ce_bid) / ((ce_ask + ce_bid) / 2) * 100
    if spread_pct is not None and spread_pct > 1.5:
        return 0, f"Wide option spread {spread_pct:.1f}% — executable cost degrades signal"
    if prev_spot is not None and prev_sf_ltp is not None:
        move_threshold = spot * 0.0003
        spot_move = spot - prev_spot
        sf_move = sf_ltp - prev_sf_ltp
        if spot_move > move_threshold and sf_move > move_threshold:
            return 1, f"SF co-movement bullish: spot Δ{spot_move:+.1f}, SF Δ{sf_move:+.1f} — confirming"
        if spot_move < -move_threshold and sf_move < -move_threshold:
            return -1, f"SF co-movement bearish: spot Δ{spot_move:+.1f}, SF Δ{sf_move:+.1f} — confirming"
        basis = sf_ltp - spot
        carry = "normal" if basis >= -(spot * 0.001) else "backwardation"
        return 0, f"SF diverging or insufficient move — no directional vote (basis {basis:+.1f}, {carry})"
    basis = sf_ltp - spot
    carry = "normal" if basis >= -(spot * 0.001) else "backwardation"
    return 0, f"SF snapshot only (no prior bar): basis {basis:+.1f} ({carry}) — score 0"

SYNTHETIC_FUTURES = StatisticSpec(name="Synthetic Futures", compute=_compute_synthetic_futures)


STATISTIC_REGISTRY: list[StatisticSpec] = [
    PCR_LEVEL,
    CALL_OI_FLOW,
    PUT_OI_FLOW,
    OI_WALL,
    DELTA_BIAS,
    GAMMA_REGIME,
    OI_VELOCITY,
    IV_REGIME,
    STRADDLE_VELOCITY,
    SYNTHETIC_FUTURES,
]


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 6 — SIGNAL ENGINE           OIFlowAnalyzer / SignalEngine   ║
# ╚══════════════════════════════════════════════════════════════════════╝

class SignalEngine:
    """Computes composite directional score and trap score from market data."""

    def __init__(self, cfg: BotConfig):
        self._config = cfg

    @staticmethod
    def iv_rank(
        current_iv: float | None,
        iv_52w_low: float | None,
        iv_52w_high: float | None,
    ) -> float | None:
        if current_iv is None or iv_52w_low is None or iv_52w_high is None:
            return None
        if iv_52w_high <= iv_52w_low:
            return None
        return (current_iv - iv_52w_low) / (iv_52w_high - iv_52w_low) * 100

    def score(
        self,
        spot: float,
        df_spot: pd.DataFrame,
        chain_rows: list[dict],
        atm_ce_ltp: float,
        atm_pe_ltp: float,
        iv_rank: float | None = None,
        straddle_price: float | None = None,
        prev_straddle_price: float | None = None,
        sf_ltp: float | None = None,
        ce_bid: float | None = None,
        ce_ask: float | None = None,
        pe_bid: float | None = None,
        pe_ask: float | None = None,
        ce_delta: float | None = None,
        pe_delta: float | None = None,
        gex_levels: dict[str, Any] | None = None,
        min_score_override: int | None = None,
        prev_spot: float | None = None,
        prev_sf_ltp: float | None = None,
        ce_iv_rank: float | None = None,
        pe_iv_rank: float | None = None,
        best_fit_iv_side: str | None = None,
    ) -> SignalResult:
        """Compute composite directional score (−100 → +100) and trap_score (0 → 100)."""
        cfg = self._config
        components: list[ScoreComponent] = []
        reasons:    list[str] = []

        # ── LAYER 1: Technical Trend (from INDICATOR_REGISTRY) ────────────────
        for ind_spec in INDICATOR_REGISTRY:
            components.append(ind_spec.evaluate(df_spot, cfg))

        # ── LAYERS 2-5: Market Statistics (from STATISTIC_REGISTRY) ────────────
        _ctx = dict(
            spot=spot, chain_rows=chain_rows,
            atm_ce_ltp=atm_ce_ltp, atm_pe_ltp=atm_pe_ltp,
            iv_rank=iv_rank,
            straddle_price=straddle_price, prev_straddle_price=prev_straddle_price,
            sf_ltp=sf_ltp, ce_bid=ce_bid, ce_ask=ce_ask,
            pe_bid=pe_bid, pe_ask=pe_ask,
            ce_delta=ce_delta, pe_delta=pe_delta,
            gex_levels=gex_levels,
            prev_spot=prev_spot, prev_sf_ltp=prev_sf_ltp,
            ce_iv_rank=ce_iv_rank, pe_iv_rank=pe_iv_rank,
            best_fit_iv_side=best_fit_iv_side,
        )
        _intermediates: dict[str, Any] = {}
        for stat_spec in STATISTIC_REGISTRY:
            components.append(stat_spec.evaluate(_ctx, cfg, _intermediates))

        # ── Trap Score ───────────────────────────────────────────────────────
        trap_score   = 0
        trap_reasons = []
        if _intermediates.get("straddle_vel") == "Contracting":
            trap_score += 25; trap_reasons.append("Straddle contracting — IV crush trap")
        _best_ivr = _intermediates.get("best_ivr")
        if _best_ivr is not None and _best_ivr > 60:
            trap_score += 20; trap_reasons.append(f"High IVR {_best_ivr:.1f}% — options structurally overpriced")
        elif iv_rank is not None and iv_rank > 60:
            trap_score += 20; trap_reasons.append(f"High IVR {iv_rank:.1f}% — options structurally overpriced")
        if sf_ltp and spot and abs(sf_ltp - spot) > spot * 0.015:
            trap_score += 15; trap_reasons.append(f"SF basis divergence {abs(sf_ltp-spot)/spot*100:.2f}% — possible mispricing")
        if ce_bid and ce_ask and ce_bid > 0:
            sp = (ce_ask - ce_bid) / ((ce_ask + ce_bid) / 2) * 100
            if sp > 1.5:
                trap_score += 15; trap_reasons.append(f"Wide CE spread {sp:.1f}% — high slippage cost")
        if pe_bid and pe_ask and pe_bid > 0:
            sp = (pe_ask - pe_bid) / ((pe_ask + pe_bid) / 2) * 100
            if sp > 1.5:
                trap_score += 15; trap_reasons.append(f"Wide PE spread {sp:.1f}% — high slippage cost")
        _pcr = _intermediates.get("pcr")
        if _pcr is not None and _pcr > 2.5:
            trap_score += 10; trap_reasons.append(f"PCR OI {_pcr:.2f} — extreme put skew, reversal risk")
        elif _pcr is not None and _pcr < 0.4:
            trap_score += 10; trap_reasons.append(f"PCR OI {_pcr:.2f} — extreme call skew, reversal risk")
        trap_score = min(100, trap_score)

        # ── Final Score ──────────────────────────────────────────────────────
        # Active score_max sum includes Gamma Regime now.
        # Current total: EMA(1)+RSI(1)+MACD(1)+VWAP(1)+PCR(1)+CE-flow(2)+PE-flow(2)
        # +Wall(1)+Delta(1)+Gamma(2)+OI-vel(1)+IV(1)+Straddle(2)+SF(1) = 16
        MAX_RAW_SCORE = sum(c.score_max for c in components if c.available)
        raw_score  = sum(c.score for c in components if c.available)
        
        # We cap expected alignment to PRACTICAL_ALIGNMENT_FACTOR, so achieving this threshold yields a 100 score.
        effective_max = MAX_RAW_SCORE * PRACTICAL_ALIGNMENT_FACTOR
        base_score = (raw_score / effective_max) * 100 if effective_max > 0 else 0
        
        final_score = int(max(-100, min(100, base_score)))

        for c in components:
            if abs(c.score) >= (c.score_max * 0.5):
                reasons.append(c.note)

        abs_score = abs(final_score)
        effective_min_score = int(min_score_override) if min_score_override is not None else cfg.entry.min_score
        if effective_min_score < 1:
            effective_min_score = 1
        elif effective_min_score > 100:
            effective_min_score = 100

        if trap_score > cfg.entry.max_trap:
            signal = "NO_TRADE"
            if trap_reasons:
                reasons.insert(0, f"⚠ High trap risk: {trap_reasons[0]}")
        elif abs_score >= effective_min_score:
            signal = "EXECUTE"
        elif abs_score >= int(effective_min_score * WATCH_FACTOR):
            signal = "WATCH"
        else:
            signal = "NO_TRADE"

        label = "Bullish" if final_score > 15 else "Bearish" if final_score < -15 else "Neutral"
        direction: str | None = "CE" if final_score > 0 else ("PE" if final_score < 0 else None)

        return SignalResult(
            score=final_score, label=label, signal=signal, direction=direction,
            trap_score=trap_score, trap_reasons=trap_reasons,
            reasons=list(dict.fromkeys(reasons)), components=components,
        )


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 7 — DATA LAYER                          DataFetcher         ║
# ╚══════════════════════════════════════════════════════════════════════╝

class DataFetcher:
    """Fetches all market data using the OpenAlgo SDK client."""

    def __init__(self, client: api, cfg: BotConfig, notify_callback: Callable[[str, int], None] | None = None):
        self.client = client
        self.config = cfg
        self._greeks_cache: OrderedDict[tuple[str, str], dict[str, float]] = OrderedDict()
        self._greeks_cache_hits: int = 0
        self._notify = notify_callback
        self._greeks_cache_misses: int = 0
        self._greeks_api_calls: int = 0
        self._greeks_cache_max_size: int = 500  # LRU: prevent unbounded growth
        self._auth_error_notified: bool = False  # One-time alert per session for UDAPI100050
        self._rate_limit_notified: bool = False  # One-time alert per session for UDAPI10005 rate limit
        # Token bucket rate limiter for fetch_quote (global across all callers)
        self._quote_rate_limit_rps: float = cfg.broker.quote_api_rps
        self._quote_burst: int = cfg.broker.quote_api_burst
        self._quote_tokens: float = float(self._quote_burst)
        self._quote_last_refill: float = time.time()
        self._quote_lock = threading.Lock()
        # Per-symbol expiry list cache (called at most once per symbol per strategy lifecycle).
        self._expiry_list_cache: dict[str, list[str] | None] = {}

    def clear_greeks_cache(self, symbol: str | None = None) -> None:
        """Clear cached option greeks. Called once per scan to avoid stale reads."""
        if symbol is None:
            self._greeks_cache.clear()
            self._greeks_cache_hits = 0
            self._greeks_cache_misses = 0
            self._greeks_api_calls = 0
            return
        keys = [k for k in self._greeks_cache if k[0] == symbol]
        for k in keys:
            self._greeks_cache.pop(k, None)
        # Symbol scan cycle starts fresh counters.
        self._greeks_cache_hits = 0
        self._greeks_cache_misses = 0
        self._greeks_api_calls = 0

    def _fetch_option_greeks_cached(self, symbol: str, option_symbol: str | None) -> dict[str, float] | None:
        if not option_symbol:
            return None
        cache_key = (symbol, option_symbol)
        cached = self._greeks_cache.get(cache_key)
        if cached is not None:
            self._greeks_cache_hits += 1
            self._greeks_cache.move_to_end(cache_key)
            return cached
        self._greeks_cache_misses += 1

        # Rate limit: share token bucket with fetch_quote()
        if not self._acquire_quote_token():
            return None

        try:
            self._greeks_api_calls += 1
            resp = self.client.optiongreeks(
                symbol=option_symbol,
                exchange=self.config.market.fno_exchange,
                underlying_symbol=symbol,
                underlying_exchange=self.underlying_exchange(symbol),
            )
            if resp and resp.get("status") == "success":
                greeks = resp.get("greeks", {}) or {}
                parsed = {
                    "delta": float(greeks.get("delta", 0) or 0),
                    "gamma": float(greeks.get("gamma", 0) or 0),
                    "theta": float(greeks.get("theta", 0) or 0),
                    "iv": float(resp.get("implied_volatility", 0) or 0),
                }
                while len(self._greeks_cache) >= self._greeks_cache_max_size:
                    self._greeks_cache.popitem(last=False)
                self._greeks_cache[cache_key] = parsed
                return parsed
        except Exception as exc: err(f"[DATA] optiongreeks error for {option_symbol}: ", exc)
        return None

    def greeks_perf_snapshot(self, symbol: str | None = None) -> dict[str, float | int]:
        cache_size = len(self._greeks_cache)
        if symbol is not None:
            cache_size = sum(1 for k in self._greeks_cache if k[0] == symbol)
        total_lookups = self._greeks_cache_hits + self._greeks_cache_misses
        hit_rate = (self._greeks_cache_hits / total_lookups * 100.0) if total_lookups > 0 else 0.0
        return {
            "hits": self._greeks_cache_hits,
            "misses": self._greeks_cache_misses,
            "api_calls": self._greeks_api_calls,
            "cache_size": cache_size,
            "hit_rate": round(hit_rate, 1),
        }

    def batch_prefetch_option_greeks(self, symbol: str, option_symbols: list[str]) -> None:
        """Prefetch greeks for unique option symbols used in this scan cycle."""
        for opt_sym in dict.fromkeys([s for s in option_symbols if s]):
            self._fetch_option_greeks_cached(symbol, opt_sym)

    def underlying_exchange(self, symbol: str) -> str:
        """Return NSE_INDEX/BSE_INDEX for index underlyings, else SPOT_EXCHANGE."""
        return self.config.market.index_exchange if symbol in self.config.market.index_underlyings else self.config.market.spot_exchange

    def fetch_candles(self, symbol: str, exchange: str) -> pd.DataFrame | None:
        """Fetch OHLCV history in pandas DataFrame format for any instrument symbol on a given exchange."""
        try:
            end = get_ist_now()
            start = end - timedelta(days=self.config.market.lookback_days)
            result = self.client.history(
                symbol=symbol,
                exchange=exchange,
                interval=self.config.market.candle_interval,
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
            )
            if not isinstance(result, pd.DataFrame):
                dbg(f"[DATA] history() returned non-DataFrame for {symbol}@{exchange}: {result}")
                return None
            return result
        except Exception as exc:
            err(f"[DATA] Candle fetch error for {symbol}@{exchange}", exc)
            return None

    def fetch_spot_candles(self, symbol: str) -> pd.DataFrame | None:
        df = self.fetch_candles(symbol, self.underlying_exchange(symbol))
        if df is None or len(df) < self.config.entry.slow_ema_period + 5:
            return None
        return df

    def fetch_option_candles(self, option_symbol: str) -> pd.DataFrame | None:
        return self.fetch_candles(option_symbol, self.config.market.fno_exchange)

    def fetch_option_chain(self, symbol: str, expiry: str | None = None) -> tuple[list[dict], str | None]:
        """Fetch and flatten the option chain (CE/PE nested → flat dicts)."""
        try:
            ul_exchange = self.underlying_exchange(symbol)
            kwargs: dict = dict(underlying=symbol, exchange=ul_exchange)
            if expiry:
                kwargs["expiry_date"] = expiry
            kwargs["strike_count"] = self.config.market.strike_count
            raw = self.client.optionchain(**kwargs)
            if not raw:
                return [], None
            if isinstance(raw, dict) and raw.get("status") == "error":
                err(f"[DATA] Option chain API error for {symbol}: {raw.get('message', str(raw))}")
                return [], None
            if isinstance(raw, dict):
                expiry_date = raw.get("expiry_date")
                nested = raw.get("chain", raw.get("data", []))
            else:
                nested, expiry_date = raw, None
            if not isinstance(nested, list):
                return [], expiry_date

            flat_rows: list[dict] = []
            for entry in nested:
                strike = entry.get("strike")
                if strike is None:
                    continue
                ce = entry.get("ce") or {}
                pe = entry.get("pe") or {}
                ce_ltp  = float(ce.get("ltp")  or 0) or None
                pe_ltp  = float(pe.get("ltp")  or 0) or None
                ce_prev = float(ce.get("prev_close") or 0) or None
                pe_prev = float(pe.get("prev_close") or 0) or None
                flat_rows.append({
                    "strike":     strike,
                    "ce_symbol":  ce.get("symbol"),
                    "pe_symbol":  pe.get("symbol"),
                    "ce_ltp":     ce_ltp,
                    "pe_ltp":     pe_ltp,
                    "ce_bid":     float(ce.get("bid") or 0) or None,
                    "ce_ask":     float(ce.get("ask") or 0) or None,
                    "pe_bid":     float(pe.get("bid") or 0) or None,
                    "pe_ask":     float(pe.get("ask") or 0) or None,
                    "ce_oi":      float(ce.get("oi")  or 0),
                    "pe_oi":      float(pe.get("oi")  or 0),
                    "ce_volume":  float(ce.get("volume") or 0),
                    "pe_volume":  float(pe.get("volume") or 0),
                    "ce_oi_chg":  float(ce.get("oi_change") or 0),
                    "pe_oi_chg":  float(pe.get("oi_change") or 0),
                    "ce_ltp_chg": (ce_ltp - ce_prev) if (ce_ltp and ce_prev) else 0.0,
                    "pe_ltp_chg": (pe_ltp - pe_prev) if (pe_ltp and pe_prev) else 0.0,
                    "lotsize":    ce.get("lotsize") or pe.get("lotsize") or 1,
                })
            return flat_rows, expiry_date
        except Exception as exc:
            err(f"[DATA] Option chain error for {symbol}", exc)
            return [], None

    def _acquire_quote_token(self) -> bool:
        """Acquire a token from the quote API rate limiter.
        Returns True if token acquired, False if rate limited.
        """
        with self._quote_lock:
            now = time.time()
            # Refill tokens based on elapsed time
            elapsed = now - self._quote_last_refill
            self._quote_tokens = min(
                self._quote_burst,
                self._quote_tokens + elapsed * self._quote_rate_limit_rps
            )
            self._quote_last_refill = now
            if self._quote_tokens >= 1.0:
                self._quote_tokens -= 1.0
                return True
            return False

    def fetch_quote(self, symbol: str, exchange: str) -> dict:
        # Rate limit: return empty if rate limited
        if not self._acquire_quote_token():
            dbg(f"[RATE] fetch_quote rate limited for {symbol}@{exchange}")
            return {}
        try:
            response = self.client.quotes(symbol=symbol, exchange=exchange) or {}
            if response.get("status") == "success":
                return response.get("data", {})
            
            error_msg = response.get("message", "")
            if isinstance(error_msg, str) and ("Invalid token" in error_msg or "UDAPI100050" in error_msg):
                err(f"{symbol}@{exchange}: broker token invalid (UDAPI100050): {response}")
                if self._notify and not self._auth_error_notified:
                    self._auth_error_notified = True
                    self._notify(
                        f"🚨 API Auth Error: Broker token invalid (UDAPI100050) for {symbol}.\n"
                        f"All quote/chain calls will fail until token is refreshed.\n"
                        f"Action: Re-login to broker and restart strategy.",
                        9,
                    )
            elif isinstance(error_msg, str) and ("UDAPI10005," in error_msg or "Too Many Request Sent" in error_msg):
                err(f"{symbol}@{exchange}: broker rate limit (UDAPI10005): {response}")
                if self._notify and not hasattr(self, '_rate_limit_notified'):
                    self._rate_limit_notified = True
                    self._notify(
                        f"⚠️ Upstox rate limit hit (UDAPI10005) for {symbol}.\n"
                        f"Action: Reduce quote API frequency or check for other clients using same API key.",
                        7,
                    )
                time.sleep(2)  # Backoff before next call to let the rate window reset
            elif isinstance(error_msg, str) and "not found" in error_msg.lower():
                dbg(f"[QUOTES] {symbol}@{exchange}: symbol not found (expected if weekly expiry has no corresponding futures contract)")
            else:
                err(f"{symbol}@{exchange}: quotes API error: {response}")
            return {}
        except Exception as e:
            if "Invalid token" in str(e) or "UDAPI100050" in str(e):
                err(f"{symbol}@{exchange}: broker token invalid", e)
                if self._notify and not self._auth_error_notified:
                    self._auth_error_notified = True
                    self._notify(
                        f"🚨 API Auth Error: Broker token invalid (exception) for {symbol}.\n"
                        f"Action: Re-login to broker and restart strategy.",
                        9,
                    )
            else:
                err(f"{symbol}@{exchange}: quotes API exception", e)
            return {}

    def fetch_synthetic_future(self, symbol: str, expiry: str | None) -> float | None:
        if symbol in self.config.market.index_underlyings and expiry:
            try:
                resp = self.client.syntheticfuture(
                    underlying=symbol,
                    exchange=self.underlying_exchange(symbol),
                    expiry_date=expiry,
                )
                if resp and resp.get("status") == "success":
                    price = float(resp.get("synthetic_future_price") or 0)
                    return price if price else None
            except Exception as exc: err(f"[DATA] syntheticfuture error for {symbol}: ", exc)
        return None

    def fetch_atm_greeks(self, symbol: str, ce_symbol: str | None, pe_symbol: str | None) -> tuple[float | None, float | None]:
        ce_delta: float | None = None
        pe_delta: float | None = None
        for opt_sym, key in ((ce_symbol, "ce"), (pe_symbol, "pe")):
            if not opt_sym:
                continue
            greeks = self._fetch_option_greeks_cached(symbol, opt_sym)
            if greeks is not None:
                delta = greeks.get("delta")
                if key == "ce":
                    ce_delta = float(delta)
                else:
                    pe_delta = float(delta)
        return ce_delta, pe_delta

    def fetch_option_delta(self, symbol: str, option_symbol: str | None) -> float | None:
        if not option_symbol:
            return None
        greeks = self._fetch_option_greeks_cached(symbol, option_symbol)
        if greeks is not None:
            return abs(float(greeks.get("delta", 0) or 0))
        return None

    def fetch_option_gamma(self, symbol: str, option_symbol: str | None) -> float | None:
        if not option_symbol:
            return None
        greeks = self._fetch_option_greeks_cached(symbol, option_symbol)
        if greeks is not None:
            return float(greeks.get("gamma", 0) or 0)
        return None

    @staticmethod
    def derive_gex_levels(gex_chain: list[dict], spot_price: float) -> dict[str, Any]:
        """Derive institutional GEX levels from per-strike net-gex profile."""
        if not gex_chain:
            return {
                "gamma_flip": None,
                "call_gamma_wall": None,
                "put_gamma_wall": None,
                "absolute_wall": None,
                "total_net_gex": 0.0,
                "upside_punch_target": None,
                "downside_punch_target": None,
            }

        sorted_chain = sorted(gex_chain, key=lambda x: x["strike"])
        total_net_gex = float(sum(float(x.get("net_gex", 0) or 0) for x in sorted_chain))

        # Gamma flip via cumulative net-gex sign change.
        gamma_flip: float | None = None
        cumsum = 0.0
        prev_sign = None
        prev_item = None
        for item in sorted_chain:
            prev_cumsum = cumsum
            cumsum += float(item.get("net_gex", 0) or 0)
            sign = 1 if cumsum >= 0 else -1
            if prev_sign is not None and sign != prev_sign and prev_item is not None:
                if cumsum != prev_cumsum:
                    frac = -prev_cumsum / (cumsum - prev_cumsum)
                    gamma_flip = round(
                        float(prev_item["strike"]) + frac * (float(item["strike"]) - float(prev_item["strike"])),
                        2,
                    )
                else:
                    gamma_flip = float(item["strike"])
                break
            prev_sign = sign
            prev_item = item

        above_spot_pos = [x for x in sorted_chain if x["strike"] > spot_price and (x.get("net_gex", 0) or 0) > 0]
        below_spot_neg = [x for x in sorted_chain if x["strike"] < spot_price and (x.get("net_gex", 0) or 0) < 0]
        call_gamma_wall = max(above_spot_pos, key=lambda x: x["net_gex"])["strike"] if above_spot_pos else None
        put_gamma_wall = min(below_spot_neg, key=lambda x: x["net_gex"])["strike"] if below_spot_neg else None
        absolute_wall = max(sorted_chain, key=lambda x: abs(x.get("net_gex", 0) or 0))["strike"] if sorted_chain else None

        above_neg = [x for x in sorted_chain if x["strike"] > spot_price and (x.get("net_gex", 0) or 0) < 0]
        below_neg = [x for x in sorted_chain if x["strike"] < spot_price and (x.get("net_gex", 0) or 0) < 0]
        upside_punch_target = min(above_neg, key=lambda x: x["strike"])["strike"] if above_neg else None
        downside_punch_target = max(below_neg, key=lambda x: x["strike"])["strike"] if below_neg else None

        return {
            "gamma_flip": gamma_flip,
            "call_gamma_wall": call_gamma_wall,
            "put_gamma_wall": put_gamma_wall,
            "absolute_wall": absolute_wall,
            "total_net_gex": round(total_net_gex, 2),
            "upside_punch_target": upside_punch_target,
            "downside_punch_target": downside_punch_target,
        }

    def fetch_gex_levels(self, symbol: str, chain_rows: list[dict], spot_price: float) -> dict[str, Any] | None:
        """Compute per-strike GEX from live option greeks + OI using SDK APIs."""
        if not self.config.entry.gex_enabled:
            return None
        if not chain_rows or not spot_price:
            return None

        gex_chain: list[dict] = []
        for row in chain_rows:
            strike = float(row.get("strike", 0) or 0)
            if not strike:
                continue

            ce_symbol = row.get("ce_symbol")
            pe_symbol = row.get("pe_symbol")
            ce_oi = float(row.get("ce_oi", 0) or 0)
            pe_oi = float(row.get("pe_oi", 0) or 0)
            lot_size = float(row.get("lotsize", 1) or 1)

            ce_gamma = self.fetch_option_gamma(symbol, ce_symbol) if ce_oi > 0 else None
            pe_gamma = self.fetch_option_gamma(symbol, pe_symbol) if pe_oi > 0 else None

            ce_gex = (ce_gamma or 0.0) * ce_oi * lot_size
            pe_gex = (pe_gamma or 0.0) * pe_oi * lot_size
            net_gex = ce_gex - pe_gex

            gex_chain.append(
                {
                    "strike": strike,
                    "ce_gamma": round(float(ce_gamma or 0.0), 6),
                    "pe_gamma": round(float(pe_gamma or 0.0), 6),
                    "ce_gex": round(float(ce_gex), 2),
                    "pe_gex": round(float(pe_gex), 2),
                    "net_gex": round(float(net_gex), 2),
                }
            )

        if not gex_chain:
            return None

        levels = self.derive_gex_levels(gex_chain, spot_price)
        levels["chain"] = gex_chain
        return levels

    def fetch_atm_iv_ranks(self, symbol: str, ce_symbol: str | None = None, pe_symbol: str | None = None) -> dict[str, float | None]:
        """Fetch separate IV Rank for ATM CE and PE.
        Returns: {"ce_iv_rank": float|None, "pe_iv_rank": float|None, "best_fit": "CE"|"PE"|None}
        Best fit = lower IVR (cheaper options for buying).
        """
        result = {"ce_iv_rank": None, "pe_iv_rank": None, "best_fit": None}
        try:
            # Fetch CE IVR
            if ce_symbol:
                ce_greeks = self._fetch_option_greeks_cached(symbol, ce_symbol)
                if ce_greeks:
                    ce_iv = ce_greeks.get("iv")
                    if ce_iv is not None and float(ce_iv) > 0:
                        result["ce_iv_rank"] = SignalEngine.iv_rank(
                            float(ce_iv), self.config.entry.iv_52w_low, self.config.entry.iv_52w_high
                        )
            
            # Fetch PE IVR
            if pe_symbol:
                pe_greeks = self._fetch_option_greeks_cached(symbol, pe_symbol)
                if pe_greeks:
                    pe_iv = pe_greeks.get("iv")
                    if pe_iv is not None and float(pe_iv) > 0:
                        result["pe_iv_rank"] = SignalEngine.iv_rank(
                            float(pe_iv), self.config.entry.iv_52w_low, self.config.entry.iv_52w_high
                        )
            
            # Determine best fit: lower IVR = cheaper = better for buying
            ce_ivr = result["ce_iv_rank"]
            pe_ivr = result["pe_iv_rank"]
            if ce_ivr is not None and pe_ivr is not None:
                result["best_fit"] = "CE" if ce_ivr <= pe_ivr else "PE"
            elif ce_ivr is not None:
                result["best_fit"] = "CE"
            elif pe_ivr is not None:
                result["best_fit"] = "PE"
            
        except Exception as exc: err(f"[DATA] IV ranks fetch error: ", exc)
        
        return result

    def _expiry_list(self, symbol: str) -> list[str] | None:
        """Fetch and cache the raw expiry list. Called at most once per symbol per strategy lifecycle."""
        if symbol in self._expiry_list_cache:
            return self._expiry_list_cache[symbol]
        if not hasattr(self.client, "expiry"):
            self._expiry_list_cache[symbol] = None
            return None
        try:
            resp = self.client.expiry(
                symbol=symbol,
                exchange=self.config.market.fno_exchange,
                instrumenttype="options",
            )
            if not resp:
                self._expiry_list_cache[symbol] = None
                return None
            if isinstance(resp, list):
                parsed: list[str] = resp
            elif isinstance(resp, dict):
                parsed = resp.get("data", resp.get("expiries", []))
            else:
                self._expiry_list_cache[symbol] = None
                return None
            self._expiry_list_cache[symbol] = parsed
            return parsed
        except Exception as exc:
            err(f"[DATA] expiry list fetch error for {symbol}", exc)
            self._expiry_list_cache[symbol] = None
            return None

    def fetch_target_expiry(self, symbol: str) -> str | None:
        expiry_list = self._expiry_list(symbol)
        if not expiry_list:
            return None
        now = get_ist_now().date()
        for exp in expiry_list:
            exp_text = str(exp).strip().upper()
            exp_date = None
            for fmt in ("%d%b%y", "%d-%b-%y", "%d%b%Y", "%d-%b-%Y"):
                try:
                    exp_date = datetime.strptime(exp_text, fmt).date()
                    break
                except ValueError:
                    pass
            if exp_date is None:
                continue
            dte = (exp_date - now).days
            if self.config.market.dte_min <= dte <= self.config.market.dte_max:
                return exp_date.strftime("%d%b%y").upper()
        return None

    def pick_nearest_expiry(self, symbol: str) -> str | None:
        """Return the nearest available expiry when none is in DTE range."""
        expiry_list = self._expiry_list(symbol)
        if not expiry_list:
            return None
        first = str(expiry_list[0]).strip().upper()
        for fmt in ("%d%b%y", "%d-%b-%y", "%d%b%Y", "%d-%b-%Y"):
            try:
                exp_date = datetime.strptime(first, fmt).date()
                return exp_date.strftime("%d%b%y").upper()
            except ValueError:
                continue
        return None


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 8 — ENTRY ENGINE                   EntryStopLossPolicy +    ║
# ║                                            StrikeSelector            ║
# ╚══════════════════════════════════════════════════════════════════════╝

class EntryStopLossPolicy:
    """Resolves Phase A initial hard SL points (premium-based) using delta-aware moneyness adaptation or fallback fixed points."""

    def __init__(self, fetcher: DataFetcher, cfg: BotConfig):
        self._fetcher = fetcher
        self._config = cfg

    @staticmethod
    def get_moneyness_multipliers(delta: float | None) -> tuple[str, float, float, float]:
        """
        Returns (moneyness_label, sl_width_pct, tgt_mult, act_mult).
        Deep-ITM: Tightest SL width (20%), Largest TP (2.0x), Smallest Trail Act buffer (0.5x).
        Deep-OTM: Widest SL width (75%), Smallest TP (0.5x), Largest Trail Act buffer (2.0x).
        """
        if delta is None:
            return ("Unknown", 40, 1.0, 1.0)
        d = abs(delta)
        if d >= 0.75: return ("Deep-ITM", 20, 2.0, 0.5)
        elif d >= 0.65: return ("ITM", 25, 1.5, 0.75)
        elif d >= 0.55: return ("Sl-ITM", 30, 1.25, 0.9)
        elif d >= 0.45: return ("ATM", 40, 1.0, 1.0)
        elif d >= 0.35: return ("Sl-OTM", 50, 0.85, 1.2)
        elif d >= 0.25: return ("OTM", 60, 0.7, 1.5)
        else: return ("Deep-OTM", 75, 0.5, 2.0)

    def _sl_pts_by_delta(self, delta: float | None, entry_premium: float) -> tuple[float, str]:
        """Compute raw SL points adapted to entry delta (moneyness). Wider SL for OTM, tighter for ITM.
        No cap applied here — the final ceiling is applied once, at the end
        of the full modifier chain in scan_underlying (via cfg.entry.max_sl_pts).
        """
        moneyness, sl_width_pct, _, _ = self.get_moneyness_multipliers(delta)
        sl_pts = max(10, entry_premium * (sl_width_pct / 100.0))
        return (sl_pts, moneyness)

    def resolve_entry_sl_points(
        self,
        option_symbol: str,
        df_spot: pd.DataFrame | None,
        entry_delta: float | None = None,
        est_premium: float | None = None,
    ) -> tuple[float, str]:
        """Resolve Phase A hard entry SL using delta moneyness (if available), else fallback fixed pts."""
        cfg = self._config
        base_sl = cfg.entry.premium_stop_pts
        base_source = "hard_sl_pts_fallback"

        if entry_delta is not None and est_premium is not None and est_premium > 0:
            delta_sl, moneyness = self._sl_pts_by_delta(entry_delta, est_premium)
            return (delta_sl, f"moneyness_adapted_{moneyness}")
        
        return (base_sl, base_source)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 8b — PROTECTION MONITOR                                   ║
# ╚══════════════════════════════════════════════════════════════════════╝

class ProtectionMonitor:
    """Institutional rules for premium protection.

    Note: monotonicity is already structurally enforced at every ratchet
    site via `if new_sl > pos.sl:` — the code never assigns a non-improving
    SL. monotonic() below checks against pos.sl directly rather than a
    separate tracker, verifying the *existing* invariant rather than
    introducing a new guard.
    """

    @staticmethod
    def is_protected(pos: OptionPosition, sl_premium: float) -> bool:
        """Capital is protected when SL is above a defined floor."""
        return sl_premium >= pos.entry_premium * 0.5

    @staticmethod
    def profit_is_protected(pos: OptionPosition, sl_premium: float) -> bool:
        """Profit is protected when SL is at or above entry premium."""
        return sl_premium >= pos.entry_premium

    @staticmethod
    def monotonic(proposed_sl: float, pos: OptionPosition) -> bool:
        """True if proposed_sl would not weaken current protection."""
        return proposed_sl >= pos.sl - 0.01


def check_invariants(pos: OptionPosition, last_seen_sl: float | None, last_seen_peak: float | None) -> list[str]:
    """Check runtime invariants for a single position.
    Call once per scan cycle, passing externally-tracked "last seen" values
    since neither _prev_epoch_sl nor _prev_peak_close exist on TrailState.
    """
    violations: list[str] = []
    if last_seen_sl is not None and pos.sl < last_seen_sl - 0.01:
        violations.append(f"SL went backward: {last_seen_sl:.2f} -> {pos.sl:.2f}")
    if last_seen_peak is not None and pos.trail_peak_close is not None and pos.trail_peak_close < last_seen_peak - 0.01:
        violations.append(f"Peak decreased: {last_seen_peak:.2f} -> {pos.trail_peak_close:.2f}")
    for v in violations:
        err(f"[INVARIANT] {pos.symbol}: {v}")
    return violations

def validate_state(state: BotState, last_seen_sl_by_slot: dict[str, float], _cycle: int = 0) -> list[str]:
    """Periodic state validation across all positions.
    Maintain `last_seen_sl_by_slot` at the call site and pass it in each cycle.
    """
    violations: list[str] = []
    for slot_id, pos in state.positions.all_items():
        snap = state.snapshot_cache.get_for_symbol(pos.symbol)
        if snap and snap.option_ltp is not None and pos.sl > snap.option_ltp:
            violations.append(f"SL {pos.sl:.1f} > current premium {snap.option_ltp:.1f} for {slot_id}")
        _last_sl = last_seen_sl_by_slot.get(slot_id)
        if _last_sl is not None and pos.sl < _last_sl - 0.01:
            violations.append(f"Protection weakened for {slot_id}: {_last_sl} -> {pos.sl}")
        last_seen_sl_by_slot[slot_id] = pos.sl
    for v in violations:
        err(f"[VALIDATION] {v}")
    return violations


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 9 — TRAIL ENGINE                      TrailSLEngine         ║
# ╚══════════════════════════════════════════════════════════════════════╝

class TrailSLEngine:
    """
    Computes trailing SL ratchets (Phase B) periodically on the strategy thread.
    Supports fixed %, ATR-based, and live Delta-based trailing steps.
    """

    def __init__(self, fetcher: DataFetcher, cfg: BotConfig):
        self._fetcher = fetcher
        self._config = cfg
        self.modify_callback: Callable[[str, float, str | None], bool] | None = None
        self._last_pl_pct: dict[str, float] = {}
        self._data_skip_logged: set[str] = set()
        self._kl_tick_count: dict[str, int] = {}

    def _compute_raw_activation_threshold(self, pos: OptionPosition) -> tuple[float, float, float]:
        """Returns (raw_threshold, capped_threshold, target_gain_cap).

        raw_threshold = entry_premium * 25% * conviction_scale
        capped = min(raw, activate_at_max_pts, target_gain * 0.8)
        """
        cfg = self._config
        ep = pos.entry_premium
        _conv = max(0.01, cfg.trail.conv_trail_act_base - pos.entry_conviction * cfg.trail.conv_trail_act_range)
        raw = ep * 0.25 * _conv
        _tgt_gain = (pos.tgt - ep) * 0.8 if pos.tgt > ep else 999.0
        capped = min(raw, cfg.trail.activate_at_max_pts, _tgt_gain)
        return (raw, capped, _tgt_gain)

    def compute_activation_threshold(self, pos: OptionPosition) -> float:
        """Public: returns the capped activation threshold in premium pts above entry.
        Returns 0.0 for ATR mode — activation is at breakeven."""
        cfg = self._config
        if cfg.trail.sl_method == "atr":
            return 0.0
        return self._compute_raw_activation_threshold(pos)[1]

    def check_trailing_stops(self, state: BotState) -> None:
        """Run periodically to calculate trailing SL ratchets and update orders if needed."""
        cfg = self._config
        with state.state_lock:
            positions = list(state.positions.all_items())

        if positions:
            _ep_strs = [f"{ul}={pos.entry_premium:.1f}" for ul, pos in positions if not pos.exit_pending]
            _gain_strs = []
            _act_strs = []
            for ul, pos in positions:
                if pos.exit_pending:
                    continue
                _snap = state.snapshot_cache.get_for_symbol(pos.symbol)
                _cur_ltp = _snap.option_ltp if _snap else None
                _gain = _cur_ltp - pos.entry_premium if _cur_ltp is not None else None
                if cfg.trail.sl_method == "atr":
                    _act_strs.append(f"{ul}:atr→BE")
                else:
                    _raw, _capped, _ = self._compute_raw_activation_threshold(pos)
                    _act_strs.append(f"{ul}:{_raw:.0f}->{_capped:.1f}")
                _gain_strs.append(f"{ul}:{_gain:.1f}" if _gain is not None else f"{ul}:N/A")
            inf(f"[TRAIL] check_trailing_stops: {len(positions)} pos(s) — "
                f"EP=[{', '.join(_ep_strs)}]  "
                f"GAIN=[{', '.join(_gain_strs)}]  "
                f"ACT=[{', '.join(_act_strs)}]")

        for underlying, pos in positions:
            if pos.exit_pending:
                continue

            # CE+PE safe: fetch option data for the exact position symbol
            _opt_snap = state.snapshot_cache.get_for_symbol(pos.symbol)
            _spot_snap = state.snapshot_cache.get(pos.underlying)
            opt_ltp = _opt_snap.option_ltp if _opt_snap else None
            spot_ltp = _spot_snap.spot_ltp if _spot_snap else None

            # Only require spot_ltp for modes that actually consume it
            _needs_spot = (
                cfg.trail.sl_method == "key_level"
                or cfg.trail.tracking_mode == "spot"
            )
            _missing = []
            if opt_ltp is None:
                _missing.append("option_ltp")
            if _needs_spot and spot_ltp is None:
                _missing.append("spot_ltp")

            if _missing:
                _key = f"{underlying}|{'_'.join(_missing)}"
                if _key not in self._data_skip_logged:
                    self._data_skip_logged.add(_key)
                    _ts = (_opt_snap.timestamp if _opt_snap else None) or (_spot_snap.timestamp if _spot_snap else None)
                    inf(
                        f"[DATA-MISS] {underlying}: {_missing} — "
                        f"snapshot={_ts if _ts else 'NONE'} | "
                        f"age={(time.time() - _ts):.1f}s" if _ts else ""
                    )
                continue
            if self._data_skip_logged:
                self._data_skip_logged.clear()
            confirmed_close = opt_ltp
            if confirmed_close is None:
                continue
            prior_trail_peak_close = (
                pos.trail_peak_close
                if pos.trail_peak_close is not None
                else pos.entry_premium
            )
            is_new_confirmed_close_high = confirmed_close > prior_trail_peak_close
            if is_new_confirmed_close_high:
                pos.trail_peak_close = confirmed_close

            ep = pos.entry_premium
            # ── Trail analytics (continuous update) ─────────────────────
            pos.mfe = max(pos.mfe, confirmed_close - ep)
            if pos.premium_trail_active or pos.kl_active or pos.trail_active:
                if pos.peak_after_activation is None or confirmed_close > pos.peak_after_activation:
                    pos.peak_after_activation = confirmed_close
                if pos.mae_after_activation is None or confirmed_close < pos.mae_after_activation:
                    pos.mae_after_activation = confirmed_close

            # ── Activation Buffer ────────
            _trail_conv_adj = cfg.trail.conv_trail_act_base - pos.entry_conviction * cfg.trail.conv_trail_act_range

            # V2-A3: Signal-aware trail tightening
            _signal_trail_boost = 1.0
            _sig_data = state.latest_signals.get(underlying)
            if _sig_data and time.time() - _sig_data[1] < cfg.market.signal_check_interval * 3:
                _sig_result = _sig_data[0]
                _sig_dir = _sig_result.direction
                if _sig_dir and _sig_dir != pos.option_type and abs(_sig_result.score) >= cfg.entry.min_score:
                    _sig_strength = abs(_sig_result.score) / 100.0
                    _trail_conv_adj *= 1.0 - (_sig_strength * 0.4)
                    _signal_trail_boost = 1.0 + (_sig_strength * 0.5)
            
            # ── Mode Processing ────────
            spot_ltp = _spot_snap.spot_ltp if _spot_snap else None
            if spot_ltp is None:
                continue
            if cfg.trail.sl_method == "key_level":
                self._process_key_level_trail(underlying, pos, spot_ltp, confirmed_close)
            elif cfg.trail.tracking_mode == "premium":
                self._process_premium_trail(
                    underlying,
                    pos,
                    confirmed_close,
                    _trail_conv_adj,
                    is_new_confirmed_close_high,
                    _signal_trail_boost,
                )
            elif cfg.trail.tracking_mode == "spot":
                self._process_spot_trail(underlying, pos, spot_ltp, _trail_conv_adj, _signal_trail_boost)

            # ── Record activation analytics on first detection ────────
            if pos.activation_time is None and (
                pos.premium_trail_active or pos.kl_active or pos.trail_active
            ):
                pos.activation_time = get_ist_now()
                pos.activation_price = confirmed_close
                pos.activation_bucket = state.bucket_counter
                pos.peak_after_activation = confirmed_close
                pos.mae_after_activation = confirmed_close

    def _get_step_pts(self, pos: OptionPosition, base_dist: float, price_series_df: pd.DataFrame | None, current_delta: float | None = None) -> float:
        """Resolve step points based on sl_method.

        Cap logic (prevents oversized steps on high-premium options):
          fixed_pts → raw N pts, no cap (it IS the explicit value)
          fixed_pct → capped at entry_premium × 50%
          delta     → capped at entry_premium × 50%
          atr       → no cap (ATR is self-scaling)
        """
        cfg = self._config
        method = cfg.trail.sl_method

        # ── fixed_pts: always return a fixed raw premium point step ──────────
        if method == "fixed_pts":
            return max(1.0, cfg.trail.step_pts)

        # ── atr: self-adapting; no external cap applied ────────────────────
        if method == "atr" and price_series_df is not None and len(price_series_df) >= cfg.trail.atr_period + 2:
            try:
                # Filter to today's session only — prevents overnight gaps inflating ATR
                _df_atr = price_series_df
                if isinstance(price_series_df.index, pd.DatetimeIndex):
                    _df_today = price_series_df[price_series_df.index.tz_localize(None).normalize() == pd.Timestamp(get_ist_now().date())]
                    if len(_df_today) >= cfg.trail.atr_period + 2:
                        _df_atr = _df_today
                atr_series = ta.atr(
                    _df_atr["high"],
                    _df_atr["low"],
                    _df_atr["close"],
                    period=cfg.trail.atr_period,
                )
                atr_val = ta_value(atr_series, -2)
                if atr_val is not None and atr_val > 0:
                    return atr_val * cfg.trail.atr_mult
            except Exception as e: err(f"[TRAIL] ATR compute error: ", e)

        # ── delta: tier-based pct ──────────────────────────────────────────
        if method == "delta" and current_delta is not None:
            d = abs(current_delta)
            if d >= 0.55:   step_pct = cfg.trail.delta_itm_step_pct
            elif d >= 0.35: step_pct = cfg.trail.delta_atm_step_pct
            else:           step_pct = cfg.trail.delta_otm_step_pct
            return base_dist * (step_pct / 100.0)

        # ── fixed_pct (default/fallback) ───────────────────────────────────
        return base_dist * (cfg.trail.step_pct / 100.0)

    def _process_premium_trail(
        self,
        underlying: str,
        pos: OptionPosition,
        confirmed_close: float,
        conv_adj: float,
        is_new_confirmed_close_high: bool,
        signal_trail_boost: float = 1.0,
    ) -> None:
        cfg = self._config
        ep = pos.entry_premium
        move = confirmed_close - ep
        ltp = confirmed_close
        
        # ATR method: activate after price crosses BE + buffer_pts
        if cfg.trail.sl_method == "atr":
            _atr_buffer = cfg.trail.atr_activation_buffer_pts
            if not pos.premium_trail_active and move <= _atr_buffer:
                return
            activate_pts = _atr_buffer  # for logging — 0.0 = pure breakeven activation
        else:
            activate_pts = ep * (cfg.trail.activate_at_pct / 100.0) * conv_adj * pos.trail_act_mult
            # Hard ceiling: prevents activation requiring more pts than the TP window on high-premium options
            if cfg.trail.activate_at_max_pts > 0:
                activate_pts = min(activate_pts, cfg.trail.activate_at_max_pts)
            # Self-correcting cap: never require more than 80% of this position's own target gain
            _tgt_gain = pos.tgt - ep
            if _tgt_gain > 0:
                activate_pts = min(activate_pts, _tgt_gain * 0.8)

            if not pos.premium_trail_active and move < activate_pts:
                return  # not activated yet

        # Resolve step points
        current_delta = None
        df = None
        if cfg.trail.sl_method == "delta":
            greeks = self._fetcher._fetch_option_greeks_cached(underlying, pos.symbol)
            if greeks and "delta" in greeks:
                current_delta = greeks["delta"]
        elif cfg.trail.sl_method == "atr":
            df = self._fetcher.fetch_option_candles(pos.symbol)
            
        _base_step_pts = self._get_step_pts(pos, ep, df, current_delta)
        
        # ── Profit Acceleration Compression Engine ─────────────────────────────
        # 1. Base Gamma Speed (ROI-based)
        _roi_pct = ((confirmed_close - ep) / ep * 100.0) if ep > 0 else 0.0
        if _roi_pct >= 150:
            _trail_speed = 2.5
            _gamma_tier = "TIER_3_150PLUS"
        elif _roi_pct >= 100:
            _trail_speed = 2.0
            _gamma_tier = "TIER_2_100_150"
        elif _roi_pct >= 50:
            _trail_speed = 1.5
            _gamma_tier = "TIER_1_50_100"
        else:
            _trail_speed = 1.0
            _gamma_tier = "TIER_0_0_50"
        
        # 2. Trend Efficiency Factor (Market Structure & Ranging Avoidance)
        if df is None:
            df = self._fetcher.fetch_option_candles(pos.symbol)
            
        trend_efficiency = 1.0
        _net_move = 0.0
        _path_length = 0.0
        if df is not None and not df.empty:
            # Filter to today's session only — overnight gaps distort efficiency ratio
            if isinstance(df.index, pd.DatetimeIndex):
                df_today_opt = df[df.index.tz_localize(None).normalize() == pd.Timestamp(get_ist_now().date())]
                recent = df_today_opt.tail(15) if len(df_today_opt) >= 2 else df.tail(15)
            else:
                recent = df.tail(15)  # fallback: no DatetimeIndex
            if len(recent) > 1:
                closes = recent["close"].values
                _net_move = abs(closes[-1] - closes[0])
                _path_length = sum(abs(closes[i] - closes[i-1]) for i in range(1, len(closes)))
                if _path_length > 0:
                    trend_efficiency = _net_move / _path_length
                    
        # Clamp efficiency between 0.50 and 1.0 to prevent dividing by zero or inflating the step
        trend_efficiency_factor = max(0.50, min(1.0, trend_efficiency))
        
        # Apply efficiency multiplier: ranging markets will lower the trail speed (looser trail)
        _trail_speed *= trend_efficiency_factor
        _trail_speed *= signal_trail_boost  # V2-A3: tighten when signal opposes
        
        # 3. Apply intelligence to raw step (Option B architecture)
        step_pts = max(_base_step_pts * cfg.trail.gamma_speed_step_floor, _base_step_pts / max(0.1, _trail_speed))
        
        # 4. Final Safety Limit Cap (Guarantees trail doesn't exceed 50% of entry premium)
        step_pts = min(step_pts, ep * 0.50)
        
        # ── Incremental PnL ──
        _unrealized_pnl_pts = confirmed_close - ep
        _unrealized_pnl_pct = (_unrealized_pnl_pts / ep * 100.0) if ep > 0 else 0.0
        _unrealized_pnl_abs = _unrealized_pnl_pts * pos.remaining_qty
        
        # ── Detailed Trail Logging ──
        inf(
            f"[TRAIL] {underlying} | ROI={_roi_pct:.1f}% ({_gamma_tier}) | "
            f"KER={trend_efficiency:.3f} (net={_net_move:.2f}/path={_path_length:.2f}) → "
            f"KER_factor={trend_efficiency_factor:.3f} | "
            f"Speed={_trail_speed:.2f}x | BaseStep={_base_step_pts:.2f} → "
            f"FinalStep={step_pts:.2f} | Cap={ep*0.50:.2f} | "
            f"UnrealPnL={_unrealized_pnl_pts:.2f}pts ({_unrealized_pnl_pct:.1f}%) ₹{_unrealized_pnl_abs:.0f} | "
            f"PeakClose={pos.trail_peak_close:.2f} | LTP={confirmed_close:.2f}"
        )
        
        # Trail activation and ratchet placement use confirmed periodic closes.
        _prev_sl = pos.sl
        if not pos.premium_trail_active:
            new_sl = confirmed_close - step_pts

            # Profit-lock ladder: guarantee minimum locked profit at activation
            # ATR skips the artificial floor on first activation — first SL stays
            # below BE so the position has room to breathe. The natural ratchet
            # (confirmed_close - step_pts) lifts SL above BE as premium grows.
            if cfg.trail.sl_method == "atr":
                _lock_floor = 0.0  # no floor — SL sits at confirmed_close - step_pts
            else:
                _target_gain = pos.tgt - ep
                if _target_gain > 0:
                    _peak_gain = (pos.trail_peak_close or ep) - ep
                    _pct_of_target = _peak_gain / _target_gain
                    if   _pct_of_target >= 1.0:  _lock_floor = ep + _target_gain * 0.50
                    elif _pct_of_target >= 0.75: _lock_floor = ep + _target_gain * 0.25
                    elif _pct_of_target >= 0.50: _lock_floor = ep + _target_gain * 0.10
                    else:                        _lock_floor = ep + _target_gain * cfg.trail.activation_lock_pct

                    # Profit-lock milestone log
                    _prev_pl_pct = self._last_pl_pct.get(pos.slot_id, 0.0)
                    if _pct_of_target >= 0.50 and _prev_pl_pct < 0.50:
                        _advance_stage(pos, LifecycleStage.PROFIT_LOCK)
                        inf(f"[PROFIT-LOCK] {underlying}: milestone 50% ({_lock_floor:.1f}) at peak_gain={_peak_gain:.1f}")
                    elif _pct_of_target >= 0.75 and _prev_pl_pct < 0.75:
                        _advance_stage(pos, LifecycleStage.PROFIT_LOCK)
                        inf(f"[PROFIT-LOCK] {underlying}: milestone 75% ({_lock_floor:.1f}) at peak_gain={_peak_gain:.1f}")
                    elif _pct_of_target >= 1.0 and _prev_pl_pct < 1.0:
                        inf(f"[PROFIT-LOCK] {underlying}: milestone 100%+ ({_lock_floor:.1f}) at peak_gain={_peak_gain:.1f}")
                        _advance_stage(pos, LifecycleStage.PROFIT_LOCK)
                    self._last_pl_pct[pos.slot_id] = _pct_of_target
                    new_sl = max(new_sl, _lock_floor)
                else:
                    new_sl = max(new_sl, ep)

            _min_improvement = confirmed_close * cfg.trail.atr_min_ratchet_improvement_pct / 100.0
            if new_sl > pos.sl + _min_improvement:
                _broker_ok = True
                if cfg.broker.broker_sl_orders and pos.sl_order_id and self.modify_callback:
                    _broker_ok = self.modify_callback(underlying, new_sl, pos.slot_id)
                if _broker_ok:
                    _advance_stage(pos, LifecycleStage.ACTIVATED)
                    pos.premium_trail_active = True
                    pos.premium_trail_peak = pos.trail_peak_close
                    pos.premium_trail_sl = new_sl
                    pos.trail_activation_sl = new_sl
                    pos.sl = new_sl
                    _lock_type = "breakeven" if _lock_floor >= ep else "none"
                    inf(f"[TRAIL-ACT] {underlying} {pos.symbol}: threshold={activate_pts:.1f}, premium={confirmed_close:.1f}, gain={move:.1f}")
                    inf(f"[TRAIL] Premium ACTIVATED {underlying}: peak {ltp:.2f} SL→{new_sl:.2f} (speed={_trail_speed:.1f}x)")
                    if _lock_floor >= ep:
                        _advance_stage(pos, LifecycleStage.LOCKED)
                        inf(f"[TRAIL-LOCK] {underlying}: sl={new_sl:.1f}, lock_type={_lock_type}")
                else:
                    inf(f"[TRAIL] Premium activation BLOCKED {underlying}: broker rejected new_sl={new_sl:.2f} — retrying next cycle")
            else:
                if new_sl <= pos.sl:
                    dbg(f"[TRAIL] {underlying}: new_sl={new_sl:.2f} <= current sl={pos.sl:.2f} — not yet beneficial, retry next cycle")
                else:
                    dbg(f"[TRAIL] {underlying}: new_sl={new_sl:.2f} improves sl={pos.sl:.2f} by {new_sl - pos.sl:.2f}pt "
                        f"but needs {_min_improvement:.2f}pt ({cfg.trail.atr_min_ratchet_improvement_pct:.1f}%) — margin not met")
        else:
            if is_new_confirmed_close_high:
                pos.premium_trail_peak = pos.trail_peak_close
                new_sl = confirmed_close - step_pts
                _min_improvement = confirmed_close * cfg.trail.atr_min_ratchet_improvement_pct / 100.0
                if new_sl > pos.sl + _min_improvement:
                    _broker_ok = True
                    if cfg.broker.broker_sl_orders and pos.sl_order_id and self.modify_callback:
                        _broker_ok = self.modify_callback(underlying, new_sl, pos.slot_id)
                    if _broker_ok:
                        _advance_stage(pos, LifecycleStage.RATCHETING)
                        pos.premium_trail_sl = new_sl
                        pos.sl = new_sl
                        inf(f"[TRAIL-RATCHET] {underlying} {pos.symbol}: {_prev_sl:.1f}->{new_sl:.1f}, step={step_pts:.1f}, method={cfg.trail.sl_method}")
                        inf(f"[TRAIL] Premium RATCHET {underlying}: peak {ltp:.2f} SL→{new_sl:.2f} (speed={_trail_speed:.1f}x)")
                    else:
                        inf(f"[TRAIL-BLOCKED] {underlying} {pos.symbol}: broker rejected new_sl={new_sl:.1f}, retrying next cycle")
                        inf(f"[TRAIL] Premium ratchet BLOCKED {underlying}: broker rejected new_sl={new_sl:.2f} — retrying next cycle")
                else:
                    if new_sl <= pos.sl:
                        inf(f"[TRAIL-BLOCKED] {underlying} {pos.symbol}: proposed={new_sl:.1f} <= current={pos.sl:.1f} — step too wide")
                        dbg(f"[TRAIL] {underlying}: new high (peak={pos.trail_peak_close:.2f}) but new_sl={new_sl:.2f} <= "
                            f"current sl={pos.sl:.2f} — step too wide for this move, no ratchet")
                    else:
                        inf(f"[TRAIL-BLOCKED] {underlying} {pos.symbol}: proposed={new_sl:.1f} improves current={pos.sl:.1f} by "
                            f"{new_sl - pos.sl:.2f}pt but needs {_min_improvement:.2f}pt "
                            f"({cfg.trail.atr_min_ratchet_improvement_pct:.1f}% of {confirmed_close:.1f}) — margin not met")

    def _process_spot_trail(self, underlying: str, pos: OptionPosition, spot_ltp: float, conv_adj: float, signal_trail_boost: float = 1.0) -> None:
        cfg = self._config
        reward_dist = pos.reward_dist
        
        activate_pts = reward_dist * (cfg.trail.activate_at_pct / 100.0) * conv_adj * pos.trail_act_mult
        # Hard ceiling: prevents activation requiring more pts than the TP window on expensive options
        if cfg.trail.activate_at_max_pts > 0:
            activate_pts = min(activate_pts, cfg.trail.activate_at_max_pts)

        if pos.option_type == "CE": move = spot_ltp - pos.spot_entry
        else: move = pos.spot_entry - spot_ltp

        if not pos.trail_active and move < activate_pts:
            return
            
        # Resolve step points
        current_delta = None
        df = None
        if cfg.trail.sl_method == "delta":
            greeks = self._fetcher._fetch_option_greeks_cached(underlying, pos.symbol)
            if greeks and "delta" in greeks:
                current_delta = greeks["delta"]
        elif cfg.trail.sl_method == "atr":
            df = self._fetcher.fetch_spot_candles(underlying)
            
        step_pts = self._get_step_pts(pos, reward_dist, df, current_delta)

        # Final Safety Limit Cap for Spot Mode (Option B architecture)
        step_pts = min(step_pts, reward_dist * 0.50)

        # V2-A3: tighten step when signal opposes
        step_pts = step_pts / max(1.0, signal_trail_boost)

        # Spot PnL equivalent (spot move vs entry)
        _spot_move_pts = move
        _spot_move_pct = (_spot_move_pts / pos.spot_entry * 100.0) if pos.spot_entry > 0 else 0.0
        _sl_spot_str = f"{pos.trail_sl_spot:.2f}" if pos.trail_sl_spot else "N/A"

        inf(
            f"[TRAIL] {underlying} SPOT | Move={_spot_move_pts:.2f}pts ({_spot_move_pct:.2f}%) | "
            f"ActivateReq={activate_pts:.2f} | Step={step_pts:.2f} | Cap={reward_dist*0.50:.2f} | "
            f"Peak={pos.trail_peak if pos.trail_peak else 'N/A'} | LTP={spot_ltp:.2f} | "
            f"SL_Spot={_sl_spot_str}"
        )

        if not pos.trail_active:
            # INITIAL_PROTECTED → ACTIVATED
            _advance_stage(pos, LifecycleStage.ACTIVATED)
            pos.trail_active = True
            pos.trail_peak = spot_ltp
            new_sl_spot = (spot_ltp - step_pts) if pos.option_type == "CE" else (spot_ltp + step_pts)
            pos.trail_sl_spot = new_sl_spot
            inf(f"[TRAIL] Spot ACTIVATED {underlying}: peak {spot_ltp:.2f}, SL spot → {new_sl_spot:.2f}")
        else:
            if pos.option_type == "CE":
                if pos.trail_peak is None or spot_ltp > pos.trail_peak:
                    pos.trail_peak = spot_ltp
                    new_sl_spot = spot_ltp - step_pts
                    if pos.trail_sl_spot is None or new_sl_spot > pos.trail_sl_spot:
                        pos.trail_sl_spot = new_sl_spot
                        inf(f"[TRAIL] Spot RATCHET {underlying}: peak {spot_ltp:.2f}, SL spot → {new_sl_spot:.2f}")
            else:
                if pos.trail_peak is None or spot_ltp < pos.trail_peak:
                    pos.trail_peak = spot_ltp
                    new_sl_spot = spot_ltp + step_pts
                    if pos.trail_sl_spot is None or new_sl_spot < pos.trail_sl_spot:
                        pos.trail_sl_spot = new_sl_spot
                        inf(f"[TRAIL] Spot RATCHET {underlying}: peak {spot_ltp:.2f}, SL spot → {new_sl_spot:.2f}")

    # ── Key Level Trail Helpers ──────────────────────────────────────────────
    def _get_key_levels(self, spot: float, underlying: str) -> list[float]:
        """Generate a symmetric strike ladder around spot using per-instrument spacing.

        Returns a sorted list of price levels (e.g. for NIFTY with spacing=50:
        [..., 24750, 24800, 24850, 24900, 24950, ...]).
        """
        cfg = self._config
        # Resolve spacing from config dict; fallback to 50 for unknown instruments
        spacing = cfg.trail.key_level_spacing.get(underlying, 50)
        if spacing <= 0:
            spacing = 50

        # Nearest level at or below spot (floor to spacing grid)
        floor_level = math.floor(spot / spacing) * spacing
        # Generate ~20 levels in each direction (enough for the session)
        levels = []
        for i in range(-20, 21):
            lvl = floor_level + i * spacing
            if lvl > 0:
                levels.append(lvl)
        levels.sort()
        return levels

    def _get_next_key_level(
        self,
        spot: float,
        direction: str,
        underlying: str,
        current_level: float | None,
    ) -> float | None:
        """Return the next structure level the spot must cross to trigger a trail ratchet.

        CE: next level ABOVE current_level (upward targets).
        PE: next level BELOW current_level (downward targets).
        If current_level is None, finds the nearest level on the correct side of spot.
        """
        levels = self._get_key_levels(spot, underlying)
        if not levels:
            return None

        if current_level is None:
            # First call: pick the nearest level on the favorable side of spot
            if direction == "CE":
                above = [l for l in levels if l > spot]
                return min(above) if above else None
            else:
                below = [l for l in levels if l < spot]
                return max(below) if below else None

        # Find the next level beyond current_level in the trade direction
        if direction == "CE":
            above = [l for l in levels if l > current_level]
            return min(above) if above else None
        else:
            below = [l for l in levels if l < current_level]
            return max(below) if below else None

    def _process_key_level_trail(
        self,
        underlying: str,
        pos: OptionPosition,
        spot_ltp: float,
        premium_ltp: float,
    ) -> None:
        """Structure-driven trailing SL based on key strike levels.

        Logic:
          1. When spot crosses the next structure level → lock in a portion of
             the premium move since the last level (capture_pct) or a fixed pts
             amount.
          2. After key_level_breakeven_after_levels completed levels, SL moves
             to entry cost (breakeven).
          3. SL ratchets UP for both CE and PE (long options profit from
             increasing premium). The one-way ratchet is: SL only moves higher,
             never lower. Spot levels move opposite directions (CE: up, PE: down)
             but premium-based SL always ratchets upward.

        Gap-jump handling: uses a while loop so multiple levels crossed in a
        single tick are all processed immediately.
        """
        cfg = self._config
        ep = pos.entry_premium

        # ── Diagnostic: data snapshot on every key_level trail call ─────────
        _roi_pct = ((premium_ltp - ep) / ep * 100.0) if ep > 0 else 0.0
        self._kl_tick_count[underlying] = self._kl_tick_count.get(underlying, 0) + 1
        _kl_cnt = self._kl_tick_count[underlying]
        if _kl_cnt <= 5 or _kl_cnt % 10 == 0:
            inf(
                f"[DATA-KL] {underlying} tick#{_kl_cnt}: "
                f"spot=₹{spot_ltp:.2f} premium=₹{premium_ltp:.2f} | "
                f"entry=₹{ep:.2f} ROI={_roi_pct:.1f}% | "
                f"SL=₹{pos.sl:.2f} initial=₹{pos.initial_sl:.2f} | "
                f"direction={pos.option_type} moneyness={pos.moneyness} | "
                f"kl_active={pos.kl_active} kl_next={pos.kl_next_level} "
                f"kl_completed={pos.kl_levels_completed} "
                f"kl_level_premium={pos.kl_level_premium if pos.kl_level_premium else 'N/A'}"
            )

        # ── Initialization on first tick ────────────────────────────────────
        if not pos.kl_active:
            # INITIAL_PROTECTED → ACTIVATED (allows further transitions)
            _advance_stage(pos, LifecycleStage.ACTIVATED)
            # ACTIVATED → KEY_LEVEL (structure-driven variant)
            _advance_stage(pos, LifecycleStage.KEY_LEVEL)
            pos.kl_active = True
            pos.kl_next_level = self._get_next_key_level(
                spot_ltp, pos.option_type, underlying, None
            )
            pos.kl_levels_completed = 0
            pos.kl_level_premium = premium_ltp
            inf(
                f"[TRAIL] KeyLevel INIT {underlying}: "
                f"next_level={pos.kl_next_level:.0f} | "
                f"premium={premium_ltp:.2f}"
            )
            return

        # ── Guard: no next level computed ───────────────────────────────────
        if pos.kl_next_level is None:
            return

        # ── Process all crossed levels in a loop (handles gap jumps) ────────
        # CE: spot rising crosses upward levels; PE: spot falling crosses downward levels.
        while pos.kl_next_level is not None:
            if pos.option_type == "CE" and spot_ltp < pos.kl_next_level:
                break
            elif pos.option_type == "PE" and spot_ltp > pos.kl_next_level:
                break

            # ── Level crossed — compute trail step ─────────────────────────
            pos.kl_levels_completed += 1
            # A7: structured key-level hit telemetry
            inf(f"[TRAIL-KL] {underlying}: level={pos.kl_next_level:.0f}, "
                f"completed={pos.kl_levels_completed}, premium={premium_ltp:.2f}")
            captured_range = premium_ltp - (pos.kl_level_premium or ep)

            if cfg.trail.key_level_trail_style == "capture_pct":
                trail_step = max(1.0, captured_range * (cfg.trail.key_level_capture_pct / 100.0))
            else:
                trail_step = max(1.0, cfg.trail.key_level_fixed_pts)

            # ── Breakeven after N completed levels ─────────────────────────
            if (
                cfg.trail.key_level_breakeven_after_levels > 0
                and pos.kl_levels_completed >= cfg.trail.key_level_breakeven_after_levels
                and not pos.breakeven_moved
                and ep > pos.sl
            ):
                _broker_ok = True
                if cfg.broker.broker_sl_orders and pos.sl_order_id and self.modify_callback:
                    _broker_ok = self.modify_callback(underlying, ep, pos.slot_id)
                if _broker_ok:
                    pos.sl = ep
                    pos.breakeven_moved = True
                    inf(
                        f"[TRAIL] KeyLevel BREAKEVEN {underlying}: "
                        f"SL → entry ₹{ep:.2f} after {pos.kl_levels_completed} level(s)"
                    )

            # ── Compute new SL from captured range ─────────────────────────
            new_sl = premium_ltp - trail_step
            # Invariant 1: never activate SL below entry cost
            new_sl = max(new_sl, ep)

            # One-directional ratchet (SL only moves UP for both CE and PE)
            if new_sl > pos.sl:
                _broker_ok = True
                if cfg.broker.broker_sl_orders and pos.sl_order_id and self.modify_callback:
                    _broker_ok = self.modify_callback(underlying, new_sl, pos.slot_id)
                if _broker_ok:
                    pos.sl = new_sl
                    pos.premium_trail_sl = new_sl
                    inf(
                        f"[TRAIL] KeyLevel RATCHET {underlying}: "
                        f"level_crossed={pos.kl_next_level:.0f} | "
                        f"captured={captured_range:.2f}pts → step={trail_step:.2f} | "
                        f"SL→₹{new_sl:.2f} | completed={pos.kl_levels_completed}"
                    )
            else:
                inf(
                    f"[TRAIL] KeyLevel CROSS {underlying}: "
                    f"level_crossed={pos.kl_next_level:.0f} | "
                    f"captured={captured_range:.2f}pts → step={trail_step:.2f} | "
                    f"SL unchanged ₹{pos.sl:.2f} (new_sl={new_sl:.2f} not higher)"
                )

            # ── Advance to next level ──────────────────────────────────────
            pos.kl_level_premium = premium_ltp
            pos.kl_next_level = self._get_next_key_level(
                spot_ltp, pos.option_type, underlying, pos.kl_next_level
            )

        # Log distance to next level (only when no level was crossed this tick)
        if pos.kl_next_level is not None:
            _move_to_level = abs(spot_ltp - pos.kl_next_level)
            inf(
                f"[TRAIL] KeyLevel {underlying}: "
                f"spot={spot_ltp:.0f} → next_level={pos.kl_next_level:.0f} "
                f"({_move_to_level:.0f}pts away) | "
                f"completed={pos.kl_levels_completed} | "
                f"SL={pos.sl:.2f} | premium={premium_ltp:.2f}"
            )


class StrikeSelector:
    """Selects the best entry strike using check_all_checkpoints criteria."""

    def __init__(self, fetcher: DataFetcher, cfg: BotConfig):
        self._fetcher = fetcher
        self._config  = cfg

    @staticmethod
    def simple_otm(
        chain_rows: list[dict],
        spot: float,
        option_type: str,
        otm_offset: int,
    ) -> dict | None:
        """Pick a slightly OTM strike that is `otm_offset` strikes away from ATM."""
        strikes = sorted(set(r["strike"] for r in chain_rows if "strike" in r))
        if not strikes:
            return None
        atm = min(strikes, key=lambda x: abs(x - spot))
        idx = strikes.index(atm)
        if option_type == "CE":
            target_idx = min(idx + otm_offset, len(strikes) - 1)
        else:
            target_idx = max(idx - otm_offset, 0)
        target_strike = strikes[target_idx]
        for row in chain_rows:
            if row.get("strike") == target_strike:
                if option_type in (row.get("option_type", ""), ""):
                    return row
        for row in chain_rows:
            if row.get("strike") == target_strike:
                return row
        return None

    def select_best(
        self,
        symbol: str,
        chain_rows: list[dict],
        spot: float,
        direction: str,
        iv_rank: float | None,
        signal_score: float = 50.0,
        gex_levels: dict[str, Any] | None = None,
    ) -> dict | None:
        """
        Conviction-driven strike selection.

        All selection parameters (delta target, delta weight, asym threshold)
        are derived from a single `conviction` scalar ∈ [0, 1] so that the
        entire function behaves as a self-consistent system:

            Low conviction  → conservative OTM strike, liquidity-weighted
            High conviction → near-ATM strike, delta-weighted

        Returns None if no qualifying strike found.
        """
        cfg = self._config

        # ── Guard: empty input ────────────────────────────────────────────────
        if not chain_rows or not spot:
            return None

        # ── Guard: IVR too high for buyer edge ────────────────────────────────
        if iv_rank is not None and iv_rank >= cfg.entry.iv_rank_max_entry:
            inf(f"[STRIKE] IVR {iv_rank:.1f}% >= max {cfg.entry.iv_rank_max_entry:.1f}% — buyer edge rejected")
            return None

        # ── Guard: insufficient signal conviction ─────────────────────────────
        abs_score = abs(signal_score)
        if abs_score < cfg.entry.min_score:
            inf(f"[STRIKE] Signal score {signal_score:.0f} < min {cfg.entry.min_score} — insufficient edge")
            return None

        # ── Conviction scalar ─────────────────────────────────────────────────
        # Maps [min_score, 100] → [0.0, 1.0] so STRIKE_DELTA_BASE is the actual
        # minimum delta at the weakest tradeable signal, not a theoretical floor
        # at score=0 which can never be reached after the min_score gate above.
        conviction = min(
            (abs_score - cfg.entry.min_score) / max(100.0 - cfg.entry.min_score, 1.0),
            1.0,
        )

        # ── Piecewise continuous delta target ─────────────────────────────────
        # 0 - 50 score   → STRIKE_DELTA_BASE(0.25) to STRIKE_DELTA_PIVOT(0.50)  (near-OTM → ATM)
        # 50 - 100 score → STRIKE_DELTA_PIVOT(0.50) to STRIKE_DELTA_MAX(0.70)   (ATM → mild ITM)
        if abs_score <= STRIKE_SCORE_PIVOT:
            # Map [min_score, SCORE_PIVOT] -> [BASE, PIVOT]
            score_range = max(STRIKE_SCORE_PIVOT - cfg.entry.min_score, 1.0)
            fraction = max(0.0, abs_score - cfg.entry.min_score) / score_range
            target_delta = STRIKE_DELTA_BASE + fraction * (STRIKE_DELTA_PIVOT - STRIKE_DELTA_BASE)
        else:
            # Map [SCORE_PIVOT, 100] -> [PIVOT, MAX]
            score_range = 100.0 - STRIKE_SCORE_PIVOT
            fraction = min((abs_score - STRIKE_SCORE_PIVOT) / score_range, 1.0)
            target_delta = STRIKE_DELTA_PIVOT + fraction * (STRIKE_DELTA_MAX - STRIKE_DELTA_PIVOT)
        target_delta_low  = max(0.01, target_delta - STRIKE_DELTA_BAND)
        target_delta_high = min(0.99, target_delta + STRIKE_DELTA_BAND)
        inf(
            f"[STRIKE] conviction={conviction:.2f} "
            f"target_delta={target_delta:.3f} "
            f"band=[{target_delta_low:.2f},{target_delta_high:.2f}]"
        )

        # ── Stage 1: Price-range filter ───────────────────────────────────────
        # Window scales from config; avoids hardcoding ±5%.
        lo = spot if direction == "CE" else spot * (1 - STRIKE_RANGE_PCT)
        hi = spot * (1 + STRIKE_RANGE_PCT) if direction == "CE" else spot
        oi_key  = "ce_oi"     if direction == "CE" else "pe_oi"
        vol_key = "ce_volume" if direction == "CE" else "pe_volume"
        opt_key = "ce_symbol" if direction == "CE" else "pe_symbol"

        # ── Stage 2: Liquidity filter ─────────────────────────────────────────
        candidates: list[dict] = []
        for row in chain_rows:
            strike = row.get("strike", 0)
            if not (lo <= strike <= hi):
                continue
            oi = float(row.get(oi_key, 0) or 0)
            if oi < cfg.entry.min_oi_filter:
                continue
            vol = float(row.get(vol_key, 0) or 0)
            if vol < cfg.entry.min_vol_filter:
                continue
            candidates.append(row)

        if not candidates:
            return None

        # ── Stage 3: Delta filter (optional — only when greeks available) ─────
        # Single-pass: fetch delta ONCE and annotate every candidate immediately.
        # The fallback path reads _abs_delta from the annotated list — zero re-fetches.
        delta_checked: list[dict] = []
        delta_available = False
        annotated: list[dict] = []
        for row in candidates:
            abs_delta = self._fetcher.fetch_option_delta(symbol, row.get(opt_key))
            gamma = self._fetcher.fetch_option_gamma(symbol, row.get(opt_key))
            row = dict(row)                         # copy — safe to annotate
            if abs_delta is not None:
                row["_abs_delta"] = abs_delta
                delta_available = True
                if target_delta_low <= abs_delta <= target_delta_high:
                    delta_checked.append(row)
            if gamma is not None:
                row["_gamma"] = gamma
            bid = float(row.get(f"{direction.lower()}_bid", 0) or 0)
            ask = float(row.get(f"{direction.lower()}_ask", 0) or 0)
            mid = (bid + ask) / 2 if (bid and ask) else 0.0
            row["_spread_pct"] = ((ask - bid) / mid * 100) if mid > 0 else None
            annotated.append(row)

        if delta_available:
            if not delta_checked:
                inf(
                    f"[STRIKE] No candidate delta in "
                    f"[{target_delta_low:.2f}, {target_delta_high:.2f}] "
                    f"— conviction={conviction:.2f}, relaxing to closest available"
                )
                # Fallback: nearest-delta candidate — reads cached _abs_delta (no re-fetch)
                best_fallback: dict | None = None
                best_gap = float("inf")
                for row in annotated:
                    ad = row.get("_abs_delta")
                    if ad is None:
                        continue
                    gap = abs(ad - target_delta)
                    if gap < best_gap:
                        best_gap = gap
                        best_fallback = row
                if best_fallback and best_gap <= MAX_DELTA_GAP:
                    candidates = [best_fallback]
                else:
                    # Gap too large — pathological fallback; bypass delta filter
                    if best_fallback:
                        inf(
                            f"[STRIKE] Fallback gap {best_gap:.2f} > MAX_DELTA_GAP {MAX_DELTA_GAP:.2f} "
                            f"— delta filter bypassed, using liquidity ranking only"
                        )
                    candidates = annotated
            else:
                candidates = delta_checked
        else:
            candidates = annotated  # delta unavailable: all liquidity candidates proceed (no silent skip)

        # ── Stage 4: Conviction-driven asymmetry scoring ──────────────────────
        # IV weight: lower IV = better buyer conditions.
        # IVR missing → do NOT penalize; skip IV component (set ivr_weight to 0).
        ivr_known: bool = iv_rank is not None
        iv_score_raw: float = (1 - (iv_rank or 0.0) / 100) if ivr_known else 0.0

        # Delta weight scales with conviction; liquidity gets the remainder.
        delta_weight = STRIKE_DELTA_WEIGHT_BASE + conviction * STRIKE_DELTA_WEIGHT_RANGE
        # Distribute remaining weight across IV, OI, Vol, Spread, GEX:
        #   with IVR:  4:3:2:1:1  (iv 36%, oi 27%, vol 18%, spread 9%, gex 9%)
        #   no  IVR:   6:4:2:1    (oi 46%, vol 31%, spread 15%, gex 8%)
        liq_total  = 1.0 - delta_weight
        if ivr_known:
            iv_w      = liq_total * (4/11)
            oi_w      = liq_total * (3/11)
            vol_w     = liq_total * (2/11)
            spread_w  = liq_total * (1/11)
            gex_w     = liq_total * (1/11)
        else:
            iv_w      = 0.0
            oi_w      = liq_total * (6/13)
            vol_w     = liq_total * (4/13)
            spread_w  = liq_total * (2/13)
            gex_w     = liq_total * (1/13)

        # Pre-compute chain-level maxima ONCE — O(n), not O(n²) per candidate.
        max_oi  = max(float(r.get(oi_key,  0) or 0) for r in chain_rows) or 1.0
        max_vol = max(float(r.get(vol_key, 0) or 0) for r in chain_rows) or 1.0
        max_spread_pct = cfg.entry.max_entry_spread_pct

        best_row: dict | None = None
        best_asym = -1.0

        for row in candidates:
            strike_oi  = float(row.get(oi_key,  0) or 0)
            strike_vol = float(row.get(vol_key, 0) or 0)
            # OI / Vol concentration normalized to best-in-chain strike
            oi_conc    = min(strike_oi / max_oi, 1.0)
            vol_conc   = min(strike_vol / max_vol, 1.0)

            abs_delta = row.get("_abs_delta")
            if abs_delta is not None:
                # smoother decay: half the band on each side
                delta_score = max(0.0, 1.0 - abs(abs_delta - target_delta) / max(2 * STRIKE_DELTA_BAND, 0.01))
            else:
                delta_score = 0.5  # neutral when no greeks

            spread_pct = row.get("_spread_pct")
            if spread_pct is not None and max_spread_pct > 0:
                spread_score = max(0.0, 1.0 - spread_pct / max_spread_pct)
            else:
                spread_score = 0.5

            premium = float(row.get(f"{direction.lower()}_ltp", 0) or 0)
            if premium > 0 and cfg.trail.activate_at_max_pts > 0:
                efficiency_ratio = cfg.trail.activate_at_max_pts / premium
                efficiency_score = max(0.0, min(1.0, 1.0 - efficiency_ratio))
            else:
                efficiency_score = 0.5

            strike = float(row.get("strike", 0) or 0)
            gamma_flip = (gex_levels or {}).get("gamma_flip")
            if gamma_flip is not None and strike > 0:
                dist = min(1.0, abs(strike - gamma_flip) / (gamma_flip * 0.005))
                favorable = (direction == "CE" and strike >= gamma_flip) or (direction == "PE" and strike <= gamma_flip)
                if favorable:
                    gex_score = 0.5 + 0.5 * dist   # 0.5 at flip, 1.0 at ≥0.5% away
                else:
                    gex_score = 0.5 * (1.0 - dist)  # 0.5 at flip, 0.0 at ≥0.5% away
            else:
                gex_score = 0.5

            iv_component = (iv_score_raw * iv_w) if ivr_known else 0.0
            asym_score = (
                iv_component
                + oi_conc        * oi_w
                + vol_conc       * vol_w
                + spread_score   * spread_w
                + gex_score      * gex_w
                + delta_score    * delta_weight
                + efficiency_score * 0.0
            )
            if asym_score > best_asym:
                best_asym = asym_score
                best_row  = row

        # ── Stage 5: Conviction-scaled minimum quality gate ───────────────────
        # Institutional logic: strong signal → more willing to execute on a
        # slightly imperfect strike.  Weak signal → insist on cleaner setup.
        # Scales between [threshold * 0.80, threshold * 1.00]:
        #   conviction=0.0 → min = threshold × 1.00  (strictest)
        #   conviction=1.0 → min = threshold × 0.80  (relaxed 20%)
        min_asym = cfg.entry.asym_score_threshold * (1.00 - conviction * 0.20)
        if best_asym < min_asym:
            inf(
                f"[STRIKE] Best asym {best_asym:.3f} < conviction-scaled min "
                f"{min_asym:.3f} (conviction={conviction:.2f}) — no qualifying strike"
            )
            return None
        return best_row


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 10 — RISK ENGINE                      RiskManager           ║
# ╚══════════════════════════════════════════════════════════════════════╝

class RiskManager:
    """Manages session-level risk: trade counts, loss streaks, entry cooldowns."""

    def __init__(self, client: api, cfg: BotConfig, state: BotState):
        self.client  = client
        self.config  = cfg
        self._state  = state

        self._session_date               = get_ist_now().strftime("%Y-%m-%d")
        self._session_trade_count        = 0
        self._session_consecutive_losses = 0
        self._session_consecutive_wins   = 0
        self._last_entry_times: dict[str, float] = {}
        self._daily_pnl                  = 0.0

        self._funds_cache:       float = 0.0   # last broker-reported available capital
        self._funds_cache_time:  float = 0.0
        self._funds_cache_ttl:   float = 60.0  # re-poll interval; between refreshes uses pnl delta
        self._pnl_at_last_fetch: float = 0.0
        self._pnl_history: deque[tuple[float, float]] = deque()  # (unix_timestamp, cumulative_pnl)

    def available_capital(self) -> float:
        """Cached funds() call: re-polls broker every _funds_cache_ttl seconds.
        Between refreshes returns cached broker capital + script P&L delta since last poll.
        """
        now = time.time()
        if self._funds_cache_time and (now - self._funds_cache_time) < self._funds_cache_ttl:
            delta_pnl = self._daily_pnl - self._pnl_at_last_fetch
            return max(0.0, self._funds_cache + delta_pnl)

        try:
            resp = self.client.funds()
            data = resp.get("data", {}) if isinstance(resp, dict) else {}
            for key in ("availablecash", "available_cash", "cash", "available_margin", "net"):
                value = data.get(key)
                if value is None:
                    continue
                capital = float(value)
                if capital > 0:
                    self._funds_cache       = capital
                    self._funds_cache_time  = now
                    self._pnl_at_last_fetch = self._daily_pnl
                    return capital
            inf(f"[FUNDS] available cash not found in funds() response: {resp}")
        except Exception as exc:
            err(f"[FUNDS] funds() fetch error", exc)
            if self._funds_cache_time:
                delta_pnl = self._daily_pnl - self._pnl_at_last_fetch
                return max(0.0, self._funds_cache + delta_pnl)
        return 0.0

    def _maybe_reset_daily_state(self):
        today = get_ist_now().strftime("%Y-%m-%d")
        with self._state.state_lock:
            if today != self._session_date:
                inf(f"[RISK] New trading day {today} — resetting session state")
                self._session_date               = today
                self._session_trade_count        = 0
                self._session_consecutive_losses = 0
                self._session_consecutive_wins   = 0
                self._daily_pnl                  = 0.0
                self._pnl_at_last_fetch          = 0.0
                self._last_entry_times.clear()
                self._state.reset_market_caches()
                self._state.reset_strike_loss_pts()
                self._pnl_history.clear()

    def check_entry_gates(self, symbol: str = "") -> tuple[bool, str]:
        """Tier 1 + Tier 2: Full gate check before placing an entry order."""
        self._maybe_reset_daily_state()
        cfg = self.config
        daily_pnl = self.daily_pnl  # Read BEFORE state_lock (daily_pnl calls _maybe_reset which acquires state_lock)
        with self._state.state_lock:
            trade_count        = self._session_trade_count
            consecutive_losses = self._session_consecutive_losses
            last_entry_time    = self._last_entry_times.get(symbol)
            entry_in_flight    = self._state.entry_in_flight.get(symbol, 0)
            # F64: snapshot drawdown-rate state under lock — record_exit() mutates
            # _pnl_history under this same lock reachable cross-thread via place_exit()
            drawdown_ok = True
            window_pnl_change = 0.0
            if cfg.risk.drawdown_rate_enabled and cfg.risk.drawdown_rate_max_loss > 0 and len(self._pnl_history) >= 2:
                window_pnl_change = self._daily_pnl - self._pnl_history[0][1]
                drawdown_ok = window_pnl_change > -cfg.risk.drawdown_rate_max_loss

        if entry_in_flight > 0:
            return False, f"Entry already in flight for {symbol} ({entry_in_flight})"
        if cfg.risk.max_trades_per_session > 0 and trade_count >= cfg.risk.max_trades_per_session:
            return False, (
                f"Max trades/session reached ({trade_count}/{cfg.risk.max_trades_per_session})"
            )
        if cfg.risk.max_consecutive_losses > 0 and consecutive_losses >= cfg.risk.max_consecutive_losses:
            return False, (
                f"Loss streak limit reached ({consecutive_losses} consecutive losses)"
            )
        if cfg.risk.entry_cooldown_secs > 0 and symbol:
            if last_entry_time is not None:
                elapsed = time.monotonic() - last_entry_time
                if elapsed < cfg.risk.entry_cooldown_secs:
                    remaining = int(cfg.risk.entry_cooldown_secs - elapsed)
                    return False, f"Entry cooldown active for {symbol} ({remaining}s remaining)"
        # ── Timing gate: no new entries after configured time (IST) ──────────
        # get_ist_now() is TZ-safe: returns IST regardless of Docker/UTC host.
        _now_ist = get_ist_now()
        if cfg.risk.max_daily_loss_pct > 0:
            capital = self.available_capital()
            max_loss_amt = capital * (cfg.risk.max_daily_loss_pct / 100.0)
            if daily_pnl <= -max_loss_amt:
                return False, (
                    f"Daily loss limit hit ({cfg.risk.max_daily_loss_pct}% = "
                    f"₹{max_loss_amt:.0f}) | current P&L ₹{daily_pnl:.0f}"
                )
        if cfg.risk.max_daily_loss_amount > 0 and daily_pnl <= -cfg.risk.max_daily_loss_amount:
            return False, (
                f"Daily loss limit hit (₹{cfg.risk.max_daily_loss_amount:.0f}) "
                f"| current P&L ₹{daily_pnl:.0f}"
            )
        if not drawdown_ok:
            return False, (
                f"Drawdown rate limit: ₹{abs(window_pnl_change):.0f} lost in last "
                f"{cfg.risk.drawdown_rate_window_mins}m (limit ₹{cfg.risk.drawdown_rate_max_loss:.0f})"
            )
        if cfg.risk.max_daily_profit_amount > 0 and daily_pnl >= cfg.risk.max_daily_profit_amount:
            return False, (
                f"Daily profit target reached ₹{daily_pnl:.0f} "
                f"(target ₹{cfg.risk.max_daily_profit_amount:.0f}) — locking in gains for the day"
            )
        if cfg.market.no_new_trade_after:
            now_hm = _now_ist.strftime("%H:%M")
            if now_hm >= cfg.market.no_new_trade_after:
                return False, (
                    f"No new entries after {cfg.market.no_new_trade_after} IST "
                    f"(current {now_hm}) — waiting for EOD"
                )
        return True, ""

    def record_entry(self, symbol: str):
        """Call after a confirmed entry fill."""
        with self._state.state_lock:
            self._session_trade_count += 1
            self._last_entry_times[symbol] = time.monotonic()

    def record_exit(self, pnl: float):
        """Call after a confirmed exit fill. Updates daily P&L and loss streak."""
        with self._state.state_lock:
            self._daily_pnl += pnl
            now_ts = time.time()
            self._pnl_history.append((now_ts, self._daily_pnl))
            cutoff = now_ts - (self.config.risk.drawdown_rate_window_mins * 60)
            while self._pnl_history and self._pnl_history[0][0] < cutoff:
                self._pnl_history.popleft()
            if pnl < 0:
                self._session_consecutive_losses += 1
                self._session_consecutive_wins = 0
                inf(f"[RISK] Loss streak: {self._session_consecutive_losses} | "
                      f"Daily P&L ₹{self._daily_pnl:.0f}")
            else:
                self._session_consecutive_losses = 0
                self._session_consecutive_wins += 1

    def effective_lot_multiplier(self, base_multiplier: int) -> int:
        """Adaptive lot sizing (U9). Disabled by default for safety."""
        cfg = self.config
        if not cfg.entry.adaptive_sizing_enabled:
            return max(1, base_multiplier)
        bonus = (
            self._session_consecutive_wins // cfg.entry.adaptive_win_streak_trigger
        ) * cfg.entry.adaptive_win_streak_step
        return max(1, min(base_multiplier + bonus, cfg.entry.adaptive_max_lot_mult))

    @property
    def consecutive_wins(self) -> int:
        return self._session_consecutive_wins

    @property
    def daily_pnl(self) -> float:
        self._maybe_reset_daily_state()
        return self._daily_pnl

    @property
    def halted(self) -> bool:
        """Convenience property — True when check_entry_gates() would block new entries."""
        allowed, _ = self.check_entry_gates()
        return not allowed


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 11 — EXECUTION             WebSocketManager +               ║
# ║                                     OrderManager                     ║
# ║                                     JournalWriter / TradeAnalytics   ║
# ╚══════════════════════════════════════════════════════════════════════╝

class WebSocketManager:
    """
    Manages the WebSocket connection and per-tick breach detection (SL/target hits).
    Trailing SL ratchets are computed by TrailSLEngine on the strategy thread.
    Callbacks for exit and broker SL modification are wired after construction
    to avoid circular dependency with OrderManager.
    """

    def __init__(self, client: api, cfg: BotConfig, state: BotState):
        self.client = client
        self.config = cfg
        self._state = state
        self._exit_callback:      Callable[[str, str, str | None], None] | None = None
        self._notify_callback:    Callable[[str, int], None] | None = None   # U-G: wired after init
        self._fetcher:            DataFetcher | None = None  # Set via set_fetcher() after construction
        self._ws_started     = threading.Event()
        self._ws_stop_event  = threading.Event()   # Signals _ws_thread to shut down gracefully
        self._ws_thread_ref: threading.Thread | None = None  # Track thread to prevent duplicates
        self._desired: set[tuple[str, str]] = set()   # Instruments we WANT subscribed (desired state)
        self._actual:  set[tuple[str, str]] = set()   # Instruments SDK has confirmed subscribed (actual state)
        self._subscribe_lock  = threading.Lock()
        self._last_tick_time: float = 0.0                   # updated on every valid tick; used by watchdog
        self._ws_stale_alerted: bool = False                # U-G: rate-limit 30s WARNING log to once per stale window
        self._delta_cache: OrderedDict[str, tuple[float, float]] = OrderedDict()
        self._delta_cache_max_size: int = 200  # Prevent unbounded growth
        self._delta_fetch_inflight: set[str] = set()
        self._delta_fetch_limit: int = 100
        self._delta_lock = threading.Lock()
        # Thread pool to limit concurrent delta fetches (avoid spawning unlimited daemon threads)
        self._delta_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="delta-pool")
        self._exit_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix="exit-pool")
        self._ws_connected: bool = False  # True only while SDK reports a live, authenticated connection
        self._reconnect_count: int = 0
        self._reconcile_cycles: int = 0
        self._repaired_subscriptions: int = 0
        self._ws_start_time: float = time.time()
        self._telemetry_last_log_time: float = 0.0
        self._raw_cb_count: int = 0
        self._tick_counts: dict[str, int] = {}
        self._spot_tick_counts: dict[str, int] = {}
        self._order_event_queue: queue.Queue[dict] = queue.Queue()

    def set_fetcher(self, fetcher: DataFetcher) -> None:
        """Set DataFetcher reference to consolidate greeks API calls."""
        self._fetcher = fetcher

    def set_notify_callback(self, cb: Callable[[str, int], None]) -> None:
        """Wire the orchestrator's Telegram notify function into the WS watchdog (U-G)."""
        self._notify_callback = cb

    def is_connected(self) -> bool:
        """Returns True when the WebSocket is live and authenticated. Used by scan_underlying() entry guard."""
        return self._ws_connected

    # ── Order-update stream (account-level push subscription) ─────────────────
    def _on_order_event(self, data: dict) -> None:
        """Callback for subscribe_orders — fires on SDK thread. Enqueue only."""
        try:
            self._order_event_queue.put_nowait(data)
        except queue.Full:
            err("[ORDER-STREAM] Event queue full — dropping event", None)

    def drain_order_events(self) -> list[dict]:
        """Called once per strategy-thread cycle. Never blocks."""
        events = []
        while True:
            try:
                events.append(self._order_event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def _get_cached_delta(self, underlying: str, option_symbol: str, ttl: float = 30.0) -> float | None:
        """Return cached |delta| and refresh asynchronously when stale."""
        with self._delta_lock:
            cached = self._delta_cache.get(option_symbol)
            if cached and (time.time() - cached[1]) < ttl:
                return cached[0]
            if option_symbol not in self._delta_fetch_inflight:
                if len(self._delta_fetch_inflight) < self._delta_fetch_limit:
                    self._delta_fetch_inflight.add(option_symbol)
                    # Use thread pool instead of unlimited daemon spawn
                    # Pass fetcher to reuse cached greeks instead of duplicate API call
                    self._delta_executor.submit(self._fetch_and_cache_delta, underlying, option_symbol, self._fetcher)
                else:
                    inf(f"[WS] Delta fetch suppressed because {len(self._delta_fetch_inflight)} requests are pending")
            return cached[0] if cached else None

    def _fetch_and_cache_delta(self, underlying: str, option_symbol: str, fetcher: DataFetcher | None = None) -> None:
        """Reuse DataFetcher's cached greeks instead of duplicate optiongreeks API call."""
        try:
            if fetcher is None:
                # Fallback: direct API call if fetcher unavailable (should not happen in normal flow)
                ul_exch = (
                    self.config.market.index_exchange
                    if underlying in self.config.market.index_underlyings
                    else self.config.market.spot_exchange
                )
                resp = self.client.optiongreeks(
                    symbol=option_symbol,
                    exchange=self.config.market.fno_exchange,
                    underlying_symbol=underlying,
                    underlying_exchange=ul_exch,
                )
                if resp and resp.get("status") == "success":
                    delta = resp.get("greeks", {}).get("delta")
                    if delta is not None:
                        with self._delta_lock:
                            while len(self._delta_cache) >= self._delta_cache_max_size:
                                self._delta_cache.popitem(last=False)
                            self._delta_cache[option_symbol] = (abs(float(delta)), time.time())
            else:
                # Use DataFetcher's cached greeks (consolidates API calls)
                greeks = fetcher._fetch_option_greeks_cached(underlying, option_symbol)
                if greeks and greeks.get("delta") is not None:
                    with self._delta_lock:
                        while len(self._delta_cache) >= self._delta_cache_max_size:
                            self._delta_cache.popitem(last=False)
                        self._delta_cache[option_symbol] = (abs(float(greeks["delta"])), time.time())
        except Exception:
            pass
        finally:
            with self._delta_lock:
                self._delta_fetch_inflight.discard(option_symbol)

    def set_exit_callback(self, cb: Callable[[str, str, str | None], None]) -> None:
        self._exit_callback = cb

    def start(self) -> None:
        if self._ws_thread_ref and self._ws_thread_ref.is_alive():
            inf("[WS] Thread already running — skipping duplicate start")
            return
        self._ws_stop_event.clear()
        t = threading.Thread(target=self._ws_thread, name="ws-thread", daemon=True)
        self._ws_thread_ref = t
        t.start()
        self._ws_started.wait(timeout=10)

    def subscribe(self, exchange: str, symbol: str) -> None:
        with self._subscribe_lock:
            self._desired.add((exchange, symbol))
            try:
                self.client.subscribe_ltp(
                    [{"exchange": exchange, "symbol": symbol}],
                    on_data_received=self._on_ws_data,
                )
                self._actual.add((exchange, symbol))
                inf(f"[WS] Subscribed option {exchange}:{symbol}")
            except Exception as exc: err(f"[WS] Subscribe error {exchange}:{symbol}: ", exc)

    def subscribe_spot(self, symbol: str) -> None:
        exch = self.config.market.index_exchange if symbol in self.config.market.index_underlyings else self.config.market.spot_exchange
        with self._subscribe_lock:
            self._desired.add((exch, symbol))
            try:
                self.client.subscribe_ltp(
                    [{"exchange": exch, "symbol": symbol}],
                    on_data_received=self._on_ws_data,
                )
                self._actual.add((exch, symbol))
                inf(f"[WS] Subscribed spot {exch}:{symbol}")
            except Exception as exc: err(f"[WS] Subscribe spot error {symbol}: ", exc)

    def unsubscribe(self, exchange: str, symbol: str) -> None:
        with self._subscribe_lock:
            self._desired.discard((exchange, symbol))
            try:
                self.client.unsubscribe_ltp([{"exchange": exchange, "symbol": symbol}])
                self._actual.discard((exchange, symbol))
            except Exception as exc:
                self._actual.discard((exchange, symbol))
                err(f"[WS] Unsubscribe error {exchange}:{symbol}", exc)

    def unsubscribe_spot(self, symbol: str) -> None:
        exch = self.config.market.index_exchange if symbol in self.config.market.index_underlyings else self.config.market.spot_exchange
        with self._subscribe_lock:
            self._desired.discard((exch, symbol))
            try:
                self.client.unsubscribe_ltp([{"exchange": exch, "symbol": symbol}])
                self._actual.discard((exch, symbol))
            except Exception as exc:
                self._actual.discard((exch, symbol))
                err(f"[WS] Unsubscribe spot error {symbol}", exc)

    def _on_ws_data(self, data: dict) -> None:
        """
        Handles every tick.  Two independent paths:
          Part A — option premium trail (premium trail SL)
          Part B — spot trail (spot-based SL ratchet for indices)
        """
        # ── RAW CALLBACK DIAGNOSTIC — fires on EVERY WS message ────────────
        self._raw_cb_count += 1
        _raw_cnt = self._raw_cb_count
        if _raw_cnt <= 5 or _raw_cnt % 50 == 0:
            _dtype = type(data).__name__
            _keys = list(data.keys()) if isinstance(data, dict) else "N/A"
            _inner = data.get("data") if isinstance(data, dict) else None
            _inner_keys = list(_inner.keys()) if isinstance(_inner, dict) else type(_inner).__name__ if _inner else "None"
            dbg(f"[WS-RAW] cb#{_raw_cnt}: type={_dtype} keys={_keys} | "
                f"inner_type={type(data.get('data')).__name__ if isinstance(data, dict) else 'N/A'} "
                f"inner_keys={_inner_keys}"
            )
        # ── END RAW DIAGNOSTIC ─────────────────────────────────────────────

        if not isinstance(data, dict):
            return
            
        # OpenAlgo SDK encapsulates actual market data inside a nested 'data' dictionary.
        # Fallback to root level just in case.
        inner_data = data.get("data") if isinstance(data.get("data"), dict) else data
        
        symbol = inner_data.get("symbol") or data.get("symbol", "")
        ltp    = inner_data.get("ltp") or data.get("ltp")
        
        if ltp is None:
            return
        try:
            ltp = float(ltp)
        except (TypeError, ValueError):
            return

        self._last_tick_time = time.time()    # feed heartbeat for watchdog
        with self._state.state_lock:
            self._state.ltp_map[symbol] = ltp

        # ── Feed SnapshotCache on every tick for active positions ──────────
        for underlying, pos in list(self._state.positions.all_items()):
            if pos.exit_pending:
                continue
            if pos.symbol == symbol:
                # Option premium tick → update per-symbol snapshot
                self._state.snapshot_cache.set_option_symbol(underlying, symbol)
                self._state.snapshot_cache.update(symbol, option_ltp=ltp)
            elif pos.spot_symbol == symbol:
                # Spot tick → update per-symbol snapshot + rolling spot buffer
                self._state.snapshot_cache.update(underlying, spot_ltp=ltp)
                self._state.record_spot_price(underlying, ltp)

        # ── Diagnostic: log ticks for active position symbols ───────────────
        for underlying, pos in list(self._state.positions.all_items()):
            if pos.exit_pending:
                continue
            if pos.symbol == symbol:
                self._tick_counts[symbol] = self._tick_counts.get(symbol, 0) + 1
                cnt = self._tick_counts[symbol]
                # Log every 5th tick to avoid flooding, plus first tick
                if cnt <= 3 or cnt % 5 == 0:
                    spot_snap = self._state.snapshot_cache.get(underlying)
                    spot_ltp = spot_snap.spot_ltp if spot_snap else None
                    dbg(
                        f"[WS-TICK] {underlying} option={symbol} "
                        f"premium=₹{ltp:.2f} spot={spot_ltp if spot_ltp else 'N/A'} | "
                        f"tick#{cnt} SL=₹{pos.sl:.2f} TGT=₹{pos.tgt:.2f} | "
                        f"kl_active={pos.kl_active} kl_next={pos.kl_next_level}"
                    )
            elif pos.spot_symbol == symbol:
                self._spot_tick_counts[underlying] = self._spot_tick_counts.get(underlying, 0) + 1
                cnt = self._spot_tick_counts[underlying]
                if cnt <= 3 or cnt % 5 == 0:
                    opt_snap = self._state.snapshot_cache.get(underlying)
                    opt_ltp = opt_snap.option_ltp if opt_snap else None
                    dbg(
                        f"[WS-TICK] {underlying} spot={symbol} "
                        f"spot_ltp=₹{ltp:.2f} premium={opt_ltp if opt_ltp else 'N/A'} | "
                        f"spot_tick#{cnt} | "
                        f"kl_active={pos.kl_active} kl_next={pos.kl_next_level}"
                    )

        # ── Part A: Premium Trail (option LTP → trail SL) ──────────────────
        for underlying, pos in list(self._state.positions.all_items()):
            if pos.exit_pending or pos.symbol != symbol:
                continue
            self._check_premium_trail(underlying, pos, ltp)

        # ── Part B: Spot Trail (underlying LTP → spot SL ratchet) ──────────
        for underlying, pos in list(self._state.positions.all_items()):
            if pos.exit_pending or pos.spot_symbol != symbol:
                continue
            self._check_spot_trail(underlying, pos, ltp)

    def _check_premium_trail(self, underlying: str, pos: OptionPosition, ltp: float) -> None:
        cfg = self.config
        if cfg.entry.delta_exit_threshold > 0 and not pos.exit_pending:
            live_delta = self._get_cached_delta(underlying, pos.symbol)
            if live_delta is not None and live_delta < cfg.entry.delta_exit_threshold:
                inf(
                    f"[WS] DEEP OTM EXIT {underlying}: delta {live_delta:.3f} "
                    f"< threshold {cfg.entry.delta_exit_threshold:.3f}"
                )
                self._trigger_exit(underlying, f"DeepOTM_delta_{live_delta:.3f}", pos=pos)
                return
        # Read SL/TGT under state_lock to avoid racing trail engine (HR-3)
        with self._state.state_lock:
            _sl = pos.sl
            _tgt = pos.tgt
        if ltp <= _sl:
            inf(f"[WS] PREMIUM SL HIT {underlying}: LTP {ltp:.2f} <= SL {_sl:.2f}")
            self._trigger_exit(underlying, "premium_sl_hit", pos=pos)
            return
        if ltp >= _tgt:
            inf(f"[WS] PREMIUM TARGET HIT {underlying}: LTP {ltp:.2f} >= TGT {_tgt:.2f}")
            self._trigger_exit(underlying, "premium_target_hit", pos=pos)
            return

    def _check_spot_trail(self, underlying: str, pos: OptionPosition, spot_ltp: float) -> None:
        with self._state.state_lock:
            _sl_spot = pos.trail_sl_spot
        if _sl_spot is not None:
            if pos.option_type == "CE" and spot_ltp <= _sl_spot:
                inf(f"[WS] SPOT TRAIL SL HIT {underlying}: spot {spot_ltp:.2f} <= trail_sl_spot {_sl_spot:.2f}")
                self._trigger_exit(underlying, "spot_trail_sl_hit", pos=pos)
            elif pos.option_type == "PE" and spot_ltp >= _sl_spot:
                inf(f"[WS] SPOT TRAIL SL HIT {underlying}: spot {spot_ltp:.2f} >= trail_sl_spot {pos.trail_sl_spot:.2f}")
                self._trigger_exit(underlying, "spot_trail_sl_hit", pos=pos)

    def _trigger_exit(self, underlying: str, reason: str,
                      pos: OptionPosition | None = None) -> None:
        normalized_reason = ExitReason.normalize(reason)
        with self._state.state_lock:
            if not pos or pos.exit_pending:
                return
            pos.exit_pending = True
            with self._state.exit_lock:
                if pos.slot_id in self._state.exit_queue:
                    return
                self._state.exit_queue.add(pos.slot_id)
        if self._exit_callback:
            self._exit_executor.submit(self._exit_callback, underlying, normalized_reason, pos.slot_id)

    def _ws_thread(self) -> None:
        inf("[WS] WebSocket thread starting...")
        _os = "ENABLED" if self.config.broker.order_stream_enabled else "disabled"
        _osc = "+auto-complete" if self.config.broker.order_stream_complete_entries else ""
        _up = "platform-ready" if self.config.broker.order_updates_enabled else "no-platform-support"
        dbg(f"[ORDER-STREAM] WS-thread config: order_stream={_os}{_osc} ({_up})")
        self._ws_started.set()
        ws_url = self.config.broker.ws_url or "(SDK default)"
        backoff_secs = 5
        max_backoff_secs = 300  # 5 minutes max backoff
        consecutive_failures = 0
        max_consecutive_failures = 36  # ~3 hours of retries before circuit break
        is_first_connect = True
        while True:
            if self._ws_stop_event.is_set():
                inf("[WS] Stop event received — exiting WS thread")
                try:
                    self.client.disconnect()
                except Exception as _disc_exc:
                    err("[WS] Stop-path disconnect error", _disc_exc)
                break
            try:
                # Persistent single-client architecture — SDK-aligned.
                # Per OpenAlgo SDK docs: one client instance, one connect(), many subscriptions.
                # Re-instantiating api() on every attempt spawns new internal SDK threads
                # without cleaning up the old ones, exhausting the OS thread limit.
                # Fix: reuse self.client (constructed once in BuyerEdgeStrategy.__init__);
                # disconnect() the previous transport before reconnecting.
                inf(f"[WS] Connecting... (active OS threads: {threading.active_count()})")
                try:
                    self.client.disconnect()   # Release previous transport threads
                except Exception as _disc_exc:
                    err("[WS] Reconnect-path disconnect error", _disc_exc)
                with self._subscribe_lock:
                    self._actual.clear()
                time.sleep(0.5)               # Brief pause: allow SDK thread teardown

                ok = self.client.connect()
                _actual_url = getattr(self.client, 'ws_url', ws_url)
                inf(f"[WS] Client connects using {_actual_url} (expected {ws_url})")
                if ok:
                    if not is_first_connect:
                        self._reconnect_count += 1
                    is_first_connect = False
                    self._ws_connected = True
                    inf(f"[WS] Connected to {_actual_url} — SDK managing reconnects automatically")
                    backoff_secs = 5  # Reset backoff on successful connect
                    consecutive_failures = 0
                    # ── Diff-based subscription reconciliation ──────────────────────────────
                    # Reconcile desired vs actual rather than a full replay.
                    # Avoids redundant SDK subscribe calls for already-active instruments.
                    with self._subscribe_lock:
                        to_add    = self._desired - self._actual
                        to_remove = self._actual  - self._desired  # stale cleanup (edge case)
                    if to_add or to_remove:
                        inf(f"[WS] Reconciling: +{len(to_add)} subscribe / -{len(to_remove)} unsubscribe")
                    for (exch, sym) in to_remove:
                        try:
                            self.client.unsubscribe_ltp([{"exchange": exch, "symbol": sym}])
                            with self._subscribe_lock:
                                self._actual.discard((exch, sym))
                        except Exception as _un_exc: err(f"[WS] Reconcile unsubscribe error {exch}:{sym}: ", _un_exc)
                    for (exch, sym) in to_add:
                        with self._subscribe_lock:
                            if (exch, sym) not in self._desired:
                                continue
                        try:
                            self.client.subscribe_ltp(
                                [{"exchange": exch, "symbol": sym}],
                                on_data_received=self._on_ws_data,
                            )
                            with self._subscribe_lock:
                                if (exch, sym) in self._desired:
                                    self._actual.add((exch, sym))
                        except Exception as _re_exc: err(f"[WS] Reconcile subscribe error {exch}:{sym}: ", _re_exc)

                    # ── Order-update stream (account-level, one subscription covers everything) ──
                    if self.config.broker.order_updates_enabled and self.config.broker.order_stream_enabled:
                        inf("[ORDER-STREAM] Attempting to subscribe to account-level order updates via subscribe_orders()...")
                        try:
                            sent = self.client.subscribe_orders(on_order_update=self._on_order_event)
                            if sent:
                                inf("[ORDER-STREAM] Subscribed to account-level order updates — broker push events will be processed")
                            else:
                                err("[ORDER-STREAM] subscribe_orders() returned False — platform does not advertise 'orders' in supported_features. "
                                    "Continuing on polling only.", None)
                        except Exception as _os_exc:
                            err("[ORDER-STREAM] subscribe_orders() raised exception — continuing on polling only", _os_exc)
                    else:
                        dbg("[ORDER-STREAM] order_stream_enabled=False — subscribe_orders() skipped. "
                            "All order-status updates via REST polling.")

                    while True:  # watchdog: graduated alerts then force-reconnect if feed silent
                        if self._ws_stop_event.wait(timeout=30):
                            inf("[WS] Stop event received during watchdog — exiting")
                            try:
                                self.client.disconnect()
                            except Exception as _disc_exc:
                                err("[WS] Watchdog stop-path disconnect error", _disc_exc)
                            return
                        elapsed = time.time() - self._last_tick_time
                        hm = int(get_ist_now().strftime("%H%M"))
                        in_market = self._last_tick_time and MARKET_HOURS_START <= hm <= MARKET_HOURS_END
                        with self._subscribe_lock:
                            has_subs = len(self._desired) > 0
                        if in_market and has_subs and elapsed > 30 and not self._ws_stale_alerted:
                            inf(f"[WS] WARNING: Stale tick feed — no ticks in {int(elapsed)}s (market hours active, {len(self._desired)} subs)")
                            self._ws_stale_alerted = True
                        if in_market and has_subs and elapsed > 120:
                            _msg = f"⚠️ WS Feed STALE: No ticks for {int(elapsed)}s during market hours. Forcing reconnect — check broker/VPS connectivity."
                            if self._notify_callback:
                                self._notify_callback(_msg, 9)
                            inf(f"[WS] Feed silent {int(elapsed)}s — forcing hard reconnect...")
                            self._ws_stale_alerted = False   # reset for next connection window
                            try:
                                self.client.disconnect()
                            except Exception as _disc_exc:
                                err("[WS] Watchdog force-reconnect disconnect error", _disc_exc)
                            break   # exit watchdog → outer loop reconnects immediately
                        if not in_market or not has_subs:
                            self._ws_stale_alerted = False   # reset outside market hours or when no subs

                        # ── Fix B5: Periodic Reconcile Check ──
                        # If a mid-batch subscribe fails, it won't be in _actual. Retry here.
                        with self._subscribe_lock:
                            missing = self._desired - self._actual
                        if missing:
                            self._reconcile_cycles += 1
                            self._repaired_subscriptions += len(missing)
                            inf(f"[WS] Watchdog: Found {len(missing)} missing subscriptions. Attempting to reconcile...")
                            for (exch, sym) in missing:
                                with self._subscribe_lock:
                                    if (exch, sym) not in self._desired:
                                        continue
                                try:
                                    self.client.subscribe_ltp(
                                        [{"exchange": exch, "symbol": sym}],
                                        on_data_received=self._on_ws_data,
                                    )
                                    with self._subscribe_lock:
                                        if (exch, sym) in self._desired:
                                            self._actual.add((exch, sym))
                                except Exception as _re_exc: err(f"[WS] Watchdog subscribe error {exch}:{sym}: ", _re_exc)

                        # ── Telemetry Logging ──
                        now_ts = time.time()
                        if now_ts - self._telemetry_last_log_time >= 300:
                            self._telemetry_last_log_time = now_ts
                            with self._subscribe_lock:
                                d_len = len(self._desired)
                                a_len = len(self._actual)
                            uptime_mins = (now_ts - self._ws_start_time) / 60.0
                            last_tick_sec = (now_ts - self._last_tick_time) if self._last_tick_time else 0.0
                            dbg(f"[WS-HEALTH] Uptime: {uptime_mins:.1f}m | Threads: {threading.active_count()} | "
                                f"Subs: {d_len}/{a_len} | Reconnects: {self._reconnect_count} | "
                                f"Reconciles: {self._reconcile_cycles} (Repaired: {self._repaired_subscriptions}) | "
                                f"LastTick: {last_tick_sec:.1f}s"
                            )

                    continue        # skip backoff sleep — reconnect without delay
                consecutive_failures += 1
                self._ws_connected = False
                inf(f"[WS] Connection failed, Verify [WEBSOCKET_URL={self.config.broker.ws_url}, API Key: {self.config.broker.api_key[-6:]}], attempt {consecutive_failures}/{max_consecutive_failures}")
            except Exception as exc:
                _emsg = str(exc)
                consecutive_failures += 1
                self._ws_connected = False
                err(f"[WS] Connection error: {exc}. Attempt {consecutive_failures}/{max_consecutive_failures}", exc)
                if "Invalid API key" in _emsg or "AUTHENTICATION_ERROR" in _emsg:
                    inf("[WS] HINT: Check OPENALGO_API_KEY — copy the key from OpenAlgo dashboard \u2192 API Key page")
                elif "InvalidStatus" in type(exc).__name__ or "HTTP 200" in _emsg:
                    inf("[WS] HINT: Reverse proxy (/ws) not routing to port 8765 — fix Caddyfile or use ws://127.0.0.1:8765")
            # Circuit breaker: if persistent failures, give up to prevent memory accumulation
            if consecutive_failures >= max_consecutive_failures:
                inf(f"[WS] Circuit breaker triggered: {consecutive_failures} consecutive failures. Giving up.")
                inf("[WS] Check broker connectivity, credentials, and reverse proxy configuration.")
                if self._notify_callback:
                    try:
                        self._notify_callback(
                            f"🚨 WS Circuit Breaker: {consecutive_failures} consecutive failures. "
                            f"WebSocket monitoring STOPPED. Only broker SL-M protecting positions.",
                            9,
                        )
                    except Exception:
                        pass
                return  # Exit thread to prevent infinite retry accumulation
            # Exponential backoff (5s → 7.5s → 11.25s ... → 300s max)
            current_backoff = min(backoff_secs, max_backoff_secs)
            inf(f"[WS] Retrying in {current_backoff:.0f}s...")
            time.sleep(current_backoff)
            backoff_secs = min(backoff_secs * 1.5, max_backoff_secs)

    def stop(self) -> None:
        """Shut down thread pool executors and signal WS thread to stop."""
        self._ws_stop_event.set()
        try:
            self.client.disconnect()
        except Exception as _disc_exc:
            err("[WS] stop() disconnect error", _disc_exc)
        if self._ws_thread_ref and self._ws_thread_ref.is_alive():
            self._ws_thread_ref.join(timeout=5)
        self._delta_executor.shutdown(wait=False)
        self._exit_executor.shutdown(wait=False)


class OrderManager:
    """
    Places and manages all orders via the OpenAlgo SDK.
    Depends on WebSocketManager (for subscribe/unsubscribe) and RiskManager.
    notify(message, priority) sends Telegram alerts.
    """

    def __init__(
        self,
        client:  api,
        cfg:  BotConfig,
        state:   BotState,
        risk:    "RiskManager",
        ws:      WebSocketManager,
        fetcher: "DataFetcher",
        notify:  Callable[[str, int], None],
    ):
        self.client = client
        self.config = cfg
        self._state = state
        self._risk  = risk
        self._ws    = ws
        self._fetcher = fetcher
        self._notify = notify
        self._journal = JournalWriter(self.config.journal.trade_journal_path)
        self._pending_tranche_exits: dict[str, str] = {}  # key=f"{underlying}_{tr.tranche_id}" → order_id
        self._pending_tranche_exits_lock: threading.Lock = threading.Lock()

    def _cancel_three_outcome(self, order_id: str, pending: PendingEntry | None = None) -> str:
        """Cancel order_id and determine terminal disposition.
        
        Returns one of three outcomes:
          'cancelled'    — terminal fail status, filled_qty == 0; caller should remove pending entry
          'reconciled'   — terminal fill status, filled_qty > 0, usable price; entry already registered
          'still_open'   — status open/unknown or no usable fill price; caller should retry/alert
        Always calls orderstatus even when cancelorder errors (the error may mean order filled in race).
        """
        try:
            self.client.cancelorder(order_id=order_id, strategy=self.config.broker.strategy_name)
        except Exception as exc:
            err(f"[ORDER] Cancel-error {order_id}: ", exc)
        try:
            confirm = self.client.orderstatus(order_id=order_id, strategy=self.config.broker.strategy_name)
            if isinstance(confirm, dict):
                data = confirm.get("data") or confirm
                bs = str(data.get("order_status", "")).lower()
                ep = float(data.get("average_price", 0) or data.get("price", 0) or 0)
                fq_raw = int(data.get("filled_quantity", 0) or data.get("filled_qty", 0) or 0)
                # F76: REST API never populates filled_quantity/filled_qty for 27+/32+ brokers.
                # Use fq_raw as primary signal, fall back to pending.qty when absent.
                if bs in ("complete", "filled", "executed") and ep > 0:
                    if pending:
                        use_qty = fq_raw if fq_raw > 0 else pending.qty
                        self._risk.record_entry(pending.underlying)
                        self.register_filled_entry(
                            pending.underlying, pending.symbol, use_qty,
                            pending.spot, pending.direction, ep,
                            sl_pts=pending.sl_pts, entry_delta=pending.entry_delta,
                            entry_conviction=pending.entry_conviction,
                            entry_sl_source=pending.entry_sl_source,
                        )
                        inf(f"[ORDER] Cancel-race {order_id}: reconciled {use_qty} @ \u20b9{ep:.2f}")
                    return "reconciled"
                if bs in ("cancelled", "canceled", "rejected") and fq_raw == 0:
                    inf(f"[ORDER] Cancel confirmed for {order_id}: {bs}")
                    return "cancelled"
                if bs in ("cancelled", "canceled", "rejected") and ep > 0:
                    if pending:
                        use_qty = fq_raw if fq_raw > 0 else pending.qty
                        self._risk.record_entry(pending.underlying)
                        self.register_filled_entry(
                            pending.underlying, pending.symbol, use_qty,
                            pending.spot, pending.direction, ep,
                            sl_pts=pending.sl_pts, entry_delta=pending.entry_delta,
                            entry_conviction=pending.entry_conviction,
                            entry_sl_source=pending.entry_sl_source,
                        )
                        inf(f"[ORDER] Cancel-race {order_id}: partial {use_qty} @ \u20b9{ep:.2f} — reconciled")
                    return "reconciled"
                inf(f"[ORDER] Cancel-confirm status {bs} for {order_id}: fq_raw={fq_raw} ep={ep}")
        except Exception as exc:
            err(f"[ORDER] Cancel-confirm error {order_id}: ", exc)
        return "still_open"

    def apply_confirmed_partial_exit(
        self,
        pos: "OptionPosition",
        tranche: "Tranche",
        filled_qty: int,
        price: float,
        reason: str | ExitReason,
        underlying: str,
        opt_sym: str,
    ) -> None:
        """Record a confirmed partial exit for one tranche.
        
        Journals the filled slice as a partial-exit row, records risk P&L and
        strike loss, decrements BOTH tranche.qty and pos.core.qty, marks the
        tranche exited only when its residual hits zero, and cancels/reissues
        protection using the new remaining quantity.
        """
        if filled_qty <= 0 or price <= 0:
            return
        filled_qty = min(filled_qty, tranche.qty)
        # Build a temporary Tranche for the filled slice (journal only, not persisted)
        filled_slice = Tranche(
            tranche_id=f"{tranche.tranche_id}:partial",
            qty=filled_qty,
            sl=tranche.sl,
            initial_sl=tranche.initial_sl,
            is_runner=tranche.is_runner,
            tp_pts=tranche.tp_pts,
            is_exit_placed=True,
            exit_price=price,
            exit_reason=reason.value if isinstance(reason, ExitReason) else str(reason),
        )
        tr_pnl = _calc_pnl(pos, price, qty=filled_qty)
        self._risk.record_exit(tr_pnl)
        _pts_loss = max(0.0, pos.entry_premium - price)
        self._state.record_strike_loss(opt_sym, pos.option_type, _pts_loss)
        tr_exit_record = TradeAnalytics.build_tranche(
            underlying=underlying, pos=pos, tr=filled_slice,
            paper_trade=self.config.broker.paper_trade,
        )
        self._journal.write(tr_exit_record)
        # Decrement both the tranche and the position-level total
        tranche.qty = max(0, tranche.qty - filled_qty)
        pos.core.qty = max(0, pos.core.qty - filled_qty)
        if tranche.qty <= 0:
            tranche.is_exit_placed = True
        else:
            tranche.sl_order_id = None
            tranche.tgt_order_id = None
            # NOT clearing pos.sl_order_id / pos.tgt_order_id here:
            # they belong to the runner tranche; this call processes a
            # non-runner (guarded by caller) but the else branch fires
            # when residual remains — clearing the runner's IDs would
            # cause duplicate reissue on the next verify pass.
        inf(
            f"[PARTIAL] {underlying} {opt_sym}: filled {filled_qty} @ \u20b9{price:.2f} "
            f"P&L \u20b9{tr_pnl:.0f} | residual {tranche.qty}"
        )

    def _raw_order_status(self, order_id: str) -> dict | None:
        """One-shot orderstatus call. Returns the full response dict (data layer)
        for any status — including rejected/cancelled. Returns None on error."""
        try:
            resp = self.client.orderstatus(order_id=order_id, strategy=self.config.broker.strategy_name)
            if isinstance(resp, dict) and resp.get("status") == "success":
                data = resp.get("data") or resp
                if isinstance(data, dict) and data.get("order_status"):
                    return data
        except Exception as exc:
            err(f"[ORDER] status error {order_id}: ", exc)
        return None

    def poll_order_status(
        self,
        order_id: str,
        max_retries: int | None = None,
        sleep_secs: float | None = None,
    ) -> dict | None:
        cfg = self.config
        max_r = max_retries if max_retries is not None else cfg.broker.order_status_max_retries
        slp   = sleep_secs  if sleep_secs  is not None else cfg.broker.order_poll_interval
        _TERMINAL_FILL    = ("complete", "filled", "executed")
        _TERMINAL_FAIL    = ("rejected", "cancelled")
        for attempt in range(max_r):
            try:
                resp = self.client.orderstatus(order_id=order_id, strategy=cfg.broker.strategy_name)
                if not resp:
                    time.sleep(slp)
                    continue
                if not isinstance(resp, dict):
                    time.sleep(slp)
                    continue
                api_status = resp.get("status", "").lower()
                if api_status not in ("success",):
                    time.sleep(slp)
                    continue
                data         = resp.get("data") or resp
                order_status = str(data.get("order_status", "")).lower()
                if order_status in _TERMINAL_FILL:
                    return resp
                if order_status in _TERMINAL_FAIL:
                    inf(f"[ORDER] Order {order_id} {order_status}")
                    return None
                # ORD-2: detect partial fill near end of retry window
                filled_qty = int(data.get("filled_quantity", 0) or data.get("filled_qty", 0) or 0)
                if filled_qty > 0 and attempt >= int(max_r * 0.8):
                    inf(
                        f"[ORDER] Partial fill detected: {filled_qty} units "
                        f"for {order_id} (attempt {attempt+1}/{max_r}) — treating as fill"
                    )
                    return resp
            except Exception as exc: err(f"[ORDER] orderstatus error (attempt {attempt+1}): ", exc)
            time.sleep(slp)
        inf(f"[ORDER] Timed out polling order {order_id} after {max_r} attempts")
        return None

    def _finalize_exit(
        self,
        underlying: str,
        pos: "OptionPosition",
        executed_price: float,
        pnl: float,
        reason: str | ExitReason,
        exit_price_source: str = "broker_fill",
        opt_symbol: str | None = None,
        pop_pending_exit: bool = False,
    ) -> None:
        """Shared exit-finalize sequence used by all full-exit sites.

        Records PnL, writes journal, unsubscribes WS (with has_siblings guard),
        transitions lifecycle to CLOSED (fixes 3 sites that were missing it),
        emits TRAIL-EXIT telemetry (fixes 2 sites missing it), and cleans up
        state/exit locks.

        Parameters
        ----------
        opt_symbol : str or None
            Override for WS unsubscribe symbol (defaults to pos.symbol).
            Used by pending-exit paths that bind opt_sym = pos.symbol before
            the state-lock cleanup.
        pop_pending_exit : bool
            Also pop from pending_exits under the state lock (pending-exit paths).
        """
        opt_sym = opt_symbol or pos.symbol
        self._risk.record_exit(pnl)
        _pts_loss = max(0.0, pos.entry_premium - executed_price)
        self._state.record_strike_loss(opt_sym, pos.option_type, _pts_loss)
        reason_str = reason.value if isinstance(reason, ExitReason) else str(reason)
        self._write_journal(underlying, pos, executed_price, pnl, reason_str,
                            exit_price_source=exit_price_source)
        self._ws.unsubscribe(self.config.market.fno_exchange, opt_sym)
        if not self._state.positions.has_siblings(pos.slot_id):
            self._ws.unsubscribe_spot(pos.spot_symbol)
        _advance_stage(pos, LifecycleStage.CLOSED)
        inf(f"[TRAIL-EXIT] {underlying} {pos.symbol}: reason={reason_str}, final_sl={pos.sl:.1f}, peak={pos.trail_peak_close or 0:.1f}")
        with self._state.state_lock:
            self._state.positions.pop(pos.slot_id, None)
            self._state.pending_opposite_exit.discard(underlying)
            if pop_pending_exit:
                self._state.pending_exits.pop(pos.slot_id, None)
        with self._state.exit_lock:
            self._state.exit_queue.discard(pos.slot_id)

    def _resolve_option_ltp(self, underlying: str, symbol: str) -> float | None:
        """Resolve option LTP from snapshot cache, falling back to ltp_map.
        Used by all 5 option-price resolution sites — eliminates the identical
        3-line snap + fallback pattern."""
        snap = self._state.snapshot_cache.get(underlying)
        return (snap.option_ltp if snap and snap.option_ltp is not None
                else self._state.ltp_map.get(symbol))

    def _cancel_tranche_orders(self, underlying: str, pos: OptionPosition) -> dict:
        """Cancel outstanding orders for all open tranches. Returns dict of filled orders."""
        broker_filled: dict = {}
        for tr in pos.open_tranches:
            for attr_name in ("sl_order_id", "tgt_order_id"):
                oid = getattr(tr, attr_name, None)
                if not oid:
                    continue
                try:
                    resp = self.client.orderstatus(
                        order_id=oid, strategy=self.config.broker.strategy_name
                    )
                    if isinstance(resp, dict) and resp.get("status") == "success":
                        data = resp.get("data") or resp
                        broker_stat = str(data.get("order_status", "")).lower()
                        if broker_stat in ("complete", "filled", "executed"):
                            broker_filled[f"{tr.tranche_id}_{attr_name}"] = {
                                "order_id": oid,
                                "executed": float(data.get("average_price", 0) or 0),
                                "order_status": broker_stat,
                                "tranche_id": tr.tranche_id,
                            }
                            inf(f"[ORDER] Broker {attr_name} already filled for {underlying} t={tr.tranche_id}: {oid}")
                except Exception as exc:
                    err(f"[ORDER] pre-check fill error {oid}: ", exc)

            for attr_name in ("sl_order_id", "tgt_order_id"):
                oid = getattr(tr, attr_name, None)
                key = f"{tr.tranche_id}_{attr_name}"
                if not oid or key in broker_filled:
                    continue
                try:
                    resp = self.client.cancelorder(
                        order_id=oid, strategy=self.config.broker.strategy_name
                    )
                    if isinstance(resp, dict) and resp.get("status") in ("success", "cancelled"):
                        inf(f"[ORDER] Cancelled broker {attr_name} {oid} for {underlying} t={tr.tranche_id}")
                    else:
                        inf(f"[ORDER] Cancel resp for {oid}: {resp}")
                except Exception as exc:
                    err(f"[ORDER] Cancel error {oid}: ", exc)

            for attr_name in ("sl_order_id", "tgt_order_id"):
                oid = getattr(tr, attr_name, None)
                if not oid:
                    continue
                try:
                    resp = self.client.orderstatus(
                        order_id=oid, strategy=self.config.broker.strategy_name
                    )
                    if isinstance(resp, dict) and resp.get("status") == "success":
                        data = resp.get("data") or resp
                        broker_stat = str(data.get("order_status", "")).lower()
                        inf(f"[ORDER] Post-cancel status {oid}: {broker_stat}")
                except Exception as exc:
                    err(f"[ORDER] Post-cancel check error {oid}: ", exc)
                setattr(tr, attr_name, None)
        pos.sl_order_id = None  # F62: clear flat alias — per-tranche loop clears tr.sl_order_id, but pos.sl_order_id (direct broker field, not a property delegation) would remain stale for multi-tranche positions that survived restart
        return broker_filled

    def cancel_broker_orders(self, underlying: str, slot_id: str | None = None) -> dict:
        """Cancel outstanding broker SL-M + LIMIT target orders for an underlying."""
        pos = self._state.positions.slot(slot_id) if slot_id else self._state.positions.get_one(underlying)
        if not pos:
            return {}
        is_multi = len(pos.tranches) > 1
        if is_multi:
            return self._cancel_tranche_orders(underlying, pos)

        broker_filled: dict = {}
        sl_id  = pos.sl_order_id
        tgt_id = pos.tgt_order_id

        for attr_name, oid in (("sl_order_id", sl_id), ("tgt_order_id", tgt_id)):
            if not oid:
                continue
            try:
                resp = self.client.orderstatus(order_id=oid, strategy=self.config.broker.strategy_name)
                if isinstance(resp, dict) and resp.get("status") == "success":
                    data = resp.get("data") or resp
                    broker_stat = str(data.get("order_status", "")).lower()
                    if broker_stat in ("complete", "filled", "executed"):
                        broker_filled[attr_name] = {
                            "order_id":    oid,
                            "executed":    float(data.get("average_price", 0) or 0),
                            "order_status": broker_stat,
                        }
                        inf(f"[ORDER] Broker {attr_name} already filled: {oid}")
            except Exception as exc: err(f"[ORDER] pre-check fill error {oid}: ", exc)

        for attr_name, oid in (("sl_order_id", sl_id), ("tgt_order_id", tgt_id)):
            if not oid or attr_name in broker_filled:
                continue
            try:
                resp = self.client.cancelorder(order_id=oid, strategy=self.config.broker.strategy_name)
                if isinstance(resp, dict) and resp.get("status") in ("success", "cancelled"):
                    inf(f"[ORDER] Cancelled broker {attr_name} {oid}")
                else:
                    inf(f"[ORDER] Cancel resp for {oid}: {resp}")
            except Exception as exc: err(f"[ORDER] Cancel error {oid}: ", exc)

        for attr_name, oid in (("sl_order_id", sl_id), ("tgt_order_id", tgt_id)):
            if not oid:
                continue
            try:
                resp = self.client.orderstatus(order_id=oid, strategy=self.config.broker.strategy_name)
                if isinstance(resp, dict) and resp.get("status") == "success":
                    data = resp.get("data") or resp
                    broker_stat = str(data.get("order_status", "")).lower()
                    inf(f"[ORDER] Post-cancel status {oid}: {broker_stat}")
            except Exception as exc: err(f"[ORDER] Post-cancel check error {oid}: ", exc)
        pos.sl_order_id  = None
        pos.tgt_order_id = None
        pos.broker_protection = False
        return broker_filled

    def modify_broker_sl(self, underlying: str, new_trigger: float, slot_id: str | None = None) -> bool:
        """Modify broker SL-M trigger price. Returns True if the broker accepted the change."""
        if self.config.broker.paper_trade:
            return False  # no-op in paper trade mode
        pos = self._state.positions.slot(slot_id) if slot_id else self._state.positions.get_one(underlying)
        if not pos or not pos.sl_order_id:
            return False
        # ORD-4: pre-check if broker SL already filled before sending modifyorder
        try:
            pre = self.client.orderstatus(
                order_id=pos.sl_order_id, strategy=self.config.broker.strategy_name
            )
            if isinstance(pre, dict) and pre.get("status") == "success":
                _data = pre.get("data") or pre
                if str(_data.get("order_status", "")).lower() in ("complete", "filled", "executed"):
                    inf(f"[ORDER] SL already filled for {underlying} — skipping modify, triggering exit")
                    self.place_exit(underlying, "broker_sl_filled_on_modify", slot_id=pos.slot_id)
                    return False
        except Exception as _pre_exc: err(f"[ORDER] modify_broker_sl pre-check error for {underlying}: ", _pre_exc)
        try:
            resp = self.client.modifyorder(
                order_id=pos.sl_order_id,
                strategy=self.config.broker.strategy_name,
                symbol=pos.symbol,
                exchange=self.config.market.fno_exchange,
                action="SELL",
                quantity=pos.remaining_qty,
                price_type="SL-M",
                product="MIS",
                price=0,
                trigger_price=new_trigger,
            )
            if isinstance(resp, dict) and resp.get("status") == "success":
                inf(f"[ORDER] Broker SL modified for {underlying} → trigger ₹{new_trigger:.2f}")
                return True
            else:
                inf(f"[ORDER] modifyorder resp for {underlying}: {resp}")
                # TOCTOU guard: modify may have failed because SL filled in the
                # window between pre-check and modifyorder. Re-query immediately.
                try:
                    post = self.client.orderstatus(
                        order_id=pos.sl_order_id, strategy=self.config.broker.strategy_name
                    )
                    if isinstance(post, dict) and post.get("status") == "success":
                        _post_data = post.get("data") or post
                        if str(_post_data.get("order_status", "")).lower() in ("complete", "filled", "executed"):
                            inf(f"[ORDER] SL filled in modify window for {underlying} — triggering exit")
                            self.place_exit(underlying, "broker_sl_filled_on_modify", slot_id=pos.slot_id)
                except Exception:
                    pass
                return False
        except Exception as exc:
            err(f"[ORDER] modify_broker_sl error for {underlying}", exc)
            # TOCTOU guard: same immediate status check on exception
            try:
                post = self.client.orderstatus(
                    order_id=pos.sl_order_id, strategy=self.config.broker.strategy_name
                )
                if isinstance(post, dict) and post.get("status") == "success":
                    _post_data = post.get("data") or post
                    if str(_post_data.get("order_status", "")).lower() in ("complete", "filled", "executed"):
                        inf(f"[ORDER] SL filled in modify window (exc) for {underlying} — triggering exit")
                        self.place_exit(underlying, "broker_sl_filled_on_modify", slot_id=pos.slot_id)
            except Exception:
                pass
            return False

    def _handle_broker_order_fill(
        self,
        underlying: str,
        pos: OptionPosition,
        attr_name: str,
        oid: str,
        raw_reason: str,
        executed_price: float,
        tr: Tranche | None = None,
    ) -> None:
        """Handle a filled broker order (SL or TGT) for a position or tranche."""
        reason = ExitReason.normalize(raw_reason)
        is_multi = len(pos.tranches) > 1

        if is_multi and tr and not tr.is_runner:
            if tr.is_exit_placed:
                return
            # Partial exit: non-runner tranche filled — mark exited, cancel opposite
            tr.is_exit_placed = True
            tr.exit_price = executed_price
            tr.exit_reason = reason
            other_oid = tr.tgt_order_id if attr_name == "sl_order_id" else tr.sl_order_id
            other_name = "tgt_order_id" if attr_name == "sl_order_id" else "sl_order_id"
            if other_oid:
                try:
                    self.client.cancelorder(order_id=other_oid, strategy=self.config.broker.strategy_name)
                except Exception as c_exc:
                    err(f"[ORDER] Cancel {other_name} error for {underlying} t={tr.tranche_id}: ", c_exc)
                finally:
                    setattr(tr, other_name, None)
            pnl = _calc_pnl(pos, executed_price, qty=tr.qty) if executed_price > 0 else 0.0
            inf(
                f"[ORDER] Partial exit {underlying} t={tr.tranche_id}: "
                f"₹{executed_price:.2f} × {tr.qty} | P&L ₹{pnl:.0f} | "
                f"remaining_qty={pos.remaining_qty}"
            )
            self._risk.record_exit(pnl)
            _pts_loss = max(0.0, pos.entry_premium - executed_price)
            self._state.record_strike_loss(pos.symbol, pos.option_type, _pts_loss)
            tranche_record = TradeAnalytics.build_tranche(
                underlying=underlying, pos=pos, tr=tr,
                paper_trade=self.config.broker.paper_trade,
            )
            self._journal.write(tranche_record)
            return

        # Full exit (single-tranche or runner tranche)
        if attr_name == "tgt_order_id" and (pos.premium_trail_active or pos.kl_active or pos.trail_active):
            inf(f"[TARGET] {underlying}: target filled while trail active "
                f"(stage={pos.trail.stage.value if hasattr(pos.trail, 'stage') else 'N/A'}, "
                f"trail_peak={pos.trail_peak_close:.2f})")

        _advance_stage(pos, LifecycleStage.EXIT_PENDING)
        with self._state.state_lock:
            if pos.exit_pending:
                return
            pos.exit_pending = True
            with self._state.exit_lock:
                self._state.exit_queue.add(pos.slot_id)
        inf(f"[ORDER] Broker {attr_name} filled for {underlying} ({oid})")

        # Cancel opposite leg
        other_oid = pos.tgt_order_id if attr_name == "sl_order_id" else pos.sl_order_id
        other_name = "tgt_order_id" if attr_name == "sl_order_id" else "sl_order_id"
        if other_oid:
            try:
                inf(f"[ORDER] Cancelling opposite broker order {other_name} ({other_oid})...")
                self.client.cancelorder(order_id=other_oid, strategy=self.config.broker.strategy_name)
            except Exception as c_exc: err(f"[ORDER] Cancel opposite broker order error {other_name} ({other_oid}): ", c_exc)

        if executed_price > 0:
            qty = tr.qty if (is_multi and tr) else None
            pnl = _calc_pnl(pos, executed_price, qty=qty)
        else:
            pnl = 0.0
        direction_emoji = "🔺 UP" if pos.option_type.upper() == "CE" else "🔻 DN"
        emoji = "✅ PROFIT" if pnl >= 0 else "❌ LOSS"
        risk_pts = max(0.01, pos.entry_premium - pos.initial_sl)
        risk_qty = tr.qty if (is_multi and tr) else pos.remaining_qty
        risk_amt = risk_pts * risk_qty
        r_multiple = pnl / risk_amt if risk_amt > 0 else 0.0
        hold_mins = max(0, int((get_ist_now() - pos.entry_time).total_seconds() / 60))
        self._notify(
            f"{emoji} EXIT: {underlying}\n"
            f"📌 {reason.upper()}\n"
            f"{direction_emoji} {pos.symbol}\n"
            f"🚪 ₹{pos.entry_premium:.2f} → ₹{executed_price:.2f}\n"
            f"💰 P&L: ₹{pnl:.0f} ({r_multiple:+.2f}R)\n"
            f"⏱ Hold: {hold_mins}m | Daily: ₹{self._risk.daily_pnl:.0f}",
            2,
        )
        self._finalize_exit(underlying, pos, executed_price, pnl, reason,
                            exit_price_source="broker_fill")

    def check_broker_order_fills(self) -> None:
        """Periodic poll: if broker SL or target order was filled, trigger exit."""
        for underlying, pos in list(self._state.positions.all_items()):
            if pos.exit_pending:
                continue
            is_multi = len(pos.tranches) > 1
            # ── Check tranche-level orders (multi-tranche mode) ──────────────
            if is_multi:
                for tr in pos.open_tranches:
                    for attr_name, raw_reason in (
                        ("sl_order_id",  "broker_sl_filled"),
                        ("tgt_order_id", "broker_target_filled"),
                    ):
                        oid = getattr(tr, attr_name, None)
                        if not oid:
                            continue
                        try:
                            resp = self.client.orderstatus(order_id=oid, strategy=self.config.broker.strategy_name)
                            if not isinstance(resp, dict) or resp.get("status") != "success":
                                continue
                            data = resp.get("data") or resp
                            broker_stat = str(data.get("order_status", "")).lower()
                            if broker_stat in ("complete", "filled", "executed"):
                                executed_price = float(data.get("average_price", 0) or 0)
                                self._handle_broker_order_fill(
                                    underlying, pos, attr_name, oid, raw_reason,
                                    executed_price, tr=tr,
                                )
                        except Exception as exc:
                            err(f"[ORDER] check_broker_order_fills error ({underlying} t={tr.tranche_id}, {oid}): ", exc)
            # ── Check position-level orders (single-tranche mode only) ──
            # In multi-tranche mode, all orders are checked at the tranche level above.
            if is_multi:
                continue
            for attr_name, raw_reason in (
                ("sl_order_id",  "broker_sl_filled"),
                ("tgt_order_id", "broker_target_filled"),
            ):
                oid = getattr(pos, attr_name, None)
                if not oid:
                    continue
                try:
                    resp = self.client.orderstatus(order_id=oid, strategy=self.config.broker.strategy_name)
                    if not isinstance(resp, dict) or resp.get("status") != "success":
                        continue
                    data = resp.get("data") or resp
                    broker_stat = str(data.get("order_status", "")).lower()
                    if broker_stat in ("complete", "filled", "executed"):
                        executed_price = float(data.get("average_price", 0) or 0)
                        self._handle_broker_order_fill(
                            underlying, pos, attr_name, oid, raw_reason, executed_price,
                        )
                except Exception as exc: err(f"[ORDER] check_broker_order_fills error ({underlying}, {oid}): ", exc)

    def verify_sl_orders_active(self) -> None:
        """Periodic verification that broker SL/LIMIT orders are still open.
        Detects externally cancelled orders and re-issues them.
        Handles both single-tranche (position-level) and multi-tranche modes.
        """
        if self.config.broker.paper_trade:
            return
        for underlying, pos in list(self._state.positions.all_items()):
            if pos.exit_pending:
                continue
            is_multi = len(pos.tranches) > 1
            if not is_multi:
                # ── Single-tranche: verify SL + LIMIT at position level ────
                if not pos.sl_order_id:
                    err(f"[ORDER] SL MISSING (never placed) for {underlying} — re-issuing")
                    self._place_protection_orders_sequential(
                        underlying, pos, pos.symbol, pos.qty, pos.sl, pos.tgt
                    )
                    continue
                self._verify_one_order(underlying, pos, "sl_order_id", "SL")
                if pos.tgt_order_id:
                    self._verify_one_order(underlying, pos, "tgt_order_id", "LIMIT")
            else:
                # ── Multi-tranche: verify each tranche's orders ────────────
                for tr in pos.open_tranches:
                    if tr.qty <= 0:
                        continue
                    if tr.is_runner and not tr.sl_order_id:
                        err(f"[ORDER] SL MISSING (never placed) for {underlying} t={tr.tranche_id} — re-issuing")
                        self._place_protection_orders_sequential(
                            underlying, pos, pos.symbol, pos.qty, pos.sl, pos.tgt
                        )
                        continue
                    if tr.is_runner:
                        self._verify_one_order(underlying, pos, "sl_order_id", "SL", tr=tr)
                    if tr.tgt_order_id:
                        self._verify_one_order(underlying, pos, "tgt_order_id", "LIMIT", tr=tr)

    def _verify_one_order(
        self,
        underlying: str,
        pos: OptionPosition,
        attr: str,
        label: str,
        tr: Tranche | None = None,
    ) -> None:
        """Check one broker order status; re-issue if cancelled/rejected/expired."""
        oid = getattr(tr, attr) if tr else getattr(pos, attr)
        if not oid:
            return
        try:
            resp = self.client.orderstatus(order_id=oid, strategy=self.config.broker.strategy_name)
            if not isinstance(resp, dict) or resp.get("status") != "success":
                return
            data = resp.get("data") or resp
            broker_stat = str(data.get("order_status", "")).lower()
            if broker_stat in ("cancelled", "rejected", "canceled", "expired"):
                tag = f"t={tr.tranche_id} " if tr else ""
                inf(f"[ORDER] {label} ORDER MISSING for {underlying} {tag}(status={broker_stat}) — re-issuing")
                if tr:
                    setattr(tr, attr, None)
                else:
                    setattr(pos, attr, None)
                self._place_protection_orders_sequential(
                    underlying, pos, pos.symbol, pos.qty, pos.sl, pos.tgt
                )
        except Exception as exc:
            tag = f"t={tr.tranche_id} " if tr else ""
            err(f"[ORDER] verify_{label.lower()}_order error for {underlying} {tag}", exc)

    def register_filled_entry(
        self,
        underlying: str,
        option_symbol: str,
        qty: int,
        spot: float,
        direction: str,
        executed: float,
        sl_pts: float | None = None,
        entry_delta: float | None = None,
        entry_conviction: float = 0.0,
        entry_sl_source: str = "",
    ) -> None:
        """Register filled entry with delta tracking for moneyness analysis."""
        cfg = self.config
        moneyness, _, tgt_mult, act_mult = EntryStopLossPolicy.get_moneyness_multipliers(entry_delta)

        resolved_sl_pts = sl_pts if (sl_pts is not None and sl_pts > 0) else cfg.entry.premium_stop_pts
        sl  = executed - resolved_sl_pts
        tgt = executed + (cfg.entry.premium_target_pts * tgt_mult)
        reward_dist = spot * (cfg.entry.spot_reward_pct / 100.0)

        pos = OptionPosition.build(
            underlying=underlying,
            symbol=option_symbol,
            entry_premium=executed,
            qty=qty,
            option_type=direction,
            entry_delta=entry_delta,
            moneyness=moneyness,
            sl=sl,
            initial_sl=sl,
            tgt=tgt,
            spot_symbol=underlying,
            spot_entry=spot,
            reward_dist=reward_dist,
            entry_time=get_ist_now(),
            entry_conviction=max(0.0, min(1.0, entry_conviction)),
            trail_act_mult=act_mult,
            entry_bucket=self._state.bucket_counter,
            entry_sl_source=entry_sl_source,
        )
        pos.tranches = _build_tranches(pos, qty, cfg)
        with self._state.state_lock:
            self._state.positions.add(pos)
        # Link snapshot cache with the active option symbol
        self._state.snapshot_cache.set_option_symbol(underlying, option_symbol)

        self._ws.subscribe(cfg.market.fno_exchange, option_symbol)
        self._ws.subscribe_spot(underlying)
        inf(
            f"[DATA] TRADE REGISTERED {underlying}: "
            f"option={option_symbol} exchange={cfg.market.fno_exchange} | "
            f"spot={underlying} spot_exchange={'NSE_INDEX' if underlying in cfg.market.index_underlyings else cfg.market.spot_exchange} | "
            f"entry=₹{executed:.2f} spot_entry=₹{spot:.2f} direction={direction} | "
            f"SL=₹{sl:.2f} TGT=₹{tgt:.2f} | "
            f"delta={entry_delta if entry_delta else 'N/A'} conviction={entry_conviction:.2f} | "
            f"ws_desired={list(self._ws._desired)}"
        )

        if cfg.broker.broker_sl_orders and not cfg.broker.paper_trade:
            if cfg.broker.use_basket_protection and hasattr(self.client, "basketorder") and not cfg.tranche.enabled:
                self._place_protection_basket(underlying, pos, option_symbol, qty, sl, tgt)
            else:
                self._place_protection_orders_sequential(underlying, pos, option_symbol, qty, sl, tgt)

            if pos.sl_order_id or pos.tgt_order_id:
                pos.broker_protection = True

        # Advance lifecycle: ENTRY → INITIAL_PROTECTED (protection orders placed)
        _advance_stage(pos, LifecycleStage.INITIAL_PROTECTED)

        inf(
            f"[ORDER] Position registered for {underlying}: {option_symbol} "
            f"QTY={qty} ENTRY=₹{executed:.2f} SL=₹{sl:.2f} "
            f"(pts={resolved_sl_pts:.2f}) TGT=₹{tgt:.2f}"
        )

        direction_emoji = "🔺 UP" if direction.upper() == "CE" else "🔻 DN"
        now_str = get_ist_now().strftime("%H:%M:%S")
        actual_sl_pts = round(executed - sl, 2)
        actual_target_pts = round(tgt - executed, 2)
        rrr = round(actual_target_pts / actual_sl_pts, 2) if actual_sl_pts > 0 else 0
        sl_amt = actual_sl_pts * qty
        tgt_amt = actual_target_pts * qty
        delta_str = f"{entry_delta:.2f}" if entry_delta is not None else "N/A"
        mode_str = "PAPER" if cfg.broker.paper_trade else "TRADE"
        self._notify(
            f"🚀 {direction_emoji} {mode_str} ENTRY: {underlying} @ {now_str}\n"
            f"🔹 Option: {option_symbol} (x{qty})\n"
            f"🎯 Fill Price: ₹{executed:.2f}\n"
            f"📊 {moneyness} | RRR: 1:{rrr} | Δ:{delta_str} | Conv:{entry_conviction:.0%}\n"
            f"🛑 SL: {actual_sl_pts:.1f} (₹{sl_amt:.0f}) | 🏁 TGT: {actual_target_pts:.1f} (₹{tgt_amt:.0f})",
            2,
        )

    def _place_protection_basket(
        self,
        underlying: str,
        pos: OptionPosition,
        option_symbol: str,
        qty: int,
        sl: float,
        tgt: float
    ) -> None:
        cfg = self.config
        try:
            basket_orders = [
                {
                    "symbol": option_symbol,
                    "exchange": cfg.market.fno_exchange,
                    "action": "SELL",
                    "quantity": qty,
                    "pricetype": "SL-M",
                    "product": "MIS",
                    "trigger_price": sl,
                    "price": 0,
                },
                {
                    "symbol": option_symbol,
                    "exchange": cfg.market.fno_exchange,
                    "action": "SELL",
                    "quantity": qty,
                    "pricetype": "LIMIT",
                    "product": "MIS",
                    "price": tgt,
                }
            ]
            basket_resp = self.client.basketorder(strategy=cfg.broker.strategy_name, orders=basket_orders)
            if isinstance(basket_resp, dict) and basket_resp.get("status") == "success":
                results = basket_resp.get("results", [])
                if len(results) != len(basket_orders):
                    inf(f"[ORDER] Basket result count mismatch for {underlying}: "
                        f"sent {len(basket_orders)}, got {len(results)} — falling back to sequential")
                else:
                    for i, leg in enumerate(results):
                        if leg.get("status") != "success" or not leg.get("orderid"):
                            inf(f"[ORDER] Basket leg {i} rejected for {underlying}: {leg}")
                            continue
                        # NOTE: basketorder's response schema has no field identifying leg type
                        # (confirmed against openalgo SDK source) — position in `results` is
                        # assumed to match position in the submitted `orders` list.
                        is_sl = (i == 0)
                        if is_sl:
                            pos.sl_order_id = leg.get("orderid")
                            inf(f"[ORDER] Basket SL-M placed for {underlying}: trigger ₹{sl:.2f} (id:{pos.sl_order_id})")
                        else:
                            pos.tgt_order_id = leg.get("orderid")
                            inf(f"[ORDER] Basket LIMIT placed for {underlying}: ₹{tgt:.2f} (id:{pos.tgt_order_id})")

                    if pos.sl_order_id and pos.tgt_order_id:
                        return
        except Exception as exc: err(f"[ORDER] Basket order error for {underlying}: ", exc)

        inf(f"[ORDER] Falling back to sequential protective orders for {underlying}...")
        self._place_protection_orders_sequential(underlying, pos, option_symbol, qty, sl, tgt)

    def _place_protection_orders_sequential(
        self,
        underlying: str,
        pos: OptionPosition,
        option_symbol: str,
        qty: int,
        sl: float,
        tgt: float
    ) -> None:
        cfg = self.config
        is_multi = len(pos.tranches) > 1
        if not is_multi:
            # ── Single-tranche (backward compat) ──────────────────────────────
            if not pos.sl_order_id:
                try:
                    sl_resp = self.client.placeorder(
                        strategy=cfg.broker.strategy_name,
                        symbol=option_symbol,
                        action="SELL",
                        exchange=cfg.market.fno_exchange,
                        price_type="SL-M",
                        product="MIS",
                        quantity=qty,
                        price=0,
                        trigger_price=sl,
                    )
                    if isinstance(sl_resp, dict) and sl_resp.get("status") == "success":
                        pos.sl_order_id = sl_resp.get("orderid")
                        inf(f"[ORDER] Broker SL-M placed for {underlying}: trigger ₹{sl:.2f} (id:{pos.sl_order_id})")
                except Exception as exc: err(f"[ORDER] Broker SL-M error for {underlying}: ", exc)

            if not pos.tgt_order_id:
                try:
                    tgt_resp = self.client.placeorder(
                        strategy=cfg.broker.strategy_name,
                        symbol=option_symbol,
                        action="SELL",
                        exchange=cfg.market.fno_exchange,
                        price_type="LIMIT",
                        product="MIS",
                        quantity=qty,
                        price=tgt,
                    )
                    if isinstance(tgt_resp, dict) and tgt_resp.get("status") == "success":
                        pos.tgt_order_id = tgt_resp.get("orderid")
                        inf(f"[ORDER] Broker LIMIT placed for {underlying}: ₹{tgt:.2f} (id:{pos.tgt_order_id})")
                except Exception as exc: err(f"[ORDER] Broker LIMIT target error for {underlying}: ", exc)
        else:
            # ── Multi-tranche: each tranche gets its own orders ──────────────
            for tr in pos.open_tranches:
                if tr.qty <= 0:
                    continue
                if tr.is_runner:
                    if not tr.sl_order_id:
                        try:
                            sl_resp = self.client.placeorder(
                                strategy=cfg.broker.strategy_name,
                                symbol=option_symbol,
                                action="SELL",
                                exchange=cfg.market.fno_exchange,
                                price_type="SL-M",
                                product="MIS",
                                quantity=tr.qty,
                                price=0,
                                trigger_price=sl,
                            )
                            if isinstance(sl_resp, dict) and sl_resp.get("status") == "success":
                                tr.sl_order_id = sl_resp.get("orderid")
                                inf(f"[ORDER] Broker SL-M placed for {underlying} t={tr.tranche_id}: trigger ₹{sl:.2f} (id:{tr.sl_order_id})")
                        except Exception as exc: err(f"[ORDER] Broker SL-M error for {underlying} t={tr.tranche_id}: ", exc)
                if not tr.tgt_order_id:
                    _tgt_price = tr.tp_pts if tr.tp_pts is not None else tgt
                    try:
                        tgt_resp = self.client.placeorder(
                            strategy=cfg.broker.strategy_name,
                            symbol=option_symbol,
                            action="SELL",
                            exchange=cfg.market.fno_exchange,
                            price_type="LIMIT",
                            product="MIS",
                            quantity=tr.qty,
                            price=_tgt_price,
                        )
                        if isinstance(tgt_resp, dict) and tgt_resp.get("status") == "success":
                            tr.tgt_order_id = tgt_resp.get("orderid")
                            inf(f"[ORDER] Broker LIMIT placed for {underlying} t={tr.tranche_id}: ₹{_tgt_price:.2f} (id:{tr.tgt_order_id})")
                    except Exception as exc: err(f"[ORDER] Broker LIMIT target error for {underlying} t={tr.tranche_id}: ", exc)

    # ── Trade Journal ──────────────────────────────────────────────────────────

    def _write_journal(
        self,
        underlying: str,
        pos: OptionPosition,
        exit_price: float,
        pnl_abs: float,
        exit_reason: str,
        exit_price_source: str = "broker_fill",
        record_type: str | None = None,
    ) -> None:
        """Append one row to the CSV trade journal via JournalWriter / TradeAnalytics."""
        record = TradeAnalytics.build(
            underlying=underlying, pos=pos, exit_price=exit_price,
            pnl_abs=pnl_abs, exit_reason=exit_reason,
            exit_price_source=exit_price_source,
            paper_trade=self.config.broker.paper_trade,
            sl_method=self.config.trail.sl_method,
            activation_lock_pct=self.config.trail.activation_lock_pct,
            record_type=record_type,
        )
        self._journal.write(record)

    def place_entry(
        self,
        underlying: str,
        option_symbol: str,
        qty: int,
        spot: float,
        direction: str,
        sl_pts: float | None = None,
        entry_delta: float | None = None,
        entry_conviction: float = 0.0,
        entry_sl_source: str = "",
    ) -> bool:
        """Place a market BUY order, poll for fill, then register the position with moneyness tracking."""
        cfg = self.config
        resolved_sl_pts = sl_pts if (sl_pts is not None and sl_pts > 0) else cfg.entry.premium_stop_pts
        allowed, reason = self._state.position_book.can_enter(underlying, direction, cfg)
        if not allowed:
            inf(f"[ORDER] {underlying} blocked by position guard: {reason}")
            return False

        if cfg.broker.paper_trade:
            executed = self._resolve_option_ltp(underlying, option_symbol) or spot * 0.01
            inf(f"[PAPER] Simulated BUY {qty}x {option_symbol} @ ₹{executed:.2f}")
            self._risk.record_entry(underlying)
            self.register_filled_entry(
                underlying, option_symbol, qty, spot, direction, executed,
                sl_pts=resolved_sl_pts, entry_delta=entry_delta,
                entry_conviction=entry_conviction,
                entry_sl_source=entry_sl_source,
            )
            return True

        with self._state.state_lock:
            self._state.entry_in_flight[underlying] = self._state.entry_in_flight.get(underlying, 0) + 1
        try:
            if cfg.entry.preflight_spread_check and not cfg.broker.paper_trade:
                live_q = self._fetcher.fetch_quote(option_symbol, cfg.market.fno_exchange)
                if live_q:
                    bid = float(live_q.get("bid", 0) or 0)
                    ask = float(live_q.get("ask", 0) or 0)
                    ltp = float(live_q.get("ltp", 0) or 0)
                    mid = (bid + ask) / 2 if (bid and ask) else ltp
                    if cfg.entry.preflight_min_bid > 0 and bid < cfg.entry.preflight_min_bid:
                        inf(
                            f"[ORDER] Pre-flight FAIL {option_symbol}: "
                            f"bid ₹{bid:.2f} < min ₹{cfg.entry.preflight_min_bid:.2f}"
                        )
                        return False
                    if (
                        cfg.entry.preflight_max_spread_pct > 0
                        and mid > 0
                        and ask > bid
                    ):
                        spread_pct = (ask - bid) / mid * 100
                        if spread_pct > cfg.entry.preflight_max_spread_pct:
                            inf(
                                f"[ORDER] Pre-flight FAIL {option_symbol}: "
                                f"spread {spread_pct:.1f}% > max {cfg.entry.preflight_max_spread_pct:.1f}%"
                            )
                            return False

            inf(f"[ORDER] Calling placeorder for {underlying}...")
            resp = self.client.placeorder(
                strategy=cfg.broker.strategy_name,
                symbol=option_symbol,
                action="BUY",
                exchange=cfg.market.fno_exchange,
                price_type="MARKET",
                product="MIS",
                quantity=qty,
            )
            inf(f"[ORDER] placeorder returned for {underlying}")
            if not isinstance(resp, dict) or resp.get("status") != "success":
                inf(f"[ORDER] Entry order rejected for {underlying}: {resp}")
                return False
            order_id: str | None = resp.get("orderid")
            if not order_id:
                err(f"[ORDER] {underlying}: place_order returned no orderid — abandoning entry")
                return False
            inf(f"[ORDER] Entry order {order_id} placed for {underlying} ({option_symbol} x{qty})")

            # Add to pending entries for reconciliation
            pending_entry = PendingEntry(
                underlying=underlying,
                order_id=order_id,
                symbol=option_symbol,
                qty=qty,
                spot=spot,
                direction=direction,
                sl_pts=resolved_sl_pts,
                created_at=get_ist_now(),
                entry_delta=entry_delta,
                entry_conviction=entry_conviction,
                entry_sl_source=entry_sl_source,
            )
            with self._state.state_lock:
                self._state.pending_entries[order_id] = pending_entry

            filled = self.poll_order_status(order_id)
            if not filled:
                outcome = self._cancel_three_outcome(order_id, pending_entry)
                if outcome == "cancelled":
                    with self._state.state_lock:
                        self._state.pending_entries.pop(order_id, None)
                    inf(f"[ORDER] Entry order {order_id} not filled — cancelled confirmed, removed")
                elif outcome == "reconciled":
                    with self._state.state_lock:
                        self._state.pending_entries.pop(order_id, None)
                    inf(f"[ORDER] Entry order {order_id} not filled — reconciled via race-fill")
                    return True
                else:
                    inf(f"[ORDER] Cannot confirm cancel for {order_id} — keeping pending entry")
                inf(f"[ORDER] Entry order {order_id} not filled within poll window — abandoning")
                return False

            data       = filled.get("data") or filled
            executed   = float(data.get("average_price", 0) or 0)
            if not executed:
                executed = float(data.get("price", 0) or 0)
            if not executed:
                inf(f"[ORDER] Executed price is zero for {order_id} — cannot register position")
                return False

            filled_qty = int(data.get("filled_quantity", 0) or data.get("filled_qty", 0) or 0)
            if filled_qty > 0 and filled_qty != qty:
                outcome = self._cancel_three_outcome(order_id, pending_entry)
                if outcome == "cancelled":
                    qty = filled_qty
                    inf(f"[ORDER] Partial fill accepted: {filled_qty} (residual cancelled)")
                elif outcome == "reconciled":
                    with self._state.state_lock:
                        self._state.pending_entries.pop(order_id, None)
                    inf(f"[ORDER] Partial fill reconciled by cancel-race for {order_id}")
                    return True
                else:
                    inf(f"[ORDER] Cannot confirm residual for {order_id} — keeping pending entry")
                    return False
            with self._state.state_lock:
                self._state.pending_entries.pop(order_id, None)

            self._risk.record_entry(underlying)
            self.register_filled_entry(
                underlying, option_symbol, qty, spot, direction, executed,
                sl_pts=resolved_sl_pts, entry_delta=entry_delta,
                entry_conviction=entry_conviction,
                entry_sl_source=entry_sl_source,
            )
            return True
        except Exception as exc:
            err(f"[ORDER] placeorder error for {underlying}", exc)
            return False
        finally:
            with self._state.state_lock:
                self._state.entry_in_flight[underlying] = max(0, self._state.entry_in_flight.get(underlying, 0) - 1)

    def _exit_non_runner_tranche(self, underlying: str, pos: OptionPosition, tr: Tranche, reason: str) -> None:
        cfg = self.config
        if tr.is_exit_placed or tr.is_runner:
            return
        # Check if we already have a pending SELL for this tranche
        _tranche_key = f"{underlying}_{tr.tranche_id}"
        with self._pending_tranche_exits_lock:
            _pending_oid = self._pending_tranche_exits.get(_tranche_key)
        if _pending_oid:
            raw = self._raw_order_status(_pending_oid)
            if raw:
                bs = str(raw.get("order_status", "")).lower()
                ep = float(raw.get("average_price", 0) or 0)
                fq_raw = int(raw.get("filled_quantity", 0) or raw.get("filled_qty", 0) or 0)
                if bs in ("complete", "filled", "executed") and ep > 0:
                    use_qty = fq_raw if fq_raw > 0 else tr.qty
                    with self._pending_tranche_exits_lock:
                        self._pending_tranche_exits.pop(_tranche_key, None)
                    self.apply_confirmed_partial_exit(pos, tr, use_qty, ep, reason, underlying, pos.symbol)
                    for attr_name, oid in [("sl_order_id", tr.sl_order_id), ("tgt_order_id", tr.tgt_order_id)]:
                        if oid:
                            try:
                                self.client.cancelorder(order_id=oid, strategy=cfg.broker.strategy_name)
                            except Exception as exc:
                                err(f"[ORDER] Cancel {attr_name} error for {underlying} t={tr.tranche_id}: ", exc)
                    inf(f"[ORDER] Tranche exit SELL {_pending_oid} complete for {underlying} t={tr.tranche_id}")
                elif bs in ("cancelled", "canceled", "rejected") and ep > 0:
                    use_qty = fq_raw if fq_raw > 0 else tr.qty
                    with self._pending_tranche_exits_lock:
                        self._pending_tranche_exits.pop(_tranche_key, None)
                    self.apply_confirmed_partial_exit(pos, tr, use_qty, ep, reason, underlying, pos.symbol)
                    if pos.remaining_qty > 0:
                        for trr in pos.tranches:
                            trr.sl_order_id = None
                            trr.tgt_order_id = None
                        pos.sl_order_id = None
                        pos.tgt_order_id = None
                        self._place_protection_orders_sequential(
                            underlying, pos, pos.symbol, pos.remaining_qty,
                            pos.sl, pos.tgt,
                        )
                    inf(f"[ORDER] Tranche exit SELL {_pending_oid} partially filled {fq_raw} — protection re-placed for residual")
                elif bs in ("cancelled", "canceled", "rejected"):
                    with self._pending_tranche_exits_lock:
                        self._pending_tranche_exits.pop(_tranche_key, None)
                    inf(f"[ORDER] Tranche exit SELL {_pending_oid} unreported — protection left active")
                else:
                    inf(f"[ORDER] Tranche exit SELL {_pending_oid} status {bs} — still pending")
            else:
                inf(f"[ORDER] Tranche exit SELL {_pending_oid} status check failed — will retry")
            return
        if cfg.broker.paper_trade:
            executed_price = self._resolve_option_ltp(underlying, pos.symbol) or pos.entry_premium
            tr.is_exit_placed = True
            tr.exit_reason = reason
            tr.exit_price = executed_price
            pnl = _calc_pnl(pos, executed_price, qty=tr.qty) if executed_price > 0 else 0.0
            inf(f"[ORDER] Signal-deterioration partial exit {underlying} t={tr.tranche_id}: "
                f"\u20b9{executed_price:.2f} \u00d7 {tr.qty} | P&L \u20b9{pnl:.0f}")
            self._risk.record_exit(pnl)
            _pts_loss = max(0.0, pos.entry_premium - executed_price)
            self._state.record_strike_loss(pos.symbol, pos.option_type, _pts_loss)
            tr_exit_record = TradeAnalytics.build_tranche(
                underlying=underlying, pos=pos, tr=tr,
                paper_trade=cfg.broker.paper_trade,
            )
            self._journal.write(tr_exit_record)
            return
        # Place SELL first — keep protection active until fill confirmed
        order_id = None
        try:
            resp = self.client.placeorder(
                strategy=cfg.broker.strategy_name,
                symbol=pos.symbol,
                action="SELL",
                exchange=cfg.market.fno_exchange,
                price_type="MARKET",
                product="MIS",
                quantity=tr.qty,
            )
            if isinstance(resp, dict) and resp.get("status") == "success":
                order_id = resp.get("orderid")
                inf(f"[ORDER] Partial exit order {order_id} placed for {underlying} t={tr.tranche_id}")
            else:
                inf(f"[ORDER] Partial exit order response: {resp}")
        except Exception as exc:
            err(f"[ORDER] Partial exit error for {underlying} t={tr.tranche_id}: ", exc)
        if order_id is None:
            inf(f"[ORDER] Partial exit SELL failed for {underlying} t={tr.tranche_id} — protection remains active")
            return
        # Register in-flight before poll so place_exit sees it (F-A1)
        with self._pending_tranche_exits_lock:
            self._pending_tranche_exits[_tranche_key] = order_id
        filled = self.poll_order_status(order_id)
        if filled:
            data = filled.get("data") or filled
            executed_price = float(data.get("average_price", 0) or 0)
            if executed_price > 0:
                # SELL confirmed — remove from in-flight tracker, cancel protection
                with self._pending_tranche_exits_lock:
                    self._pending_tranche_exits.pop(_tranche_key, None)
                for attr_name, oid in [("sl_order_id", tr.sl_order_id), ("tgt_order_id", tr.tgt_order_id)]:
                    if oid:
                        try:
                            self.client.cancelorder(order_id=oid, strategy=cfg.broker.strategy_name)
                        except Exception as exc:
                            err(f"[ORDER] Cancel {attr_name} error for {underlying} t={tr.tranche_id}: ", exc)
                tr.is_exit_placed = True
                tr.exit_reason = reason
                tr.exit_price = executed_price
                pnl = _calc_pnl(pos, executed_price, qty=tr.qty) if executed_price > 0 else 0.0
                inf(f"[ORDER] Signal-deterioration partial exit {underlying} t={tr.tranche_id}: "
                    f"\u20b9{executed_price:.2f} \u00d7 {tr.qty} | P&L \u20b9{pnl:.0f}")
                self._risk.record_exit(pnl)
                _pts_loss = max(0.0, pos.entry_premium - executed_price)
                self._state.record_strike_loss(pos.symbol, pos.option_type, _pts_loss)
                tr_exit_record = TradeAnalytics.build_tranche(
                    underlying=underlying, pos=pos, tr=tr,
                    paper_trade=cfg.broker.paper_trade,
                )
                self._journal.write(tr_exit_record)
                return
        # Fill unconfirmed — entry already in _pending_tranche_exits, stays for reconciliation
        inf(f"[ORDER] Partial exit SELL unconfirmed for {underlying} t={tr.tranche_id} — saved for reconciliation")

    def _sellable_qty(self, pos: OptionPosition) -> int:
        """remaining_qty minus any in-flight tranche exits for this position (F-A1)."""
        in_flight = 0
        for tr in pos.tranches:
            if tr.is_exit_placed:
                continue
            with self._pending_tranche_exits_lock:
                if f"{pos.underlying}_{tr.tranche_id}" in self._pending_tranche_exits:
                    in_flight += tr.qty
        return max(0, pos.remaining_qty - in_flight)

    def place_exit(self, underlying: str, reason: str = "manual", slot_id: str | None = None) -> None:
        """Cancel broker orders first, then place SELL MARKET to exit position."""
        cfg = self.config
        pos = self._state.positions.slot(slot_id) if slot_id else self._state.positions.get_one(underlying)
        if not pos:
            return
        pos.exit_bucket = self._state.bucket_counter
        _advance_stage(pos, LifecycleStage.EXIT_PENDING)
        # Normalize exit reason to enum for consistent attribution
        norm_reason = ExitReason.normalize(reason)
        inf(f"[ORDER] Exiting {underlying} — reason: {reason} → {norm_reason}")

        if cfg.broker.paper_trade:
            executed_price = self._resolve_option_ltp(underlying, pos.symbol) or pos.entry_premium
            exit_qty = self._sellable_qty(pos)
            pnl = _calc_pnl(pos, executed_price, qty=exit_qty)
            inf(f"[PAPER] Simulated SELL {exit_qty}x {pos.symbol} @ ₹{executed_price:.2f} | P&L ₹{pnl:.2f}")
            self._finalize_exit(underlying, pos, executed_price, pnl, norm_reason,
                                exit_price_source="paper")
            direction_emoji = "🔺 UP" if pos.option_type.upper() == "CE" else "🔻 DN"
            emoji = "✅ PROFIT" if pnl >= 0 else "❌ LOSS"
            risk_pts = max(0.01, pos.entry_premium - pos.initial_sl)
            risk_amt = risk_pts * pos.remaining_qty
            r_multiple = pnl / risk_amt if risk_amt > 0 else 0.0
            hold_mins = max(0, int((get_ist_now() - pos.entry_time).total_seconds() / 60))
            self._notify(
                    f"{emoji} PAPER EXIT: {underlying}\n"
                    f"📌 {norm_reason}\n"
                    f"{direction_emoji} {pos.symbol}\n"
                    f"🚪 ₹{pos.entry_premium:.2f} → ₹{executed_price:.2f}\n"
                    f"💰 P&L: ₹{pnl:.0f} ({r_multiple:+.2f}R)\n"
                    f"⏱ Hold: {hold_mins}m | Daily: ₹{self._risk.daily_pnl:.0f}",
                    2,
                )
            # Safety check: verify position was actually removed
            if self._state.positions.slot(pos.slot_id):
                err(f"[CLEANUP] PAPER EXIT failed to remove {pos.symbol} from book — force-removing")
                with self._state.state_lock:
                    self._state.positions.pop(pos.slot_id, None)
            return

        broker_filled = {}
        if cfg.broker.broker_sl_orders:
            broker_filled = self.cancel_broker_orders(underlying, slot_id=pos.slot_id)

        is_multi_tranche = any("tranche_id" in v for v in broker_filled.values())

        if not is_multi_tranche:
            for attr_name, info in broker_filled.items():
                if isinstance(info, dict) and info.get("order_status") in ("complete", "filled", "executed"):
                    executed_price = info.get("executed", 0)
                    inf(f"[ORDER] Broker {attr_name} already filled at ₹{executed_price:.2f} — skipping SELL")
                    pnl = _calc_pnl(pos, float(executed_price))
                    self._finalize_exit(underlying, pos, float(executed_price), pnl, norm_reason,
                                        exit_price_source="broker_fill")
                    return
        else:
            for attr_name, info in broker_filled.items():
                if isinstance(info, dict) and info.get("tranche_id") is not None:
                    tr_id = info["tranche_id"]
                    tr = next((t for t in pos.tranches if t.tranche_id == tr_id), None)
                    if tr and not tr.is_exit_placed:
                        tr.is_exit_placed = True
                        tr.exit_reason = ExitReason.BROKER_FILLED
                        tr.exit_price = info.get("executed", 0)
                        tr_pnl = _calc_pnl(pos, tr.exit_price, qty=tr.qty) if tr.exit_price > 0 else 0.0
                        self._risk.record_exit(tr_pnl)
                        _pts_loss = max(0.0, pos.entry_premium - tr.exit_price)
                        self._state.record_strike_loss(pos.symbol, pos.option_type, _pts_loss)
                        tr_exit_record = TradeAnalytics.build_tranche(
                            underlying=underlying, pos=pos, tr=tr,
                            paper_trade=cfg.broker.paper_trade,
                        )
                        self._journal.write(tr_exit_record)
                        inf(f"[ORDER] Tranche {tr_id} {attr_name} filled at broker — P&L ₹{tr_pnl:.0f}")
            if pos.remaining_qty == 0:
                # All tranches exited via broker fills — cleanup without _finalize_exit
                # to avoid double-recording P&L and duplicate full-exit journal row
                opt_sym = pos.symbol
                self._ws.unsubscribe(self.config.market.fno_exchange, opt_sym)
                if not self._state.positions.has_siblings(pos.slot_id):
                    self._ws.unsubscribe_spot(pos.spot_symbol)
                _advance_stage(pos, LifecycleStage.CLOSED)
                inf(f"[TRAIL-EXIT] {underlying} {pos.symbol}: reason={norm_reason}, all-tranche-broker-fill")
                with self._state.state_lock:
                    self._state.positions.pop(pos.slot_id, None)
                    self._state.pending_opposite_exit.discard(underlying)
                with self._state.exit_lock:
                    self._state.exit_queue.discard(pos.slot_id)
                return

        # F-A1: don't oversell — in-flight tranche exits may already be covering remaining qty
        sellable_qty = self._sellable_qty(pos)
        if sellable_qty <= 0:
            inf(f"[ORDER] Exit skipped for {underlying} — all qty covered by in-flight tranche exits")
            with self._state.exit_lock:
                self._state.exit_queue.discard(pos.slot_id)
            pos.exit_pending = False
            return

        executed_price = 0.0
        order_id       = None
        try:
            resp = self.client.placeorder(
                strategy=cfg.broker.strategy_name,
                symbol=pos.symbol,
                action="SELL",
                exchange=cfg.market.fno_exchange,
                price_type="MARKET",
                product="MIS",
                quantity=sellable_qty,
            )
            if isinstance(resp, dict) and resp.get("status") == "success":
                order_id = resp.get("orderid")
                inf(f"[ORDER] Exit order {order_id} placed for {underlying}")
            else:
                inf(f"[ORDER] Exit order response: {resp}")
        except Exception as exc: err(f"[ORDER] place_exit error for {underlying}: ", exc)

        if order_id is None:
            now_hm = get_ist_now().strftime("%H:%M")
            is_past_cutoff = bool(cfg.market.square_off_time and now_hm >= cfg.market.square_off_time)

            if is_past_cutoff:
                best_price = self._resolve_option_ltp(underlying, pos.symbol)
                if best_price is not None:
                    pnl = _calc_pnl(pos, best_price)
                    journal_reason = ExitReason.FORCE_UNTRACK_EST
                else:
                    best_price = 0.0
                    pnl = 0.0
                    journal_reason = ExitReason.FORCE_UNTRACK_UNKNOWN
                    
                self._finalize_exit(underlying, pos, best_price, pnl, journal_reason,
                                    exit_price_source="estimated")
                inf(
                    f"[ORDER] Exit order rejected after EOD cutoff — untracking {underlying} "
                    f"({journal_reason} price ₹{best_price:.2f} | P&L ₹{pnl:.0f})"
                )
                with self._state.state_lock:
                    self._state.positions.pop(pos.slot_id, None)
                    self._state.pending_opposite_exit.discard(underlying)
                with self._state.exit_lock:
                    self._state.exit_queue.discard(pos.slot_id)
                return

            # Order was not submitted — safe to release exit lock so the next SL
            # trigger from the WS trail can retry the exit on the next tick.
            inf(f"[ORDER] Exit order not submitted for {underlying} — releasing for retry")
            with self._state.exit_lock:
                self._state.exit_queue.discard(pos.slot_id)
            pos.exit_pending = False
            return

        with self._state.state_lock:
            self._state.pending_exits[pos.slot_id] = PendingExit(
                order_id=order_id,
                reason=norm_reason,
                created_at=get_ist_now(),
                exit_qty=pos.remaining_qty,
            )
        filled = self.poll_order_status(order_id)
        if not filled:
            # Order submitted but fill could not be confirmed within the poll window.
            # Leave pending_exits intact so check_pending_exits() reconciles on the
            # next strategy cycle; position and exit_pending stay as-is.
            inf(
                f"[ORDER] Exit fill unconfirmed for {underlying} (order {order_id}) "
                f"— leaving in pending_exits for reconciliation"
            )
            return

        data           = filled.get("data") or filled
        executed_price = float(data.get("average_price", 0) or 0)
        filled_qty     = int(data.get("filled_quantity", 0) or data.get("filled_qty", 0) or 0)
        order_qty      = int(data.get("quantity", 0) or 0)

        # F76: REST API never populates filled_qty — treat 0 as fully filled when ep>0
        if filled_qty > 0 and order_qty > 0 and filled_qty < order_qty:
            inf(
                f"[ORDER] Exit partial fill for {underlying}: {filled_qty}/{order_qty} — "
                f"leaving in pending_exits for full reconciliation"
            )
            return

        with self._state.state_lock:
            self._state.pending_exits.pop(pos.slot_id, None)

        pnl = _calc_pnl(pos, executed_price)
        self._finalize_exit(underlying, pos, executed_price, pnl, norm_reason,
                            exit_price_source="broker_fill")

        direction_emoji = "🔺 UP" if pos.option_type.upper() == "CE" else "🔻 DN"
        emoji = "✅ PROFIT" if pnl >= 0 else "❌ LOSS"
        risk_pts = max(0.01, pos.entry_premium - pos.initial_sl)
        risk_amt = risk_pts * pos.remaining_qty
        r_multiple = pnl / risk_amt if risk_amt > 0 else 0.0
        hold_mins = max(0, int((get_ist_now() - pos.entry_time).total_seconds() / 60))
        self._notify(
            f"{emoji} EXIT: {underlying}\n"
            f"📌 {reason.upper()}\n"
            f"{direction_emoji} {pos.symbol}\n"
            f"🚪 ₹{pos.entry_premium:.2f} → ₹{executed_price:.2f}\n"
            f"💰 P&L: ₹{pnl:.0f} ({r_multiple:+.2f}R)\n"
            f"⏱ Hold: {hold_mins}m | Daily: ₹{self._risk.daily_pnl:.0f}",
            2,
        )

    def check_pending_entries(self) -> None:
        """Reconcile stale pending entry orders. Post-cutoff entries queue immediate exit."""
        cfg = self.config
        with self._state.state_lock:
            pending = list(self._state.pending_entries.items())
        now_hm = get_ist_now().strftime("%H:%M")
        square_off_hm = cfg.market.square_off_time
        for order_id, pending_entry in pending:
            underlying = pending_entry.underlying
            filled = self.poll_order_status(order_id, max_retries=1, sleep_secs=0)
            if filled:
                data     = filled.get("data") or filled
                status   = str(data.get("order_status", "")).lower() if isinstance(data, dict) else ""
                price    = float((data.get("average_price") if isinstance(data, dict) else None) or 0)
                if status == "complete" and price:
                    with self._state.state_lock:
                        self._state.pending_entries.pop(order_id, None)
                        already_open = any(p.symbol == pending_entry.symbol for p in self._state.positions.get_all(underlying))
                    if already_open:
                        self._notify(
                            f"\u26a0\ufe0f {cfg.broker.strategy_name}: pending BUY {order_id} filled but "
                            f"{pending_entry.symbol} already has a tracked slot — duplicate. Reconcile manually.",
                            9,
                        )
                        continue
                    inf(f"[PENDING] BUY {order_id} filled for {underlying} @ \u20b9{price:.2f}; activating protection")
                    filled_qty = int(data.get("filled_quantity", 0) or data.get("filled_qty", 0) or 0)
                    if filled_qty > 0 and filled_qty != pending_entry.qty:
                        inf(f"[PENDING] Partial fill: requested {pending_entry.qty}, filled {filled_qty}")
                    use_qty = filled_qty if filled_qty > 0 else pending_entry.qty
                    self._risk.record_entry(underlying)
                    self.register_filled_entry(
                        underlying, pending_entry.symbol, use_qty,
                        pending_entry.spot, pending_entry.direction, price,
                        sl_pts=pending_entry.sl_pts,
                        entry_delta=pending_entry.entry_delta,
                        entry_conviction=pending_entry.entry_conviction,
                        entry_sl_source=pending_entry.entry_sl_source,
                    )
                    # If filled after square_off_time, queue immediate exit
                    if square_off_hm and now_hm >= square_off_hm:
                        inf(f"[PENDING] Entry {order_id} filled AFTER cutoff ({now_hm} >= {square_off_hm}) — queuing exit")
                        _cutoff_slot_id = None
                        with self._state.state_lock:
                            pos = next(
                                (p for p in self._state.positions.get_all(underlying) if p.symbol == pending_entry.symbol),
                                None,
                            )
                            if pos:
                                _cutoff_slot_id = pos.slot_id
                                pos.exit_pending = True
                                with self._state.exit_lock:
                                    self._state.exit_queue.add(pos.slot_id)
                        if _cutoff_slot_id:
                            self.place_exit(underlying, "PostCutoffEntry", slot_id=_cutoff_slot_id)
                    self._notify(
                        f"\u2705 {cfg.broker.strategy_name}: pending BUY {order_id} reconciled "
                        f"for {underlying} @ \u20b9{price:.2f} (fill detected outside normal path)",
                        5,
                    )
                elif status in ("rejected", "cancelled", "canceled"):
                    with self._state.state_lock:
                        self._state.pending_entries.pop(order_id, None)
                    inf(f"[PENDING] BUY {order_id} {status}; removed from pending entries")
            elif square_off_hm and now_hm >= square_off_hm:
                # Cancel unfilled pending entry after square_off_time cutoff
                outcome = self._cancel_three_outcome(order_id, pending_entry)
                if outcome == "cancelled":
                    with self._state.state_lock:
                        self._state.pending_entries.pop(order_id, None)
                    inf(f"[PENDING] Cancelled unfilled entry {order_id} after cutoff")
                elif outcome == "reconciled":
                    with self._state.state_lock:
                        self._state.pending_entries.pop(order_id, None)
                    inf(f"[PENDING] Entry {order_id} reconciled via cancel-race fill after cutoff")
                else:
                    inf(f"[PENDING] Cannot confirm cancel for {order_id} after cutoff — keeping pending entry")

    def check_pending_exits(self) -> None:
        """Reconcile stale pending exit orders (safety net — runs every cycle)."""
        with self._state.state_lock:
            pending = list(self._state.pending_exits.items())
        for slot_id, pending_exit in pending:
            order_id = pending_exit.order_id
            raw = self._raw_order_status(order_id)
            with self._state.state_lock:
                pos = self._state.positions.slot(slot_id)
            if not pos:
                with self._state.state_lock:
                    self._state.pending_exits.pop(slot_id, None)
                continue
            underlying = pos.underlying
            opt_sym = pos.symbol
            if raw:
                status         = str(raw.get("order_status", "")).lower()
                executed_price = float(raw.get("average_price", 0) or 0)
                if status == "complete" and executed_price:
                    pnl = _calc_pnl(pos, executed_price)
                    pnl_sign = "✅" if pnl >= 0 else "❌"
                    norm_reason = ExitReason.normalize(pending_exit.reason)
                    self._finalize_exit(underlying, pos, executed_price, pnl, norm_reason,
                                        exit_price_source="broker_fill",
                                        opt_symbol=opt_sym, pop_pending_exit=True)
                    inf(f"[PENDING] EXIT {order_id} complete for {underlying} @ \u20b9{executed_price:.2f} | P&L \u20b9{pnl:.2f} | reason={norm_reason}")
                    self._notify(
                        f"{pnl_sign} {self.config.broker.strategy_name} EXIT confirmed\n"
                        f"{underlying} {pos.option_type} | {opt_sym}\n"
                        f"Exit \u20b9{executed_price:.2f} | Entry \u20b9{pos.entry_premium:.2f} | P&L \u20b9{pnl:.2f}\n"
                        f"Daily P&L \u20b9{self._risk.daily_pnl:.0f}",
                        8 if pnl < 0 else 6,
                    )
                elif status in ("rejected", "cancelled", "canceled"):
                    now_hm = get_ist_now().strftime("%H:%M")
                    is_past_cutoff = bool(self.config.market.square_off_time and now_hm >= self.config.market.square_off_time)
                    exit_filled_qty = int(raw.get("filled_quantity", 0) or raw.get("filled_qty", 0) or 0)
                    avg_price = float(raw.get("average_price", 0) or 0)

                    # F76: REST API never populates filled_qty — use avg_price as the fill signal
                    if avg_price > 0:
                            fill_qty = exit_filled_qty if exit_filled_qty > 0 else pos.remaining_qty
                            reduction = min(fill_qty, pos.remaining_qty)
                            rem = reduction
                            for tr in pos.tranches:
                                if rem <= 0:
                                    break
                                if not tr.is_exit_placed:
                                    chunk = min(rem, tr.qty)
                                    self.apply_confirmed_partial_exit(
                                        pos, tr, chunk, avg_price,
                                        ExitReason.FORCE_UNTRACK_EST,
                                        underlying, opt_sym,
                                    )
                                    rem -= chunk
                            # Re-place protection for residual
                            if pos.remaining_qty > 0:
                                for trr in pos.tranches:
                                    trr.sl_order_id = None
                                    trr.tgt_order_id = None
                                pos.sl_order_id = None
                                pos.tgt_order_id = None
                                self._place_protection_orders_sequential(
                                    underlying, pos, opt_sym, pos.remaining_qty,
                                    pos.sl, pos.tgt,
                                )
                            # Clean up pending exit
                            with self._state.state_lock:
                                self._state.pending_exits.pop(slot_id, None)
                                pos.exit_pending = False
                            with self._state.exit_lock:
                                self._state.exit_queue.discard(pos.slot_id)
                            inf(
                                f"[PENDING] EXIT {order_id} {status} — partial fill {reduction} "
                                f"@ \u20b9{avg_price:.2f} — qty reduced, protection re-placed"
                            )
                            continue

                    if is_past_cutoff:
                        best_price = self._resolve_option_ltp(underlying, opt_sym)
                        if best_price is not None:
                            pnl = _calc_pnl(pos, best_price)
                            journal_reason = ExitReason.FORCE_UNTRACK_EST
                        else:
                            best_price = 0.0
                            pnl = 0.0
                            journal_reason = ExitReason.FORCE_UNTRACK_UNKNOWN

                        self._finalize_exit(underlying, pos, best_price, pnl, journal_reason,
                                            exit_price_source="estimated",
                                            opt_symbol=opt_sym, pop_pending_exit=True)
                        inf(
                            f"[PENDING] EXIT {order_id} {status} after EOD cutoff — untracking {underlying} "
                            f"({journal_reason} price \u20b9{best_price:.2f} | P&L \u20b9{pnl:.0f})"
                        )
                    else:
                        with self._state.state_lock:
                            self._state.pending_exits.pop(slot_id, None)
                            pos.exit_pending = False
                        with self._state.exit_lock:
                            self._state.exit_queue.discard(pos.slot_id)
                        # F71: SELL was rejected zero-fill; place_exit already cancelled SL/TP
                        if pos.remaining_qty > 0:
                            for trr in pos.tranches:
                                trr.sl_order_id = None
                                trr.tgt_order_id = None
                            pos.sl_order_id = None
                            pos.tgt_order_id = None
                            self._place_protection_orders_sequential(
                                underlying, pos, opt_sym, pos.remaining_qty,
                                pos.sl, pos.tgt,
                            )
                        self._notify(
                            f"\U0001f6a8 {self.config.broker.strategy_name}: pending EXIT {order_id} {status} for {underlying} {opt_sym}\n"
                            "Position remains tracked; protection re-placed.",
                            9,
                        )


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  SECTION 12 — ORCHESTRATOR            OptionsBuyerEdgeBot + main()   ║
# ╚══════════════════════════════════════════════════════════════════════╝

class OptionsBuyerEdgeBot:
    """
    Thin orchestrator.  Creates all components, wires callbacks, then runs the
    two long-lived threads: WebSocket + strategy scan loop.
    """

    def __init__(self, cfg: BotConfig):
        self.config = cfg
        # Verbosity: 0=False (errors only, default) | 1=True (connection/auth/subscription) | 2=Debug (LTP/Quote/Depth updates)
        api_kwargs: dict = dict(api_key=cfg.broker.api_key, host=cfg.broker.api_host, verbose=2)
        if cfg.broker.ws_url:
            api_kwargs["ws_url"] = cfg.broker.ws_url   # explicit override; otherwise SDK derives from host
        self.client  = api(**api_kwargs)
        self.state   = BotState(chain_smooth_bars=cfg.market.chain_smooth_bars)
        self.risk    = RiskManager(self.client, cfg, self.state)
        self.fetcher = DataFetcher(self.client, cfg, notify_callback=self._send_alert)
        self.sl_policy      = EntryStopLossPolicy(self.fetcher, cfg)
        self.trail_engine   = TrailSLEngine(self.fetcher, cfg)
        self.scorer         = SignalEngine(cfg)
        self.strikes        = StrikeSelector(self.fetcher, cfg)
        self.ws             = WebSocketManager(self.client, cfg, self.state)
        self.orders         = OrderManager(self.client, cfg, self.state, self.risk, self.ws, self.fetcher, self._send_alert)
        # Wire callbacks and dependencies to break circular dependency + consolidate API calls
        self.ws.set_fetcher(self.fetcher)       # Reuse DataFetcher cache for delta in trailing SL
        self.ws.set_exit_callback(self.orders.place_exit)
        self.ws.set_notify_callback(self._send_alert)  # U-G: WS watchdog alert
        self.trail_engine.modify_callback = self.orders.modify_broker_sl
        self._last_pnl_alert_time: float = 0.0
        self._last_quote_refresh_ts: dict[str, float] = {}

    # ── Order-stream event dispatcher ────────────────────────────────────────
    def _handle_order_stream_event(self, event: dict) -> None:
        """Universal order-update event dispatcher.

        Three dispatch targets in priority order, then shadow log fallback:
          1. Entry completion  — match against pending_entries (existing)
          2. Exit completion   — match against pending_exits (stream-accelerated)
          3. Protection fill   — match sl_order_id / tgt_order_id against active
                                 positions (bypasses next polling cycle)
          4. Shadow log        — inf() for every unmatched event (replaces silent drop)

        The polling safety net (check_pending_entries / check_pending_exits /
        check_broker_order_fills) runs AFTER this in the same cycle and is
        idempotent — each _handle_broker_order_fill call exits cleanly if
        exit_pending / is_exit_placed is already set.
        """
        order_id = event.get("orderid")
        if not order_id:
            return
        os_status = str(event.get("order_status", "")).lower()
        dbg(f"[ORDER-STREAM] raw event: {event}")
        handled = False

        # ── 1. Entry completion (existing) ────────────────────────────
        with self.state.state_lock:
            pending = self.state.pending_entries.get(order_id)
        if pending:
            handled = True
            if (self.config.broker.order_stream_complete_entries
                    and os_status in ("complete", "filled", "executed")):
                filled_qty = int(event.get("filled_quantity", 0) or 0)
                avg_price  = float(event.get("average_price", 0) or 0)
                if filled_qty > 0 and avg_price > 0:
                    inf(f"[ORDER-STREAM] Confirmed fill for {order_id}: "
                        f"qty={filled_qty} @ {avg_price} — completing entry immediately")
                    self.orders.register_filled_entry(
                        pending.underlying, pending.symbol, filled_qty,
                        pending.spot, pending.direction, avg_price,
                        sl_pts=pending.sl_pts,
                        entry_delta=pending.entry_delta,
                        entry_conviction=pending.entry_conviction,
                        entry_sl_source=pending.entry_sl_source,
                    )
                    with self.state.state_lock:
                        self.state.pending_entries.pop(order_id, None)
                    return
            inf(
                f"[ORDER-STREAM] {order_id}: {os_status} "
                f"{event.get('symbol', '')} (entry)"
            )

        # ── 2. Exit completion (NEW) ──────────────────────────────────
        if not handled:
            with self.state.state_lock:
                pending_exit = self.state.pending_exits.get(order_id)
            if pending_exit:
                handled = True
                if os_status in ("complete", "filled", "executed"):
                    inf(f"[ORDER-STREAM] Exit confirmed: {order_id} "
                        f"{event.get('symbol', '')}")

        # ── 3. Protection order fill (NEW — LIMIT / SL-M matched to positions) ──
        if not handled and os_status in ("complete", "filled", "executed"):
            executed_price = float(event.get("average_price", 0) or 0)
            if executed_price > 0:
                for underlying, pos in self.state.positions.all_items():
                    if pos.exit_pending:
                        continue
                    for attr_name, raw_reason in (
                        ("sl_order_id",  "broker_sl_filled"),
                        ("tgt_order_id", "broker_target_filled"),
                    ):
                        # Position-level match (single-tranche path)
                        if getattr(pos, attr_name, None) == order_id:
                            inf(f"[ORDER-STREAM] Protection fill detected: "
                                f"{attr_name} {order_id} → handling immediately")
                            self.orders._handle_broker_order_fill(
                                underlying, pos, attr_name, order_id,
                                raw_reason, executed_price,
                            )
                            return
                        # Tranche-level match (multi-tranche path)
                        for tr in (pos.tranches or []):
                            if getattr(tr, attr_name, None) == order_id:
                                inf(f"[ORDER-STREAM] Protection fill detected: "
                                    f"{attr_name} t={tr.tranche_id} {order_id} → handling immediately")
                                self.orders._handle_broker_order_fill(
                                    underlying, pos, attr_name, order_id,
                                    raw_reason, executed_price, tr=tr,
                                )
                                return

        # ── 4. Shadow log for all unmatched events (NEW — replaces silent return) ──
        if not handled:
            inf(
                f"[ORDER-STREAM] {order_id}: {os_status} "
                f"{event.get('symbol', '')} qty={event.get('filled_quantity', 0)} "
                f"@ {event.get('average_price', 0)}"
            )

    def _send_alert(self, message: str, priority: int = 1) -> None:
        try:
            # self.client.whatsapp(message=message)
            self.client.telegram(username=self.config.broker.openalgo_username, message=message, priority=priority)
        except Exception as exc: err(f"[ALERT] Send error: ", exc)

    def _verify_registration(self) -> None:
        """Check strategy is recognized by the platform. Standalone scripts skip registration."""
        cfg = self.config
        try:
            resp = self.client.orderbook(strategy=cfg.broker.strategy_name)
            if isinstance(resp, dict) and resp.get("status") == "success":
                inf(f"[STARTUP] ✓ Strategy '{cfg.broker.strategy_name}' recognized")
                return
        except Exception:
            pass
        dbg(f"[STARTUP] Strategy '{cfg.broker.strategy_name}' not registered in platform (expected in standalone mode)")

    def _check_open_positions_on_startup(self) -> None:
        """Restore broker positions + resubscribe WS + reconcile protection orders.

        Reconciliation logic:
          Case A: SL ✓ Target ✓ → adopt both, no new orders
          Case B: SL ✗ Target ✓ → re-issue SL
          Case C: SL ✓ Target ✗ → re-issue target
          Case D: SL ✗ Target ✗ → re-issue both

        Orphan detection:
          Open SL/TGT orders with no matching position → cancel.
        """
        try:
            cfg = self.config
            resp = self.client.positionbook()
            if not isinstance(resp, dict) or resp.get("status") != "success":
                return
            positions = resp.get("data", []) or []
            if not positions:
                inf("[STARTUP] No open positions found in broker position book")
                return
            inf(f"[STARTUP] Found {len(positions)} broker position(s). Restoring...")

            # Fetch orderbook to find SL/TGT orders
            orderbook_resp = self.client.orderbook(strategy=cfg.broker.strategy_name)
            _ob_data = orderbook_resp.get("data", {}) if isinstance(orderbook_resp, dict) else {}
            open_orders = _ob_data.get("orders", []) if isinstance(_ob_data, dict) else []

            # ── Orphan detection ───────────────────────────────────
            # Collect symbols from broker positions, cancel orders for others
            pos_symbols: set[str] = set()

            for p in positions:
                sym = p.get("symbol", "")
                qty = int(p.get("quantity", 0) or 0)
                if sym and qty != 0:
                    pos_symbols.add(sym)

            orphan_orders_cancelled = 0
            for order in open_orders:
                o_sym = order.get("symbol", "")
                o_stat = str(order.get("order_status", "")).lower()
                if o_sym and o_sym not in pos_symbols and o_stat in ("pending", "open"):
                    oid = order.get("orderid")
                    if oid:
                        try:
                            resp_c = self.client.cancelorder(order_id=oid, strategy=cfg.broker.strategy_name)
                            if isinstance(resp_c, dict) and resp_c.get("status") in ("success", "cancelled"):
                                orphan_orders_cancelled += 1
                                inf(f"[STARTUP] Cancelled orphan order {oid} for {o_sym}")
                        except Exception:
                            pass
            if orphan_orders_cancelled:
                inf(f"[STARTUP] Cancelled {orphan_orders_cancelled} orphan order(s)")

            # ── Restore positions ──────────────────────────────────
            for p in positions:
                sym      = p.get("symbol", "")
                qty      = int(p.get("quantity", 0) or 0)
                entry_px = float(p.get("average_price", 0) or 0)
                if not sym or qty == 0 or entry_px <= 0:
                    continue

                # Robust underlying extraction
                underlying = ""
                m = re.match(r"^(.*?)(\d{1,2}[A-Z]{3}\d{2})(?:\d+(?:\.\d+)?)?(CE|PE|FUT)$", sym)
                if m:
                    underlying = m.group(1)
                if not underlying:
                    candidates = sorted(cfg.market.underlyings, key=len, reverse=True)
                    underlying = next((u for u in candidates if sym.startswith(u)), "")
                if not underlying:
                    inf(f"[STARTUP] Could not derive underlying from {sym} — skipping restore")
                    continue

                opt_type = "CE" if sym.endswith("CE") else ("PE" if sym.endswith("PE") else None)
                if not opt_type:
                    continue

                spot_q = self.fetcher.fetch_quote(underlying, self.fetcher.underlying_exchange(underlying))
                restored_spot = float(spot_q.get("ltp", 0) or 0)
                if restored_spot <= 0:
                    restored_spot = entry_px

                # NOTE: entry_conviction defaults to 0.0 (not persisted), making trail
                # activation more conservative post-restart (later trail activation).
                # Try to recover delta from option greeks for accurate tgt/act_mult.
                _restore_delta = None
                try:
                    _greeks = self.client.optiongreeks(symbol=sym, exchange=cfg.market.fno_exchange)
                    if isinstance(_greeks, dict):
                        _restore_delta = float(_greeks.get("delta", 0) or 0)
                except Exception:
                    pass
                _mm_label, _, tgt_mult, act_mult = EntryStopLossPolicy.get_moneyness_multipliers(_restore_delta)
                pos = OptionPosition.build(
                    underlying=underlying,
                    symbol=sym,
                    entry_premium=entry_px,
                    qty=qty,
                    option_type=opt_type,
                    sl=entry_px - cfg.entry.premium_stop_pts,
                    initial_sl=entry_px - cfg.entry.premium_stop_pts,
                    tgt=entry_px + (cfg.entry.premium_target_pts * tgt_mult),
                    spot_symbol=underlying,
                    spot_entry=restored_spot,
                    reward_dist=restored_spot * (cfg.entry.spot_reward_pct / 100.0),
                    entry_time=get_ist_now(),
                    entry_bucket=self.state.bucket_counter,
                    moneyness=_mm_label,
                    entry_delta=_restore_delta or 0.0,
                    trail_act_mult=act_mult,
                )

                # Reconstruct tranche structure (needed for tgt_order_id routing)
                pos.tranches = _build_tranches(pos, qty, cfg)

                # Query SL/TGT order IDs from orderbook
                sl_orders: list[dict] = []
                tgt_orders: list[dict] = []
                for order in open_orders:
                    o_sym = order.get("symbol", "")
                    o_stat = str(order.get("order_status", "")).lower()
                    o_type = str(order.get("pricetype", "")).lower()
                    if o_stat in ("pending", "open", "trigger pending") and o_sym == sym:
                        if "sl" in o_type:
                            sl_orders.append(order)
                        elif "limit" in o_type or o_type == "market":
                            tgt_orders.append(order)

                is_multi = len(pos.tranches) > 1
                if is_multi:
                    # Multi-tranche: match orders to tranches by quantity
                    for tr in pos.tranches:
                        for o in sl_orders:
                            if int(o.get("quantity", 0) or 0) == tr.qty and not tr.sl_order_id:
                                tr.sl_order_id = o.get("orderid")
                                break
                        for o in tgt_orders:
                            if int(o.get("quantity", 0) or 0) == tr.qty and not tr.tgt_order_id:
                                tr.tgt_order_id = o.get("orderid")
                                _order_price = float(o.get("price", 0) or 0)
                                if _order_price > 0:
                                    tr.tp_pts = _order_price - pos.entry_premium
                                    if tr.is_runner:
                                        pos.tgt = _order_price
                                        inf(f"[STARTUP] {underlying}: restored runner TGT ₹{_order_price:.2f}")
                                    else:
                                        inf(f"[STARTUP] {underlying}: restored tranche {tr.tranche_id} TGT ₹{_order_price:.2f}")
                                break
                    runner = pos.runner_tranche
                    if runner:
                        pos.sl_order_id = runner.sl_order_id
                else:
                    # Single-tranche: flat field assignment (backward compat)
                    for o in sl_orders:
                        pos.sl_order_id = o.get("orderid")
                    for o in tgt_orders:
                        pos.tgt_order_id = o.get("orderid")
                        _order_price = float(o.get("price", 0) or 0)
                        if _order_price > 0:
                            pos.tgt = _order_price
                            inf(f"[STARTUP] {underlying}: restored TGT price ₹{_order_price:.2f} from broker order")

                if pos.sl_order_id or pos.tgt_order_id:
                    pos.broker_protection = True
                    # Advance lifecycle: protection orders already active at broker
                    _advance_stage(pos, LifecycleStage.INITIAL_PROTECTED)

                # Register + resubscribe WS
                with self.state.state_lock:
                    self.state.positions.add(pos)
                self.state.snapshot_cache.set_option_symbol(underlying, sym)
                self.ws.subscribe(cfg.market.fno_exchange, sym)
                self.ws.subscribe_spot(underlying)
                inf(f"[STARTUP] ✓ Restored {underlying}: {sym} x{qty} @ ₹{entry_px:.2f} "
                      f"SL_id={pos.sl_order_id or 'MISSING'} TGT_id={pos.tgt_order_id or 'MISSING'}")

                # Re-issue missing protection orders
                if cfg.broker.broker_sl_orders and not cfg.broker.paper_trade:
                    sl_ok = bool(pos.sl_order_id)
                    tgt_ok = bool(pos.tgt_order_id)
                    if not sl_ok or not tgt_ok:
                        inf(f"[STARTUP] Reconciling protection orders for {underlying}: "
                              f"SL={'OK' if sl_ok else 'MISSING'} TGT={'OK' if tgt_ok else 'MISSING'}")
                        self.orders._place_protection_orders_sequential(underlying, pos, sym, qty, pos.sl, pos.tgt)
                        if pos.sl_order_id or pos.tgt_order_id:
                            pos.broker_protection = True
                            _advance_stage(pos, LifecycleStage.INITIAL_PROTECTED)

        except Exception as exc: err(f"[STARTUP] positionbook error: ", exc)

    def _check_max_hold(self) -> None:
        """Exit positions held > max_hold_minutes (theta decay guard). 0=disabled."""
        cfg = self.config
        if cfg.market.max_hold_minutes <= 0:
            return
        now = get_ist_now()
        with self.state.state_lock:
            positions = list(self.state.positions.all_items())
        for ul, pos in positions:
            held_minutes = (now - pos.entry_time).total_seconds() / 60.0
            if held_minutes < cfg.market.max_hold_minutes:
                continue
            with self.state.state_lock:
                if pos.exit_pending:
                    continue
                with self.state.exit_lock:
                    pos.exit_pending = True
            inf(
                f"[TIME-EXIT] {ul}: held {held_minutes:.0f}m "
                f">= max {cfg.market.max_hold_minutes}m — exiting (theta guard)"
            )
            self.orders.place_exit(ul, f"MaxHoldTime({cfg.market.max_hold_minutes}m)", slot_id=pos.slot_id)

    def _cleanup_stale_positions(self) -> None:
        """Force-remove positions stuck in the book after exit cleanup missed them.
        
        A position is stale if exit_pending is True but both the pending_exit
        entry and broker protection orders are gone — meaning the exit ran
        but the final positions.pop() was skipped (e.g. exception between
        pending_exits.pop and positions.pop in the poll-confirmed path).
        """
        stale = []
        with self.state.state_lock:
            for pos in self.state.positions.all_positions():
                if not pos.exit_pending:
                    continue
                if pos.slot_id in self.state.pending_exits:
                    continue
                if pos.sl_order_id or pos.tgt_order_id:
                    continue
                stale.append(pos)
            for pos in stale:
                _est_exit = pos.sl or pos.entry_premium
                _est_pnl = _calc_pnl(pos, _est_exit)
                self.orders._write_journal(
                    pos.underlying, pos, _est_exit, _est_pnl, "orphan_cleanup",
                    exit_price_source="estimated", record_type="orphan_cleanup",
                )
                inf(f"[CLEANUP] Force-removing stale position {pos.symbol} ({pos.slot_id}) — "
                    f"exit already processed, wrote orphan_cleanup row. If PnL seems missing check broker.")
                _advance_stage(pos, LifecycleStage.CLOSED)
                self.state.positions.pop(pos.slot_id, None)
                self.state.pending_opposite_exit.discard(pos.underlying)
                with self.state.exit_lock:
                    self.state.exit_queue.discard(pos.slot_id)

    def _send_live_pnl_alert(self, open_positions: list[OptionPosition]) -> None:
        """Fetch live positions and dispatch a single-line active PNL alert."""
        try:
            broker_positions: dict[str, dict] = {}
            if not self.config.broker.paper_trade and hasattr(self.client, "positionbook"):
                resp = self.client.positionbook()
                if isinstance(resp, dict) and resp.get("status") == "success":
                    for p in resp.get("data", []):
                        sym = p.get("symbol", "")
                        if sym:
                            broker_positions[sym] = p
                else:
                    err(f"[PNL] Broker positionbook call failed: {resp}")

            for pos in open_positions:
                pnl = 0.0
                if self.config.broker.paper_trade:
                    snap = self.state.snapshot_cache.get(pos.underlying)
                    if snap and snap.option_ltp is not None:
                        pnl = _calc_pnl(pos, snap.option_ltp)
                        inf(f"[PNL - CACHE] ltp=₹{snap.option_ltp:.2f} entry=₹{pos.entry_premium:.2f} qty={pos.remaining_qty} pnl=₹{pnl:.2f}")
                    else:
                        err(f"[PNL - CACHE] no snapshot data. snap_exists={snap is not None} opt_ltp={snap.option_ltp if snap else 'None'}")
                elif pos.symbol in broker_positions:
                    p = broker_positions.get(pos.symbol, {})
                    pnl = float(p.get("pnl", 0) or 0)
                    inf(f"[PNL - LIVE] pnl=₹{pnl:.2f} symbol={pos.symbol}")
                else:
                    err(f"[PNL - LIVE] {pos.underlying}: symbol={pos.symbol} NOT in broker data. broker_symbols={list(broker_positions.keys())} raw_entry={broker_positions.get(pos.symbol, {})}")

                hold_mins = max(0, int((get_ist_now() - pos.entry_time).total_seconds() / 60))
                hours = hold_mins // 60
                mins  = hold_mins % 60
                hold_str = f"{hours}h{mins}m" if hours > 0 else f"{mins}m"

                side  = pos.option_type.upper()
                emoji = "🟢" if pnl >= 0 else "🔴"
                sign  = "+" if pnl >= 0 else ""
                self._send_alert(f"{emoji} {pos.underlying} {side} | PNL: ₹{sign}{pnl:.0f} | Hold: {hold_str}", 3)
                
        except Exception as exc: err(f"[PNL REPORT] Error checking active PNL: ", exc)

    def _is_market_hours(self) -> bool:
        hm = int(get_ist_now().strftime("%H%M"))
        return MARKET_HOURS_START <= hm <= MARKET_HOURS_END

    def _print_startup_info(self) -> None:
        cfg = self.config
        inf("=" * 70)
        inf(f"  {cfg.broker.strategy_name}{'  [PAPER TRADE]' if cfg.broker.paper_trade else ''}")
        _sdk_ver = getattr(openalgo, "__version__", "?")
        inf(f"  SDK version     : openalgo {_sdk_ver}")
        inf("=" * 70)
        inf(f"  API Host        : {cfg.broker.api_host}")
        inf(f"  WebSocket URL   : {cfg.broker.ws_url if cfg.broker.ws_url else '(SDK auto-derive from host)'}")
        inf(f"  Underlyings     : {', '.join(cfg.market.underlyings)}")
        inf(f"  FNO Exchange    : {cfg.market.fno_exchange}")
        inf(f"  Min Score       : {cfg.entry.min_score} | Max Trap: {cfg.entry.max_trap}")
        inf(f"  SL Points       : {cfg.entry.premium_stop_pts} (Phase A hard SL fallback)")
        inf(f"  Phase A SL      : moneyness-adapted from entry_delta or fallback to PREMIUM_STOP_PTS")
        _max_pts_str = f" (hard cap {cfg.trail.activate_at_max_pts:.0f}pts)" if cfg.trail.activate_at_max_pts > 0 else ""
        inf(
            f"  Phase B Trail   : tracking={cfg.trail.tracking_mode}  method={cfg.trail.sl_method}  "
            f"activate={cfg.trail.activate_at_pct:.0f}%{_max_pts_str}"
        )
        if cfg.trail.sl_method == "fixed_pct":
            inf(f"  Trail Step      : {cfg.trail.step_pct:.1f}% of base distance (cap: 50% of entry premium)")
        elif cfg.trail.sl_method == "fixed_pts":
            inf(f"  Trail Step      : {cfg.trail.step_pts:.1f} raw pts (no scaling — use for high-VIX/high-premium options)")
        elif cfg.trail.sl_method == "atr":
            inf(f"  Trail ATR       : period={cfg.trail.atr_period}, mult={cfg.trail.atr_mult}, "
                  f"buffer={cfg.trail.atr_activation_buffer_pts:.1f}pts")
        elif cfg.trail.sl_method == "delta":
            inf(
                f"  Trail Delta     : ITM={cfg.trail.delta_itm_step_pct:.0f}%  "
                f"ATM={cfg.trail.delta_atm_step_pct:.0f}%  OTM={cfg.trail.delta_otm_step_pct:.0f}%  (cap: 50% of entry premium)"
            )
        elif cfg.trail.sl_method == "key_level":
            style = cfg.trail.key_level_trail_style
            if style == "capture_pct":
                inf(f"  Key Level Trail : capture_pct={cfg.trail.key_level_capture_pct:.0f}% per level, spacing={cfg.trail.key_level_spacing}")
            else:
                inf(f"  Key Level Trail : fixed={cfg.trail.key_level_fixed_pts:.0f}pts per level, spacing={cfg.trail.key_level_spacing}")
            inf(f"  Key Level BE    : after {cfg.trail.key_level_breakeven_after_levels} level(s)")
        inf(f"  Activation Lock : lock_pct={cfg.trail.activation_lock_pct:.0%} of target gain at activation")
        inf(f"  Long Only Mode  : {cfg.entry.long_only_mode}")
        inf(f"  Broker SL Orders: {cfg.broker.broker_sl_orders}")
        inf(f"  DTE Range       : {cfg.market.dte_min} – {cfg.market.dte_max} days")
        inf(f"  Candle Interval : {cfg.market.candle_interval}")
        inf(f"  Check Interval  : {cfg.market.signal_check_interval}s")
        _os_auto = " (auto-complete entries)" if cfg.broker.order_stream_complete_entries else ""
        _os_plat = " [platform:READY]" if cfg.broker.order_updates_enabled else " [platform:UNAVAIL]"
        inf(f"  Order Stream    : {'ENABLED' if cfg.broker.order_stream_enabled else 'disabled'}{_os_auto}{_os_plat}")
        inf("-" * 70)
        inf(f"  [RISK GATES]")
        inf(f"  Max Trades/Day  : {cfg.risk.max_trades_per_session or 'unlimited'}")
        inf(f"  Max Consec Loss : {cfg.risk.max_consecutive_losses}")
        inf(f"  Daily Loss Limit: ₹{cfg.risk.max_daily_loss_amount:.0f}"
              + (f" | {cfg.risk.max_daily_loss_pct:.1f}%" if cfg.risk.max_daily_loss_pct > 0 else ""))
        inf(f"  Daily Profit Tgt: {'disabled' if cfg.risk.max_daily_profit_amount <= 0 else f'₹{cfg.risk.max_daily_profit_amount:.0f}'}")
        inf(f"  Entry Cooldown  : {cfg.risk.entry_cooldown_secs}s per underlying")
        inf(f"  [TIMING]")
        inf(f"  No New Entries  : after {cfg.market.no_new_trade_after} IST")
        inf(f"  EOD Square-Off  : {cfg.market.square_off_time} IST")
        inf(f"  Max Hold Time   : {'disabled' if cfg.market.max_hold_minutes <= 0 else f'{cfg.market.max_hold_minutes}m per trade'}")
        if cfg.journal.trade_journal_path:
            inf(f"  Trade Journal   : {os.path.abspath(cfg.journal.trade_journal_path)}")
        if cfg.broker.paper_trade:
            inf(f"\n  *** PAPER TRADE MODE — no real orders will be sent ***")
        inf("=" * 70)

    def scan_underlying(self, symbol: str) -> None:
        """Full scan pipeline for one underlying.  Called from strategy thread."""
        cfg    = self.config
        state  = self.state
        orders = self.orders

        # NEW-2: skip scan while opposite-side exit is in progress
        if symbol in state.pending_opposite_exit:
            return

        # Fast path: skip signal compute if entry impossible AND no management feature needs scoring
        _ul_count = state.position_book.count(symbol)
        _needs_signal_for_management = _ul_count > 0 and (
            cfg.position.signal_parallel_exit
            or cfg.position.opposite_side_exit_on_signal
            or cfg.tranche.enabled
        )
        if not _needs_signal_for_management:
            if _ul_count >= cfg.position.max_positions_per_underlying:
                return
            _total_count = state.position_book.count()
            if _total_count >= cfg.position.max_total_positions:
                return

        # Keep greeks cache scoped to this scan cycle for fresh yet deduplicated API calls.
        self.fetcher.clear_greeks_cache(symbol)

        def _log_greeks_perf(
            stage:     str,
            sep_count: int = 0,
            sep_char:  str = "━",
        ) -> None:
            """Log greeks cache performance for this scan-cycle stage.

            Args:
                stage:     Execution stage label  (e.g. 'no-execute', 'entry-order').
                sep_count: When > 0 prints a closing separator of this many `sep_char`
                           characters directly after the perf line, letting callers
                           consolidate  ``_log_greeks_perf(...)``  +  separator  into
                           one call instead of two.
                sep_char:  Separator character (default: ━).
            """
            perf = self.fetcher.greeks_perf_snapshot(symbol)
            dbg(
                f"  [PERF] {symbol} [{stage}] greeks: "
                f"hit={perf['hits']} miss={perf['misses']} "
                f"api_calls={perf['api_calls']} hit_rate={perf['hit_rate']}% "
                f"cache_size={perf['cache_size']}"
            )
            if sep_count > 0:
                inf(f"  {sep_char * sep_count}\n")

        # U-C: Session-Aware Min Score — use global helper for clean, testable logic
        _ist_now          = get_ist_now()
        effective_min_score, _session_label = _effective_min_score(_ist_now, cfg)
        if _session_label != "mid-session":
            inf(f"[SCAN] {symbol}: session regime [{_session_label}]")

        spot_q = self.fetcher.fetch_quote(symbol, self.fetcher.underlying_exchange(symbol))
        spot   = float(spot_q.get("ltp", 0) or 0)
        if not spot:
            inf(f"[SCAN] {symbol}: no spot LTP")
            return

        expiry = self.fetcher.fetch_target_expiry(symbol)
        if not expiry:
            expiry = self.fetcher.pick_nearest_expiry(symbol)
            if expiry:
                dbg(f"[SCAN] {symbol}: nearest expiry {expiry} (outside DTE range)")
            else:
                inf(f"[SCAN] {symbol}: no expiry available — skip")
                return

        # Fetch option chain
        chain_rows, expiry_used = self.fetcher.fetch_option_chain(symbol, expiry)
        if not chain_rows:
            inf(f"[SCAN] {symbol}: empty option chain")
            return
        if expiry_used and not expiry:
            expiry = expiry_used

        chain_hist = state.get_chain_history(symbol)
        chain_hist.append(chain_rows)
        smoothed = OIFlowAnalyzer.smooth_chain_rows(list(chain_hist))
        if not smoothed:
            return

        df_spot = self.fetcher.fetch_spot_candles(symbol)

        strikes = sorted(set(r["strike"] for r in smoothed))
        atm_k   = min(strikes, key=lambda x: abs(x - spot))
        atm_row = next((r for r in smoothed if r.get("strike") == atm_k), {})
        atm_ce_ltp  = float(atm_row.get("ce_ltp", 0) or 0)
        atm_pe_ltp  = float(atm_row.get("pe_ltp", 0) or 0)

        # Prefetch greeks only for symbols that will be consumed in this scan:
        # 1) ATM CE/PE (L3 delta component)
        # 2) Strikes near ATM with OI > 0 (GEX gamma profile)
        # 3) Liquidity-qualified strikes near ATM (strike selection delta gate)
        # Limit to near-ATM strikes to stay within rate budget.
        _atm_idx = strikes.index(atm_k)
        _near_strikes = set(strikes[max(0, _atm_idx - cfg.market.strike_count):
                                     _atm_idx + cfg.market.strike_count + 1])
        option_symbols: list[str] = []
        if atm_row.get("ce_symbol"):
            option_symbols.append(atm_row.get("ce_symbol"))
        if atm_row.get("pe_symbol"):
            option_symbols.append(atm_row.get("pe_symbol"))

        for row in chain_rows:
            if row.get("strike") not in _near_strikes:
                continue
            if float(row.get("ce_oi", 0) or 0) > 0 and row.get("ce_symbol"):
                option_symbols.append(row.get("ce_symbol"))
            if float(row.get("pe_oi", 0) or 0) > 0 and row.get("pe_symbol"):
                option_symbols.append(row.get("pe_symbol"))

        for row in smoothed:
            if row.get("strike") not in _near_strikes:
                continue
            if (
                float(row.get("ce_oi", 0) or 0) >= cfg.entry.min_oi_filter
                and float(row.get("ce_volume", 0) or 0) >= cfg.entry.min_vol_filter
                and row.get("ce_symbol")
            ):
                option_symbols.append(row.get("ce_symbol"))
            if (
                float(row.get("pe_oi", 0) or 0) >= cfg.entry.min_oi_filter
                and float(row.get("pe_volume", 0) or 0) >= cfg.entry.min_vol_filter
                and row.get("pe_symbol")
            ):
                option_symbols.append(row.get("pe_symbol"))

        self.fetcher.batch_prefetch_option_greeks(symbol, option_symbols)

        # ── Per-strike Greeks harvest (zero extra API calls — reads _greeks_cache) ──
        _now_ts = time.time()
        for row in smoothed:
            _strike = row.get("strike")
            if _strike is None:
                continue
            _ce_sym = row.get("ce_symbol")
            _pe_sym = row.get("pe_symbol")
            _ce_g = self.fetcher._fetch_option_greeks_cached(symbol, _ce_sym) if _ce_sym else None
            _pe_g = self.fetcher._fetch_option_greeks_cached(symbol, _pe_sym) if _pe_sym else None
            if _ce_g is None and _pe_g is None:
                continue
            _snap: dict[str, Any] = {"timestamp": _now_ts}
            if _ce_g is not None:
                _ce_iv = _ce_g.get("iv")
                _snap["ce_delta"]   = _ce_g.get("delta")
                _snap["ce_iv_rank"] = (
                    self.scorer.iv_rank(_ce_iv, cfg.entry.iv_52w_low, cfg.entry.iv_52w_high)
                    if _ce_iv and _ce_iv > 0 else None
                )
            if _pe_g is not None:
                _pe_iv = _pe_g.get("iv")
                _snap["pe_delta"]   = _pe_g.get("delta")
                _snap["pe_iv_rank"] = (
                    self.scorer.iv_rank(_pe_iv, cfg.entry.iv_52w_low, cfg.entry.iv_52w_high)
                    if _pe_iv and _pe_iv > 0 else None
                )
            state.get_greeks_history(symbol, _strike).append(_snap)

        straddle_price = (atm_ce_ltp + atm_pe_ltp) if (atm_ce_ltp and atm_pe_ltp) else None
        # Only compare premium expansion if the ATM strike is the same as the previous scan.
        # If the ATM strike shifted, straddle velocity is undefined/reset for this bar.
        prev_str = state.prev_straddle.get(symbol)
        prev_straddle_price = None
        if isinstance(prev_str, dict) and prev_str.get("strike") == atm_k:
            prev_straddle_price = prev_str.get("price")
        if straddle_price is not None:
            state.prev_straddle[symbol] = {"strike": atm_k, "price": straddle_price}

        sf_ltp   = self.fetcher.fetch_synthetic_future(symbol, expiry)
        prev_sf_ltp  = state.prev_sf.get(symbol)
        prev_spot_ltp = state.prev_spot.get(symbol)
        if sf_ltp:
            state.prev_sf[symbol] = sf_ltp
        state.prev_spot[symbol] = spot

        ce_delta, pe_delta = self.fetcher.fetch_atm_greeks(
            symbol,
            atm_row.get("ce_symbol"),
            atm_row.get("pe_symbol"),
        )
        gex_levels = self.fetcher.fetch_gex_levels(symbol, chain_rows, spot)

        ce_bid = float(atm_row.get("ce_bid", 0) or 0) or None
        ce_ask = float(atm_row.get("ce_ask", 0) or 0) or None
        pe_bid = float(atm_row.get("pe_bid", 0) or 0) or None
        pe_ask = float(atm_row.get("pe_ask", 0) or 0) or None

        # Fetch separate CE and PE IV Ranks (best fit = lower = cheaper for buying)
        iv_ranks = self.fetcher.fetch_atm_iv_ranks(
            symbol,
            ce_symbol=atm_row.get("ce_symbol"),
            pe_symbol=atm_row.get("pe_symbol"),
        )
        ce_iv_rank = iv_ranks.get("ce_iv_rank")
        pe_iv_rank = iv_ranks.get("pe_iv_rank")
        best_fit_iv_side = iv_ranks.get("best_fit")
        # Legacy fallback for backward compatibility
        iv_rank_val = ce_iv_rank if (ce_iv_rank is not None and pe_iv_rank is None) else (pe_iv_rank if pe_iv_rank is not None else None)

        # Smooth greeks across last N scan cycles — per-strike deque, no cross-contamination
        _sg = _smooth_greeks(
            state.get_greeks_history(symbol, atm_k),
            lookback=3,
            max_age_secs=cfg.market.greeks_smooth_max_age,
        )
        ce_delta = _sg.get("ce_delta", ce_delta) or ce_delta
        pe_delta = _sg.get("pe_delta", pe_delta) or pe_delta
        ce_iv_rank = _sg.get("ce_iv_rank", ce_iv_rank)
        pe_iv_rank = _sg.get("pe_iv_rank", pe_iv_rank)
        # Recompute derived values after smoothing
        iv_rank_val = ce_iv_rank if (ce_iv_rank is not None and pe_iv_rank is None) else (pe_iv_rank if pe_iv_rank is not None else None)

        result = self.scorer.score(
            spot=spot,
            df_spot=df_spot,
            chain_rows=smoothed,
            atm_ce_ltp=atm_ce_ltp,
            atm_pe_ltp=atm_pe_ltp,
            iv_rank=iv_rank_val,
            straddle_price=straddle_price,
            prev_straddle_price=prev_straddle_price,
            sf_ltp=sf_ltp,
            ce_bid=ce_bid,
            ce_ask=ce_ask,
            pe_bid=pe_bid,
            pe_ask=pe_ask,
            ce_delta=ce_delta,
            pe_delta=pe_delta,
            gex_levels=gex_levels,
            min_score_override=effective_min_score,
            prev_spot=prev_spot_ltp,
            prev_sf_ltp=prev_sf_ltp,
            ce_iv_rank=ce_iv_rank,
            pe_iv_rank=pe_iv_rank,
            best_fit_iv_side=best_fit_iv_side,
        )
        state.latest_signals[symbol] = (result, time.time())

        # ── Formatted scoring panel ──────────────────────────────────────────
        _s        = result.score
        _trap     = result.trap_score
        _signal   = result.signal
        _dir_ico  = "▲" if _s > 0 else ("▼" if _s < 0 else "◆")
        _sig_ico  = "✔" if _signal == "EXECUTE" else ("⚡" if _signal == "WATCH" else "✘")
        _nfill    = int(abs(_s) / 100 * 16)
        _score_bar = "█" * _nfill + "░" * (16 - _nfill)
        _sep        = "━" * 79
        _now_hdr    = get_ist_now()   # TZ-safe IST — works on Docker/UTC and local hosts
        _time_str   = _now_hdr.strftime("%H:%M:%S")
        _spot_fmt   = f"{spot:,.0f}" if spot else ""
        _header_txt = f"  ━━ SCAN · {symbol} · {_spot_fmt} · {_time_str}  "
        inf(_header_txt + "━" * max(1, 79 - len(_header_txt)))
        inf(f"      {_dir_ico} {result.label:<10}  score {_s:+d}/100  {_score_bar}  trap {_trap}/100   {_sig_ico} {_signal}")
        inf(f"  {_sep}")
        _cbar_w = 8
        for c in result.components:
            _cfill = int(abs(c.score) / max(c.score_max, 0.01) * _cbar_w)
            _cbar  = "█" * _cfill + "░" * (_cbar_w - _cfill)
            inf(f"     {c.score:+.0f}/{c.score_max:.0f}  {_cbar}  {c.label:<20} {c.note}")
        if result.trap_reasons:
            inf(f"  ⚠ TRAP {_trap}  ·  {'  ·  '.join(result.trap_reasons)}")

        if _signal != "EXECUTE":
            inf(
                f"  {_sig_ico} {_signal}  —  not executing  "
                f"(score {abs(_s)}/100, min {effective_min_score})"
            )
            _log_greeks_perf("no-execute", sep_count=79)
            return

        # ✔ EXECUTE path — separator printed AFTER every blocking guard below
        inf(f"  ✔ EXECUTE  {_dir_ico}  {result.direction}")

        # V2-A6: Signal parallel sync — exit opposing active positions on new EXECUTE signal
        if cfg.position.signal_parallel_exit:
            _sig_dir = result.direction
            if _sig_dir is None:
                _sig_dir = "CE" if result.score > 0 else ("PE" if result.score < 0 else None)
            if _sig_dir and abs(result.score) >= effective_min_score:
                for _pos in state.position_book.get_all(symbol):
                    if not _pos.exit_pending and _pos.option_type != _sig_dir:
                        inf(f"[SIGNAL-SYNC] {symbol}: signal={_sig_dir}({result.score}) vs position={_pos.option_type} — exiting")
                        with state.state_lock:
                            _pos.exit_pending = True
                        orders.place_exit(symbol, "opposite_signal_sync", slot_id=_pos.slot_id)

        direction = result.direction
        if cfg.entry.long_only_mode and direction not in ("CE", "PE"):
            _log_greeks_perf("blocked-direction", sep_count=79)
            return
        if direction is None:
            _log_greeks_perf("neutral-direction", sep_count=79)
            return

        # V2-A1: Log signal context vs open positions
        for _pos in state.position_book.get_all(symbol):
            if not _pos.exit_pending:
                _pos_dir = _pos.option_type
                if direction != _pos_dir:
                    inf(f"[SIGNAL] {symbol}: signal={direction}({result.score}) vs position={_pos_dir} — OPPOSING")

        # V2-A5: Signal-deterioration tranche exit
        if cfg.tranche.enabled:
            for _pos in state.position_book.get_all(symbol):
                if _pos.exit_pending or len(_pos.open_tranches) < 2:
                    continue
                _pos_dir = _pos.option_type
                if direction != _pos_dir:
                    for _tr in _pos.open_tranches:
                        if _tr.is_runner or _tr.is_exit_placed:
                            continue
                        inf(f"[TRANCH-SIGNAL] {symbol}: signal reversed ({_pos_dir}\u2192{direction}) — exiting {_tr.tranche_id}")
                        orders._exit_non_runner_tranche(symbol, _pos, _tr, "signal_reversal")
                        break

        # V2: multi-position entry guard
        _can_enter, _guard_reason = state.position_book.can_enter(symbol, direction, cfg)
        if not _can_enter:
            inf(f"[SCAN] {symbol} blocked by position guard: {_guard_reason}")
            _log_greeks_perf(_guard_reason.replace(" ", "-"), sep_count=79)
            return
        if _guard_reason == "opposite_exit_pending":
            _opp_slots: list[str] = []
            with state.state_lock:
                for _opp in state.position_book.get_all(symbol):
                    if _opp.core.option_type != direction and not _opp.exit_pending:
                        _opp.exit_pending = True
                        _opp_slots.append(_opp.slot_id)
            state.pending_opposite_exit.add(symbol)
            for _sid in _opp_slots:
                orders.place_exit(symbol, "opposite_side_signal", slot_id=_sid)
            inf(f"[SCAN] {symbol}: deferring entry — triggered opposite-side exit")
            _log_greeks_perf("opposite-exit-pending", sep_count=79)
            return

        # V2-A4: Same-direction add conviction gate
        if _guard_reason == "ok" and state.position_book.has_same_direction(symbol, direction):
            _conviction = abs(result.score) / 100.0
            if _conviction < cfg.position.same_direction_min_conviction:
                inf(f"[SCAN] {symbol}: same-direction add skipped — conviction {_conviction:.2f} < min {cfg.position.same_direction_min_conviction}")
                _log_greeks_perf("low-conviction-add", sep_count=79)
                return

        best = self.strikes.select_best(
            symbol, smoothed, spot, direction, iv_rank_val,
            signal_score=result.score,
            gex_levels=gex_levels,
        )
        if best is None:
            best = StrikeSelector.simple_otm(smoothed, spot, direction, cfg.market.otm_offset)
            if best:
                inf(f"[SCAN] {symbol}: using simple OTM fallback strike {best.get('strike')}")
            else:
                inf(f"[SCAN] {symbol}: no qualifying strike found — skip")
                _log_greeks_perf("no-strike", sep_count=79)
                return

        opt_key    = "ce_symbol" if direction == "CE" else "pe_symbol"
        opt_symbol = best.get(opt_key)
        if not opt_symbol:
            inf(f"[SCAN] {symbol}: strike {best.get('strike')} has no {direction} symbol — skip")
            _log_greeks_perf("missing-option-symbol", sep_count=79)
            return

        if cfg.entry.strike_loss_guard_enabled and cfg.entry.max_strike_cum_loss_pts > 0:
            cum_loss = state.strike_cum_loss_pts(opt_symbol, direction)
            if cum_loss >= cfg.entry.max_strike_cum_loss_pts:
                inf(
                    f"[SCAN] {symbol}: {opt_symbol} {direction} cumulative loss "
                    f"{cum_loss:.1f}pts >= cap {cfg.entry.max_strike_cum_loss_pts:.1f}pts — skip"
                )
                _log_greeks_perf("strike-loss-guard", sep_count=79)
                return

        if cfg.entry.max_entry_spread_pct > 0:
            bid_key = "ce_bid" if direction == "CE" else "pe_bid"
            ask_key = "ce_ask" if direction == "CE" else "pe_ask"
            bid = float(best.get(bid_key, 0) or 0)
            ask = float(best.get(ask_key, 0) or 0)
            mid = (bid + ask) / 2 if (bid and ask) else 0.0
            if mid > 0 and ask > bid:
                live_spread_pct = (ask - bid) / mid * 100
                if live_spread_pct > cfg.entry.max_entry_spread_pct:
                    inf(
                        f"[SCAN] {symbol}: entry blocked — spread {live_spread_pct:.1f}% "
                        f"> max {cfg.entry.max_entry_spread_pct:.1f}% (bid={bid:.2f}, ask={ask:.2f})"
                    )
                    _log_greeks_perf("hard-spread-block", sep_count=79)
                    return

        est_premium = float(best.get("ce_ltp" if direction == "CE" else "pe_ltp", 0) or 0)
        base_sl_pts, entry_sl_source = self.sl_policy.resolve_entry_sl_points(
            opt_symbol,
            df_spot,
            entry_delta=best.get("_abs_delta"),
            est_premium=est_premium,
        )

        # ── Conviction scalar (single source of truth for all adaptive risk) ──────
        # Maps [min_score, 100] → [0.0, 1.0]. Used for SL, BE, and trail adaptation.
        entry_conviction = max(0.0, min(
            (abs(result.score) - cfg.entry.min_score) / max(100.0 - cfg.entry.min_score, 1.0),
            1.0,
        ))

        # ── Part 2: Conviction-Driven SL Sizing + Dynamic Cap ──────────────
        # Chain: base → conviction → floor → dynamic ceiling (applied LAST).
        _sl_raw_conv = min(abs(result.score) / 100.0, 1.0)
        sl_factor    = 1.10 - (_sl_raw_conv * 0.20)

        entry_sl_pts = base_sl_pts * sl_factor
        entry_sl_pts = max(5.0, entry_sl_pts)

        # Dynamic ceiling: absolute cap (max_sl_pts or premium_stop_pts sentinel)
        # optionally tightened by a premium-proportional ratio
        _effective_ceiling = cfg.entry.max_sl_pts if cfg.entry.max_sl_pts > 0 else cfg.entry.premium_stop_pts
        if cfg.entry.max_sl_premium_ratio > 0:
            _premium_cap = est_premium * (cfg.entry.max_sl_premium_ratio / 100.0)
            _effective_ceiling = min(_effective_ceiling, _premium_cap)
        entry_sl_pts = min(entry_sl_pts, _effective_ceiling)  # ceiling — applied once, LAST

        inf(
            f"[SCAN] {symbol}: Phase A initial SL source={entry_sl_source} "
            f"base={base_sl_pts:.2f} × factor={sl_factor:.2f} "
            f"(conv={entry_conviction:.2f}) → clamped={entry_sl_pts:.2f}pts (ceiling={_effective_ceiling:.0f})"
            )

        lotsize = int(best.get("lotsize", 1) or 1)
        effective_mult = self.risk.effective_lot_multiplier(cfg.entry.lot_multiplier)
        fixed_qty = max(1, effective_mult) * lotsize
        if cfg.entry.adaptive_sizing_enabled:
            inf(
                f"[SCAN] {symbol}: lot_mult={effective_mult} "
                f"(base={cfg.entry.lot_multiplier}, wins={self.risk.consecutive_wins})"
            )

        available  = self.risk.available_capital()
        if cfg.entry.risk_based_sizing_enabled:
            risk_cap      = available * (cfg.entry.risk_percent / 100.0)
            risk_per_unit = entry_sl_pts
            risk_qty      = int(risk_cap / risk_per_unit) if risk_per_unit > 0 else 0
            risk_qty      = (risk_qty // lotsize) * lotsize if lotsize > 0 else risk_qty
            qty = min(fixed_qty, risk_qty) if risk_qty > 0 else 0
            if qty <= 0:
                min_risk_pct = (entry_sl_pts * lotsize / available * 100) if available > 0 else 0.0
                inf(
                    f"[SCAN] {symbol}: qty=0 — 1 lot risk exceeds cap "
                    f"(stop ₹{entry_sl_pts:.2f} pts × {lotsize} units = ₹{entry_sl_pts*lotsize:.0f}/lot, "
                    f"risk cap ₹{risk_cap:.0f} @ {cfg.entry.risk_percent}% of ₹{available:.0f} available; "
                    f"need RISK_PERCENT≥{min_risk_pct:.1f}%)"
                )
                _log_greeks_perf("qty-zero", sep_count=79)
                return
        else:
            qty = fixed_qty
            inf(f"[SCAN] {symbol}: qty={qty} (risk-based sizing disabled — using fixed lot_mult)")

        # ── WS connectivity guard — must run last so all preflight logs are printed ──
        # When WS is down, trail/target detection is blind; broker SL-M provides minimum protection.
        # Block entry entirely if broker_sl_orders=False (no fallback protection at all).
        if not self.ws.is_connected():
            if not cfg.broker.broker_sl_orders:
                inf(
                    f"[SCAN] {symbol}: entry BLOCKED — WS disconnected and broker_sl_orders=False. "
                    f"No protection available."
                )
                _log_greeks_perf("ws-dead-no-broker-sl", sep_count=79)
                return
            inf(
                f"[RISK] {symbol}: WS disconnected — entry allowed (broker SL-M active). "
                f"Trail/target hit detection blind until WS recovers."
            )

        # All guards passed — close the scan block then log intent
        _log_greeks_perf("entry-preflight", sep_count=79)
        inf(
            f"[SCAN] {symbol}: placing {direction} entry | strike {best.get('strike')} "
            f"| {opt_symbol} x{qty}"
        )

        entry_allowed, entry_reason = self.risk.check_entry_gates(symbol)
        if not entry_allowed:
            inf(f"[SCAN] {symbol}: entry blocked — {entry_reason}")
            _log_greeks_perf("entry-gate-blocked", sep_count=79)
            return
        _log_greeks_perf("entry-order")
        orders.place_entry(
            symbol, opt_symbol, qty, spot, direction,
            sl_pts=entry_sl_pts,
            entry_delta=best.get("_abs_delta"),
            entry_conviction=entry_conviction,
            entry_sl_source=entry_sl_source,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # SNAPSHOT FRESHNESS: producer-failure fallback
    # ──────────────────────────────────────────────────────────────────────────

    def _refresh_stale_snapshots(self) -> None:
        """For every open position whose snapshot is stale, fetch a broker quote
        and update SnapshotCache.  WS-dead → still have data for trail/PNL.

        Guards:
          1. Re-check freshness right before write — if a WS tick arrived between
             stale detection and quote response, don't overwrite the newer data.
          2. Per-underlying cooldown — only one refresh per stale_timeout window
             to avoid quote API rate limiting.
        """
        cfg = self.config
        timeout = cfg.broker.snapshot_stale_timeout
        stale_underlyings = self.state.snapshot_cache.get_stale_underlyings(timeout)

        # Also check positions with no snapshot at all (fresh startup)
        for ul, pos in list(self.state.positions.all_items()):
            if pos.exit_pending:
                continue
            if ul not in stale_underlyings:
                snap = self.state.snapshot_cache.get(ul)
                if snap is None or not snap.has_both_prices:
                    stale_underlyings.append(ul)

        if not stale_underlyings:
            return

        last_ts = self._last_quote_refresh_ts
        now = time.time()

        for ul in stale_underlyings:
            # Rate limit: skip if refreshed within the stale window
            if ul in last_ts and (now - last_ts[ul]) < timeout * 0.8:
                continue
            last_ts[ul] = now

            # Collect all non-exit-pending positions for this underlying
            positions = [p for p in self.state.positions.get_all(ul) if not p.exit_pending]
            if not positions:
                continue

            # Guard: if WS has already fully refreshed both prices, skip
            snap = self.state.snapshot_cache.get(ul)
            if snap and snap.has_both_prices and not snap.is_stale(timeout):
                continue

            # Option premium refresh — one per symbol (handles CE+PE mode)
            for pos in positions:
                try:
                    q = self.fetcher.fetch_quote(pos.symbol, cfg.market.fno_exchange)
                    if q:
                        ltp = float(q.get("ltp", q.get("last_price", 0)) or 0)
                        if ltp > 0:
                            snap2 = self.state.snapshot_cache.get_for_symbol(pos.symbol)
                            if snap2 is None or snap2.option_ltp is None or snap2.is_stale(timeout):
                                self.state.snapshot_cache.set_option_symbol(ul, pos.symbol)
                                self.state.snapshot_cache.update(pos.symbol, option_ltp=ltp)
                except Exception as exc:
                    err(f"[SNAPSHOT] Quote refresh failed for {pos.symbol}: ", exc)

            # Spot refresh — once per underlying (shared across all slots)
            try:
                spot_exch = cfg.market.index_exchange if ul in cfg.market.index_underlyings else cfg.market.spot_exchange
                sq = self.fetcher.fetch_quote(ul, spot_exch)
                if sq:
                    spot_ltp = float(sq.get("ltp", sq.get("last_price", 0)) or 0)
                    if spot_ltp > 0:
                        snap2 = self.state.snapshot_cache.get_for_symbol(ul)
                        if snap2 is None or snap2.spot_ltp is None or snap2.is_stale(timeout):
                            self.state.snapshot_cache.update(ul, spot_ltp=spot_ltp)
                        self.state.record_spot_price(ul, spot_ltp)
            except Exception:
                pass

    def _start_strategy_watchdog(self) -> threading.Thread:
        """Start a watchdog thread that dumps all thread stacks if the strategy thread
        does not update its heartbeat within 2.5x the scan interval.
        
        This is a diagnostic tool for identifying the exact hang location when the
        strategy thread stops producing output but the WS thread remains alive.
        """
        _interval = max(self.config.market.signal_check_interval, 1)
        _timeout = _interval * 2.5
        wd = threading.Thread(target=self._watchdog_loop, args=(_timeout,), name="strategy-watchdog", daemon=True)
        wd.start()
        return wd

    def _watchdog_loop(self, timeout: float) -> None:
        while True:
            time.sleep(timeout)
            elapsed = time.time() - getattr(self, "_last_strategy_heartbeat", 0.0)
            if elapsed < timeout:
                continue
            ts = f"{get_ist_now():%H:%M:%S}"
            stacks = []
            for t in threading.enumerate():
                frame = getattr(t, "_thread__target", None) or getattr(t, "_target", None)
                ident = t.ident
                try:
                    _f = sys._current_frames().get(ident)
                    if _f:
                        stack = "".join(traceback.format_stack(_f))
                        stacks.append(f"Thread[{t.name}](ident={ident}):\n{stack}")
                except Exception:
                    pass
            stack_dump = "\n---\n".join(stacks) if stacks else "(no stack frames captured)"
            err(
                f"[WATCHDOG] Strategy heartbeat stale for {elapsed:.0f}s (> {timeout:.0f}s timeout)\n"
                f"--- THREAD DUMP ---\n{stack_dump}\n--- END DUMP ---"
            )

    def _strategy_thread(self) -> None:
        """Clock-anchored strategy scan loop."""
        cfg = self.config
        _invariant_cycle = 0
        _last_vals: dict[str, tuple[float, float]] = {}  # slot_id -> (sl, peak)
        inf("[STRATEGY] Strategy scan thread started")
        while True:
            self._last_strategy_heartbeat = time.time()
            try:
                for event in self.ws.drain_order_events():
                    self._handle_order_stream_event(event)
                self._cleanup_stale_positions()
                self.orders.check_pending_entries()
                self.orders.check_pending_exits()
                if cfg.broker.broker_sl_orders and not cfg.broker.paper_trade:
                    self.orders.check_broker_order_fills()
                    self.orders.verify_sl_orders_active()

                if cfg.market.square_off_time:
                    now_hm = get_ist_now().strftime("%H:%M")
                    if now_hm >= cfg.market.square_off_time:
                        with self.state.state_lock:
                            eod_underlyings = list(self.state.positions.underlyings())
                        if eod_underlyings:
                            inf(
                                f"[SQUAREOFF] {cfg.market.square_off_time} reached — "
                                f"closing {len(eod_underlyings)} position(s)"
                            )
                            for ul in eod_underlyings:
                                for pos in self.state.positions.get_all(ul):
                                    with self.state.exit_lock:
                                        if pos.exit_pending:
                                            continue
                                        pos.exit_pending = True
                                    self.orders.place_exit(ul, "EOD-SquareOff", slot_id=pos.slot_id)
                self._check_max_hold()
                self._refresh_stale_snapshots()
                self.trail_engine.check_trailing_stops(self.state)

                # Periodic invariant + state validation
                _invariant_cycle += 1
                with self.state.state_lock:
                    # Prune stale _last_vals entries for exited positions to prevent false invariant violations on slot_id reuse.
                    _active_slots = {pos.slot_id for _, pos in self.state.positions.all_items()}
                    for stale_sid in list(_last_vals.keys()):
                        if stale_sid not in _active_slots:
                            del _last_vals[stale_sid]
                    for _, pos in self.state.positions.all_items():
                        _sid = pos.slot_id
                        _last = _last_vals.get(_sid)
                        _last_sl = _last[0] if _last else None
                        _last_peak = _last[1] if _last else None
                        check_invariants(pos, _last_sl, _last_peak)
                        _last_vals[_sid] = (pos.sl, pos.trail_peak_close or 0.0)
                if _invariant_cycle % 60 == 0:
                    validate_state(self.state, {})

                if LIVE_PNL_ALERT_INTERVAL > 0 and self._is_market_hours():
                    with self.state.state_lock:
                        pnl_positions = self.state.positions.all_positions()
                    if pnl_positions:
                        now_ts = time.time()
                        if now_ts - getattr(self, "_last_pnl_alert_time", 0.0) >= LIVE_PNL_ALERT_INTERVAL:
                            self._send_live_pnl_alert(pnl_positions)
                            self._last_pnl_alert_time = now_ts

                if self._is_market_hours():
                    for symbol in cfg.market.underlyings:
                        self.scan_underlying(symbol)
                else:
                    inf("[STRATEGY] Outside market hours — skipping signal scan")

            except Exception as exc: err(f"[STRATEGY ERROR] ", exc)

            self.state.bucket_counter += 1

            # clock-anchored sleep: align to next N-second boundary
            interval = max(cfg.market.signal_check_interval, 1)
            now = time.time()
            sleep_secs = interval - (now % interval)
            if sleep_secs < 1.0:
                sleep_secs += interval
            time.sleep(sleep_secs)

    # ──────────────────────────────────────────────────────────────────────────
    # Self-test WS connectivity, SIGTERM handler, Trail/TP validation
    # ──────────────────────────────────────────────────────────────────────────

    def _test_websocket(self) -> None:
        """Smoke-test: connect → authenticate → subscribe → await ticks. Prints PASS/FAIL before live feed starts."""
        import asyncio as _aio
        import json as _json
        try:
            import websockets as _websockets
        except ImportError:
            inf("[WS-TEST] SKIP — 'websockets' package not installed")
            return

        cfg   = self.config
        ws_url = cfg.broker.ws_url
        if not ws_url:
            inf("[WS-TEST] SKIP — ws_url not configured (set WEBSOCKET_URL)")
            return

        TICK_WAIT   = 15   # seconds to wait for a live tick after subscribing
        TEST_SYMBOL = {"exchange": "NSE_INDEX", "symbol": "Nifty 50"}
        try:
            import httpx as _httpx
            _rest_resp = _httpx.post(
                f"{cfg.broker.api_host}/api/v1/orderbook",
                json={"apikey": cfg.broker.api_key},
                timeout=10,
                verify=False,  # tolerate self-signed certs on dev servers
            )
            _rest_data = _rest_resp.json()
            if _rest_data.get("status") == "success":
                _ob = _rest_data.get("data", {})
                _n = len(_ob.get("orders", [])) if isinstance(_ob, dict) else 0
                inf(f"[WS-TEST] REST API key OK (orderbook: {_n} order(s))")
            else:
                _rest_msg = _rest_data.get("message", str(_rest_data))
                inf(f"[WS-TEST] WARN: REST API key check failed: {_rest_msg}")
                inf(f"[WS-TEST]       If REST also returns 'Invalid API key', the key in OPENALGO_API_KEY is wrong.")
                inf(f"[WS-TEST]       Get the correct key from: {cfg.broker.api_host}/apikey")
        except Exception as _rest_exc: err(f"[WS-TEST] REST check skipped: ", _rest_exc)

        inf(f"[WS-TEST] Testing {ws_url} ...")

        async def _run() -> None:
            try:
                async with _websockets.connect(ws_url, open_timeout=10) as ws:
                    inf("[WS-TEST] Transport OK — WebSocket handshake succeeded")

                    await ws.send(_json.dumps({
                        "action": "authenticate",
                        "api_key": cfg.broker.api_key,
                    }))
                    raw = await _aio.wait_for(ws.recv(), timeout=10)
                    resp = _json.loads(raw)
                    status = resp.get("status") or resp.get("type", "")
                    if status not in ("success", "authenticated"):
                        code = resp.get("code", "")
                        inf(f"[WS-TEST] FAIL — auth rejected: {resp}")
                        if code == "AUTHENTICATION_ERROR" or "Invalid API key" in resp.get("message", ""):
                            inf(
                                f"[WS-TEST] HINT: The API key in OPENALGO_API_KEY does not match"
                                f" any key stored in the OpenAlgo database."
                                f"\n[WS-TEST]       1. Log in to your OpenAlgo dashboard"
                                f"\n[WS-TEST]       2. Go to API Key page (Account → API Key)"
                                f"\n[WS-TEST]       3. Copy the key and set OPENALGO_API_KEY=<copied-key> in your .env"
                            )
                        return
                    inf(f"[WS-TEST] Auth OK")

                    await ws.send(_json.dumps({
                        "action": "subscribe",
                        "symbols": [TEST_SYMBOL],
                        "mode": "ltp",
                    }))
                    inf(f"[WS-TEST] Subscribed {TEST_SYMBOL['exchange']}:{TEST_SYMBOL['symbol']}")

                    deadline = _aio.get_event_loop().time() + TICK_WAIT
                    tick_count = 0
                    while _aio.get_event_loop().time() < deadline:
                        remaining = deadline - _aio.get_event_loop().time()
                        try:
                            raw = await _aio.wait_for(ws.recv(), timeout=min(5, remaining))
                            msg = _json.loads(raw)
                            # Skip subscribe-ack messages
                            if msg.get("action") == "subscribe" or msg.get("type") == "subscribed":
                                continue
                            tick_count += 1
                            ltp = msg.get("ltp") or msg.get("data", {}).get("ltp", "?")
                            inf(f"[WS-TEST] Tick #{tick_count} — ltp={ltp}")
                            if tick_count >= 3:
                                break
                        except _aio.TimeoutError:
                            inf(f"[WS-TEST] (no tick yet, {remaining:.0f}s remaining...)")

                    if tick_count == 0:
                        inf(
                            f"[WS-TEST] WARNING — connected & authenticated but 0 ticks "
                            f"in {TICK_WAIT}s. Market may be closed or WS server has no feed."
                        )
                    else:
                        inf(f"[WS-TEST] PASS — received {tick_count} tick(s) ✓")

            except OSError as exc:
                err(f"[WS-TEST] FAIL — cannot reach {ws_url}", exc)
                inf("[WS-TEST] Check: Is the WebSocket server running? Is /ws proxied to port 8765 in Caddy/nginx?")
            except Exception as exc:
                _hint = ""
                _emsg = str(exc)
                _exc_type = type(exc).__name__
                if "scheme" in _emsg or "InvalidURI" in _exc_type or "isn't a valid URI" in _emsg:
                    if cfg.broker.api_host.startswith("https://"):
                        _ws_domain = cfg.broker.api_host[8:].split("/")[0]
                        _hint = (
                            f"\n[WS-TEST] HINT: '{ws_url}' is wrong for an HTTPS host."
                            f"\n[WS-TEST]       Remote server → set  WEBSOCKET_URL=wss://{_ws_domain}/ws"
                            f"\n[WS-TEST]       Same server   → set  WEBSOCKET_URL=ws://127.0.0.1:8765"
                        )
                elif "InvalidStatus" in _exc_type or "HTTP 200" in _emsg or "HTTP 4" in _emsg:
                    _hint = (
                        f"\n[WS-TEST] HINT: The server returned an HTTP response instead of upgrading to WebSocket."
                        f"\n[WS-TEST]       This means the reverse proxy (Caddy/nginx) is NOT routing '{ws_url}'"
                        f"\n[WS-TEST]       to the OpenAlgo WebSocket server on port 8765."
                        f"\n[WS-TEST]       Fix: Add a /ws → localhost:8765 block in your Caddyfile:"
                        f"\n[WS-TEST]         @websocket path /ws /ws/*"
                        f"\n[WS-TEST]         handle @websocket {{ reverse_proxy localhost:8765 }}"
                        f"\n[WS-TEST]       Then reload Caddy: sudo systemctl reload caddy"
                        f"\n[WS-TEST]       Until then, use ws://127.0.0.1:8765 if running on the same server."
                    )
                err(f"[WS-TEST] FAIL — {_exc_type}: {exc}{_hint}", exc)

        try:
            _aio.run(_run())
        except RuntimeError:
            # Already inside a running event loop (e.g. eventlet) — skip test
            inf("[WS-TEST] SKIP — cannot run async test inside existing event loop")

    @staticmethod
    def _sigterm_handler(_signum: int, _frame) -> None:
        raise KeyboardInterrupt()

    def _validate_thresholds(self) -> None:
        """Check threshold relationships (single-field checks now in TrailConfig.validate())."""
        cfg = self.config
        _act = cfg.trail.activate_at_max_pts
        _step_pts = cfg.trail.step_pts
        _step_pct = cfg.trail.step_pct
        _ep_sample = 100.0
        if _step_pts >= _act:
            inf(f"[VALIDATION] step_pts={_step_pts} >= activate_at_max_pts={_act} — first step overshoots activation")
        if _ep_sample * (_step_pct / 100.0) >= _act:
            inf(f"[VALIDATION] Step {_step_pct}% of EP ({_ep_sample * _step_pct / 100:.1f}) >= activate_at_max_pts ({_act}) at EP={_ep_sample}")

    def run(self) -> None:
        """Start WebSocket + strategy threads, run until KeyboardInterrupt."""
        cfg = self.config
        signal.signal(signal.SIGTERM, self._sigterm_handler)
        self._verify_registration()
        self._validate_thresholds()
        self._print_startup_info()

        # ── Order-stream platform-infra diagnostic ────────────────────────────
        _up_raw = os.getenv("ORDER_UPDATES_ENABLED", "NOT-SET")
        _pi_raw = os.getenv("ORDER_POLL_INTERVAL", "NOT-SET")
        inf(f"[CONFIG] Platform ORDER_UPDATES_ENABLED={_up_raw!r} → order_updates_enabled={cfg.broker.order_updates_enabled}")
        inf(f"[CONFIG] Platform ORDER_POLL_INTERVAL={_pi_raw!r} → order_poll_interval={cfg.broker.order_poll_interval}")
        inf(f"[CONFIG] Script order_stream_enabled={cfg.broker.order_stream_enabled} (config-managed, not from env)")
        inf(f"[CONFIG] Script order_stream_complete_entries={cfg.broker.order_stream_complete_entries} (config-managed, not from env)")
        if cfg.broker.order_updates_enabled and cfg.broker.order_stream_enabled:
            inf("[CONFIG] Order-stream feature ENABLED (platform-ready + script-config) — will attempt subscribe_orders() on WS connect")
        elif not cfg.broker.order_updates_enabled:
            inf("[CONFIG] Order-stream DISABLED — platform ORDER_UPDATES_ENABLED is not TRUE."
                " All order-status updates will use REST polling")
        else:
            inf("[CONFIG] Order-stream DISABLED — script order_stream_enabled=False."
                " All order-status updates will use REST polling")

        self._check_open_positions_on_startup()

        self._send_alert(
            f"🚀 {cfg.broker.strategy_name} starting\n"
            f"Underlyings: {', '.join(cfg.market.underlyings)}\n"
            f"Min Score: {cfg.entry.min_score} | Max Trap: {cfg.entry.max_trap}",
            1,
        )

        self._test_websocket()
        self.ws.start()

        st_thread = threading.Thread(target=self._strategy_thread, name="strategy-thread", daemon=True)
        st_thread.start()
        self._last_strategy_heartbeat = time.time()
        self._start_strategy_watchdog()

        inf(f"[BOT] {cfg.broker.strategy_name} running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            inf("\n[SHUTDOWN] Stopping bot...")
            for ul in list(self.state.positions.underlyings()):
                for pos in self.state.positions.get_all(ul):
                    inf(f"[SHUTDOWN] Closing {pos.slot_id}...")
                    self.orders.place_exit(ul, "Bot Shutdown", slot_id=pos.slot_id)
        finally:
            try:
                self.client.disconnect()
            except Exception as _disc_exc:
                err("[SHUTDOWN] client.disconnect() error", _disc_exc)
            try:
                self.ws.stop()
            except Exception as _stop_exc:
                err("[SHUTDOWN] ws.stop() error", _stop_exc)
            self._send_alert(f"🛑 {cfg.broker.strategy_name} stopped", 1)
            inf("[BOT] Shutdown complete")


# ── ROOT ENTRY POINT ────────────────────────────────────────────────────
if __name__ == "__main__":
    config = BotConfig.from_env()
    config.validate()

    if not config.broker.api_key or config.broker.api_key == "openalgo-apikey":
        inf(
            "[WARNING] OPENALGO_API_KEY is not set in environment.\n"
            "          Export it before running: export OPENALGO_API_KEY=your-key"
        )

    bot = OptionsBuyerEdgeBot(config)
    bot.run()
