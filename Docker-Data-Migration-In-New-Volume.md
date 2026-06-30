# 🚀 Production Guide: Migrate Docker Data Root to a New EBS Volume (Coolify Server)

> **Goal**
>
> Migrate Docker from the root filesystem (`/var/lib/docker`) to a dedicated EBS volume (`/data/docker`) safely, with rollback support, strict command ordering, verification after every critical step, and minimal downtime.

---

# 📌 Choose Your Approach

| Option | Recommended | Downtime | Complexity | Future-Proof |
|---------|------------|----------|------------|--------------|
| ✅ **Option 1** – Attach a new EBS volume and move Docker Data Root | ⭐⭐⭐⭐⭐ | Low | Medium | ⭐⭐⭐⭐⭐ |
| Option 2 – Increase existing Root EBS volume | ⭐⭐⭐ | None | Easy | ⭐⭐⭐ |

---

# ✅ Option 1 (Recommended)

## Production Architecture

```
30GB Root (/)
│
├── Ubuntu
├── Logs
├── Configs
├── Packages
└── System Files

50GB (/data)
│
└── Docker
    ├── Images
    ├── Containers
    ├── Volumes
    ├── Networks
    ├── PostgreSQL
    ├── Redis
    ├── Coolify
    ├── OpenCode
    ├── FileBrowser
    ├── AI Agents
    └── Future Projects
```

**Best for**

- Coolify
- PostgreSQL
- Redis
- OpenCode
- FileBrowser
- AI workloads
- MCP Servers
- Large Docker Images

---

# 🚨 STRICT ORDER (DO NOT SKIP OR REORDER)

```
1. Format disk
2. Mount disk
3. Verify mount
4. Configure /etc/fstab
5. Stop Docker completely
6. Verify Docker is stopped
7. Copy Docker data
8. Verify copied data
9. Configure daemon.json
10. Validate configuration
11. Start Docker
12. Verify Docker Root
13. Verify all containers
14. Rename old Docker directory
15. Restart Docker
16. Verify again
17. Reboot
18. Delete backup
19. Final verification
```

---

# Step 1 — Create Filesystem

> ⚠️ Skip this step if the disk already contains data.

```bash
sudo mkfs.ext4 /dev/nvme1n1
```

---

# Step 2 — Create Mount Point

```bash
sudo mkdir -p /data
```

---

# Step 3 — Mount Disk

```bash
sudo mount /dev/nvme1n1 /data
```

---

# Step 4 — Verify Mount

```bash
df -h
```

Expected

```text
/dev/nvme1n1    50G    ...    /data
```

❌ If `/data` is missing, **STOP**.

---

# Step 5 — Make Mount Persistent

Find UUID

```bash
sudo blkid /dev/nvme1n1
```

Edit

```bash
sudo nano /etc/fstab
```

Append

```text
UUID=<UUID> /data ext4 defaults,nofail 0 2
```

Test

```bash
sudo mount -a
```

Verify

```bash
df -h
```

---

# 🟠 Docker Migration

---

## Step 6 — Stop Docker Completely

⚠️ Docker **Socket** must also be stopped.

```bash
sudo systemctl stop docker.service
sudo systemctl stop docker.socket
sudo systemctl stop containerd.service
```

Verify Docker is completely stopped

```bash
ps -ef | grep dockerd
```

Expected

```text
Only grep process should appear.
```

❌ If `dockerd` is still running, **STOP**.

---

## Step 7 — Copy Docker Data

```bash
sudo rsync -aHAX --info=progress2 /var/lib/docker/ /data/docker/
```

---

## Step 8 — Verify Copied Data

```bash
sudo ls /data/docker
```

Expected

```text
buildkit
containers
engine-id
image
network
plugins
rootfs
runtimes
swarm
tmp
volumes
```

---

## Step 9 — Configure Docker

Edit

```bash
sudo nano /etc/docker/daemon.json
```

Add **data-root** as another top-level key.

```json
{
  "iptables": true,
  "ip-forward": true,
  "userland-proxy": false,
  "live-restore": true,
  "ip6tables": false,
  "data-root": "/data/docker",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-address-pools": [
    {
      "base": "172.17.0.0/12",
      "size": 24
    }
  ]
}
```

---

## Step 10 — Validate Configuration

```bash
sudo dockerd --validate --config-file /etc/docker/daemon.json
```

Expected

```text
configuration OK
```

❌ If validation fails, **STOP**.

---

## Step 11 — Start Docker

```bash
sudo systemctl start containerd
sudo systemctl start docker
```

---

## Step 12 — Verify Docker Root

```bash
docker info | grep "Docker Root Dir"
```

Expected

```text
Docker Root Dir: /data/docker
```

❌ If it still shows `/var/lib/docker`, **STOP**.

---

## Step 13 — Verify Everything

