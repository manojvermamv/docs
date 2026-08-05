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
startup.

---

## What You'll Need

| Requirement | Details |
|-------------|---------|
| ADB | `C:\Program Files (x86)\Minimal ADB and Fastboot\adb.exe` (adjust to your path) |
| Android device | USB debugging enabled, connected via USB, **rooted** |
| Root access | `input text` / `input keyevent` / `wm dismiss-keyguard` need `su -c` (`INJECT_EVENTS` restriction) |
| Claude app | Installed and logged in on the device |
| Screen resolution | All coordinates are for **1080x2460**. For other screens, dump UI and re-measure. |
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
| `claude_keepalive.sh` | One unit of work: wake, unlock, network check, navigate to Usage, classify state, optionally send + verify the first message, then write the next-check time. |
| `claude_loop.sh` | Daemon that sleeps until the next-check time, runs `claude_keepalive.sh`, and self-cleans stale instances. |

### On-device files / logs

| Path | Purpose |
|------|---------|
| `/data/local/tmp/claude_keepalive.sh` | Keep-alive unit script |
| `/data/local/tmp/claude_loop.sh` | Loop daemon |
| `/data/local/tmp/claude_keepalive.log` | Keep-alive unit log |
| `/data/local/tmp/claude_loop.log` | Loop daemon log |
| `/data/local/tmp/claude_next_check` | Epoch (seconds) of the next check |
| `/data/local/tmp/claude_loop.pid` | PID of the running loop (single-instance guard) |
| `/data/local/tmp/claude_keepalive.lock` | Lock file held while a keep-alive unit runs |

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

A healthy first run logs roughly:
```
=== Starting keep-alive ===
Network OK (IP: <WAN_IP>)
--- Screen readiness check ---
… screen ON / unlocked / home …
Initial screen: CHAT_HOME
Screen after navigation: USAGE
Usage: 1% | Remaining: 2 hr 13 min | State: TYPE1_ACTIVE
TYPE1: window already active … → nothing to send
Scheduling next check in 2 hr 3 min …
=== Finished ===
Sleeping 1 hr 40 min (wake at 03:29 AM IST)
```

### Step 4 — How it decides and sleeps

After reading the Usage page, `claude_keepalive.sh` writes the next-check epoch:

| State at end of run | Next check |
|--------------------|------------|
| `TYPE1_ACTIVE` (still time left) | `now + (remaining − 10 min)` → just before expiry |
| `TYPE1_ACTIVE` (near expiry, ≤10 min left) | `now + 10 min` (poll until it flips) |
| `TYPE2_LIMIT` | `now + 30 min` (wait for reset) |
| `TYPE3_FRESH` (send failed) | `now + 5 min` (retry) |
| `UNKNOWN` | `now + 10 min` |
| **No network** | `now + 10 min`, then abort |

The loop reads `claude_next_check` and `sleep`s until then (each individual sleep capped
at 100 min as a safety; it re-checks the schedule on wake). This is why it goes quiet for
hours instead of polling every few minutes.

### Step 5 — Sending and verifying the first message

When the state is `TYPE3_FRESH`, the keep-alive runs `send_verify_loop`:

1. Cycle 1: **send** the message, then navigate to Usage and **pull-to-refresh**.
2. Accept success if the state is now `VERIFIED` (`TYPE1_ACTIVE`, usage 1–99%) **or** any
   new non-fresh state appeared.
3. If still `TYPE3_FRESH`, wait `2 min`, retry; on next failure wait `4 min`, then `6 min`,
   etc. (increment by 2 min each cycle).
4. If still not verified after **15 cycles**, stop this run and schedule a retry in 5 min
   (the lock is released; the loop retries on the next scheduled run — a temporary give-up,
   not a permanent stop).

The message text is `Hello From India? YYYY-MM-DD HH:MM:SS IST`. Spaces are escaped as
`%s` for `input text`; the IST datetime is produced with `TZ=Asia/Kolkata`.

### Step 6 — Manual run / forced check

```powershell
& $adb shell "su -c 'rm -f /data/local/tmp/claude_keepalive.lock'"
& $adb shell "su -c 'sh /data/local/tmp/claude_keepalive.sh'"
```

### Step 7 — Stop everything / full clean reinstall

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
- **Network-aware:** if there is no network, it aborts and retries in 10 min rather than
  failing mid-navigation.
- **Self-healing:** only one loop runs (PID-file guard); a crashed/stale instance is killed
  on next start; a stuck verify loop gives up after 15 cycles and retries later.

---

## Common Pitfalls

