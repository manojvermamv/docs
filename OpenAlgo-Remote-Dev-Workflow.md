# 🚀 OpenAlgo Remote Dev Workflow (Docker + Windows PowerShell + Live Strategy Editing)

A production-grade, end-to-end workflow to manage OpenAlgo strategy development from Windows (VSCode) to a Dockerized Debian server with deterministic deployment, live strategy access, and clean automation commands.

This system is designed for:

* ⚡ Fast iteration in trading strategy development
* 🔁 Repeatable deployment without manual panel usage
* 🧠 Stable Docker-volume-based execution model
* 🖥️ VSCode-first development experience
* 🔐 SSH + SCP controlled deployment flow

---

# 🧭 Architecture Overview

```
Windows (VSCode)
      ↓
PowerShell (oa-set)
      ↓
SSH + SCP
      ↓
Debian Server (OpenAlgo)
      ↓
Docker Container (openalgo-web)
      ↓
/app/strategies/scripts
      ↓
Live strategy execution process
```

---

# 📦 1. FINAL CANONICAL: `openalgo-mount`

## 🎯 Purpose

Creates a stable, developer-friendly bind mount from Docker-managed OpenAlgo strategy volume to a clean Linux workspace:

```
/opt/openalgo-strategies
```

This ensures:

* Upgrade-safe access to Docker volume
* Clean VSCode browsing path
* Stable external development directory
* Persistent `/etc/fstab` mount registration

---

## ⚙️ Implementation (FINAL)

```bash
# OpenAlgo Docker Volume Mount (SUDO SAFE VERSION)
openalgo-mount() {
    local container="openalgo-web"
    local target="/opt/openalgo-strategies"

    echo "[OpenAlgo] Resolving live container mount..."

    # 1. Resolve current strategies mount from container
    local source=$(docker inspect "$container" \
        --format '{{range .Mounts}}{{if eq .Destination "/app/strategies"}}{{.Source}}{{end}}{{end}}')

    if [ -z "$source" ]; then
        echo "[ERROR] Cannot resolve /app/strategies mount from container"
        return 1
    fi

    echo "[OpenAlgo] Active source: $source"

    # 2. Ensure target directory exists (sudo required)
    if [ ! -d "$target" ]; then
        sudo mkdir -p "$target"
    fi

    # 3. Check current mount
    local current=$(findmnt -n -o SOURCE --target "$target" 2>/dev/null)

    if [ "$current" == "$source" ]; then
        echo "[OpenAlgo] Mount already correct."
    else
        echo "[OpenAlgo] Updating bind mount..."

        # safely unmount if needed
        if mountpoint -q "$target"; then
            sudo umount "$target"
        fi

        sudo mount --bind "$source" "$target"
        echo "[OpenAlgo] Mounted: $source → $target"
    fi

    # 4. Update /etc/fstab safely (requires sudo)
    echo "[OpenAlgo] Syncing /etc/fstab..."

    sudo sed -i '\|/opt/openalgo-strategies|d' /etc/fstab
    echo "$source $target none bind 0 0" | sudo tee -a /etc/fstab > /dev/null

    echo "[OpenAlgo] fstab updated."

    # 5. Verify
    echo "[OpenAlgo] Verification:"
    findmnt "$target"
}
```

---

## 🧠 Key Behavior

| Feature            | Behavior                       |
| ------------------ | ------------------------------ |
| Source detection   | Dynamic via Docker inspect     |
| Target path        | `/opt/openalgo-strategies`     |
| Persistence        | `/etc/fstab` updated safely    |
| Safety             | Idempotent mount logic         |
| Upgrade resilience | Works across volume recreation |

---

# 📤 2. FINAL CANONICAL: `oa-set` (PowerShell)

## 🎯 Purpose

A Windows-side global command to:

* Upload local strategy file
* Automatically detect latest active OpenAlgo strategy on server
* Overwrite active `.py` file (NOT `.bak`)
* Maintain deterministic deployment behavior

---

## ⚙️ Implementation (FINAL)

