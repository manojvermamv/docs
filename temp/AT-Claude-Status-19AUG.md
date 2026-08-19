# TURN - 1

Verifying each assumption against the box as it is now, not as I left it.

A4 disagrees with what I reported — console and desk now show 4 scheduler lines each, where I claimed zero. Reading them.

Those four are `Sched: scheduler: disabled` startup banners — one per restart. My claim holds, with better evidence than a count. Gathering the rest.

Counts reconcile (52 defects in both the file and the map; 8 open items). Now the docs sweep — scanning all markdown for claims I can mechanically test.

TOOLING.md claims to list *every* runnable entry point. Checking whether today's new scripts are in it.

Four runnable scripts missing from the file that promises to list them all. Adding them.

Now OPERATIONS.md — the operations authority should describe the daily cycle.

OPERATIONS.md has **two tables of contents** — two documents concatenated — and says nothing about the daily cycle it's meant to be the authority on. Checking its structure.

The second half is a deliberately folded-in runbook, so it stays. But line 13 points `../docs/OPERATIONS.md` at **itself**. Fixing that and adding the daily cycle it lacks.

My own new README says "Six units" while there are **nine files** (seven services, two timers). Correcting it.

I checked every claim below against the box rather than recalling it. **Two of my assumptions were wrong.**

## Section 1 — Assumptions, tested

| # | What I assumed | Verdict | Evidence |
|---|---|---|---|
| 1 | Console and desk run **zero** scheduled jobs | **Wrong number, right conclusion** | They log 4 lines each — all `Sched: scheduler: disabled`, one per restart. I'd counted the banner. Claim holds, better evidence |
| 2 | Neither profile overrides `record_ticks` | **Wrong** | I read `config/profiles/` which doesn't exist. Real path: `src/interfaces/mcp/config/profiles/` — and both **already** set `scheduler.enabled: false` |
| 3 | Setting `record_ticks: false` in the profile fixes it | **Wrong — inert** | `.env` has `MCP_MARKET_DATA__RECORD_TICKS=true` and env beats profile. Only the unit's own `ExecStart` works |
| 4 | Only `:8000` records | **Holds** | Console reports `recording: False, subscribed: 0`; `mcp-gateway` still schedules |
| 5 | All services run as `admin` | **Holds** — after a third pass | `at-admin-console` was *still* root; the apply list named what I remembered. Now all five |
| 6 | Zero root-owned files under `run/` | **Holds** | `find run/ -user root` → **0** |
| 7 | The CLI can be pointed at the recorder | **Wrong** | `:8000` returns **404** on `/console/api/ticks`. There is nothing to point at |
| 8 | Session schedule follows config | **Holds** | `session_units.py --check` → *follows configuration*; strategy stopped itself at **15:30:12** |
| 9 | The cron canary works | **Holds** | Ran the exact entry: `[OK] session health`, 210 decisions |
| 10 | My path guard catches hardcoding | **Wrong** | It hardcoded `/home/admin`, so it passed on a `/home/ubuntu` host. Now catches both, proven by rewriting a unit |
| 11 | Defect/concept counts | **Holds** | 52 rows in the file, `defect 52` in the map, 8 open items |

**The one that cost most:** the "duplicate recording streams" was never duplicated *data*. Only `:8000` ever subscribes. What was doubled was **reporting** — two processes holding a connected, never-fed stream whose cache reads stale forever. That's the 47.7-hour figure.

## Section 2 — What's left, in plain words

**Code and data — no decision needed (52 rows).** The ones that bite:

| What's wrong | Why it matters |
|---|---|
| `at ticks watch` can't reach the recorder | The recorder has no HTTP route; the CLI now says so instead of misleading you |
| The chain costs 5× what it needs | `WorkerSpec.needs` exists to fix this and the store ignores it |
| Per-minute OHLC isn't stored | Every intraday question re-derives them |
| Option history is a closing window | Miss the capture before expiry and it's gone |
| `_compute_oi_wall` has no bullish case | +0.5 against −1.0 — a standing directional skew |
| One seam test fails | −9 vs −10, from `slow_norm` 0.833 vs 0.750 |
| `test_jobs` takes 8m37s | Passes; makes a suite run look hung |

**Nine upstream items** are OpenAlgo's and already worked around here.

## Section 3 — For you, not the code

| Decision | Situation |
|---|---|
| **Telegram alert credentials** | The canary logs but cannot alert. Only you have the token |
| **The signal has negative edge** | Measured at every horizon. The AI doesn't fix it. The big one |
| **Five measured numbers that move money** | Measured, unapplied — applying one is your call |
| **Six phantom bars** | Deleting recorded data is yours alone |
| **Four inert orchestrator stages** | Report PASSED while checking nothing |
| **Options seller support** | Door open, room not built |
| **Intraday square-off has nowhere to be recorded** | A real gap in the books |

## Section 4 — Docs updated

- **`docs/TOOLING.md`** promised *every* runnable entry point and was missing four. Its example still passed the stale `--until 15:30`.
- **`docs/OPERATIONS.md`** — the operations authority — said nothing about the daily cycle. It gains a **§0: the trading day, start to finish**. Its document table also had a row pointing at itself.
- **`deploy/README.md`** — four runnable scripts, no index. Now written, leading with portability: no host, user or path is written down anywhere.
- **Dead links across all markdown: 0.**

I found one error in my own new prose while checking it — "six units" where there are nine files — and fixed it.

