# General System Tooling Prompts

## Generic, Multi-Agent _agentplay_ Prompt
```text
Please act as my systems and tooling orchestrator. I want to install and set up `agentplay` (https://github.com/Entelligence-AI/agentplay/blob/main/README.md) both globally and from source at `~/agentplay` to serve as a local session replay analyzer, timeline visualizer, and trace forensics tool for my AI coding agent sessions (such as Claude Code, Codex CLI, Cursor, Windsurf, Cline, or any supported client).

**Target Input & Interactive Discovery (Interrogate User Before Proceeding):**
- `TARGET_AGENT`: `<specify or leave blank to scan>`
- `ACTIVE_TRANSCRIPT_PATH`: `<specify or leave blank to scan>`
- **Discovery & Confirmation Protocol:** If `TARGET_AGENT` or `ACTIVE_TRANSCRIPT_PATH` is not explicitly filled in above:
  1. Perform a strictly read-only, non-locking scan of known local agent directories (e.g., `~/.codex/`, `~/.claude/`, `~/.cursor/`, `~/.windsurf/`, etc.) to discover available agents and their most recently modified session transcripts (displaying file path, last-modified timestamp, and file size).
  2. **Pause and interrogate me** with a numbered list of the auto-detected agent/transcript options (plus an option to provide a custom path) and wait for my explicit selection before copying any files or running `agentplay build`.

Follow these strict safety, installation, disk, and memory guidelines:

### 1. Host Prerequisites & Global Setup (First Step)
- First, check the host system for required build and runtime tools: **Python 3.11+** (prefer 3.12+), **`uv`**, **`pipx`**, **Git**, **GNU Make**, **Node.js 20+ / npm**, and **`pnpm`** (required for `make setup` and building the web viewer).
- If any prerequisite is missing on the host, **install it globally on the host first** before proceeding.
- Read the repository's `README.md` and `install.md` to ensure full compliance with its native setup checks and supported environment variables.
- Configure strict local-only privacy and isolated agent home environment variables for the session so zero network calls or signup prompts occur, and persist them to `~/.bashrc` (or the active shell profile):
  `export AGENTPLAY_NO_NETWORK=1`
  `export DO_NOT_TRACK=1`
  *(Once the target agent is confirmed, also export its corresponding isolated home override variable—e.g., `AGENTPLAY_CODEX_HOMES`, `AGENTPLAY_CLAUDE_HOMES`, or equivalent supported by `agentplay`—pointing to `~/agentplay_workspace/agent_home`).*

### 2. Zero-Impact Transcript Safety & Dynamic Sizing (CRITICAL)
- My AI coding client may be actively running and continuously appending to the confirmed `ACTIVE_TRANSCRIPT_PATH` inside its live state directory (e.g., `~/.codex/`, `~/.claude/`, `~/.cursor/`, etc.).
- DO NOT edit, rename, truncate, move, write to, or hold an exclusive file lock on the active transcript or anything inside the live agent state directory.
- Treat the live agent directory as STRICTLY READ-ONLY.
- **Dynamic Size & Event-Limit Handling:** `agentplay` skips transcripts >512 MB and truncates session maps after 20,000 events. Before copying the confirmed transcript, inspect its file size and line/event count dynamically using non-locking stream reads:
  1. Create an isolated workspace directory that mirrors the relative directory structure expected by the target agent's parser, plus an export folder:
     `mkdir -p ~/agentplay_workspace/agent_home/<relative_agent_session_subdir>`
     `mkdir -p ~/agentplay_workspace/exports/`
  2. **If the transcript is within safe limits (<512 MB and <=20,000 events):** Extract a non-locking, read-only copy of the **entire untrimmed session** from start to finish into `~/agentplay_workspace/agent_home/<relative_agent_session_subdir>/`.
  3. **If the transcript exceeds 512 MB or 20,000 events:** Create a safe, valid snapshot in the workspace by preserving any required session metadata/header lines from the start of the file and streaming the most recent N lines/events so it stays cleanly under the truncation ceiling.
  4. Validate JSON/JSONL integrity line-by-line using a streaming Python check to strip or repair any incomplete trailing line caused by an active write during copy.

### 3. Global Install & Source Setup at `~/agentplay`
- **Global CLI Install:** Install `agentplay` globally on the host using `uv` (or `pipx` / `pip`) and ensure the binary is linked in `PATH` (e.g., `~/.local/bin` or `/usr/local/bin/agentplay`) so the CLI is accessible system-wide:
  `uv tool install agentplay`
- **Source Clone & Full Build at `~/agentplay`:**
  1. Clone the repository (or pull latest if already present):
     `git clone https://github.com/Entelligence-AI/agentplay ~/agentplay`
  2. Navigate to `~/agentplay` and run the official source build targets:
     - `make setup PY=$(which python3.12 || which python3)` (sets up `python/.venv` with dev dependencies and runs `pnpm install` in `viewer`)
     - `make viewer` (builds the frontend web viewer into `viewer/dist` and copies it into `python/src/agentplay/viewer`)
     - `make check` (runs `ruff`, `tsc`, `pytest`, `vitest`, and the hygiene guard to verify a clean build)

### 4. Resource, Memory & Storage Guardrails
- **Memory Guard:** Never load large raw transcript files into memory at once in any custom Python or Node script; always use `agentplay`'s streaming parser or line-by-line iteration.
- **Data Isolation Guard:** Point `agentplay` strictly at the isolated workspace directory (`~/agentplay_workspace/agent_home`) so it never scans, locks, or creates I/O contention on any live agent directories.
- **Local Server Guard:** Ensure the viewer binds strictly to `127.0.0.1` (localhost) with no external network exposure.

### 5. Session Replay, Map Building & Trace Forensics Goal
- Run `agentplay agents` to verify that the selected target agent is detected and pointing to `~/agentplay_workspace/agent_home`.
- Run `agentplay build --rebuild --json` to compile the session map across all captured prompts/turns and output the machine-readable build summary.
- Run `agentplay list --json` to inspect the indexed session(s), total token counts, session duration, tool/MCP touchpoints, and error counts.
- Export the mapped session using `agentplay export` into `~/agentplay_workspace/exports/session_map.json` so we can programmatically inspect:
  - **File contact maps:** Which files were searched, read, or edited across all turns.
  - **Failure & retry clusters:** Exact shell exit codes, tool errors, failed hooks, and repeated retry loops.
  - **Context compactions & model switches:** Where models switched or context compressed/expanded along the timeline.
- Start the local replay server in the background on an available local port (default `7317`):
  `agentplay view --no-build --no-open --port 7317`
- Verify `curl -s http://127.0.0.1:7317/api/status` returns `"available": true` and summarize the forensic findings from the exported session map.

Start by verifying host prerequisites, scanning for available agent transcripts to present my selection menu (if not hardcoded above), and walking me through the setup and build once I confirm the target session.
```

