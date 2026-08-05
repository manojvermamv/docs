# Claude Android — Autonomous First-Message Keep-Alive Guide

## Overview

A rooted, ADB-driven script system that keeps a Claude Android app usage window active
by sending **only the first message of each 5-hour rolling window**, then staying quiet
until the window is about to expire.

It does **not** send keep-alive pings every few minutes. Instead it:

1. Reads the Usage page and classifies the window state.
2. When the window is **fresh** (`0% used`, no reset timer), sends one message
   `Hello From India? <full IST datetime>`.
3. Verifies the message took effect by pulling-to-refresh the Usage page; if not yet
   reflected, retries with increasing backoff (2 → 4 → 6 … min, up to 15 attempts).
4. When the window is confirmed active, sleeps until just before it expires, then
   repeats — 24/7, day or night.

The two scripts run as a background daemon (`nohup`) and self-clean stale instances on
startup. The loop holds a **partial wake lock** while sleeping so the device cannot
deep-sleep and freeze the timer, and every UI action is **package-checked** so it never
fires against a non-Claude window.

---

## What You'll Need

| Requirement | Details |
|-------------|---------|
| ADB | `C:\Program Files (x86)\Minimal ADB and Fastboot\adb.exe` (adjust to your path) |
| Android device | USB debugging enabled, connected via USB, **rooted** |
| Root access | `input text` / `input keyevent` / `wm dismiss-keyguard` need `su -c` (`INJECT_EVENTS` restriction) |
| Claude app | Installed and logged in on the device |
| Lock-screen security | **Swipe / None** only — `wm dismiss-keyguard` cannot unlock a PIN/pattern/password |
| Screen resolution | Reference coordinates are for **1080x2460**; Settings/Usage are found dynamically, so layout changes are tolerated |
| Files | `claude_keepalive.sh` and `claude_loop.sh` (see below) |

### Verify ADB Connection

```powershell
& "C:\Program Files (x86)\Minimal ADB and Fastboot\adb.exe" devices
```

Expected:

```
List of devices attached
<SERIAL>    device
```

If no device: enable **Developer Options** (tap Build Number 7×), enable **USB Debugging**,
then **Allow** the prompt on the device. If the ADB server will not start, set
`ANDROID_ADB_LOG_PATH` to a writable path first (e.g. `C:\Users\<you>\AppData\Local\Temp\opencode\adb.log`).

---

## The Two Files

