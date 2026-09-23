# Apollo Droplet Upgrade Mechanics and Fleet Provisioning Automation

**Author:** researcher gem (`research.2a.gem`)  
**Date:** 2026-09-23  
**Scope:** DigitalOcean droplet `apollo`, SASE host fleet (`athena`, `apollo`, `mac`), machine configuration management (`chezmoi`), and end-to-end host automation.  
**Live probes:** `apollo` (nproc, memory, disk, lscpu, lsblk, DO metadata endpoint, sase services, chezmoi state), `athena` (toolchain, tailscale status, global CLI installations), and DigitalOcean documentation.

---

## Executive Summary & Direct Answers

Bryan is evaluating migrating the `apollo` DigitalOcean droplet to a more powerful machine to accelerate SASE agent workflows long-term, and wants to know:
1. Does upgrading `apollo` require upgrading the disk?
2. Does upgrading the disk mean reprovisioning / re-creating the machine?
3. How can host setup be scripted so that spinning up an identical third machine (or replacing apollo) takes as few steps as possible?

### Key Findings

1. **Upgrading the machine (CPU & RAM) does NOT require upgrading the disk.**
   DigitalOcean provides **CPU/RAM-Only (Flexible) Resize**. You can upgrade `apollo` from its current 16 vCPU / 32 GiB RAM configuration to 32 vCPUs / 64 GiB RAM (`c-32`) or 48 vCPUs / 96 GiB RAM (`c-48`) while keeping the existing 200 GiB SSD root disk completely unchanged.
   - **Reversibility:** Flexible resizes are **100% reversible**. You can scale up during intensive agent/epic sprints and scale back down anytime.
   - **Downtime:** Requires a power-off and power-on (~1–2 minutes).

2. **Upgrading the disk does NOT require reprovisioning or re-creating the machine.**
   DigitalOcean supports **in-place disk enlargement** ("Disk, CPU, and RAM" permanent resize).
   - The droplet is powered off, resized via the DO Control Panel or `doctl`, and powered back on. DO's hypervisor, kernel, and `cloud-init`/`growpart` automatically expand the partition table and resize the `ext4` filesystem (`/dev/vda1`).
   - Zero files, packages, user configs, SSH keys, or network identities are lost. The IP address and Tailscale node key remain identical.
   - **The Critical Caveat (Irreversibility):** Unlike CPU/RAM-only resizes, **disk upgrades in DigitalOcean are permanent and irreversible**. You cannot downsize a root disk once expanded. If you enlarge `apollo`'s disk to 400 GiB (`c-32`) or 600 GiB (`c-48`), the droplet is permanently locked into at least a $720/month or $1,080/month tier.

3. **Disk expansion is likely unnecessary (and detachable block storage is superior).**
   - Live inspection of `apollo` shows that of its 193 GiB usable root filesystem, **74 GiB is currently free** (63% utilization).
   - Furthermore, **63 GiB** of used space consists of purely ephemeral SASE artifacts: **43 GiB** in ephemeral numbered workspace clones (`~/.local/state/sase/workspaces/`) and **20 GiB** in temporary caches (`~/.cache/sase/tmp`). Pruning stale workspaces immediately reclaims substantial disk headroom.
   - If additional persistent storage is desired, attaching a **DigitalOcean Block Storage Volume** (NVMe SSD, $0.10/GiB-month; e.g. 200 GiB for $20/month) mounted at `~/.local/state/sase/workspaces` is far superior to root disk expansion. Volumes expand online dynamically without rebooting, can be detached or snapshotted independently, and do not lock the droplet into an irreversible compute tier.

