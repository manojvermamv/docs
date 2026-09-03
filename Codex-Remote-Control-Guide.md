# Codex Remote Control — Linux Server to ChatGPT Mobile

## Overview

This document describes the verified setup for running **Codex CLI on a Linux server** and accessing that server through **ChatGPT Mobile → Codex → Remote**.

The setup was successfully established with Codex CLI `0.151.0`, later experienced a managed-daemon failure during the `0.151.0 → 0.152.1` update, and was subsequently brought back to a healthy managed-daemon state on `0.153.0`.

The latest unresolved problem is **not the App Server or Remote Control connection itself**. The current problem is specifically the **Remote Control pairing operation returning `401 token_revoked`** after authentication changes.

---

# 1. Confirmed Architecture

The working architecture is:

```text
┌──────────────────────────────┐
│ ChatGPT Mobile               │
│                              │
│ Codex → Remote               │
└──────────────┬───────────────┘
               │
               │ Remote Control / pairing
               ▼
┌──────────────────────────────┐
│ Linux Server                 │
│                              │
│ Codex CLI                    │
│ Managed App Server           │
│ Remote Control               │
│                              │
│ Project workspace            │
└──────────────────────────────┘
```

The managed App Server runs locally on the Linux server.

In the confirmed configuration it uses:

```text
unix://
```

and the control socket:

```text
~/.codex/app-server-control/app-server-control.sock
```

The successful setup did **not** require exposing a public Codex TCP port.

---

# 2. Confirmed Environment History

| Stage         | Codex version | Result                                                             |
| ------------- | ------------: | ------------------------------------------------------------------ |
| Initial setup |     `0.151.0` | Managed App Server + Mobile Remote successfully paired             |
| Update        |     `0.152.1` | Managed daemon failed                                              |
| Recovery      |     `0.153.0` | Managed App Server restored                                        |
| Current state |     `0.153.0` | Remote connection works; pairing currently returns `token_revoked` |

The latest confirmed CLI output is:

```text
codex-cli 0.153.0
```

The managed daemon also reports:

```text
managedCodexVersion: 0.153.0
cliVersion:          0.153.0
appServerVersion:    0.153.0
```

---

# 3. Prerequisites

## Linux server

Required:

* Codex CLI installed.
* A Codex version supporting:

  * `codex app-server`
  * `codex remote-control`
* A valid ChatGPT account login.
* Outbound network connectivity.
* A Linux user under which Codex can run.

The verified server workspace was:

```text
~/AutonomousTrading
```

Replace that path for another project.

## Mobile

Required:

* ChatGPT mobile app.
* Codex/Remote functionality available.
* The mobile app signed into the account intended for the remote environment.

---

# 4. Verify Codex Installation

Check the CLI:

```bash
codex --version
```

The latest confirmed version is:

```text
codex-cli 0.153.0
```

Verify Remote Control support:

```bash
codex remote-control --help
```

The confirmed commands are:

```text
start
stop
pair
```

Verify App Server support:

```bash
codex app-server --help
```

The confirmed commands include:

```text
daemon
proxy
generate-ts
generate-json-schema
```

---

# 5. Authenticate the Linux Server

Codex can authenticate to the ChatGPT account using device authentication.

Run:

```bash
codex login --device-auth
```

The browser/device flow supplies a temporary device code.

Never publish the actual device code.

After successful login:

```bash
codex login status
```

The confirmed successful result was:

```text
Logged in using ChatGPT
```

### Important authentication distinction

`codex login status` confirms that the CLI has a ChatGPT login, but it does not by itself prove that every Remote Control enrollment request will succeed.

That distinction became important later when:

```text
codex login status
→ Logged in using ChatGPT
```

while:

```text
codex remote-control pair
→ HTTP 401
→ token_revoked
```

This behavior is also consistent with reported Codex remote-control authentication/enrollment issues.

---

# 6. Bootstrap the Managed App Server

The managed daemon is installed using:

```bash
codex app-server daemon bootstrap
```

For a Remote Control environment, the CLI also supports:

```bash
codex app-server daemon bootstrap --remote-control
```

The latter is the preferred explicit configuration when rebuilding the managed environment for Remote Control.

The bootstrap operation creates managed App Server state under:

```text
~/.codex/app-server-control/
```

including the control socket.

---

# 7. Enable Remote Control

Run:

```bash
codex app-server daemon enable-remote-control
```

The confirmed result was equivalent to:

```json
{
  "status": "enabled",
  "remoteControlEnabled": true
}
```

---

# 8. Start the Managed Daemon

Run:

```bash
codex app-server daemon start
```

If the command reports:

```text
alreadyRunning
```

that is not an error; it means the managed daemon is already running.

