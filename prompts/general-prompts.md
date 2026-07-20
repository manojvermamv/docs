# General Use Prompts

## OpenAlgo Source-Grounded Cross-Check Loop
```text
Now start a new finding loop (cross-check every trace locally against the real-world OpenAlgo setup: the latest OpenAlgo infra from the GitHub-cloned (Offical Repo: https://github.com/marketcalls/openalgo) local repo at `/home/ubuntu/openalgo/` and the Python SDK — used together in combination; the Python SDK's source code calls into OpenAlgo infra via `{openalgo-infra-repo}/restx_api/`, or if validation fails within that directory alone, expand the search to `{openalgo-infra-repo}/...`; load both the infra and SDK source from GitHub into session memory and ground all findings in their source code as evidence — do not trust SDK or OpenAlgo infra internal code/function docstrings alone — then assess effects and patches strictly according to those sources) — starting from a clean slate.
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