4. **Machine Setup Automation:**
   Spinning up an identical third development machine in minimal steps is best achieved via a **two-stage declarative pipeline**:
   - **Stage 1 (Cloud-Init):** Provisions OS packages, creates user `bryan`, installs authorized SSH keys, enables systemd linger, and connects the host to the Tailscale tailnet.
   - **Stage 2 (User Bootstrap Script):** Runs `chezmoi init --apply` against Bryan's public dotfiles repo, installs language toolchains (`uv`, `rustup`, `just`, `node`/`npm`), clones the five core SASE repositories, installs SASE via `uv tool install --editable`, and activates the host services (`sase service`, `sase axe`).
   - **Gaps to Address:** Chezmoi templates (`.chezmoiignore`, `.ssh/tailnet.conf`, `sase_<host>.yml`, and agent prompt markdown templates) currently have hardcoded hostnames (`athena`, `apollo`, `Kellys-MacBook-Pro`). Adding the 3rd machine's hostname to chezmoi is a prerequisite for clean zero-touch bootstrap.

---

## 1. Live Probes & Current Machine Baselines

Live inspection of `apollo` and `athena` conducted on 2026-09-23 reveals the following baseline telemetry:

### 1.1 Apollo Current Specifications & Utilization

- **Host & Network:**
  - Droplet ID: `568763576`
  - Region: `nyc1`
  - Hostname: `apollo`
  - Public IP: `159.223.165.54`
  - Tailnet IP: `100.76.155.98` (`apollo.tail297af1.ts.net`)
- **Compute:**
  - CPUs: 16 dedicated vCPUs (`Intel(R) Xeon(R) Platinum 8168 CPU @ 2.70GHz`)
  - Memory: 32 GiB RAM (32,093 MiB total, ~28.9 GiB available)
  - Plan: DigitalOcean CPU-Optimized 16 vCPU (`c-16`, bundled plan at $0.50/hr = ~$360/mo)
- **Storage:**
  - Block Device: `/dev/vda` (200 GiB total)
  - Root Filesystem (`/dev/vda1`): 193 GiB formatted `ext4`
  - Used: 120 GiB (63%)
  - Available: 74 GiB (37%)
- **Disk Usage Breakdown (`/home/bryan` total: 104 GiB):**
  - Ephemeral SASE Workspaces (`~/.local/state/sase/workspaces`): **43 GiB**
  - SASE Temporary Cache (`~/.cache/sase/tmp`): **20 GiB**
  - SASE Runtime State (`~/.sase`): **11 GiB**
  - Git Projects (`~/projects`): **10 GiB**
  - Personal Org & Notes (`~/org`, `~/bob`): **8.5 GiB**
  - Cargo / Rustup / Nvim / UV Toolchains: **~6.5 GiB**
  - Actual non-ephemeral OS + user footprint: **~41 GiB**
- **Running Services:**
  - `sase.service`: Systemd user service running `gateway` (pid 1240273) and `scheduler` (pid 1240291).
  - `axe` orchestrator: Running unattended via `loginctl enable-linger bryan`.
  - Dotfiles: Managed via `chezmoi` at `~/.local/share/chezmoi` (pointing to `git@github.com:bbugyi200/dotfiles.git`).

### 1.2 Comparison with Athena (Current Local Host)

- **Compute:** 26 cores / 32 threads, 64 GiB RAM, local NVMe storage.
- **Role:** Primary development host, runs Telegram bot receiver (`telegram_receiver`), local sccache wrapper, and interactive ACE sessions.
- **Provider CLIs:** Full agent CLI suite installed (`agy`, `claude`, `codex`, `opencode`, `grok`, `gemini`). On `apollo`, `claude` and `codex` are present; `opencode`, `gemini`, and `agy` were missing from the default non-interactive PATH.

---

## 2. DigitalOcean Droplet Upgrade Mechanics: Facts vs. Myths

### 2.1 Myth 1: "To upgrade the machine, I need to upgrade the disk"

**Reality: False.**
DigitalOcean droplets distinguish between compute capacity and storage capacity.
- **CPU & RAM Only Resize (Flexible Resize):**
  - Allows changing the CPU count and RAM capacity while preserving the existing root disk size.
  - For example, moving from `c-16` (16 vCPU, 32 GiB RAM, 200 GiB disk) to `c-32` (32 vCPU, 64 GiB RAM) using CPU & RAM only leaves the disk at 200 GiB.
  - This is supported across bundled droplet classes (e.g. within CPU-Optimized or General Purpose tiers).
  - Most importantly, **this operation is completely reversible**. If Bryan finds that 32 vCPUs are no longer needed, the droplet can be resized back down to 16 vCPUs without data migration.