---

# 9. Verify the Managed App Server

Run:

```bash
codex app-server daemon version
```

A healthy state should report:

```text
status: running
```

The current verified version values are:

```text
managedCodexVersion: 0.153.0
cliVersion:          0.153.0
appServerVersion:    0.153.0
```

---

# 10. Verify the Control Socket

Run:

```bash
ls -l ~/.codex/app-server-control/app-server-control.sock
```

A healthy installation should show a Unix socket similar to:

```text
srw------- ... /home/admin/.codex/app-server-control/app-server-control.sock
```

The exact username/path is environment-specific and should not be copied into public documentation.

---

# 11. Verify the Running Processes

Run:

```bash
ps aux | grep -E 'codex|app-server' | grep -v grep
```

A healthy managed setup can include processes resembling:

```text
codex app-server --remote-control --listen unix://
```

```text
codex app-server daemon pid-update-loop
```

and potentially:

```text
codex-code-mode-host
```

These processes should **not** be killed merely because they appear in process inspection.

---

# 12. Public Network Exposure Is Not Required

The successful configuration uses:

```text
--listen unix://
```

rather than a public TCP listener.

The diagnostic command:

```bash
ss -lntp | grep -i codex
```

returned no Codex TCP listener during the successful setup.

Therefore:

* Do not expose a Codex port publicly solely for Remote Control.
* Do not add an AWS security-group rule for this purpose.
* Do not convert the managed daemon to `0.0.0.0:<port>` unless a separate, explicit requirement exists and the security implications are understood.

---

# 13. Check Remote Control Connectivity

Run:

```bash
codex remote-control --json
```

A healthy connection can report:

```json
{
  "mode": "foreground",
  "status": "connected",
  "serverName": "...",
  "environmentId": "...",
  "timedOut": false
}
```

The exact `serverName` and `environmentId` are environment-specific and should be treated as private connection metadata.

### Important interpretation

The current server demonstrated:

```text
Remote Control connection → connected
```

even when pairing later failed.

Therefore:

```text
Remote connection
```

and:

```text
Pairing enrollment
```

must be treated as separate operations.

---

# 14. Generate a Mobile Pairing Code

When the managed service is healthy, run:

```bash
codex remote-control pair
```

The CLI generates a short-lived pairing code.

Example:

```text
Pairing code: XXXX-XXXX
```

The real code must not be published.

The code is intended for the mobile pairing flow.

---

# 15. Pair with ChatGPT Mobile

On the phone:

```text
ChatGPT
→ Codex
→ Remote
→ Pair/Add Remote
```

Enter the freshly generated pairing code.

This was **successfully completed earlier in the actual environment**, establishing that Linux-side CLI Remote Control can be paired with ChatGPT Mobile through the experimental CLI/headless workflow.

Current Codex sources expose the experimental Remote Control pairing methods at the App Server protocol level, and the repository documents CLI/headless pairing support.

---

# 16. Important Distinction: Existing CLI Session vs Managed App Server

Do not assume that:

```bash
codex
```

started as an ordinary terminal process is automatically the same session as:

```text
Managed App Server
```

used by Remote Control.

The conversation established mobile access to the managed Remote Control environment, but did **not conclusively prove automatic attachment of an arbitrary pre-existing interactive CLI process**.

Therefore, treat these separately:

```text
Interactive CLI session
```

and:

```text
Managed App Server / Remote Control session
```

---

# 17. The 0.151.0 → 0.152.1 Failure

After Codex updated:

```text
0.151.0 → 0.152.1
```

the managed App Server stopped working.

The observed symptoms were:

```text
codex app-server daemon version
→ failed to connect to ~/.codex/app-server-control/app-server-control.sock
```

The managed App Server itself was no longer running.

The Unix socket was missing.

`codex remote-control stop` also hung for more than one minute.

Process inspection showed:

```text
codex app-server daemon pid-update-loop
```

and:

```text
[codex] <defunct>
```

At the same time, foreground Remote Control could still connect successfully.

The evidence therefore distinguished:

```text
Foreground Remote Control    ✅
Managed App Server           ❌
Managed daemon updater       ⚠️
Unix control socket          ❌
```

The issue was the **persistent managed daemon**, not general Remote Control network connectivity.

---

# 18. Recovery from the Stale Managed Daemon

For that incident, the stale updater had a specific PID.

Because PIDs change between incidents, never hard-code that historical PID into a future runbook.

First inspect:

```bash
ps aux | grep -E 'codex|app-server' | grep -v grep
```

Identify the stale:

```text
codex app-server daemon pid-update-loop
```

process.

Gracefully terminate the current stale updater:

```bash
kill -TERM <CURRENT_STALE_PID>
```