Head is `b6af3ce`, tree clean, 56 tests pass. Tomorrow's timer is armed for 03:40 UTC.


----


# TURN - 2

Confirmed `score_max=1.0` — **it votes**, so a bullish case changes real scores. That one is gated; I'll propose it rather than apply it. Checking what `at ticks status` reads, since that decides how to fix item 1.

`at ticks status` reads the **store** directly, so status is already truthful. But it points at `at ticks health`, which earlier printed a domain list instead. Verifying that pointer.

The `health` subcommand exists and calls the right tool. Running it now to see why it printed a domain list.

**Found it — `at ticks health` has never worked.** `cmd_tools()` only *lists* tools; it ignores its arguments, so `cmd_tools call monitoring_market_data_health` prints the inventory and discards the call. Fixing it to actually ask.

The nested heredoc broke my Python string. Writing the block to a file and splicing it in.

My fix reports a **freshly constructed** stream, not the running gateway's — "NOT connected" while ticks recorded fine today. Discarding that approach: the recorder exposes no route, so the only truth available is the store.

Too noisy — it lists every contract ever recorded. Scoping it to the configured recording targets.

That's the right answer, from the only source that can give it. Verifying it would have caught this morning's outage.

Stale detection works and would have flagged this morning. Committing.

Now the slow `test_jobs` — it builds the whole real warehouse. Checking what it actually needs.

The job always reads the real 31 MB store; only its output is configurable. But the test only needs *a* job that succeeds — it's about the `error` field, not the warehouse. Checking for a cheap one.

`adapt_review` succeeds in **0.14s** versus 8m37s. Switching the test to it, since the test is about the `error` field, not the warehouse.

Whole file now runs in **7.2s**. Checking I didn't orphan the skip helper.

Still used elsewhere, lint clean. Now the seam test — investigating the one-point mismatch.

The direct call omits what the seam adds. Checking whether the seam passes greeks the direct call doesn't.

`fast_norm` and `fast_coverage` are identical; only `slow_norm` differs. Checking whether the greeks-dependent components are slow-tier — which would mean the test compares a greeks-aware call to a greeks-blind one.

Slow components are all spot-frame derived, not greeks. So the seam and the direct call see **different spot frames** — a quarter point on one component. Checking how the seam builds its frame.

Both use `upto=stamp`, so the frames should match. Diffing the actual component scores to find which one moves.

I've narrowed the seam mismatch but not closed it, and the remaining step decides a score — so I'll report rather than guess. Committing what's done.

Three of your seven are done. Here's where each stands.

## Done

**`at ticks watch` / the recorder** — the real bug was next door: **`at ticks health` had never worked**. It called `cmd_tools call ...` and `cmd_tools` takes no arguments — it only *lists* tools, so the command printed the tool inventory while `at ticks status` pointed at it as the way to ask.

The obvious repair was worse and I threw it away: importing the monitoring domain reads a **newly constructed** stream, and reported `socket NOT connected, subscribed 0` on a box that recorded 58,635 ticks that day. It now reads the store — the only place that says what was actually written — and flags `STALE` when the market is open and nothing has arrived:

```
market        closed  (16:42 Asia/Kolkata, session 09:15-15:30)
BANKNIFTY       58635 ticks, newest 3694s ago
NIFTY           57891 ticks, newest 3693s ago
```

Verified it flags this morning's shape. The recorder still exposes no HTTP route, so *subscribe now* stays unreachable — but it self-subscribes every 5 minutes, and status was always truthful.

**`test_jobs` slow — 8m37s → 0.14s.** It enqueued `warehouse_build` (the whole 31 MB store through DuckDB) to prove a job record always carries `error`. Any successful job proves that; it now uses `adapt_review`. Whole file: 7.2s. This is the test mistaken for a hang twice today, and what sent me chasing a cache regression that didn't exist.

## Narrowed, needs your call

**Seam mismatch** — `fast_norm` and `fast_coverage` are **identical**; only `slow_norm` differs, 0.8333 vs 0.7500. Over three slow components at `score_max=1.0` that's **exactly a quarter point on one**. Ruled out: the greeks the seam adds (all three slow components read the spot frame, none reads a greek) and the frame window (both use `upto=stamp`). Which side is right **decides a score on real bars**, so I stopped there rather than guess.

## One is not what you think

**`_compute_oi_wall` bullish case — this is a score change, not a bug fix.** `OI_WALL` has `score_max=1.0`, so **it votes**. Adding a bullish branch changes composite scores on real bars. CLAUDE.md gates exactly this. I'd propose: `spot >= cw` currently returns −1 unconditionally, treating a breakout above the call wall as bearish resistance. But that's your decision with measurement, not mine.

## Not started — genuine features, not bugs

| Item | Why it's bigger than it reads |
|---|---|
| Chain heavier than needed | `WorkerSpec.needs` exists; the store ignores it. Splitting the fetch changes what every caller gets |
| Per-minute OHLC not stored | A new persisted stream. Note the cache made re-deriving cheap — 2.3 ms/bar — so the cost that motivated it is mostly gone |
| Option history before expiry | Needs a scheduled capture job and a retention decision |

**Most impactful remaining work:**
- Decide the seam mismatch — the quarter point is in one of `EMA Trend` / `RSI Momentum` / `Spot vs VWAP`.
- Decide the OI wall bullish case, or leave the skew documented.
- Add the Telegram credentials and rerun `scripts/install-cron.sh`; the canary logs but cannot alert.