Both live on the device at `/data/local/tmp/`. Working copies are kept on the PC
(e.g. `C:\Users\<you>\Desktop\ClaudeKeepAlive\`).

| File | Role |
|------|------|
| `claude_keepalive.sh` | One unit of work: wake, unlock, network check, navigate to Usage, classify state, optionally send + verify the first message, then write the next-check time. **v6.4** |
| `claude_loop.sh` | Daemon that sleeps until the next-check time (holding a wake lock), runs `claude_keepalive.sh`, and self-cleans stale instances. **v4.2** |

### On-device files / logs

| Path | Purpose |
|------|---------|
| `/data/local/tmp/claude_keepalive.sh` | Keep-alive unit script |
| `/data/local/tmp/claude_loop.sh` | Loop daemon |
| `/data/local/tmp/claude_keepalive.log` | Keep-alive unit log |
| `/data/local/tmp/claude_loop.log` | Loop daemon log |
| `/data/local/tmp/claude_next_check` | Epoch (seconds) of the next check |
| `/data/local/tmp/claude_loop.pid` | PID of the running loop (single-instance guard) |
| `/data/local/tmp/claude_keepalive.lock` | Lock file held while a keep-alive unit runs (stale >30 min auto-removed) |

---

## Window States (from the Usage page)

| State | Meaning | Detect on Usage page |
|-------|---------|----------------------|
| `TYPE3_FRESH` | Fresh window, timer not started | `0% used` **and** no `Resets in …` text |
| `TYPE1_ACTIVE` | Window active, timer running | `X% used` (1–99) **and** `Resets in X hr Y min` |
| `TYPE2_LIMIT` | 100% used, waiting for reset | `100% used` |
| `UNKNOWN` | Could not parse | — |

**Key rule:** a message is sent **only** when the state is `TYPE3_FRESH`. It is never sent
while the window still has time remaining, so it can never count against an expiring window.

---

## Architecture & Execution Flow (v6.4)

Every navigation/action tap is wrapped in `nav_step()`: **tap → 3s delay → verify the
focused window is `com.anthropic.claude`**. If the app crashes, a system dialog grabs
focus, or HOME/shade steals it, the script force-stops + relaunches Claude and restarts
navigation from scratch (up to 3 attempts). Settings/Usage taps are located dynamically
by `text`/`content-desc` (Claude-scoped) so app layout changes do not break navigation.

Two additions in v6.4 keep the run robust:

- **Drift detection.** `detect_screen()` now returns `DRIFTED` for **any** unrecognized
  in-app page — Settings sub-pages (Notifications, Profile, Billing, …), modals,
  conversations, etc. — not just pages with a `Go back` button. `UNKNOWN` is reserved for
  the case where the UI dump could not be produced. Recovery from a drift is a **fresh
  relaunch** (force-stop + relaunch) — far more reliable than navigating back from a page
  whose layout is unknown — then navigation restarts via the normal path.
- **Screen wake lock.** The loop daemon's partial wake lock keeps the CPU awake but not
  the display, so a long run could hit `screen_off_timeout` (60 s here) mid-operation.
  While working, the keepalive raises the display timeout to 30 min
  (`screen_lock_on`), restoring the saved value on exit (`screen_lock_off`), so the
  screen stays on for the whole run.

```
┌─────────────────────────────────────────────────────────────────┐
│                     LOOP DAEMON (claude_loop.sh)                │
│   start → cleanup_stale (kill old loop/orphans) → while true:   │
│     read next_check → due?  YES → run claude_keepalive.sh       │
│                              NO  → sleep_until (holds wake lock)│
└───────────────────────────────────┬─────────────────────────────┘
                                    │  keep-alive unit
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                  KEEP-ALIVE UNIT (claude_keepalive.sh)          │
│  [Lock guard: fresh lock → exit; stale lock (>30m) → clean]     │
│                     │                                           │
│                     ▼                                           │
│  [Network check] ──(no net)──► [write next_check = +10m] → exit │
│                     │ (OK)                                      │
│                     ▼                                           │
│  [Wake screen + dismiss keyguard] (Swipe/None security only)    │
│                     ▼                                           │
│  [Launch Claude] → [STRICT PACKAGE CHECK GATE]                  │
│                     │ YES                    │ NO               │
│                     ▼                        ▼                  │
│          [Dump UI & detect screen]  [force-stop + relaunch]     │
│   detect_screen() → in-app screen state:                        │
│     LOGIN / NOT_CLAUDE → force-stop + relaunch Claude           │
│     USAGE              → already there (skip navigation)        │
│     CHAT_HOME / UNKNOWN → menu (66,182) → Settings → Usage      │
│     MENU_DRAWER        → Settings → Usage                       │
│     SETTINGS           → tap Usage                              │
│     DRIFTED (sub-page) → force-stop + relaunch fresh            │
│   [each tap: nav_step package check; retry max 3 from scratch]  │
│   [detect_screen returns] → next: PARSE & CLASSIFY below        │
│                    ┌─────────────────────────────┐              │
│                    │ PARSE & CLASSIFY USAGE STATE│              │
│                    └───────┬──────────┬──────────┴──────────┐   │
│                            ▼          ▼                     ▼   │
│                     TYPE1_ACTIVE  TYPE2_LIMIT           TYPE3_FRESH
│                     (%1–99, timer) (100%, wait reset)   (0%, no timer)
│                            │          │                     │
│                            ▼          ▼                     ▼
│                    schedule =      reset known?        [SEND VERIFY LOOP]
│                    expiry − 10m    YES → reset + 2m     cycle 1: send message
│                                    NO  → +5m          goto_usage + refresh
│                                                       verified / state changed?
│                                                        YES → schedule expiry−10m
│                                                        NO  → backoff 2→4→6…m
│                                                               (max 15 cycles)
│                            └──────► write next_check ──► HOME → exit
└─────────────────────────────────────────────────────────────────┘
```

### Usage State Classification

```
                                  [Dump UI XML]
                                        │
                                        ▼
                         Does XML contain Login strings?
                         ("Continue with Google", etc.)
                                 ├── YES ──► [State = LOGIN] (Abort execution)
                                 └── NO
                                        │
                                        ▼
                            Extract `X% used` Value
                            Extract `Resets in ...` Text
                                        │
                                        ▼
            ┌───────────────────────────┼───────────────────────────┐
            ▼                           ▼                           ▼
  Is % used >= 100%?            Is Reset Text absent         Is % used between
            │                    AND % used == 0%?             1% and 99% WITH
            ▼                           │                    Reset Text present?
  [STATE = TYPE2_LIMIT]                 ▼                           │
   • Window exhausted.          [STATE = TYPE3_FRESH]               ▼
   • Waiting for reset.          • Fresh window ready!       [STATE = TYPE1_ACTIVE]
                                 • Target for message.      • Timer currently running.
                                                           • Do not send message.
```

### Scheduling after each run

| State at end of run | Next check |
|--------------------|------------|
| `TYPE1_ACTIVE` (still time left) | `now + (remaining − 10 min)` → just before expiry |
| `TYPE1_ACTIVE` (near expiry, ≤10 min left) | `now + 10 min` (poll until it flips) |
| `TYPE2_LIMIT` (reset time known) | `now + (reset_min + 2 min)` → first message tried promptly after reset |
| `TYPE2_LIMIT` (reset time unknown) | `now + 5 min` |
| `TYPE3_FRESH` (send failed) | `now + 5 min` (retry) |
| `UNKNOWN` | `now + 10 min` |
| **No network** | `now + 10 min`, then abort |

---

## Step-by-Step Instructions

### Step 1 — Install the scripts (one-time)

```powershell
$adb = "C:\Program Files (x86)\Minimal ADB and Fastboot\adb.exe"
& $adb push "C:\Users\<you>\Desktop\ClaudeKeepAlive\claude_keepalive.sh" /data/local/tmp/claude_keepalive.sh
& $adb push "C:\Users\<you>\Desktop\ClaudeKeepAlive\claude_loop.sh" /data/local/tmp/claude_loop.sh
& $adb shell "su -c 'chmod 755 /data/local/tmp/claude_keepalive.sh /data/local/tmp/claude_loop.sh'"
# Verify syntax
& $adb shell "su -c 'sh -n /data/local/tmp/claude_keepalive.sh && sh -n /data/local/tmp/claude_loop.sh && echo SYNTAX_OK'"
```

### Step 2 — Start the loop daemon

```powershell
& $adb shell "su -c 'nohup sh /data/local/tmp/claude_loop.sh > /dev/null 2>&1 &'"
Start-Sleep -Seconds 5
& $adb shell "su -c 'ps -ef'" | Select-String "claude_loop"
```

Expected: exactly **one** `sh /data/local/tmp/claude_loop.sh` process. A single PID file
(`/data/local/tmp/claude_loop.pid`) is written; on any later start, the new instance kills
the previous one and any orphaned keep-alive children, then takes over — so there is never
more than one runner.

### Step 3 — Confirm the first run

```powershell
& $adb shell "cat /data/local/tmp/claude_loop.log" | Select-Object -Last 12
& $adb shell "cat /data/local/tmp/claude_keepalive.log" | Select-Object -Last 20
```

For **realtime log monitoring** (streams both logs as the loop wakes, Ctrl+C to stop):

```powershell
& "C:\Program Files (x86)\Minimal ADB and Fastboot\adb.exe" shell "tail -f /data/local/tmp/claude_loop.log /data/local/tmp/claude_keepalive.log"
```

A healthy first run logs roughly:

```
=== Starting keep-alive ===
Network OK (IP: <WAN_IP>)
--- Screen readiness check ---
… screen ON / unlocked / home …
Initial screen: CHAT_HOME
Screen before goto_usage (attempt 1): CHAT_HOME
On chat (or unknown) → menu → Settings → Usage
Settings found dynamically at (104 2323)
Usage found dynamically at (227 913)
Screen after navigation (attempt 1): USAGE
Usage: 1% | Remaining: 2 hr 13 min | State: TYPE1_ACTIVE
TYPE1: window already active … → nothing to send
Scheduling next check in 2 hr 3 min …
=== Finished ===
Sleeping 1 hr 40 min (wake at 03:29 AM IST)
```

### Step 4 — Sending and verifying the first message

When the state is `TYPE3_FRESH`, the keep-alive runs `send_verify_loop`:

1. Cycle 1: **send** the message (`send_hi`), then navigate to Usage and **pull-to-refresh**.
2. Accept success if the state is now `VERIFIED` (`TYPE1_ACTIVE`, usage 1–99%) **or** any
   new non-fresh state appeared.
3. If still `TYPE3_FRESH`, wait `2 min`, retry; on next failure wait `4 min`, then `6 min`,
   etc. (increment by 2 min each cycle).
4. If still not verified after **15 cycles**, stop this run and schedule a retry in 5 min
   (the lock is released; the loop retries on the next scheduled run).

The message text is `Hello From India? YYYY-MM-DD HH:MM:SS IST`. Spaces are escaped as
`%s` for `input text`; the IST datetime is produced with `TZ=Asia/Kolkata`.

### Step 5 — Manual run / forced check

```powershell
& $adb shell "su -c 'rm -f /data/local/tmp/claude_keepalive.lock'"
& $adb shell "su -c 'sh /data/local/tmp/claude_keepalive.sh'"
```

### Step 6 — Stop everything / full clean reinstall

```powershell
$adb = "C:\Program Files (x86)\Minimal ADB and Fastboot\adb.exe"
& $adb shell "su -c 'pkill -9 -f claude_loop.sh; pkill -9 -f claude_keepalive.sh'"
& $adb shell "su -c 'rm -f /data/local/tmp/claude_keepalive.sh /data/local/tmp/claude_loop.sh /data/local/tmp/claude_keepalive.log /data/local/tmp/claude_loop.log /data/local/tmp/claude_loop.pid /data/local/tmp/claude_next_check /data/local/tmp/claude_keepalive.lock /data/local/tmp/ui.xml /data/local/tmp/ui.xml.claude'"
```

Then repeat **Step 1** and **Step 2** to clean-push and re-register.

---

## Expected Outcome

- **24/7 operation:** the first message of each fresh 5-hr window is sent automatically,
  day or night.
- **Quiet between windows:** the phone's screen stays off for most of the window and only
  wakes near expiry. A partial wake lock (CPU-only, screen still off) is held during the
  loop's sleep so the device cannot deep-sleep and freeze the timer; it is released as soon
  as the loop wakes.
- **Robust wake path:** if the screen is off and locked, the script wakes it (`keyevent 26`)
  and unlocks via `wm dismiss-keyguard` (only a short swipe if still locked) — then handles
  the notification shade **after** unlock so the unlock swipe never drags the shade down.
- **Package-gated actions:** every tap/type/swipe is preceded by a post-delay check that
  the focused window is still `com.anthropic.claude`; on focus loss the app is relaunched
  and navigation restarts (max 3 attempts).
- **Drift-aware:** if a Settings tap lands on any in-app sub-page (Notifications, Profile,
  Billing, …), the script detects `DRIFTED` and force-stops + relaunches Claude fresh, then
  re-navigates — so a single mis-tap never breaks the run.
- **Screen stays on while working:** `screen_off_timeout` is temporarily raised to 30 min
  during the run and restored afterwards, so the display never blanks mid-operation.
- **Dynamic targeting:** Settings/Usage are found by `text`/`content-desc` at runtime, so
  app layout changes don't break navigation (hardcoded coords are only a fallback).
- **Self-healing:** one loop runs (PID-file guard); stale instances are killed on start; a
  stale `claude_keepalive.lock` older than 30 min is auto-removed; a stuck verify loop
  gives up after 15 cycles and retries later.
- **Network-aware:** if there is no network, it aborts and retries in 10 min rather than
  failing mid-navigation.

---

## Common Pitfalls

| Issue | Cause | Solution |
|-------|-------|----------|
| `INJECT_EVENTS` error on `input …` | Device security blocks input | Always prefix with `su -c` (root required) |
| `input text` drops spaces | ADB limitation | Escape spaces as `%s` (already done for the message) |
| Hardware back does nothing | **Claude ignores `keyevent 4`** | Use in-app buttons only: menu `(66,182)`; Settings/Usage found dynamically |
| Navigation stuck after relaunch | Notification shade grabbed focus | Collapse the shade *after* confirming unlocked; swipe top→bottom |
| `uiautomator dump` stale | Animations / transitions | Wait (`sleep 2+`) before dumping |
| Verify loop never ends | Usage page never updates (network/app glitch) | Built-in 15-cycle cap → retries on next scheduled run |
| Two loops running | Old instance left from before PID guard | The `cleanup_stale` guard kills the previous loop on start |
| Daemon stalls forever | Abrupt kill left a stale `claude_keepalive.lock` | v6.3 auto-removes any lock older than 30 min |
| Settings/Usage tap misses after app update | Layout padding / scaling changed | v6.3 finds them by `text`/`content-desc` at runtime; coords are only a fallback |
| Settings tap opens a sub-page (Notifications etc.) | Hardcoded coordinate hit the wrong row | v6.4 detects `DRIFTED` (any unrecognized page) → force-stops + relaunches Claude fresh, then re-navigates |
| `refresh_usage` swiped on the wrong screen | Pull-to-refresh ran while not actually on Usage (e.g. after a failed `goto_usage`) | v6.4 re-navigates to Usage before swiping; parse is never run against a non-Usage screen |
| Screen blanks mid-run | `screen_off_timeout` hit during long navigation/verify waits | v6.4 raises the display timeout to 30 min while working, restores it on exit |
| Unlock fails after reboot | Device has PIN/Pattern/Password | Keyguard only dismisses for Swipe/None — configure **Swipe/None** |

> **Lock-screen requirement:** `wm dismiss-keyguard` only works for **Swipe / None**
> security. If the device has a PIN, pattern, or password, keyguard dismissal fails silently
> and every tap misses. Keep the test device on Swipe/None (or remove credentials before
> running).

---

## Navigation / Coordinate Reference (1080x2460)

Settings and Usage taps are **found dynamically at runtime** via `get_bounds_center()`
(matches `text` or `content-desc` on a `com.anthropic.claude` node). The hardcoded
coordinates below are the fallback when the node is not found:

| Action | Dynamic target | Fallback tap |
|--------|----------------|--------------|
| Open menu (back arrow) | *(no text — always hardcoded)* | `(66,182)` |
| Settings (in drawer) | `content-desc="…, Settings"` | `(104,2323)` |
| Usage (in Settings) | `text="Usage"` | `(227,913)` |
| Chat input | `class="android.widget.EditText"` | `(545,1214)` |

> Navigation uses **only in-app buttons** because the Claude app ignores the hardware back
> button (`keyevent 4`). `keyevent 3` (HOME) is used at the end of a run to background the app.

---

## Current Goal Status (as of 2026-08-05)

| Goal | Status | Verified |
|------|--------|----------|
| 24/7 operation: first message of each fresh 5-hr window sent automatically | ✅ **ACHIEVED** | Live since 01:26 IST, running continuously |
| Only first message per window (no periodic keep-alive pings) | ✅ **ACHIEVED** | TYPE1_ACTIVE never sends; only TYPE3_FRESH triggers send |
| First message tried ~2 min after reset (not 20+ min wait) | ✅ **ACHIEVED** | Reset 08:40 → first send 08:42 (2 min) |
| Send-verify backoff 2→4→6 min active | ✅ **ACHIEVED** | Cycle 2 fired at +7 min (08:49), verified at 08:50 |
| Verified at TYPE1_ACTIVE 1% (true window activation) | ✅ **ACHIEVED** | 08:50:10 confirmed 1% / 4h49m |
| Wake lock prevents deep-sleep freeze | ✅ **ACHIEVED** | `claude_keepalive_wl` held during all sleeps; no timer overrun since v4.2 |
| Smart sleep: sleeps until next-check epoch (capped 100 min) | ✅ **ACHIEVED** | Loop wakes, re-checks, re-sleeps — no polling |
| Self-healing: PID guard, stale cleanup, 15-cycle verify cap | ✅ **ACHIEVED** | Stale loop killed on restart; verify cap tested |
| Network check with IP logging, 10-min retry on failure | ✅ **ACHIEVED** | Live IP logged: 47.15.97.13, 47.15.100.68, 47.15.106.133 |
| Robust wake/unlock + notification shade handling | ✅ **ACHIEVED** | Tested multiple cycles; no stuck shade |
| Dynamic Settings/Usage targeting (v6.3) | ✅ **ACHIEVED** | `Settings found dynamically at (104 2323)`; `Usage … (227 913)` |
| Stale-lock auto-recovery (v6.3) | ✅ **ACHIEVED** | 3600s-old lock detected & cleaned, run proceeded |
| In-app drift detection (v6.4) | ✅ **ACHIEVED** | Billing page (≠Notifications) → `DRIFTED` detected → fresh relaunch → Usage reached |
| Screen wake lock while working (v6.4) | ✅ **ACHIEVED** | `Screen wake lock ON` at run start; restored to 60000 ms at exit |
| Pull-to-refresh verified | ✅ **CONFIRMED** | Swipe `(540,700)→(540,1800)` triggers a `ProgressBar`; refresh completes |
| `refresh_usage` screen-gated (v6.4) | ✅ **ACHIEVED** | Re-navigates to Usage before swiping; never parses a non-Usage screen |

---

## Appendix — Full Source Code

Both files below are the current deployed versions (keepalive **v6.4**, loop **v4.2**).
Save them locally as `claude_keepalive.sh` and `claude_loop.sh`, then follow **Step 1** to install.

### `claude_keepalive.sh` (unit script)

```sh
#!/system/bin/sh
# ============================================================
# Claude Keep-Alive – Native Android Bash (v6.4)
# Screen: 1080x2460 (change coordinates if needed)
#
# v6.4 changes:
#   - DRIFT DETECTION. detect_screen() now returns DRIFTED for ANY
#     unrecognized in-app page (not just pages with a "Go back"
#     button): Settings sub-pages (Notifications, Profile, Billing,
#     …), modals, conversations, etc. UNKNOWN is reserved for the
#     case where the UI dump could not be produced. Recovery from a
#     drift is a FRESH RELAUNCH (force-stop + relaunch) — far more
#     reliable than navigating back from a page whose layout is
#     unknown — then navigation resumes normally. send_hi() relaunches
#     to chat; refresh_usage() re-navigates to Usage before swiping.
#   - SCREEN WAKE LOCK. The loop daemon holds a partial wake lock
#     (CPU only) so the display can still turn off mid-operation
#     (screen_off_timeout is 60 s here). The keepalive now bumps
#     screen_off_timeout to 30 min while working and restores it on
#     exit, so the screen stays on for the whole run.
#
# v6.3 changes:
#   - DYNAMIC NODE TARGETING. Settings / Usage taps now use
#     get_bounds_center("text") to extract node bounds from the
#     live UI tree, so layout changes do not silently break
#     navigation. Hardcoded coords remain as fallbacks.
#   - STALE-LOCK GUARD. If claude_keepalive.lock survives an
#     abrupt kill (OOM/signal) it is auto-removed when older than
#     30 minutes instead of stalling the daemon forever.
#
# v6.2 changes:
#   - STRICT PACKAGE CHECK GATE. Every navigation/action tap is
#     wrapped in nav_step(): tap → 3s delay → verify the focused
#     window is com.anthropic.claude. On failure the app is
#     force-stopped + relaunched and navigation restarts from
#     scratch (goto_usage now retries up to 3 times).
#   - Package guards added to send_hi() and refresh_usage() so no
#     typing/swiping ever fires against a non-Claude window.
#
# v6 changes:
#   - PACKAGE-CONSTRAINED screen detection. Every UI parse is
#     gated on the focused window being com.anthropic.claude,
#     and all node searches run against a Claude-only filter.
#   - detect_screen() tells the script where it is:
#       CHAT_HOME | MENU_DRAWER | SETTINGS | USAGE | LOGIN |
#       NOT_CLAUDE | UNKNOWN
#   - goto_usage() is smart: skips navigation if already on
#     USAGE, else navigates from wherever it is.
#   - send_hi() is smart: navigates to chat from any screen.
#   - send-verify loop, state reset, lock guard preserved from
#     v5.1. Main flow aborts on LOGIN / unreachable Usage.
#
# Navigation uses ONLY in-app buttons (Claude ignores hardware
# back / keyevent 4):
#       menu button        = tap 66 182
#       Settings (drawer)  = tap 104 2323
#       Usage   (Settings) = tap 227 913
#       chat input         = found dynamically via EditText
# ============================================================

LOG="/data/local/tmp/claude_keepalive.log"
UI_XML="/data/local/tmp/ui.xml"
UI_CLAUDE="${UI_XML}.claude"
NEXT_CHECK="/data/local/tmp/claude_next_check"
MAX_TRIES=10
VERIFY_WAIT=120     # seconds (2 min) between send-verify cycles
REFRESH_EARLY=10    # wake up this many min before window expiry

CLAUDE_PKG="com.anthropic.claude"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

tap() {
    input tap "$1" "$2"
}

screen_is_on() {
    dumpsys power 2>/dev/null | grep -q "mWakefulness=Awake"
}

is_unlocked() {
    ! dumpsys window 2>/dev/null | grep -q "isKeyguardShowing=true"
}

is_home_screen() {
    dumpsys window 2>/dev/null | grep -q "mCurrentFocus=Window.*com.miui.home"
}

not_on_shade() {
    ! dumpsys window 2>/dev/null | grep -q "mCurrentFocus=Window.*NotificationShade"
}

# Format minutes → "X hr Y min"
fmt_mins() {
    local m=$1
    if [ "$m" -ge 60 ]; then
        echo "$(( m / 60 )) hr $(( m % 60 )) min"
    else
        echo "${m} min"
    fi
}

# ------------------------------------------------------------
# Screen wake lock. The loop daemon's partial wake lock keeps the
# CPU awake but NOT the display, so a long keep-alive run could
# still hit screen_off_timeout mid-operation. While working on the
# Claude app we temporarily raise the display timeout (saved and
# restored), keeping the screen on for the whole run.
# ------------------------------------------------------------
SCREEN_TIMEOUT_SAVED=""

screen_lock_on() {
    SCREEN_TIMEOUT_SAVED=$(settings get system screen_off_timeout 2>/dev/null)
    settings put system screen_off_timeout 1800000 2>/dev/null
    log "Screen wake lock ON (display timeout raised while working)"
}

screen_lock_off() {
    if [ -n "$SCREEN_TIMEOUT_SAVED" ]; then
        settings put system screen_off_timeout "$SCREEN_TIMEOUT_SAVED" 2>/dev/null
        log "Screen wake lock OFF (display timeout restored to ${SCREEN_TIMEOUT_SAVED} ms)"
    fi
    SCREEN_TIMEOUT_SAVED=""
}

# ------------------------------------------------------------
# Package + Screen detection helpers
# ------------------------------------------------------------
# Returns the package of the current focused window
current_package() {
    dumpsys window 2>/dev/null | \
        grep -oE 'mCurrentFocus=Window\{[^}]+\}' | \
        head -1 | \
        grep -oE '[a-z0-9_.]+/[a-zA-Z0-9_.]+' | \
        cut -d'/' -f1
}

# True if Claude is the focused app
is_claude_focused() {
    [ "$(current_package)" = "$CLAUDE_PKG" ]
}

# Dump UI with retry, then create a Claude-only filtered copy.
dump_ui() {
    rm -f "$UI_XML" "$UI_CLAUDE"
    i=0
    while [ $i -lt 5 ]; do
        uiautomator dump "$UI_XML" >/dev/null 2>&1
        if [ -f "$UI_XML" ] && [ -s "$UI_XML" ]; then
            # Keep a Claude copy; detection already gates on package,
            # so this just marks the dump as belonging to Claude.
            cp "$UI_XML" "$UI_CLAUDE" 2>/dev/null
            return 0
        fi
        sleep 2
        i=$((i + 1))
    done
    log "ERROR: uiautomator dump failed after $i attempts"
    return 1
}

# Claude-only XML for parsing (falls back to full dump).
claude_xml() {
    if [ -s "$UI_CLAUDE" ]; then
        echo "$UI_CLAUDE"
    else
        echo "$UI_XML"
    fi
}

# Detect current screen inside Claude.
# Possible return values:
#   CHAT_HOME | MENU_DRAWER | SETTINGS | USAGE | LOGIN |
#   DRIFTED | UNKNOWN | NOT_CLAUDE
detect_screen() {
    if ! is_claude_focused; then
        echo "NOT_CLAUDE"
        return
    fi

    local XML
    XML=$(claude_xml)
    if [ ! -f "$XML" ] || [ ! -s "$XML" ]; then
        echo "UNKNOWN"
        return
    fi

    # --- LOGIN / onboarding (check first) ---
    if grep -qE 'Continue with (Google|email)|Enter your email|verification code|Verify Email' "$XML"; then
        echo "LOGIN"
        return
    fi

    # --- USAGE page ---
    if grep -q 'Current session' "$XML" && \
       (grep -qE '[0-9]+% used' "$XML" || grep -q 'Resets in' "$XML"); then
        echo "USAGE"
        return
    fi

    # --- SETTINGS page ---
    if grep -q 'text="Usage"' "$XML" && grep -q 'text="Settings"' "$XML"; then
        echo "SETTINGS"
        return
    fi

    # --- MENU / DRAWER ---
    if grep -qE 'text="(New chat|Chats|Projects)"' "$XML"; then
        echo "MENU_DRAWER"
        return
    fi

    # --- CHAT HOME (EditText present) ---
    if grep -q 'class="android.widget.EditText"' "$XML"; then
        echo "CHAT_HOME"
        return
    fi

    # --- Chat fallback text signals ---
    if grep -qE 'Chat with Claude|Ask Claude' "$XML"; then
        echo "CHAT_HOME"
        return
    fi

    # --- DRIFTED: inside Claude but on ANY unrecognized in-app page.
    # --- This is the fallback for every page that is not one of the
    # --- known screens above — a Settings sub-page (Notifications,
    # --- Profile, Billing, …), a modal, a conversation, or any other
    # --- page the app has moved to. UNKNOWN is now reserved for the
    # --- case where the UI dump itself could not be produced.
    echo "DRIFTED"
}

# Convenience wrapper: dump + detect in one call
get_screen() {
    dump_ui || { echo "UNKNOWN"; return 1; }
    detect_screen
}

# ------------------------------------------------------------
# Ensure device is awake + unlocked + on home screen
# ------------------------------------------------------------
ensure_screen_ready() {
    log "--- Screen readiness check ---"

    if screen_is_on; then
        log "Screen already ON"
    else
        log "Screen OFF → waking"
        input keyevent 26
        sleep 3
        if ! screen_is_on; then
            log "ERROR: could not wake screen"
            return 1
        fi
        # Small settle after wake before touching the lockscreen.
        sleep 1
    fi

    if is_unlocked; then
        log "Already unlocked"
    else
        log "Locked → dismissing keyguard"
        wm dismiss-keyguard 2>/dev/null
        sleep 2
        if ! is_unlocked; then
            # Lockscreen may need a swipe; use a short upward drag only
            # if still locked, then re-check before any shade interaction.
            log "Still locked → short unlock swipe"
            input swipe 540 1800 540 1200 150
            sleep 2
        fi
        i=0
        while [ $i -lt 3 ]; do
            if is_unlocked; then
                break
            fi
            log "Still locked → retry dismiss-keyguard ($i)"
            wm dismiss-keyguard 2>/dev/null
            sleep 2
            i=$((i + 1))
        done
        if ! is_unlocked; then
            log "ERROR: could not unlock device"
            return 1
        fi
        log "Unlocked OK"
    fi

    # Only handle the notification shade AFTER we are confirmed unlocked,
    # so the unlock swipe never misinterprets as a shade pull.
    if not_on_shade; then
        log "No notification shade"
    else
        log "Notification shade focused → collapsing"
        cmd statusbar collapse 2>/dev/null
        sleep 2
        input swipe 540 400 540 2400 300
        sleep 2
    fi

    if is_home_screen; then
        log "On HOME screen → proceeding"
        return 0
    else
        log "Not on home screen → pressing HOME"
        input keyevent 3
        sleep 2
        if is_home_screen; then
            log "Now on HOME screen → proceeding"
            return 0
        fi
        log "WARNING: not confirmed on home screen, continuing anyway"
        return 0
    fi
}

# ------------------------------------------------------------
# Parse Usage card and classify state (Claude-only nodes).
# Sets: USAGE_PCT, REMAIN_MIN, STATE
# ------------------------------------------------------------
parse_usage() {
    USAGE_PCT=100
    REMAIN_MIN=0
    STATE="UNKNOWN"

    local XML
    XML=$(claude_xml)
    [ -f "$XML" ] || return 1

    PCT_LINE=$(grep -oE '[0-9]+% used' "$XML" | head -1)
    if [ -n "$PCT_LINE" ]; then
        USAGE_PCT=$(echo "$PCT_LINE" | grep -oE '[0-9]+')
    fi

    RESET_LINE=$(grep -oE 'Resets in [0-9]+ hr [0-9]+ min|Resets in [0-9]+ min' "$XML" | head -1)
    if [ -n "$RESET_LINE" ]; then
        if echo "$RESET_LINE" | grep -q "hr"; then
            H=$(echo "$RESET_LINE" | grep -oE '[0-9]+' | head -1)
            M=$(echo "$RESET_LINE" | grep -oE '[0-9]+' | tail -1)
            REMAIN_MIN=$((H * 60 + M))
        else
            REMAIN_MIN=$(echo "$RESET_LINE" | grep -oE '[0-9]+')
        fi
    fi

    if [ "$USAGE_PCT" -ge 100 ]; then
        STATE="TYPE2_LIMIT"
    elif [ -z "$RESET_LINE" ]; then
        STATE="TYPE3_FRESH"
    else
        STATE="TYPE1_ACTIVE"
    fi

    log "Usage: ${USAGE_PCT}% | Remaining: $(fmt_mins $REMAIN_MIN) | State: ${STATE}"
}

# ------------------------------------------------------------
# Launch Claude (fresh chat home, drawer closed)
# ------------------------------------------------------------
launch_claude() {
    am force-stop "$CLAUDE_PKG"
    sleep 2
    monkey -p "$CLAUDE_PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
    sleep 6
}

# ------------------------------------------------------------
# Package-enforced navigation step: tap, let the UI react, then
# verify the focused window is still Claude. If the app crashed,
# a system dialog grabbed focus, or HOME/shade stole it, relaunch
# Claude and signal failure so the caller restarts navigation.
# ------------------------------------------------------------
nav_step() {
    local x="$1" y="$2"
    input tap "$x" "$y"
    sleep 3
    if ! is_claude_focused; then
        log "PACKAGE CHECK: focus lost after tap (${x},${y}) → focused: $(current_package). Relaunching..."
        launch_claude
        return 1
    fi
    return 0
}

# ------------------------------------------------------------
# Dynamic node targeting: find a Claude-owned node whose text OR
# content-desc contains the given label and print its center as
# "X Y". Returns nothing on failure so the caller falls back to a
# hardcoded coordinate. The full <node ...> element is captured
# first so the package= attribute (which may precede the matched
# attribute) is included, then filtered to com.anthropic.claude
# to avoid e.g. MIUI's home-screen Settings shortcut. Used for
# Settings / Usage so layout changes do not break navigation.
# ------------------------------------------------------------
get_bounds_center() {
    local label="$1"
    local XML
    XML=$(claude_xml)
    [ -f "$XML" ] || return 1
    local NODE attr B X1 Y1 X2 Y2
    NODE=""
    for attr in text content-desc; do
        NODE=$(grep -o '<node[^>]*>' "$XML" | \
               grep "${attr}=\"[^\"]*${label}[^\"]*\"" | \
               grep 'package="com.anthropic.claude"' | head -1)
        [ -n "$NODE" ] && break
    done
    [ -n "$NODE" ] || return 1
    B=$(echo "$NODE" | grep -oE '\[[0-9]+,[0-9]+\]\[[0-9]+,[0-9]+\]' | head -1)
    [ -n "$B" ] || return 1
    X1=$(echo "$B" | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\1/')
    Y1=$(echo "$B" | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\2/')
    X2=$(echo "$B" | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\3/')
    Y2=$(echo "$B" | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\4/')
    echo "$(( (X1 + X2) / 2 )) $(( (Y1 + Y2) / 2 ))"
}

# Navigate to Settings (dynamic text/content-desc target, hardcoded fallback).
goto_settings() {
    local c
    dump_ui
    c=$(get_bounds_center "Settings")
    if [ -n "$c" ]; then
        log "Settings found dynamically at ($c)"
        nav_step $c
    else
        log "Settings node not found → using fallback (104,2323)"
        nav_step 104 2323
    fi
}

# Navigate to Usage (dynamic text/content-desc target, hardcoded fallback).
goto_usage_item() {
    local c
    dump_ui
    c=$(get_bounds_center "Usage")
    if [ -n "$c" ]; then
        log "Usage found dynamically at ($c)"
        nav_step $c
    else
        log "Usage node not found → using fallback (227,913)"
        nav_step 227 913
    fi
}

# ------------------------------------------------------------
# Navigate to Usage page (screen-aware + package-enforced).
# Every tap is followed by a post-delay package check (nav_step);
# if focus is lost, Claude is relaunched and navigation restarts
# from scratch (max 3 attempts). parse_usage is called on success.
# ------------------------------------------------------------
goto_usage() {
    local screen attempt
    attempt=0
    while [ $attempt -lt 3 ]; do
        attempt=$((attempt + 1))
        screen=$(get_screen)
        log "Screen before goto_usage (attempt ${attempt}): $screen"

        case "$screen" in
            USAGE)
                log "Already on Usage page"
                ;;
            DRIFTED)
                # Inside Claude but on an unrecognized page (Settings
                # sub-page, modal, conversation, etc.). Recovery is a
                # fresh relaunch — force-stop + relaunch is far more
                # reliable than trying to navigate back from an unknown
                # page whose layout we do not know. After the relaunch,
                # simply restart the loop so the normal CHAT_HOME path
                # (menu → Settings → Usage) handles navigation.
                log "Drifted to an unrecognized in-app page → relaunching fresh"
                launch_claude
                sleep 2
                continue
                ;;
            SETTINGS)
                log "On Settings → tapping Usage"
                goto_usage_item || continue
                sleep 2
                ;;
            MENU_DRAWER)
                log "Drawer open → tapping Settings then Usage"
                goto_settings || continue
                sleep 2
                goto_usage_item || continue
                sleep 2
                ;;
            CHAT_HOME|UNKNOWN)
                log "On chat (or unknown) → menu → Settings → Usage"
                nav_step 66 182 || continue          # menu (back-arrow, no text → hardcoded)
                sleep 2
                goto_settings || continue
                sleep 2
                goto_usage_item || continue
                sleep 2
                ;;
            NOT_CLAUDE|LOGIN)
                log "Not inside Claude or on login → relaunching Claude"
                launch_claude
                sleep 2
                nav_step 66 182 || continue
                sleep 2
                goto_settings || continue
                sleep 2
                goto_usage_item || continue
                sleep 2
                ;;
            *)
                log "Unexpected screen ($screen) → default menu → Settings → Usage"
                nav_step 66 182 || continue
                sleep 2
                goto_settings || continue
                sleep 2
                goto_usage_item || continue
                sleep 2
                ;;
        esac

        # Final verification (package-gated via get_screen/detect_screen)
        screen=$(get_screen)
        log "Screen after navigation (attempt ${attempt}): $screen"
        if [ "$screen" = "USAGE" ]; then
            parse_usage
            return 0
        fi
        log "WARNING: not on Usage page (now on $screen) → retrying navigation from scratch"
        launch_claude
        sleep 2
    done
    log "ERROR: failed to reach Usage page after $attempt attempts"
    return 1
}

