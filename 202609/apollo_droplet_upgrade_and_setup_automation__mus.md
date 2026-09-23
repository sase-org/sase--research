# Apollo Droplet Upgrade and Setup Automation

**Researcher:** mus (independent swarm report; peer `__cld` / `__gem` reports not consulted)
**Date:** 2026-09-23
**Question:** How best to move the `apollo` DigitalOcean droplet to a more powerful
machine, keep it as a long-term second dev machine, and script setup so a third
identical machine takes as few steps as possible? Is a disk upgrade a forced
reprovision/re-create?

## Summary

- **No — a disk upgrade does not force a re-create.** DigitalOcean supports an
  in-place **Disk + CPU + RAM resize** that grows the disk without rebuilding the
  droplet. It is permanent (disk can never shrink afterward), needs a power-off, and
  costs roughly a minute of downtime per GB of used disk. A CPU/RAM-only resize is
  the reversible variant that leaves disk alone.
- **Current apollo is already the "temporary" upgrade.** On 2026-09-03 it was a Basic
  Premium AMD box in `nyc1` (4 shared vCPU / ~8 GB / 160 GB, 73% full). Today it
  probes as **16 vCPU / 31 GB RAM / 193 GB root disk** (`/dev/vda1`, 120 GB used /
  74 GB free, 63% full), Ubuntu 24.04.3, up 19 days — i.e. approximately the
  CPU-Optimized 16 plan (16 / 32 GB / 200 GB) from the prior research. Region is
  still `nyc1` (droplet_id `568763576`).
- **Apollo was built by hand, not from automation.** Droplet metadata `user-data` is
  empty (only stock DigitalOcean `vendor-data`); there is no `chezmoi` / `stow` /
  `dotdrop` dotfiles manager, no setup repo, and no shell history of a bootstrap.
  Everything below was assembled manually: Tailscale enrollment, `gh` + `claude` +
  `codex` CLIs, `uv` + `just` + Rust + Node toolchains, `uv tool install sase` plus
  plugins, `~/projects/github/sase-org/*` checkouts, a full hand-built home
  directory (`~/bob`, `~/org`, `.gitconfig`, `.ssh`, provider configs), and SASE
  workspaces.
- **Disk pressure comes from agent work, not the base install.** Largest consumers
  observed: `~/.local/state/sase/workspaces/sase-org` **41 GB** (many agent
  workspace clones), `~/.cache` (uv) **21 GB**, `~/projects/github/sase-org`
  **~9–10 GB**, `~/.sase/projects` 6.6 GB + `~/.sase/cache` 3.2 GB. Any sizing for
  the next machine should assume 120 GB used today plus headroom for more parallel
  agents — not just the base OS + toolchain.
- **Recommendation:** (1) snapshot apollo now; (2) capture a small versioned
  bootstrap (cloud-config user-data + one idempotent setup script) derived from
  apollo's actual state; (3) do the **in-place Disk+CPU+RAM resize** of apollo to
  the next tier; (4) prove the automation by spinning the **third machine from
  clean Ubuntu + that bootstrap** (not from the snapshot) so the snapshot stays
  insurance and the script stays honest. Details in §5.

## 1. What apollo is today (observed, not assumed)

Probed over `ssh apollo` on 2026-09-23 (read-only commands):

- `nproc` → 16; `free` → 31 GB RAM; `df /` → `/dev/vda1 193G 120G 74G 63%`;
  `PRETTY_NAME="Ubuntu 24.04.3 LTS"`; uptime 19 days.
- Droplet metadata endpoint: `droplet_id 568763576`, hostname `apollo`, region
  `nyc1`. `user-data` endpoint returns empty; `vendor-data` is only the stock DO
  cloud-config (root locked down, `manage_etc_hosts`, Ubuntu mirrors). So **no
  custom cloud-init was used at creation**.
- Runtime present: `just 1.50.0` (via `~/.cargo/bin`), `uv 0.11.8`
  (`~/.local/bin/uv`, notably absent from non-login `PATH` which explains the
  earlier `uv not found`), `cargo`/`rustc`, system `node` + `python3.12`,
  `tailscale` CLI, `/usr/bin/gh`, `/usr/local/bin/claude`, `/usr/local/bin/codex`.
