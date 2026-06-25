# 🚀 OpenCode Remote Server + Coolify + Shared Sessions (Windows/Linux/Desktop)

> **Goal:** Use a single OpenCode server running on a Linux VPS so multiple OpenCode Desktop clients (Windows, Linux, etc.) can access the **same sessions**, **same configuration**, and **same projects** without manual export/import.

***

# 📐 Final Architecture

```
┌─────────────────────┐
│ Windows Desktop     │
│ OpenCode Desktop    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ OpenCode Server     │
│ Coolify + Docker    │
│ VPS/Linux           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Persistent Volumes  │
│ Sessions            │
│ Config              │
└─────────────────────┘

           ▲
           │
┌─────────────────────┐
│ Linux Desktop       │
│ OpenCode Desktop    │
└─────────────────────┘
```

All OpenCode Desktop clients connect to the same server.

Result:

✅ Shared sessions

✅ Shared chat history

✅ Shared configuration

✅ Shared project access

✅ No export/import workflow

***

# 📦 Final Docker Compose Configuration

This is the final working configuration.

```YAML
services:
  opencode:
    image: 'ghcr.io/anomalyco/opencode:latest'
    working_dir: /workspace
    command: 'serve --hostname 0.0.0.0 --port 4096'
    environment:
      - 'OPENCODE_SERVER_USERNAME=${OPENCODE_SERVER_USERNAME}'
      - 'OPENCODE_SERVER_PASSWORD=${OPENCODE_SERVER_PASSWORD}'
      - 'OPENROUTER_API_KEY=${OPENROUTER_API_KEY}'
      - 'OPENAI_API_KEY=${OPENAI_API_KEY}'
      - 'ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}'
      - 'GOOGLE_API_KEY=${GOOGLE_API_KEY}'
      - 'XAI_API_KEY=${XAI_API_KEY}'
      - 'GROQ_API_KEY=${GROQ_API_KEY}'
    volumes:
      - 'opencode-data:/home/opencode/.local/share/opencode'
      - 'opencode-config:/home/opencode/.config/opencode'
      - 'opencode-cache:/home/opencode/.cache'
      - '/home/ubuntu:/workspace'
    healthcheck:
      test:
        - CMD
        - wget
        - '--spider'
        - '-q'
        - 'http://127.0.0.1:4096/doc'
      interval: 30s
      timeout: 5s
      retries: 3
```

***

# 🧠 Why This Configuration Works

## 1. Persistent Sessions

```YAML
- opencode-data:/home/opencode/.local/share/opencode
```

Stores:

- Sessions
- State
- Local OpenCode data

Persistent across:

```Bash
docker compose down
docker compose up -d
```

***

## 2. Persistent Configuration

```YAML
- opencode-config:/home/opencode/.config/opencode
```

Stores:

- Config
- Providers
- Settings

Persistent across container recreation.

***

## 3. Shared Project Access

```YAML
- /home/ubuntu:/workspace
```

Makes the server filesystem available inside OpenCode.

Example:

```
Host
/home/ubuntu/openalgo

Container
/workspace/openalgo
```

***

# 🔍 Verification

Verify mount exists:

```Bash
docker exec -it opencode-b2ypzoogabqgmdak2zhes95b sh
```

```Bash
ls /workspace
```

Example:

```
ai-stack
openalgo
```

Verify project:

```Bash
ls /workspace/openalgo
```

Expected:

```
.git
README.md
app.py
...
```

***

# 📂 Why OpenCode Initially Didn't Show Projects

Initially:

```Bash
docker inspect ... | jq '.[0].Config.WorkingDir'
```

returned:

```
"/"
```

OpenCode Desktop only showed:

```
~
.cache
.config
.local
.npm
```

because the server started from root.

***

# ✅ Fix

Added:

```YAML
working_dir: /workspace
```

Now OpenCode Desktop can browse:

```
/workspace/openalgo
/workspace/ai-stack
```

and other mounted projects.

***

# 🖥️ OpenCode Desktop Workflow

## Connect To Remote Server

Server:

```
https://opencode.karm8boost.online
```

