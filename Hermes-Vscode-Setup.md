# Hermes Agent × VS Code — Full Setup Guide

> **Date:** May 21, 2026  
> **Platform:** Windows 11 · VS Code · GitHub Copilot  
> **Hermes version:** 0.14.0 (2026-05-16)  
> **LLM backend:** Google AI Studio — `gemini-3.5-flash` (free tier)

---

## Overview

This guide documents the complete process of integrating Hermes Agent with VS Code as requested in the original autonomous setup prompt. The goal is:

| Surface | Role |
|---|---|
| **GitHub Copilot Chat** | UI chat model (Claude / GPT / etc.) |
| **Hermes Agent** | Skill backend · persistent memory · tool delegation |
| **Google Gemini** | LLM powering Hermes' own sessions |

---

## Original Execution Plan (Autonomous Setup)

```
STEP 1 — Environment Check
STEP 2 — Fix API Provider (Google Gemini AI Studio)
STEP 3 — Reset MCP/ACP Layer
STEP 4 — VSCode MCP Compatibility
STEP 5 — Integration Test
STEP 6 — Final Diagnostic Report
```

---

## STEP 1 — Environment Check

**Commands run:**
```powershell
python --version
hermes --version
hermes status
hermes doctor
```

**Results:**

| Check | Result |
|---|---|
| System Python | 3.14.0 |
| Hermes Python (venv) | 3.11.15 |
| Hermes version | v0.14.0 (2026.5.16) |
| Hermes executable | `C:\Users\Manoj\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe` |
| MCP package | `mcp 1.27.0` |
| OpenAI SDK | 2.24.0 |
| Virtual env | ✓ active |
| Required packages | ✓ all present |

**Status: PASS**

---

## STEP 2 — Fix API Provider (Google Gemini)

**`hermes status` output (relevant section):**
```
Model:        gemini-3.5-flash
Provider:     Google AI Studio
Google / Gemini  ✓ AIza...LLgA
```

**`hermes doctor` API check:**
```
◆ API Connectivity
  ✓ OpenRouter API
  ✓ gemini
```

**Status: PASS** — Gemini API key already configured and reachable.

---

## STEP 3 — Reset MCP/ACP Layer

**Check ACP dependencies:**
```powershell
hermes acp --check
# Output: Hermes ACP check OK

hermes acp --version
# Output: 0.14.0
```

**Status: PASS**

---

## STEP 4 — VSCode MCP Compatibility

### Problem 1: bare `"command": "hermes"` fails

VS Code spawns MCP servers with a restricted PATH. The bare command `hermes` is not resolvable.

**Fix:** Use full absolute path in `mcp.json`.

### Problem 2: `hermes acp` — protocolVersion mismatch (`-32602`)

**VS Code log:**
```
[error] Error: MPC -32602: Invalid params
```

**Root cause:**

| Client | protocolVersion format | Example |
|---|---|---|
| VS Code (standard MCP) | string | `"2024-11-05"` |
| Hermes ACP | integer | `1` |

**Test confirming the mismatch:**
```powershell
# String version → error
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05",...}}'
# → {"error":{"code":-32602,"message":"Invalid params",...}}

# Integer version → success
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,...}}'
# → {"result":{"protocolVersion":1,"agentInfo":{"name":"hermes-agent","version":"0.14.0"},...}}
```

### Problem 3: Windows stdin buffer crash

**Error seen with `hermes acp` in terminal:**
```
Fatal Python error: _enter_buffered_busy: could not acquire lock for
<_io.BufferedReader name='<stdin>'> at interpreter shutdown
```

**Fix:** Set `PYTHONUNBUFFERED=1` in the server env block.

---

## STEP 5 — Integration Tests

### Test A: `hermes mcp serve` (standard MCP)

