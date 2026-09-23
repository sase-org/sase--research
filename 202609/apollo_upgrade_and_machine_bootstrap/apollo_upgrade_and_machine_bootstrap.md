# Upgrading Apollo Into A Permanent Second Dev Machine, And Scripting Its Rebuild

**Question:** apollo, the DigitalOcean droplet, is going to be a long-term second
development machine instead of a temporary one, and it needs to be faster for SASE
agents. Does upgrading it mean growing the disk, and does that mean re-creating the
droplet? And how should the setup be scripted so that a third, identical machine takes
as few steps as possible?

**Date / scope:** 2026-09-23. This merges three independent reports (`__cld`, `__mus`,
`__gem` in this directory) with the lead researcher's own checks:

- read-only probes of apollo: uv tool receipt, chezmoi source, `sase disk list`,
  sysstat, systemd units, identity files, CLI install paths
- the linked chezmoi repo (`bbugyi200/dotfiles` @ `d02225f4`)
- sase `docs/remote_dispatch.md` and `tests/_suite_gate_budget.py`
- DigitalOcean, Tailscale, chezmoi and Hetzner docs, re-fetched today

It builds on the 2026-09-03 report `research:202609/temporary_high_capacity_test_machine.md`.
Prices and plan rules change often, so re-confirm them in the create or resize dialog
before you pay.

---

## Bottom Line

**No. Upgrading apollo doesn't require re-creating it, and more CPU and RAM don't
require more disk either.**

