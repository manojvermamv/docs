# Antigravity CLI Remote Control: Auto-Approval & Headless Setup Runbook

A production-ready reference to bypass interactive confirmation prompts (tools, commands, file writes) when running headless Linux/EC2 instances via the web portal ([https://antigravity.google.com/r/](https://antigravity.google.com/r/)).

---

## 0. Generic Environment Defaults

Use the hostname and Linux username that match your machine. The defaults below are your environment mappings; adjust them for other servers.

| Machine hostname | Linux username | Trusted workspace |
| --- | --- | --- |
| `debian-oa` | `admin` | `/home/admin` |
| `ubuntu-cp` | `ubuntu` | `/home/ubuntu` |

---

## 1. Configure Global Tool & Command Grants

Antigravity’s daemon uses compiled Protobuf schemas (`proto3 JSON`). Permission grants must reside under `userSettings.globalPermissionGrants` inside `~/.gemini/config/config.json`.

1. Open the configuration file:

```bash
nano ~/.gemini/config/config.json
```

2. Add wildcard grants (`"command(*)"`, `"read_file(*)"`, `"write_file(*)"`, `"mcp(*)"`) to the top of the `"allow"` array:

```json
{
  "userSettings": {
    "cliRemoteControlHostname": "debian-oa",
    "enableNotificationsForSpecialEvents": false,
    "globalPermissionGrants": {
      "allow": [
        "command(*)",
        "read_file(*)",
        "write_file(*)",
        "mcp(*)",
        "read_url(raw.githubusercontent.com)",
        ...
      ]
    }
  }
}
```

> **Configuration & Syntax Notes:**
>
> - **Hostname Customization:** Replace `"debian-oa"` in `cliRemoteControlHostname` with your preferred identifier (e.g., `"ubuntu-cp"`, `"ec2-prod"`, `"workspace-primary"`). This determines the machine name displayed in the Antigravity web dashboard switcher.
> - **Retain Existing Allow Entries:** Keep any existing individual command/URL lines below the wildcards intact.
> - **Strict JSON Schema:** A missing comma or mismatched bracket will cause the Go runtime Protobuf parser to fail (`proto: syntax error`).
> - **Forbidden Keys:** Do not insert `artifactReviewMode`, `permissions`, or `hooks` blocks inside `config.json`.

---

## 2. Configure Workspace Execution Defaults

Set local environment flags, workspace access, and execution mode in `~/.gemini/antigravity-cli/settings.json`.

1. Open or create the settings file:

```bash
mkdir -p ~/.gemini/antigravity-cli
nano ~/.gemini/antigravity-cli/settings.json
```

2. Populate it with clean baseline workspace settings:

```json
{
  "toolPermission": "always-proceed",
  "artifactReviewPolicy": "always-proceed",
  "allowNonWorkspaceAccess": true,
  "enableTerminalSandbox": false,
  "mode": "accept-edits",
  "trustedWorkspaces": [
    "/home/admin"
  ]
}
```

> **Key Settings:**  
>
> - **`"trustedWorkspaces"`:** Adjust `"/home/admin"` to match your environment's user directory (e.g., `"/home/ubuntu"` on standard AWS Ubuntu AMIs).
> - **`"mode": "accept-edits"`:** Bypasses manual diff approvals for file edits and writes.
> - **`"allowNonWorkspaceAccess": true`:** Enables file operations across system directories outside the current project root.
> - **`"enableTerminalSandbox": false`:** Avoids sandbox constraint issues during headless remote command execution.

---

## 3. Apply Changes & Restart Daemon

1. Start and name the remote-control daemon, Select one for the actual command:

```bash
# For Debian
agy remote-control start --name "debian-oa"

# For Ubuntu
agy remote-control start --name "ubuntu-cp"
```

2. Restart the background systemd user service after edit:

```bash
systemctl --user restart antigravity-cli-daemon.service
```

3. Verify that the daemon is active and running cleanly:

```bash
agy remote-control status
```

4. Confirm there are no proto parser or startup errors in the service journal:

```bash
journalctl --user -u antigravity-cli-daemon.service -n 25 --no-pager
```