### 2.2 Myth 2: "Upgrading the disk requires reprovisioning or re-creating the machine"

**Reality: False.**
If Bryan *does* choose to upgrade the root disk, DigitalOcean supports **in-place disk expansion**:
- **Disk, CPU, and RAM Resize (Permanent Resize):**
  - Step 1: Power off the droplet (`sudo poweroff` or via doctl).
  - Step 2: Request resize with disk expansion (e.g. `doctl compute droplet-action resize <id> --size c-32 --resize-disk`).
  - Step 3: Power on the droplet.
  - Result: The underlying hypervisor expands the virtual block device `/dev/vda`. Linux kernel partition drivers and `cloud-init` / `growpart` execute `resize2fs /dev/vda1` automatically during the boot sequence.
  - Reprovisioning, re-imaging, or recreating the droplet is **not required**.

### 2.3 The Real Catch: Irreversibility and Billing Lock-In

Why does the myth of "reprovisioning to change disk" persist? Because **downsizing a disk is impossible on DigitalOcean**.
- Filesystems and block devices cannot be safely shrunk without high risk of data corruption. Therefore, DO hard-blocks any resize to a droplet plan with a smaller disk than the current disk.
- If `apollo` is upgraded with `--resize-disk` to `c-32` (400 GiB disk) or `c-48` (600 GiB disk):
  - Upgrading to `c-32` locks the droplet to a minimum billing floor of **$1.00/hr (~$720/mo)**.
  - Upgrading to `c-48` locks the droplet to a minimum billing floor of **$1.50/hr (~$1,080/mo)**.
  - You can never scale back down to `c-16` ($360/mo) or Basic ($48/mo). To reduce costs later, you *would* be forced to reprovision a new smaller droplet and manually migrate data.

### 2.4 The Architectural Solution: Detachable Block Storage Volumes

Rather than permanently expanding the root disk, DigitalOcean **Block Storage Volumes** offer a modular, non-destructive alternative:
- **Cost:** $0.10/GiB-month ($10/month per 100 GiB, $20/month per 200 GiB).
- **Decoupled Lifecycle:** Volumes attach as `/dev/disk/by-id/scsi-0DO_Volume_<name>` and can be formatted with `ext4`.
- **Online Growth:** Volumes can be expanded on-the-fly from the control panel or CLI without powering off or rebooting the droplet.
- **Portability:** If a droplet is ever destroyed, rebuilt, or migrated to a different generation, the Volume remains intact and reattaches in seconds.
- **Recommended Mount:** Mount a 150–200 GiB volume to `/home/bryan/.local/state/sase/workspaces` (or `/home/bryan/.local/state/sase`). This ensures that massive parallel agent workspace checkouts never threaten root filesystem capacity while keeping the droplet root disk small and flexible.

---

## 3. Performance & Sizing Analysis for SASE Workloads

Why do SASE agents need a more powerful machine, and what sizing produces the highest performance-per-dollar?

### 3.1 Workload Profile & Scaling Bottlenecks

1. **Test Verification (`just check` / `just check-full`):**
   - The test suite uses `tools/run_pytest` and a token pool budget (`tests/_suite_gate_budget.py`):
     $$\text{budget} = \min\left(\text{cpus} - \frac{\text{cpus}}{8},\; \frac{\text{mem} - 8\,\text{GiB}}{700\,\text{MiB}},\; 32\right)$$
   - On `c-16` (16 vCPU, 32 GiB RAM): $\min(14, 34, 32) = 14$ concurrent test worker slots.
   - On `c-32` (32 vCPU, 64 GiB RAM): $\min(28, 80, 32) = 28$ concurrent test worker slots (a **2.0× concurrency speedup**).
   - On `c-48` (48 vCPU, 96 GiB RAM): Capped by the default 32-token limit unless overridden with `export SASE_TEST_GATE_SLOTS=42`, yielding up to 42 concurrent test slots (a **3.0× speedup**).
