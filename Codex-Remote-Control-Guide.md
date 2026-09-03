# Codex Remote Control — Linux Server to ChatGPT Mobile

## Overview

This document records the verified setup, operating procedure, failure history, and recovery process for using **Codex CLI on a Linux server with ChatGPT Mobile → Codex → Remote**.

The environment was initially working with Codex `0.151.0`, later experienced a managed-daemon failure during the `0.151.0 → 0.152.1` update, and was subsequently restored on Codex `0.153.0`.

The **latest confirmed state** is:

```text
Codex CLI                    0.153.0
ChatGPT CLI login            Logged in using ChatGPT
Managed App Server           Running
Remote Control process       Running
Unix control socket          Present
Foreground Remote Control   Connected
Remote Control pairing       Failing with HTTP 401 token_revoked
```

The current failure is therefore isolated to **Remote Control pairing/enrollment authentication**, not the managed App Server itself.

OpenAI's current help documentation describes the mobile Remote experience as a way to access supported remote Codex work from the ChatGPT mobile app.

---

# 1. Confirmed Architecture

The verified Linux-side architecture is:

```text
┌─────────────────────────┐
│ ChatGPT Mobile         │
│                         │
│ Codex → Remote          │
└────────────┬────────────┘
             │
             │ Remote Control
             │ pairing / relay
             ▼
┌─────────────────────────┐
│ Linux Server            │
│                         │
│ Codex CLI               │
│ Managed App Server      │
│ Remote Control          │
│                         │
│ Project workspace       │
└─────────────────────────┘
```

The managed App Server runs locally with:

```text
--listen unix://
```

and uses:

```text
~/.codex/app-server-control/app-server-control.sock
```

No public Codex TCP listener was required for the confirmed mobile Remote Control setup.

---

# 2. Versions and State History

| Stage         |   Version | Result                                              |
| ------------- | --------: | --------------------------------------------------- |
| Initial setup | `0.151.0` | Remote Control and mobile pairing succeeded         |
| Upgrade       | `0.152.1` | Managed daemon failed                               |
| Recovery      | `0.153.0` | Managed daemon restored                             |
| Latest state  | `0.153.0` | App Server healthy; pairing returns `token_revoked` |

The latest verified managed-daemon output is equivalent to:

```json
{
  "status": "running",
  "managedCodexVersion": "0.153.0",
  "cliVersion": "0.153.0",
  "appServerVersion": "0.153.0"
}
```

---

# 3. Prerequisites

## Linux server

Required:

* Codex CLI installed.
* A version supporting:

  * `codex app-server`
  * `codex remote-control`
* A valid ChatGPT account login.
* Outbound network connectivity.
* A Linux user that can run Codex and access the project workspace.

The verified project workspace was:

```text
~/AutonomousTrading
```

## Mobile

Required:

* ChatGPT mobile app.
* Access to the Codex Remote experience.
* The intended ChatGPT account signed in on the phone.

OpenAI's current documentation states that the ChatGPT mobile app can access supported desktop/remote Codex chats through the Remote tab.

---

# 4. Verify Codex

Check the installed version:

```bash
codex --version
```

The latest verified environment is:

```text
codex-cli 0.153.0
```

Check Remote Control:

```bash
codex remote-control --help
```

The confirmed commands are:

```text
start
stop
pair
```

Check App Server:

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

Use ChatGPT device authentication:

```bash
codex login --device-auth
```

Complete the device authorization in the browser.

Do not publish the temporary device code.

Verify the login:

```bash
codex login status
```

Expected:

```text
Logged in using ChatGPT
```

### Important

A successful:

```bash
codex login status
```

does not by itself guarantee that Remote Control pairing will succeed.

The latest environment demonstrated:

```text
codex login status
→ Logged in using ChatGPT
```

while:

```bash
codex remote-control pair
```

still returned:

```text
HTTP 401 Unauthorized
token_revoked
```

This separates ordinary CLI authentication from Remote Control enrollment. Current upstream reports document related Remote Control authentication/enrollment failures.

---

# 6. Bootstrap the Managed App Server

For a fresh setup:

```bash
codex app-server daemon bootstrap --remote-control
```

This installs durable managed App Server management with Remote Control enabled.

The resulting managed state uses the local control socket:

```text
~/.codex/app-server-control/app-server-control.sock
```

---

# 7. Start the Managed App Server

Run:

```bash
codex app-server daemon start
```

Possible healthy response:

```text
alreadyRunning
```

That means the managed daemon was already running.

---

# 8. Verify the Managed App Server

Run:

```bash
codex app-server daemon version
```

