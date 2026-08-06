# Setup/Linking `gemini-web2api` with OpenCode (Windows)

## Overview

[`gemini-web2api`](https://github.com/Sophomoresty/gemini-web2api) (v1.1.0) reverse-engineers Google Gemini's **web** `StreamGenerate` protocol and exposes it as a local, **OpenAI-compatible API**. OpenCode (v1.18.12) consumes it as a custom provider via the `@ai-sdk/openai-compatible` runtime, so the 8 Gemini models appear directly in OpenCode's model picker.

Confirmed flow:

```text
OpenCode (CLI / desktop)
   │  provider "gemini-web2api"          npm: @ai-sdk/openai-compatible
   ▼
gemini-web2api server  (127.0.0.1:8085)  OpenAI-compatible /v1 endpoints
   │  StreamGenerate RPC
   ▼
gemini.google.com  (anonymous / web session)
```

Key confirmed facts:

| Item | Value |
|---|---|
| `gemini-web2api` version | 1.1.0 |
| OpenCode version | 1.18.12 |
| Python | 3.14.0 |
| `httpx` | 0.28.1 |
| Base URL | `http://127.0.0.1:8085/v1` |
| Host / port | `127.0.0.1` / `8085` |
| Default model | `gemini-3.6-flash` |

## Prerequisites

- Windows (verified on `win32`, PowerShell 5.1).
- Python 3.8+ (verified on 3.14). The packaging metadata requires `>=3.8`.
- `git`.
- OpenCode CLI installed (`opencode --version` → 1.18.12).
- Direct network access to `gemini.google.com` (confirmed reachable on this machine; a proxy/VPN is required in regions where it is blocked — see Troubleshooting).

## 1. Installation

### 1.1 Clone

```bash
git clone --depth 1 https://github.com/Sophomoresty/gemini-web2api.git "C:\Users\Manoj\tools\gemini-web2api"
```

> **Flagged assumption** — `C:\Users\Manoj\tools\` did not exist and was created during setup as the chosen system-wide install parent. Adjust this path if you prefer a different location, and propagate the change anywhere the path appears below.

### 1.2 Packaging fix (required)

The repo ships both `gemini_web2api.py` and a `gemini_web2api/` package at the root, which breaks setuptools auto-discovery. Add an explicit `packages` directive to the cloned `pyproject.toml`:

```toml
[project.scripts]
gemini-web2api = "gemini_web2api.__main__:main"

[tool.setuptools]
packages = ["gemini_web2api"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

### 1.3 Install with streaming support

`[streaming]` pulls in the optional `httpx` dependency (streaming HTTP). Edit-mode keeps the installed command tied to the clone for easy `git pull` updates.

```bash
pip install -e "C:\Users\Manoj\tools\gemini-web2api[streaming]"
```

Expected result: `Successfully installed gemini-web2api-1.1.0`, plus `httpx 0.28.1`.

### 1.4 Make the command available system-wide

The console script is installed to:

```text
C:\Users\Manoj\AppData\Roaming\Python\Python314\Scripts
```

Verify it resolves:

```powershell
gemini-web2api --version   # -> gemini-web2api 1.1.0
```

If it does not resolve, add that `Scripts` directory to the user `PATH`:

```powershell
$scriptsDir = "C:\Users\Manoj\AppData\Roaming\Python\Python314\Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$scriptsDir*") {
  [Environment]::SetEnvironmentVariable("Path", $userPath.TrimEnd(';') + ";" + $scriptsDir, "User")
}
```

## 2. Server configuration

### 2.1 Config file

The packaged entry point discovers config from `./config.json` (cwd) or `~/.config/gemini-web2api/config.json` (or the `GEMINI_WEB2API_CONFIG` env var / `--config` flag). The confirmed system-wide file is:

**`C:\Users\Manoj\.config\gemini-web2api\config.json`**

```json
{
  "port": 8085,
  "host": "127.0.0.1",
  "retry_attempts": 3,
  "retry_delay_sec": 2,
  "request_timeout_sec": 180,
  "gemini_bl": "boq_assistant-bard-web-server_20260716.08_p0",
  "auth_user": null,
  "xsrf_token": null,
  "default_model": "gemini-3.6-flash",
  "api_keys": ["<YOUR_API_KEY>"],
  "cookie_file": null,
  "proxy": null,
  "log_requests": true,
  "temporary_chats": false
}
```

Field notes (confirmed from the project README and this session):

- `port` — set to **8085** to avoid a collision with React Native Metro's default `8081` (see Troubleshooting for details). The project default is `8081`.
- `host` — set to `127.0.0.1` (local-only). The project default is `0.0.0.0` (LAN-exposed).
- `api_keys` — when non-empty, `/v1/*` requires `Authorization: Bearer <key>` or `x-api-key: <key>`. Empty array disables auth. This value **is the same one stored in OpenCode's auth.json** (§4.2).
- `gemini_bl` — the frontend build identifier the RPC targets; the server auto-updates it when stale.

> **Sensitive value redacted** — the actual key value is not reproduced here; it is a locally generated shared secret. Replace every `<YOUR_API_KEY>` below with the same value you put in `api_keys`.

### 2.2 Start and verify

```powershell
gemini-web2api
```

Server output (confirmed):

```text
gemini-web2api v1.1.0
  Listening: http://0.0.0.0:8085
  Base URL:  http://localhost:8085/v1
  Models:    gemini-3.6-flash, gemini-3.5-flash, gemini-3.5-flash-thinking, gemini-3.1-pro, gemini-auto, gemini-3.5-flash-thinking-lite, gemini-flash-lite
  Cookie:    none (anonymous)
  Proxy:     system env
  Streaming: httpx (true streaming)
```

Verify the endpoints:

```bash
curl.exe -s -H "Authorization: Bearer <YOUR_API_KEY>" http://127.0.0.1:8085/v1/models
```

Confirmed response — 8 models (the server may also expose `gemini-3.1-pro-enhanced`):

```json
{
  "object": "list",
  "data": [
    { "id": "gemini-3.6-flash",            "owned_by": "google" },
    { "id": "gemini-3.5-flash",            "owned_by": "google" },
    { "id": "gemini-3.5-flash-thinking",   "owned_by": "google" },
    { "id": "gemini-3.1-pro",              "owned_by": "google" },
    { "id": "gemini-3.1-pro-enhanced",     "owned_by": "google" },
    { "id": "gemini-auto",                 "owned_by": "google" },
    { "id": "gemini-3.5-flash-thinking-lite", "owned_by": "google" },
    { "id": "gemini-flash-lite",           "owned_by": "google" }
  ]
}
```

## 3. Automatic startup on login

A Windows **Scheduled Task at logon** was attempted first but failed with `Register-ScheduledTask: Access is denied` because the account is **not elevated** (confirmed `Admin? False`). The working non-admin solution is a **Startup-folder shortcut**.

### 3.1 Hidden launcher

**`C:\Users\Manoj\tools\gemini-web2api\start-hidden.vbs`** launches the server with no console window:

```vbscript
' gemini-web2api auto-start launcher (runs hidden)
Option Explicit
Dim shell, exePath
exePath = "C:\Users\Manoj\AppData\Roaming\Python\Python314\Scripts\gemini-web2api.exe"
cfgPath = "C:\Users\Manoj\.config\gemini-web2api\config.json"
Set shell = CreateObject("WScript.Shell")
shell.Run Chr(34) & exePath & Chr(34) & " --config " & Chr(34) & cfgPath & Chr(34), 0, False
Set shell = Nothing
```

### 3.2 Startup shortcut

A `.lnk` named `gemini-web2api.lnk` was created in:

```text
C:\Users\Manoj\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
```

with `Target = wscript.exe`, `Arguments = "C:\Users\Manoj\tools\gemini-web2api\start-hidden.vbs"`, `WindowStyle = 7` (minimized).

To rebuild it programmatically:

```powershell
$startup = [Environment]::GetFolderPath("Startup")
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("$startup\gemini-web2api.lnk")
$sc.TargetPath = "wscript.exe"
$sc.Arguments = '"C:\Users\Manoj\tools\gemini-web2api\start-hidden.vbs"'
$sc.WorkingDirectory = "C:\Users\Manoj\tools\gemini-web2api"
$sc.WindowStyle = 7
$sc.Description = "Auto-starts the local Gemini Web2API server (hidden)"
$sc.Save()
```

Result: the server starts silently at every login. Verify by killing any running instance, launching via `cscript //nologo ...\start-hidden.vbs`, and confirming a listener exists:

```powershell
Get-NetTCPConnection -LocalPort 8085 -State Listen
```

## 4. Linking into OpenCode

OpenCode's global config is shared by the **CLI and the desktop app**, so one change covers both.

### 4.1 Provider config

**`C:\Users\Manoj\.config\opencode\opencode.jsonc`** (existing file, provider block appended):

```jsonc
{
  "plugin": [
    "oh-my-openagent@latest",
    "./plugins/claude-mem.js",
    "~/.config/opencode/node_modules/superpowers",
    "~/.config/opencode/node_modules/@dietrichgebert/ponytail/.opencode/plugins/ponytail.mjs"
  ],
  "provider": {
    "gemini-web2api": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Gemini Web2API (local)",
      "options": {
        "baseURL": "http://127.0.0.1:8085/v1"
      },
      "models": {
        "gemini-3.6-flash":             { "name": "Gemini 3.6 Flash" },
        "gemini-3.5-flash":             { "name": "Gemini 3.5 Flash" },
        "gemini-3.5-flash-thinking":    { "name": "Gemini 3.5 Flash Thinking" },
        "gemini-3.5-flash-thinking-lite": { "name": "Gemini 3.5 Flash Thinking Lite" },
        "gemini-3.1-pro":               { "name": "Gemini 3.1 Pro" },
        "gemini-3.1-pro-enhanced":      { "name": "Gemini 3.1 Pro Enhanced" },
        "gemini-auto":                  { "name": "Gemini Auto" },
        "gemini-flash-lite":            { "name": "Gemini Flash Lite" }
      }
    }
  },
  "$schema": "https://opencode.ai/config.json"
}
```

Consistency with the official docs:

- `npm: "@ai-sdk/openai-compatible"` — correct for an OpenAI `/v1/chat/completions` endpoint. (Per docs, use `@ai-sdk/openai` only for `/v1/responses`.)
- `models` IDs must match the `id` returned by `GET /v1/models` (verified above).
- `options.baseURL` points at the running server.
- `options.apiKey` is intentionally **absent** — the key is supplied by the credential store (§4.2), which is the documented alternative to hardcoding it.

### 4.2 Register the credential

Instead of the interactive `/connect` (TUI), the credential was written directly to OpenCode's auth store in the exact schema `Auth.set` uses for API keys:

**`C:\Users\Manoj\.local\share\opencode\auth.json`**

```json
{
  "gemini-web2api": {
    "type": "api",
    "key": "<YOUR_API_KEY>"
  }
}
```

> **Sensitive value redacted** — `<YOUR_API_KEY>` must equal the value in the server's `api_keys` array (§2.1).

Confirm:

```powershell
opencode auth list
```

Expected:

```text
┌  Credentials ~\.local\share\opencode\auth.json
│  •  gemini-web2api  api
└  1 credentials
```

## 5. Usage

1. Ensure the server is running: `gemini-web2api`.
2. In OpenCode: model picker twice, select any `gemini-web2api/*` model (`/models`), or pass it explicitly via CLI.
3. The desktop app reads the same global config — restart it once after any config/credential change to pick it up.

Model identifier format:

```text
gemini-web2api/<model-id>
```

Thinking-depth suffix is supported on model names (e.g. `gemini-3.5-flash-thinking@think=0`), per the upstream README.

## 6. Examples

### OpenCode CLI (via provider)

```bash
opencode run "Explain dynamic programming" --model gemini-web2api/gemini-3.5-flash
```

Confirmed: this reaches the server via `llm.provider=gemini-web2api` / `llm.model=gemini-3.5-flash` and returns a real Gemini reply.

### Raw API — models list

```bash
curl.exe -s -H "Authorization: Bearer <YOUR_API_KEY>" http://127.0.0.1:8085/v1/models
```

### Raw API — chat completion

```bash
curl.exe --% http://127.0.0.1:8085/v1/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer <YOUR_API_KEY>" -d "{\"model\":\"gemini-3.5-flash\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello!\"}]}"
```

> On PowerShell, use `curl.exe` and `--%` so quotes are not re-parsed, and prefer a request-body file when the body is complex.

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8085/v1", api_key="<YOUR_API_KEY>")
resp = client.chat.completions.create(
    model="gemini-3.5-flash-thinking",
    messages=[{"role": "user", "content": "Explain quantum computing"}],
)
print(resp.choices[0].message.content)
```

### Tool calling

```python
resp = client.chat.completions.create(
    model="gemini-3.5-flash",
    messages=[{"role": "user", "content": "What's the weather in Tokyo?"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }],
)
```

## 7. Troubleshooting

**Port collision with React Native Metro.**
Both gemini-web2api (default `8081`) and Metro (`react-native/cli.js start`) bind `8081`. Confirmed both were coexisting via `SO_REUSEADDR`, which is unstable (requests may route to the wrong process). Resolved by moving gemini-web2api to **`8085`** in both the server config and OpenCode `baseURL`. Check the listener:

```powershell
Get-NetTCPConnection -LocalPort 8085 -State Listen   # gemini server
Get-NetTCPConnection -LocalPort 8081 -State Listen   # Metro
```

**`opencode auth list` shows 0 credentials while the desktop/CLI connection works.**
When the key is hardcoded in `options.apiKey`, no credential record exists. Expected. To make the credential visible (the official `/connect` flow), create `auth.json` as in §4.2 and remove `options.apiKey` from the config.

**Server logs show nothing recent.**
Python buffers `stderr` when redirected to a file; a running instance created via `Start-Process -RedirectStandardError` may lag in file output. Confirm liveness via the port/`/v1/models` instead.

**Upstream `gemini.google.com` unreachable / times out.**
Direct access is confirmed working on this machine (system proxy disabled). If you hit `curl: (28)` timeouts, set a proxy via CLI, config, or env var:

**CLI:**
```bash
gemini-web2api --proxy http://127.0.0.1:7890
```
**Config:**
```json
{ "proxy": "http://127.0.0.1:7890" }
```
**Env (auto-detected):**
```bash
export HTTPS_PROXY=http://127.0.0.1:7890
```

**Response ignores an exact-output instruction.**
Gemini web is non-deterministic and may ignore "reply exactly with X" phrasing, returning unrelated or elaborate content instead. This is upstream behavior of the reverse-engineered web API; it does not indicate a connection failure.

**`autostart scheduled task` fails with "Access is denied".**
`Register-ScheduledTask` at logon requires elevation. Use the Startup-folder shortcut (§3.2) instead, which needs no admin.

**`gemini-3.1-pro` behaves like Flash.**
Anonymous access routes `3.1-pro` to Flash. Real Pro routing requires a Gemini Advanced cookie (see upstream README's Optional Cookie section). A free-account cookie authenticates but silently falls back to Flash.

## 8. References

- Project repo & README: <https://github.com/Sophomoresty/gemini-web2api>
- OpenCode providers docs (Custom provider): <https://opencode.ai/docs/providers/#custom-provider>
- AI SDK openai-compatible package: `@ai-sdk/openai-compatible`
- Config discovery precedence (server): `--config` → `GEMINI_WEB2API_CONFIG` → `./config.json` → `~/.config/gemini-web2api/config.json`

---

## Appendix — files created/modified

| Path | Action | Purpose |
|---|---|---|
| `C:\Users\Manoj\tools\gemini-web2api\` | created (clone) | source + `pyproject.toml` fix |
| `C:\Users\Manoj\tools\gemini-web2api\start-hidden.vbs` | created | hidden auto-start launcher |
| `...\Start Menu\Programs\Startup\gemini-web2api.lnk` | created | auto-start on login |
| `C:\Users\Manoj\.config\gemini-web2api\config.json` | created | server config (port 8085, key) |
| `C:\Users\Manoj\.config\opencode\opencode.jsonc` | edited | added `gemini-web2api` provider |
| `C:\Users\Manoj\.local\share\opencode\auth.json` | created | API-key credential |
| bash/python `PATH` | edited | `...\Python314\Scripts` for `gemini-web2api` |

Open questions intentionally not changed: whether to later expose the server on `0.0.0.0` (LAN) or move from local-only `127.0.0.1` — not done, to keep the default secure.

---

Done. Installed and configured end to end, with two deviations from the doc due to your machine:

**Installed**
- Cloned `gemini-web2api` v1.1.0 to `C:\Users\Manoj\tools\gemini-web2api` + applied the setuptools `packages` fix
- `pip install -e "...[streaming]"` (httpx 0.28.1 already present)
- Script resolved on PATH at `...\Python313\Scripts` (you have **Python 3.13 Store**, not 3.14 — I used the real paths throughout)

**Configured & verified**
- `C:\Users\Manoj\.config\gemini-web2api\config.json` — port 8085, host 127.0.0.1, generated shared API key. Fixed a UTF-8 BOM issue (PowerShell 5.1 writes BOM by default, which broke Python's JSON parser)
- Server running on `127.0.0.1:8085`; `/v1/models` returns all 8 Gemini models; chat completion returns real replies
- Auto-start: `start-hidden.vbs` (hidden, points at the actual 3.13 exe path) + `gemini-web2api.lnk` in the Startup folder — verified it relaunches the listener
- `opencode.jsonc` — `gemini-web2api` provider with `@ai-sdk/openai-compatible`, baseURL `http://127.0.0.1:8085/v1`, 8 models
- `auth.json` — `gemini-web2api` api credential; `opencode auth list` shows 1 credential
- Confirmed via OpenCode: `opencode run "..." --model gemini-web2api/gemini-3.5-flash` → returned a real Gemini reply

The API key is saved at `C:\Users\Manoj\AppData\Local\Temp\opencode\gwa_key.txt` if you ever need it; same value is in `config.json` and `auth.json`. Note `gemini-3.1-pro` will behave like Flash without an Advanced cookie (as documented).