Login:

```
OPENCODE_SERVER_USERNAME
OPENCODE_SERVER_PASSWORD
```

***

## Open Project

Search:

```
/workspace
```

Now visible:

```
/workspace/openalgo
/workspace/ai-stack
...
```

Select desired project.

***

# 🌍 Multi-System Workflow

## Machine 1

```
Windows Desktop
```

Connects to:

```
https://opencode.karm8boost.online
```

Continue session.

***

## Machine 2

```
Linux Desktop
```

Connects to:

```
https://opencode.karm8boost.online
```

Same session appears.

***

## Machine 3

```
Laptop
```

Connects to:

```
https://opencode.karm8boost.online
```

Continue where previous machine stopped.

***

# 📁 Important Filesystem Concept

OpenCode Server can only access files that exist on the server.

Example:

### Accessible

```
/workspace/openalgo
```

because:

```
Server:
/home/ubuntu/openalgo
```

exists.

***

### Not Accessible

```
C:\Projects\openalgo
```

because that path only exists on your Windows PC.

***

# 🔄 Recommended Development Workflow

## Option A (Recommended)

Keep repositories on server.

```
/home/ubuntu/openalgo
/home/ubuntu/ai-stack
```

Use OpenCode remotely.

Benefits:

✅ Single source of truth

✅ Same project everywhere

✅ No syncing needed

***

## Option B

Work locally and push to Git.

```Bash
git push
```

Server:

```Bash
git pull
```

Then open:

```
/workspace/openalgo
```

inside OpenCode.

***

# 💾 Persistence Testing

Verify volumes:

```Bash
docker volume ls | grep opencode
```

Example:

```
b2ypzoogabqgmdak2zhes95b_opencode-data
b2ypzoogabqgmdak2zhes95b_opencode-config
```

Inspect:

```Bash
docker volume inspect b2ypzoogabqgmdak2zhes95b_opencode-data
```

Expected:

```
/var/lib/docker/volumes/.../_data
```

***

# 🩺 Health Check

Image does not contain curl.

Failed approach:

```Bash
curl http://127.0.0.1:4096/doc
```

Inside container:

```
curl: not found
```

***

## Correct Health Check

```YAML
healthcheck:
  test:
    - CMD
    - wget
    - '--spider'
    - '-q'
    - 'http://127.0.0.1:4096/doc'
```

Because:

```Bash
which wget
```

returns:

```
/usr/bin/wget
```

***

# 🔐 SSL / Coolify Notes

Current issue observed:

```Bash
curl -I https://opencode.karm8boost.online
```

returns:

```
SSL certificate problem: self-signed certificate
```

and Coolify proxy logs contain ACME errors:

```
Unable to get token
Cannot retrieve the ACME challenge
missing token
```

This indicates a Coolify/Traefik certificate issuance problem rather than an OpenCode issue.

***

## Current Public Endpoint

```
https://opencode.karm8boost.online
```

If using direct service exposure, configure the service according to the port exposed by OpenCode:

```
4096
```

and ensure Coolify/Traefik routing and Let's Encrypt are functioning correctly.

***

# 🛠 Troubleshooting

## Project Not Visible

Verify:

```Bash
docker exec -it <container> pwd
```

Expected:

```
/workspace
```

***

## Project Exists?

```Bash
ls /workspace/openalgo
```

***

## Volume Mounted?

```Bash
docker inspect <container>
```

Check mounts.

***

## Session Lost After Restart?

Check:

```Bash
docker volume ls
```

and verify:

```
opencode-data
opencode-config
```

still exist.

***

## OpenCode Shows Only

```
~
.cache
.config
.local
.npm
```

Check:

```YAML
working_dir: /workspace
```

and redeploy.

***

# ✅ Final Result

You now have:

- OpenCode Server running in Docker
- Managed by Coolify
- Persistent sessions
- Persistent configuration
- Shared projects
- Multi-device access
- No export/import workflow
- Single central OpenCode environment

Use any OpenCode Desktop client, connect to the same server, open `/workspace/<project>`, and continue exactly where you left off.
