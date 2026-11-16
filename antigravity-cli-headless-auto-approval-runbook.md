# 🖥️ Antigravity CLI: Headless Remote Control & Auto-Approval

**Use Antigravity on your Linux server from a browser, without keeping a terminal open.**

This guide configures unattended approvals for commands, tools and file changes through [Antigravity Remote Control](https://antigravity.google.com/r/).

> [!IMPORTANT]
> These settings allow broad command, file and MCP access without approval prompts and disable the terminal sandbox. Apply them only when you intentionally want unattended execution. Linux permissions still apply; this does not grant root access.

[Plan](#plan) · [Install and sign in](#install) · [Tool grants](#grants) · [Workspace settings](#workspace) · [Verify](#verify) · [Troubleshooting](#fix)

---

<a id="plan"></a>
<a id="0-generic-environment-defaults"></a>
## 📋 1. Choose your server

| Dashboard name | Linux user | Trusted workspace |
|---|---|---|
| `debian-oa` | `admin` | `/home/admin` |
| `ubuntu-cp` | `ubuntu` | `/home/ubuntu` |

Use your actual account and workspace for other machines. The dashboard name is a label; it does not change the operating system's hostname. The examples below use Ubuntu. Substitute `debian-oa` and `/home/admin` for Debian.

**▶ Run in: the server terminal**, logged in as the intended Linux user. Do not create these files on your Windows client or run the CLI setup as root.

### If an AI assistant is doing the setup

- Inspect the existing installation, configuration and service. Reuse known answers; ask only for missing server, user and workspace choices.
- Confirm the user intends broad auto-approval; an explicit request to apply this runbook supplies that choice.
- Back up existing settings and merge changes, preserving unrelated fields and grants.
- Let the user complete sign-in locally. Keep authorization codes and tokens out of chat, logs and repository files.
- Test the service and a harmless headless command. Report any remaining blockers and checks not performed.

---

<a id="install"></a>
## 📦 2. Install or update, then sign in

**▶ Run in: the server terminal**

```bash
command -v agy
agy --version
```

If missing, download and review [Google's installer](https://antigravity.google/docs/cli/tutorial), then run it:

```bash
mkdir -p ~/.cache/agy-setup
curl -fsSL https://antigravity.google/cli/install.sh -o ~/.cache/agy-setup/install.sh
less ~/.cache/agy-setup/install.sh
bash ~/.cache/agy-setup/install.sh
```

The installer selects the platform release and checks its download checksum. If the current shell cannot find `agy`, use `~/.local/bin/agy` or open a new login shell. For an existing installation, use `agy update`, then check `agy --version`; do not assume a version recorded here is still the latest.

Start the CLI:

```bash
agy
```

Choose **Google OAuth** and follow the instructions. Open the printed link in your browser and enter any returned code in the server's terminal. CLI sign-in is separate from signing into the editor.

**You should see:** an authenticated CLI session. Exit it when finished; the background daemon is started in Step 5.

---

<a id="grants"></a>
<a id="1-configure-global-tool--command-grants"></a>
## 🔓 3. Configure tool and command grants

Grants belong under **`userSettings.globalPermissionGrants`** in `~/.gemini/config/config.json`. The daemon uses a Protobuf-backed JSON schema (`proto3 JSON`), so settings must be in the correct file and location.

**▶ Run in: the server terminal**

```bash
mkdir -p ~/.gemini/config ~/.gemini/antigravity-cli
stamp=$(date +%Y%m%d-%H%M%S)
for file in ~/.gemini/config/config.json ~/.gemini/antigravity-cli/settings.json; do
    if [ -f "$file" ]; then
        cp -p "$file" "$file.before-headless-$stamp"
    fi
done
nano ~/.gemini/config/config.json
```

Merge these fields into the existing file. For a new file, this is a complete, valid JSON example:

```json
{
  "userSettings": {
    "cliRemoteControlHostname": "ubuntu-cp",
    "enableNotificationsForSpecialEvents": false,
    "globalPermissionGrants": {
      "allow": [
        "command(*)",
        "read_file(*)",
        "write_file(*)",
        "mcp(*)",
        "read_url(raw.githubusercontent.com)"
      ]
    }
  }
}
```

| Setting | Purpose |
|---|---|
| `cliRemoteControlHostname` | Name shown in the dashboard switcher, such as `ubuntu-cp`, `debian-oa`, `ec2-prod` or `workspace-primary` |
| `enableNotificationsForSpecialEvents: false` | Disable special-event notifications |
| Four wildcard grants | Broadly allow commands, file reads, file writes and MCP tool calls |
| `read_url(raw.githubusercontent.com)` | Example of a specific URL grant; retain existing individual command/URL entries below the wildcards |

> [!WARNING]
> Preserve existing settings and allow entries. Do not replace an existing file wholesale or duplicate its `userSettings`, `globalPermissionGrants` or `allow` keys.
>
> Use strict JSON: no `...`, comments or trailing commas. Missing commas or mismatched brackets can cause `proto: syntax error`. Do not insert `artifactReviewMode`, `permissions` or `hooks` blocks into this `config.json` as part of the setup.

---

<a id="workspace"></a>
<a id="2-configure-workspace-execution-defaults"></a>
## 📁 4. Configure workspace execution defaults

**▶ Run in: the server terminal**

```bash
mkdir -p ~/.gemini/antigravity-cli
nano ~/.gemini/antigravity-cli/settings.json
```

Merge the following fields, preserving unrelated settings and existing trusted workspaces. For a new file:

```json
{
  "toolPermission": "always-proceed",
  "artifactReviewPolicy": "always-proceed",
  "allowNonWorkspaceAccess": true,
  "enableTerminalSandbox": false,
  "mode": "accept-edits",
  "trustedWorkspaces": [
    "/home/ubuntu"
  ]
}
```

| Setting | What it requests |
|---|---|
| `toolPermission` | Proceed without interactive tool approval |
| `artifactReviewPolicy` | Proceed without manual artifact review |
| `allowNonWorkspaceAccess` | Permit operations outside the current project root, subject to the Linux user's permissions |
| `enableTerminalSandbox: false` | Disable the terminal sandbox for headless execution |
| `mode: accept-edits` | Accept file edits without manual diff approval; command grants are configured separately above |
| `trustedWorkspaces` | Trust the selected directory; use `/home/admin` for the Debian mapping |

Protect the files and validate their JSON:

```bash
chmod 600 ~/.gemini/config/config.json ~/.gemini/antigravity-cli/settings.json
python3 -m json.tool ~/.gemini/config/config.json >/dev/null
python3 -m json.tool ~/.gemini/antigravity-cli/settings.json >/dev/null
```

**You should see:** no syntax errors. This checks JSON syntax, not whether a CLI version recognizes every field. Verify actual behavior next.

---

<a id="verify"></a>
<a id="3-apply-changes--restart-daemon"></a>
## ✅ 5. Start Remote Control and test it

**▶ Run in: the server terminal**

Choose **one** command for the actual machine:

```bash
# Ubuntu
agy remote-control start --name "ubuntu-cp"

# Debian — use this instead on that machine
agy remote-control start --name "debian-oa"
```

This registers and starts the systemd **user** service. After later configuration edits, restart the registered service:

```bash
systemctl --user restart antigravity-cli-daemon.service
```

Check its status and recent logs:

```bash
agy remote-control status
systemctl --user is-active antigravity-cli-daemon.service
systemctl --user is-enabled antigravity-cli-daemon.service
loginctl show-user "$(id -un)" -p Linger
journalctl --user -u antigravity-cli-daemon.service -n 25 --no-pager
```

| Check | Expected result |
|---|---|
| CLI status | Active, with your chosen machine name |
| systemd | `active` and `enabled` |
| Linger | `Linger=yes`, so the user service survives logout and starts at boot |
| Journal | No Protobuf parser, authentication or startup errors; redact account details before sharing logs |

The start command enabled lingering during the verified Ubuntu setup. If yours remains off, inspect registration output rather than assume the daemon will survive logout.

### Test a headless command

Run from your trusted workspace (`/home/admin` for Debian):

```bash
cd /home/ubuntu
agy --print "Run the command printf AGY_HEADLESS_OK in the terminal and report its output. Do not modify any files or run other commands." --print-timeout 90s
```

**You should see:** `AGY_HEADLESS_OK` reported without an approval prompt. Do not add a separate permission-bypass flag to this test; it would mask whether the saved configuration works. A model request can consume your Antigravity usage allowance.

### Check the browser

Open [Antigravity Remote Control](https://antigravity.google.com/r/), sign in with the **same Google account**, select the machine, and confirm a session opens. Verify unattended writes and MCP tools separately with harmless tasks in a disposable workspace if you need them; a command test does not prove every grant or review setting works.

**Verified on Ubuntu, 16 November 2026:** CLI 1.5.9 installed with checksum verification; signed in; `ubuntu-cp` daemon active and enabled; lingering enabled; headless command test passed; no startup/parser errors observed. Browser interaction, unattended writes, MCP calls and a reboot test were not verified in that check.

---

<a id="fix"></a>
## 🔧 Troubleshooting and undo

| You see / want | What to do |
|---|---|
| `agy: command not found` | Try `~/.local/bin/agy`; check PATH or reopen the login shell |
| `not signed in` | Run `agy` as the intended Linux user, complete Google OAuth, then retry the start command |
| `proto: syntax error` or unknown-field errors | Check JSON and field location, inspect the journal, and compare with the installed version's schema; restore the backup if needed |
| Daemon inactive | Check CLI status and the service journal; fix the reported cause before retrying |
| Wrong dashboard name | Edit `cliRemoteControlHostname` and restart, or rerun `start --name`. Do not confuse it with the editor's `remoteControlHostname` |
| Machine missing in browser | Confirm the same Google account, an active daemon, internet access and Remote Control availability for the account |
| Approval prompts remain | Check the installed version's effective settings and the specific tool; a running daemon does not prove all policies took effect |
| Undo settings | Restore the timestamped backups, or remove only the fields added by this setup if no original file existed; restart the service |
| Stop and unregister Remote Control | Run `agy remote-control stop` |

> [!IMPORTANT]
> **EC2 idle-stop:** Remote Control works only while EC2 is running. The detector checked on `ubuntu-cp` recognized `claude`, `codex` and `aider`, but not `agy`/Antigravity. Browser-only work may therefore be interrupted by auto-stop. Keep an SSH session open while working until a workload check covering active Antigravity work is configured and tested. Do not count the always-running daemon as permanent activity, or it can prevent all idle stops.

References: [Google installation guide](https://antigravity.google/docs/cli/tutorial) · [Google Remote Control documentation](https://antigravity.google/docs/remote-control?tab=cli)
