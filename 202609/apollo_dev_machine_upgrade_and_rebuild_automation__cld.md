# Upgrading Apollo Into A Long-Term Second Dev Machine, And Scripting Its Rebuild

**Research question:** Bryan wants apollo, his DigitalOcean droplet, to become a
permanent, more powerful second development machine where SASE agents run faster. He
thinks growing the disk means re-creating the droplet. He also wants the setup scripted
so that a third, identical machine takes as few steps as possible. What is the best
upgrade path, and how should the machine's setup be automated?

**Date / scope:** 2026-09-23. Live read-only probes of apollo (`ssh apollo`: hardware,
DO metadata, sysstat history, services, installed tooling, `~/.sase` layout) and athena.
Also read: the linked chezmoi repo (`bbugyi200/dotfiles` at `d02225f4`), sase
`docs/remote_dispatch.md` and `docs/configuration.md`, and the prior research
`research:202609/temporary_high_capacity_test_machine.md` and
`research:202609/tailnet_dispatch_setup/tailnet_dispatch_setup.md`. Pricing and platform
rules come from DigitalOcean, Hetzner, OVHcloud and Tailscale pages fetched today;
re-confirm them in the create dialog before you buy.

---

## Executive Summary

1. **Short answer to "I need to re-create it, right?": not for the disk.**
   DigitalOcean resizes a droplet's disk in place with the "Disk, CPU and RAM" option.
   The only catch is that a disk increase is permanent. A "CPU and RAM only" resize is
   also in place and reversible. Two things force a new droplet:
   - **moving to DO's new v5 droplets (5th-gen AMD EPYC).** Bundled plans can only
     resize to other bundled plans, and v5 plans only to other v5 plans.
   - **changing region**, which v5 currently needs anyway: it is available in ATL1,
     RIC1, MEM1 and MKC1, not NYC1.
2. **Apollo's upgrade is already permanent.** It is no longer the 4-vCPU Basic droplet
   from the September research. It now runs as **CPU-Optimized `c-16`**: 16 dedicated
   vCPUs on a 2017-era Intel Xeon Platinum 8168 (Skylake), 32 GiB RAM, and a 200 GB
   disk (up from 160 GB). It costs **$336/month**. Because the disk grew, the droplet
   can never shrink back to its old plan. The "temporary" upgrade is effectively
   permanent already.
3. **Apollo is CPU-bound at peak, even with only 5 agents allowed.**
   - sysstat shows load averages of 25–57 on 16 vCPUs on busy days.
   - On 2026-09-21, the CPU was saturated (<10% idle) for about 10 of 24 hours.
   - Free memory dropped to 3.8 GiB, and there is no swap.
   - Doubling the cores or getting much faster cores would both help. Faster cores also
     cut the wall time of each agent's `just check`, `mypy` and cargo builds.