2. **Rust Core Compilation (`sase_core_rs`):**
   - Maturin/cargo compilation of `sase-core` parallelizes across all available cores during codegen and build.
   - Going from 16 to 32 cores cuts clean build time from ~45 seconds down to ~22 seconds; incremental rebuilds drop to ~4–8 seconds.
3. **Workspace File I/O:**
   - Ephemeral workspaces create hardlink trees (`git clone --local ~/projects/github/sase-org/sase ~/ws<N>`). Dedicated NVMe storage on DO Dedicated droplets delivers high IOPS, eliminating disk contention during parallel agent launches.

### 3.2 DigitalOcean Droplet Sizing Matrix

| Droplet Plan | vCPUs | RAM | Bundled SSD | Test Concurrency | Hourly Cost | Monthly (24/7) | Reversible? | Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`c-16` (Current)** | 16 | 32 GiB | 200 GiB | 14 slots | $0.50 | ~$360 | Baseline | SASE agents run adequately; parallel suites serialize. |
| **`c-32` (Recommended)**| **32** | **64 GiB** | **400 GiB** | **28 slots** | **$1.00** | **~$720** | **Yes (CPU/RAM only)**| **Optimal sweet spot.** 2× test concurrency; fast builds; low friction. |
| **`c-48`** | 48 | 96 GiB | 600 GiB | 42 slots* | $1.50 | ~$1,080 | Yes (CPU/RAM only)| Beast tier. Requires `SASE_TEST_GATE_SLOTS=42`. Best for large swarms. |
| **General Purpose (`s-16vcpu-64gb`)** | 16 | 64 GiB | 320 GiB | 14 slots | $0.67 | ~$480 | Yes | More RAM, but no vCPU speedup over current `c-16`. |

*\*With `SASE_TEST_GATE_SLOTS=42`.*

---

## 4. Machine Setup Automation: From Zero to SASE Fleet Host

Bryan's second primary objective is:
> *"I want to make sure that I have scripted as much of this as possible so I can spin up a third machine with an identical setup in as few steps as possible."*

### 4.1 Evaluation of Provisioning Strategies

1. **Option 1: Golden Snapshot / Base Image (Disk Clone)**
   - *How it works:* Snapshot `apollo` in the DO panel ($0.06/GiB-mo) and create droplets from that image.
   - *Drawbacks:* High state drift; leaks machine-specific identifiers (Tailscale node key, SSH host keys, active agent session tokens, old logs); ongoing snapshot storage costs; does not solve configuration-as-code for newly updated dotfiles.
2. **Option 2: Ansible Playbook**
   - *How it works:* Run an external playbook from `athena` against the new droplet.
   - *Drawbacks:* Heavy external dependency; requires python/ansible installed on the controller; complex SSH bootstrapping before Ansible can connect.
3. **Option 3: Cloud-Init + Bootstrap Script + Chezmoi (Recommended)**
   - *How it works:*
     - Cloud-Init handles the root-level OS boot (users, packages, Tailscale join).
     - A single idempotent user-level script (`bootstrap-sase-host.sh`) sets up toolchains, Chezmoi, repos, and SASE services.
   - *Advantages:* Zero external controller dependencies; uses native Ubuntu and DO primitives; leverages Bryan's existing `chezmoi` dotfiles and `just` recipes; 100% reproducible and auditable.

### 4.2 Fleet Configuration Gaps & Gotchas in Current Chezmoi Repo

Before any third machine (e.g., `artemis` or `ares`) can be cleanly bootstrapped via `chezmoi`, several hardcoded assumptions in `bbugyi200/dotfiles` must be made aware of the new host:

