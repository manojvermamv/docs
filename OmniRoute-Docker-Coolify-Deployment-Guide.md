# Deploying OmniRoute (Chromium/Playwright Build) on Coolify

## Overview

This guide consolidates a full troubleshooting session into a single deployment
reference. The goal: run **OmniRoute** (an open-source AI/LLM gateway,
`diegosouzapw/OmniRoute`) as a production service on **Coolify**, with the
Chromium/Playwright-enabled build (required for web-cookie providers such as
`gemini-web`, `claude-web`, and `claude-turnstile`).

The source repository ships two Compose files:

| File | Purpose | Coolify-friendly? |
|---|---|---|
| `docker-compose.yml` | Multi-profile file (`base`, `web`, `cli`, `host`, `cliproxyapi`, `memory`, `bifrost`) — nothing runs without an explicit `--profile` flag | No — Coolify has no simple way to pass `--profile`; would need a `COMPOSE_PROFILES` env var workaround |
| `docker-compose.prod.yml` | Self-contained "production snapshot" (app + Redis, fixed ports) | Yes — chosen as the base for this deployment |

`docker-compose.prod.yml` was progressively modified across several failed
deploy attempts. **The version at the end of this document is the current,
authoritative one** — it supersedes every intermediate version shown during
the session (including versions that used `build:` to compile from source).

**Key finding:** This Compose file is deployed in Coolify as a **Service**
(a pasted/raw Compose resource), not as a Git-linked **Application**. Coolify
Services never clone a repository — they only run the Compose file as
written. This ruled out `build: context: .` entirely (there is no Dockerfile
on disk to build from) and is why the final version pulls a **pre-built,
published Docker image** instead of building.

**Version caveat:** `v3.8.50` (the release originally requested) is **not
yet published as a Docker Hub image tag**. The newest published tags are
`3.8.49` and `3.8.49-web` — currently identical to what `latest`/`latest-web`
point to. The final config below pins `3.8.49-web` as the closest available
match.

---

## What You'll Need

- A running Coolify instance with a server attached.
- Outbound access to Docker Hub (the images used are public; no `docker
  login` required).
- The service deployed as a Coolify **Service** resource (see note above —
  not a Git-linked Application).
- A `.env` file for the service. The Compose file references `env_file: .env`,
  and Compose requires that file to exist on disk (even if empty) — Coolify
  normally manages this automatically via its **Environment Variables** tab.
- A domain/subdomain you want Coolify to route to the OmniRoute dashboard.
- **Gap/assumption flagged:** beyond the variables with inline defaults shown
  below, no additional required secrets (e.g., auth/session keys) were
  confirmed for this specific Compose file during the session. A separate
  reference file (for a different, similarly-named project) used vars like
  `JWT_SECRET`, `INITIAL_PASSWORD`, `API_KEY_SECRET` — those were **not**
  verified as required by this OmniRoute build and are intentionally omitted
  below. Confirm against the project's own `.env.example` before going live.

---

## Step-by-Step Instructions

1. **Create the Service in Coolify.**
   In your Coolify project, add a new **Service** resource and paste in the
   final Compose file (reproduced in full at the end of this guide).

2. **Ensure a `.env` file exists for the service.**
   Even with no custom values, Coolify needs something on disk for the
   `env_file: .env` reference to resolve. Add any project-specific overrides
   here (e.g., a non-default `PORT` or `OMNIROUTE_BASE_PATH`) if needed.

3. **Assign a public domain via the `SERVICE_FQDN` variable.**
   In Coolify's environment/domain settings for this service, assign your
   domain to `SERVICE_FQDN_OMNIROUTE_20128`. This is the port the dashboard
   listens on, and Coolify's built-in proxy uses this variable to route
   traffic to the container — no host port publishing is used.
   - Leave `SERVICE_FQDN_OMNIROUTE_20129` (API) and `SERVICE_FQDN_OMNIROUTE_20132`
     (WebSocket) **unset** unless you specifically need those reachable on
     their own public subdomains.

4. **Deploy the service.**
   Trigger a deploy from the Coolify UI.

5. **Watch the deploy log for these expected phases, in order:**
   - `Saved configuration files to /data/coolify/services/<service-id>`
   - Redis (`redis:8.6.2-alpine`) pulling and completing.
   - `omniroute-prod` (`diegosouzapw/omniroute:3.8.49-web`) pulling and
     completing — with the final image-based config, this **will** pull (it
     is no longer skipped, unlike the intermediate build-only version tested
     mid-session).
   - Docker network creation.
   - Service start, healthchecks passing.

6. **Verify the dashboard loads** at the domain assigned in Step 3.

---

## Expected Outcome

- Both containers (`omniroute-redis-prod`, `omniroute-prod`) running and
  healthy, with no host ports published — all traffic reaching the app via
  Coolify's proxy and the assigned domain.
- The Playwright/Chromium-enabled build is active, so web-cookie providers
  (`gemini-web`, `claude-web`, `claude-turnstile`) should function without
  the "Executable doesn't exist at .../ms-playwright/chromium..." error seen
  with the lean/base image.

> **Not yet confirmed:** at the time this document was produced, the final
> image-based version had **not** been redeployed and verified successful
> end-to-end in the session. Treat the outcome above as expected-per-config,
> not as a confirmed result.

---

## Common Pitfalls (each one actually encountered this session)