Then inspect again:

```bash
ps aux | grep -E 'codex|app-server' | grep -v grep
```

If the updater remains:

```bash
kill -KILL <CURRENT_STALE_PID>
```

Do not attempt to kill a process whose state is:

```text
Z
<defunct>
```

A zombie process has already exited and must be reaped by its parent.

---

# 19. Rebuild the Managed Remote-Control Environment

After stale-process cleanup:

```bash
codex app-server daemon bootstrap --remote-control
```

Then:

```bash
codex app-server daemon start
```

Verify:

```bash
codex app-server daemon version
```

And:

```bash
ls -l ~/.codex/app-server-control/app-server-control.sock
```

The desired state is:

```text
status: running
```

with the control socket present.

---

# 20. The 0.153.0 Authentication Failure

After the recovery, the environment was upgraded to:

```text
0.153.0
```

The following became true:

```text
codex login status
→ Logged in using ChatGPT
```

The managed App Server was healthy:

```text
status: running
```

The control socket existed.

The Remote Control connection itself was healthy:

```json
{
  "mode": "foreground",
  "status": "connected",
  ...
}
```

However:

```bash
codex remote-control pair
```

returned:

```text
HTTP 401 Unauthorized
```

with:

```text
auth error code: token_revoked
```

The failing endpoint was:

```text
https://chatgpt.com/backend-api/wham/remote/control/server/refresh
```

The exact request identifiers and server metadata are intentionally omitted.

---

# 21. Correct Interpretation of the Current Failure

The latest confirmed state is:

```text
Codex CLI                     0.153.0   ✅
ChatGPT CLI login             active    ✅
Managed App Server            running   ✅
Unix control socket           present   ✅
Remote Control connection     connected ✅
Remote Control pairing       failing   ❌
Pairing API response          401       ❌
Authentication error          token_revoked
```

Therefore the problem is **not currently**:

* a missing Unix socket,
* a dead App Server,
* a missing TCP port,
* an AWS security-group problem,
* general Remote Control connectivity.

The immediate failure is specifically:

```text
Remote Control pairing enrollment
→ token_revoked
```

There are current upstream reports of Codex remote-control enrollment/client state becoming invalid after revocation or authentication changes, including cases involving mobile pairing and stale enrollment state.

---

# 22. Authentication Recovery Procedure

Because the current pairing request is returning `token_revoked`, refresh the CLI's account authentication.

First:

```bash
codex logout
```

Then:

```bash
codex login --device-auth
```

Complete the device authentication using the intended ChatGPT account.

Verify:

```bash
codex login status
```

Expected:

```text
Logged in using ChatGPT
```

Then test the existing Remote Control connection:

```bash
codex remote-control --json
```

A healthy connection can report:

```json
{
  "mode": "foreground",
  "status": "connected"
}
```

Then generate a new pairing code:

```bash
codex remote-control pair
```

Do not reuse an old pairing code.

---

# 23. If Pairing Still Returns `token_revoked`

If this sequence:

```bash
codex logout
codex login --device-auth
codex login status
codex remote-control --json
codex remote-control pair
```

still ends with:

```text
401 Unauthorized
token_revoked
```

then restarting the daemon repeatedly is not the primary next step.

At that point the evidence indicates a **Remote Control authentication/enrollment issue**, potentially involving stale or revoked remote-control enrollment state rather than the Linux App Server itself.

Upstream reports document related cases where:

* the remote host remains online,
* Remote Control connectivity works,
* the client/enrollment remains stale or revoked,
* and re-pairing fails.

---

# 24. What Not to Do

Do not use:

```bash
rm -rf ~/.codex
```

Do not delete Codex databases or state files as a first response.

Do not expose an arbitrary Codex TCP port publicly.

Do not modify AWS security-group rules for a Unix-socket/Remote-Control authentication error.

Do not repeatedly kill healthy:

```text
codex app-server --remote-control --listen unix://
```

or:

```text
codex app-server daemon pid-update-loop
```

processes when the managed daemon is already healthy.

Do not kill `[codex] <defunct>` directly.

Do not publish device-auth codes or Remote Control pairing codes.

---

# 25. Bubblewrap Warning

The managed App Server has also produced:

```text
Codex could not find bubblewrap on PATH.
Install bubblewrap with your OS package manager.
Codex will use the bundled bubblewrap in the meantime.
```

Based on the message itself, Codex explicitly states that it will use the bundled `bubblewrap` fallback.

Therefore this warning was **not established as the cause of the Remote Control pairing failure**.

The confirmed pairing failure is:

```text
401 Unauthorized
token_revoked
```

---

# 26. Operational Health Checks

Use these commands to determine which layer is broken.