Healthy output should contain:

```text
status: running
```

For the latest verified environment:

```text
managedCodexVersion: 0.153.0
cliVersion:          0.153.0
appServerVersion:    0.153.0
```

---

# 9. Verify the Local Control Socket

Run:

```bash
ls -l ~/.codex/app-server-control/app-server-control.sock
```

Expected type:

```text
srw-------
```

The socket is local IPC and should not be treated as a public network endpoint.

---

# 10. Verify Managed Processes

Run:

```bash
ps aux | grep -E 'codex|app-server' | grep -v grep
```

A healthy managed environment can contain processes similar to:

```text
codex app-server --remote-control --listen unix://
```

```text
codex app-server daemon pid-update-loop
```

and:

```text
codex-code-mode-host
```

These are normal managed components when the daemon is healthy.

Do not kill them merely because they appear in `ps`.

---

# 11. Verify Public Network Exposure

Check whether Codex is listening on TCP:

```bash
ss -lntp | grep -i codex
```

The verified working configuration showed no Codex TCP listener.

That is compatible with the managed Remote Control architecture.

Do not add an AWS security-group rule simply because the command returns no Codex TCP listener.

---

# 12. Check Remote Control Connectivity

Run:

```bash
codex remote-control --json
```

A healthy foreground connection can report:

```json
{
  "mode": "foreground",
  "status": "connected",
  "serverName": "...",
  "environmentId": "...",
  "timedOut": false
}
```

The exact `serverName` and `environmentId` are private environment metadata and should not be published.

### Current interpretation

Remote Control connectivity and Remote Control pairing are separate operations.

The latest environment has demonstrated:

```text
Remote Control connection → connected
```

while:

```text
Remote Control pairing    → 401 token_revoked
```

---

# 13. Generate a Mobile Pairing Code

When the managed environment is healthy:

```bash
codex remote-control pair
```

A short-lived pairing code is generated.

Example format:

```text
Pairing code: XXXX-XXXX
```

Never publish the real code.

---

# 14. Pair the ChatGPT Mobile App

On the phone:

```text
ChatGPT
→ Codex
→ Remote
→ Pair / Add Remote
```

Enter the fresh pairing code generated by:

```bash
codex remote-control pair
```

The original `0.151.0` setup successfully completed this mobile pairing.

OpenAI's current release notes state that Remote Control uses authenticated one-to-one pairing between supported mobile devices and hosts.

---

# 15. Important Session Distinction

Do not assume that an ordinary interactive terminal session:

```bash
codex
```

is automatically identical to the managed Remote Control session.

The environment contains separate concepts:

```text
Interactive CLI session
```

and:

```text
Managed App Server / Remote Control environment
```

The conversation confirmed successful mobile Remote access to the managed environment, but did not conclusively establish automatic attachment of an arbitrary already-running CLI process.

There is also an upstream issue specifically describing difficulty attaching Remote Control to an in-progress live CLI session while completed threads can work differently.

---

# 16. Failure After 0.151.0 → 0.152.1

After updating from:

```text
0.151.0
```

to:

```text
0.152.1
```

the managed App Server stopped functioning.

Symptoms included:

```text
codex app-server daemon version
→ failed to connect to ~/.codex/app-server-control/app-server-control.sock
```

and:

```text
codex remote-control stop
```

hanging for more than one minute.

Process inspection showed:

```text
codex app-server daemon pid-update-loop
```

and:

```text
[codex] <defunct>
```

The managed App Server itself was no longer running and the control socket was missing.

At the same time, foreground Remote Control was able to connect successfully.

Therefore:

```text
Foreground Remote Control   ✅
Managed daemon              ❌
Updater                     ⚠️ stale
Unix socket                 ❌
```

This isolated the failure to the persistent managed daemon.

---

# 17. Managed-Daemon Recovery

Do not use the hanging stop command repeatedly.

First inspect:

```bash
ps aux | grep -E 'codex|app-server' | grep -v grep
```

Identify the current stale:

```text
codex app-server daemon pid-update-loop
```

PID.

Terminate it gracefully:

```bash
kill -TERM <CURRENT_STALE_PID>
```

Recheck:

```bash
ps aux | grep -E 'codex|app-server' | grep -v grep
```

Only if it remains:

```bash
kill -KILL <CURRENT_STALE_PID>
```

Do not kill a process shown as:

```text
[codex] <defunct>
```

A defunct process has already exited and must be reaped by its parent.

Then rebuild the managed Remote Control configuration:

```bash
codex app-server daemon bootstrap --remote-control
```

and start:

```bash
codex app-server daemon start
```