```bash
docker ps

docker system df

df -h
```

Verify

- ✅ All containers running
- ✅ Coolify loads
- ✅ OpenCode works
- ✅ FileBrowser works
- ✅ PostgreSQL healthy
- ✅ Redis healthy

---

# 🟡 Safe Recovery Point

> ⚠️ **DO NOT DELETE** the old Docker directory yet.

Rename instead.

```bash
sudo mv /var/lib/docker /var/lib/docker.backup
sudo mkdir /var/lib/docker
```

Restart Docker

```bash
sudo systemctl restart docker
```

Verify again

```bash
docker ps

docker info | grep "Docker Root Dir"
```

---

# 🚨 CRITICAL CHECKPOINT

## DO NOT CONTINUE unless ALL are true

```bash
docker info | grep "Docker Root Dir"
```

Must return

```text
Docker Root Dir: /data/docker
```

```bash
docker ps
```

Must show all expected containers.

Also verify

- ✅ Coolify
- ✅ OpenCode
- ✅ FileBrowser
- ✅ PostgreSQL
- ✅ Redis

If anything is broken:

**STOP HERE**

Do **NOT** delete `/var/lib/docker.backup`.

---

# Backup Cleanup

## If Delete Works

```bash
sudo rm -rf /var/lib/docker.backup
```

Done.

---

## If You Get

```text
Device or resource busy
```

or

```text
Directory not empty
```

This usually means old overlay mounts are still attached.

---

## Check

```bash
docker info | grep "Docker Root Dir"

sudo lsof +D /var/lib/docker.backup

sudo fuser -vm /var/lib/docker.backup

mount | grep docker.backup

mount | grep overlay
```

---

## Recommended Solution

Reboot

```bash
sudo reboot
```

Reconnect

```bash
mount | grep docker.backup
```

Expected

```text
(no output)
```

Now delete

```bash
sudo rm -rf /var/lib/docker.backup
```

---

# 🔄 Rollback

If Docker fails after migration

Stop

```bash
sudo systemctl stop docker.service
sudo systemctl stop docker.socket
sudo systemctl stop containerd.service
```

Restore

```bash
sudo rm -rf /var/lib/docker

sudo mv /var/lib/docker.backup /var/lib/docker
```

Remove

```json
"data-root": "/data/docker"
```

from

```text
/etc/docker/daemon.json
```

Start

```bash
sudo systemctl start containerd
sudo systemctl start docker
```

Verify

```bash
docker ps

docker info | grep "Docker Root Dir"
```

---

# ✅ Final Cross Verification

Run every command below.

```bash
docker info | grep "Docker Root Dir"
```

Expected

```text
Docker Root Dir: /data/docker
```

---

```bash
docker ps
```

All expected containers running.

---

```bash
docker system df
```

Docker storage reported normally.

---

```bash
df -h
```

Verify

- `/` has reclaimed space
- `/data` mounted

---

```bash
mount | grep docker.backup
```

Expected

```text
(no output)
```

---

```bash
sudo systemctl status docker --no-pager
```

Must be

```text
active (running)
```

---

```bash
sudo systemctl status containerd --no-pager
```

Must be

```text
active (running)
```

---

# Option 2 — Increase Existing Root EBS Volume

Recommended sizes

- 50GB (Minimum)
- 80GB (Recommended)
- 100GB (Future-proof)

---

## AWS Console

```
EC2
 └── Volumes
      └── Select Root Volume
           └── Actions
                └── Modify Volume
                     └── Increase Size
```

Wait until

```text
Optimizing
```

or

```text
Completed
```

---

## Verify New Disk Size

```bash
lsblk
```

Expected

```text
nvme0n1    80G
```

---

## Grow Partition

```bash
sudo growpart /dev/nvme0n1 1
```

---

## Resize Filesystem

```bash
sudo resize2fs /dev/nvme0n1p1
```

---

## Verify

```bash
df -h
```

Expected

```text
Filesystem      Size
/dev/root       ~80G
```

---

## If You See

```text
NOCHANGE: partition cannot be grown
```

It means the AWS EBS volume has **not** been resized yet.

Verify

```bash
lsblk
```

If it still shows

```text
nvme0n1    30G
```

Go back to AWS Console, wait for the volume modification to complete, then rerun:

```bash
sudo growpart /dev/nvme0n1 1

sudo resize2fs /dev/nvme0n1p1
```

---

# 🏁 Recommendation

## ✅ Option 1 (Recommended)

- Dedicated Docker storage
- Cleaner production architecture
- Easier expansion
- Better for Coolify and AI workloads
- Prevents Docker from filling the root filesystem
- Safer long-term

## Option 2

- Simpler
- Single filesystem
- Suitable for lightweight Docker hosts
- More likely to hit disk-space limits as Docker usage grows
