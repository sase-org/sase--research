---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
---

# A Temporary High-Capacity Machine For Parallel Sase Test Suites (Through Sunday)

**Research question:** Bryan needs a much faster machine for developing sase — one that
can run **5–10 full `just check-full` suites concurrently** — but only until **Sunday
2026-09-06** (~2–3 days). The active machine (Apple M1, 8 cores, 8 GB) must stay
unburdened, and apollo is too slow. Is a short-lived DigitalOcean droplet (or similar)
feasible, and if so what size, at what cost, and how should it be set up?

**Scope:** sase at master `f67169ea7`. Evidence from the repo: `justfile` (check-full
composition, `_setup`/`_setup-visual` toolchain), `tools/run_pytest` + `tests/_suite_gate_budget.py`
+ `tests/_suite_gate_env.py` (host-wide worker-token pool), `.github/workflows/ci.yml`
(canonical Linux platform), and the `two-speed-verification` decision record (measured
suite cost). Live probes: local `sysctl`, `ssh apollo` (nproc/free/metadata). Pricing
from DigitalOcean, Hetzner, and AWS pages fetched 2026-09-03; re-confirm at purchase
time.

---

## Executive Summary

**Yes — this is not only possible, it is cheap and low-friction.** The DigitalOcean
account already exists (apollo *is* a DO droplet: its CPU reports `DO-Premium-AMD`,
4 shared vCPU / 8 GB / 160 GB disk, region `nyc1`). DigitalOcean bills droplets
**per-second** (since 2026-01-01, 60-second minimum) and billing stops the moment a
droplet is **destroyed** — so a machine that lives Thursday→Sunday costs only those
hours.

**Recommendation: create a fresh CPU-Optimized 48 vCPU / 96 GB droplet in `nyc1`
(~$1.50/hr → roughly $72 for 48h, $108 for 72h), run the suites there, and destroy it
Sunday.** The repo's own suite-gate machinery already load-balances any number of
concurrent full runs on one host through a shared per-user token pool; the only tweak a
big dedicated box needs is `SASE_TEST_GATE_SLOTS=42` to lift the default 32-token cap.
Expected throughput: a wave of **10 concurrent full suites completes in roughly 15–20
minutes**; 5 concurrent in roughly 8–10 minutes.

A close runner-up that requires zero new-machine setup: **temporarily resize apollo**
(CPU/RAM-only resize, which is reversible) up to a CPU-Optimized plan for the weekend
and back down on Sunday. It loses on disk headroom (apollo is 73% full) and requires
two reboots of a machine that has other jobs, so the fresh droplet is preferred.

---

## 1. The Workload, Measured

What one "full test suite" run actually costs, from repo evidence:

- **~61 worker-minutes per full-suite run** — the measured number in the
  `two-speed-verification` decision record (the same measurement that makes
  `check-full` monitor-only on shared hosts). 5–10 concurrent runs is therefore
  **305–610 worker-minutes per wave**.
- **`just check-full` = every lint gate + the full suite** (`justfile:655`): fmt
  checks, keep-sorted, ruff, mypy, flags, pyscripts, test-waits, changelog,
  terminology, symvision, toobig, `sase` validation, committed plans, then
  `just test-cost` (full default suite with cost attribution) plus budget and
  flake-baseline checks. The lint gates add a few CPU-minutes per run (mypy is the
  heavy one) on top of the 61 test worker-minutes.
- **~500 MiB peak RSS per pytest worker**, budgeted at 700 MiB/worker with 8 GiB
  host reserve (`tests/_suite_gate_budget.py:28-36`, remeasured 2026-08-09). Memory is
  not the binding constraint on any plan with ≥2 GB per vCPU.
- **Linux is the canonical platform.** CI runs `ubuntu-latest` everywhere
  (`.github/workflows/ci.yml`), and the PNG visual-snapshot goldens are pinned to the
  canonical Linux renderer stack (fontconfig + Fira Code). A Linux cloud box is the
  *preferred* environment — it can run `just test-visual` byte-exact, which macOS
  cannot.