```powershell
function oa-set {

    param (
        [string]$LocalFile
    )

    # =========================
    # OpenAlgo CONFIG
    # =========================
    $OA_USER = "admin"
    $OA_HOST = "SERVER_PUBLIC_IP"
    $OA_KEY  = "C:\Users\Manoj\.ssh\DebianPairKey.Pem"

    $OA_REMOTE_DIR = "/opt/openalgo-strategies/scripts"

    Write-Host "[OpenAlgo] Upload starting..." -ForegroundColor Cyan

    # -------------------------
    # Validate local file
    # -------------------------
    if (-not $LocalFile -or -not (Test-Path $LocalFile)) {
        Write-Host "[ERROR] Invalid or missing file: $LocalFile" -ForegroundColor Red
        return
    }

    # -------------------------
    # Resolve latest active strategy on server
    # -------------------------
    Write-Host "[OpenAlgo] Resolving latest active strategy..." -ForegroundColor Yellow

    $remoteFile = ssh -i $OA_KEY "$OA_USER@$OA_HOST" `
        "ls -1t $OA_REMOTE_DIR/BuyerEdgeStrategy_*.py 2>/dev/null | head -n 1"

    if (-not $remoteFile) {
        Write-Host "[ERROR] No active BuyerEdgeStrategy_*.py found" -ForegroundColor Red
        return
    }

    Write-Host "[OpenAlgo] Target: $remoteFile" -ForegroundColor Green

    # -------------------------
    # Upload (overwrite active file)
    # -------------------------
    scp -i $OA_KEY $LocalFile "${OA_USER}@${OA_HOST}:$remoteFile"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Upload failed" -ForegroundColor Red
        return
    }

    Write-Host "[OpenAlgo] Upload complete → $remoteFile" -ForegroundColor Green
}
```

---

## 🧠 Key Behavior

| Feature           | Behavior                               |
| ----------------- | -------------------------------------- |
| Target resolution | Always latest `BuyerEdgeStrategy_*.py` |
| Safety filter     | `.bak` files ignored                   |
| Transfer method   | SCP over SSH key                       |
| Deployment model  | Overwrite active execution file        |
| Execution trigger | Manual restart via OpenAlgo UI         |

---

# 🧪 End-to-End Workflow

## 1. Server Setup (one-time)

```bash
openalgo-mount
```

---

## 2. Development (Windows + VSCode)

Edit locally:

```
BuyerEdgeStrategy_local.py
```

---

## 3. Deploy to OpenAlgo

```powershell
oa-set .\BuyerEdgeStrategy_local.py
```

---

## 4. Execution

Restart strategy from OpenAlgo UI:

* new code is loaded
* old process replaced

---

# ⚠️ Known Behavior (Important)

| Area               | Behavior                                        |
| ------------------ | ----------------------------------------------- |
| Live editing       | NOT supported (Python process memory isolation) |
| Hot reload         | Not enabled by default                          |
| `.bak` files       | Safe historical snapshots                       |
| Strategy execution | File-based per process start                    |

---

# 🧯 Troubleshooting

### ❌ SCP failure

* Check SSH key path
* Verify server IP
* Ensure port 22 open

---

### ❌ Remote file not found

* Ensure OpenAlgo has created active `.py`
* Run `openalgo-mount` first

---

### ❌ Mount issues

* Always rerun:

```bash
openalgo-mount
```

---

# 📁 Suggested Markdown File Name

Best production naming options:

### ⭐ Recommended

```
openalgo-remote-dev-workflow.md
```

### Alternatives

```
openalgo-docker-strategy-dev-guide.md
openalgo-trading-strategy-deployment-pipeline.md
openalgo-vscode-ssh-workflow.md
openalgo-infra-automation-guide.md
```

---

# 🚀 Result

You now have a fully structured system:

* Docker-aware server mount layer
* Windows PowerShell deployment CLI
* Deterministic strategy overwrite pipeline
* Clean VSCode-based development loop
* Upgrade-safe architecture