# ------------------------------------------------------------
# Focus the chat input field (Claude-only, found dynamically).
# Falls back to known fresh-chat coordinate if EditText not found.
# ------------------------------------------------------------
focus_input() {
    dump_ui
    local XML
    XML=$(claude_xml)
    BOUNDS=$(grep -o 'class="android.widget.EditText"[^>]*bounds="\[[0-9]*,[0-9]*\]\[[0-9]*,[0-9]*\]"' "$XML" | head -1)
    if [ -n "$BOUNDS" ]; then
        B=$(echo "$BOUNDS" | grep -oE '\[[0-9]+,[0-9]+\]\[[0-9]+,[0-9]+\]')
        X1=$(echo "$B" | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\1/')
        Y1=$(echo "$B" | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\2/')
        X2=$(echo "$B" | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\3/')
        Y2=$(echo "$B" | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\4/')
        CX=$(( (X1 + X2) / 2 ))
        CY=$(( (Y1 + Y2) / 2 ))
        log "Chat input found at center (${CX},${CY})"
        tap "$CX" "$CY"
    else
        log "EditText not found → using fresh-chat fallback (545,1214)"
        tap 545 1214
    fi
    sleep 2
}

# ------------------------------------------------------------
# Send keep-alive message (screen-aware).
# ------------------------------------------------------------
send_hi() {
    local screen TS TS_IST MSG
    TS=$(date +%s 2>/dev/null || echo $RANDOM)
    # Full datetime in IST; spaces are escaped as %s for `input text`.
    TS_IST=$(TZ=Asia/Kolkata date '+%Y-%m-%d %H:%M:%S IST' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S')
    MSG="Hello%sFrom%sIndia?%s${TS_IST}"

    screen=$(get_screen)
    log "Screen before send: $screen"

    case "$screen" in
        CHAT_HOME|MENU_DRAWER)
            log "Already in a good place for sending"
            ;;
        DRIFTED)
            # Drifted to an unrecognized in-app page before send.
            # Fresh relaunch is the reliable recovery — we cannot trust
            # navigation back from an unknown layout.
            log "Drifted to an unrecognized in-app page before send → relaunching fresh"
            launch_claude
            sleep 2
            screen=$(get_screen)
            if [ "$screen" != "CHAT_HOME" ] && [ "$screen" != "MENU_DRAWER" ]; then
                log "Not on chat after relaunch (${screen}) → relaunching Claude"
                launch_claude
            fi
            ;;
        USAGE|SETTINGS)
            log "Leaving Usage/Settings → back to chat via menu button"
            tap 66 182
            sleep 2
            screen=$(get_screen)
            if [ "$screen" != "CHAT_HOME" ] && [ "$screen" != "MENU_DRAWER" ]; then
                log "Still not on chat → relaunching Claude"
                launch_claude
            fi
            ;;
        *)
            log "Not on chat → relaunching Claude"
            launch_claude
            ;;
    esac

    # Package gate before typing: if we lost Claude focus, stop.
    if ! is_claude_focused; then
        log "PACKAGE CHECK: not in Claude before send → relaunching"
        launch_claude
        sleep 2
    fi

    focus_input
    input text "$MSG"
    sleep 2
    # re-focus in case the keyboard stole focus
    focus_input
    sleep 1
    if ! is_claude_focused; then
        log "PACKAGE CHECK: lost Claude focus during send → relaunching"
        launch_claude
        sleep 2
    fi
    input keyevent 66
    log "Sent: Hello From India? ${TS_IST}"
    sleep 6
}

# ------------------------------------------------------------
# Pull-to-refresh on the current (Usage) screen, then re-parse.
# Package-gated: never swipe unless Claude still has focus.
# Screen-gated: never swipe unless we are actually on Usage (a
# pull-to-refresh gesture only makes sense there), otherwise
# re-navigate first.
# ------------------------------------------------------------
refresh_usage() {
    local s
    if ! is_claude_focused; then
        log "PACKAGE CHECK: not in Claude before refresh → relaunching"
        launch_claude
        sleep 2
    fi
    s=$(get_screen)
    if [ "$s" != "USAGE" ]; then
        log "Not on Usage before refresh (now on $s) → re-navigating to Usage"
        goto_usage || { log "Could not reach Usage for refresh → skipping"; return 1; }
    fi
    log "Pull-to-refresh on Usage screen"
    input swipe 540 700 540 1800 400
    sleep 4
    dump_ui
    parse_usage
}

# ------------------------------------------------------------
# Verify the current STATE matches the expected scenario.
#   FIRST     : message sent from fresh window => TYPE1_ACTIVE, usage 1-99%
#   KEEPALIVE : message sent in active window   => still TYPE1_ACTIVE
# ------------------------------------------------------------
is_verified() {
    case "$1" in
        FIRST)
            [ "$STATE" = "TYPE1_ACTIVE" ] && [ "$USAGE_PCT" -ge 1 ] && [ "$USAGE_PCT" -lt 100 ]
            ;;
        KEEPALIVE)
            [ "$STATE" = "TYPE1_ACTIVE" ]
            ;;
        *)
            return 1
            ;;
    esac
}

