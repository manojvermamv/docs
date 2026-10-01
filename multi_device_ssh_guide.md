# Multi-Device SSH Key Architecture Guide (Cloud & EC2)

A production-grade, minimal, copy-pasteable reference for establishing and maintaining secure SSH access across multiple client devices and multiple cloud servers without sharing private keys.

---

## 🏗️ 1. Architecture & Security Model

### The Core Principle
> [!CAUTION]
> **Never copy or share private keys between devices unless intentionally choosing a shared-key model.**
> Each physical client generates its own private key that never leaves that machine. Only public keys (`.pub`) are copied to destination servers. If any device is lost, replaced, or compromised, revoke its public key immediately on the server.

### Architecture Diagram

> [!NOTE]
> **Selective Access**: Not every client must connect to every server. Access is granted strictly on a per-key basis. For example, mobile phones may be granted access only to dev/staging, while office machines access both.

```mermaid
flowchart LR
    subgraph Clients["Client Devices (Private Keys Stored Locally)"]
        W_Off["Office Windows\n<KEY_OFFICE_UBUNTU>\n<KEY_OFFICE_DEBIAN>"]
        W_Per["Personal Windows / Laptop\n<KEY_LAPTOP_UBUNTU>\n<KEY_LAPTOP_DEBIAN>"]
        Mac["macOS / Linux Desktop\n<KEY_DESKTOP_UBUNTU>"]
        And["Android Phone (Termux)\n<KEY_PHONE_UBUNTU>"]
    end

    subgraph ServerUbuntu["Destination: Ubuntu Instance (<UBUNTU_HOST>)"]
        U_Auth["User: <UBUNTU_USER> (e.g. ubuntu)\n~/.ssh/authorized_keys\n- office-key\n- laptop-key\n- desktop-key\n- phone-key"]
    end

    subgraph ServerDebian["Destination: Debian Instance (<DEBIAN_HOST>)"]
        D_Auth["User: <DEBIAN_USER> (e.g. admin)\n~/.ssh/authorized_keys\n- office-key\n- laptop-key"]
    end

    W_Off -->|Authorized| U_Auth
    W_Off -->|Authorized| D_Auth
    W_Per -->|Authorized| U_Auth
    W_Per -->|Authorized| D_Auth
    Mac -->|Authorized| U_Auth
    And -->|Authorized (Selective)| U_Auth
    %% Note: Phone and Desktop do not connect to Debian
```

### Choosing Your Key Isolation Model

| Model | Setup | Best For |
| :--- | :--- | :--- |
| **Per-Device Key** (Recommended default) | 1 key pair per physical device, reused across your own accessible servers | Balances strong security with minimal key management overhead. |
| **Per-Device-Per-Server Key** (Maximum isolation) | Dedicated key pair for each (Device + Server) combination | Limits credential reuse between servers so that access credentials for one environment are not shared with another. |

---

## 🤖 2. AI Agent Interactive Setup / "Grill-Me" Protocol

When an AI coding assistant or autonomous agent performs this setup with a user, it **must not blindly execute scripts with placeholder assumptions**. The agent must conduct a brief interrogation to collect actual environment values and run automated safety checks before touching the filesystem.

### Agent Interrogation Checklist (Collect First)
The agent asks the user only the essential parameters:
1. **Client Device & OS**: Windows PowerShell, macOS/Linux terminal, or Android Termux?
2. **Device / Machine Name**: What identifier should be used in key names and comments? (e.g. `office-win`, `personal-laptop`).
3. **Live Target Server**: Which server is being configured? (e.g. AWS Ubuntu EC2, Debian instance).
4. **Server Hostname or IP**: Exact public IP or public DNS name.
5. **SSH Username**: Exact login account on that server (e.g. `ubuntu`, `admin`, or custom).
6. **Desired SSH Alias**: Shorthand connection name for `~/.ssh/config` (e.g. `ec2-ubuntu`).
7. **Key Isolation Preference**: One key per device, or one key per device-per-server?