Verify:

```bash
codex app-server daemon version
```

Then verify:

```bash
ls -l ~/.codex/app-server-control/app-server-control.sock
```

---

# 18. Codex 0.153.0 Authentication Failure

After the recovery, the environment was upgraded to `0.153.0`.

The following succeeded:

```bash
codex login --device-auth
```

and:

```bash
codex login status
```

returned:

```text
Logged in using ChatGPT
```

The managed daemon was also healthy:

```text
status: running
```

The control socket existed.

Remote Control connectivity could also report:

```json
{
  "mode": "foreground",
  "status": "connected"
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

The failing backend operation was the Remote Control server refresh/enrollment path.

---

# 19. Current Root-Cause Classification

The latest evidence supports this layered diagnosis:

```text
Authentication
    └── CLI login:                 ✅

Managed App Server
    └── running:                   ✅

Unix control socket
    └── present:                   ✅

Remote Control transport
    └── foreground connected:      ✅

Remote Control pairing/enrollment
    └── HTTP 401 token_revoked:    ❌
```

Therefore the current problem should **not** be treated as:

* a missing control socket,
* a dead managed daemon,
* a missing public TCP port,
* an AWS security-group problem,
* or general network reachability.

The unresolved layer is **Remote Control pairing/enrollment authentication**.

Current upstream reports document related cases involving revoked/stale Remote Control enrollment and mobile pairing failures.

---

# 20. Authentication Refresh Procedure

When pairing returns:

```text
401 Unauthorized
token_revoked
```

refresh the CLI authentication:

```bash
codex logout
```

Then:

```bash
codex login --device-auth
```

Complete the device login using the intended ChatGPT account.

Verify:

```bash
codex login status
```

Then check Remote Control:

```bash
codex remote-control --json
```

If the connection is healthy, generate a fresh pairing code:

```bash
codex remote-control pair
```

Use that new code in the ChatGPT mobile Remote pairing flow.

Do not reuse an old pairing code.

---

# 21. If `token_revoked` Persists

If all of the following are true:

```text
codex login status
→ Logged in using ChatGPT

codex app-server daemon version
→ status: running

codex remote-control --json
→ connected / otherwise healthy

codex remote-control pair
→ 401 token_revoked
```

then the managed daemon should not be repeatedly killed and restarted.

The available evidence points to a Remote Control enrollment/authentication issue that can involve persisted or server-side enrollment state. Current upstream reports describe stale/revoked enrollment continuing to interfere with pairing even after local authentication changes.

At that point, investigate the specific Remote Control enrollment state or current upstream issue rather than deleting the complete Codex state directory.

---

# 22. Bubblewrap Warning

The managed App Server has produced:

```text
Codex could not find bubblewrap on PATH.
Install bubblewrap with your OS package manager.
Codex will use the bundled bubblewrap in the meantime.
```

The message itself states that Codex will use the bundled fallback.

Therefore this warning has **not been established as the cause** of the current Remote Control pairing failure.

The confirmed pairing failure is:

```text
HTTP 401 Unauthorized
auth error code: token_revoked
```

---

# 23. Files That Should Not Be Deleted as a First Response

The Codex state directory contains significant state, including:

```text
auth.json
thread_history_1.sqlite
logs_2.sqlite
state_5.sqlite
queue_1.sqlite
memories_1.sqlite
sessions/
archived_sessions/
```

Do not begin troubleshooting by deleting:

```bash
rm -rf ~/.codex
```

Do not delete Codex SQLite databases or session history simply to repair Remote Control pairing.

The available evidence does not justify that level of destructive reset.

---

# 24. Sensitive Information

Do not publish:

* Device authorization codes.
* Remote Control pairing codes.
* OAuth tokens.
* Refresh tokens.
* Cookies.
* Credentials from `auth.json`.
* Private environment IDs when unnecessary.
* Private server identifiers or public IP addresses.

If diagnostic logs contain such information, redact it before sharing.

---

# 25. Standard Health-Check Commands

### Authentication

```bash
codex login status
```

### Codex version

```bash
codex --version
```

### Managed App Server

```bash
codex app-server daemon version
```

### Control socket

```bash
ls -l ~/.codex/app-server-control/app-server-control.sock
```

### Managed processes

```bash
ps aux | grep -E 'codex|app-server' | grep -v grep
```

### Public TCP listener

```bash
ss -lntp | grep -i codex
```

### Remote Control connection

```bash
codex remote-control --json
```

### Remote pairing

```bash
codex remote-control pair
```

### Managed App Server log

```bash
tail -n 100 ~/.codex/app-server-daemon/app-server.stderr.log
```

### Managed App Server updater log

```bash
tail -n 100 ~/.codex/app-server-daemon/app-server-updater.stderr.log
```

---

# 26. Diagnostic Decision Tree

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
        ├── Failed / socket missing
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
        ├── Not connected
        │       ↓
        │   inspect Remote Control connectivity
        │
        └── Connected
                ↓
codex remote-control pair
        │
        ├── Pairing code created
        │       ↓
        │   ChatGPT Mobile → Codex → Remote
        │
        └── HTTP 401 token_revoked
                ↓
        refresh ChatGPT CLI login
                ↓
        retry pairing once
                ↓
        still token_revoked?
                ↓
        investigate Remote Control
        enrollment/backend state
```