4. **Most of the setup is not scripted today.** Chezmoi covers dotfiles and a handful
   of user-level installers (nvim, luarocks, lazygit, tpm, basher, bashunit). Nothing
   installs the system packages, zsh, Tailscale, uv, rustup and its ~25 cargo tools,
   nvm/node and the agent CLIs, the SASE repos and install, the SASE service host and
   gateway, Tailscale Serve, the Bob vault sync unit, or the secrets. Apollo was built by
   hand, and its drift shows (texlive, kitty, wkhtmltopdf, host blocks in `~/.ssh/config`
   that chezmoi doesn't manage, an org remote on a LAN IP).

**Recommendation: rebuild, don't resize, and make the rebuild the test of the
automation.**

- Write a layered bootstrap:
  - a `doctl` provisioning script
  - a cloud-init template for the root/system layer
  - declarative package lists plus `run_onchange` scripts in chezmoi for the user layer
  - a secrets hand-off plus a short checklist of interactive logins
  - a SASE host-setup script
  - a `doctor` check
- Use it to create throwaway candidate droplets for an hour-long benchmark (a few
  dollars with per-second billing).
- Then build the new apollo next to the old one, cut over, and destroy the old one.

A new v5 `g5` droplet with ~24–32 dedicated EPYC vCPUs and 64 GiB is the likely winner,
at about $710–$875/month. The in-place alternative, `c-32`, costs $672/month and doubles
the old Skylake cores. The benchmark decides between them.

**Stopgap:** if you need speed this week, do a reversible CPU-and-RAM-only resize of
apollo to `c-32` now. It doesn't block the rebuild.

The end state for a third machine is: run one provisioning command, wait about 30–45
unattended minutes, push secrets, spend about 10 minutes on interactive logins, run
`sase init` plus the host-setup script, and enroll from athena.

---

## 1. What Apollo Is Today (Measured 2026-09-23)

| Property | Value | Evidence |
| --- | --- | --- |
| Plan | CPU-Optimized, regular Intel: 16 vCPU / 32 GiB / 200 GB SSD → **`c-16`, $0.50/h, $336/mo** | `nproc`, `free`, `lsblk`; matches DO's c-16 row exactly |
| CPU | Intel Xeon Platinum 8168 @ 2.70 GHz (Skylake-SP, 2017) | `lscpu` |
| Disk | 200 GB, 120 GB used (63%) | `df`; it was 160 GB on 2026-09-03, so a **disk-including (permanent) resize** already happened |
| Region / ID | `nyc1` / droplet 568763576 | DO metadata endpoint |
| OS | Ubuntu 24.04.3 LTS, kernel 6.8 | `lsb_release` |
| Public IP | 159.223.165.54 (the `apollo-do` SSH alias) | chezmoi `private_tailnet.conf` |
| Swap | **none** | `free` |
| sudo | password required (fits the `/sase_sudo` gate model) | `sudo -n true` fails |

**Roles apollo plays**, which a replacement must reproduce:

- `sase.service`: a systemd **user** unit with linger enabled, running `sase service run`.
  Its `gateway` proc listens on `127.0.0.1:7629`. The overlay `sase_apollo.yml` enables
  it.
- **Tailscale Serve**: `https://apollo.tail297af1.ts.net` (tailnet only) proxies to
  `127.0.0.1:7629`. Athena has enrolled apollo at that endpoint with installation pin
  `sase_inst_v1_8d5f…`.
- `bob-vault-sync.service`, a user unit. The unit file comes from chezmoi; enabling it
  and cloning the vault were manual. It uses the `github-bob` SSH alias with the
  `id_bob_vault` key.
- A regular dev box: `~/org` (git), `~/.password-store` (git + GPG), `~/projects`
  (10 GB), and SASE workspaces (43 GB, regenerable).

**Utilization (sysstat, 10-minute samples, last 9 days):**

| Day | Mean CPU busy | Saturated samples (<10% idle) | Max 1-min load (16 vCPU) | Min available RAM |
| --- | --- | --- | --- | --- |
| 09-15 | 31% | 4 / 144 | 28.0 | 11.3 GiB |
| 09-17 | 26% | 2 / 144 | 21.2 | **3.8 GiB** |
| 09-18 | 55% | **30 / 144** | 35.4 | 7.0 GiB |
| 09-20 | 40% | 11 / 144 | 30.7 | 10.2 GiB |
| 09-21 | 81% | **61 / 144** | **57.0** | 5.0 GiB |
| 09-22 | 22% | 3 / 144 | 24.8 | 12.7 GiB |

Takeaways:

- Busy days are CPU-bound. On 09-21, 41% of CPU time was `nice`, which is consistent
  with niced test workers.
- `max_running_agents_override.json` is `limit: 5`, so five agents alone saturate the
  box.
- Memory is the second constraint: dips below 5 GiB with no swap is an OOM risk as
  concurrency rises.
- I/O wait never exceeded ~6%, so disk speed isn't the bottleneck.

---

## 2. Does Upgrading The Disk Force A Re-Create? (DigitalOcean Rules)

| Change | In place? | Reversible? | Notes |
| --- | --- | --- | --- |
| CPU/RAM-only resize to a bigger bundled plan (e.g. c-16 → c-32) | **Yes** | **Yes** | The disk stays at 200 GB. The target plan's disk must be ≥ the current disk. |
| Disk + CPU + RAM resize (e.g. c-16 → c-32 with 400 GB) | **Yes** | No: "You cannot decrease the size of a Droplet's disk." | No re-create needed. Take a snapshot first. |
| Bundled plan → v5 (`g5-*`/`s5-*`) | **No** | n/a | "Droplets created with a v5 configuration resize only to other v5 configurations, and Droplets created with a bundled plan resize only to other bundled plans." |
| Change region (nyc1 → atl1/ric1 for v5) | **No** | n/a | Snapshots can be transferred between regions and used to create droplets there. |
| Shrink the disk | **No** | n/a | Needs a new, smaller droplet plus a data migration. |

- **Downtime** for any resize: power off, then "about one minute … per GB of used disk"
  in the worst case, because the droplet may move to a new hypervisor. Apollo has
  120 GB used, so allow up to ~2 hours, though it is usually much shorter.
- A **re-create** can overlap with the old machine, so downtime is only the cutover.

So the premise is half right. You don't need to re-create apollo to get more disk or more
of the same cores. You do need to re-create it to get the new CPU generation. Re-creating
is also the only way to prove your automation works.

---

## 3. Upgrade Options Compared

Prices are from DO pricing pages fetched 2026-09-23.

- **Bundled plans** bill per second, capped at 672 hours (28 days) a month, and still
  bill while powered off.
- **v5 plans** bill per second for the sum of their parts:
  - g5 dedicated vCPU: $0.028/h
  - memory: $0.0040411/GiB-h
  - NVMe boot disk: $0.000137/GiB-h
  - **v5 has no monthly cap**, so the table uses ~730 h/month.

| Option | Shape | $/h | ≈ $/mo | Per-core speed vs today | Re-create? | Automation value |
| --- | --- | --- | --- | --- | --- | --- |
| Today: `c-16` | 16 vCPU Skylake / 32 GiB / 200 GB | 0.50 | 336 | 1× | — | — |
| A. Resize → `c-32` (CPU/RAM only) | 32 vCPU Skylake-class / 64 GiB / *200 GB kept* | 1.00 | 672 | ~1× (same generation) | No | None |
| A′. Resize → `c-32` with disk | … / 400 GB SSD | 1.00 | 672 | ~1× | No | None |
| B. Resize → `c2-32` (Premium Intel) | 32 vCPU newer Intel ("latest two generations") / 64 GiB / 800 GB NVMe | 1.119 | 752 | better (Ice Lake or newer) | No | None |
| **C. New v5 `g5-24vcpu-64gb-300gb`** | 24 dedicated EPYC Gen 5 / 64 GiB / 300 GB NVMe | 0.972 | **~709** | substantially faster (2017 Skylake → 2024 Zen 5); DO claims "up to 30%" over its *previous* generation, so the gap to Skylake is larger | **Yes** | **Full** |
| **C′. New v5 `g5-32vcpu-64gb-300gb`** | 32 dedicated EPYC Gen 5 / 64 GiB / 300 GB | 1.196 | **~873** | same | Yes | Full |
| C″. `g5-16vcpu-64gb-300gb` | 16 dedicated EPYC Gen 5 / 64 GiB | 0.748 | ~546 | same | Yes | Full |
| D. Hetzner AX102-1 (bare metal, Falkenstein/Helsinki) | Ryzen 9 7950X3D 16C/32T / 128 GB DDR5 / 2×1.92 TB NVMe | monthly | **$302** + $149 setup | very fast (desktop Zen 4, 5 GHz) | new provider | Full |
| E. OVH Advance (US, Vint Hill) | EPYC 4004/4005 6–16 cores | monthly | $147–$255+, rising | fast | new provider | Full |

Notes on the table:

- **Valid g5 shapes:** DO documents ratios of 2×–8× memory per vCPU and 2–64 vCPUs.
  Confirm that a given shape (e.g. 24 vCPU with 64 GiB) is offered in the configurator.
  Otherwise use 24/48 (~$662/mo) or 24/96 (~$804/mo).
- **Snapshot route:** a snapshot of a bundled droplet can seed a new droplet in a v5
  region, where you "can choose a Shared or General Purpose configuration". This makes a
  lift-and-shift of apollo's disk onto `g5` possible. It is not recommended; see §5.
- **Hetzner** re-priced dedicated servers on 2026-06-15. The AX102 went from roughly
  €104–122 to €257.30 (ex. VAT) as DDR5 costs rose about 6× in a year.
  - It is still the best price/performance for a long-lived box, at roughly 2–3× apollo's
    throughput for less than a `c-32`.
  - But it is EU-only for dedicated servers (~90–100 ms from the US East Coast), billed
    monthly with a setup fee, and a new vendor. That defeats the "spin up a third
    machine for a weekend" use case.
- **OVH** is raising dedicated-server prices from Aug–Oct 2026, and US Advance stock
  showed as "Coming Soon".
- **A home box** is the cheapest per unit of compute. A Ryzen 9950X-class machine pays
  for itself against a $700/mo droplet in months. But it duplicates athena's single
  points of failure (home power and network) and isn't "spin up in one command". Treat
  it as a separate decision.

**Why stay on DigitalOcean:**

- The account, SSH keys and billing already exist.
- Per-second billing makes throwaway benchmark and third-machine droplets cheap.
- It is scriptable with `doctl`.
- It is US-East adjacent.
- v5 fixes DO's main weakness, old CPUs.

**Sizing:** target about double today's effective compute and memory, i.e. 24–32 modern
dedicated vCPUs and 64 GiB. Then raise apollo's `max_running_agents` override from 5.

- The suite gate's default 32-token cap only matters above ~36 vCPUs (the 2026-09-03
  research: set `SASE_TEST_GATE_SLOTS` there).