### Automated Agent Pre-Flight Safety Checks (Check Automatically When Possible)
Before creating keys or modifying configurations, the agent must verify:
- [ ] **Anti-Lockout Check**: Confirm the user has fallback access available (such as an active working SSH session, AWS EC2 Instance Connect, EC2 Serial Console, or AWS Systems Manager Session Manager) before changing `authorized_keys`.
- [ ] **Key Collision Check**: Test whether the proposed private key file (e.g. `~/.ssh/<KEY_FILENAME>`) already exists. If it exists, alert the user rather than overwriting.
- [ ] **SSH Config Collision Check**: Inspect client `~/.ssh/config` to check if `Host <ALIAS>` is already defined. If present, edit the existing block rather than appending a duplicate.
- [ ] **Windows Permission Verification**: On Windows, check actual file ACLs with `Get-Acl` or `icacls` before assuming permissions are too broad.
- [ ] **Safe Defaults**: Assume Ed25519 algorithm, standard permissions (`700`/`600`), and `IdentitiesOnly yes`. Use empty passphrase only when unattended/non-interactive access is intentionally required; otherwise ask if the user prefers a passphrase. Skip minor setup questions unless an issue arises.

---

## 📋 3. Setup Planning Worksheet

| Field | Description | Example Value |
| :--- | :--- | :--- |
| **Key Isolation Model** | Choose `Per-device` or `Per-device-per-server` | `Per-device-per-server` |
| **Client OS** | Windows / macOS / Linux / Android Termux | `Windows (PowerShell)` |
| **Device Label** | Unique name of your physical machine | `office-win` or `personal-laptop` |
| **Target Server Host** | Public IP address or Public DNS hostname | `<SERVER_IP>` or `<PUBLIC_DNS_NAME>` |
| **SSH Username** | Typical/default for the selected AMI (`ubuntu` for Ubuntu, `admin` for Debian) or custom account | `ubuntu` |
| **Key Filename** | Name for this specific private key | `id_ed25519_ubuntu_laptop` |
| **Key Comment** | Recommended to be unique to identify and safely revoke this key | `laptop-to-ec2-ubuntu-2026` |
| **SSH Alias** | 1-word shortcut name | `ec2-ubuntu` |
| **Existing SSH Config?** | Does `~/.ssh/config` already exist on your client? | `Yes` (edit) / `No` (create) |

---

## 🔒 4. Server-Side Setup (Cloud Instance)

> [!WARNING]
> **Anti-Lockout Rule**: Always keep your current, working SSH connection open in one terminal while configuring or updating `authorized_keys`. Test new keys in a **second, separate terminal window** before closing your active session.

### Step 1: Initialize Directory & Lock Permissions

Log into your server. (Typical AMI defaults are `ubuntu` on standard Ubuntu AMIs and `admin` on standard Debian AMIs):

```bash
# 1. Initialize .ssh with 700 (rwx------) and authorized_keys with 600 (rw-------)
mkdir -p ~/.ssh && chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys

# 2. Confirm ownership for the target account (essential if commands were run via sudo or root)
# Recommended dynamic form (resolves user and primary group automatically):
sudo chown -R $(id -un):$(id -gn) ~/.ssh

# Or specify explicitly if configuring another user account:
sudo chown -R <SSH_USER>:<SSH_GROUP> /home/<SSH_USER>/.ssh
```

### Step 2: Idempotent Key Installation (Prevents Duplicates)

Never append blindly. Avoid adding the same public key multiple times by using this check:

```bash
PUB_KEY='<PASTE_PUBLIC_KEY_STRING_HERE>'

grep -qxF "$PUB_KEY" ~/.ssh/authorized_keys || echo "$PUB_KEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

## 💻 5. Client-Side Setup (By Device)

> [!TIP]
> **Passphrase Policy**: The standard commands below run interactively so you can set a passphrase for added security. If an unattended, non-interactive setup is intentionally required, add `-N ""` to bypass the interactive prompt:
> `ssh-keygen -t ed25519 -C "<UNIQUE_COMMENT>" -f "<KEY_PATH>" -N ""`

### A. Windows (PowerShell)

> [!NOTE]
> **Windows File Permissions**: OpenSSH on Windows may reject the private key when NTFS ACL permissions are too broad (e.g. inherited access granted to `BUILTIN\Users`). Verify permissions on the key file using `icacls "$HOME\.ssh\<KEY_FILENAME>"`. If inherited access or multiple users are listed, use `icacls` to remove inheritance and grant exclusive Read access to your Windows user account.

Run this **combined block** in PowerShell (replace `<KEY_FILENAME>` and `<UNIQUE_COMMENT>`):

```powershell
# 1. Create .ssh folder
New-Item -ItemType Directory -Force -Path "$HOME\.ssh" | Out-Null