### Authentication

```bash
codex login status
```

### Managed App Server

```bash
codex app-server daemon version
```

### Local socket

```bash
ls -l ~/.codex/app-server-control/app-server-control.sock
```

### Running processes

```bash
ps aux | grep -E 'codex|app-server' | grep -v grep
```

### Network listener check

```bash
ss -lntp | grep -i codex
```

### Remote Control connection

```bash
codex remote-control --json
```

### Mobile pairing

```bash
codex remote-control pair
```

---

# 27. Diagnostic Decision Tree

Use this order.

```text
codex login status
        │
        ├── Not logged in
        │       ↓
        │   codex login --device-auth
        │
        └── Logged in
                ↓
codex app-server daemon version
        │
        ├── socket/connection failure
        │       ↓
        │   inspect processes
        │   clean stale daemon
        │   bootstrap --remote-control
        │   start
        │
        └── status: running
                ↓
codex remote-control --json
        │
        ├── not connected
        │       ↓
        │   investigate Remote Control connectivity
        │
        └── connected
                ↓
codex remote-control pair
        │
        ├── pairing code generated
        │       ↓
        │   ChatGPT Mobile → Codex → Remote
        │
        └── HTTP 401 token_revoked
                ↓
        refresh ChatGPT CLI authentication
                ↓
        retry pairing
```

---

# 28. Complete Fresh Setup

For a clean new Linux host/account, the sequence is:

```bash
# 1. Check Codex
codex --version

# 2. Authenticate
codex login --device-auth

# 3. Confirm login
codex login status

# 4. Bootstrap managed App Server with Remote Control
codex app-server daemon bootstrap --remote-control

# 5. Start managed daemon
codex app-server daemon start

# 6. Verify daemon
codex app-server daemon version

# 7. Verify Unix socket
ls -l ~/.codex/app-server-control/app-server-control.sock

# 8. Check Remote Control connectivity
codex remote-control --json

# 9. Generate pairing code
codex remote-control pair
```

Then on the phone:

```text
ChatGPT
→ Codex
→ Remote
→ Pair/Add Remote
```

Use the fresh pairing code.

---

# 29. Complete Recovery Procedure

For an already-configured host whose managed daemon has broken:

```bash
# 1. Inspect current Codex/App Server processes
ps aux | grep -E 'codex|app-server' | grep -v grep

# 2. Identify the current stale pid-update-loop PID
#    Replace <CURRENT_STALE_PID> below.

# 3. Gracefully terminate it
kill -TERM <CURRENT_STALE_PID>

# 4. Recheck
ps aux | grep -E 'codex|app-server' | grep -v grep

# 5. Force-kill only if it remains
kill -KILL <CURRENT_STALE_PID>

# 6. Rebuild managed Remote Control configuration
codex app-server daemon bootstrap --remote-control

# 7. Start
codex app-server daemon start

# 8. Verify
codex app-server daemon version

# 9. Verify socket
ls -l ~/.codex/app-server-control/app-server-control.sock

# 10. Verify Remote Control
codex remote-control --json

# 11. Generate a fresh pairing code
codex remote-control pair
```

---

# 30. Final Verified State

The latest successful server-side state is:

```text
Codex CLI
└── 0.153.0
    │
    ├── ChatGPT login
    │     └── Logged in
    │
    ├── Managed App Server
    │     └── Running
    │
    ├── Remote Control
    │     └── Connected
    │
    ├── Unix control socket
    │     └── Present
    │
    └── Mobile Remote
          └── Previously proven to pair successfully
```

The latest unresolved condition is specifically:

```text
codex remote-control pair
        ↓
HTTP 401 Unauthorized
        ↓
token_revoked
```

This should therefore be handled as an **authentication/enrollment problem**, not as a managed-daemon or public-networking problem.

---

# References

The following references were used only to validate current behavior relevant to the consolidated runbook:

* Codex App Server protocol includes experimental Remote Control pairing/status/client methods.
* Current Codex issue discussion documents the experimental CLI/headless workflow using `codex remote-control start` and `codex remote-control pair`.
* Current upstream reports document Remote Control authentication/enrollment problems involving revoked or stale client state.
* Current reports also document OAuth/refresh-token invalidation producing Remote Control authentication failures.

## Known documentation caveat

Current Codex documentation and issue discussions have shown some inconsistency between the general Remote Connections documentation and the newer experimental CLI/headless Remote Control workflow. The **actual successful pairing in this environment is the strongest evidence for this specific setup**: Linux Codex CLI → Remote Control → ChatGPT Mobile was successfully paired.

That workflow should therefore be treated here as **verified experimental behavior**, rather than generalized beyond the confirmed environment.
