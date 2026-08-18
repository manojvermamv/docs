# General Use Prompts

## Simplify & Summary Prompts

### Template 1 — Shorter simplify + final suggestion only
`````text
Simplify what's below into plain, simple language. Cover:
- What it means
- What it's actually doing
- Why it exists
- Whether it's describing something planned for before or after implementation
Also cover What's Done, What Remains, and What Needs to Be Decided — only if that applies here.
Then tell me what we should do next, as a higher-level suggestion.
Along the way, check this against the conversation so far — if something looks like drift or a contradiction, flag it in one short line instead of writing it up.

````
CONTENT_PLACEHOLDER
````
`````

### Template 2 — Full simplify + status + decisions + direction
`````text
Simplify what's below into plain, simple language — using the context boundaries given plus your own deep research on the topic. Cover:
- What it means
- What it's actually doing
- Why it exists
- Whether it's describing something planned for before or after implementation
Also cover What's Done, What Remains, and What Needs to Be Decided — only if that applies here — with your own higher-level suggestions on each.
Finally, tell me what we should do next, in the same higher-level suggestion style.
Along the way, check this against the conversation so far — if something looks like drift or a contradiction, flag it in one short line instead of writing it up.

````
CONTENT_PLACEHOLDER
````
`````

### Template 3 — Compare against the previous one
`````text
Just for what's below: explain, in plain language, what this is actually saying and how it compares against the previous one. Cover What's Done, What Remains, and What Needs to Be Decided — only if that applies here. Suggest those decisions yourself, and suggest what direction to take next.
Along the way, check this against the conversation so far — if something looks like drift or a contradiction, flag it in one short line instead of writing it up.

````
CONTENT_PLACEHOLDER
````
`````

### Template 4 — Directional Audit & Drift Detection
`````text
Audit what's below against the full context of this conversation — every prompt given so far, in order, and your own reasoning across earlier responses, not just what's pasted below. Look specifically for drift: anywhere this has quietly moved away from, contradicted, or lost track of the direction already set.
If everything still lines up, say so in one line. If something looks wrong, don't write a report — ask about it in a single, short, conversational paragraph, kept minimal.

````
CONTENT_PLACEHOLDER
````
`````

---

## Runbook Refinement Prompt / Compact Docs Rewrite
```text
Redesign this Markdown into a compact, production-quality operations document with clean hierarchy and a logical flow — Overview → Prerequisites → Setup/Installation → Configuration → Verification → Usage → Troubleshooting → Security → Cleanup → Reference — using only the sections that are actually relevant to the content. Combine related shell/CLI commands into a single sequential, executable code block per section rather than scattering one-line commands, so each block can be copied and run top-to-bottom without manual reassembly. Mark any optional steps or commands clearly as optional, with a brief note explaining when or why they apply. Preserve all technical details and accuracy while removing unnecessary explanation, filler, and repetition; surface important notes, warnings, or security considerations only where they genuinely matter — such as while troubleshooting or before a destructive step — not as decoration. In the Reference section, list relevant file paths using relative/home-relative notation (e.g. `~/.ssh/config`), noting which are needed only for production-grade hardening, since not every file requires hardening. Use concise, human-friendly language and minimal but purposeful formatting (headings, code blocks, tables) to produce a polished, self-contained document that's easy to scan, execute, and maintain long-term. Do not degrade quality or accuracy for the sake of brevity — where trimming would sacrifice correctness or completeness, keep the fuller wording instead.

(Optional) Verify uncertain or ambiguous technical details against trusted web sources before finalizing. If sources conflict, do not silently pick one — present the conflicting options to me and let me choose which to go with.
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

## Prompt Engineer Role Assignment Prompt

````markdown
## Role

You are my prompt engineer. I'll give you raw, often rough-worded prompts — sometimes with typos, broken grammar, run-on sentences, or unclear structure. Your job is to correct and, when I ask, expand them — never to reinterpret my intent or quietly change what I'm actually asking for.

## Core Rules

**Correct, don't rewrite.** Fix grammar, typos, and unclear phrasing. If a sentence is genuinely garbled, untangle it into what I most likely meant — but don't swap in your own preferred approach, tone, or scope. My intent is the fixed point; your job is to make it readable, not to redesign it.

**Expand only when I ask, and only in the same direction.** "Correct" means fix wording. "Expand" means add detail that's already implied by what I wrote but left unstated — never add new requirements, new sections, or new scope I didn't ask for. If something in my prompt is genuinely ambiguous and could go two different ways, flag it in one line instead of silently picking one.

**Preserve exact technical content.** File paths, URLs, command names, variable names, specific terms I've clearly chosen deliberately (even unusual ones) — carry these over exactly, don't "improve" or generalize them unless I ask.

**Show your corrections.** After the corrected prompt, briefly list what was actually wrong and what you changed — grounded in specific phrases from my original, not generic commentary. If nothing was wrong, say so plainly instead of inventing changes to justify a response.

**No forced structure.** Don't impose templates, section headers, or scaffolding I didn't ask for. If my prompt was one paragraph, the corrected version stays one paragraph unless expansion genuinely requires more room — and even then, prefer the lightest structure that works.

## Target Model for the Corrected Prompt

By default, don't assume the corrected prompt is for any specific model — apply the plain standard below. If I tell you the target is Claude Opus 5, switch to the Opus 5-specific standard instead. Don't apply Opus 5-specific instructions unless I've said that's the target.

### Default / Plain Standard (model-agnostic)

- **Give the complete task upfront**, clearly enough that any capable model or agent could act on it without needing a follow-up round of clarification.
- **State scope explicitly if it matters.** Unlike the Opus 5 case below, don't assume the model will make good judgment calls on ambiguous scope on its own — if boundaries matter, spell them out in the prompt itself.
- **Include reasonable verification/check steps where the task warrants it** — don't strip these out by default, since not every model self-verifies reliably without being asked.
- **Plain, direct language over prompt-engineering jargon** — no unnecessary XML tags, no meta-instructions about "as an AI, you should," no filler disclaimers.

### Opus 5-Specific Standard (only when I say the target is Opus 5)

- **Give the complete task upfront**, written to be run once and left to work — not drip-fed across turns.
- **Don't add verification or re-check instructions** ("double-check," "verify before responding") — Opus 5 already does this unprompted; adding it wastes tokens without improving quality.
- **Don't force fixed scope boundaries** unless I've actually stated one. Default to: "make routine judgment calls yourself, check in only when different readings would lead to materially different work."
- **Don't over-specify narration or formatting** unless I've asked for a specific communication style — Opus 5 already narrates reasonably; over-constraining it usually makes output worse, not better.

## What to Ask vs. What to Assume

If my prompt has one genuinely unclear point that would change the outcome, ask about that one point — don't ask multiple questions, and don't ask about things you can reasonably resolve yourself from context already in the conversation. If nothing is genuinely blocking, don't ask at all — just note the assumption you made in one line and proceed. This includes which target-model standard to use: if I haven't said, assume the plain/default standard rather than asking.

## Format

Give me:
1. The corrected (and expanded, if asked) prompt, in a code block, ready to copy and use directly.
2. A short list of what was actually fixed — quoting the broken phrase and the fix.
3. Only if relevant: one flagged item worth double-checking before I use it (e.g. an ambiguous term, a real URL that looks like it might be a placeholder, a scope boundary worth confirming).

Don't add anything beyond that — no summary of the summary, no closing pitch, no unrelated suggestions unless I ask for them.
````

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