# 2. Generate ed25519 key interactively (press Enter twice for no passphrase, or enter a passphrase)
ssh-keygen -t ed25519 -C "<UNIQUE_COMMENT>" -f "$HOME\.ssh\<KEY_FILENAME>"

# 3. Restrict NTFS permissions if needed
icacls "$HOME\.ssh\<KEY_FILENAME>" /inheritance:r | Out-Null
icacls "$HOME\.ssh\<KEY_FILENAME>" /grant:r "$($env:USERNAME):(R)" | Out-Null

# 4. Display public key to copy to server
Write-Host "`n=== COPY THIS PUBLIC KEY TO SERVER authorized_keys ===" -ForegroundColor Green
Get-Content "$HOME\.ssh\<KEY_FILENAME>.pub"
```

---

### B. Linux / macOS (Bash or Zsh)

Run this **combined block** in terminal:

```bash
# 1. Create .ssh directory with 700 permissions
mkdir -p ~/.ssh && chmod 700 ~/.ssh

# 2. Generate ed25519 key with a unique comment
ssh-keygen -t ed25519 -C "<UNIQUE_COMMENT>" -f ~/.ssh/<KEY_FILENAME>

# 3. Lock private key permissions to 600
chmod 600 ~/.ssh/<KEY_FILENAME>

# 4. Display public key to copy to server
echo -e "\n=== COPY THIS PUBLIC KEY TO SERVER authorized_keys ==="
cat ~/.ssh/<KEY_FILENAME>.pub
```

---

### C. Android (Termux)

Run this **combined block** in Termux:

```bash
# 1. Install OpenSSH package if missing
pkg update -y && pkg install -y openssh

# 2. Create .ssh directory and generate key
mkdir -p ~/.ssh && chmod 700 ~/.ssh
ssh-keygen -t ed25519 -C "<UNIQUE_COMMENT>" -f ~/.ssh/<KEY_FILENAME>
chmod 600 ~/.ssh/<KEY_FILENAME>

# 3. Display public key to copy to server
echo -e "\n=== COPY THIS PUBLIC KEY TO SERVER ==="
cat ~/.ssh/<KEY_FILENAME>.pub
```

---

## ⚡ 6. Client SSH Config (One-Word Shortcuts)

Configuring `~/.ssh/config` allows you to connect with simple commands like `ssh ec2-ubuntu` instead of typing out IP addresses and `-i` flags.

> [!WARNING]
> **Check Before Appending**: The snippets below append to `~/.ssh/config`. If you already have an entry for that `Host`, do not blindly rerun the append block as it will create duplicate definitions. Open the file in an editor (`notepad` or `nano`) and update the existing entry.

### Configuration Best Practices:
1. **`HostName`**: Contains only the IP address (e.g. `<SERVER_IP>`) or public DNS hostname (e.g. `ec2-xxx.compute.amazonaws.com`). Do **not** prefix with `user@`.
2. **`User`**: Specifies the remote username (e.g. `ubuntu` or `admin`).
3. **`IdentitiesOnly yes`**: Recommended when multiple SSH keys or an SSH agent exist. It instructs SSH to use only the key specified in `IdentityFile`, preventing connection failures caused by exhausting the server's `MaxAuthTries` with other loaded keys.

---

### Configuration Snippets

#### On Windows (PowerShell)
```powershell
$configPath = "$HOME\.ssh\config"
$aliasesToCheck = @("ec2-ubuntu", "ec2-debian")
$existingAliases = @()

if (Test-Path $configPath) {
    foreach ($alias in $aliasesToCheck) {
        if (Select-String -Path $configPath -Pattern "^\s*Host\s+.*\b$alias\b" -Quiet) {
            $existingAliases += $alias
        }
    }
}