# ------------------------------------------------------------
# Verify after sending the FIRST message of a fresh window.
# After the send, pull-to-refresh on the Usage screen. If the state
# still hasn't changed (still TYPE3_FRESH / pending), wait incrementally
# (2 min, then 4, then 6, ...) and retry. Keeps checking & trying until
# a NEW state appears on the Usage screen. No cap on attempts.
# ------------------------------------------------------------
send_verify_loop() {
    local scenario="$1"
    local try=1
    local wait="$VERIFY_WAIT"   # starts at 2 min
    local max_cycles=15         # safety: avoid holding the lock forever

    while :; do
        log "=== Send-verify cycle ${try} (${scenario}) ==="

        # Safety cap: if the Usage page never updates (network/app glitch),
        # don't hold the lock forever. Retry on the next scheduled run.
        if [ "$try" -gt "$max_cycles" ]; then
            log "Giving up after ${max_cycles} cycles (state still ${STATE}) → retry on next scheduled run"
            return 1
        fi

        # 1) CHECK current state (should be on Usage page).
        parse_usage

        # Verified already => done.
        if is_verified "$scenario"; then
            log "VERIFIED: ${STATE}, ${USAGE_PCT}% → new state obtained"
            return 0
        fi

        # If a NEW state appeared that is not the pending fresh window,
        # we are done (message delivered, window no longer fresh).
        if [ "$STATE" != "TYPE3_FRESH" ]; then
            log "New state obtained: ${STATE} (${USAGE_PCT}%) → stopping verify loop"
            return 0
        fi

        # 2) SEND the first message (only on the first cycle).
        if [ "$try" -eq 1 ]; then
            log "Sending first message (cycle ${try})"
            send_hi
        else
            log "Message already sent (cycle ${try}) → only re-checking"
        fi

        # 3) CHECK again via pull-to-refresh on the Usage screen.
        goto_usage || { log "Could not reach Usage after send → retrying later"; }
        log "Not yet verified (${STATE}, ${USAGE_PCT}%) → pull-to-refresh"
        refresh_usage

        # After refresh, accept success or any new non-fresh state.
        if is_verified "$scenario"; then
            log "VERIFIED after refresh: ${STATE}, ${USAGE_PCT}% → new state obtained"
            return 0
        fi
        if [ "$STATE" != "TYPE3_FRESH" ]; then
            log "New state obtained after refresh: ${STATE} (${USAGE_PCT}%) → stopping verify loop"
            return 0
        fi

        # 4) Still fresh/pending → wait incrementally, then retry.
        log "Still pending (${STATE}, ${USAGE_PCT}%) → waiting $(fmt_secs_keep $wait) before next check"
        sleep "$wait"
        wait=$(( wait + VERIFY_WAIT ))   # 2 → 4 → 6 → ... minutes
        try=$((try + 1))
    done

    # Unreachable (infinite loop), kept for safety.
    log "FAILED: verify loop exited unexpectedly"
    return 1
}