### The suite gate already supports N concurrent runs on one host

This was the main open risk and it resolves in favor of the plan:

- All runs under one UID share a single token pool at
  `/tmp/sase-pytest-tokens-<uid>` (`tests/_suite_gate_env.py:43`), regardless of which
  clone they run from. Concurrent `check-full` runs coordinate; they do not
  oversubscribe each other.
- The default host budget is `min(cpus − cpus/8, (mem − 8 GiB)/700 MiB, **32**)`
  (`tests/_suite_gate_budget.py:96-112`). The hard 32-token default cap means a 48-vCPU
  box idles a third of its cores unless you set **`SASE_TEST_GATE_SLOTS=42`**
  (48 − 6 reserved). Memory never binds on the recommended plans
  (96 GB → ~128 tokens).
- Each run's automatic lease asks for floor 4 / fair-share ceiling (≤28), so ten
  concurrent runs at floor-4 need 40 tokens — which fits a 42-token pool and does
  **not** fit the 28-token pool of a 32-vCPU box (some runs would queue). This is the
  argument for 48 vCPU over 32 if "10 at once" is a real target.

### Sizing math (idealized linear scaling; xdist is slightly worse in practice)

| Scenario | Tokens/run | Test-phase wall time | Wave incl. lints |
| --- | --- | --- | --- |
| 10 × check-full, 48 vCPU (42 tokens) | ~4 | ~15 min | **~15–20 min** |
| 5 × check-full, 48 vCPU (42 tokens) | ~8 | ~8 min | **~8–12 min** |
| 10 × check-full, 32 vCPU (28 tokens) | ~2.8 + queueing | ~22 min | ~25–30 min |
| 1 × check-full alone, 48 vCPU | up to 28 (ceiling) | ~2–4 min | ~5–8 min |
| (baseline) 1 × check-full on apollo, 4 shared vCPU | ≤4 | ~15–20+ min | ~25+ min |

The 61-worker-minute figure was measured on the shared dev host; dedicated 2.6 GHz+
cloud vCPUs should be in the same ballpark or better, but re-measure one run on the new
box before trusting the wave estimates.

## 2. Why Apollo Cannot Do This As-Is

Probed over SSH on 2026-09-03: apollo is a DigitalOcean **Basic Premium AMD** droplet
in **nyc1** — 4 shared vCPU, 7.8 GiB RAM (4.1 GiB already in use), 160 GB disk at
**73% full (42 GB free)**. One full suite alone is a ~15–20 minute affair there and the
suite-gate memory limit would grant it only a handful of workers; ten concurrent runs
is out of the question. But its existence is the key logistics fact: **the DO account,
SSH keys, and billing are already set up.**

## 3. Option A (Recommended): Fresh DigitalOcean CPU-Optimized Droplet

DigitalOcean CPU-Optimized droplets have **dedicated** (not shared) vCPUs at 2.6 GHz+,
2 GB RAM per vCPU. Current bundled-plan pricing (fetched from DO's pricing page
2026-09-03):

| Plan | vCPU | RAM | SSD | Hourly | ~48h | ~72h |
| --- | --- | --- | --- | --- | --- | --- |
| CPU-Opt 16 | 16 | 32 GiB | 200 GiB | $0.50 | $24 | $36 |
| CPU-Opt 32 | 32 | 64 GiB | 400 GiB | $1.00 | $48 | $72 |
| **CPU-Opt 48** | **48** | **96 GiB** | **600 GiB** | **$1.50** | **$72** | **$108** |

Billing facts that make the two-day rental work (DO droplet pricing docs):

- **Per-second billing** with a 60-second/$0.01 minimum, capped at 672 hrs/month.
- **Powered-off droplets still bill** (resources stay reserved). Billing ends only on
  **destroy** — so destroy on Sunday, don't just shut down.