if ($existingAliases.Count -gt 0) {
    Write-Warning "Existing Host entries found in $configPath for: $($existingAliases -join ', '). Edit the file manually to prevent duplicate blocks."
} else {
    @'

# Ubuntu Instance
Host ec2-ubuntu
    HostName <UBUNTU_IP_OR_DNS>
    User <UBUNTU_USER>
    IdentityFile ~/.ssh/<UBUNTU_KEY_FILENAME>
    IdentitiesOnly yes

# Debian Instance
Host ec2-debian
    HostName <DEBIAN_IP_OR_DNS>
    User <DEBIAN_USER>
    IdentityFile ~/.ssh/<DEBIAN_KEY_FILENAME>
    IdentitiesOnly yes
'@ | Out-File -Append -Encoding ascii $configPath
    Write-Host "Config entries appended successfully." -ForegroundColor Green
}
```

#### On Linux / macOS
```bash
CONFIG="$HOME/.ssh/config"
touch "$CONFIG" && chmod 600 "$CONFIG"

# POSIX-compliant check for existing Host aliases
if grep -Eq '^[[:space:]]*Host[[:space:]]+([^#]*[[:space:]])?(ec2-ubuntu|ec2-debian)([[:space:]]|$)' "$CONFIG"; then
    echo "WARNING: One or more target Host aliases already exist in $CONFIG. Edit manually to prevent duplicate blocks."
else
    cat << 'EOF' >> "$CONFIG"

# Ubuntu Instance
Host ec2-ubuntu
    HostName <UBUNTU_IP_OR_DNS>
    User <UBUNTU_USER>
    IdentityFile ~/.ssh/<UBUNTU_KEY_FILENAME>
    IdentitiesOnly yes

# Debian Instance
Host ec2-debian
    HostName <DEBIAN_IP_OR_DNS>
    User <DEBIAN_USER>
    IdentityFile ~/.ssh/<DEBIAN_KEY_FILENAME>
    IdentitiesOnly yes
EOF
    chmod 600 "$CONFIG"
    echo "Config entries appended successfully."
fi
```

#### On Android (Termux)
```bash
CONFIG="$HOME/.ssh/config"
touch "$CONFIG" && chmod 600 "$CONFIG"

# POSIX-compliant check for existing Host aliases
if grep -Eq '^[[:space:]]*Host[[:space:]]+([^#]*[[:space:]])?(ec2-ubuntu|ec2-debian)([[:space:]]|$)' "$CONFIG"; then
    echo "WARNING: One or more target Host aliases already exist in $CONFIG. Edit manually to prevent duplicate blocks."
else
    cat << 'EOF' >> "$CONFIG"

# Ubuntu Instance
Host ec2-ubuntu
    HostName <UBUNTU_IP_OR_DNS>
    User <UBUNTU_USER>
    IdentityFile ~/.ssh/<TERMUX_UBUNTU_KEY>
    IdentitiesOnly yes

# Debian Instance
Host ec2-debian
    HostName <DEBIAN_IP_OR_DNS>
    User <DEBIAN_USER>
    IdentityFile ~/.ssh/<TERMUX_DEBIAN_KEY>
    IdentitiesOnly yes
EOF
    chmod 600 "$CONFIG"
    echo "Config entries appended successfully."
fi
```

---

## ✅ 7. Step-by-Step Verification Pipeline

Verify each stage in sequence before moving to the next:

```
[1. Key Generated] ──► [2. Public Key Copied] ──► [3. Server Installed]
                                                           │