- SASE present as a `uv tool` install (`~/.local/share/uv/tools/sase/bin/sase`
  works; bare `sase` is not on non-login `PATH`). `sase plugin list` shows the
  three official built-ins installed (github, research-artifacts, telegram).
- Source checkouts: `~/projects/github/sase-org/` contains `sase`, `sase-core`,
  `sase-github`, `sase-research-artifacts`, `sase-telegram`, `sdd`.
- Fleet wiring: `tailscale status` shows `apollo`, `athena`, `kellys-macbook-pro`
  (plus offline `pixel-10-pro-xl`); `tailscale serve` exposes
  `https://apollo.tail297af1.ts.net → http://127.0.0.1:7629`.
- Home directory is bespoke: stock-Ubuntu `.bashrc`, full `.gitconfig` (delta,
  aliases, `user.email bryanbugyi34@gmail.com`), `~/.ssh` keys
  (`id_rsa`, `id_bob_vault`, `tailnet.conf`), `~/bob`, `~/org`, `~/bin` full of
  personal scripts, macOS carryover dirs (`~/Library`, `.hammerspoon`). No
  dotfiles repo or manager found (`chezmoi`/`dotdrop`/`stow` all absent).
- `~/sase` on apollo is **not** the sase repo — it contains only
  `memory skills xprompts`. The real checkouts live under `~/projects/github/`.

Prior-research anchor: the 2026-09-03 report
(`research:202609/temporary_high_capacity_test_machine.md`, read via audited
` sase artifact read`) recommended a fresh CPU-Optimized 48 vCPU / 96 GB box for a
weekend wave and documented apollo at 4 vCPU / 8 GB / 160 GB. The current 16/31/193
shape is consistent with apollo itself having been resized up to roughly `c-16`
since then and kept.

## 2. DigitalOcean resize semantics (the "must I reprovision?" question)

Verified against the live docs on 2026-09-23
(`https://docs.digitalocean.com/products/droplets/how-to/resize/`,
`.../how-to/provide-user-data/`):

- Two resize modes for CPU droplets: **CPU and RAM only** (reversible, disk
  untouched) vs **Disk, CPU and RAM** (grows CPU/RAM **and permanently grows the
  disk**). The user's mental model ("disk upgrade ⇒ re-create") is understandable
  but wrong: the disk-growing resize is an in-place operation, not a rebuild.
- Hard constraints:
  - You can only resize to a plan with **disk ≥ current disk**, and you can
    **never shrink a disk** (filesystem-corruption risk). A disk-growing resize
    cannot be undone by resizing back down.
  - **No bundled-plan ↔ v5-configuration cross-resizes.** Apollo's sizes
    (160 GB → 193 GB usable) look like bundled CPU-Optimized lineage; confirm the
    exact plan/slug in the control panel or `doctl` before committing, and stay
    within the same lineage.
  - Droplet must be **powered off**; budget **~1 min per GB of used disk**
    (apollo: 120 GB used ⇒ plan a generous window; actual time is usually shorter
    but hypervisor moves transfer the whole used disk).
  - **Snapshot first.** DO strongly recommends it; snapshots cost
    ~$0.06/GiB-month of used disk prorated (≈ $7/mo for a 120 GB image, pennies
    for a few days of insurance — delete after verifying the resize).
  - If `df -h` is unchanged after a disk resize, the partition/filesystem did not
    grow — diagnose with `gdisk -l /dev/vda` and `growpart /dev/vda 1` per the
    docs. Ubuntu 24.04 images normally grow automatically; keep this as a
    fallback, not the plan.
