# QEMU/KVM Virtual Machines with Browser-Based Access

A practical, self-hostable guide to creating Linux or Windows virtual
machines on a Linux host and accessing their graphical desktops through
a web browser using **QEMU/KVM + noVNC**.

> **Status:** Community-style setup guide\
> **Last reviewed:** 11 November 2026\
> **Primary target:** Ubuntu/Debian x86-64 hosts\
> **Important:** This project runs on a Linux machine that you control.
> GitHub is suitable for hosting the source code and documentation, but
> GitHub's repository website and GitHub Pages do not run QEMU virtual
> machines.

------------------------------------------------------------------------

## Contents

-   [1. What this project does](#1-what-this-project-does)
-   [2. Architecture](#2-architecture)
-   [3. Use cases](#3-use-cases)
-   [4. Hosting and platform
    compatibility](#4-hosting-and-platform-compatibility)
-   [5. Requirements and limitations](#5-requirements-and-limitations)
-   [6. Supported guest operating
    systems](#6-supported-guest-operating-systems)
-   [7. Quick start](#7-quick-start)
-   [8. Complete VM management script](#8-complete-vm-management-script)
-   [9. Install and use a VM](#9-install-and-use-a-vm)
-   [10. Browser access](#10-browser-access)
-   [11. Useful QEMU options](#11-useful-qemu-options)
-   [12. Alternative configurations](#12-alternative-configurations)
-   [13. GitHub and VS Code
    integration](#13-github-and-vs-code-integration)
-   [14. Security recommendations](#14-security-recommendations)
-   [15. Troubleshooting](#15-troubleshooting)
-   [16. Maintenance and backups](#16-maintenance-and-backups)
-   [17. References](#17-references)

------------------------------------------------------------------------

## 1. What this project does

This project creates a virtual computer inside an existing Linux
machine.

You can choose an operating-system installer, allocate CPU cores, memory
and disk space, install the guest operating system, and access its
graphical desktop through a browser.

It uses:

  Component    Purpose
  ------------ ----------------------------------------------------------
  QEMU         Emulates and runs the virtual machine
  KVM          Accelerates virtualization using supported host hardware
  `qemu-img`   Creates and manages virtual disk images
  noVNC        Provides a browser-based VNC client
  Websockify   Bridges browser WebSocket connections to VNC
  Git          Retrieves the noVNC source code

The guest operating system runs on the host. noVNC is only the remote
display/control interface; it does not host or execute the VM.

### What it is not

-   It is not a GitHub-hosted virtual machine service.
-   It is not a replacement for GitHub Codespaces.
-   It does not make a VM run inside a browser without a host.
-   It does not automatically provide a public, authenticated cloud
    desktop.
-   It does not bypass Windows licensing or activation.
-   It does not guarantee KVM access on a VPS or cloud instance.

------------------------------------------------------------------------

## 2. Architecture

``` text
Your computer / browser
          |
          | HTTPS or SSH tunnel
          v
Linux host (Ubuntu / Debian / compatible)
          |
          +-- QEMU
          |     |
          |     +-- KVM acceleration (if available)
          |     |
          |     +-- Guest CPU / RAM / virtual disk
          |              |
          |              +-- Ubuntu / Xubuntu / Windows
          |
          +-- VNC server (bound to 127.0.0.1)
          |
          +-- noVNC + Websockify (bound to 127.0.0.1)
```

The recommended default is to bind both VNC and noVNC to loopback
(`127.0.0.1`) and reach them through an SSH tunnel. Do not expose an
unauthenticated VNC or noVNC port directly to the public internet.

------------------------------------------------------------------------

## 3. Use cases

  ---------------------------------------------------------------------
  Use case                           Example
  ---------------------------------- ----------------------------------
  Linux desktop in a browser         Run Xubuntu or Lubuntu on a remote
                                     Linux host

  Windows desktop in a browser       Run a properly licensed Windows
                                     guest

  Cross-platform testing             Test software on multiple guest
                                     operating systems

  Browser-based GUI testing          Test desktop applications in a
                                     disposable VM

  Development workstation            Keep a separate development
                                     environment on a server

  Training and demonstrations        Provide a controlled desktop for
                                     demonstrations

  Legacy application testing         Test software that requires an
                                     older supported OS

  Isolated experiments               Test configuration changes without
                                     changing the host OS

  Personal remote desktop            Access a VM from a laptop or
                                     tablet

  CI / automated testing             Run headless guest workloads where
                                     the host and test framework
                                     support them
  ---------------------------------------------------------------------

### Workloads that need special consideration

-   **Android Studio / emulators:** Nested virtualization, graphics
    acceleration, RAM and CPU requirements can make this unsuitable for
    small VPS instances.
-   **GPU-intensive applications:** The basic script uses a virtual
    display adapter, not physical GPU passthrough.
-   **Gaming / 3D workloads:** Expect limited performance without a more
    advanced GPU-passthrough setup.
-   **Multiple users:** This script creates one VM configuration.
    Multi-user provisioning, authentication, quotas and isolation
    require additional infrastructure.
-   **Production workloads:** Use a maintained virtualization management
    solution and proper backups, monitoring and access controls.

------------------------------------------------------------------------

## 4. Hosting and platform compatibility

  -----------------------------------------------------------------------
  Platform                Can host this VM?       Notes
  ----------------------- ----------------------- -----------------------
  Local Ubuntu/Debian PC  Yes, if KVM is          Recommended starting
                          available               point

  Dedicated Linux server  Yes, if KVM is          Good for persistent use
                          available               

  VPS                     Conditional             Provider and instance
                                                  must expose
                                                  virtualization support

  AWS EC2                 Conditional             Check instance family,
                                                  host support and
                                                  `/dev/kvm`; do not
                                                  assume nested KVM is
                                                  available

  GitHub repository       No                      Repository pages
  website                                         display source code;
                                                  they do not execute it

  GitHub Pages            No                      Static website hosting
                                                  only

  GitHub Codespaces       Not a dependable KVM    A Codespace is a
                          host                    development
                                                  container/VM, not a
                                                  general
                                                  nested-virtualization
                                                  service; check actual
                                                  device and provider
                                                  support

  VS Code Web alone       No                      An editor interface is
                                                  not a VM host

  VS Code Remote SSH      Yes, indirectly         VS Code connects to a
                                                  separate Linux host
                                                  that runs QEMU

  Browser-based           Yes, alongside a VM     code-server is an
  code-server                                     editor; QEMU still runs
                                                  on the Linux host
  -----------------------------------------------------------------------

### Check the host before installing

``` bash
uname -m
lscpu | grep -E 'Architecture|Virtualization'
ls -l /dev/kvm
```

For an x86-64 KVM host, `/dev/kvm` should exist and the account running
QEMU should have permission to access it.

A cloud provider may expose CPU virtualization flags without exposing
nested KVM to the guest. The practical test is whether QEMU can open
`/dev/kvm` and start with KVM acceleration.

If KVM is unavailable, QEMU can use TCG software emulation. TCG is
useful for compatibility tests and light experiments, but it is
generally much slower. This guide's script offers that fallback.

------------------------------------------------------------------------

## 5. Requirements and limitations

### Host requirements

-   Ubuntu or Debian, preferably a supported release.
-   x86-64 host for the supplied `qemu-system-x86_64` command.
-   Sufficient CPU, RAM and free disk space.
-   KVM access for accelerated virtualization.
-   Network access to download installation media and noVNC.
-   A browser with JavaScript and WebSocket support.

### Example resource planning

These are starting points, not guarantees. Actual requirements depend on
the guest OS and workload.

  Guest workload              Suggested starting allocation
  --------------------------- ---------------------------------
  Lightweight Linux desktop   2 vCPU, 2--4 GiB RAM
  General Linux desktop       2--4 vCPU, 4--8 GiB RAM
  Windows desktop             2--4 vCPU, 4--8 GiB RAM or more
  Development tools / IDE     4+ vCPU, 8--16 GiB RAM or more

Keep resources for the host itself. Do not allocate all physical memory
or CPU capacity to guests.

### Disk formats

  -----------------------------------------------------------------------
  Format                  Advantages              Trade-offs
  ----------------------- ----------------------- -----------------------
  QCOW2                   Thin-provisioned,       Some overhead; actual
                          supports snapshots and  disk usage grows as
                          backing files           data is written

  RAW                     Simple and broadly      Usually consumes the
                          compatible; low format  allocated space when
                          overhead                fully provisioned
  -----------------------------------------------------------------------

The script below uses QCOW2 by default.

A virtual disk's maximum capacity is not the same as guaranteed free
physical storage. Monitor the host filesystem.

------------------------------------------------------------------------

## 6. Supported guest operating systems

The script includes official Ubuntu-family desktop images and a custom
ISO option.

### Ubuntu-family images

The URLs below point to official release locations. Confirm the current
filename and checksum in the linked release directory before
downloading.

  -----------------------------------------------------------------------------------------------------
  Menu option   Distribution   Official release directory
  ------------- -------------- ------------------------------------------------------------------------
  1             Xubuntu        [Xubuntu
                24.04.5 LTS    24.04.5](https://cdimage.ubuntu.com/xubuntu/releases/24.04.5/release/)

  2             Kubuntu        [Kubuntu
                24.04.5 LTS    24.04.5](https://cdimage.ubuntu.com/kubuntu/releases/24.04.5/release/)

  3             Lubuntu        [Lubuntu
                24.04.5 LTS    24.04.5](https://cdimage.ubuntu.com/lubuntu/releases/24.04.5/release/)

  4             Ubuntu 24.04.5 [Ubuntu 24.04.5](https://releases.ubuntu.com/24.04/)
                LTS            

  5             Custom ISO     Supply an ISO you obtained from its publisher
  -----------------------------------------------------------------------------------------------------

Ubuntu flavors have their own support periods. Check each project's
release information rather than assuming every flavor has the same
lifecycle.

### Windows images

The custom ISO option can be used for Windows 10/11, Windows LTSC,
Windows Server, or another operating system, provided you have the right
to use the image.

Official Microsoft starting points:

-   [Windows 11 Enterprise Evaluation
    Center](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise)
-   [Windows 11 Enterprise
    download](https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise)
-   [Microsoft Windows
    downloads](https://www.microsoft.com/software-download/)

Microsoft evaluation media has evaluation terms and time limits. A
downloaded ISO does not grant a production license. Check edition,
architecture, licensing and support lifecycle.

### Tiny11 and other modified images

Tiny11 is an unofficial modified Windows image, not a Microsoft Windows
edition. Prefer building from legitimate Microsoft media using the
project's published build instructions:

-   [Tiny11 Builder source
    repository](https://github.com/ntdevlabs/tiny11builder)

Do not download modified operating-system images from arbitrary
file-sharing links. Review the build scripts, source media, integrity
and licensing implications.

### Verify installation media

For Ubuntu-family images, download `SHA256SUMS` from the same official
release directory and verify the exact ISO:

``` bash
cd ~/qemu-vms/isos

# Example: download the checksum list from the official directory.
wget -O SHA256SUMS \
  https://releases.ubuntu.com/24.04/SHA256SUMS

# Verify the ISO filename is present in the checksum list.
grep 'ubuntu-24.04.5-desktop-amd64.iso' SHA256SUMS

# Verify the downloaded file against the checksum entry.
grep 'ubuntu-24.04.5-desktop-amd64.iso' SHA256SUMS \
  | sha256sum --check -
```

Use the matching release directory and filename for Xubuntu, Kubuntu or
Lubuntu. For Windows, compare the hash against Microsoft's published
hash for that exact download.

------------------------------------------------------------------------

## 7. Quick start

### Step 1 --- Install host packages

``` bash
sudo apt update

sudo apt install -y \
  qemu-system-x86 \
  qemu-utils \
  qemu-kvm \
  git \
  wget \
  curl \
  ca-certificates \
  openssh-client
```

Package names can differ on other distributions.

### Step 2 --- Check KVM

``` bash
test -e /dev/kvm && echo "KVM device exists" || echo "KVM device not found"
test -r /dev/kvm && test -w /dev/kvm \
  && echo "Current user can access KVM" \
  || echo "Current user cannot access KVM"
```

On Ubuntu/Debian, inspect the device group and your account:

``` bash
ls -l /dev/kvm
id
```

If the device is owned by the `kvm` group, an administrator can add your
account:

``` bash
sudo usermod -aG kvm "$USER"
```

Log out and back in for the new group membership to apply. Do not change
device permissions to world-writable as a shortcut.

### Step 3 --- Create a project directory

``` bash
mkdir -p ~/qemu-vms/isos
cd ~/qemu-vms
```

Save the script in the next section as `vm-manager.sh`.

### Step 4 --- Make it executable

``` bash
chmod +x vm-manager.sh
```

### Step 5 --- Create and install a VM

``` bash
./vm-manager.sh create
```

Follow the prompts. The script creates the VM directory, downloads or
copies the installer ISO, creates the virtual disk and prepares a
launcher.

------------------------------------------------------------------------

## 8. Complete VM management script

Save the following as `vm-manager.sh`.

The script is intentionally limited to a single VM per generated VM
directory. It does not create public accounts, configure a public
reverse proxy, or modify host firewall rules.

``` bash
#!/usr/bin/env bash
set -Eeuo pipefail

# ------------------------------------------------------------
# QEMU/KVM + noVNC single-VM manager
# Supported host: Ubuntu/Debian x86-64
# ------------------------------------------------------------

BASE_DIR="${HOME}/qemu-vms"
NOVNC_DIR="${BASE_DIR}/noVNC"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

info()  { printf "${BLUE}[INFO]${RESET} %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${RESET} %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${RESET} %s\n" "$*"; }
error() { printf "${RED}[ERROR]${RESET} %s\n" "$*" >&2; }

die() {
    error "$*"
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"
}

safe_name() {
    [[ "$1" =~ ^[a-zA-Z0-9_-]+$ ]] ||
        die "VM name may contain only letters, numbers, underscores and hyphens."
}

usage() {
    cat <<'EOF'
Usage:
  ./vm-manager.sh create
  ./vm-manager.sh list
  ./vm-manager.sh start <vm-name> [install]
  ./vm-manager.sh stop <vm-name>
  ./vm-manager.sh status <vm-name>
  ./vm-manager.sh delete <vm-name>

Commands:
  create             Create a VM and its launcher
  list               List VM directories
  start NAME install Boot from installation ISO
  start NAME         Boot the installed virtual disk
  stop NAME          Stop the QEMU process
  status NAME        Show VM process status
  delete NAME        Delete a VM after confirmation

Examples:
  ./vm-manager.sh create
  ./vm-manager.sh start my-linux install
  ./vm-manager.sh start my-linux
  ./vm-manager.sh status my-linux
  ./vm-manager.sh stop my-linux

The generated VM launcher can also be run directly from its VM directory.
EOF
}

check_host() {
    [[ "$(uname -m)" == "x86_64" ]] ||
        die "This script targets x86_64 hosts. ARM hosts need an ARM-specific QEMU configuration."

    require_command qemu-system-x86_64
    require_command qemu-img
    require_command git
    require_command wget
    require_command sha256sum
}

install_novnc() {
    mkdir -p "$BASE_DIR"

    if [[ -d "$NOVNC_DIR/.git" ]]; then
        info "noVNC repository already exists."
    elif [[ -e "$NOVNC_DIR" ]]; then
        die "$NOVNC_DIR exists but is not a Git checkout. Move it or inspect it manually."
    else
        git clone --depth 1 https://github.com/novnc/noVNC.git "$NOVNC_DIR"
    fi

    [[ -x "$NOVNC_DIR/utils/novnc_proxy" ]] ||
        die "noVNC proxy script was not found."
}

download_iso() {
    local iso_name="$1"
    local iso_url="$2"
    local checksum_url="$3"
    local iso_path="$4"
    local sums_path="${iso_path%/*}/SHA256SUMS"

    if [[ -s "$iso_path" ]]; then
        warn "ISO already exists: $iso_path"
        read -r -p "Reuse this existing ISO? [Y/n]: " answer
        if [[ "${answer,,}" != "n" ]]; then
            return
        fi
        rm -f "$iso_path"
    fi

    wget --https-only --show-progress -O "$iso_path" "$iso_url" ||
        die "ISO download failed."

    if [[ -n "$checksum_url" ]]; then
        wget --https-only -O "$sums_path" "$checksum_url" ||
            die "Could not download checksum list."

        local line
        line="$(grep -F " $iso_name" "$sums_path" || true)"
        [[ -n "$line" ]] || die "ISO filename was not found in SHA256SUMS."

        printf '%s\n' "$line" | (cd "${iso_path%/*}" && sha256sum --check -) ||
            die "ISO checksum verification failed."
    else
        warn "No trusted checksum URL was supplied. Verify this ISO manually."
    fi
}

create_vm() {
    check_host
    install_novnc

    mkdir -p "$BASE_DIR/isos"

    printf "\n${GREEN}QEMU VM Creator${RESET}\n\n"
    printf "1) Xubuntu 24.04.5 LTS\n"
    printf "2) Kubuntu 24.04.5 LTS\n"
    printf "3) Lubuntu 24.04.5 LTS\n"
    printf "4) Ubuntu 24.04.5 LTS\n"
    printf "5) Custom local ISO (Windows or another OS)\n\n"

    local choice vm_name cores ram disk_gib iso_name iso_url checksum_url iso_path

    read -r -p "Select OS [1-5]: " choice

    case "$choice" in
        1)
            iso_name="xubuntu-24.04.5-desktop-amd64.iso"
            iso_url="https://cdimage.ubuntu.com/xubuntu/releases/24.04.5/release/${iso_name}"
            checksum_url="https://cdimage.ubuntu.com/xubuntu/releases/24.04.5/release/SHA256SUMS"
            ;;
        2)
            iso_name="kubuntu-24.04.5-desktop-amd64.iso"
            iso_url="https://cdimage.ubuntu.com/kubuntu/releases/24.04.5/release/${iso_name}"
            checksum_url="https://cdimage.ubuntu.com/kubuntu/releases/24.04.5/release/SHA256SUMS"
            ;;
        3)
            iso_name="lubuntu-24.04.5-desktop-amd64.iso"
            iso_url="https://cdimage.ubuntu.com/lubuntu/releases/24.04.5/release/${iso_name}"
            checksum_url="https://cdimage.ubuntu.com/lubuntu/releases/24.04.5/release/SHA256SUMS"
            ;;
        4)
            iso_name="ubuntu-24.04.5-desktop-amd64.iso"
            iso_url="https://releases.ubuntu.com/24.04/${iso_name}"
            checksum_url="https://releases.ubuntu.com/24.04/SHA256SUMS"
            ;;
        5)
            read -r -e -p "Path to an existing ISO file: " iso_path
            [[ -f "$iso_path" ]] || die "ISO file does not exist."
            iso_path="$(realpath "$iso_path")"
            iso_name="$(basename "$iso_path")"
            iso_url=""
            checksum_url=""
            ;;
        *)
            die "Invalid OS selection."
            ;;
    esac

    read -r -p "VM name (e.g. ubuntu-desktop): " vm_name
    safe_name "$vm_name"

    local vm_dir="${BASE_DIR}/${vm_name}"
    [[ ! -e "$vm_dir" ]] || die "VM directory already exists: $vm_dir"

    read -r -p "CPU cores (e.g. 2): " cores
    [[ "$cores" =~ ^[1-9][0-9]*$ ]] || die "CPU cores must be a positive integer."

    read -r -p "RAM (e.g. 4G or 8192M): " ram
    [[ "$ram" =~ ^[1-9][0-9]*[GM]$ ]] ||
        die "RAM must use a positive integer followed by G or M."

    read -r -p "Virtual disk size in GiB (e.g. 40): " disk_gib
    [[ "$disk_gib" =~ ^[1-9][0-9]*$ ]] ||
        die "Disk size must be a positive integer in GiB."

    mkdir -p "$vm_dir/isos"

    local vm_iso="$vm_dir/isos/${iso_name}"

    if [[ "$choice" == "5" ]]; then
        cp -- "$iso_path" "$vm_iso"
    else
        download_iso "$iso_name" "$iso_url" "$checksum_url" "$vm_iso"
    fi

    info "Creating QCOW2 virtual disk..."
    qemu-img create -f qcow2 "$vm_dir/disk.qcow2" "${disk_gib}G"

    cat > "$vm_dir/vm.conf" <<EOF
VM_NAME="${vm_name}"
CPU_CORES="${cores}"
RAM="${ram}"
DISK="${vm_dir}/disk.qcow2"
ISO="${vm_iso}"
NOVNC_DIR="${NOVNC_DIR}"
EOF

    cat > "$vm_dir/vm.sh" <<'LAUNCHER'
#!/usr/bin/env bash
set -Eeuo pipefail

VM_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$VM_DIR/vm.conf"

PID_FILE="$VM_DIR/qemu.pid"
LOG_FILE="$VM_DIR/qemu.log"
NOVNC_PID_FILE="$VM_DIR/novnc.pid"
NOVNC_LOG="$VM_DIR/novnc.log"

VNC_DISPLAY="${VNC_DISPLAY:-0}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
VNC_PORT="$((5900 + VNC_DISPLAY))"

is_running() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

start_novnc() {
    if [[ -f "$NOVNC_PID_FILE" ]] &&
       kill -0 "$(cat "$NOVNC_PID_FILE")" 2>/dev/null; then
        echo "noVNC already running."
        return
    fi

    "$NOVNC_DIR/utils/novnc_proxy" \
        --vnc "127.0.0.1:${VNC_PORT}" \
        --listen "127.0.0.1:${NOVNC_PORT}" \
        >"$NOVNC_LOG" 2>&1 &

    echo "$!" > "$NOVNC_PID_FILE"
    sleep 2

    if ! kill -0 "$(cat "$NOVNC_PID_FILE")" 2>/dev/null; then
        echo "noVNC failed. Inspect $NOVNC_LOG"
        rm -f "$NOVNC_PID_FILE"
        exit 1
    fi
}

start_vm() {
    local mode="${1:-normal}"

    if is_running; then
        echo "VM is already running (PID $(cat "$PID_FILE"))."
        return
    fi

    rm -f "$PID_FILE"

    local accel=()
    if [[ -r /dev/kvm && -w /dev/kvm ]]; then
        accel=(-enable-kvm -cpu host)
        echo "Using KVM acceleration."
    else
        accel=(-accel tcg -cpu max)
        echo "KVM is unavailable to this user; using slower TCG emulation."
    fi

    local boot=()
    local cdrom=()

    if [[ "$mode" == "install" ]]; then
        [[ -f "$ISO" ]] || { echo "Installer ISO not found."; exit 1; }
        boot=(-boot once=d)
        cdrom=(-drive "file=$ISO,media=cdrom,readonly=on")
    elif [[ "$mode" != "normal" ]]; then
        echo "Usage: $0 start [install]"
        exit 2
    fi

    qemu-system-x86_64 \
        "${accel[@]}" \
        -machine q35 \
        -m "$RAM" \
        -smp "$CPU_CORES" \
        "${boot[@]}" \
        -drive "file=$DISK,format=qcow2,if=virtio" \
        "${cdrom[@]}" \
        -netdev user,id=net0 \
        -device virtio-net-pci,netdev=net0 \
        -device qemu-xhci \
        -device usb-tablet \
        -vga std \
        -display none \
        -vnc "127.0.0.1:${VNC_DISPLAY}" \
        -pidfile "$PID_FILE" \
        -daemonize \
        -D "$LOG_FILE"

    start_novnc

    echo "VM started."
    echo "Browser URL (through SSH tunnel): http://127.0.0.1:${NOVNC_PORT}/vnc.html"
    echo "QEMU log: $LOG_FILE"
}

stop_vm() {
    if is_running; then
        kill "$(cat "$PID_FILE")"
        echo "Stop signal sent to QEMU."
    else
        echo "VM is not running."
    fi

    if [[ -f "$NOVNC_PID_FILE" ]] &&
       kill -0 "$(cat "$NOVNC_PID_FILE")" 2>/dev/null; then
        kill "$(cat "$NOVNC_PID_FILE")" || true
    fi

    rm -f "$PID_FILE" "$NOVNC_PID_FILE"
}

case "${1:-}" in
    start)
        start_vm "${2:-normal}"
        ;;
    stop)
        stop_vm
        ;;
    status)
        if is_running; then
            echo "VM is running (PID $(cat "$PID_FILE"))."
        else
            echo "VM is stopped."
        fi
        ;;
    *)
        echo "Usage: $0 {start [install]|stop|status}"
        exit 2
        ;;
esac
LAUNCHER

    chmod +x "$vm_dir/vm.sh"

    ok "VM created: $vm_dir"
    echo
    echo "Install the guest OS:"
    echo "  $vm_dir/vm.sh start install"
    echo
    echo "After completing installation and shutting down the guest:"
    echo "  $vm_dir/vm.sh start"
    echo
    echo "Stop the VM:"
    echo "  $vm_dir/vm.sh stop"
}

list_vms() {
    mkdir -p "$BASE_DIR"
    shopt -s nullglob
    local found=0
    for dir in "$BASE_DIR"/*; do
        if [[ -f "$dir/vm.conf" && -f "$dir/vm.sh" ]]; then
            echo "$(basename "$dir")"
            found=1
        fi
    done
    [[ "$found" == "1" ]] || echo "No managed VMs found."
}

vm_action() {
    local action="$1"
    local name="${2:-}"
    safe_name "$name"

    local vm_dir="${BASE_DIR}/${name}"
    [[ -x "$vm_dir/vm.sh" ]] || die "VM not found: $name"

    case "$action" in
        start)
            "$vm_dir/vm.sh" start "${3:-normal}"
            ;;
        stop)
            "$vm_dir/vm.sh" stop
            ;;
        status)
            "$vm_dir/vm.sh" status
            ;;
        delete)
            warn "This permanently deletes the VM disk, ISO and configuration."
            read -r -p "Type DELETE to confirm: " confirm
            [[ "$confirm" == "DELETE" ]] || die "Deletion cancelled."
            "$vm_dir/vm.sh" stop || true
            rm -rf -- "$vm_dir"
            ok "Deleted $name"
            ;;
        *)
            usage
            exit 2
            ;;
    esac
}

case "${1:-}" in
    create)
        create_vm
        ;;
    list)
        list_vms
        ;;
    start|stop|status|delete)
        vm_action "$@"
        ;;
    *)
        usage
        exit 2
        ;;
esac
```

### Script behavior and important notes

-   The script downloads Ubuntu-family ISOs from official release
    directories and checks their SHA256 entry.
-   The custom ISO option copies a local ISO into the VM directory.
    Verify its hash with the publisher before using it.
-   It creates a QCOW2 virtual disk and a per-VM launcher.
-   `start install` attaches the installer ISO and uses `-boot once=d`.
-   After installing the guest OS, shut it down from inside the guest.
    Start it again without `install` to boot from the virtual disk.
-   KVM is used when `/dev/kvm` is readable and writable; otherwise the
    launcher falls back to TCG.
-   The VM's VNC and noVNC listeners bind to loopback by default.
-   The generated launcher uses a simple PID-file approach. For
    long-running production deployments, use a proper service manager
    and process supervision.
-   The script is a starting point, not a complete multi-tenant
    virtualization platform.

------------------------------------------------------------------------

## 9. Install and use a VM

### Create a VM

``` bash
./vm-manager.sh create
```

Example selections:

``` text
Select OS [1-5]: 1
VM name: xubuntu-test
CPU cores: 2
RAM: 4G
Virtual disk size in GiB: 40
```

### Start the installer

``` bash
./vm-manager.sh start xubuntu-test install
```

Open the browser interface through the SSH tunnel described in the next
section. Complete the guest OS installation.

### First reboot after installation

Shut down the guest OS cleanly using its own shutdown menu. Then run:

``` bash
./vm-manager.sh start xubuntu-test
```

The normal start command does not attach the installer ISO, so the
virtual disk is used for booting.

### Stop a VM

``` bash
./vm-manager.sh stop xubuntu-test
```

Prefer shutting down from inside the guest before stopping the host-side
QEMU process. A forced host-side stop can lose guest data that has not
been written to disk.

### Check status

``` bash
./vm-manager.sh status xubuntu-test
```

### List managed VMs

``` bash
./vm-manager.sh list
```

### Delete a VM

``` bash
./vm-manager.sh delete xubuntu-test
```

Deletion removes the VM's virtual disk, installer ISO and configuration.
Back up anything important first.

------------------------------------------------------------------------

## 10. Browser access

### Recommended: SSH tunnel

The noVNC server listens on the Linux host's loopback interface on port
`6080`.

From your local computer, open a terminal:

``` bash
ssh -N -L 6080:127.0.0.1:6080 USER@YOUR_SERVER
```

Replace `USER` and `YOUR_SERVER` with your Linux SSH username and host.

Keep this SSH session open. Then visit:

``` text
http://127.0.0.1:6080/vnc.html
```

The browser connects to your local forwarded port; SSH carries the
connection securely to the server.

If you use a non-default SSH port:

``` bash
ssh -p 2222 -N -L 6080:127.0.0.1:6080 USER@YOUR_SERVER
```

### VS Code Remote SSH

1.  Install the VS Code Remote - SSH extension on your local VS Code.
2.  Connect to the Linux host.
3.  Run the VM manager in the remote terminal.
4.  Forward port `6080` using the VS Code Ports panel.
5.  Open the forwarded address in a browser.

VS Code is providing remote development and port forwarding. QEMU still
runs on the Linux host.

### Public HTTPS access

For a shared or public-facing deployment, put noVNC behind a reverse
proxy or access gateway that provides:

-   HTTPS/TLS.
-   Authentication before access to the noVNC page and WebSocket
    endpoint.
-   Authorization and per-user access controls.
-   Rate limiting and sensible connection limits.
-   Logging and monitoring.
-   A firewall that prevents direct access to the backend VNC port.

Do not simply change `127.0.0.1` to `0.0.0.0` and expose ports `5900` or
`6080`. The example VM has no VNC password configured, and noVNC itself
is not an identity-management system.

------------------------------------------------------------------------

## 11. Useful QEMU options

The generated launcher uses a small set of common options. QEMU supports
many more.

### CPU and memory

``` bash
-m 4G
-smp 4
```

-   `-m` sets guest memory.
-   `-smp` sets the guest vCPU count.

Do not allocate more resources than the host can safely provide.

### KVM acceleration

``` bash
-enable-kvm -cpu host
```

Use when KVM is available and accessible.

### TCG fallback

``` bash
-accel tcg -cpu max
```

Uses software emulation. Performance can be substantially lower than
KVM.

### Disk formats

Create a QCOW2 disk:

``` bash
qemu-img create -f qcow2 disk.qcow2 40G
```

Create a RAW disk:

``` bash
qemu-img create -f raw disk.img 40G
```

Inspect a disk:

``` bash
qemu-img info disk.qcow2
```

Convert a disk (ensure the VM is shut down first):

``` bash
qemu-img convert -p -f raw -O qcow2 disk.img disk.qcow2
```

### Networking

The example uses QEMU user-mode networking:

``` bash
-netdev user,id=net0 \
-device virtio-net-pci,netdev=net0
```

This is convenient for basic outbound connectivity. It is not the same
as a bridged network interface. Inbound services require explicit port
forwarding or a different network configuration.

Example: forward host port `2222` to guest port `22`:

``` bash
-netdev user,id=net0,hostfwd=tcp:127.0.0.1:2222-:22 \
-device virtio-net-pci,netdev=net0
```

Only add port forwarding when the guest service is installed and
configured. Keep host-side forwarded ports private unless there is a
deliberate secured exposure design.

### Display

The example uses:

``` bash
-vga std
```

Other display adapters and graphics configurations are possible.
Available choices depend on QEMU build, guest drivers and workload. A
virtual display is not physical GPU passthrough.

### UEFI firmware

UEFI boot can be configured with OVMF firmware if the host has the
appropriate package installed. Firmware paths vary by distribution;
locate the installed OVMF files rather than assuming a universal path.

------------------------------------------------------------------------

## 12. Alternative configurations

### A. Use RAW instead of QCOW2

Change the disk creation command:

``` bash
qemu-img create -f raw disk.img 40G
```

Change the QEMU disk argument:

``` bash
-drive file=disk.img,format=raw,if=virtio
```

### B. Use a different VNC display and noVNC port

The generated launcher supports environment variables:

``` bash
VNC_DISPLAY=1 NOVNC_PORT=6081 ./vm.sh start
```

Display `1` normally maps to VNC port `5901`. Forward the matching noVNC
port:

``` bash
ssh -N -L 6081:127.0.0.1:6081 USER@YOUR_SERVER
```

### C. Use another Linux distribution

Choose the custom ISO option and supply a local, verified ISO. Ensure
the ISO architecture matches the QEMU machine and host configuration.

### D. Use Windows

1.  Obtain the ISO from Microsoft or another source you are legally
    entitled to use.
2.  Verify the published checksum.
3.  Choose the custom ISO option.
4.  Complete Windows installation through noVNC.
5.  Install the appropriate guest drivers and QEMU guest agent where
    supported.
6.  Activate Windows using a valid license.

Windows performance and device compatibility can require additional
configuration, including UEFI firmware, TPM emulation, Secure Boot,
storage drivers and VirtIO drivers. The basic script does not configure
all Windows 11 hardware requirements or emulate a TPM.

### E. Use a headless guest

A graphical desktop is not required for every workload. For server
workloads, use a server ISO and manage the guest through SSH or another
secured management channel. You can omit noVNC entirely if no graphical
console is needed.

### F. Use a VM management platform

For multiple VMs, user accounts, lifecycle management, networks, storage
pools and a web management interface, evaluate established tools such
as:

-   [libvirt](https://libvirt.org/)
-   [virt-manager](https://virt-manager.org/)
-   [Cockpit](https://cockpit-project.org/) with its virtualization
    functionality where supported
-   [Proxmox
    VE](https://www.proxmox.com/en/proxmox-virtual-environment/overview)

These are alternatives for more complete management, not dependencies of
the basic script.

------------------------------------------------------------------------

## 13. GitHub and VS Code integration

### Host the project on GitHub

GitHub can host:

-   This README.
-   The Bash scripts.
-   Configuration examples.
-   Issue tracking and release notes.
-   Documentation and screenshots.

Example:

``` bash
git init
git add README.md vm-manager.sh
git commit -m "Add QEMU VM manager and documentation"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

Clone it onto the Linux host:

``` bash
git clone https://github.com/USERNAME/REPOSITORY.git
cd REPOSITORY
chmod +x vm-manager.sh
```

Review scripts before running them, especially when cloning public
repositories.

### GitHub Pages

GitHub Pages can publish a static project website or documentation. It
cannot run QEMU, KVM, noVNC backend processes or persistent virtual
machines.

### GitHub Codespaces

Codespaces can be useful for editing the project, running shell checks
and developing documentation. Do not assume it exposes `/dev/kvm` or
permits nested virtualization. If the device is unavailable, this
QEMU/KVM configuration will not run with KVM acceleration there; TCG may
be too slow or restricted for practical desktop use.

### VS Code Web and code-server

A browser-based editor can be used alongside a separately hosted VM:

``` text
Browser
  |
  +-- VS Code Web / code-server
  |
  +-- noVNC desktop
           |
           +-- Linux server running QEMU/KVM
```

The editor and VM are separate services. Protect both with
authentication and HTTPS.

------------------------------------------------------------------------

## 14. Security recommendations

A remote desktop is a powerful access path to a machine. Treat it as an
administrative service.

### Minimum safeguards

-   Bind VNC to `127.0.0.1`.
-   Bind noVNC to `127.0.0.1`.
-   Prefer SSH tunnelling for personal access.
-   Use HTTPS and authentication for browser access by other users.
-   Never publish SSH private keys, passwords, tokens or cloud
    credentials in the repository.
-   Do not run QEMU as root unless a specific, reviewed requirement
    makes it necessary.
-   Keep the host and guest operating systems patched.
-   Restrict network access to only the ports you need.
-   Verify downloaded operating-system images.
-   Back up VM disks before risky upgrades or experiments.
-   Do not run untrusted guest workloads on a sensitive host without
    appropriate isolation and resource limits.

### Public deployment warning

The example is a single-user, loopback-only starting configuration. It
is not a hardened public multi-user service. A public deployment needs a
reverse proxy/access gateway, authentication, authorization, TLS,
resource controls and operational monitoring.

------------------------------------------------------------------------

## 15. Troubleshooting

### `Could not access KVM kernel module`

Check:

``` bash
ls -l /dev/kvm
id
```

Confirm that the host/provider exposes KVM and that the QEMU user has
access. If KVM is unavailable, the generated launcher attempts TCG
emulation.

### `qemu-system-x86_64: command not found`

Install the QEMU system emulator package:

``` bash
sudo apt update
sudo apt install -y qemu-system-x86 qemu-utils
```

### `qemu-img: command not found`

``` bash
sudo apt install -y qemu-utils
```

### VM boots to an empty disk instead of the installer

Use the install mode:

``` bash
./vm-manager.sh start VM_NAME install
```

The installer uses `-boot once=d`, which selects the CD-ROM for the
initial boot. After installation, shut down and use normal start mode.

### noVNC page does not load

Check the VM and noVNC logs:

``` bash
cat ~/qemu-vms/VM_NAME/qemu.log
cat ~/qemu-vms/VM_NAME/novnc.log
```

Check listeners:

``` bash
ss -ltnp | grep -E '5900|6080'
```

Confirm the SSH tunnel is active and that the local browser is opening
the forwarded port.

### Browser opens but cannot connect to VNC

Confirm that QEMU is running and that the VNC display matches the port
configured for noVNC.

Default mapping:

``` text
VNC display :0  -> TCP 5900
noVNC        -> TCP 6080
```

### Guest has no internet access

The sample uses QEMU user-mode networking. Check the guest's network
configuration and DNS. For inbound access to a guest service, configure
a deliberate port-forwarding rule or a different network mode.

### Windows installer cannot see the virtual disk

Some Windows installers need VirtIO storage drivers when using VirtIO
disks. Attach the appropriate VirtIO driver ISO and load the storage
driver during installation, or use a compatible emulated storage
controller. Obtain drivers from the official [Fedora VirtIO driver
project](https://github.com/virtio-win/virtio-win).

### VM is slow

-   Confirm KVM is actually in use.
-   Check host CPU and memory pressure.
-   Avoid overcommitting RAM.
-   Use a lightweight desktop guest.
-   Check disk I/O and available storage.
-   Do not expect GPU acceleration from the default virtual display.

### Disk is full

``` bash
df -h
du -sh ~/qemu-vms/*
qemu-img info ~/qemu-vms/VM_NAME/disk.qcow2
```

QCOW2 is thin-provisioned; guest writes can still fill the host
filesystem.

------------------------------------------------------------------------

## 16. Maintenance and backups

### Back up a VM

Shut down the guest cleanly first. Then copy its VM directory:

``` bash
cp -a ~/qemu-vms/VM_NAME \
  ~/qemu-vms/VM_NAME-backup
```

For large disks, use a backup destination with sufficient free space. A
live copy of a disk that is being written to is not a reliable
application-consistent backup.

### Check disk usage

``` bash
du -h --max-depth=2 ~/qemu-vms
df -h
```

### Update noVNC

Stop active noVNC processes and review the upstream changes before
updating the checkout:

``` bash
cd ~/qemu-vms/noVNC
git fetch origin
git log --oneline HEAD..origin/master
```

Review the upstream branch and project instructions before merging or
resetting local changes. Do not blindly overwrite a customized checkout.

### Update the host

Keep the host OS, QEMU, noVNC and guest operating systems maintained.
Test important updates against a backup or non-production VM before
applying them to an important environment.

------------------------------------------------------------------------

## 17. References

Use upstream documentation for current options and platform-specific
details.

### QEMU and KVM

-   [QEMU documentation](https://www.qemu.org/docs/master/)
-   [QEMU system
    invocation](https://www.qemu.org/docs/master/system/invocation.html)
-   [QEMU system
    manual](https://www.qemu.org/docs/master/system/qemu-manpage.html)
-   [Linux KVM documentation](https://www.linux-kvm.org/)

### noVNC

-   [noVNC GitHub repository](https://github.com/novnc/noVNC)
-   [noVNC project documentation](https://novnc.com/)
-   [Websockify](https://github.com/novnc/websockify)

### Ubuntu images

-   [Ubuntu 24.04 release directory](https://releases.ubuntu.com/24.04/)
-   [Xubuntu 24.04.5 release
    directory](https://cdimage.ubuntu.com/xubuntu/releases/24.04.5/release/)
-   [Kubuntu 24.04.5 release
    directory](https://cdimage.ubuntu.com/kubuntu/releases/24.04.5/release/)
-   [Lubuntu 24.04.5 release
    directory](https://cdimage.ubuntu.com/lubuntu/releases/24.04.5/release/)

### Windows

-   [Microsoft Windows 11 Enterprise Evaluation
    Center](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise)
-   [Microsoft Windows
    downloads](https://www.microsoft.com/software-download/)
-   [VirtIO Windows drivers](https://github.com/virtio-win/virtio-win)

### Development and hosting

-   [GitHub Codespaces
    documentation](https://docs.github.com/en/codespaces)
-   [GitHub Pages documentation](https://docs.github.com/en/pages)
-   [VS Code Remote
    Development](https://code.visualstudio.com/docs/remote/remote-overview)
-   [code-server](https://github.com/coder/code-server)

------------------------------------------------------------------------

## License and responsibility

This guide and the example script are provided as a starting point.
Review, test and adapt them before use. QEMU, KVM, noVNC,
operating-system images and other dependencies have their own licenses
and terms. You are responsible for complying with the applicable
software licenses, image distribution terms, cloud-provider policies and
security requirements.