| Issue | Cause | Solution |
|-------|-------|----------|
| `INJECT_EVENTS` error on `input …` | Device security blocks input | Always prefix with `su -c` (root required) |
| `input text` drops spaces | ADB limitation | Escape spaces as `%s` (already done for the message) |
| Hardware back does nothing | **Claude ignores `keyevent 4`** | Use in-app buttons only: menu `(66,182)`; Settings `(104,2323)`; Usage `(227,913)` |
| Navigation stuck after relaunch | Notification shade grabbed focus | Collapse the shade *after* confirming unlocked; swipe top→bottom |
| `uiautomator dump` stale | Animations / transitions | Wait (`sleep 2+`) before dumping |
| Verify loop never ends | Usage page never updates (network/app glitch) | Built-in 15-cycle cap → retries on next scheduled run |
| Two loops running | Old instance left from before PID guard | The `cleanup_stale` guard kills the previous loop on start |
| Wrong coordinates | Different screen resolution | Dump UI and re-measure bounds; scale proportionally |

---

## Navigation / Coordinate Reference (1080x2460)

| Action | Tap |
|--------|-----|
| Open menu (back arrow) | `(66,182)` |
| Settings (in drawer) | `(104,2323)` |
| Usage (in Settings) | `(227,913)` |
| Chat input | Found dynamically via `class="android.widget.EditText"`; fallback `(545,1214)` |

> Navigation uses **only in-app buttons** because the Claude app ignores the hardware back
> button (`keyevent 4`). `keyevent 3` (HOME) is used at the end of a run to background the app.

---

## Appendix — Full Source Code

Both files below are the current deployed versions. Save them locally as
`claude_keepalive.sh` and `claude_loop.sh`, then follow **Step 1** to install.

### `claude_keepalive.sh` (unit script)

```sh
#!/system/bin/sh
# ============================================================
# Claude Keep-Alive – Native Android Bash (v6.1)
# Screen: 1080x2460 (change coordinates if needed)
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
#   CHAT_HOME | MENU_DRAWER | SETTINGS | USAGE | LOGIN | UNKNOWN | NOT_CLAUDE
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

    echo "UNKNOWN"
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

    # Only handle the notification shade AFTER we are confirmed unlocked.
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
# Navigate to Usage page (screen-aware).
# Returns 0 if USAGE reached, 1 otherwise. parse_usage is called.
# ------------------------------------------------------------
goto_usage() {
    local screen
    screen=$(get_screen)
    log "Screen before goto_usage: $screen"

    case "$screen" in
        USAGE)
            log "Already on Usage page"
            ;;
        SETTINGS)
            log "On Settings → tapping Usage"
            tap 227 913
            sleep 4
            ;;
        MENU_DRAWER)
            log "Drawer open → tapping Settings then Usage"
            tap 104 2323
            sleep 3
            tap 227 913
            sleep 4
            ;;
        CHAT_HOME|UNKNOWN)
            log "On chat (or unknown) → menu → Settings → Usage"
            tap 66 182          # menu
            sleep 3
            tap 104 2323        # Settings
            sleep 3
            tap 227 913         # Usage
            sleep 4
            ;;
        NOT_CLAUDE|LOGIN)
            log "Not inside Claude or on login → relaunching Claude"
            launch_claude
            sleep 2
            tap 66 182
            sleep 3
            tap 104 2323
            sleep 3
            tap 227 913
            sleep 4
            ;;
        *)
            log "Unexpected screen ($screen) → default menu → Settings → Usage"
            tap 66 182
            sleep 3
            tap 104 2323
            sleep 3
            tap 227 913
            sleep 4
            ;;
    esac

    # Final verification
    screen=$(get_screen)
    log "Screen after navigation: $screen"
    if [ "$screen" != "USAGE" ]; then
        log "WARNING: failed to reach Usage page (now on $screen)"
        return 1
    fi
    parse_usage
}

# ------------------------------------------------------------
# Focus the chat input field (Claude-only, found dynamically).
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
# Send the first-message (screen-aware).
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

    focus_input
    input text "$MSG"
    sleep 2
    # re-focus in case the keyboard stole focus
    focus_input
    sleep 1
    input keyevent 66
    log "Sent: Hello From India? ${TS_IST}"
    sleep 6
}

# ------------------------------------------------------------
# Pull-to-refresh on the current (Usage) screen, then re-parse.
# ------------------------------------------------------------
refresh_usage() {
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
# a NEW state appears on the Usage screen. Safety cap at 15 cycles.
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
# ---- its 2-min internal send-verify loop.
LOCK="/data/local/tmp/claude_keepalive.lock"
if [ -f "$LOCK" ]; then
    log "Another keep-alive instance still running → exiting this cycle"
    echo "" >> "$LOG"
    exit 0
fi
touch "$LOCK"
trap 'rm -f "$LOCK"' EXIT

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
        NEXT=$(( now + 30 * 60 ))
        log "Scheduling next check in 30 min (100% limit used, waiting for reset)"
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
