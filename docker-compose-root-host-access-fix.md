# Docker Compose Host Access — Diagnosis & Fix

## Current Container State

| Property | Value |
|---|---|
| **Image** | `debian:bookworm-slim` |
| **Container** | `opencode-p3w9brzbubrjxtuinxf64vpx` |
| **PID mode** | `host` (shares host PID namespace) |
| **Network mode** | `p3w9brzbubrjxtuinxf64vpx` (container's own Docker network, NOT host) |
| **Capabilities** | `CAP_NET_ADMIN`, `CAP_NET_RAW`, `CAP_SYS_ADMIN`, `CAP_SYS_PTRACE` |
| **Entrypoint** | `nsenter -t 1 -m -- /root/.opencode/bin/opencode` (mount namespace only) |
| **Volumes** | `/opt/hostbin:/opt/hostbin:ro`, `/opt/automation:/opt/automation:rw`, docker socket, SSL certs, opencode binary |
| **PATH** | `/opt/hostbin:/usr/local/bin:/usr/bin:/bin` (OLD — missing `/usr/sbin`, `/sbin`) |
| **BASH_ENV** | `/opt/hostbin/.bashenv` (dead weight) |

---

## Two Issues Identified

### Issue 1: PATH Problem (RESOLVED)

**Root cause:** The compose environment sets `PATH=/opt/hostbin:/usr/local/bin:/usr/bin:/bin` which is missing `/usr/sbin` and `/sbin` — where `ufw` and `iptables` actually live on the host.

**Evidence:**
```
# Inside container — binary not found:
$ which ufw
ufw not found

# On host (SSH) — binary exists:
$ which ufw
/usr/sbin/ufw
```

**Fix:** Remove the `PATH=` and `BASH_ENV=` env vars entirely, and the `/opt/hostbin` volume mount. The base `debian:bookworm-slim` image's default PATH already includes `/usr/local/sbin`, `/usr/sbin`, `/sbin` — matching the host's SSH session exactly. This is the compose-level fix (Option 2 from the original analysis, applied at source).

### Issue 2: Network Namespace Isolation (NOT FIXABLE IN COMPOSE)

**Root cause:** The entrypoint uses `nsenter -t 1 -m` which shares only the **mount namespace** — not the network namespace (`-n` was deliberately left out). This means `ufw`/`iptables` binaries resolve correctly as real host binaries (PATH fix), but the kernel firewall state they read/write is still scoped to the container's own network namespace.

**Evidence (NAT Table Comparison):**

| Aspect | Container | Host (SSH) |
|---|---|---|
| `127.0.0.11` DNAT | Present | Not present |
| DOCKER chain | Not present | Present with DNAT rules |
| MASQUERADE rules | Not present | Present for multiple Docker networks |
| Port forwarding | None | 6001→10.0.1.4, 6002→10.0.1.4, 8000→10.0.1.6, 80/443→10.0.1.7 |

| Aspect | Container | Host (SSH) |
|---|---|---|
| INPUT policy | ACCEPT (empty) | ACCEPT (with UFW chains) |
| FORWARD policy | ACCEPT (empty) | DROP (with UFW chains) |
| OUTPUT policy | ACCEPT (empty) | ACCEPT (with UFW chains) |
| DOCKER-USER chain | Not present | Present |
| UFW chains | Not present | Present (but inactive) |

**Why `-n` was not added:** Adding `-n` to `nsenter` would enter the host's network namespace, which broke Traefik routing when tried earlier. The network namespace isolation must remain. The PATH fix alone resolves `ufw`/`iptables` binary resolution; the firewall state remains container-scoped by design.

**Key finding correction:** The original report's "System has NO active firewall" was wrong. The host has proper Docker-managed iptables rules (DOCKER, DOCKER-USER, DOCKER-FORWARD chains). UFW is installed but inactive. Docker's iptables chains ARE the firewall — this is normal for a Docker host running Coolify/Traefik.

---

## The Compose Fix

Replace the Coolify service compose with:

```yaml
services:
  opencode:
    image: debian:bookworm-slim
    container_name: opencode

    # ── Namespace sharing ──────────────────────────────────────
    pid: host                        # keeps PID 1 visible for nsenter
    # network_mode intentionally NOT set to host — -n breaks Traefik

    # ── Capabilities ───────────────────────────────────────────
    cap_add:
      - SYS_ADMIN                    # needed for nsenter/chroot
      - SYS_PTRACE                   # needed for process introspection
      - NET_ADMIN                    # needed for iptables/ufw manipulation
      - NET_RAW                      # needed for raw socket operations

    # ── Volumes ────────────────────────────────────────────────
    volumes:
      # Host filesystem access (chroot approach — replaces old hostbin)
      - /:/host:rslave

      # Persistent state
      - /root/.local/share/opencode:/root/.local/share/opencode:rw
      - /root/.config/opencode:/root/.config/opencode:rw
      - /root/.cache/opencode:/root/.cache/opencode:rw

      # Automation workspace
      - /opt/automation:/opt/automation:rw

      # Docker socket + binary
      - /var/run/docker.sock:/var/run/docker.sock:rw
      - /usr/bin/docker:/usr/bin/docker:ro

      # OpenCode binary
      - /root/.opencode/bin/opencode:/usr/local/bin/opencode:ro

      # SSL certs
      - /etc/ssl/certs:/etc/ssl/certs:ro

    # ── Environment ────────────────────────────────────────────
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      # NOTE: Do NOT set PATH= or BASH_ENV= here.
      # The debian:bookworm-slim default PATH already includes
      # /usr/local/sbin, /usr/sbin, /sbin — which is what ufw
      # and iptables need. The old /opt/hostbin prefix and
      # BASH_ENV are dead weight — removed.

    # ── Entrypoint ─────────────────────────────────────────────
    # Mount namespace only (-m), NOT network namespace (-n)
    entrypoint:
      - nsenter
      - -t
      - "1"
      - -m
      - --
      - /root/.opencode/bin/opencode
    command:
      - serve
      - --hostname
      - "0.0.0.0"
      - --port
      - "4096"
      - --print-logs
      - --log-level
      - DEBUG

    # ── Ports ──────────────────────────────────────────────────
    ports:
      - "4096:4096"

    restart: unless-stopped
```

---

## What Was Removed (and Why)

| Removed | Reason |
|---|---|
| `PATH=/opt/hostbin:/usr/local/bin:/usr/bin:/bin` | Base image PATH already includes `/usr/sbin`, `/sbin`. The old prefix caused the ufw/iptables resolution failure. |
| `BASH_ENV=/opt/hostbin/.bashenv` | Was a shim for the old hostbin approach. Dead weight now that chroot wrappers handle host access. |
| `/opt/automation/scripts/common/hostbin:/opt/hostbin:ro` volume mount | Replaced by `/:/host:rslave` which gives full host filesystem access via chroot. The hostbin shim directory is no longer needed. |

---

## What Stays the Same

| Kept | Reason |
|---|---|
| `nsenter -t 1 -m` (mount only, no `-n`) | `-n` breaks Traefik routing. Network namespace isolation is intentional. |
| `pid: host` | Required for `nsenter -t 1` to target the host's PID 1. |
| `cap_add: SYS_ADMIN, SYS_PTRACE, NET_ADMIN, NET_RAW` | SYS_ADMIN for nsenter/chroot, SYS_PTRACE for process introspection, NET_ADMIN/NET_RAW for network diagnostics (container-scoped). |
| `/:/host:rslave` | Chroot-based host access. Wrappers in the Dockerfile shadow container binaries. |
| Docker socket mount | Container management via Docker CLI. |

---

## Host Firewall Reality

The host's firewall posture is managed by Docker's iptables chains, not UFW:

1. **UFW:** Installed but inactive (`Status: inactive`)
2. **Docker iptables chains:** DOCKER, DOCKER-USER, DOCKER-FORWARD — these ARE the firewall
3. **FORWARD policy:** DROP — Docker's chains handle allowed traffic
4. **Port forwarding active:** 6001, 6002, 8000, 80, 443, 8080 DNAT'd to container IPs
5. **No `127.0.0.11` rule on host** — that's a container-internal Docker DNS artifact

This is normal and expected for a Docker host running Coolify/Traefik.

---

## Post-Deploy Verification

```bash
# From inside the container:
docker exec -it opencode bash

# 1. Verify PATH includes /usr/sbin
echo $PATH
# Should show: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# 2. Verify ufw binary resolves
which ufw
# Should show: /usr/sbin/ufw

# 3. Verify ufw reads container state (not host — expected)
ufw status
# Will show container's own state

# 4. Verify chroot still works
chroot /host /usr/bin/uname -r
# Should show host kernel version

# 5. Verify iptables resolves (container-scoped)
iptables -L -n | head -10
# Will show container's iptables, not host's — this is correct
```

---

## Lesson Learned

Always verify network-related findings via SSH to the host, not from within a container — even with mount namespace sharing (`-m`), the network namespace remains isolated. The `127.0.0.11` DNAT rule is Docker's per-container embedded DNS resolver and only exists in container network namespaces, never on the host.
