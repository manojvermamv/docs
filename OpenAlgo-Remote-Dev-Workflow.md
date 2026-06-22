# 🚀 OpenAlgo Remote Dev Workflow (Docker + Windows PowerShell)

A production-grade, end-to-end workflow to manage OpenAlgo strategy development from Windows (VSCode) to a Dockerized Linux server with deterministic deployment, live strategy access, and clean automation commands.

This system is designed for:

* ⚡ Fast iteration in trading strategy development
* 🔁 Repeatable deployment without manual panel usage
* 🧠 Stable Docker-volume-based execution model
* 🖥️ VSCode-first development experience
* 🔐 SSH + SCP controlled deployment flow
* 🗄 Docker-managed volumes

---

## 🧭 Architecture Overview

```tree
Windows (VSCode)
      ↓
PowerShell (oa-set / oa-logs)
      ↓
SSH + SCP
      ↓
Linux Server (OpenAlgo)
      ↓
Docker Container (openalgo-web)
      ↓
/app/strategies/scripts & /app/log
      ↓
Live strategy execution & logging
```

---

## ⚙️ 1. Setup & Installation

### Linux Server Setup (`openalgo-mount`)

#### 🎯 Purpose

Creates a stable, developer-friendly bind mount from Docker-managed OpenAlgo strategy and log volumes to a clean Linux workspace:
* `/opt/openalgo-strategies`
* `/opt/openalgo-logs`

This ensures upgrade-safe access, a clean VSCode browsing path, and persistent `/etc/fstab` registration.

#### ⚙️ Implementation

Add this function to your server's `~/.bashrc`:
* `nano ~/.bashrc`
* `source ~/.bashrc` in the server terminal to apply the changes.

```bash
# OpenAlgo Docker Volume Mount (STRATEGIES + LOGS)
openalgo-mount() {

    local container="openalgo-web"

    local strategy_target="/opt/openalgo-strategies"
    local log_target="/opt/openalgo-logs"

    echo "[OpenAlgo] Resolving live container mounts..."

    # =========================
    # 1. STRATEGY SOURCE
    # =========================
    local strategy_source=$(docker inspect "$container" \
        --format '{{range .Mounts}}{{if eq .Destination "/app/strategies"}}{{.Source}}{{end}}{{end}}')

    if [ -z "$strategy_source" ]; then
        echo "[ERROR] Cannot resolve /app/strategies mount"
        return 1
    fi

    echo "[OpenAlgo] Strategy source: $strategy_source"

    # =========================
    # 2. LOG SOURCE
    # =========================
    local log_source=$(docker inspect "$container" \
        --format '{{range .Mounts}}{{if eq .Destination "/app/log"}}{{.Source}}{{end}}{{end}}')

    if [ -z "$log_source" ]; then
        echo "[ERROR] Cannot resolve /app/log mount"
        return 1
    fi

    echo "[OpenAlgo] Log source: $log_source"

    # =========================
    # 3. CREATE DIRECTORIES
    # =========================
    sudo mkdir -p "$strategy_target"
    sudo mkdir -p "$log_target"

    # =========================
    # 4. STRATEGY MOUNT (SAFE)
    # =========================
    if mountpoint -q "$strategy_target"; then
        current_strategy=$(findmnt -n -o SOURCE --target "$strategy_target")

        if [ "$current_strategy" != "$strategy_source" ]; then
            echo "[OpenAlgo] Remounting strategies..."
            sudo umount "$strategy_target"
            sudo mount --bind "$strategy_source" "$strategy_target"
        else
            echo "[OpenAlgo] Strategy mount already correct."
        fi
    else
        sudo mount --bind "$strategy_source" "$strategy_target"
    fi

    echo "[OpenAlgo] Strategy mounted → $strategy_target"

    # =========================
    # 5. LOG MOUNT (SAFE)
    # =========================
    if mountpoint -q "$log_target"; then
        current_log=$(findmnt -n -o SOURCE --target "$log_target")

        if [ "$current_log" != "$log_source" ]; then
            echo "[OpenAlgo] Remounting logs..."
            sudo umount "$log_target"
            sudo mount --bind "$log_source" "$log_target"
        else
            echo "[OpenAlgo] Log mount already correct."
        fi
    else
        sudo mount --bind "$log_source" "$log_target"
    fi

    echo "[OpenAlgo] Logs mounted → $log_target"

    # =========================
    # 6. FSTAB SYNC (CLEAN)
    # =========================
    echo "[OpenAlgo] Syncing /etc/fstab..."

    sudo sed -i '\|/opt/openalgo-strategies|d' /etc/fstab
    sudo sed -i '\|/opt/openalgo-logs|d' /etc/fstab

    echo "$strategy_source $strategy_target none bind 0 0" | sudo tee -a /etc/fstab > /dev/null
    echo "$log_source $log_target none bind 0 0" | sudo tee -a /etc/fstab > /dev/null

    # =========================
    # 7. SYSTEMD SYNC FIX
    # =========================
    sudo systemctl daemon-reload

    # =========================
    # 8. VERIFICATION
    # =========================
    echo "[OpenAlgo] Verification:"

    findmnt "$strategy_target"
    findmnt "$log_target"
}
```