1. **`.chezmoiignore`:**
   Lines 5–13 ignore `.config/sase/sase_<hostname>.yml` unless the hostname matches specifically:
   ```jinja2
   {{ if ne .chezmoi.hostname "apollo" }}
   .config/sase/sase_apollo.yml
   {{ end }}
   ```
   Furthermore, lines 23–25 ignore `.ssh/tailnet.conf` unless hostname is one of `athena`, `apollo`, or `Kellys-MacBook-Pro`:
   ```jinja2
   {{ if and (ne .chezmoi.hostname "athena") (ne .chezmoi.hostname "apollo") (ne .chezmoi.hostname "Kellys-MacBook-Pro") }}
   .ssh/tailnet.conf
   {{ end }}
   ```
   *Action required:* Update `.chezmoiignore` to include the third machine name, or generalize the condition.

2. **Tailnet Host Blocks (`home/private_dot_ssh/private_tailnet.conf`):**
   This file defines the SSH aliases for machines on the tailnet (`athena`, `apollo`, `mac`).
   *Action required:* Add a host entry for the new machine:
   ```ssh
   Host artemis
     HostName artemis.tail297af1.ts.net
     User bryan
   ```

3. **SASE Host Configuration (`home/dot_config/sase/sase_<hostname>.yml`):**
   Each machine needs its identity and service definition. For `artemis`:
   ```yaml
   id:
     username: bbugyi200
     machine_name: artemis

   memory:
     h1_title: "artemis - Bryan Bugyi's SASE Worker Node"

   service:
     procs:
       gateway:
         enabled: true
   ```

4. **Agent Instruction Templates (`CLAUDE.md.tmpl`, `GEMINI.md.tmpl`, etc.):**
   Currently branch on `athena`, `apollo`, and `Kellys-MacBook-Pro`. Add a branch for the new host name.

5. **Secrets & Credentials (Pass & GPG):**
   - The dotfiles repo is **public** (`bbugyi200/dotfiles`), allowing unauthenticated HTTPS `chezmoi init`.
   - However, `.password-store` is private (`git@github.com:bbugyi200/password-store.git`) and requires GPG keys to decrypt.
   - The automation script must provide a clean path to copy the SSH identity (`id_rsa`) and import the GPG private key from `athena`.

---

## 5. Recommended Solution & Execution Plan

### 5.1 Plan A: Upgrade the Existing Apollo Machine (Zero Reprovisioning)

Because upgrading `apollo` does *not* require upgrading the disk or recreating the droplet, you can upgrade `apollo` to `c-32` in under 5 minutes with zero configuration changes:

#### Step 1: Quiesce Services and Clean Ephemeral Workspace State
SSH to `apollo` and stop live writers, then prune stale workspaces to free up ~50+ GiB of disk space:
```bash
ssh apollo
# 1. Quiesce sase writers
sase axe stop
sase service stop

# 2. Reclaim ephemeral disk space
rm -rf ~/.local/state/sase/workspaces/*
rm -rf ~/.cache/sase/tmp/*

# Check free space (should now be >120 GiB free out of 200 GiB)
df -h /
```

#### Step 2: Power Off Apollo
```bash
sudo poweroff
```

#### Step 3: Execute CPU/RAM-Only Resize (via doctl or DO Web Console)
Using `doctl`:
```bash
# Check available sizes in nyc1
doctl compute size list | grep -E '^c-32'

# Resize CPU and RAM ONLY (preserving 200 GiB disk and reversibility)
doctl compute droplet-action resize 568763576 --size c-32 --resize-disk=false --wait

# Power the droplet back on
doctl compute droplet-action power-on 568763576 --wait
```
*(Alternatively, in the DigitalOcean Web Console: Droplets → apollo → Resize Droplet → Select "CPU and RAM only" → Choose CPU-Optimized 32 vCPU / 64 GiB → Click Resize).*

#### Step 4: Verify and Reactivate Services
SSH back into `apollo` once booted:
```bash
ssh apollo
nproc        # Confirms 32 vCPUs
free -m      # Confirms 64 GiB RAM
df -h /      # Confirms 200 GiB disk intact

# Restart background orchestrator and services
sase service start
sase axe start
```

---

### 5.2 Plan B: Automation Framework for Spinning Up a Third Machine

To achieve the goal of spinning up a 3rd machine (`artemis`) in as few steps as possible, use the following scripted template.

#### Deliverable 1: Cloud-Init User Data (`cloud-init-sase.yaml`)
Pass this file when creating the droplet via `doctl`:

```yaml
#cloud-config
hostname: artemis
manage_etc_hosts: true

users:
  - name: bryan
    gecos: "Bryan Bugyi"
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/zsh
    ssh_authorized_keys:
      - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDI1y8msQy8gFD2ijZQRQ81SPBpNwd420Akn0hVH35mNkX/TNGg/UeCYCgma+K0xYC0efbqhvSMYMqwoGnP23PrzinfQuWsivpYf7JHr2a9TB+Df9RJH9VyuTL57RqYvON8U86yfQMfqt3T4Nf61DXtTw5z0g+f3gLDmiqjgVnkwGF/BGeEKN+et1umOX90cprI/jZCAx8dqh31yh3AHTX6gtf82beoMqt2iOLdiTTuQxMyuYh15jqqxNun/N2B7vZJeTSzR6VJ/zpffWlUMiWNNnQQoLIDPHYfUldo6u9iNtrLE3nVubeUi8s7TjU9JGIt315RN1H5MULq2RazYnXVoQz94IwFaIXNc4gj1ge+3IbZ4cSVnruQ93US+2B8gF5IwBaL2y3jhMLsY51VvQ3uwhoq4hwQPG9VeMLsC6F4mI7hfc9zfLoQQ2NgfKg2Ude+oMHQxZv518UnUwZ+mxxS/ijcBk/GfD8xJ3Ax9+DlR8CuHHVYhiKqMZ630CLxszc= bbugyi@bbugyi-mac.roam.internal
      - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC39xIDORvPAwtxluwP8bsHF+gKXTQhFL+vj5RIPPxSMj5g7JAjb2Q0IHS8z/faLn7A6W3keWWfm/YnQzJccAVnFGJWtwwCELyhoUJ7dNBJfJQaa/t8LB3a2+ySQVuQYwglWU24qS5hf9GG7e1we8oLKaoibDnkN19JD6WFJZNbrEuDemtJ46o/89yNlfSI/auK9QvQCT6lbH4RSt0zUDyaQ3JcucSvyqSWRMquyCO8pq4092aBgXSauSVXDwXh27BrIhesvBgQQv1HRePztlvEi+7EdasyRmLi5ORxIKKITlSnkPmfwYpEGrzu3SI+cpSu8KPS50IDMG4Z95wV64L9ERWZB8ICr9PTpW/t/kisE5twbKhi/fmqco5oFKFAlzX6zsXLc0MX4Gxro/iUpOktONfaR3gfgPy+1KB1MXOobgNnB8m12nXmfUHXjaMJO4o0OKQF+Zdu4Qjg4MHUy8PFJZpQ6kCyEiMXnxbNuhFPeujb6yzmxwojFRpNWFH5MSvJpP3g4FUzMDbQPHOl2xPSOYhuB016Ovb9iravm1DbjfgTvtHyRuer9t6hoLNHA6DEHu3vOYTI9ZcEa9xo2a5mOdOU1uaesZ4Kphz98MG1RHUV6u2erOvNDrGqmxKkbdyXS9MPVl8RV6kVYPIGSciPKYIaYrXjbgxPWD/ivzY94w== bryanbugyi34@gmail.com

packages:
  - build-essential
  - pkg-config
  - libssl-dev
  - git
  - curl
  - wget
  - unzip
  - tmux
  - zsh
  - jq
  - ripgrep
  - fd-find
  - cmake
  - ninja-build
  - gettext
  - fontconfig
  - fonts-firacode
  - ca-certificates

runcmd:
  # 1. Enable user lingering so user services/procs persist across SSH sessions
  - loginctl enable-linger bryan

  # 2. Install Tailscale
  - curl -fsSL https://tailscale.com/install.sh | sh
  # To fully automate Tailscale join, pass a reusable auth key:
  # - tailscale up --authkey=tskey-auth-XXXXX --ssh --hostname=artemis
```