# Format seconds → "X min Y S" (used in the verify loop log).
fmt_secs_keep() {
    local s=$1
    local m=$(( s / 60 ))
    local r=$(( s % 60 ))
    if [ "$m" -gt 0 ]; then
        echo "${m} min ${r} S"
    else
        echo "${r} S"
    fi
}

# ------------------------------------------------------------
# Minimal network check (free AWS checkip – returns plain IP).
# Tries curl, then wget, then ping as fallback. 3 attempts each.
# ------------------------------------------------------------
has_network() {
    local i=0
    while [ $i -lt 3 ]; do
        if command -v curl >/dev/null 2>&1; then
            if curl -s --connect-timeout 5 --max-time 8 \
                https://checkip.amazonaws.com >/dev/null 2>&1; then
                return 0
            fi
        elif command -v wget >/dev/null 2>&1; then
            if wget -q -T 5 -O /dev/null https://checkip.amazonaws.com 2>/dev/null; then
                return 0
            fi
        else
            # Fallback: ping Google DNS (no HTTP needed)
            if ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
                return 0
            fi
        fi
        sleep 2
        i=$((i + 1))
    done
    return 1
}

# ------------------------------------------------------------
# Reset everything (stored state, counters) for a clean next run.
# ------------------------------------------------------------
reset_state() {
    INITIAL_STATE="NONE"
    INITIAL_USAGE=0
    log "State reset → INITIAL_STATE=${INITIAL_STATE}"
}