#### 🧠 Key Behavior

| Feature            | Behavior                       |
| ------------------ | ------------------------------ |
| Source detection   | Dynamic via Docker inspect     |
| Target path        | `/opt/openalgo-strategies` & logs |
| Persistence        | `/etc/fstab` updated safely    |
| Safety             | Idempotent mount logic         |
| Upgrade resilience | Works across volume recreation |

---

## 🔧 2. Configuration (Windows)

Add these functions to your Windows PowerShell `$PROFILE` (`C:\Users\Manoj\Documents\WindowsPowerShell\profile.ps1`).
* `notepad $PROFILE.CurrentUserAllHosts` to open the profile.
* `. $PROFILE.CurrentUserAllHosts` to apply changes to the current session.

### Deployment CLI (`oa-set`)

#### 🎯 Purpose

A Windows-side global command to:
* Upload local strategy file
* Automatically detect latest active OpenAlgo strategy on server
* Overwrite active `.py` file (NOT `.bak`)
* Maintain deterministic deployment behavior

#### ⚙️ Implementation

```powershell
function oa-set {

    param (
        [string]$LocalFile
    )

    if ($global:oa_upload_lock) {
        Write-Host "Upload already running"
        return
    }
    $global:oa_upload_lock = $true

    try {
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

        $remoteFile = ssh -o ConnectTimeout=5 -i $OA_KEY "${OA_USER}@${OA_HOST}" `
            "ls -1t $OA_REMOTE_DIR/BuyerEdgeStrategy_*.py 2>/dev/null | head -n 1"

        if (-not $remoteFile) {
            Write-Host "[ERROR] No active BuyerEdgeStrategy_*.py found" -ForegroundColor Red
            return
        }

        Write-Host "[OpenAlgo] Target: $remoteFile" -ForegroundColor Green

        # -------------------------
        # Upload (overwrite active file)
        # -------------------------
        scp -o ConnectTimeout=5 -i $OA_KEY $LocalFile "${OA_USER}@${OA_HOST}:$remoteFile"

        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Upload failed" -ForegroundColor Red
            return
        }

        Write-Host "[OpenAlgo] Upload complete → $remoteFile" -ForegroundColor Green
    }
    finally {
        $global:oa_upload_lock = $false
    }
}
```

#### 🧠 Key Behavior

| Feature           | Behavior                               |
| ----------------- | -------------------------------------- |
| Target resolution | Always latest `BuyerEdgeStrategy_*.py` |
| Safety filter     | `.bak` files ignored                   |
| Transfer method   | SCP over SSH key                       |
| Deployment model  | Overwrite active execution file        |

---

### Log Monitor CLI (`oa-logs`)

Quickly fetch, tail, list, or download OpenAlgo execution logs straight from your Windows terminal.

```powershell
function oa-logs {

    param (
        [string]$Mode = "latest"
    )

    # =========================
    # CONFIG
    # =========================
    $OA_USER = "admin"
    $OA_HOST = "SERVER_PUBLIC_IP"
    $OA_KEY  = "C:\Users\Manoj\.ssh\DebianPairKey.Pem"
    $CONTAINER_LOG_DIR = "/opt/openalgo-logs/strategies"

    Write-Host "[OpenAlgo] Log mode: $Mode" -ForegroundColor Cyan

    # =========================
    # Resolve latest log file
    # =========================
    $latestLog = ssh -o ConnectTimeout=5 -i $OA_KEY "${OA_USER}@${OA_HOST}" `
        "ls -1t $CONTAINER_LOG_DIR/*.log 2>/dev/null | head -n 1"

    if (-not $latestLog) {
        Write-Host "[ERROR] No log files found" -ForegroundColor Red
        return
    }

    # =========================
    # MODE: latest file content
    # =========================
    if ($Mode -eq "latest") {

        Write-Host "[OpenAlgo] Showing latest log: $latestLog" -ForegroundColor Green

        ssh -o ConnectTimeout=5 -i $OA_KEY "${OA_USER}@${OA_HOST}" `
            "tail -n 200 $latestLog"

        return
    }

    # =========================
    # MODE: live streaming
    # =========================
    if ($Mode -eq "tail") {

        Write-Host "[OpenAlgo] Tailing live logs..." -ForegroundColor Yellow

        ssh -o ConnectTimeout=5 -i $OA_KEY "${OA_USER}@${OA_HOST}" `
            "tail -f $latestLog"

        return
    }

    # =========================
    # MODE: list all logs
    # =========================
    if ($Mode -eq "list") {

        ssh -o ConnectTimeout=5 -i $OA_KEY "${OA_USER}@${OA_HOST}" `
            "ls -lt $CONTAINER_LOG_DIR"

        return
    }

    # =========================
    # MODE: download logs locally
    # =========================
    if ($Mode -eq "download") {

        $localPath = ".\openalgo-logs"

        if (!(Test-Path $localPath)) {
            New-Item -ItemType Directory -Path $localPath | Out-Null
        }

        Write-Host "[OpenAlgo] Downloading logs..." -ForegroundColor Cyan

	    scp -o ConnectTimeout=5 -i $OA_KEY "${OA_USER}@${OA_HOST}:$latestLog" $localPath

        Write-Host "[OpenAlgo] Logs saved to $localPath" -ForegroundColor Green
        return
    }

    Write-Host "[ERROR] Unknown mode. Use: latest | tail | list | download" -ForegroundColor Red
}
```

#### 🧠 Key Behavior

| Feature           | Behavior                               |
| ----------------- | -------------------------------------- |
| Target resolution | Automatically finds latest `.log` file |
| Interaction Modes | `latest`, `tail`, `list`, `download`   |
| Connectivity      | Native SSH execution                   |

---

## 🚀 3. Usage & Examples

### Step 1: Server Setup (One-time execution)
Run on the Linux server to initialize the mounts.
```bash
openalgo-mount
```

### Step 2: Development (Windows + VSCode)
Edit your strategy locally in VSCode:
```
C:\Users\Manoj\Desktop\Office_2016\OA\strategies\examples\BuyerEdgeStrategy.py
```

### Step 3: Deployment
Upload your code to the server using the PowerShell function:
```powershell
oa-set .\BuyerEdgeStrategy.py
# OR
oa-set C:\Users\Manoj\Desktop\Office_2016\OA\strategies\examples\BuyerEdgeStrategy.py
```

### Step 4: Execution
Restart the strategy from the **OpenAlgo Web UI** to ensure the new file is loaded into the Python process memory.

### Step 5: Log Monitoring
Monitor strategy execution logs from PowerShell:

| Command | Action |
|---------|--------|
| `oa-logs` | Fetch the last 200 lines of the latest log file. |
| `oa-logs tail` | Stream the latest log file live. |
| `oa-logs list` | List all log files on the server. |
| `oa-logs download` | Download the latest log file to `.\openalgo-logs`. |

---

## ⚠️ 4. Known Behaviors (Important)

| Area | Behavior |
|------|----------|
| **Live editing** | NOT supported. Python process memory isolates loaded modules. |
| **Hot reload** | Not enabled by default. Requires strategy restart via UI. |
| **`.bak` files** | Ignored by deployment script. Preserved as historical snapshots. |
| **Strategy execution** | File-based execution upon process start. |

---

## 🧯 5. Troubleshooting

### ❌ SCP or SSH Failure
* Check SSH key path (`C:\Users\Manoj\.ssh\DebianPairKey.Pem`).
* Verify server IP (`SERVER_PUBLIC_IP`).
* Ensure Port 22 is open and the network is reachable.

### ❌ Remote File Not Found during `oa-set`
* Ensure the strategy has been created and run at least once in the OpenAlgo UI to generate the `.py` file.
* Run `openalgo-mount` on the Linux server to ensure the directory is mapped.

### ❌ Mount Issues on Server
* Always try remounting using the bash function:
```bash
openalgo-mount
```
* Verify mounts explicitly:
```bash
findmnt /opt/openalgo-strategies
findmnt /opt/openalgo-logs
```

---

## 📚 6. References
* OpenAlgo Official Documentation
* Docker Volumes Documentation
* SSH/SCP Key-based Authentication Guide

---

## 📥 Download Trade Journal (`trades.csv`)
To securely download your `trades.csv` journal directly from the running OpenAlgo Docker container, run the following command in PowerShell:

```powershell
ssh -i "C:\Users\Manoj\.ssh\DebianPairKey.pem" admin@SERVER_PUBLIC_IP "docker exec openalgo-web cat /app/trades.csv" > trades.csv
