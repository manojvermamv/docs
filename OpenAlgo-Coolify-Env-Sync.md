# Coolify Deployment: OpenAlgo `.env` Sync Guide

## Overview

This document describes the correct workflow for syncing OpenAlgo environment files during Coolify deployment and fixing the `.env` directory issue.

When Coolify processes Docker resources from a GitHub repo using Docker Compose, it may accidentally create a directory named `.env` instead of a file. That breaks the OpenAlgo build and startup.

## Fix: Remove stray `.env` directory

If the Coolify application path contains an empty directory named `.env`, delete it before deployment or restart:

```bash
rm -rf /data/coolify/applications/a97ioq7zyseuomyd4837x2a2/.env
```

This ensures Coolify can create or use the proper `.env` file instead of a directory.

## Correct Coolify env file naming

Use these two files in your workflow:

- ` .env.openalgo` — official OpenAlgo environment template
- ` .env.coolify` — Coolify deployment environment file

The final production file should be named ` .env.coolify` and follow the official OpenAlgo structure while preserving Coolify production values.

## Exact merge prompt for AI models

Use this prompt with any AI model or agent:

```text
You have two files:
1. official OpenAlgo env template `.env.openalgo`
2. deployed Coolify env `.env.coolify`

Task:
- Merge `.env.openalgo` and `.env.coolify` into one final `.env.coolify` that follows the official OpenAlgo format while preserving Coolify production-specific values.
- Use `.env.openalgo` as the source of truth for variable names, structure, and comments.
- Use `.env.coolify` as the source of truth for current production values and domain-specific overrides.

Rules:
1. Keep `FLASK_DEBUG` and `FLASK_ENV` from the current `.env.coolify` by default, and keep them marked with a clear comment that they are intentionally left in development mode.
2. Preserve production domain values for:
   - `SERVICE_URL_OPENALGO`
   - `SERVICE_FQDN_OPENALGO`
   - `HOST_SERVER`
   - `REDIRECT_URL`
   - `WEBSOCKET_HOST`
   - `WEBSOCKET_PORT`
   - `WEBSOCKET_URL`
   - `CORS_ALLOWED_ORIGINS`
   - all `CSP_*` entries
3. Remove any duplicate or stale CSP rules. Keep only one CSP definition block.
4. Keep placeholder secrets as-is if present, but do not invent new secret values.
5. Do not drop official comments from `.env.openalgo`. Preserve them where possible.
6. Normalize boolean and string values to the official env style, but retain production intent.
7. Output only the final `.env.coolify` file contents, with comments, and no extra explanation.

Goal:
Produce a single consistent Coolify-ready `.env.coolify` file that is aligned with official OpenAlgo defaults plus current production overrides, while preserving intentional dev-mode FLASK settings with comments.
```

## Variables to preserve for production

Always preserve the production values from ` .env.coolify` for these keys:

- `SERVICE_URL_OPENALGO`
- `SERVICE_FQDN_OPENALGO`
- `HOST_SERVER`
- `REDIRECT_URL`
- `WEBSOCKET_HOST`
- `WEBSOCKET_PORT`
- `WEBSOCKET_URL`
- `CORS_ALLOWED_ORIGINS`
- `CSP_DEFAULT_SRC`
- `CSP_SCRIPT_SRC`
- `CSP_STYLE_SRC`
- `CSP_IMG_SRC`
- `CSP_CONNECT_SRC`
- `CSP_FONT_SRC`
- `CSP_MEDIA_SRC`
- `CSP_FRAME_SRC`
- `CSP_FORM_ACTION`
- `CSP_FRAME_ANCESTORS`
- `CSP_BASE_URI`
- `CSP_UPGRADE_INSECURE_REQUESTS`
- `CSP_REPORT_URI`

## Production validation

Make sure `.env.coolify` contains a valid websocket URL for production. If the site is served over HTTPS and websockets connect on port `8765`, use:

```env
WEBSOCKET_URL=wss://oa.karm8boost.online:8765
```

If you proxy websocket traffic through port `443`, use:

```env
WEBSOCKET_URL=wss://oa.karm8boost.online
```

## Verification commands

Use these commands to verify the Docker and Coolify environment before retrying a build:

```bash
# Check Docker daemon disk space usage
docker system df

# Check filesystem disk space on Coolify storage
df -h /data/coolify

# Check whether BuildKit cache inspection is available
docker buildx du 2>/dev/null || echo "BuildKit cache not available"

# Clean Docker build cache and retry
docker buildx prune --all --force

# List OpenAlgo-related Docker images
docker images | grep openalgo
```

## Notes

- Keep `FLASK_DEBUG` and `FLASK_ENV` only if you are intentionally running in development mode.
- Do not use a directory named `.env`; Coolify expects a file named `.env`.
- If `.env` is missing or invalid, Coolify may still report build success while the application fails at runtime.

## My Raw Doc

Now i got correct flow for openalgo setup & fixes while deployment in Coolify..

When we create new Project & add resource from github repo With docker compose, 
Than Resource added succesfully, But while coolify proccess the docker resources (Issue: Created a directory (named `.env`) instead of `.env`  file at path `/data/coolify/applications/a97ioq7zyseuomyd4837x2a2`), This crashed the openalgo after build success.

FIX:
So we need to delete empty `.env` dir from `/data/coolify/applications/a97ioq7zyseuomyd4837x2a2` if persent

### Correct Coolify ENV Vairiables:
```
You have two files:
1. official OpenAlgo env template `.env.openalgo`
2. deployed Coolify env `.env.coolify`

Task:
- Merge `.env.openalgo` and `.env.coolify` into one final `.env.coolify` that follows the official OpenAlgo format while preserving Coolify production-specific values.
- Use `.env.openalgo` as the source of truth for variable names, structure, and comments.
- Use `.env.coolify` as the source of truth for current production values and domain-specific overrides.

Rules:
1. Keep `FLASK_DEBUG` and `FLASK_ENV` from the current `.env.coolify` by default, and keep them marked with a clear comment that they are intentionally left in development mode.
2. Preserve production domain values for:
   - `SERVICE_URL_OPENALGO`
   - `SERVICE_FQDN_OPENALGO`
   - `HOST_SERVER`
   - `REDIRECT_URL`
   - `WEBSOCKET_HOST`
   - `WEBSOCKET_PORT`
   - `WEBSOCKET_URL`
   - `CORS_ALLOWED_ORIGINS`
   - all `CSP_*` entries
3. Remove any duplicate or stale CSP rules. Keep only one CSP definition block.
4. Keep placeholder secrets as-is if present, but do not invent new secret values.
5. Do not drop official comments from `.env.openalgo`. Preserve them where possible.
6. Normalize boolean and string values to the official env style, but retain production intent.
7. Output only the final `.env.coolify` file contents, with comments, and no extra explanation.

Goal:
Produce a single consistent Coolify-ready `.env.coolify` file that is aligned with official OpenAlgo defaults plus current production overrides, while preserving intentional dev-mode FLASK settings with comments.
```

### FINAL EXTRA COMMANDS: 
```
# Check Docker daemon disk space
docker system df

# Check system disk space
df -h /data/coolify

# Check if build was actually attempted
docker buildx du 2>/dev/null || echo "BuildKit cache not available"

# Clean build cache and retry
docker buildx prune --all --force

# Docker / Linux-based deployment: ensure `.env` file ownership and permissions
docker system df
cd /data/coolify/applications/a97ioq7zyseuomyd4837x2a2/
sudo chown 1000:1000 .env
sudo chmod 600 .env

# If you are using a mounted folder in Docker, ensure the mount is not read-only.
# XYZ
docker images | grep openalgo
```
