# General Use Prompts

## Runbook Refinement Prompt / Compact Docs Rewrite
```text
Redesign this Markdown into a compact, production-quality operations document with clean hierarchy and a logical flow — Overview → Prerequisites → Setup/Installation → Configuration → Verification → Usage → Troubleshooting → Security → Cleanup → Reference — using only the sections that are actually relevant to the content. Combine related shell/CLI commands into a single sequential, executable code block per section rather than scattering one-line commands, so each block can be copied and run top-to-bottom without manual reassembly. Mark any optional steps or commands clearly as optional, with a brief note explaining when or why they apply. Preserve all technical details and accuracy while removing unnecessary explanation, filler, and repetition; surface important notes, warnings, or security considerations only where they genuinely matter — such as while troubleshooting or before a destructive step — not as decoration. In the Reference section, list relevant file paths using relative/home-relative notation (e.g. `~/.ssh/config`), noting which are needed only for production-grade hardening, since not every file requires hardening. Use concise, human-friendly language and minimal but purposeful formatting (headings, code blocks, tables) to produce a polished, self-contained document that's easy to scan, execute, and maintain long-term.
```

---

## OpenAlgo Source-Grounded Cross-Check Loop
```text
Now start a new finding loop (cross-check every traces/my-given-findings locally against the real-world OpenAlgo setup: the latest OpenAlgo infra from the GitHub-cloned [Official Repo: https://github.com/marketcalls/openalgo] local repo at `/home/ubuntu/openalgo/` and the Python SDK — used together in combination; the Python SDK's source code calls into OpenAlgo infra via `{openalgo-infra-repo}/restx_api/`, or if validation fails within that directory alone, expand the search to `{openalgo-infra-repo}/...`; load both the infra and SDK source from GitHub into session memory and ground all findings in their source code as evidence — do not trust SDK or OpenAlgo infra internal code/function docstrings alone — then assess effects and patches strictly according to those sources) — starting from a clean slate.
```

---

## Structural Analysis — Oh-My-Opencode / Codegraph
```text
Act as a compiler engineer. Run exhaustive multi-layer structural analysis on the given file/project via `codegraph_explore` + internal AST parser. Strict rules:

1. **Truncate nothing.** Index every node — class, function, decorator, control-flow, assign, call, return, raise, await, yield, lambda, comprehension — all assigned sequential IDs (`Node000001…`).
2. **Multi-representation parse:** AST (structure) + LibCST (comments/exact positions) + `symtable` (scope resolution). Never trust docstrings as ground truth.
3. **Build layered graphs in order:** Call Graph → per-function CFG (execution paths, unreachable branches, exception flows) → DFG (variable definition / mutation / consumption chains, tainted-data propagation).
4. **Typed knowledge graph:** entities — Module, Class, Function, Variable, Import, Decorator, Exception, AsyncTask, Thread; edges — `calls`, `imports`, `inherits`, `mutates`, `raises`, `returns`, `reads`, `writes`, `catches`.
5. **Trace every call path** step-by-step including dynamic dispatch, callbacks, decorators, and monkey-patching.
6. **Detect smells:** God Objects/Functions, cyclic imports, tight coupling, deep nesting, mutable globals, hidden side effects.
7. **Security pass:** flag `eval`, `exec`, `pickle`, `yaml.load`, `subprocess(shell=True)`, `os.system`, SQL string concat, hardcoded secrets.
8. **Map full structural blast radius** of any change — upstream + downstream through the complete dependency chain.
```

---

## Auditing, Verification & Fixes Pormpts

### Verify-Then-Fix Audit / Findings Verification & Conditional Fix
```text
Verify whether the findings below are correct by analyzing them in depth against the complete script/codebase architecture, including all usages, dependencies, and relationships with other components. Then apply fixes only if still necessary after this verification.
```

### Post-Fix Consistency Audit / Step-by-Step Fix Reconciliation
```text
Verify that all fixed or patched findings are correct and mutually consistent with each other within the complete script/codebase architecture. Go through this step by step, in depth, checking all usages and relationships with other components, and identify any subtle or remaining findings and issues that still need attention.
```

### Context-Scoped Correctness Audit / Last-Context Integrity Check
```text
Review all changes made so far and verify their correctness end-to-end, using the last valid message and available context to determine the correct scope of review. Explicitly check for anything that was skipped, left incomplete, or silently dropped, and surface it clearly rather than assuming it was handled.
```

### Post-Continue Verification Check / Continuity & Correctness Audit
```text
Review all changes made so far and verify their correctness end-to-end. Explicitly check for anything that was skipped, left incomplete, or silently dropped during prior "Continue" responses, and surface it clearly rather than assuming it was handled.
```

---

## New Online Auditing Pormpts

### A
```text
Now refetch the new script and validate against below applied patches on your last findings (Verify after fetched & loaded the new script from GitHub);
[Your/AI made changes summary goes here]
```

### B
```text
Now refetch the new script and validate against applied patches (By checking diff from last/previous version script) on your last findings (Verify after fetched & loaded the new script from GitHub).
```

---

## 9Router Docker Compose + Prompt