- Adjacent facts that shape the recommendation:
  - **Powered-off droplets still bill**; only `destroy` stops billing. Snapshots
    bill separately until deleted.
  - **User-data / cloud-init** (`--user-data` / `--user-data-file` in `doctl`,
    "Startup scripts" in the panel) runs **only at first boot** and is immutable
    afterward — it is the correct hook for third-machine automation, not for
    mutating apollo.
  - **Snapshots are bootable images**: `doctl compute droplet create --image
    <snapshot-id>` (or the panel's Snapshots tab, or Terraform
    `digitalocean_image` / `droplet_snapshot` data sources) clones a machine
    including its disk. That is the fast path to an identical box, but a clone
    carries forward everything — including cruft and stale credentials — which is
    why §5 keeps the snapshot as insurance and proves a clean bootstrap
    separately.
  - **Volumes** (attachable block storage) are the escape hatch when only bulk
    data needs room: attach/detach/delete without resizing root. They do **not**
    substitute for root-disk headroom for SASE workspaces, uv caches, and system
    state — do not solve this problem with a volume.

## 3. Options considered

| Option | What it is | Pros | Cons |
| --- | --- | --- | --- |
| **A. In-place Disk+CPU+RAM resize of apollo** | Power off → snapshot → resize to next tier (e.g. CPU-Opt 32: 32 vCPU / 64 GB / 400 GB, or 48 / 96 / 600) → verify `df -h` → power on | Keeps IP, hostname, Tailscale identity, SSH keys, SASE state; single downtime window; no re-enrollment | Irreversible disk growth; downtime scales with 120 GB used; does not by itself produce automation for machine #3 |
| **B. Snapshot-clone to a new bigger droplet** | Snapshot apollo → create `apollo-2` from snapshot at larger size → cut over | Apollo keeps running during prep; new box is byte-identical; trivially yields "machine #3 pattern" | Clone inherits 120 GB of state + secrets (must rotate Bootstrap/secrets, re-enroll Tailscale, rename host); snapshot of a running DB-ish workload (sqlite WALs under `~/.sase`) risks minor inconsistency — snapshot while quiet or powered off |
| **C. Fresh droplet + versioned bootstrap** | Clean Ubuntu 24.04 in `nyc1` + cloud-config user-data + one idempotent setup script → install toolchain, SASE, repos, dotfiles, Tailscale | Only path that actually delivers "third identical machine in a few steps"; forces the automation the user wants; no inherited cruft | Up-front scripting effort (half a day); provider/secret enrollment stays manual by design (OAuth, Tailscale auth, API keys) |
| **D. Attach a volume instead of growing root** | Extra 100–500 GB volume for overflow | No downtime, reversible, cheap | Wrong tool here: workspaces, caches, and `~/.sase` live on root; a volume only helps if bulk data is relocated onto it |