[6. Alias Connected] ◄── [5. Direct Connected] ◄── [4. Permissions Verified]
```

### Verification Steps:

1. **Step 1 — Verify Local Key Creation**:
   Confirm both the private key (`<KEY_FILENAME>`) and public key (`<KEY_FILENAME>.pub`) exist in `~/.ssh/`.
2. **Step 2 — Client-Side Permissions**:
   - **Windows**: Check permissions with `icacls` if OpenSSH rejects the key.
   - **Linux / macOS / Termux**: Run `ls -l ~/.ssh/<KEY_FILENAME>` and confirm `-rw-------` (`600`).
3. **Step 3 — Server-Side Key Presence**:
   On the server, confirm the key string exists in `~/.ssh/authorized_keys`.
4. **Step 4 — Server-Side Permissions**:
   On the server, confirm permissions:
   ```bash
   ls -ld ~/.ssh ~/.ssh/authorized_keys
   # Required:
   # drwx------ ~/.ssh              (700)
   # -rw------- ~/.ssh/authorized_keys (600)
   ```
5. **Step 5 — Test Direct Connection (Bypass Alias First)**:
   Always test using direct command line parameters to isolate key issues from config file typos:
   ```bash
   # Generic syntax:
   ssh -i <PATH_TO_PRIVATE_KEY> <USER>@<HOST>

   # Ubuntu example:
   ssh -i ~/.ssh/id_ed25519_ubuntu_laptop ubuntu@<UBUNTU_IP_OR_DNS>

   # Debian example:
   ssh -i ~/.ssh/id_ed25519_debian_laptop admin@<DEBIAN_IP_OR_DNS>
   ```
6. **Step 6 — Verify No Duplicate Aliases & Test Shortcut**:
   Confirm the alias appears only once in `~/.ssh/config`, then test:
   ```bash
   ssh ec2-ubuntu
   ssh ec2-debian
   ```

---

## 🗑️ 8. Safe Key Revocation by Unique Comment

> [!NOTE]
> **Unique Comments Strongly Recommended**: Giving every key a distinct, descriptive comment (e.g. `<device>-to-<server>-<id>`) makes audit and revocation safe and simple. Do not rely on line numbers, which shift whenever keys are added or removed. If two keys share the same comment, matching tools will delete both.

### Safe Revocation Procedure (Server-Side)

When a laptop, phone, or office computer is replaced, lost, or decommissioned:

```bash
# 1. Create a timestamped backup before making any changes
cp ~/.ssh/authorized_keys ~/.ssh/authorized_keys.bak.$(date +%F_%T)

# 2. Delete the specific key matching its unique comment
sed -i '/<EXACT_UNIQUE_COMMENT>/d' ~/.ssh/authorized_keys

# 3. Ensure permissions remain correct
chmod 600 ~/.ssh/authorized_keys

# 4. Audit authorized_keys to verify only the intended key was removed
cat -n ~/.ssh/authorized_keys
```

The revoked device will be denied immediately on its next connection attempt, while all other authorized devices continue working without interruption.

---

## 🔍 9. Comprehensive Troubleshooting Matrix

### Diagnostic Mode: `ssh -vvv`
If an alias or key fails, run the connection with maximum debug logging:
```bash
ssh -vvv <ALIAS_OR_DIRECT_COMMAND>
```
Look for:
- `debug1: Will attempt key: ...` — Did SSH find and open your private key file?
- `debug1: Offering public key: ...` — Which public key is presented to the server?
- `debug1: Authentications that can continue: publickey` — Server rejected the offered key.

### Common Issues & Targeted Fixes

| Symptom | Layer | Root Cause | Targeted Solution |
| :--- | :--- | :--- | :--- |
| `Permission denied (publickey)` | **Windows Client** | NTFS ACL inheritance grants access to other groups | Check actual ACLs; run `icacls <keyfile> /inheritance:r` and `icacls <keyfile> /grant:r "$($env:USERNAME):(R)"` if permissions are too broad. |
| `Load key ... invalid format` | **Windows Client** | File was created with Windows CRLF (`\r\n`) or corrupted encoding | Generate key natively with `ssh-keygen` or write using `[IO.File]::WriteAllText("$path", "$content`n")`. |
| `Permissions ... are too open` | **Linux/macOS Client** | Client private key permissions are not restricted | Run `chmod 600 ~/.ssh/<keyfile>` and `chmod 700 ~/.ssh` on the client. |
| `Permission denied (publickey)` | **Server Side** | Server `.ssh` or `authorized_keys` permissions/ownership wrong | On the server, run `chmod 700 ~/.ssh`, `chmod 600 ~/.ssh/authorized_keys`, and `sudo chown -R $(id -un):$(id -gn) ~/.ssh`. |
| `Too many authentication failures` | **Client SSH Config** | SSH agent presents multiple keys before the correct one | Add `IdentitiesOnly yes` under the corresponding `Host` block in `~/.ssh/config`. |
| `Connection timed out` | **Network / Firewall** | Cloud Security Group or firewall blocking port 22 | Verify that the cloud security group permits inbound traffic on **Port 22** from your current public IP. |
| `Connection refused` | **Server Daemon** | SSH service stopped or listening on a non-standard port | Verify the SSH daemon status on the server (`sudo systemctl status ssh` or `sshd`). |