```powershell
$env:PYTHONUNBUFFERED="1"
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"vscode","version":"1.0"}}}' |
  & "C:\Users\Manoj\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe" mcp serve 2>$null
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "experimental": {},
      "prompts": {"listChanged": false},
      "resources": {"subscribe": false, "listChanged": false},
      "tools": {"listChanged": false}
    },
    "serverInfo": {"name": "hermes", "version": "1.26.0"},
    "instructions": "Hermes Agent messaging bridge..."
  }
}
```

**Status: PASS** — valid MCP response, no `-32602` error.

### Test B: ACP Bridge (protocol conversion)

```powershell
$env:PYTHONUNBUFFERED="1"
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05",...}}' |
  & "C:\Users\Manoj\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" -u acp_bridge.py
```

**Result:** `PASS: protocolVersion='2024-11-05' confirmed`

### Test C: `hermes chat` direct

```powershell
hermes chat
# → "Yes, I am Hermes. How can I help you today with OpenAlgo?"
# Running on gemini-3.5-flash · 28 tools · 76 skills
```

**Status: PASS**

---

## STEP 6 — Final Diagnostic Report

```
[HERMES SETUP REPORT]

- Environment:    PASS
                  Hermes v0.14.0, Python 3.11.15 (isolated venv)
                  All packages present (OpenAI SDK, httpx, PyYAML, rich, mcp 1.27.0)

- API:            PASS
                  Provider: Google AI Studio (Gemini)
                  Model: gemini-3.5-flash
                  Key: AIza...LLgA ✓ (connectivity verified)

- ACP/MCP:        PASS
                  hermes acp --check → OK
                  hermes mcp serve → valid MCP initialize response
                  hermes chat → Hermes responds, Gemini active

- VSCode Bridge:  PASS (mcp serve mode)
                  mcp.json configured with full hermes.exe path
                  PYTHONUNBUFFERED=1 — stdin crash fixed

- Final Status:   ✅ ALL STEPS PASS

- Known Limitation:
                  hermes acp (ACP agent mode) has protocolVersion
                  incompatibility with VS Code (string vs integer).
                  acp_bridge.py created as workaround, but VS Code
                  exposes ACP agents as tools, not @chat-participants.
                  Use hermes mcp serve for tool integration with Copilot.
                  Use hermes chat in terminal for direct Hermes sessions.
```

---

## Final Configurations

### `%APPDATA%\Code\User\mcp.json` (active)

```json
{
  "servers": {
    "hermes": {
      "type": "stdio",
      "command": "C:\\Users\\Manoj\\AppData\\Local\\hermes\\hermes-agent\\venv\\Scripts\\hermes.exe",
      "args": [
        "mcp",
        "serve"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  },
  "inputs": []
}
```

### `%LOCALAPPDATA%\hermes\acp_bridge.py` (protocol bridge, optional)

```python
"""
Hermes ACP bridge for VS Code.
VS Code sends protocolVersion as string "2024-11-05" (standard MCP).
Hermes ACP expects protocolVersion as integer 1.
This bridge converts both directions transparently.
"""
import sys
import json
import subprocess
import threading
import os

HERMES = r"C:\Users\Manoj\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe"
PROTOCOL_VERSION_STRING = "2024-11-05"
PROTOCOL_VERSION_INT = 1


def forward_responses(proc):
    """Read hermes stdout, fix protocolVersion integer → string, write to our stdout."""
    try:
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip("\n")
            if not line:
                continue
            try:
                msg = json.loads(line)
                result = msg.get("result", {})
                if isinstance(result, dict) and isinstance(result.get("protocolVersion"), int):
                    result["protocolVersion"] = PROTOCOL_VERSION_STRING
            except (json.JSONDecodeError, TypeError):
                pass
            sys.stdout.write(json.dumps(msg) + "\n")
            sys.stdout.flush()
    except Exception:
        pass


def main():
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        [HERMES, "acp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        env=env,
    )

    t = threading.Thread(target=forward_responses, args=(proc,), daemon=True)
    t.start()

    try:
        for raw in sys.stdin:
            line = raw.rstrip("\n")
            if not line:
                continue
            try:
                msg = json.loads(line)
                params = msg.get("params", {})
                if (
                    msg.get("method") == "initialize"
                    and isinstance(params, dict)
                    and isinstance(params.get("protocolVersion"), str)
                ):
                    params["protocolVersion"] = PROTOCOL_VERSION_INT
            except (json.JSONDecodeError, TypeError):
                pass
            proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
            proc.stdin.flush()
    except (EOFError, BrokenPipeError):
        pass
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass

    proc.wait()


if __name__ == "__main__":
    main()
```