# ============================================================
# Main
# ============================================================
log "=== Starting keep-alive ==="

# ---- Lock guard: don't run if a previous instance is still in
# ---- its 2-min internal send-verify loop. A stale lock from an
# ---- abrupt kill (OOM, signal) is detected by age and removed.
LOCK="/data/local/tmp/claude_keepalive.lock"
if [ -f "$LOCK" ]; then
    lock_age=$(( $(date +%s) - $(stat -c %Y "$LOCK" 2>/dev/null || echo 0) ))
    if [ "$lock_age" -gt 1800 ]; then
        log "WARNING: stale lock detected (${lock_age}s old) → cleaning up"
        rm -f "$LOCK"
    else
        log "Another keep-alive instance still running → exiting this cycle"
        echo "" >> "$LOG"
        exit 0
    fi
fi
touch "$LOCK"
trap 'rm -f "$LOCK"; screen_lock_off' EXIT

# ---------- Network check ----------
if ! has_network; then
    log "ABORT: no network access → scheduling retry in 10 min"
    now=$(date +%s)
    echo $(( now + 10 * 60 )) > "$NEXT_CHECK"
    echo "" >> "$LOG"
    exit 1
fi
WAN_IP=$(curl -s --connect-timeout 5 --max-time 8 https://checkip.amazonaws.com 2>/dev/null)
log "Network OK (IP: ${WAN_IP:-unknown})"

if ! ensure_screen_ready; then
    log "ABORT: device not ready"
    echo "" >> "$LOG"
    exit 1
fi

# Keep the screen on while we drive the Claude app.
screen_lock_on

# ---------- Launch Claude ----------
launch_claude

# ---------- Initial screen detection ----------
screen=$(get_screen)
log "Initial screen: $screen"

if [ "$screen" = "LOGIN" ]; then
    log "LOGIN screen detected – cannot proceed automatically"
    exit 1
fi

# ---------- Navigate to Usage + FIRST state check ----------
if ! goto_usage; then
    log "Could not reach Usage page – aborting this run"
    echo "" >> "$LOG"
    exit 1
fi

# ---------- Store initial state ----------
INITIAL_STATE="$STATE"
INITIAL_USAGE="$USAGE_PCT"
log "Stored initial state: ${INITIAL_STATE} (usage ${INITIAL_USAGE}%)"

# ---------- Decision ----------
case "$STATE" in
    TYPE3_FRESH)
        log "TYPE3: fresh window, 5-hr timer not active → send & verify first message"
        send_verify_loop FIRST
        ;;
    TYPE1_ACTIVE)
        log "TYPE1: window already active (${USAGE_PCT}% used, $(fmt_mins $REMAIN_MIN) left) → nothing to send"
        ;;
    TYPE2_LIMIT)
        log "TYPE2: 100% limit reached → waiting for reset, skipping send"
        ;;
    *)
        log "UNKNOWN state → skipping"
        ;;