The prior weekend-research already ranked fresh-box-over-resize for isolation and
ranked CPU/RAM-only resize second for zero-setup speed. That ranking flips now
that apollo is a keeper with 120 GB of lived-in state: **in-place disk resize
(A) wins for the upgrade itself, and fresh-bootstrap (C) wins for the
repeatability goal.** Do both, in that order, with the snapshot (B's mechanism)
as the safety net rather than the primary path.

## 4. What is and is not scriptable (from apollo's actual state)

Fully scriptable (bake into user-data + bootstrap script):

- `apt` base: `build-essential pkg-config libssl-dev git curl unzip tmux
  fontconfig fonts-firacode nodejs npm gh gdisk parted` (apollo has all of
  these; versions float — pin only where it matters).
- Toolchains: `uv` (astral installer), `just` (`just.systems` installer to
  `~/.local/bin`), Rust (`rustup`), Node (already apt; or pin via `fnm` if the
  fleet needs it).
- `uv tool install sase` (+ `--with` plugins or follow-up `sase plugin install`
  for `sase-github`, `sase-research-artifacts`, `sase-telegram` — mirror apollo's
  installed set; panel installs need `gh` auth first).
- Checkout layout: `~/projects/github/sase-org/{sase,sase-core,…}` via `git
  clone` + `sase repo open`-compatible paths; run `just install` analog
  (`uv tool install` path needs no `../sase-core` dance unless doing dev
  installs — apollo's working install is the published wheel, not a dev
  checkout, so keep the bootstrap on the published path).
- Dotfiles: **today there is no source of truth** — this is the biggest gap.
  Options in ascending order of investment: (i) `rsync -a` a curated dotfile
  list from apollo (`~/.gitconfig`, `~/.gitmessage`, `~/.gitignore_global`,
  `~/.ssh/config` sans keys, `~/.config/sase/`, shell rcs) into the bootstrap
  repo; (ii) graduate that list to a tiny `dotfiles.git` + `stow`/symlink step;
  (iii) adopt `chezmoi` (linked but unused) later. Do (i) now; (iii) is not
  required to unblock machine #3.
- Tailscale install + `tailscale up` skeleton (repo key or one-shot auth key
  passed at create time, never committed); `tailscale serve` proxy line for the
  gateway port.
- `sase` first-run scaffolding: `sase completion install` note,
  `SASE_TEST_GATE_SLOTS` export for big boxes (prior research: 48 vCPU ⇒ 42
  tokens; scale as vCPUs − reserve), `sase doctor` / `sase core health` gates.

Deliberately manual (checklist, not script):

- Secrets and device-bound auth: SSH private keys (`id_rsa`, `id_bob_vault`),
  `gh auth login`, Claude/Codex/Gemini provider logins, Tailscale auth approval,
  SASE enrollment bundles / Bearer [REDACTED] (`credential_ref` + `installation_pin` per the
  remote-machine-management research — no API mints them remotely), GPG keys.
  Script the *detection* (`sase doctor`, `gh auth status`, `tailscale status`)
  and stop for a human.
- Data sync: `~/bob`, `~/org`, `~/projects` beyond the code checkouts. `rsync`
  over Tailscale after the base is up; do not bake personal data into images.
- DNS/hostnames: keep `apollo` stable; name the new box distinctly
  (`apollo-2` / `vega` / `sase-testbox`) to avoid Tailnet/SSH alias collisions.

## 5. Recommended solution

### 5a. Upgrade apollo (in place — no reprovision)

1. **Quiesce + snapshot.** Stop agents/suites on apollo (`sase` procs, `tmux`
   waves). Snapshot from the panel or API (`POST
   /v2/droplets/<id>/actions {"type":"snapshot","name":"apollo-pre-resize-20260923"}`);
   wait for completion. Note the snapshot id.
2. **Record the baseline.** `nproc; free -g; df -h /; doctl compute droplet get
   <id>` (install/auth `doctl` locally first — currently absent on both ends).
   Confirm current plan lineage (bundled vs v5) and that the target tier (start
   with **CPU-Optimized 32**: 32 vCPU / 64 GB / 400 GB; go 48 / 96 / 600 only if
   10-wide `check-full` waves are routine) appears in apollo's resize picker.
3. **Power off and resize with disk.** Either in the panel (Droplet → Settings →
   Resize → check the disk-included option) or
   `doctl compute droplet-action resize <id> --size c-32 --resize-disk=true`
   (slug varies: `c-32` vs `c2-…` premium-NVMe — take what `size list` shows for
   `nyc1`). Expect a long window with 120 GB used; announce it.
4. **Verify before deleting the snapshot.** Power on; `df -h /` must show the new
   size (≈ 400 GB tier). If not, `gdisk -l /dev/vda` + `growpart /dev/vda 1`
   per §2, then `resize2fs` as indicated. Run `sase doctor`, `sase core health`,
   one `just check-full` on apollo, and confirm Tailscale + `tailscale serve`
   survived. Only then delete the pre-resize snapshot.
5. **Re-tune the suite gate.** Set `SASE_TEST_GATE_SLOTS` ≈ vCPUs − reserve
   (e.g. 28 for 32 vCPU) so the 32-token default cap does not idle the new box.

Rollback: if the resize misbehaves, create a same-size-or-larger droplet from
the pre-resize snapshot (panel Snapshots tab or `--image <snapshot-id>`) and
re-point Tailscale/SSH. Do not attempt to resize back down — disk cannot
shrink.

### 5b. Automate so machine #3 is a few steps (do this around the resize, not after)

1. **Create `bootstrap-apollo` (one repo, two files).** Suggested home: a small
   dir in the sase project or a `droplet-bootstrap` repo — the location matters
   less than that it is versioned and it is the *only* recipe. Contents:
   - `cloud-config.yml` — minimal user-data: default user, SSH keys (by
     fingerprint, never private material), `packages:` (the apt list in §4),
     `runcmd:` that fetches and execs the setup script as the working user.
   - `setup.sh` — idempotent: apt → uv/just/rust/node → `uv tool install sase`
     + plugins → `git clone` fleet checkouts → curated dotfiles (`rsync` list
     from §4) → Tailscale join (auth key from env/flag) → `sase doctor` gate →
     print the manual checklist (gh/provider logins, enrollment bundle,
     data rsync, gate slots).
2. **Extract, don't invent.** Build the dotfile list and apt list by diffing a
   clean Ubuntu 24.04 against apollo (`apt list --installed`, `ls ~/bin`,
   `~/.gitconfig`, `~/.config/sase`), not from memory. Commit the exact `uv`,
   `just`, and plugin versions probed in §1 as defaults with override flags.
3. **Prove it with machine #3 from clean Ubuntu** (not from the apollo
   snapshot):
   `doctl compute droplet create <name> --region nyc1 --image ubuntu-24-04-x64
   --size c-16 --ssh-keys <fp> --user-data-file cloud-config.yml --wait`,
   then run/check `setup.sh` idempotently (run it twice — the second run must be
   a no-op). Gate on `sase doctor` + `sase core health` + one `just check-full`.
   Time the run; that timing is the honest "N steps / M minutes" answer for the
   next machine.