- Add a 16 GiB swapfile either way.
- About 300 GB of disk is enough: 120 GB is used today, and 63 GB of that is regenerable
  workspaces and caches.

---

## 4. What A Rebuild Must Reproduce (Inventory)

| Layer | What apollo has | Automated today? |
| --- | --- | --- |
| **Cloud resource** | droplet, region, size, DO SSH keys, public IP (hard-coded in `tailnet.conf` as `apollo-do`) | No (control panel) |
| **System (root)** | user `bryan` with zsh and the sudo group; apt: `zsh gh golang cmake make pkg-config pass pipx pandoc tmuxinator trash-cli inotify-tools lua5.1 liblua5.1-0-dev kitty xclip wkhtmltopdf texlive-latex-recommended sd duf dict aspell sysstat …`; Tailscale; linger for bryan; unattended upgrades | **No** |
| **User toolchains** | uv; rustup/cargo plus ~25 cargo tools (`just atuin bat delta fd rg starship zoxide procs btm tokei stylua ruff eva exa mcfly cargo-update bob bob_notify bob_pomodoro zorg zorg-ls …`); nvm → node 24 → `claude`, `codex`; `agy`, `grok`, `muse` in `~/.local/bin`; oh-my-zsh plus custom plugins; go | Partly: chezmoi installs nvim (source build), luarocks and rocks, lazygit, tpm, basher, bashunit |
| **Dotfiles** | chezmoi (`bbugyi200/dotfiles`, **public**; `.chezmoiroot = home`) | **Yes** |
| **Host-specific config** | `sase_apollo.yml` (machine name, H1, gateway proc), `.chezmoiignore` hostname guards, `tailnet.conf`, the tailnet-include `run_onchange` script (hard-coded host list) | Yes, but keyed to literal hostnames |
| **SASE** | repos cloned to `~/projects/github/sase-org/{sase,sase-core,sase-github,sase-telegram,sase-research-artifacts}` (all **public**); `install_sase_github -i` (editable `uv tool install` with `sase-core-rs` built from source); `sase service init`; gateway proc; `tailscale serve --bg 7629`; bootstrap plus enrollment from athena | Partly: `install_sase_github` exists but assumes the repos are already cloned |
| **Secrets / logins** | `~/.ssh/id_rsa`, `id_bob_vault`; GPG secret key (for `pass`); `gh` auth; `~/.claude/.credentials.json`; `~/.codex/auth.json`; other agent CLIs; `~/.sase/service/env`; Tailscale node key | **No** |
| **Data** | `~/bob` (private GitHub, deploy key), `~/org` (remote `ssh://bryan@192.168.1.156:34857/…`, **a LAN IP**), `~/.password-store` (private GitHub), `~/.sase` (11 GB: identity, fleet gateway credentials, agent history; 3.2 GB of it is cache) | No |
| **Drift to fix while you're here** | `~/.ssh/config` holds `github-bob` and a stale `mac` block with a hard-coded IP, outside chezmoi; the zsh startup error `_maybe_source_locals: command not found`; packages that may be vestigial (`kitty`, `wkhtmltopdf`, texlive, `x11-apps`) | — |