- **CPU and RAM only (c-16 → c-32):** DigitalOcean does this resize in place and it is
  reversible. The disk stays at 200 GB. The docs only require that the target plan's
  disk be at least the current one ("You can resize to any Droplet plan that has an
  equal or greater amount of disk space"), and c-32's 400 GB qualifies.
- **Disk, CPU and RAM:** also in place, but permanent. Apollo doesn't need it: the disk
  has 74 GB free, and CPU is the bottleneck.
- **What actually forces a new droplet:**
  - moving to DO's new **v5** droplets (5th-gen AMD EPYC, GA 2026-08-26). "You cannot
    resize between v5 configurations and bundled plans."
  - changing region. v5 is only offered in ATL1, RIC1, MEM1 and MKC1, not NYC1.
  - shrinking the disk.

**Apollo today:**

- It is CPU-Optimized **`c-16`**: 16 vCPU on a 2017 Skylake Xeon, 32 GiB RAM, 200 GB
  disk, $336/mo.
- The September "temporary" upgrade already grew the disk from 160 to 200 GB. That
  growth is permanent, but it is **not a cost lock-in**: CPU and RAM can still shrink to
  any bundled plan with a disk of at least 200 GB, and those start at about $64–84/mo.
- **Apollo is CPU-bound at only 5 concurrent agents.** On 09-21 the CPU was 81% busy on
  average and the 1-minute load peaked at 57 on 16 vCPUs. Free RAM has dipped to
  3.8 GiB, and there is no swap.
- **Most of the setup isn't scripted.** Chezmoi covers dotfiles and a few user-level
  installers. Nothing covers system packages, Tailscale, the toolchains, the SASE repos
  and install, the service host, Tailscale Serve, the Bob vault sync, or secrets.

**Recommendation:**

1. **Today, resize apollo in place, CPU and RAM only, to `c-32`.** Also add swap and
   raise the agent limit. This takes 30–60 minutes, is reversible, and needs no rebuild.
2. **Write the machine setup as a layered bootstrap in the chezmoi repo:** `doctl` →
   cloud-init → chezmoi package lists → a secrets hand-off plus a short list of logins →
   a SASE host-setup script → a `doctor` check.
3. **Prove the bootstrap on two throwaway droplets and benchmark them at the same
   time:** a `c-32`, and a v5 `g5-24vcpu-64gb-300gb`. This takes about 2 hours and costs
   under $6.
4. **If g5 wins clearly, rebuild apollo on v5 with the automation**: build it side by
   side, cut over, then destroy the old droplet. If not, keep the resized apollo.

Either way, a third machine then takes about five commands plus roughly 10 minutes of
interactive logins.

---

## 1. Apollo Today (Verified 2026-09-23)

| Property | Value | Evidence |
| --- | --- | --- |
| Plan | CPU-Optimized `c-16`: 16 dedicated vCPU / 32 GiB / 200 GB SSD, $0.50/h, **$336/mo** (the 672 h monthly cap applies) | `nproc`, `free`, `lsblk`; DO pricing page |
| CPU | Intel Xeon Platinum 8168 @ 2.70 GHz (Skylake-SP, 2017) | `lscpu` |
| Disk | `/dev/vda1` 193 G, 120 G used (63%), 74 G free; was 160 GB on 09-03, so a permanent resize already happened | `df` |
| Region / ID | `nyc1` / droplet `568763576`; public IP 159.223.165.54 (the `apollo-do` SSH alias) | DO metadata, chezmoi `private_tailnet.conf` |
| OS / swap / sudo | Ubuntu 24.04.3; **no swap**; sudo **requires a password**, which fits the `/sase_sudo` gate model | `free`, `swapon`, `sudo -n true` |
| Agent limit | `~/.sase/max_running_agents_override.json` → `limit: 5` | file |

**Where the 120 GB goes:**

| Path | Size | Notes |
| --- | --- | --- |
| `~/.local/state/sase/workspaces/sase-org/sase` | 42 GB | 17 checkouts, uneven: `sase_16` is 11 GB and `sase_10` is 9.5 GB |
| `~/.cache/sase/tmp` | ~19–20 GB | `sase disk list` shows this as managed tmp with a **3-day horizon**, so it's a steady-state rolling footprint, not a one-off cleanup win. The uv cache is only 325 MB. |
| `~/.sase` | 11 GB | `projects` 6.6 GB; `cache` 3.2 GB, including ~3 GB of Rust prebuilds (keeps the newest 2 sets) |
| `~/projects`, `~/org` + `~/bob`, toolchains | ~10 / ~8.5 / ~6.5 GB | |

**Load (sysstat, 10-minute samples):**

| Day | Mean CPU busy | Saturated samples (<10% idle) | Max 1-min load (16 vCPU) | Min available RAM |
| --- | --- | --- | --- | --- |
| 09-17 | 26% | 2 / 144 | 21.2 | **3.8 GiB** |
| 09-18 | 55% | 30 / 144 | 35.4 | 7.0 GiB |
| 09-21 | **81%** (41% of it `nice`, i.e. test workers) | **61 / 144** | **57.0** | 5.0 GiB |
| 09-22 | 22% | 3 / 144 | 24.8 | 12.7 GiB |

- `__cld` supplied these figures. The 09-18, 09-21 and 09-22 rows were spot-checked
  and match.
- I/O wait stays under ~6%, so disk speed isn't the constraint.
- More cores help throughput. Faster cores also shorten each agent's `just check`,
  `mypy` and cargo builds.

**Roles a replacement must reproduce:**

- `sase.service`: a user unit with linger enabled. It runs the gateway on
  `127.0.0.1:7629` plus the scheduler, and `sase_apollo.yml` enables the gateway.
- **Tailscale Serve** on `https://apollo.tail297af1.ts.net`. Athena has enrolled apollo
  there by installation pin.
- `bob-vault-sync.service`.
- An ordinary dev box: `~/org`, `~/.password-store`, `~/bob` and `~/projects`.

---

## 2. Where The Reports Disagreed, And What Is Actually True

| Topic | Claims | Verdict (lead verification) |
| --- | --- | --- |
| Is apollo managed by chezmoi? | mus: "no dotfiles manager". cld and gem: chezmoi. | **Chezmoi.** `~/bin/chezmoi`, with its source at `~/.local/share/chezmoi` (remote `bbugyi200/dotfiles`). mus probed a non-login `PATH`, which doesn't include `~/bin`. |
| How is SASE installed? | mus: the published wheel. cld and gem: editable. | **Editable.** The uv receipt shows `sase` plus the github, telegram and research-artifacts plugins as editable installs from `~/projects/github/sase-org/*`, with `sase-core-rs` built from source. That's `install_sase_github -i`. |
| What is the 20 GB cache? | mus: the uv cache. gem: `~/.cache/sase/tmp`. | **`~/.cache/sase/tmp`**, which is managed and rolls over every 3 days. uv uses only 325 MB. |
| Prices | gem: $360 / $720 / $1,080 per month. cld: $336 / $672. | **$336 / $672 / $1,008** for c-16 / c-32 / c-48. Bundled plans cap billing at 672 h a month. |
| Does a disk resize lock in cost? | gem: a 400 GB disk locks you in at ≥$720/mo. | **Wrong.** The cheapest bundled plan with ≥400 GB is about $128/mo (`s-8vcpu-16gb-480gb-intel`), and with ≥200 GB about $64/mo. Only the disk is locked in, not the price tier. |
| Should apollo grow its disk? | mus: yes (Disk+CPU+RAM to c-32). gem and cld: no. | **No.** 74 GB is free, CPU is what's saturated, and the change can't be undone. It also buys nothing if apollo later moves to v5. |
| Use a volume for workspaces? | gem: a volume is "far superior" and "expands online". | **No.** Volumes are network-attached block storage, a poor fit for git- and cargo-heavy workspaces. The docs also say to *unmount* a volume before resizing it. Keep volumes as a fallback for bulk data only. |
| How to reclaim disk | gem: `rm -rf ~/.local/state/sase/workspaces/*` and `~/.cache/sase/tmp/*`. | **Unsafe.** Running agents claim those workspaces, and the registry tracks them. Use `sase disk reap` (a dry run unless you pass `--apply`), `sase workspace cleanup --stale`, and `sase workspace compact`. |
| Upgrade path | cld: rebuild on v5, resize as a stopgap. mus: in-place disk resize. gem: CPU/RAM-only resize plus a volume. | **Merged (see §7):** resize CPU/RAM only now, then let a measured bake-off decide whether to rebuild on v5. |
| Sudo on new hosts | gem: `NOPASSWD:ALL`. | **Keep password sudo.** Permanent NOPASSWD would let any agent run raw sudo and skip the reviewed `/sase_sudo` path. Use a temporary drop-in during bootstrap instead (§6.2). |
| Other gem bootstrap details | npm `opencode`, `gemini`; `nvm` in `~/.nvm`; start the service at once | **Wrong or risky:** <ul><li>the npm packages are `opencode-ai` and `@google/gemini-cli`</li><li>apollo's nvm lives in `~/.config/nvm`</li><li>starting the service while the old apollo is still live runs AXE twice</li></ul> gem's rust build timings and its "dedicated NVMe" claim for `c-16` have no source; c-16 regular runs on SSD. |

---

## 3. DigitalOcean Rules That Decide This (Docs, 2026-09-23)

| Change | In place? | Reversible? | Notes |
| --- | --- | --- | --- |
| CPU/RAM-only resize to a larger bundled plan (c-16 → c-32, c2-32, g-…) | **Yes** | **Yes** | Disk unchanged. Cross-type bundled resizes are allowed. |
| Disk+CPU+RAM resize | **Yes** | **No** | "You cannot decrease the size of a Droplet's disk." Take a snapshot first. |
| Bundled → v5 (`g5-*`, `s5-*`) | **No** | n/a | "Droplets created with a v5 configuration resize only to other v5 configurations…" |
| Region change (nyc1 → ric1/atl1) | **No** | n/a | Droplet snapshots can be copied to other regions. Reserved IPs **cannot** move between datacenters. |
| Shrink disk | **No** | n/a | Needs a new droplet plus a data migration. |

**Other facts that shape the plan:**

- **Resize downtime.** Every resize, even CPU/RAM-only, needs a power-off. Budget
  "about one minute … per GB of used disk" as the worst case, since the droplet may move
  hosts. That's up to ~2 h for apollo's 120 GB, though it's usually much shorter.
  Resizing through the API powers the droplet off for you.
- **Billing.**
  - Bundled plans bill per second, capped at 672 h a month. They still bill while
    powered off; billing stops only when you destroy the droplet.
  - Snapshots cost $0.06/GB-month. A 120 GB snapshot is about $7/mo, prorated.
  - Volumes cost $0.10/GiB-month.
- **v5 pricing** is per resource: $0.028/h per dedicated vCPU, $0.0040411/h per GiB of
  RAM, and $0.000137/h per GiB of NVMe boot disk.
  - **There is no monthly cap**, so a month is ~730 h, about 8.6% more than a bundled
    plan at the same hourly rate.
  - Shapes run from 2 to 64 vCPU at 2×–8× RAM per vCPU. Slugs look like
    `g5-<vcpus>vcpu-<mem>gb-<disk>gb`.
  - A v5 boot disk can only stay the same size or grow, so choose it deliberately.
  - Whether a specific shape is offered depends on region and capacity. Check with
    `doctl compute size list`.
- **user-data (cloud-init) runs only on first boot.** Any process on the droplet can
  read it through the metadata endpoint, so only put short-lived secrets in it.

---

## 4. Upgrade Options

| Option | Shape | ≈ $/mo | Per-core vs today | Re-create? | Test-gate tokens* |
| --- | --- | --- | --- | --- | --- |
| Today: `c-16` | 16 Skylake / 32 GiB / 200 GB | 336 | 1× | — | 14 |
| **A. CPU/RAM-only → `c-32`** | 32 Skylake-class / 64 GiB / *200 GB kept* | **672** | ~1× | **No** | 28 |
| A′. same, with disk | … / 400 GB | 672 | ~1× | No | 28 |
| B. CPU/RAM-only → `c2-32vcpu-64gb` (Premium Intel) | 32 newer Intel / 64 GiB | 752 | better (newer Intel generation) | No | 28 |
| **C. v5 `g5-24vcpu-64gb-300gb`** | 24 EPYC Zen 5 / 64 GiB / 300 GB NVMe | **~709** | much better (Skylake 2017 → Zen 5) | **Yes** | 21 |
| C′. v5 `g5-32vcpu-64gb-300gb` | 32 Zen 5 / 64 GiB / 300 GB | ~873 | same | Yes | 28 |
| D. Hetzner Cloud CCX43 / CCX53 (Ashburn) | 16 / 32 dedicated AMD, 64 / 128 GB | ~$329 / ~$635 | better | new vendor | — |
| E. Hetzner AX102-1 (EU bare metal) | Ryzen 9 7950X3D, 128 GB | ~$302 + $149 setup | very fast | new vendor, EU only | — |

\*`min(cpus − cpus/8, (mem − 8 GiB)/700 MiB, 32)` from `tests/_suite_gate_budget.py`.
The 32-token cap only matters above ~36 vCPU, where you would set
`SASE_TEST_GATE_SLOTS`.

- **Stay on DigitalOcean.** The account, SSH keys and billing already exist, per-second
  billing makes throwaway test droplets cheap, and `doctl` makes it scriptable. v5 fixes
  DO's main weakness, which is old CPUs.
  - Hetzner undercuts DO on RAM and disk per dollar even after its 2026-06-15 price
    increases, but it's a new account with new friction.
  - The automation below keeps only Layer 0 DO-specific, so switching later stays cheap.
- **Sizing target:** about twice today's effective compute plus 64 GiB. Then raise
  `max_running_agents` from 5 to about 10–12.
  - Add a 16 GiB swapfile either way.
  - On v5, choose ~300 GB of boot disk at about $30/mo. That covers today's 120 GB plus
    workspace growth when more agents run.
- **g5-24 vs c-32.** g5-24 grants fewer test tokens (21 vs 28) but each one runs much
  faster. It should win on per-agent latency, but that is an estimate. The bake-off in
  §7 measures it instead of trusting vendor claims.

---

## 5. What A Rebuild Must Reproduce

| Layer | What apollo has | Automated today? |
| --- | --- | --- |
| **Cloud resource** | Droplet, size, region; DO SSH keys; public IP hard-coded as `apollo-do` | No |
| **System (root)** | user `bryan` with zsh and sudo; apt packages (`zsh gh golang cmake pkg-config pass pipx pandoc tmuxinator trash-cli inotify-tools lua5.1 sysstat …`, plus probably vestigial `kitty wkhtmltopdf texlive x11-apps`); Tailscale; linger; unattended upgrades | **No** |
| **User toolchains** | <ul><li>uv</li><li>rustup plus ~25 cargo tools (`just atuin bat delta fd rg starship zoxide ruff … bob zorg`)</li><li>nvm in `~/.config/nvm` → node 24.15 → `claude`, `codex`</li><li>`agy`, `grok`, `muse` in `~/.local/bin`</li><li>oh-my-zsh, go</li></ul> | **Partly.** Chezmoi installs nvim, luarocks, lazygit, tpm, basher and bashunit. |
| **Dotfiles** | chezmoi, public repo, `.chezmoiroot = home` | **Yes** |
| **Host-specific config** | `sase_apollo.yml`; hostname guards in `.chezmoiignore`; `private_tailnet.conf`; `run_onchange_after_ensure_ssh_tailnet_include.tmpl` with literal `athena`/`apollo`/`Kellys-MacBook-Pro` | **Yes, but keyed to hostnames.** A new host means editing 3–4 files. |
| **SASE** | five public `sase-org` repos cloned; `install_sase_github -i`; `sase init`; `sase service init` plus the gateway proc; `tailscale serve --bg 7629`; bootstrap plus enrollment from athena | **Partly.** `install_sase_github` exists but **never clones**; it assumes the repos are already there. |
| **Secrets / logins** | `id_rsa`, `id_bob_vault`, GPG secret key (for `pass`), `gh` auth, Claude/Codex credentials, Tailscale node key | **No**, and it should stay that way |
| **Data** | `~/bob`, `~/org`, `~/.password-store`, `~/.sase` (11 GB) | No |
| **Drift to fix along the way** | <ul><li>`~/.ssh/config` holds `github-bob` and a stale `mac` block outside chezmoi</li><li>`~/org`'s remote is a **LAN IP** (`ssh://bryan@192.168.1.156:34857/…`)</li><li>stale root-installed `/usr/local/bin/claude` (2.1.126) and `codex` from May shadow nvm's copies (2.1.280) in non-login shells</li><li>`~/.sase/service/env` holds only `PATH`, pinned to `node/v24.15.0`, so it breaks on a node upgrade. Generate it; don't copy it.</li></ul> | — |

**Don't use a golden snapshot of apollo for new machines.** A snapshot carries:

- all of the drift above
- the Tailscale node identity in `/var/lib/tailscale`
- the SASE installation identity: `~/.sase/installation_identity.json`,
  `~/.sase/fleet_gateway/credentials.json` and `~/.sase/machine_name`
- OAuth refresh tokens, which invalidate each other when two machines share them

Keep snapshots only as a rollback archive.

---

## 6. Automation Design

### 6.1 Approach

| Approach | Verdict |
| --- | --- |
| **cloud-init (root, first boot) + chezmoi (declarative package lists + `run_onchange` scripts) + small bash scripts, driven by `doctl`** | **Recommended.** It builds on chezmoi, which already runs on all three machines, and adds no new state store. cloud-init runs as root, which avoids apollo's password-sudo problem at bootstrap time. The scripts can be tested with the repo's existing bashunit. |
| Ansible | A second config system beside chezmoi. Revisit only if the fleet grows past ~3 Linux hosts. |
| Terraform/OpenTofu | Needs a state file to guard; too much for 1–3 hand-named droplets. |
| Golden snapshot | Rollback archive only (§5). |
| Nix / home-manager | The most reproducible option, but a large migration. Not proportionate. |

### 6.2 Layout And Layers (All In The chezmoi Repo)

Provisioning files live **outside `home/`**. Since `.chezmoiroot = home`, chezmoi never
applies them to `$HOME`. Package lists live in `.chezmoidata`, so cloud-init and the
`run_onchange` scripts render from one source of truth. This is chezmoi's documented
"install packages declaratively" pattern.

```text
dotfiles repo
├── home/
│   ├── .chezmoidata/
│   │   ├── packages.yaml   # apt, cargo(-binstall), uv tools, npm globals, go tools, curl installers (agy/grok/muse)
│   │   └── machines.yaml   # hostname → role (dev_cloud | home_server | laptop), tailnet alias, services wanted
│   └── .chezmoiscripts/
│       ├── run_onchange_before_10_apt_packages.sh.tmpl   # no-op when all present
│       ├── run_once_before_20_toolchains.sh.tmpl         # uv, rustup, nvm+node, oh-my-zsh
│       ├── run_onchange_after_30_cargo_tools.sh.tmpl     # hash of the list → cargo binstall
│       ├── run_onchange_after_31_uv_tools.sh.tmpl
│       ├── run_onchange_after_32_npm_globals.sh.tmpl     # claude-code, codex, … under nvm
│       └── run_onchange_after_40_user_units.sh.tmpl      # enable bob-vault-sync etc. by role
└── machines/               # NOT applied to $HOME
    ├── cloud-init.yaml.tmpl
    ├── provision           # Layer 0: doctl wrapper, run from athena
    ├── push-secrets        # Layer 3: allow-listed copy, athena → new host
    ├── sase-host-setup     # Layer 4: runs on the new host
    └── doctor              # Layer 5: verifies every layer, exits nonzero on gaps
```

**Layer 0: `machines/provision <name> [size] [region]`, run from athena.**

- Renders the cloud-init with `chezmoi execute-template` to a `umask 077` temp file,
  then runs `doctl compute droplet create --image ubuntu-24-04-x64 --user-data-file …
  --enable-monitoring --tag-names sase-dev --wait`.
- Waits until the node shows up in `tailscale status`, then runs
  `ssh <host> cloud-init status --wait` and prints the manual steps.
- Pulls a **one-off, pre-approved, short-expiry** Tailscale auth key from `pass`,
  because user-data can be read from the metadata endpoint. Tailscale OAuth clients can
  only mint *tagged* keys, and tagged nodes lose user ownership, so generating the key
  by hand in the admin console (about 30 s) is the better trade.
- **Never commit a rendered file:** the dotfiles repo is public.
- One-time setup: install `doctl` on athena (it isn't installed today), keep its token
  in `pass`, and ask DO to raise the account's vCPU limit if 24–32 vCPU sizes need it.

**Layer 1: `cloud-init.yaml.tmpl` (root, first boot).**

```yaml
#cloud-config
hostname: {{ .hostname }}            # OS hostname drives chezmoi's .chezmoi.hostname guards
users:
  - name: bryan
    shell: /usr/bin/zsh
    groups: [sudo]
    lock_passwd: true
    ssh_import_id: [gh:bbugyi200]    # authorized keys from GitHub; nothing hard-coded
write_files:
  - path: /etc/sudoers.d/90-bootstrap  # removed by the manual "set sudo password" step
    permissions: "0440"
    content: "bryan ALL=(ALL) NOPASSWD:ALL\n"
package_update: true
packages: {{ .packages.apt | toJson }}
runcmd:
  - [sh, -c, 'fallocate -l 16G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo "/swapfile none swap sw 0 0" >> /etc/fstab']
  - [sh, -c, 'curl -fsSL https://tailscale.com/install.sh | sh']
  - [tailscale, up, '--auth-key={{ .ts_authkey }}', '--hostname={{ .ts_hostname }}']
  - [loginctl, enable-linger, bryan]
  - [systemctl, enable, --now, sysstat]
  - [su, -, bryan, -c, 'sh -c "$(curl -fsLS get.chezmoi.io)" -- -b ~/bin init --apply bbugyi200']
```

- The dotfiles repo is public, so `chezmoi init --apply` needs no credentials. Switch
  the remote to SSH later if you want to push from that host.
- The temporary NOPASSWD drop-in lets the first chezmoi apply run unattended. The
  manual step `sudo passwd bryan && sudo rm /etc/sudoers.d/90-bootstrap` then restores
  apollo's password-sudo behavior. No password hash ever goes into user-data.

**Layer 2: the chezmoi user layer.**

- Move every hand-made install into `packages.yaml` plus the `run_onchange` scripts.
- Use `cargo binstall` (prebuilt binaries) for the ~25 cargo tools. Compiling them is
  the slowest part of a fresh build.
- Replace the hostname literals with loops over `machines.yaml`. This covers
  `.chezmoiignore`, `private_tailnet.conf` and the tailnet-include script, so a new
  machine becomes a single YAML entry. `sase init` still writes the per-machine
  `sase_<machine>.yml` overlay and its guard.
- Bring `github-bob` under chezmoi, and repoint `~/org` at the tailnet `athena` alias
  instead of the LAN IP.

**Layer 3: `machines/push-secrets <host>` plus logins.** Keep this small and manual on
purpose.

- Copy an explicit allow-list: the GPG secret key
  (`gpg --export-secret-keys … | ssh host gpg --import`) and `id_bob_vault`. Then clone
  `~/.password-store`, `~/bob` and `~/org`.
- Instead of copying `id_rsa`, give each host a **new** SSH key registered with
  `gh ssh-key add`.
- Log in interactively on each host: `gh auth login`, `claude`, `codex login`, and
  `agy`/`grok`/`muse` where they're used. Don't copy their credential files: rotating
  refresh tokens invalidate each other across machines. This takes about 10 minutes.
- Generate `~/.sase/service/env`; don't copy it.

**Layer 4: `machines/sase-host-setup`, on the new host.**

1. Clone the five public `sase-org` repos into `~/projects/github/sase-org/` if they're
   missing. Put this in `install_sase_github` itself.
2. Run `install_sase_github -i`. It already installs `sase-xprompt-lsp` too.
3. Run `sase init`. It needs a TTY, and it creates or selects `sase_<machine>.yml`.
4. Run `sase service init`, then `sase service proc enable gateway`. Accept `--no-start`
   during a side-by-side rebuild. Then run `tailscale serve --bg --yes 7629`.
5. Run `umask 077; sase machine bootstrap --json > /tmp/bootstrap.json` and copy the file
   to athena. On athena, run `sase machine init -B …` for a new machine or
   `sase machine repair <alias> -B …` for a rebuilt one. Then run
   `sase machine status <alias>` and a `%dispatch:<alias>` smoke test, as described in
   `docs/remote_dispatch.md`.

**Layer 5: `machines/doctor`.** This checks every layer and lists the gaps:

- tools and versions on the login *and* non-login `PATH`
- `chezmoi verify`
- user units active
- Tailscale Serve answers `/api/v1/health`
- `gh auth status` and the provider logins
- `sase doctor`
- swap is on

Run it on athena and apollo today to turn "identical setup" into a checkable property
and to surface the existing drift.

---

## 7. Recommended Solution

### Phase 0: Upgrade apollo in place today (no re-create, reversible)

1. Let the running agents finish. Preview cleanup with `sase disk reap` and apply it
   only if it looks right. **Don't** `rm -rf` any workspaces.
2. Optionally take a snapshot. DO recommends one before any resize, and it's cheap:
   `apollo-pre-resize-20260923`, about $7/mo prorated. Delete it once the resize checks
   out.
3. Resize **CPU and RAM only** to `c-32`. In the panel: power off → Resize → "CPU and RAM
   only" → CPU-Optimized 32 vCPU / 64 GB. Or run
   `doctl compute droplet-action resize 568763576 --size c-32 --wait`;
   `--resize-disk` defaults to false. Power it back on if it doesn't come up by itself.
   Downtime is at worst ~1 minute per GB used, and usually much less.
4. Verify:
   - `nproc` shows 32, `free -g` shows about 62, and `df -h /` still shows ~193 G.
   - `systemctl --user status sase bob-vault-sync` and `tailscale serve status` are
     healthy.
   - From athena, `sase machine status apollo` succeeds.
5. Add a 16 GiB swapfile. It needs sudo, so go through the `/sase_sudo` gate or do it by
   hand.
6. Raise the agent limit from 5 to about 10, then watch `sar -u` / `sar -r` over a few
   busy days.

**Don't grow the disk, and don't move workspaces onto a volume.**

### Phase 1: Write the automation (one chezmoi change set; good agent work)

- Build `packages.yaml` from apollo's real state: `apt-mark showmanual`,
  `~/.cargo/bin`, uv tools, npm globals under nvm, and the provenance of `agy`, `grok`
  and `muse`. Drop the vestigial entries.
- Add the `run_onchange` scripts, the `machines.yaml` role templating and the
  `machines/` scripts.
- Add the clone-if-missing step to `install_sase_github`.
- Add shellcheck and bashunit tests, matching the repo's existing `test-bash`.
- Install and authenticate `doctl` on athena.

### Phase 2: Prove the automation and run the bake-off (~2 h, < $6)

1. `machines/provision` two throwaway droplets: `c-32` in nyc1, and
   `g5-24vcpu-64gb-300gb` in **ric1**, the closest v5 region to NYC (or atl1). Confirm
   the slugs with `doctl compute size list` first.
2. On each, run:
   - `just check` in sase
   - a clean `cargo build --release` of sase-core
   - `mypy` alone, for single-thread latency
   - three concurrent `just check` runs, for throughput

   Record wall time, `$/h`, and **the bootstrap's time-to-ready**. That last number is
   the honest answer to "how many minutes does a new machine take?"
3. Fix every automation failure you hit. Run each script a second time to confirm it's a
   no-op, then destroy both droplets.

### Phase 3: Decide

- **If g5 is materially faster per dollar** (for example, ≥25% lower `just check` wall
  time at similar cost), go to Phase 4.
- **If not**, keep the resized apollo. The automation is proven either way and ready for
  machine #3.

### Phase 4 (conditional): Rebuild apollo on v5, side by side

1. **Build the new host.** Run `machines/provision apollo <g5-size> ric1` with OS
   hostname `apollo` (so chezmoi applies apollo's overlay) and Tailscale hostname
   `apollo-next`. Then run `push-secrets`, do the logins and the sudo-password step, run
   `sase-host-setup --no-start`, and run `doctor` until it's clean. **Keep the new
   service stopped**, because both hosts share `sase_apollo.yml` and `machine_name`, and
   AXE routines must not run twice.
2. **Retire the old host.** Drain its agents and push their work. Run
   `systemctl --user stop sase bob-vault-sync` and take a snapshot, which is a ~$7/mo
   rollback archive and much cheaper than the Backups add-on.
3. **Swap identities.** Remove the old node from the tailnet. On the new host, run
   `sudo tailscale set --hostname=apollo`, then rerun `tailscale serve --bg --yes 7629`
   so the certificate matches `apollo.tail297af1.ts.net`.
4. **Start and re-enroll.**
   - Run `systemctl --user enable --now sase bob-vault-sync` and issue a bootstrap
     bundle.
   - On athena, run `sase machine repair apollo -B …`, then `sase machine status apollo`
     and a `%dispatch:apollo` smoke test.
   - To carry agent history over instead, rsync `~/.sase` (without `cache/`) while both
     services are stopped. That also carries the identity, so no repair is needed. Do
     this only because the old host is being destroyed, and never for a third machine.
5. **Update the IP.** Point `apollo-do` in `private_tailnet.conf` at the new IP and run
   `chezmoi update` on each machine. Reserved IPs can't leave their datacenter; if you
   want future rebuilds in the same region to keep their IP, add one in ric1.
6. **Decommission.** After about a week of clean running, **destroy** the old droplet;
   billing stops only then. Delete the snapshot after a month.

### Machine #3 afterwards (the end state)

1. Add an entry to `machines.yaml` and put a one-off Tailscale key in `pass`.
2. Run `machines/provision <name> <size> <region>` and wait. It runs unattended; Phase 2
   measures how long.
3. Run `machines/push-secrets <name>`, then do the interactive logins and set the sudo
   password (~10 min).
4. Run `machines/sase-host-setup`, which runs `sase init`. Then on athena run
   `sase machine init -B …`.
5. Run `machines/doctor <name>`.

---

## 8. Risks And Open Questions

- **v5 availability.** The specific `g5-…` shape, the region's capacity and the
  account's vCPU limit are all unconfirmed. Check with `doctl compute size list` and the
  create dialog. Starting a v5 droplet from a bundled-plan snapshot isn't documented,
  and it isn't the recommended path anyway.
- **The per-core gain is an estimate.** Phase 2 measures it. v5 also costs about 8.6%
  more per month at the same hourly rate because it has no 672 h cap, and the docs
  don't say whether a powered-off v5 droplet still bills.
- **Two `apollo`s during the overlap.** Keep the new host's service stopped until
  cutover.
- **Steps that need a TTY** (`sase init`, the OAuth logins, the sudo password) stay
  manual. `doctor` makes a missed step obvious.
- **Public dotfiles repo.** Rendered cloud-init contains the Tailscale key, so render it
  to a temp file, never commit it, and delete it afterwards.
- **Unknown installers.** Where `agy`, `grok` and `muse` came from hasn't been traced
  yet. Capture it in `packages.yaml` during Phase 1.
- **Leaving DO later.** Only Layer 0 (`doctl`) is DO-specific. Hetzner Cloud CCX in
  Ashburn would need only a different `provision` script.

## Sources

- **Constituent reports:** `apollo_upgrade_and_machine_bootstrap__cld.md`, `__mus.md`
  and `__gem.md` in this directory.
- **Prior research:** `research:202609/temporary_high_capacity_test_machine.md`.
- **Lead probes, 2026-09-23:**
  - `ssh apollo`: `nproc`, `free`, `df`, `lscpu`, `swapon`, `sudo -n`, the uv tool
    receipt, the chezmoi source and remote, `du` of the caches and workspaces,
    `sase disk list`, `sar -u/-q` for 09-18/21/22, `systemctl --user`, the identity
    files under `~/.sase`, the CLI install paths and versions, and the variable names
    in `~/.sase/service/env`
  - athena: `command -v doctl`
- **Repos:**
  - chezmoi `home/.chezmoiignore`, `home/.chezmoiscripts/*`,
    `home/bin/executable_install_sase_github`, `home/dot_config/sase/sase_apollo.yml`
  - sase `docs/remote_dispatch.md`, `tests/_suite_gate_budget.py`, and the
    `sase disk|workspace|service|machine` CLI help
- **Docs:**
  - DigitalOcean:
    - [Resize](https://docs.digitalocean.com/products/droplets/how-to/resize/)
    - [Droplet pricing](https://www.digitalocean.com/pricing/droplets)
    - [Pricing details (v5 rates, no cap)](https://docs.digitalocean.com/products/droplets/details/pricing/)
    - [Choosing a plan](https://docs.digitalocean.com/products/droplets/concepts/choosing-a-plan/)
    - [v5 GA changelog](https://ideas.digitalocean.com/changelog/now-generally-available-v5-droplets)
    - [Introducing v5 Droplets](https://www.digitalocean.com/blog/introducing-v5-droplets)
    - [Snapshots → Droplets](https://docs.digitalocean.com/products/snapshots/how-to/create-and-restore-droplets/)
    - [Reserved IPs](https://docs.digitalocean.com/products/networking/reserved-ips/)
    - [doctl droplet-action resize](https://docs.digitalocean.com/reference/doctl/reference/compute/droplet-action/resize/)
  - Tailscale:
    - [cloud-init](https://tailscale.com/kb/1293/cloud-init)
    - [auth keys](https://tailscale.com/kb/1085/auth-keys)
    - [OAuth clients](https://tailscale.com/kb/1215/oauth-clients)
  - [chezmoi: install packages declaratively](https://www.chezmoi.io/user-guide/advanced/install-packages-declaratively/)
  - Hetzner:
    - [2026-06-15 price adjustment](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)
    - [Locations (no US dedicated servers)](https://docs.hetzner.com/cloud/general/locations/)
