# 🚀 Infrastructure Handbook

> **Unified reference for servers, domains, Docker, OpenAlgo, Hermes, and Coolify**
> Maintained at `/host/home/ubuntu/INFRASTRUCTURE-HANDBOOK.md` — persistent on host, outside Docker.

---

## Table of Contents

1. [SSH Access & PEM Keys](#1-ssh-access--pem-keys)
2. [Shortcut Links](#2-shortcut-links)
3. [AWS / EC2 Instances](#3-aws--ec2-instances)
4. [EC2 Security & CIDR](#4-ec2-security--cidr)
5. [OpenClaw Setup](#5-openclaw-setup)
6. [OpenAlgo Install + Update](#6-openalgo-install--update)
7. [OpenAlgo Git Dev Testing](#7-openalgo-git-dev-testing)
8. [Coolify + Hermes Setup](#8-coolify--hermes-setup)
9. [Domains & DNS](#9-domains--dns)
10. [Quick Reference & Shortcuts](#10-quick-reference--shortcuts)
11. [BuyerEdgeStrategy GitHub Auto-Sync Workflow](#11-buyeredgestrategy-github-auto-sync-workflow)

---

## 1. SSH Access & PEM Keys

### PEM Files

| Key | Current(Own) Host Path | Purpose |
|-----|------------------------|---------|
| **UbuntuPairKey.pem** | `/home/ubuntu/docs/keys/UbuntuPairKey.pem` | SSH login to **current host** (Ubuntu Coolify CP). The key used to SSH into this machine itself. |
| **DebianPairKey.pem** | `/home/ubuntu/docs/keys/DebianPairKey.pem` | Runs the **OpenAlgo production server** (Debian). Also used to reach **OpenAlgo server**. |

Both servers support `su` to become root after SSH login.

### Windows SSH Setup

```powershell
# Fix PEM permissions (Windows)
cd C:\Users\Manoj\.ssh
icacls "UbuntuPairKey.pem" /inheritance:r
icacls "UbuntuPairKey.pem" /remove "Authenticated Users"
icacls "UbuntuPairKey.pem" /remove "BUILTIN\Users"
icacls "UbuntuPairKey.pem" /remove "Everyone"
icacls "UbuntuPairKey.pem" /grant:r "$($env:USERNAME):R"

# Same for Debian key
icacls "DebianPairKey.pem" /inheritance:r
icacls "DebianPairKey.pem" /remove "Authenticated Users"
icacls "DebianPairKey.pem" /remove "BUILTIN\Users"
icacls "DebianPairKey.pem" /remove "Everyone"
icacls "DebianPairKey.pem" /grant:r "$($env:USERNAME):R"
```

### SSH Login Commands

```powershell
# Ubuntu (Coolify CP) — Current Host
ssh -i "C:\Users\Manoj\.ssh\UbuntuPairKey.pem" ubuntu@98.85.232.152

# Debian (OpenAlgo Server)
ssh -i "C:\Users\Manoj\.ssh\DebianPairKey.pem" admin@100.52.17.180
```

---

## 2. Shortcut Links

| Resource | Link |
|----------|------|
| **Shared Files - Drive** | [Google Drive Folder](https://drive.google.com/drive/folders/1VbbbYOgb1sGhrAoo6VThvy-Dw7r7Z2Bb?usp=sharing) |
| **Logs Page** | [BuyerEdgeStrategy Logs](https://oadev.karm8boost.online/python/BuyerEdgeStrategy_20260603013600/logs) |
| **EC2 Console** | [AWS EC2 Instances](https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#Instances:instanceState=running) |
| **EC2 Terminal** | [EC2 Instance Connect](https://us-east-1.console.aws.amazon.com/ec2-instance-connect/ssh/home?addressFamily=ipv4&connType=standard&instanceId=i-02daf0bf9e92cb98a&osUser=ubuntu&region=us-east-1&sshPort=22) |
| **Docker Cleanup Guide** | [ChatGPT Share](https://chatgpt.com/share/6a100180-2abc-83a8-8903-71a9e47f66a3) |
| **OpenAlgo Docs** | [Installation Guide](https://docs.openalgo.in/installation-guidelines/getting-started/docker-+-custom-domain) |
| **CIDR Converter** | [ip2cidr.com](https://ip2cidr.com) |

---

## 3. AWS / EC2 Instances

### Credentials

| Field | Value |
|-------|-------|
| **Email** | `manojv097@gmail.com` |
| **Password** | `74477447*Mkv` |

### EC2 Console Links

| Resource | Link |
|----------|------|
| **EC2 Console** | [AWS EC2 Instances](https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#Instances:instanceState=running) |
| **EC2 Terminal (Ubuntu)** | [Instance Connect](https://us-east-1.console.aws.amazon.com/ec2-instance-connect/ssh/home?addressFamily=ipv4&connType=standard&instanceId=i-02daf0bf9e92cb98a&osUser=ubuntu&region=us-east-1&sshPort=22) |

### Instance Table

| Attribute | Ubuntu (Coolify CP) | Debian (OpenAlgo) |
|-----------|---------------------|--------------------|
| **Instance ID** | `i-02daf0bf9e92cb98a` | `i-047b2491ee00a070b` |
| **Public IPv4** | `98.85.232.152` | `100.52.17.180` |
| **Private IPv4** | `172.31.33.219` | `172.31.41.120` |
| **OS User** | `ubuntu` | `admin` |
| **PEM Key** | `UbuntuPairKey.pem` | `DebianPairKey.pem` |
| **Purpose** | Coolify Control Panel | OpenAlgo Server |

---

## 4. EC2 Security & CIDR

### Why Use a Custom CIDR?

A **Custom CIDR** lets you allow access for a group of trusted systems instead of just one IP address.

**Common Uses:**
- 🏢 Office network
- 🏠 Home internet with changing IPs
- 🔒 VPN users
- ☁️ AWS VPC/Subnet communication

### CIDR Quick Reference

| CIDR | Meaning |
|------|---------|
| `/32` | Single IP |
| `/24` | Small network (~256 IPs) |
| `/16` | Large network |
| `/0` | Entire internet |

### Examples

```
198.51.100.45/32   # One device
198.51.100.0/24    # Office/Home network
0.0.0.0/0          # Public access (unsafe)
```

### Security Recommendations

| Scenario | Recommended CIDR |
|----------|-------------------|
| Single user | `/32` |
| Small office | `/24` |
| Public access | ❌ Avoid `/0` for sensitive services |

### Get Your Safe CIDR (PowerShell)

```powershell
$ip = Invoke-RestMethod ipv4.icanhazip.com
if ($ip -match ':') {
    $cidr = (($ip -split ':')[0..3] -join ':') + '::/64'
} else {
    $cidr = (($ip -split '\.')[0..2] -join '.') + '.0/24'
}
Write-Host "Your Safe AWS Custom CIDR is: " -NoNewline; Write-Host $cidr -ForegroundColor Green
```

---

## 5. OpenClaw Setup

```bash
# Enter OpenClaw container
docker exec -it openclaw-g46lzdid378rimjvkwe9cepa bash

# Onboard & configure
openclaw onboard
openclaw doctor --generate-gateway-token
openclaw config get gateway.auth.token
openclaw gateway restart
openclaw gateway status
openclaw doctor --fix
openclaw doctor --repair
```

---

## 6. OpenAlgo Install + Update

### Credentials

```
BROKER_API_KEY = '27a966dd-03bf-4f29-ad38-06670c016f5d'
BROKER_API_SECRET = '07t0l4vusz'
```

### Fresh Installation

```bash
sudo apt update && sudo apt upgrade -y
wget https://raw.githubusercontent.com/manojvermamv/openalgo/refs/heads/main/install/install-docker.sh
chmod +x install-docker.sh
./install-docker.sh
```

> **Clean slate before install:**
> ```bash
> sudo swapoff /swapfile
> sudo rm -f /swapfile
> sudo sed -i '/swapfile/d' /etc/fstab
> sudo ./install.sh
> ```

### Updating OpenAlgo

```bash
cd /opt/openalgo && \
sudo docker compose down && \
sudo git pull origin main && \
sudo docker compose build --no-cache && \
sudo docker compose up -d
```

### Backup / Verify / Monitor

```bash
openalgo-backup
openalgo-status
openalgo-logs
```

### Automated Backups (Cron)

```bash
crontab -e
# Run backup daily at 2 AM, keep only last 3 days
0 2 * * * /usr/local/bin/openalgo-backup >> /var/log/openalgo-backup.log 2>&1 && find /opt/openalgo-backups/ -type f -mtime +2 -delete
```

### Download Trade Journal & Logs

```bash
# Download trades.csv from OpenAlgo container
ssh -i "C:\Users\Manoj\.ssh\DebianPairKey.pem" admin@100.52.17.180 "docker exec openalgo-web cat /app/strategies/data/trades.csv" > trades.csv
ssh -i "C:\Users\Manoj\.ssh\DebianPairKey.pem" admin@100.52.17.180 "cat /opt/openalgo-strategies/data/trades.csv" > trades.csv

# Download backups via SCP
scp -i C:\Users\Manoj\.ssh\DebianPairKey.pem admin@100.52.17.180:/opt/openalgo-backups/openalgo_backup_*.tar.gz .
scp -i C:\Users\Manoj\.ssh\DebianPairKey.pem admin@100.52.17.180:/opt/openalgo-logs/strategies/openalgo_backup_*.tar.gz .

# Download specific log file
scp -i C:\Users\Manoj\.ssh\DebianPairKey.pem admin@100.52.17.180:/opt/openalgo-logs/strategies/BuyerEdgeStrategy_2_20260629115530_20260630_091500_IST.log .
```

---

## 7. OpenAlgo Git Dev Testing

```bash
# Add upstream repository as temporary remote
git remote add dev https://github.com/manojvermamv/openalgo.git

# Verify remotes & fetch
git remote -v
git fetch dev

# Create local tracking branch from remote
git checkout -b openalgo-config-sdk-temp --track dev/openalgo-config-sdk

# Switch back to main after testing
git checkout main

# Cleanup temp branch & remote
git branch -D openalgo-config-sdk-temp
git remote remove dev
```

---

## 8. Coolify + Hermes Setup

### Pull Latest Hermes Images

```bash
sudo docker pull nousresearch/hermes-agent:latest
sudo docker pull ghcr.io/nesquena/hermes-webui:latest
```

### Find Hermes Environment & Config Files

```bash
find / -name ".env" 2>/dev/null | grep hermes
find / -name "config.yaml" 2>/dev/null | grep hermes
```

### Edit Hermes Config

```bash
nano /var/lib/docker/volumes/n8x0usrwnv439r5hdhqm5xy3_hermes-home/_data/.env
nano /var/lib/docker/volumes/n8x0usrwnv439r5hdhqm5xy3_hermes-home/_data/config.yaml
```

### Hermes Docker Shell Access

```bash
# Create alias for easy shell access
echo "alias hermes-shell='docker exec -it \$(docker ps --format '{{.Names}}' | grep '^hermes-agent-' | head -n1) bash'" >> ~/.bashrc && source ~/.bashrc

# Use it
hermes-shell
which hermes
hermes --help
```

### Telegram Pairing Approve

```bash
hermes-shell
hermes pairing approve telegram DWFKDB5C
```

---

## 9. Domains & DNS

### Top Domain Picks

| Rank | Domain | Description |
|------|--------|-------------|
| 🥇 | `karm8boost.cloud` | Best identity + money + Saturn + branding |
| 🥈 | `karmasync.cloud` | Best tech + AI + KARM8 alignment |
| 🥉 | `algoboost.cloud` | Best scalable trading/AI |
| ★ | `gainforge.cloud` | — |
| ★ | `scalperx.cloud` | — |
| ★ | `profitpulse.cloud` | — |
| ★ | `signalkarma.cloud` | — |
| ★ | `quantforge.cloud` | — |
| ★ | `karmavault.cloud` | — |
| ★ | `tradealchemy.website` | — |

**Registrar:** [Porkbun](https://porkbun.com/)

### GoDaddy + EC2 Domain Setup

#### Step 1: Update GoDaddy DNS Records

Log into GoDaddy → **DNS Management** for `karm8boost.online`:

| Record Type | Name/Host | Value/Points to | TTL |
|-------------|-----------|----------------|-----|
| **A** | `@` (root) | `54.235.22.25` | 600s |
| **A** | `www` | `54.235.22.25` | 600s |

#### Step 2: Configure EC2 with Nginx Reverse Proxy

```bash
# SSH into EC2
ssh -i "C:\Users\Manoj\.ssh\UbuntuPairKey.pem" ubuntu@98.85.232.152

# Install Nginx
sudo apt update
sudo apt install nginx -y

# Create Nginx config
sudo nano /etc/nginx/sites-available/karm8boost.online
```

Nginx config:
```nginx
server {
    listen 80;
    server_name karm8boost.online www.karm8boost.online;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Enable & restart:
```bash
sudo ln -s /etc/nginx/sites-available/karm8boost.online /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Add SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d karm8boost.online -d www.karm8boost.online
```

### Update EC2 Security Group

Ensure inbound rules allow:
- **Port 80** (HTTP) — `0.0.0.0/0`
- **Port 443** (HTTPS) — `0.0.0.0/0`
- **Port 5000** — as needed

### Verification

```bash
curl -I http://karm8boost.online
```

Check DNS propagation at [whatsmydns.net](https://whatsmydns.net).

---

## 10. Quick Reference & Shortcuts

### Docker Cleanup

```bash
# Check disk usage
docker system df

# Prune all unused (without volumes)
docker system prune -a

# Prune all including volumes
docker system prune -a --volumes
```

### Fresh Install Prerequisites

```bash
sudo swapoff /swapfile
sudo rm -f /swapfile
sudo sed -i '/swapfile/d' /etc/fstab
sudo ./install.sh
```

### OpenAlgo Install Script

```bash
sudo apt update && sudo apt upgrade -y
wget https://raw.githubusercontent.com/manojvermamv/openalgo/refs/heads/main/install/install-docker.sh
chmod +x install-docker.sh
./install-docker.sh
```

### OpenAlgo Update

```bash
cd /opt/openalgo && \
sudo docker compose down && \
sudo git pull origin main && \
sudo docker compose build --no-cache && \
sudo docker compose up -d
```


---

## 11. BuyerEdgeStrategy GitHub Auto-Sync Workflow

Automatically syncs `BuyerEdgeStrategy.py` to GitHub whenever it changes on the host, making it publicly accessible via GitHub Pages / raw.githubusercontent.com — bypassing AI agent fetch restrictions on bare IP:port addresses.

### Architecture

```
File change on disk (/home/ubuntu/OA/strategies/examples/BuyerEdgeStrategy.py)
     │
     ▼  (kernel inotify — zero CPU when idle)
systemd service → github-sync-buyer-edge
     │
     ▼  (base64 encode + GitHub Contents API PUT)
GitHub Repo: manojvermamv/docs
     │
     ├─ https://raw.githubusercontent.com/manojvermamv/docs/main/BuyerEdgeStrategy.py
     │
     └─ https://manojvermamv.github.io/docs/BuyerEdgeStrategy.py  (if Pages enabled)
```

### Access URLs

| Method | URL | AI Agent Compatible |
|--------|-----|:-------------------:|
| Raw GitHub | `https://raw.githubusercontent.com/manojvermamv/docs/main/BuyerEdgeStrategy.py` | ✅ Yes |
| GitHub Pages | `https://manojvermamv.github.io/docs/BuyerEdgeStrategy.py` | ✅ Yes |
| GitHub API | `https://api.github.com/repos/manojvermamv/docs/contents/BuyerEdgeStrategy.py` | ✅ Yes |

### Service Details

| Attribute | Value |
|-----------|-------|
| **Watch Method** | `inotifywait` (kernel-level, no CPU when idle) |
| **Sync Method** | GitHub Contents API (PUT) via `gh api` |
| **Service Name** | `github-sync-buyer-edge` |
| **Script** | `/usr/local/bin/github-sync-buyer-edge-strategy.sh` |
| **Systemd Unit** | `/etc/systemd/system/github-sync-buyer-edge.service` |
| **Source File** | `/home/ubuntu/OA/strategies/examples/BuyerEdgeStrategy.py` |
| **GitHub Repo** | `manojvermamv/docs` (public) |
| **Resource Usage** | ~2MB RAM, 0% CPU when idle |

### How It Works

1. **`inotifywait`** watches the file's directory for `close_write` and `moved_to` events (handles both in-place edits and file replacement)
2. On change, a **60-second debounce timer** starts — any new change within the window resets the timer
3. After **60s of inactivity** (no more edits), the script **base64-encodes** the file and sends a **PUT** to GitHub Contents API
4. GitHub stores the file with commit message `Auto-update: BuyerEdgeStrategy.py`
5. The file is instantly available at the raw URL above — **no build step, no delay**

### Debounce Behavior (Verified)

The debounce timer resets on **every detected change**, not just the first one. Push only happens after **60 continuous seconds of inactivity** since the last change.

```
File change ──→ "Change detected, waiting 60s debounce..."
                    │
               ┌─────▼─────┐
               │  Start 60s │
               │  timer     │
               └─────┬─────┘
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
    New change before     60s passed since
    60s expires?          last change?
    Reset timer!          Push to GitHub!
            │                   │
            ▼                   ▼
    "Another change       "No changes for 60s,
     within 60s,           pushing to GitHub..."
     resetting timer..."
```

**Verified behavior (tested 2026-07-13):** 3 rapid edits within 5 seconds → only 1 push, occurring 61 seconds after the last edit:

```
T+0s   Change detected, waiting 60s debounce...
T+2s   Another change within 60s, resetting timer...   ← timer reset
T+4s   Another change within 60s, resetting timer...   ← timer reset again
T+65s  No changes for 60s, pushing to GitHub...        ← 60s idle after LAST edit
T+71s  Push successful                                  ← only 1 push for 3 edits
```

The debounce prevents pushing **intermediate or partial edits** during active editing by AI or human. No matter how many saves happen within a minute, only one push occurs — **60 seconds after the very last save**.

### Management Commands

```bash
# Status
systemctl status github-sync-buyer-edge

# Live logs
journalctl -u github-sync-buyer-edge -f

# Restart
sudo systemctl restart github-sync-buyer-edge

# Stop
sudo systemctl stop github-sync-buyer-edge

# Start
sudo systemctl start github-sync-buyer-edge

# Disable (stop + prevent auto-start)
sudo systemctl disable --now github-sync-buyer-edge
```

### Setup History

- **2026-07-13**: Initial setup — `inotify-tools` installed, watcher script created, systemd service created and enabled, initial file pushed to `manojvermamv/docs`
- **2026-07-13**: Added 60-second debounce timer to prevent pushing intermediate edits during rapid changes
- GitHub Pages on `manojvermamv/docs` can be enabled at any time via repo Settings → Pages

---

### BuyerEdgeStrategy File Server (DEPRECATED — removed 2026-07-13)

> **Previous approach:** A Python HTTP server on port 9999 with systemd service `buyer-edge-serve`.
> **Reason for removal:** AI agents cannot fetch bare IP:port URLs. Replaced by GitHub REST API + Pages workflow above.
> **All traces removed:** systemd service deleted, script deleted, Traefik config removed, AWS SG rule (port 9999) left for user to clean up.

---

## 12. OpenCode CLI Access in Hermes Containers

Makes the `opencode` CLI available directly inside both Hermes containers (`hermes-agent`, `hermes-webui`) via bind-mount, plus Docker socket access for container orchestration.

### Architecture

```
Opencode container (debian:bookworm-slim)
  │  entrypoint: nsenter -t 1 -m -u -i -- /root/.opencode/bin/opencode serve
  │  network_mode: host
  │  pid: host
  │
  ├── nsenter into host PID 1 → host mount namespace → real /usr/bin, /etc, /sbin
  ├── network_mode: host → direct access to host netstack (ufw, iptables, ports)
  ├── can add/remove real firewall rules (verified: ufw/iptables)
  └── /root/.opencode/bin/opencode (host file)
        │
        ├── bind-mount → hermes-agent: /usr/local/bin/opencode
        │
        └── bind-mount → hermes-webui: /usr/local/bin/opencode
```

The opencode server runs as the **host's root** via `nsenter -t 1 -m -u -i`, sharing the host's init, mount table, and network stack. OpenCode can read/write any host file, manage `ufw`/`iptables`, and bind any port — it is effectively root on the machine.

Both Hermes containers also get Docker socket + CLI for executing commands inside the `opencode-*` container when needed.

### What's Configured

| Capability | hermes-agent | hermes-webui |
|------------|:------------:|:------------:|
| `opencode` CLI binary | ✅ `/usr/local/bin/opencode` | ✅ `/usr/local/bin/opencode` |
| Docker socket (`/var/run/docker.sock`) | ✅ | ✅ |
| Docker CLI (`/usr/bin/docker`) | ✅ | ✅ |

### Usage

**Direct CLI (both containers):**
```bash
opencode --version
opencode run "Respond with exactly: OPENCODE_SMOKE_OK"
```

**Docker exec into opencode container (optional):**
```bash
OPENCODE_CONTAINER=$(docker ps --format '{{.Names}}' | grep '^opencode-')
docker exec "$OPENCODE_CONTAINER" opencode <subcommand>
```

### ⚠️ Limitation: No Root-Level Access

Hermes can access and run `opencode` commands, but **cannot perform Linux AWS root-level operations** (e.g., system packages, daemon configs, kernel params, AMI-level changes). Those still require native SSH shell access via PEM key.

**Why:** The opencode CLI has two execution modes:

| Context | How it runs | Root access |
|---------|------------|-------------|
| **opencode container** | `nsenter -t 1 -m -u -i` into host PID 1 + `network_mode: host` | ✅ **Full host root** — shares host's init, mount namespace, network stack. Can modify ufw/iptables, system files, kernel params. Verified: real firewall rules added/removed. |
| **Hermes containers** | Binary bind-mounted at `/usr/local/bin/opencode` inside a **container-isolated** mount namespace | ❌ No `nsenter` path, no host PID/mount/network namespace — only the container's own filesystem and the mounted Docker socket |

Inside Hermes containers, `opencode` is just a binary on disk — it cannot `nsenter` back to the host. It can use the Docker socket to `docker exec` into the opencode container (which has full host access), but cannot modify the host directly.

### Dynamic Container Name (don't hardcode UUID)

The opencode container name includes a random Coolify UUID suffix. Always resolve it dynamically:

```bash
# Safe — works across redeploys
OPENCODE_CONTAINER=$(docker ps --format '{{.Names}}' | grep '^opencode-')

# Bad — will break on next Coolify redeploy
docker exec opencode-p3w9brzbubrjxtuinxf64vpx opencode ...
```
### ⚠️ Caveat: Coolify Persistence

The compose file at `/data/coolify/services/roows6yds269qwqtw8riwk1z/docker-compose.yml` is **generated by Coolify**. It **will be overwritten** when Coolify redeploys the service (e.g., on image update, env var change, or manual redeploy in the Coolify UI).

To persist these changes permanently, add them through the **Coolify UI** → **hermes service** → **Advanced** → **Docker Compose** customization, or as **custom environment variables** in the service settings.

The specific additions to maintain:

| Type | Value |
|------|-------|
| **Bind mount** (both) | `/root/.opencode/bin/opencode:/usr/local/bin/opencode:ro` |
| **Bind mount** (both) | `/var/run/docker.sock:/var/run/docker.sock:rw` |
| **Bind mount** (both) | `/usr/bin/docker:/usr/bin/docker:ro` |
| **Group add** (hermes-webui) | `group_add: ["988"]` (matches host docker GID) |

### Setup Reference

The configuration lives in the Coolify service docker-compose:

- **Compose file:** `/data/coolify/services/roows6yds269qwqtw8riwk1z/docker-compose.yml`
- **Environment:** `/data/coolify/services/roows6yds269qwqtw8riwk1z/.env`
- **OpenCode compose:** `/data/coolify/services/p3w9brzbubrjxtuinxf64vpx/docker-compose.yml`

---

> **Last updated:** 2026-07-19
> **Maintained by:** Infrastructure Handbook at `/host/home/ubuntu/INFRASTRUCTURE-HANDBOOK.md`