| # | Symptom in deploy log | Root cause | Fix applied |
|---|---|---|---|
| 1 | N/A (design-time) | `docker-compose.yml`'s profile system requires `--profile` flags Coolify doesn't pass by default | Use `docker-compose.prod.yml` instead |
| 2 | N/A (design-time) | `ports:` host-binding conflicts with Coolify's own reverse-proxy model | Replace with `expose:` + `SERVICE_FQDN_<NAME>_<PORT>` |
| 3 | `non-string key in services.omniroute-prod.environment: 0` | Known Coolify bug — defining both `build.args` **and** `environment` on the same service causes Coolify's internal file rewrite to inject a numeric key alongside string keys ([coollabsio/coolify#5555](https://github.com/coollabsio/coolify/issues/5555) and related issues) | Don't duplicate the same variable in `build.args` and `environment`; removed the `args:` block |
| 4 | `pull access denied for omniroute, repository does not exist...` + `WARNING: Some service image(s) must be built from source` | Defining both `build:` and a custom `image:` name that was never published — Compose's `pull` phase tries (and fails) to fetch it from Docker Hub before falling through to build, and Coolify treats that failure as fatal ([docker/compose#8805](https://github.com/docker/compose/issues/8805), [#10123](https://github.com/docker/compose/issues/10123)) | Removed the custom `image:` name from the build-based service |
| 5 | `failed to solve: failed to read dockerfile: open Dockerfile: no such file or directory` | `build: context: .` used inside a Coolify **Service** (pasted Compose, not Git-linked) — no source code exists in that context | Switched from `build:` to a published pre-built image (`diegosouzapw/omniroute:3.8.49-web`) |

**If you specifically need the unreleased `v3.8.50` source** (not just the
published `3.8.49` image): redeploy as a Coolify **Application** (not a
Service) using build pack "Docker Compose," pointing at the Git repository
`https://github.com/diegosouzapw/OmniRoute` on branch `release/v3.8.50`.
This makes Coolify actually clone the repo (including its Dockerfile) into
the build context, so `build:` would work. **This path was discussed but not
tested in this session.**

---

## Final Compose File (authoritative) — `docker-compose.prod.yml`

This is the exact, byte-for-byte content of the latest `docker-compose.prod.yml`
produced in this session — the version that follows the Step-by-Step
Instructions above and resolves every pitfall in the table.

```yaml
# ──────────────────────────────────────────────────────────────────────
# OmniRoute — Docker Compose (Production Snapshot, Web/Chromium flavor)
# Coolify Service: pulls a published image (no local build), no host
# port publishing — Coolify's proxy routes traffic via SERVICE_FQDN_*
# (set the domain in the Coolify UI).
# ──────────────────────────────────────────────────────────────────────

services:
  # ── Redis (Rate Limiter Backend) ──────────────────────────────────
  redis:
    image: redis:8.6.2-alpine
    container_name: omniroute-redis-prod
    restart: unless-stopped
    volumes:
      - redis-prod-data:/data
    command: redis-server --save 60 1 --loglevel warning
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  omniroute-prod:
    container_name: omniroute-prod
    # Pinned to the newest published web/Chromium build (3.8.49-web).
    # v3.8.50 is not yet published as a Docker image tag — swap to
    # "latest-web" to auto-track whatever the maintainer publishes next.
    image: diegosouzapw/omniroute:3.8.49-web
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    stop_grace_period: 40s
    env_file: .env
    environment:
      - SERVICE_FQDN_OMNIROUTE_20128
      - SERVICE_FQDN_OMNIROUTE_20129
      - SERVICE_FQDN_OMNIROUTE_20132
      - NODE_ENV=production
      - PORT=${PORT:-20128}
      - DASHBOARD_PORT=${DASHBOARD_PORT:-${PORT:-20128}}
      - API_PORT=${API_PORT:-20129}
      - LIVE_WS_PORT=${LIVE_WS_PORT:-20132}
      - LIVE_WS_HOST=${LIVE_WS_HOST:-0.0.0.0}
      - LIVE_WS_ALLOWED_ORIGINS=${LIVE_WS_ALLOWED_ORIGINS:-${SERVICE_FQDN_OMNIROUTE_20128}}
      - API_HOST=${API_HOST:-0.0.0.0}
      - HOSTNAME=0.0.0.0
      - DATA_DIR=/app/data
      - OMNIROUTE_BASE_PATH=${OMNIROUTE_BASE_PATH:-}
    expose:
      - '20128'
      - '20129'
      - '20132'
    volumes:
      - omniroute-prod-data:/app/data
    healthcheck:
      test: ["CMD", "node", "healthcheck.mjs"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s

volumes:
  omniroute-prod-data:
    name: omniroute-prod-data
  redis-prod-data:
    name: redis-prod-data
```

---

## Open Items / Assumptions Flagged

- **End-to-end deploy success is unverified.** The image-based final version
  was produced in response to the last error in the log, but a subsequent
  successful deploy was not confirmed in this session.
- **Deployment type inferred, not stated.** That this is a Coolify *Service*
  (vs. *Application*) was inferred from the `/data/coolify/services/<id>/`
  path visible in the deploy logs, not explicitly confirmed by the user.
- **Required secrets not fully enumerated.** No `.env.example` or full list
  of required runtime secrets for this specific Compose file was reviewed in
  this session — only the variables with inline defaults shown above are
  confirmed.
- **Nested variable interpolation untested.** `LIVE_WS_ALLOWED_ORIGINS`
  uses `${VAR:-${OTHER_VAR}}` syntax (a default value that itself references
  another variable). This was never validated against Coolify's Compose
  parser in this session — if it errors, replace it with a flat literal
  default or a single-level `${VAR:-default}` expression.
- **`3.8.49-web` vs `latest-web`:** pinned to `3.8.49-web` for reproducibility
  per the project's own stated convention ("`:latest` follows highest
  published stable SemVer... pin `:X.Y.Z` for GitOps"). Switch to `latest-web`
  if you'd rather auto-track new releases.