4. **Keep the snapshot out of the golden path.** Retain one tested snapshot as
   disaster recovery (cheap, prorated), but document the clean-bootstrap as the
   canonical way to make machines. Snapshots silently fossilize secrets and
   41 GB of workspace churn; the script does not.
5. **Tokenizer on cost.** Re-check slugs/prices/limits at purchase time (prior
   numbers: CPU-Opt 16 ≈ $0.50/hr, 32 ≈ $1.00/hr, 48 ≈ $1.50/hr in Sep 2026;
   powered-off still bills; snapshots ≈ $0.06/GiB-mo). Set a calendar reminder
   to delete one-off snapshots and to downsize only CPU/RAM if load disappoints
   (disk stays — size it for the 200 GB+ steady state, not today's 120 GB).

### What was not verified

- Exact target slugs, current prices, and account limits (no authenticated
  `doctl` on either end in this session — confirm in the create/resize dialog).
- Bundled vs v5 lineage of apollo (inferred bundled from the 160→200 GB sizes;
  the picker will refuse a cross-lineage resize if wrong — that refusal is the
  backstop).
- Full provenance of apollo's home directory (no bootstrap history survived;
  the curated dotfile list in §5b step 2 closes this by construction).
- Provider-CLI and SASE-enrollment credential flows beyond existence checks
  (by design manual; the bootstrap asserts their presence rather than
  provisioning them).

## Sources

- Live probes 2026-09-23: `ssh apollo` (`nproc`, `free`, `df`, `uptime`,
  `tailscale status/serve`, `sase plugin list`, home/repo listings); DO metadata
  endpoints (`metadata/v1.json`, `vendor-data`, `user-data`, `region`).
- Prior research (audited read): `research:202609/temporary_high_capacity_test_machine.md`
  (2026-09-03 sizing, pricing, and setup runbook); `research:202609/remote_machine_management_enablement.md`
  (enrollment-bundle / `sase machine` gaps — why credential steps stay manual).
- Docs: [DO resize](https://docs.digitalocean.com/products/droplets/how-to/resize/)
  (two resize modes, irreversibility, no-shrink, no bundled↔v5, snapshot-before,
  `growpart` fallback); [DO user-data](https://docs.digitalocean.com/products/droplets/how-to/provide-user-data/)
  (cloud-init at first boot only, panel/API/`doctl --user-data-file`); snapshot→droplet
  via `--image <snapshot-id>` / Snapshots tab / Terraform `digitalocean_image`.
- Repo: `INSTALL.md` (`uv tool install sase` as canonical path, plugin model);
  `Justfile` / `sase-core-revision.txt` (dev-install vs published-wheel paths).