- A snapshot before destroying costs $0.06/GiB-month of used disk, prorated — a ~20 GB
  snapshot is ~$1.20/month, cheap insurance if the box might be wanted again.

Caveats to check at create time (2 minutes in the control panel or `doctl`):

- **Account limits:** larger sizes may need a limit bump (Account → Limits). The
  account is established (apollo), so this is likely already fine or instantly granted.
- **Region/slug availability:** run `doctl compute size list | grep -E '^c'` to see the
  exact slugs (`c-48` regular vs `c2-…` premium-NVMe variants; premium runs slightly
  higher). Create in `nyc1` to be network-adjacent to apollo.

### Setup runbook (Ubuntu 24.04, ~20–30 minutes)

```bash
# 1. Create (or use the control panel)
doctl compute droplet create sase-testbox \
  --region nyc1 --image ubuntu-24-04-x64 --size c-48 \
  --ssh-keys <fingerprint> --wait

# 2. System deps (root)
apt update && apt install -y build-essential pkg-config libssl-dev \
  git curl unzip tmux fontconfig fonts-firacode nodejs npm

# 3. Toolchain (as the working user)
curl -LsSf https://astral.sh/uv/install.sh | sh
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh \
  | bash -s -- --to ~/.local/bin

# 4. Repos: sase + sase-core side by side (the justfile's ../sase-core fallback)
git clone <sase-remote> sase && git clone <sase-core-remote> sase-core
cd sase && just install     # builds sase_core_rs from ../sase-core

# 5. N working clones — --local hardlinks objects, so this is fast and small
for i in $(seq 1 10); do git clone --local ~/sase ~/ws$i; done
for i in $(seq 1 10); do (cd ~/ws$i && just install); done

# 6. Lift the default 32-token cap for the whole session
echo 'export SASE_TEST_GATE_SLOTS=42' >> ~/.bashrc

# 7. Fire the wave in tmux (the shared token pool does the load balancing)
for i in $(seq 1 10); do
  tmux new-window -t suites -n ws$i "cd ~/ws$i && just check-full"
done

# Sunday teardown — this is what stops billing
doctl compute droplet delete sase-testbox
```

Notes:

- The uv cache makes clones 2–10 install in seconds after the first. The Rust build
  reuses the shared `../sase-core` cargo target dir across clones; alternatively build
  the wheel once and point every clone at it with `SASE_CORE_WHEEL=<path>` (the
  justfile supports this explicitly).
- Get work onto the box by pushing a branch and pulling, or `rsync` the working tree.
  Installing Tailscale (`curl -fsSL https://tailscale.com/install.sh | sh`) makes it
  feel like a local host from both the M1 and apollo.
- The two-speed rule exists because of *shared* host capacity; on a dedicated
  disposable box, running `check-full` freely — including 10 at once — is exactly what
  the box is for.

## 4. Option B: Temporarily Resize Apollo (Reversible)

DO supports a **CPU/RAM-only resize**, which keeps the disk and is explicitly
**reversible** — resize up Friday, back down Sunday. Apollo is a bundled plan, and
bundled→bundled cross-class resizes (Basic → CPU-Optimized) are allowed; only
bundled↔v5-configuration moves are prohibited. Downtime is a power-off plus roughly a
minute per GB of *used* disk if the droplet migrates hypervisors (apollo: 113 GB used,
so plan for possibly an hour of migration window each way, usually much less).

- **Pro:** zero new-machine setup — apollo already has the environment, repos, and any
  SASE host wiring; net extra cost over its normal ~$0.08/hr is ~$0.92/hr at the
  32-vCPU tier (~$44 for 48h).