### Docker Compose
```yml
services:
  9router:
    image: 'decolua/9router:latest'
    container_name: 9router

    # ── Networking: no host access needed ──────────────────────
    # 9Router is a pure API router/proxy - it never needs host
    # filesystem, process, or network access. Standard bridged
    # container + Coolify's normal reverse-proxy path is correct
    # here; no nsenter, no network_mode: host, no cap_add.
    environment:
      - SERVICE_FQDN_9ROUTER_20128
      # If Coolify's generated FQDN value doesn't include the
      # https:// scheme, change these two lines to:
      #   - BASE_URL=https://${SERVICE_FQDN_9ROUTER_20128}
      #   - NEXT_PUBLIC_BASE_URL=https://${SERVICE_FQDN_9ROUTER_20128}
      # Check the Environment Variables tab after first deploy to
      # see the actual populated value before assuming either form.
      - 'BASE_URL=${SERVICE_FQDN_9ROUTER_20128}'                  # server-side preferred var, per .env.example
      - 'NEXT_PUBLIC_BASE_URL=${SERVICE_FQDN_9ROUTER_20128}'      # backward-compatible/public var, per .env.example

      - DATA_DIR=/app/data
      - PORT=20128
      - HOSTNAME=0.0.0.0
      - NODE_ENV=production

      # ── Token Saver: point at the Headroom sidecar ───────────
      - HEADROOM_URL=http://headroom:8787

      # ── Secrets - set real values via Coolify's env var UI, ──
      # ── never leave these as literal defaults              ──
      - 'JWT_SECRET=${JWT_SECRET}'
      - 'INITIAL_PASSWORD=${INITIAL_PASSWORD}'          # official default is "123456" - MUST override for a public deploy
      - 'API_KEY_SECRET=${API_KEY_SECRET}'
      - 'MACHINE_ID_SALT=${MACHINE_ID_SALT}'

      # ── Security hardening for a public, proxied deployment ──
      - AUTH_COOKIE_SECURE=true    # README: "set true behind HTTPS reverse proxy" - Coolify/Traefik terminates TLS, this is exactly that case
      - REQUIRE_API_KEY=true       # README: "recommended for internet-exposed deploys" - without this, /v1/* is open to anyone who finds the subdomain
      - ENABLE_REQUEST_LOGS=false  # enable only when actively debugging - writes full request/response logs

    volumes:
      - '9router-data:/app/data'

    expose:
      - '20128'

    depends_on:
      - headroom

    healthcheck:
      test:
        - CMD-SHELL
        # Node.js is guaranteed present (it's the app's own runtime),
        # regardless of the base image's shell/tooling - more portable
        # than assuming curl/wget/bash are available.
        - "node -e \"require('http').get('http://127.0.0.1:20128/api/health', r => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))\""
      interval: 30s
      timeout: 5s
      retries: 3

    restart: unless-stopped

  headroom:
    image: 'ghcr.io/chopratejas/headroom:latest'
    container_name: headroom

    # ── Internal-only, on purpose ────────────────────────────
    # Headroom only needs to be reachable by 9router over the
    # compose network (http://headroom:8787). The official compose
    # publishes 8787 to the host; we deliberately don't - nothing
    # outside this stack needs to talk to it, so no expose/ports
    # entry means one less thing exposed on a public-facing host.
    restart: unless-stopped

volumes:
  9router-data:
```

### Prompt
```
Here is official 'https://github.com/decolua/9router/blob/master/docker-compose.yml' read it; Now adjust/update our last version yml if needed;
And After Done in the end; Process the `9router` related only (Skip all others completely) from entire available chat/session/workspace context as the single source of truth and produce a complete, coherent, production-quality output in clean Markdown — do not invent facts, steps, values, or claims that weren't actually present or confirmed in that context. Consolidate all relevant information, decisions, corrections, and refinements discussed so far into one unified piece, eliminating redundancy and repetition, resolving contradictions by treating the most recently confirmed version as authoritative, and explicitly flagging any gap you had to fill with a reasonable assumption. Redact or placeholder any sensitive, private, or confidential information rather than reproducing it verbatim. Compress aggressively, surfacing only the decisions, conclusions, and action items that matter — omit exploratory back-and-forth. Organize as overview → key points → decisions made → open questions → next steps. Keep language concise, precise, and free of filler, using clear headings, lists, tables, code blocks, or other Markdown elements only where they genuinely aid readability, to create a polished, self-contained, ready-to-use document that a reader unfamiliar with the original conversation could still fully understand.
```

---

## AutonomousTrading Cleanup — Debian Instance

```text
Check whether you have complete access to the `Debian` instance. If not, read `@aws-keys/cross-instance-ssh.md` first and fix access before proceeding.

You already completed the full setup/configuration (per session/chat history) and also fixed the nginx issue on the `Debian` instance. The home path is `/home/<admin/ubuntu/debian>/`.

We now need to clean up, remove, and revert everything you did while working on `AutonomousTrading` on the `Debian` instance. This is because I've implemented two MCPs on the same server, which now handle a newer built-in version of `AutonomousTrading` — we'll work on that fresh, later, as a clean start. For now, a complete cleanup is required.

Make sure you do NOT touch the running OpenAlgo Docker container or its processes.
```

---

## AutonomousTrading Fresh Setup — Debian Instance

```text
Here is a private repo of mine, so you'll need to access it using the token `{GITHUB_TOKEN}`.
Using that token, read `https://github.com/manojvermamv/AutonomousTrading/blob/main/README.md`, including all referenced markdown files as well.

Then clone the complete setup onto the Debian instance at home path `/home/admin/`. Do not follow any previous manual setup workaround — this repo includes an installer script; use that instead. Also, do not perform manual analysis, diagnosis, or fix workarounds unless I explicitly ask for it.
```
