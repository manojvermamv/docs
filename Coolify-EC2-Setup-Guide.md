# 🚀 Complete Coolify Setup Guide — EC2 Ubuntu + Root Domain + Wildcard Subdomains

A production-ready Coolify deployment guide covering:

- AWS EC2 Ubuntu server provisioning
- Root domain dashboard (`karm8boost.online`)
- Optional subdomain dashboard (`cool.karm8boost.online`)
- Automatic SSL via Let's Encrypt + Traefik
- Wildcard subdomain routing
- Docker-based application deployments
- Full EC2 File Browser access
- Real-world issue fixes encountered during setup

---

## Table of Contents

1. [Final Architecture Overview](#1-final-architecture-overview)
2. [Requirements](#2-requirements)
3. [EC2 Security Group Configuration](#3-ec2-security-group-configuration)
4. [Connect to EC2](#4-connect-to-ec2)
5. [Update Ubuntu Server](#5-update-ubuntu-server)
6. [Install Coolify](#6-install-coolify)
7. [Verify Installation](#7-verify-installation)
8. [Fix Common Nginx Conflict](#8-fix-common-nginx-conflict)
9. [DNS Setup (GoDaddy)](#9-dns-setup-godaddy)
10. [Remove AAAA Records](#10-remove-aaaa-records)
11. [Open Coolify Dashboard](#11-open-coolify-dashboard)
12. [Dashboard Domain Options](#12-dashboard-domain-options)
13. [Configure Dashboard URL](#13-configure-dashboard-url)
14. [Configure Wildcard Domain](#14-configure-wildcard-domain)
15. [Start Coolify Proxy](#15-start-coolify-proxy)
16. [Verify Ports](#16-verify-ports)
17. [SSL Troubleshooting](#17-ssl-troubleshooting)
18. [Regenerate SSL Properly](#18-regenerate-ssl-properly)
19. [Verify Wildcard DNS](#19-verify-wildcard-dns)
20. [Deploy Applications](#20-deploy-applications)
21. [Example Production Structure](#21-example-production-structure)
22. [Full Proxy Reset — If SSL/Proxy Breaks](#22-full-proxy-reset--if-sslproxy-breaks)
23. [Complete Coolify Removal](#23-complete-coolify-removal)
24. [Fresh Reinstall](#24-fresh-reinstall)
25. [File Browser on Coolify — Full EC2 File Access](#25-file-browser-on-coolify--full-ec2-file-access)
26. [Final Best Practices](#26-final-best-practices)
27. [Final Result Summary](#27-final-result-summary)

---

# 🗺️ 1. Final Architecture Overview

## Recommended Setup

| Component          | URL                                       |
| ------------------ | ----------------------------------------- |
| Coolify Dashboard  | `https://karm8boost.online`               |
| Optional Dashboard | `https://cool.karm8boost.online`          |
| Frontend App       | `https://app.karm8boost.online`           |
| API                | `https://api.karm8boost.online`           |
| File Browser       | `https://files.karm8boost.online/files/`  |
| Any Future App     | `https://anything.karm8boost.online`      |

---

# 📋 2. Requirements

## AWS EC2

| Setting       | Recommended Value                  | Notes                                             |
| ------------- | ---------------------------------- | ------------------------------------------------- |
| OS            | Ubuntu 22.04 LTS or 24.04 LTS      | Both officially supported                         |
| Instance Type | t3.small (minimum) / t3.medium     | t3.small = 2GB RAM, tight; t3.medium = 4GB, stable |
| vCPU          | 2 minimum                          | Required by Coolify                               |
| RAM           | 2 GB minimum / 4 GB recommended    | t3.small requires swap space configured            |
| Storage       | **30 GB minimum** (50 GB+ ideal)   | 20 GB may fill up under active deployments        |
| Elastic IP    | Required                           | Prevents IP change on reboot                      |

> **⚠️ t3.small Warning:** With only 2 GB RAM, application builds (especially Node.js/Next.js) can trigger Out-of-Memory (OOM) crashes. Configure at least 4 GB of swap space if using t3.small:
>
> ```bash
> sudo fallocate -l 4G /swapfile
> sudo chmod 600 /swapfile
> sudo mkswap /swapfile
> sudo swapon /swapfile
> echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
> ```

---

# 🔒 3. EC2 Security Group Configuration

Open these inbound ports in your AWS Security Group:

| Port | Protocol | Purpose                                          |
| ---- | -------- | ------------------------------------------------ |
| 22   | TCP      | SSH                                              |
| 80   | TCP      | HTTP (required for SSL challenge)                |
| 443  | TCP      | HTTPS                                            |
| 8000 | TCP      | Coolify Dashboard (initial setup)                |
| 6001 | TCP      | Real-time WebSocket communications (optional)    |
| 6002 | TCP      | In-browser container terminal access (optional)  |

Source for all ports (initial setup):

```text
0.0.0.0/0
```

> **After domain is configured:** You can restrict ports 8000, 6001, and 6002 to your own IP or a VPN CIDR. All user traffic will then flow through 443 via Traefik.

> **⚠️ Note on UFW:** Docker uses `iptables` NAT rules that bypass UFW. Manage port rules exclusively through the **AWS Security Group**, not UFW, to avoid unexpected exposure.

---

# 🖥️ 4. Connect to EC2

## Windows PowerShell

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

> Make sure the `.pem` file has correct permissions. On Windows, restrict access via file Properties → Security if SSH complains about permissions.

---

# 🔄 5. Update Ubuntu Server

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install curl -y
```

---

# ⚙️ 6. Install Coolify

Official installation command:

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
```

> **⚠️ Important:** The script requires root privileges. Use `sudo bash` — not just `bash`. Running without `sudo` will cause permission errors during Docker installation.

This automatically installs:

- Docker Engine (v24+)
- Docker Compose
- Traefik (reverse proxy)
- PostgreSQL
- Redis
- Coolify itself

---

# ✅ 7. Verify Installation

Run:

```bash
docker ps
```

Expected running containers:

```text
coolify
coolify-proxy
coolify-db
coolify-redis
coolify-sentinel
```

Check that all 5 containers show `Up` status. If any show `Restarting` or `Exited`, inspect logs:

```bash
docker logs <container-name>
```

---

# 🔧 8. Fix Common Nginx Conflict

## Problem

Coolify proxy fails because:

```text
Port 80 is already in use
```

## Check Port Usage

```bash
sudo lsof -i :80
```

If nginx appears:

```bash
sudo systemctl stop nginx
sudo systemctl disable nginx
sudo apt remove nginx nginx-common -y
sudo apt autoremove -y
```

## Why

Coolify already includes a fully managed:

- Traefik reverse proxy
- SSL certificate management (Let's Encrypt)
- Request routing

You should **NOT** run nginx manually on the host. It will conflict with Coolify's built-in Traefik proxy.

---

# 🌐 9. DNS Setup (GoDaddy)

## Required DNS Records

| Type  | Host | Value             | Purpose                             |
| ----- | ---- | ----------------- | ----------------------------------- |
| A     | @    | YOUR_EC2_IP       | Root domain (karm8boost.online)     |
| A     | *    | YOUR_EC2_IP       | Wildcard (*.karm8boost.online)      |
| CNAME | www  | karm8boost.online | www redirect                        |

> **DNS Propagation:** After saving records, wait 5–30 minutes (sometimes up to a few hours) before testing. Use `nslookup karm8boost.online` or `dig karm8boost.online` to verify propagation.

---

## Optional Dashboard Subdomain

Only required if you're using `https://cool.karm8boost.online` as the dashboard URL:

| Type | Host | Value       |
| ---- | ---- | ----------- |
| A    | cool | YOUR_EC2_IP |

> The wildcard `*` A record already covers `cool.karm8boost.online` — adding an explicit `cool` record is optional but provides DNS clarity.

---

# 🧹 10. Remove AAAA Records (Optional but Recommended)

Delete **ALL** AAAA (IPv6) records from your DNS zone.

## Why This Is Critical

Let's Encrypt performs domain validation and may try IPv6 (AAAA) if those records exist.

If your EC2 instance does not have IPv6 properly configured:

- The HTTP-01 challenge will fail on IPv6
- SSL certificate generation will fail
- HTTPS will remain broken even though IPv4 works

> This was one of the major real-world issues encountered during setup.

---

# 🖥️ 11. Open Coolify Dashboard

Open in your browser:

```text
http://YOUR_EC2_IP:8000
```

Create a new admin account:

- Email address
- Password (use a strong password — the dashboard is publicly accessible during setup)
- Initial organization name

> This is the first-time setup wizard. There are no default credentials — you define them here.

---

# 🔀 12. Dashboard Domain Options

You can configure the Coolify dashboard using one of two approaches.

---

## Option A — Root Domain Dashboard (Recommended)

Dashboard URL:

```text
https://karm8boost.online
```

The root domain becomes the Coolify management panel. All other apps use subdomains.

---

## Option B — Subdomain Dashboard (Optional)

Dashboard URL:

```text
https://cool.karm8boost.online
```

Use this if you want the root domain available for a different primary application.

---

# 🔗 13. Configure Dashboard URL

Inside Coolify:

```text
Settings → Configuration (or General)
```

---

## If Using Root Domain Dashboard

Set Instance Domain to `https://karm8boost.online` and save.

---

## If Using Subdomain Dashboard

Set Instance Domain to `https://cool.karm8boost.online` and save. The browser will redirect to the new domain.

---

# 🌍 14. Configure Wildcard Domain

Inside Coolify:

```text
Servers → localhost → Configuration
```

## Wildcard Domain Value

Always set the wildcard domain to the **root domain**, regardless of which dashboard option you chose:

```text
https://karm8boost.online
```

> Even if your dashboard runs at `cool.karm8boost.online`, the wildcard domain must be set to `https://karm8boost.online`. This is what allows `*.karm8boost.online` subdomains to be automatically routed.

---

# 🚦 15. Start Coolify Proxy

Inside Coolify:

```text
Servers → localhost → Proxy → Start Proxy
```

This creates:

- Traefik reverse proxy container (`coolify-proxy`)
- SSL routing via Let's Encrypt HTTP-01 challenge
- Automatic ACME certificate storage at `/data/coolify/proxy/acme.json`

> After starting the proxy, wait **2–5 minutes** for initial SSL certificates to be issued before testing HTTPS.

---

# 🔌 16. Verify Ports

Run on your EC2 server:

```bash
sudo ss -tulpn | grep -E ':80|:443'
```

Expected output:

```text
tcp   LISTEN  0   128   0.0.0.0:80    ...  users:(("docker-proxy",...))
tcp   LISTEN  0   128   0.0.0.0:443   ...  users:(("docker-proxy",...))
```

`docker-proxy` listening on ports 80 and 443 confirms Traefik is correctly bound.

---

# 🛠️ 17. SSL Troubleshooting

If HTTPS shows `Not Secure` or certificate errors, these are the most common causes and fixes:

| Problem                              | Fix                                                         |
| ------------------------------------ | ----------------------------------------------------------- |
| nginx occupying port 80              | Stop and remove nginx (see Section 8)                       |
| Broken or zero-byte `acme.json`      | Fix permissions or delete and regenerate (see Section 18)   |
| Stale proxy configuration            | Full proxy rebuild (see Section 23)                         |
| AAAA (IPv6) records in DNS           | Delete all AAAA records (see Section 10)                    |
| Cloudflare proxy (orange cloud) on   | Disable temporarily during initial SSL issuance             |
| Port 80 not reachable from internet  | Verify EC2 Security Group allows 0.0.0.0/0 on port 80      |
| DNS not propagated yet               | Wait and re-test after propagation                          |
| Chrome showing stale SSL / Not Secure | Clear Chrome data + flush DNS cache (see below)            |

### Chrome SSL / DNS Cache Fix

If the server SSL is valid but Chrome still shows `Not Secure` or a certificate error:

1. **Clear Chrome browsing data** — `Settings → Privacy → Clear browsing data` (check *Cached images and files* + *Cookies*)
2. **Flush Chrome DNS cache** — open `chrome://net-internals/#dns` → click **Clear host cache**

---

# 🔁 18. Regenerate SSL Properly

## Step 1 — Fix `acme.json` Permissions

Before deleting, first try fixing permissions (Traefik requires strict 600):

```bash
sudo chmod 600 /data/coolify/proxy/acme.json
```

Then restart the proxy (see Step 2). If that doesn't resolve it, proceed to delete.

## Step 2 — Remove Old SSL Data

```bash
sudo rm -f /data/coolify/proxy/acme.json
```

## Step 3 — Restart Proxy

Inside Coolify:

```text
Servers → localhost → Proxy → Restart Proxy
```

Wait **2–5 minutes** for Let's Encrypt to issue new certificates.

## Step 4 — Check Proxy Logs

If SSL still fails, inspect the Traefik proxy logs for specific errors:

```bash
docker logs coolify-proxy --tail 100
```

Common log errors and meanings:

- `too many certificates already issued` → Let's Encrypt rate limit hit; wait up to 7 days
- `Connection refused` → Port 80 blocked by Security Group
- `NXDOMAIN` → DNS not propagated yet

---

> **⚠️ IMPORTANT — Database Certificates vs. HTTPS Certificates**
>
> Do **NOT** use the `Regenerate Certificate` popup found in the database SSL section.
>
> That is **only** for:
> - PostgreSQL internal certificates
> - MySQL internal certificates
> - Internal database-to-database encryption
>
> It has **no effect** on website HTTPS.

---

# 🌐 19. Verify Wildcard DNS

## Option 1 — Terminal (nslookup)

Run from any machine:

```bash
nslookup anything.karm8boost.online
```

Expected output includes:

```text
Address: YOUR_EC2_IP
```

## Option 2 — Chrome DNS Lookup

Open in Chrome:

```text
chrome://net-internals/#dns
```

In the **DNS lookup** field, enter:

```text
anything.karm8boost.online
```

Click **Lookup** — the result should show your EC2 IP.

> You can also click **Clear host cache** here to flush Chrome's cached DNS before re-testing.

This confirms the wildcard DNS record (`*`) is correctly pointing to your EC2 IP.

---

# 📦 20. Deploy Applications

Inside Coolify:

```text
Projects → New Project → New Resource
```

Supported deployment types:

- Docker Compose
- Docker Image
- Git Repository (GitHub, GitLab, Bitbucket)
- Nixpacks (auto-detect language/framework)
- Static Sites

For each resource, set the domain to any subdomain (e.g., `https://newapp.karm8boost.online`) and Coolify will automatically configure Traefik routing and SSL.

---

# 🏗️ 21. Example Production Structure

| Service     | Domain                        | Notes                          |
| ----------- | ----------------------------- | ------------------------------ |
| Dashboard   | `karm8boost.online`           | Coolify management panel       |
| FileBrowser | `files.karm8boost.online`     | EC2 filesystem browser         |
| OpenAlgo    | `openalgo.karm8boost.online`  | Trading platform               |

---

# ♻️ 22. Full Proxy Reset — If SSL/Proxy Breaks

Use this procedure **ONLY** if the Traefik proxy becomes corrupted or unrecoverable. This resets all SSL certificates and proxy configuration.

---

## Step 1 — Stop Proxy

Inside Coolify:

```text
Servers → localhost → Proxy → Stop Proxy
```

---

## Step 2 — Remove All Proxy Data

SSH into EC2:

```bash
sudo rm -rf /data/coolify/proxy
```

> **⚠️ This deletes all SSL certificates.** They will be re-issued by Let's Encrypt when the proxy restarts. Be mindful of Let's Encrypt rate limits (5 certificates per domain per 7 days).

---

## Step 3 — Restart Coolify

```bash
docker restart coolify
```

---

## Step 4 — Recreate Proxy

Inside Coolify:

```text
Servers → localhost → Proxy → Start Proxy
```

This fully rebuilds:

- Traefik container
- SSL certificate storage
- Routing configuration
- ACME/Let's Encrypt integration

Wait **2–5 minutes** for certificates to be issued.

---

# 🗑️ 23. Complete Coolify Removal

> **🚨 DANGER — IRREVERSIBLE**
>
> This removes **everything** permanently:
> - All deployed applications
> - All databases and their data
> - All Docker volumes
> - All SSL certificates
> - Coolify itself and its configuration
>
> **Back up all data before proceeding.**

---

## Step 1 — Stop All Containers

```bash
docker stop $(docker ps -aq)
```

---

## Step 2 — Remove All Containers

```bash
docker rm -f $(docker ps -aq)
```

---

## Step 3 — Remove All Volumes

```bash
docker volume rm $(docker volume ls -q)
```

> This permanently deletes all database data, application state, and persistent storage.

---

## Step 4 — Remove All Networks

```bash
docker network prune -f
```

---

## Step 5 — Remove Coolify Data

```bash
sudo rm -rf /data/coolify
```

---

## Step 6 — Remove Docker (Optional)

If you want to fully purge Docker from the system:

```bash
# Stop Docker services
sudo systemctl stop docker docker.socket containerd

# Purge Docker packages
sudo apt-get purge -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras

# Remove unused dependencies
sudo apt-get autoremove -y --purge

# Remove residual Docker directories
sudo rm -rf /var/lib/docker
sudo rm -rf /var/lib/containerd
sudo rm -rf /etc/docker
rm -rf ~/.docker
```

> **Note:** The original `sudo apt remove docker docker.io containerd runc` command may not remove modern Docker CE packages (installed via Docker's official apt repository). Use the purge commands above for a complete removal.

---

# 🔃 24. Fresh Reinstall

After removal, reinstall Coolify:

```bash
sudo apt update && sudo apt install curl -y
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
```

Then repeat the setup from [Section 9 (DNS)](#9-dns-setup-godaddy) onward.

---

# 📁 25. File Browser on Coolify — Full EC2 File Access

This setup deploys File Browser as a Coolify-managed Docker service, providing full browser-based access to the EC2 filesystem.

---

## Goal

- Access and manage the entire EC2 filesystem from a web browser
- Keep the service managed, persistent, and accessible via a domain
- Integrate with Coolify's Traefik routing and SSL

---

## Docker Compose — Final Working Setup

```yaml
services:
  filebrowser:
    image: 'filebrowser/filebrowser:latest'
    container_name: filebrowser-root
    user: '0:0'
    privileged: true
    restart: unless-stopped

    environment:
      - SERVICE_URL_FILEBROWSER_80

    volumes:
      - '/home:/host/home:rw'
      - '/opt:/host/opt:rw'
      - '/data:/host/data:rw'
      - '/data/coolify:/host/coolify:ro'
      - '/var/log:/host/logs:ro'
      - '/etc:/host/etc:ro'
      - './database.db:/database.db'
      - './filebrowser.json:/.filebrowser.json:ro'

    command: '--root /host'
```

---

## How It Works

```text
/home          →  /host/home   (rw)   User files
/data          →  /host/data   (rw)   App & server data
/data/coolify  →  /host/coolify (ro)  Coolify config (read-only)
/var/log       →  /host/logs   (ro)   System logs (read-only)
/etc           →  /host/etc    (ro)   OS config (read-only)
```

---

## Permissions Configuration

| Setting              | Value          | Purpose                                  |
| -------------------- | -------------- | ---------------------------------------- |
| `user: "0:0"`        | UID 0 (root)   | Required to read all mounted paths       |
| `privileged: true`   | Enabled        | Required for bind-mounting host paths    |
| `/home:/host/home`   | Read + Write   | User home directories                    |
| `/data:/host/data`   | Read + Write   | Application and server data              |
| `/data/coolify`      | Read-only      | Coolify config visible but protected     |
| `/var/log`           | Read-only      | Log inspection without modification risk |
| `/etc`               | Read-only      | OS config visible but protected          |

---

## ⚠️ Security Notes

This version mounts only **specific, scoped directories** instead of the full root filesystem — reducing blast radius significantly. However, some risks remain:

| Risk                          | Status in this version                                              |
| ----------------------------- | ------------------------------------------------------------------- |
| **Full system compromise**    | Reduced — only selected paths exposed, not entire OS               |
| **Container escape risk**     | Still present — `privileged: true` allows container escape          |
| **Data destruction**          | Reduced — `/etc` and Coolify config are read-only                  |
| **Brute force exposure**      | Still applies — protect with strong password and IP restrictions    |

**Mandatory hardening steps:**

1. **Change default credentials immediately** after first login (default: `admin` / `admin`)
2. **Restrict access** — consider IP allowlisting at the Security Group level
3. **Never expose without authentication** — use a strong unique password
4. **Optionally use Cloudflare Tunnel or Tailscale** instead of a public URL for maximum security

**Paths exposed and their risk level:**

| Path               | Access     | Risk                                      |
| ------------------ | ---------- | ----------------------------------------- |
| `/host/home`       | Read/Write | User files — safe to browse and edit      |
| `/host/data`       | Read/Write | App data — avoid deleting Coolify volumes |
| `/host/coolify`    | Read-only  | Coolify config — cannot be modified       |
| `/host/logs`       | Read-only  | System logs — inspection only             |
| `/host/etc`        | Read-only  | OS config — cannot be modified            |

---

## Optional Future Hardening

- Add restricted user accounts (non-root) with access only to specific directories
- Mount only required subdirectories instead of `/`
- Add Authelia or Authentik as an authentication layer in front of File Browser
- Use a VPN (Tailscale/WireGuard) instead of public HTTPS access

---

# 📌 26. Final Best Practices

## Always Use Wildcard DNS

Required for automatic subdomain routing:

| Type | Host | Value       |
| ---- | ---- | ----------- |
| A    | *    | YOUR_EC2_IP |

---

## Remove AAAA Records Unless IPv6 Is Configured

Prevents Let's Encrypt SSL validation failures on domains where EC2 has no IPv6 connectivity.

---

## Do Not Run Nginx Manually on the Host

Coolify uses Traefik as its built-in reverse proxy. Running nginx on the host will cause port 80/443 conflicts and break SSL.

---

## Configure Swap If Using t3.small

Required to prevent OOM crashes during builds (see Section 2).

---

## Fix `acme.json` Permissions After Manual Changes

Traefik requires strict `600` permissions:

```bash
sudo chmod 600 /data/coolify/proxy/acme.json
```

---

## Restrict Coolify Ports After Domain Setup

Once the domain is active and Coolify is accessible via HTTPS, restrict ports 8000, 6001, and 6002 to your IP only in the AWS Security Group.

---

## Check Proxy Logs When SSL Fails

```bash
docker logs coolify-proxy --tail 100
```

---

# 🎉 27. Final Result Summary

After completing this guide, you will have:

✅ AWS EC2 Ubuntu server (provisioned and updated)  
✅ Coolify installed with all required services  
✅ Root domain dashboard (`karm8boost.online`)  
✅ Optional subdomain dashboard  
✅ Wildcard subdomain routing (`*.karm8boost.online`)  
✅ Automatic SSL via Let's Encrypt + Traefik  
✅ Traefik reverse proxy managing all routing  
✅ Multi-application Docker-based deployments  
✅ Production-ready infrastructure  
✅ Browser-based EC2 file manager (File Browser)  
✅ Full EC2 filesystem access with security awareness  