esac

# ---------- Schedule the next check ----------
# Goal: only send the FIRST message of each 5-hr window, then go quiet.
# The loop sleeps until just before the window would expire, so we only
# wake the device when a fresh window needs its first message.
now=$(date +%s)
case "$STATE" in
    TYPE1_ACTIVE)
        if [ "$REMAIN_MIN" -gt "$REFRESH_EARLY" ]; then
            NEXT=$(( now + (REMAIN_MIN - REFRESH_EARLY) * 60 ))
            log "Scheduling next check in $(fmt_mins $((REMAIN_MIN - REFRESH_EARLY))) (window still active, $USAGE_PCT% used)"
        else
            NEXT=$(( now + 10 * 60 ))
            log "Scheduling next check in 10 min (window near expiry, $REMAIN_MIN min left)"
        fi
        ;;
    TYPE2_LIMIT)
        # Wake just after the reset so the first message is tried promptly
        # (the send-verify loop's 2→4→6 min backoff then handles retries).
        # If the reset time is unknown (REMAIN_MIN=0), fall back to a short poll.
        if [ "$REMAIN_MIN" -gt 0 ]; then
            NEXT=$(( now + (REMAIN_MIN + 2) * 60 ))
            log "Scheduling next check in $(fmt_mins $((REMAIN_MIN + 2))) (100% used, resetting in $REMAIN_MIN min)"
        else
            NEXT=$(( now + 5 * 60 ))
            log "Scheduling next check in 5 min (100% limit used, reset time unknown)"
        fi
        ;;
    TYPE3_FRESH)
        NEXT=$(( now + 5 * 60 ))
        log "Scheduling next check in 5 min (fresh window, retry first message)"
        ;;
    *)
        NEXT=$(( now + 10 * 60 ))
        log "Scheduling next check in 10 min (unknown state)"
        ;;