- **Con:** only 42 GB of disk free — tight for 10 clones + venvs (a temporary block
  storage volume fixes this: 100 GB ≈ $0.66 for two days); two downtime windows on a
  machine with other roles; a 32 vCPU/64 GB target yields the weaker 28-token profile
  above (48 vCPU CPU-Optimized exists as a bundled plan, but confirm it appears in
  apollo's resize picker in nyc1).

Use this if the priority is "no setup at all" over throughput and isolation.

## 5. Option C: Other Providers (For Completeness)

| Provider / plan | vCPU / RAM | Hourly | ~48h | Notes |
| --- | --- | --- | --- | --- |
| Hetzner CCX53 (Ashburn) | 32 dedicated / 128 GB | €0.855 | ~€41 (~$45–50) | US prices rose 2.1–2.6× in June 2026; now ≈ DO. New-account verification friction. |
| Hetzner CCX63 (Ashburn) | 48 dedicated / 192 GB | €1.368 | ~€66 (~$72–78) | Same friction; hourly billing, delete anytime. |
| AWS c7i.12xlarge (us-east-1) | 48 / 96 GB | $2.142 on-demand | ~$103 | Spot is ~50–70% off but interruptible mid-wave; most setup friction. |
| GitHub larger runners | 16–64 vCPU | $0.064+/min (16 vCPU) | — | $3.84+/hr equivalent; workflow-bound, not an interactive dev box. |

None beats DigitalOcean here once the existing account, existing region, and two-day
horizon are counted. Hetzner's pre-June-2026 price advantage in the US is gone.

## 6. Risks And Open Items

1. **Throughput estimates are linear-scaling idealizations.** Re-measure one
   `check-full` on the new box (the `--durations` and test-cost reports make this easy)
   before promising wave times.
2. **`SASE_TEST_GATE_SLOTS` must be set** or the box runs at 32/42 of its capacity.
   Conversely, don't set it above vCPUs-minus-reserve; the gate's budget math exists to
   prevent oversubscription collapse (see the 26-workers-on-2-CPUs contention baseline
   in the justfile: 116 failures pre-fix).
3. **Destroy, don't power off**, on Sunday — powered-off droplets bill in full.
4. **Prices/limits were fetched 2026-09-03** and DO notes v5-configuration billing is
   evolving; confirm the exact slug, region availability, and account limit in the
   creation dialog before committing.
5. If the box should run SASE *agents* (not just manual tmux waves), that is a
   follow-on integration question (host wiring, credentials, workspace provisioning)
   deliberately out of scope here.

## Sources

- Repo: `justfile` (`check-full`, `_setup`, `_setup-visual`, contention baselines),
  `tools/run_pytest`, `tests/_suite_gate_budget.py`, `tests/_suite_gate_env.py`,
  `.github/workflows/ci.yml`, `pyproject.toml`; sase memory `lint_and_test.md` and
  decision record `decisions:two-speed-verification` (61 worker-minutes/run).
- Live probes: `sysctl` (local M1), `ssh apollo` (`nproc`, `free`, `df`,
  DO metadata endpoint → `nyc1`, CPU model `DO-Premium-AMD`).
- [DigitalOcean droplet pricing docs](https://docs.digitalocean.com/products/droplets/details/pricing/) — per-second billing, powered-off billing, destroy semantics.
- [DigitalOcean pricing page](https://www.digitalocean.com/pricing/droplets) — CPU-Optimized plan table (fetched 2026-09-03).
- [DigitalOcean resize docs](https://docs.digitalocean.com/products/droplets/how-to/resize/) — CPU/RAM-only resizes reversible; bundled↔v5 resizes prohibited.
- [Hetzner cloud pricing (costgoat aggregator)](https://costgoat.com/pricing/hetzner) and [Northflank on the June 2026 Hetzner US price increase](https://northflank.com/blog/hetzner-cloud-server-price-increases).
- [AWS c7i pricing (economize)](https://www.economize.cloud/resources/aws/pricing/ec2/c7i.12xlarge/).
