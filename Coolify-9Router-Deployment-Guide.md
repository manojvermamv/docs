# 9Router Coolify Deployment

## Overview

9Router (self-hosted AI provider router/proxy, `decolua/9router`) deployed
behind Coolify/Traefik on the same host as the existing OpenCode deployment,
as a fully independent stack. Unlike OpenCode, 9Router needs no host
filesystem, process, or network access — it's a standard containerized web
service, deployed with none of the `nsenter`/`network_mode: host`/capability
mechanisms used elsewhere on this host.

## Docker Compose
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
    #
    # Deliberately using `expose:` (below), NOT `ports:` like the
    # official compose example. `ports:` publishes directly to the
    # host, which tells Coolify this service is already self-exposed
    # and it will NOT generate a Traefik/domain routing box for it -
    # confirmed behavior from this same troubleshooting earlier in
    # this deployment. `expose:` + SERVICE_FQDN below is the correct
    # Coolify-specific adaptation of the official example, not an
    # oversight.
    environment:
      - SERVICE_FQDN_9ROUTER_20128
      # If Coolify's generated FQDN value doesn't include the
      # https:// scheme, change these two lines to:
      #   - BASE_URL=https://${SERVICE_FQDN_9ROUTER_20128}
      #   - NEXT_PUBLIC_BASE_URL=https://${SERVICE_FQDN_9ROUTER_20128}
      # Check the Environment Variables tab after first deploy to
      # see the actual populated value before assuming either form.
      - 'BASE_URL=${SERVICE_FQDN_9ROUTER_20128}'
      - 'NEXT_PUBLIC_BASE_URL=${SERVICE_FQDN_9ROUTER_20128}'

      - DATA_DIR=/app/data
      - PORT=20128
      - HOSTNAME=0.0.0.0
      - NODE_ENV=production

      # ── Headroom sidecar (token-reduction) - confirmed from the ──
      # ── official docker-compose.yml, not in the README's own   ──
      # ── env var table                                          ──
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
        # NOTE: /api/health is NOT confirmed against the official
        # README or docker-compose.yml - neither documents a health
        # endpoint. If this 404s/fails after deploy, fall back to
        # the root path ('/', the dashboard) instead, which IS
        # confirmed reachable.
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
    # publishes 8787 to the host; deliberately not done here -
    # nothing outside this stack needs to talk to it, so no
    # expose/ports entry means one less thing exposed on a
    # public-facing host.
    restart: unless-stopped

volumes:
  9router-data:
```

## Key Points

- **Official image**: `decolua/9router:latest` (Docker Hub) /
  `ghcr.io/decolua/9router` (GHCR), multi-platform.
- **Container defaults**: `PORT=20128`, `HOSTNAME=0.0.0.0`, dashboard at
  `/`, OpenAI-compatible API at `/v1`.
- **Required sidecar**: `ghcr.io/chopratejas/headroom:latest` — confirmed
  from the official `docker-compose.yml` (not documented in the README's
  own env-var table). 9Router depends on it via `HEADROOM_URL=http://headroom:8787`
  and `depends_on`.
- **Data persistence**: single named volume (`9router-data:/app/data`)
  covers all state, including the SQLite DB.
- **Security defaults in the official examples are for localhost-only use.**
  Two settings the README marks optional become mandatory for a public
  deploy:
  - `INITIAL_PASSWORD` — defaults to `123456` if unset.
  - `REQUIRE_API_KEY` — defaults to `false`; README explicitly recommends
    `true` for internet-exposed deployments, otherwise `/v1/*` is open to
    anyone who finds the subdomain.

## Decisions Made