esac
echo "$NEXT" > "$NEXT_CHECK"

# ---------- Reset everything for next main-loop run ----------
reset_state

# ---------- Bring Claude to background ----------
input keyevent 3   # HOME

log "=== Finished ==="
echo "" >> "$LOG"
```

### `claude_loop.sh` (daemon)

```sh
#!/system/bin/sh

# Claude Keep-Alive – Main Loop (v4.2)
# 24/7: sends the FIRST message of each 5-hr window whenever the window
# is fresh, day or night. Uses smart sleep: reads the next-check
# timestamp written by claude_keepalive.sh and sleeps until then,
# instead of polling every 5 minutes.
#
# v4.2: Holds a partial wake lock during sleep so the device cannot
# deep-sleep (which freezes a userspace `sleep` timer and stalls the
# loop). Lock released after waking.

SCRIPT=/data/local/tmp/claude_keepalive.sh
LOG=/data/local/tmp/claude_loop.log
NEXT_CHECK=/data/local/tmp/claude_next_check
PID_FILE=/data/local/tmp/claude_loop.pid
WL_NAME="claude_keepalive_wl"
WL_PATH="/sys/power/wake_lock"
MAX_SLEEP=6000      # cap a single sleep at 100 min (safety)

# Format seconds → "X hr Y min" / "X min" / "X S" (omit empty parts)
fmt_secs() {
    local s=$1
    local h=$(( s / 3600 ))
    local m=$(( (s % 3600) / 60 ))
    local r=$(( s % 60 ))
    local out=""
    [ "$h" -gt 0 ] && out="${h} hr"
    if [ "$m" -gt 0 ]; then
        out="${out:+$out }${m} min"
    elif [ "$r" -gt 0 ] && [ "$h" -eq 0 ]; then
        out="${out:+$out }${r} S"
    fi
    echo "$out"
}

# Epoch → IST time (IST = UTC + 5:30)
epoch_to_ist() {
    date -d "@$1" '+%I:%M %p' 2>/dev/null || echo "??:??"
}

# Remove any stale loop/keepalive instance WITHOUT killing ourselves.
# Uses a PID file so the new instance is always the sole runner.
cleanup_stale() {
    local old=""
    if [ -f "$PID_FILE" ]; then
        old=$(cat "$PID_FILE" 2>/dev/null)
        rm -f "$PID_FILE"
    fi
    # Kill the previous loop (recorded PID), if it is still alive.
    if [ -n "$old" ] && [ "$old" != "$$" ]; then
        if kill -0 "$old" 2>/dev/null; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning stale loop PID $old" >> "$LOG"
            kill -9 "$old" 2>/dev/null
            sleep 1
        fi
    fi
    # Kill any orphaned keep-alive children, but never this shell or its loop.
    for p in $(pgrep -f 'claude_keepalive.sh'); do
        [ "$p" = "$$" ] && continue
        # Only kill if the keeper is not one of our own children.
        if [ "$(ps -o ppid= -p "$p" 2>/dev/null)" != "$$" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaning orphaned keepalive PID $p" >> "$LOG"
            kill -9 "$p" 2>/dev/null
        fi
    done
    # Record our own PID as the current sole instance.
    echo "$$" > "$PID_FILE"
}

# Take a partial wake lock so the device stays awake during a long sleep.
wl_acquire() {
    echo "$WL_NAME" > "$WL_PATH" 2>/dev/null
}
wl_release() {
    echo "$WL_NAME" > /sys/power/wake_unlock 2>/dev/null
}

sleep_until() {
    # $1 = epoch timestamp to wake up at
    local now wait target
    now=$(date +%s)
    wait=$(( $1 - now ))
    if [ "$wait" -le 0 ]; then
        return 0
    fi
    if [ "$wait" -gt "$MAX_SLEEP" ]; then
        wait=$MAX_SLEEP
    fi
    target=$(epoch_to_ist "$1")
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sleeping $(fmt_secs $wait) (wake at $target IST)" >> "$LOG"
    wl_acquire
    sleep "$wait"
    wl_release
}

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Loop started (24/7, smart sleep)" >> "$LOG"
cleanup_stale

while true; do
    # Run the keep-alive only when it is due.
    if [ -f "$NEXT_CHECK" ]; then
        due=$(cat "$NEXT_CHECK")
        now=$(date +%s)
        if [ "$due" -le "$now" ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Due → running keep-alive" >> "$LOG"
            "$SCRIPT" >> "$LOG" 2>&1
        else
            sleep_until "$due"
        fi
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] No schedule yet → running keep-alive (initial)" >> "$LOG"
        "$SCRIPT" >> "$LOG" 2>&1
    fi
done
```