The automation effectively has to turn this table into code, with one exception. The
secrets row stays a deliberate, short, manual hand-off (see §6.4).

---

## 5. Automation Approaches Considered

| Approach | Fit for 2–3 personal machines | Verdict |
| --- | --- | --- |
| **cloud-init + chezmoi (declarative package lists + `run_onchange` scripts) + small bash scripts, driven by `doctl`** | Builds on what already works everywhere (chezmoi on athena, apollo and the Mac); no new state store; cloud-init runs as root on first boot, which avoids apollo's password-sudo problem; scripts are testable with the repo's existing bashunit | **Recommended** |
| Ansible (Bryan's old `~/projects/ansible_config`, last touched 2023, still installed via pipx) | Good for converging system state across many hosts, but it would be a second config system beside chezmoi, and the old roles are stale | Revisit if the fleet grows past ~3 Linux hosts or system-level drift keeps recurring |
| Terraform/OpenTofu + DO provider | Declarative infrastructure, but needs a state file to guard; overkill for 1–3 hand-named droplets | Not now |
| Golden snapshot ("clone apollo") | Fastest to boot, but it carries all the drift, the **Tailscale node identity** (`/var/lib/tailscale`), the **SASE installation identity** (`~/.sase/installation_identity.json` + `fleet_gateway/credentials.json`), and OAuth refresh tokens shared across machines. Each clone needs a fragile scrub, and a 120 GB image is slow to create. | Use snapshots **only** as a rollback archive of the old apollo |
| Nix / home-manager | Most reproducible, but a large migration of an existing zsh/chezmoi setup | Not proportionate |

---

## 6. Recommended Automation Architecture

Put everything in the chezmoi repo.

- **Machine-provisioning files live outside `home/`**, e.g. a top-level `machines/`
  directory. `.chezmoiroot` is `home`, so chezmoi never applies them to `$HOME`.
- **Package lists live in chezmoi data**, so each list has one source of truth that both
  cloud-init and the `run_onchange` scripts render.

```
dotfiles repo
├── home/
│   ├── .chezmoidata/
│   │   ├── packages.yaml     # apt, cargo(-binstall), uv tools, npm globals, go tools
│   │   └── machines.yaml     # hostname → role (dev_cloud, home_server, laptop), ssh port, etc.
│   └── .chezmoiscripts/
│       ├── run_onchange_before_10_apt_packages.sh.tmpl      # linux; no-op if all present; uses chez::can_sudo
│       ├── run_once_before_20_toolchains.sh.tmpl            # uv, rustup, nvm+node, oh-my-zsh+plugins
│       ├── run_onchange_after_30_cargo_tools.sh.tmpl        # hash of packages.cargo → cargo binstall/install
│       ├── run_onchange_after_31_uv_tools.sh.tmpl
│       ├── run_onchange_after_32_npm_globals.sh.tmpl        # claude-code, codex, …
│       └── run_onchange_after_40_user_units.sh.tmpl         # daemon-reload; enable bob-vault-sync on roles that want it
└── machines/                  # NOT applied to $HOME
    ├── cloud-init.yaml.tmpl
    ├── provision              # doctl wrapper (runs on athena)
    ├── push-secrets           # athena → new host, allow-listed
    ├── sase-host-setup        # runs on the new host
    └── doctor                 # verifies every layer; lists gaps; nonzero exit on gaps
```

### 6.1 Layer 0: `machines/provision <name> [size] [region]` (on athena)

This is the pattern the September research already used, turned into a script:

```bash
doctl compute droplet create "$name" \
  --image ubuntu-24-04-x64 --region "${region:-atl1}" --size "${size:-g5-24vcpu-64gb-300gb}" \
  --ssh-keys "$(doctl compute ssh-key list --format ID --no-header | paste -sd,)" \
  --user-data-file "$rendered_cloud_init" --enable-monitoring --tag-names sase-dev --wait
# then: poll `tailscale status --json` until "$ts_hostname" is Online,
#       `ssh "$ts_hostname" cloud-init status --wait`, and print the next manual steps.
```

- Render the cloud-init with `chezmoi execute-template` so it reuses `packages.yaml`.
- Inject a **one-off, pre-approved Tailscale auth key** from `pass` (e.g.
  `pass tailscale/authkey`). Anything on the droplet can read user-data through the
  metadata endpoint, so a single-use key is the safe choice.
- Tailscale OAuth clients can mint keys automatically, but only *tagged* ones, and tagged
  nodes lose user ownership. Generating a one-off key in the admin console is a
  30-second manual step, and it's the better trade here.
- Account limits may need a vCPU/droplet-limit bump for 24–32 vCPU sizes. That's a
  one-time manual request.

### 6.2 Layer 1: `cloud-init.yaml.tmpl` (root, first boot)

```yaml
#cloud-config
hostname: {{ .hostname }}              # OS hostname drives chezmoi's .chezmoi.hostname guards
users:
  - name: bryan
    shell: /usr/bin/zsh
    groups: [sudo]
    lock_passwd: false
    hashed_passwd: {{ .sudo_hash }}    # from pass; keeps password-sudo parity with apollo
    ssh_import_id: [gh:bbugyi200]      # pull authorized keys from GitHub
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

- The dotfiles repo is public, so `chezmoi init --apply bbugyi200` needs no credentials.
  Switch the source remote to SSH later if you want to push from that host.
- Installing all apt packages here, as root, means the chezmoi apt script finds nothing
  to do on first run. That sidesteps the sudo password.

### 6.3 Layer 2: chezmoi user layer

- Move every ad-hoc install into `packages.yaml` plus the `run_onchange` scripts above.
  This follows chezmoi's documented "install packages declaratively" pattern: the script
  template embeds a hash of the list, so editing the list reruns it on every machine.
  Existing scripts in the repo already use the same idiom with
  `{{ include … | sha256sum }}` and date stamps.
- Use **`cargo binstall`** (prebuilt binaries) for the ~25 cargo tools. Compiling them
  from source is the slowest part of a fresh build.
- Make role-driven what is hostname-driven today. Today, adding a third machine means
  editing `.chezmoiignore`, `private_tailnet.conf` and
  `run_onchange_after_ensure_ssh_tailnet_include.tmpl`, which hard-codes
  `athena`/`apollo`/`Kellys-MacBook-Pro`. With `.chezmoidata/machines.yaml` and
  templates that loop over it, a new machine becomes one YAML entry. SASE's own
  `sase config init` still writes `sase_<machine>.yml` and its guard (see §6.5).
- Bring `github-bob` and any other `~/.ssh/config` host blocks under chezmoi. Point
  `~/org`'s remote at the tailnet `athena` alias instead of `192.168.1.156`.

### 6.4 Layer 3: secrets and logins (deliberately small and manual)

- `machines/push-secrets <host>`, run from athena, copies an **explicit allow-list**:
  - the GPG secret key (`gpg --export-secret-keys … | ssh host gpg --import`)
  - `id_bob_vault`
  - `~/.sase/service/env`

  Then it clones `~/.password-store`, `~/bob` and `~/org`.
- Prefer a **new** per-host SSH key registered with `gh ssh-key add` over copying
  `id_rsa`.
- **Log in interactively on each machine** to OAuth CLIs (`gh auth login`, `claude`,
  `codex login`, and `agy`/`grok`/`muse` if used there). Don't copy their credential
  files. Refresh tokens that rotate can invalidate each other when two machines share
  them. This takes about 10 minutes per machine and is the part that shouldn't be
  scripted.

### 6.5 Layer 4: `machines/sase-host-setup` (on the new host)

1. Clone the five public `sase-org` repos into `~/projects/github/sase-org/` if they're
   missing. Add this "clone if missing" step to `install_sase_github`.
2. `install_sase_github -i`. Also install `sase-xprompt-lsp`, which the script already
   handles.
3. `sase init`. It needs a TTY. It creates or selects `sase_<machine>.yml` and the
   `.chezmoiignore` guard in the chezmoi source. For a rebuilt apollo, the existing
   overlay is reused.
4. `sase service init --yes && sase service proc enable gateway`. Keep the service
   **stopped** when you pass `--no-start` during a side-by-side rebuild, so the new host
   doesn't run a second copy of AXE routines. Then `tailscale serve --bg --yes 7629`.
5. `umask 077; sase machine bootstrap --json > /tmp/bootstrap.json`, then copy it to
   athena. On athena, run `sase machine init -B …` for a new machine or
   `sase machine repair apollo -B …` for a rebuilt one. Then run
   `sase machine status <alias>` and a `%dispatch:<alias>` smoke launch. This follows
   `docs/remote_dispatch.md`.

### 6.6 Layer 5: `machines/doctor`

This is one script that checks each layer and prints the gaps:

- tools on `PATH` and their versions
- `chezmoi verify`
- the user units are active
- Tailscale Serve answers `/api/v1/health`
- `gh auth status`, and the Claude/Codex logins are present
- `sase doctor`
- the swap is on

It turns "identical setup" into something you can check. Run it on athena and apollo
today to find the drift.

---

## 7. Recommended Solution (Step By Step)

**Phase 0: optional stopgap (today, ~30–60 min downtime).** If apollo's speed hurts now:
power it off, then do a **CPU-and-RAM-only resize to `c-32`**. This doubles the cores and
RAM, keeps the 200 GB disk, and is reversible. Everything below still applies.

**Phase 1: write the automation (one agent-sized chezmoi change set).** Add §6 to the
dotfiles repo:

- `packages.yaml`, generated from `apt-mark showmanual`, `~/.cargo/bin`, the uv tools and
  the npm globals on apollo, pruning vestigial entries
- the new `run_onchange` scripts
- `machines.yaml` role templating
- the `machines/` scripts
- tests (shellcheck plus bashunit, matching the repo's existing `test-bash`)

Also install `doctl` on athena and authenticate it with a token kept in `pass`.

**Phase 2: bake-off, which also proves the automation (~2 h, under ~$6).** Use
`machines/provision` to create two throwaway droplets: `c-32` in nyc1 and
`g5-24vcpu-64gb-300gb` in atl1 (or ric1). On each, run:

- `just check` in sase
- a clean `cargo build --release` of sase-core
- `mypy` alone, for single-thread latency

Record wall time and `$/h`. Fix every automation failure you hit, then destroy both.
Choose the shape with the best wall time per dollar. Expect g5 to win on per-agent
latency, and pick 24 vs 32 vCPUs from the numbers.

**Phase 3: build the new apollo side by side (~1 h unattended).**
`machines/provision apollo <chosen-size> atl1` with Tailscale hostname `apollo-next` and
OS hostname `apollo`, so chezmoi applies apollo's overlay. Then:

- `push-secrets`
- the interactive logins
- `sase-host-setup --no-start`
- `doctor` until it's clean

Per-second billing makes a day of overlap cost about $20–30.

**Phase 4: cutover (~30 min).**

1. On old apollo, let the agents finish and push any work. Then
   `systemctl --user stop sase bob-vault-sync` and take a **DO snapshot**. At ~120 GB ×
   $0.06/GiB-mo, that's about $7/month, a cheap rollback archive instead of the Backups
   add-on (20–30% of the droplet price per month).
2. Remove the old `apollo` node from the tailnet (admin console, or `tailscale logout`
   on it). On the new host, run `sudo tailscale set --hostname=apollo`, then rerun
   `tailscale serve --bg --yes 7629` so the certificate matches
   `apollo.tail297af1.ts.net`.
3. Start the service on the new host with `systemctl --user enable --now sase
   bob-vault-sync`. Issue a bootstrap there. From athena, run
   `sase machine repair apollo -B …`, then `sase machine status apollo` and
   `%dispatch:apollo` for a smoke test.
   - This uses a fresh `~/.sase` on purpose: it exercises the third-machine path. If you
     want apollo's agent history carried over, `rsync ~/.sase` (excluding `cache/`)
     while both services are stopped. That also carries the installation identity, so
     no repair is needed. Only do this because the old host is about to be destroyed.
     Never do it for a *third* machine.
4. Update `apollo-do` in `private_tailnet.conf` to the new public IP and run
   `chezmoi update` on each machine. A Reserved IP makes future same-region rebuilds
   IP-stable.
5. Raise apollo's `max_running_agents` limit, e.g. from 5 to 10–12, and watch sysstat.

**Phase 5: decommission.** After about a week of clean operation, destroy the old droplet
(billing stops only on destroy). Keep the snapshot for a month, then delete it.

**A third machine afterwards:**

1. Add one entry to `machines.yaml` and generate a one-off Tailscale key.
2. Run `machines/provision <name> <size> <region>`, then wait.
3. Run `machines/push-secrets <name>` plus the interactive logins.
4. Run `machines/sase-host-setup` (it calls `sase init` for the new overlay), then
   `sase machine init -B …` on athena.
5. Run `machines/doctor`.

---

## 8. Risks And Open Questions

- **v5 availability and shapes:** at GA (2026-08-26), v5 was in MEM1, RIC1, ATL1 and
  MKC1 only. Confirm the region, and that the exact `g5-…` slug is valid, with
  `doctl compute size list` before provisioning.
- **Price creep:** v5 has no 672-hour cap, and 2026 memory prices are volatile (Hetzner
  and OVH both re-priced). Re-check at purchase.
- **Per-core gain is an estimate.** Phase 2 exists to measure it rather than trust
  vendor claims.
- **`sase init` and the OAuth logins need a TTY.** They stay the manual steps.
  `doctor` makes a missed step obvious.
- **Two hosts named `apollo` during overlap:** keep the new one's SASE service stopped
  until cutover, so AXE routines don't run twice. Also be aware that
  `~/.sase/machine_name` and `sase_apollo.yml` select the same identity on both hosts.
- **Unscripted installers:** the sources of `agy`, `grok` and `muse` in `~/.local/bin`
  weren't traced in this research. Record them in `packages.yaml` during Phase 1.

## Sources

- Live probes: `ssh apollo` (`nproc`, `free`, `lsblk`, `lscpu`, `df`, DO metadata
  `region`/`id`, `sar -u/-q/-r` for 2026-09-15…23, `systemctl --user`, `ss -tlnp`,
  `tailscale serve status`, `apt-mark showmanual`, the uv tool receipt, `~/.sase`
  layout); athena `sase machine list -j`; `gh repo view` visibility checks.
- Repos: chezmoi `home/.chezmoiscripts/*`, `.chezmoiignore`, `private_tailnet.conf`,
  `dot_config/sase/sase_apollo.yml`, `bin/executable_install_sase_github`, `Justfile`;
  sase `docs/remote_dispatch.md`, `docs/configuration.md` (Owner Identity).
- Prior research: `research:202609/temporary_high_capacity_test_machine.md`,
  `research:202609/tailnet_dispatch_setup/tailnet_dispatch_setup.md`.
- [DigitalOcean: How to Resize Droplets](https://docs.digitalocean.com/products/droplets/how-to/resize/)
- [DigitalOcean Droplet pricing page](https://www.digitalocean.com/pricing/droplets)
- [DigitalOcean Droplet pricing docs (v5 per-resource rates, no monthly cap)](https://docs.digitalocean.com/products/droplets/details/pricing/)
- [DigitalOcean: Choosing a plan (Premium vs Regular CPUs, v5 limits)](https://docs.digitalocean.com/products/droplets/concepts/choosing-a-plan/)
- [DigitalOcean blog: Introducing v5 Droplets](https://www.digitalocean.com/blog/introducing-v5-droplets)
- [DigitalOcean changelog: v5 Droplets GA (MEM1, RIC1, ATL1, MKC1)](https://ideas.digitalocean.com/changelog/now-generally-available-v5-droplets)
- [DigitalOcean: Create or restore Droplets from snapshots](https://docs.digitalocean.com/products/snapshots/how-to/create-and-restore-droplets/)
- [DigitalOcean: Why can't I create a Droplet from a snapshot?](https://docs.digitalocean.com/support/why-cant-i-create-a-droplet-from-a-snapshot/)
- [DigitalOcean: How to create a Droplet (user data, doctl)](https://docs.digitalocean.com/products/droplets/how-to/create/)
- [DigitalOcean Backups pricing](https://docs.digitalocean.com/products/backups/details/pricing/)
- [Cloud Mercato: DO c2-32vcpu-64gb pricing](https://pcr.cloud-mercato.com/providers/digitalocean/flavors/c2-32vcpu-64gb)
- [Hetzner price adjustment, 15 June 2026](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)
- [Hetzner AX server matrix](https://www.hetzner.com/dedicated-rootserver/matrix-ax/)
- [OVHcloud US Advance servers](https://us.ovhcloud.com/bare-metal/advance/)
- [OVHcloud: dedicated servers pricing update H2 2026](https://blog.ovhcloud.com/en/posts/dedicated-servers-pricing-update-h2-2026/)
- [Tailscale: install via cloud-init](https://tailscale.com/kb/1293/cloud-init)
- [chezmoi: install packages declaratively](https://www.chezmoi.io/user-guide/advanced/install-packages-declaratively/)