---

# 27. Fresh Setup Runbook

For a new Linux host/account:

```bash
# 1. Verify installation
codex --version

# 2. Authenticate the intended ChatGPT account
codex login --device-auth

# 3. Verify authentication
codex login status

# 4. Bootstrap managed App Server with Remote Control
codex app-server daemon bootstrap --remote-control

# 5. Start managed daemon
codex app-server daemon start

# 6. Verify daemon
codex app-server daemon version

# 7. Verify local control socket
ls -l ~/.codex/app-server-control/app-server-control.sock

# 8. Verify Remote Control connection
codex remote-control --json

# 9. Generate fresh mobile pairing code
codex remote-control pair
```

Then:

```text
ChatGPT Mobile
→ Codex
→ Remote
→ Pair / Add Remote
```

---

# 28. Managed-Daemon Recovery Runbook

For a broken managed daemon:

```bash
# 1. Inspect current processes
ps aux | grep -E 'codex|app-server' | grep -v grep

# 2. Identify the current stale pid-update-loop PID

# 3. Gracefully terminate it
kill -TERM <CURRENT_STALE_PID>

# 4. Recheck
ps aux | grep -E 'codex|app-server' | grep -v grep

# 5. Force-kill only if the stale updater remains
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

# 11. Generate new pairing code if healthy
codex remote-control pair
```

---

# 29. Authentication-Recovery Runbook

For:

```text
401 Unauthorized
token_revoked
```

use:

```bash
# 1. Refresh CLI authentication
codex logout

# 2. Authenticate the intended account
codex login --device-auth

# 3. Verify
codex login status

# 4. Check Remote Control
codex remote-control --json

# 5. Generate fresh pairing code
codex remote-control pair
```

If `token_revoked` persists after this sequence, do not keep deleting local Codex state or repeatedly restarting the healthy managed daemon.

---

# 30. Final Verified State

The latest confirmed Linux environment is:

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
    ├── Unix control socket
    │     └── Present
    │
    ├── Remote Control process
    │     └── Running
    │
    ├── Remote Control connection
    │     └── Previously confirmed connected
    │
    └── Mobile pairing
          └── Current attempt fails with
              HTTP 401 token_revoked
```

The correct current interpretation is therefore:

```text
Linux Codex/App Server        ✅
Remote Control transport     ✅ / previously confirmed
Mobile pairing enrollment    ❌
Failure class                authentication/enrollment
```

---

# 31. Known Gaps and Assumptions

### Confirmed

* Codex `0.153.0` is installed.
* The ChatGPT CLI login reports `Logged in using ChatGPT`.
* The managed App Server reports `status: running`.
* The Unix control socket exists.
* Remote Control can reach a connected foreground state.
* Mobile pairing succeeded earlier in the history.
* The current pairing attempt returns `HTTP 401 token_revoked`.

### Not conclusively established

* Whether an arbitrary already-running interactive CLI process can be attached directly to the managed mobile Remote session.
* Whether the present `token_revoked` pairing failure is entirely server-side or partly caused by client-side persisted enrollment state.
* Whether a specific additional account-level action is required beyond CLI logout/login.

These remain intentionally unresolved rather than being filled with assumptions.

---

# References

* OpenAI Help Center — ChatGPT release notes: Codex Remote became generally available and Remote Control uses authenticated one-to-one pairing for supported mobile/host connections.
* OpenAI Help Center — ChatGPT Work and Codex: the mobile app can access supported remote Codex chats from the Remote tab.
* OpenAI Codex GitHub — Linux/Android Remote Control pairing failures have been reported, including cases where the host registers and creates pairing codes but mobile pairing fails.
* OpenAI Codex GitHub — stale/revoked Remote Control enrollment and re-pairing failures have been reported.
* OpenAI Codex GitHub — live/in-progress CLI session attachment has been reported as a limitation in Remote Control.