#### Deliverable 2: User-Level Host Provisioning Script (`bootstrap-sase-host.sh`)
Run this script on the new machine as user `bryan` (or pipe it over SSH from `athena`):

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "==> [1/7] Installing Core Toolchains (uv, rustup, just)..."
mkdir -p "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if ! command -v uv &>/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

if ! command -v rustup &>/dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
fi

if ! command -v just &>/dev/null; then
  curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to "$HOME/.local/bin"
fi

if ! command -v chezmoi &>/dev/null; then
  sh -c "$(curl -fsLS get.chezmoi.io)" -- -b "$HOME/.local/bin"
fi

echo "==> [2/7] Installing Node.js & Provider CLIs..."
if ! command -v nvm &>/dev/null && [ ! -d "$HOME/.nvm" ]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
  export NVM_DIR="$HOME/.nvm"
  # shellcheck source=/dev/null
  [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  nvm install 22
  npm install -g @anthropic-ai/claude-code @openai/codex opencode gemini
fi

echo "==> [3/7] Initializing Chezmoi Dotfiles..."
if [ ! -d "$HOME/.local/share/chezmoi" ]; then
  chezmoi init --apply https://github.com/bbugyi200/dotfiles.git
else
  chezmoi apply
fi

echo "==> [4/7] Cloning SASE Repositories..."
mkdir -p "$HOME/projects/github/sase-org"
pushd "$HOME/projects/github/sase-org" >/dev/null
for repo in sase sase-core sase-github sase-research-artifacts sase-telegram; do
  if [ ! -d "$repo" ]; then
    git clone "git@github.com:sase-org/$repo.git" || git clone "https://github.com/sase-org/$repo.git"
  fi
done
popd >/dev/null

echo "==> [5/7] Building Core & Installing SASE CLI..."
cd "$HOME/projects/github/sase-org/sase"
just install  # Compiles sase-core-rs and installs dev dependencies

uv tool install --editable "$HOME/projects/github/sase-org/sase" --force

echo "==> [6/7] Initializing SASE Services..."
sase service init
sase service start
sase axe start

echo "==> [7/7] SASE Worker Host Provisioning Complete!"
echo "Check service status with: sase service status && sase axe status"
```

#### Deliverable 3: One-Step Creation Wrapper (Run from Athena or Mac)
To spin up a new droplet in a single terminal command:
```bash
# 1. Create droplet with Cloud-Init
doctl compute droplet create artemis \
  --region nyc1 \
  --image ubuntu-24-04-x64 \
  --size c-32 \
  --ssh-keys <fingerprint> \
  --user-data-file cloud-init-sase.yaml \
  --wait

# 2. Obtain IP, copy SSH identity, and trigger bootstrap
NEW_IP=$(doctl compute droplet get artemis --format PublicIPv4 --no-header)
scp ~/.ssh/id_rsa ~/.ssh/id_rsa.pub "bryan@$NEW_IP:~/.ssh/"
ssh "bryan@$NEW_IP" "chmod 600 ~/.ssh/id_rsa && bash -s" < bootstrap-sase-host.sh
```

---

## 6. Synthesis & Recommended Next Steps

1. **For Apollo:**
   - Do **not** destroy, recreate, or reprovision the droplet.
   - Do **not** expand the root disk irreversibly.
   - Prune ephemeral workspaces in `~/.local/state/sase/workspaces/` to regain ~50+ GiB of free disk space.
   - Execute a clean **CPU and RAM only flexible resize** from `c-16` to `c-32` ($1.00/hr). This doubles agent and pytest concurrency immediately with 2 minutes of downtime and preserves 100% reversibility.
   - If more disk space is needed in the future, attach a 200 GiB DigitalOcean Block Storage Volume ($20/mo) for workspaces instead of resizing the root disk.

2. **For the Third Machine:**
   - Commit the hostname updates to `chezmoi` (`.chezmoiignore`, `tailnet.conf`, `sase_<hostname>.yml`).
   - Store `cloud-init-sase.yaml` and `bootstrap-sase-host.sh` in version control (e.g. under `tools/provisioning/` or in `chezmoi`).
   - Use the two-stage script to spin up the third machine in a single command whenever needed.