---

## Architecture: Current Recommended Setup

```
┌─────────────────────────────────────────────────────────┐
│              VS Code GitHub Copilot Chat UI             │
│              Model: Claude / GPT-4.1 / etc.             │
└────────────────────────┬────────────────────────────────┘
                         │ MCP tool calls (stdio)
                         ▼
┌─────────────────────────────────────────────────────────┐
│           hermes mcp serve  (mcp.json)                  │
│                                                         │
│  Tools available to Copilot:                            │
│  • memory        → Hermes persistent memory store       │
│  • session_search → search past Hermes sessions         │
│  • skills        → invoke specialized skill agents      │
│  • delegation    → delegate sub-tasks to Hermes         │
│  • messaging     → Telegram / Discord / Slack           │
│  • browser       → web automation                       │
│  • (28 total tools)                                     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Hermes Agent backend  (gemini-3.5-flash via AI Studio) │
│  Memory DB · 76 Skills · Sessions · Cron jobs           │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Reference

### Start Hermes chat (terminal)
```powershell
hermes chat                        # fresh session
hermes chat --continue OA          # named persistent session
hermes chat --resume <session-id>  # resume by ID
```

### Check Hermes status
```powershell
hermes status
hermes doctor
```

### Verify MCP server responds
```powershell
$env:PYTHONUNBUFFERED="1"
'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"vscode","version":"1.0"}}}' |
  & "C:\Users\Manoj\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe" mcp serve 2>$null
```

### Use Hermes tools inside Copilot Chat
1. `Ctrl+Shift+P` → **Developer: Reload Window**
2. Open Copilot Chat
3. Click the **tools icon** (wrench/sparkle) in the input bar
4. Enable Hermes tools (memory, delegation, session_search, etc.)
5. Ask Copilot: *"Use the hermes memory tool to store/recall context about the OpenAlgo project"*

### Hermes config files
| File | Purpose |
|---|---|
| `%LOCALAPPDATA%\hermes\config.yaml` | Model, personality, compression, timezone |
| `%LOCALAPPDATA%\hermes\.env` | API keys (Gemini, OpenRouter, etc.) |
| `%APPDATA%\Code\User\mcp.json` | VS Code MCP server registration |
| `%LOCALAPPDATA%\hermes\acp_bridge.py` | Protocol bridge (ACP↔MCP, optional) |

---

## Issue Log

| # | Problem | Root Cause | Fix |
|---|---|---|---|
| 1 | `hermes acp` not shown in VS Code | Bare `"command":"hermes"` unresolvable in VS Code PATH | Use full absolute path in `mcp.json` |
| 2 | `-32602 Invalid params` on ACP connect | VS Code sends string `"2024-11-05"`, Hermes expects integer `1` | Switch to `hermes mcp serve` (standard MCP) |
| 3 | `Fatal Python error: _enter_buffered_busy` | Windows buffered stdin lock race at shutdown | Add `PYTHONUNBUFFERED=1` to env in `mcp.json` |
| 4 | `@hermes` not a chat participant | MCP servers provide tools, not `@`-mentionable chat agents | Use `hermes chat` in terminal for direct conversation |
| 5 | `hermes chat --session` unrecognized | Flag doesn't exist | Use `--continue <name>` or `--resume <id>` |