| Decision | Rationale |
|---|---|
| Use `expose: ['20128']`, not `ports: ['20128:20128']` (which the official compose uses) | `ports:` publishes directly to the host, which causes Coolify to treat the service as already self-exposed and skip generating a Traefik/domain routing box — a behavior confirmed earlier in this deployment (same issue hit with OpenCode). `expose:` + `SERVICE_FQDN_9ROUTER_20128` is the correct Coolify-specific adaptation. |
| Keep explicit `environment:` entries instead of the official's `env_file: .env` | `env_file` assumes a checked-in `.env` in the build context; doesn't fit Coolify's "paste compose, set variables via UI" model. Explicit `${VAR}` substitution, set through Coolify's Environment Variables tab, is the correct adaptation — same pattern already used for OpenCode. |
| Include the Headroom sidecar, unexposed (no `ports`/`expose`) | Confirmed required by the official compose (`depends_on`, `HEADROOM_URL`). Not exposed to the host since nothing outside the stack needs to reach it — reachable internally via Docker Compose's automatic per-project service-name DNS (`http://headroom:8787`), no extra network config needed. |
| Set `AUTH_COOKIE_SECURE=true` | README: "set true behind HTTPS reverse proxy" — exactly Coolify/Traefik's role here. |
| Set `REQUIRE_API_KEY=true` | README's own recommendation for internet-exposed deploys; without it, the API is open to anyone who finds the subdomain. |
| `restart: unless-stopped` on both services, not the official's `restart: always` | Matches the convention used elsewhere in this deployment; respects a manual stop through Coolify's UI rather than fighting it after a daemon restart. |
| Healthcheck via `node -e require('http')...`, not `curl`/`wget` | Neither README nor official compose documents the base image's shell/tooling. Node.js is guaranteed present (it's the app's own runtime) regardless of Alpine vs. Debian base — more portable than assuming a specific shell utility exists. |

## Open Questions

- **`/api/health` healthcheck path is unconfirmed.** Neither the README nor
  the official `docker-compose.yml` documents a health endpoint. The
  current healthcheck targets `/api/health` — verify this returns a
  non-5xx response after deploy; if it 404s, fall back to the root path
  (`/`, the dashboard), which is confirmed reachable.
- **`SERVICE_FQDN_9ROUTER_20128`'s exact resolved format (with or without
  `https://` scheme) is unconfirmed** — check the Environment Variables tab
  after first deploy before trusting `BASE_URL`/`NEXT_PUBLIC_BASE_URL` as
  currently written; adjust to prepend `https://` if the raw value is a
  bare hostname.
- **Whether `BASE_URL`/`NEXT_PUBLIC_BASE_URL` correctness affects OAuth
  provider callbacks specifically** (Claude Code, Codex, GitHub, Cursor
  connections) was not confirmed either way in the README — worth testing
  after deploy rather than assuming either outcome.
- **Traefik's default 60s `readTimeout`** may affect 9Router's streamed
  (SSE) responses the same way it did for OpenCode earlier in this
  deployment. Not yet confirmed as an actual problem for 9Router
  specifically — flagged proactively based on the shared streaming
  architecture, not from observed failure.

## Next Steps

1. Deploy the compose file via Coolify's "Edit Compose File."
2. Set real values (not placeholders) for `JWT_SECRET`, `INITIAL_PASSWORD`,
   `API_KEY_SECRET`, `MACHINE_ID_SALT` in Coolify's Environment Variables
   tab before first deploy.
3. After deploy, check the actual resolved value of
   `SERVICE_FQDN_9ROUTER_20128` and adjust `BASE_URL`/`NEXT_PUBLIC_BASE_URL`
   if it lacks the `https://` scheme.
4. Confirm the `/api/health` healthcheck path actually works; revert to
   `/` if not.
5. Log into the dashboard with `INITIAL_PASSWORD`, connect a provider, and
   generate a 9Router API key (now required on every `/v1/*` call due to
   `REQUIRE_API_KEY=true`).
6. If prompts/responses hang around the ~60s mark, apply the same Traefik
   `respondingTimeouts` fix used for OpenCode (Coolify server-level Proxy
   settings, not a compose change).
