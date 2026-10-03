# Apollo OOM-kills sase agents — research (`__mus`)

## Question

Apollo keeps killing all of its sase agents, suspected OOM. What is causing it and how to fix it?

## Bottom line

The most likely cause is **host capacity, not a single sase bug**: apollo has ~half
athena's RAM and **zero swap**, while sase's runner admission is **count-based, not
memory-aware**. A full fleet of heavy agents (each a Python runner + a Node/Python
provider CLI + workspace checkout, plus rustc/pytest children) fits on athena only
because of 63 GiB of swap; the same fleet on apollo hits a hard wall and the kernel
OOM-killer takes out the largest processes — the agents. Fix in this order:
(1) give apollo swap, (2) lower apollo's `max_running_agents` override, (3) keep
heavy builds/tests off apollo or staggered. Longer term, make admission memory-aware
or at least per-host-tuned.

## Verified host facts

All values below were observed directly in this session (2026-10-03); each key value
was corroborated by a second independent read.

| Signal | apollo (via `ssh apollo`) | athena (this host) |
|---|---|---|
| `hostname` | `apollo` | `athena` |
| `free -h` (read twice, stable) | Mem 31 Gi, Swap **0 B / 0 B** (~3.8–3.9 Gi used, ~19–21 Gi free at idle, no agents running) | Mem 62 Gi, Swap 63 Gi (~40 Gi used, ~18 Gi swap used, load ~30 on 64 cores) |
| `nproc` | 16 | 64 |
| Disk (`df -h /`) | 193 G total, 142 G used, **51 G avail (74%)** — disk is not the problem | 207 GiB free at workspace root and sase home (`sase doctor -C resources`) |
| `max_running_agents` override | `~/.sase/max_running_agents_override.json`: `limit: 5` | `~/.sase/max_running_agents_override.json`: `limit: 8` (shipped default in `src/sase/default_config.yml`: 10) |
| Live fleet (athena) | n/a (idle at check time) | `sase agent list`: **45 rows** (RUNNING + WAITING + QUEUED), TUI header load against the override budget |

Notes on provenance:

- apollo's `free`/`nproc` were read twice over separate `ssh` invocations minutes
  apart and agreed (31 Gi / 0 swap / 16 cores). `df` agrees disk is healthy.
- athena's `free` was read twice (direct + via a second shell) and agreed (62 Gi /
  63 Gi swap, ~40 Gi used + ~18 Gi swap used).
- The apollo override file (`limit 5`) and athena override file (`limit 8`) were each
  `cat`-ed directly. The shipped default (`max_running_agents: 10`) was read in
  `src/sase/default_config.yml:67`.
- `sase doctor -C resources` passes on athena (disk OK); it does not check RAM/swap,
  which is part of the gap (see §5).

What I could **not** verify (single-source or blocked):

- The actual kernel OOM log on apollo. `journalctl --dmesg` over ssh returns "no
  entries" (unprivileged user outside `adm`/`systemd-journal` cannot see other users'
  and system messages), and plain `dmesg -T | grep -i oom` returned nothing usable.
  The OOM-killer conclusion is therefore **inferred from capacity math + symptom**,
  not from a confirmed `Killed process … total-vm …` line. Confirm with the commands
  in §4 (needs sudo or `adm` group on apollo).

## Why agents die on apollo but survive on athena

### 1. No swap = no cushion

Athena is itself under heavy memory pressure right now: 40 of 62 Gi used plus 18 Gi
of swap consumed, load average ~30. It survives because 63 Gi of swap absorbs spikes.
Apollo at idle already uses ~4 Gi of 31 Gi with **zero swap**. There is nowhere for a
spike to go: once anonymous pages exceed ~31 Gi, the kernel must reclaim file pages
and then invoke the OOM-killer, which picks the largest RSS holders — agent runners
and compilers — and kills them. The user-visible effect is "all of its sase agents"
dying at once, possibly together with their provider-CLI children.

### 2. Each agent is heavy, and admission counts agents, not bytes

From `ps aux --sort=-%mem` on athena (two snapshots minutes apart, consistent ranking):

- `sase tui` itself: ~3.2–3.4 Gi RSS (PID 872820). The perf runbook
  (`docs/perf_runbook.md`) documents this class of problem: the TUI once reached
  ~10 Gi RSS before host-relief work brought it to ~766 MiB; it has since regrown.
- Each `axe/run_agent_runner.py`: ~350 MiB–1.1 Gi RSS (a dozen live at once).
- Each pytest worker (`python -u -c import sys;exec(...)`, `pytest -n 4`): ~1.0–1.2 Gi.
- Each `rustc --crate-name sase_core_rs … -C opt-level=3 -C lto=thin`: ~1.3–1.9 Gi RSS.
- Provider CLIs per agent (`claude -p … stream-json`, `codex exec …`, `muse-bin …
  exec`, `agy … --print`): ~200–450 MiB each, Node-based ones more.
- One-off `git pack-objects` during workspace/sidecar staging: ~1.1 Gi RSS.

So one "agent doing real work" (runner + provider CLI + one build or test child)
plausibly costs **1–3 Gi**, and a 5-wide research swarm where every member compiles
or runs `pytest -n 4` can transiently need **10–20+ Gi on top of the ~4 Gi base** —
before counting the TUI, the scheduler/routines, prometheus (~3 Gi on athena,
probably absent on apollo), and page cache from full workspace clones
(`sase_14`, `sase_21`, … are full checkouts, each with its own `.venv` and
`cargo-targets`).

Sase's gate does not see any of this. `docs/troubleshooting/runner-slots.md` and
`src/sase/default_config.yml` confirm the model: a global **count budget**
(`max_running_agents`, default 10; apollo override 5, athena override 8), each normal
agent claiming 1.0 unit, `%queue(weight=…)`/`capacity=` as authored exceptions.
There is no RSS/swap/pressure check at admission, no cgroup cap per agent, and no
per-host auto-tuning. Five "small" agents fit; five agents that each fork rustc +
pytest do not — and the gate cannot tell the difference.

### 3. Swarm fan-out multiplies the worst case

The current fleet shows the pattern: 45 agent rows on athena, including 5-member
research swarms (`research.3h.*`, `research.3g.*`) plus epic workers (`sase-1eq.*`,
`toobig-6x.*`) and routine refresh chops. A 5-researcher swarm dispatched to apollo
lands 5 runners + 5 provider CLIs nearly simultaneously, each cloning/checking out a
workspace and then running the same build/test commands. Correlated fan-out like this
is the classic OOM trigger: individually each agent fits, together their peaks align.

### 4. Secondary contributors (aggravating, not root cause)

- **TUI memory growth.** The runbook's athena baseline shows the TUI is capable of
  multi-GiB RSS over long sessions. If a TUI (or `sase service` host) runs on apollo,
  it eats a fixed multi-GiB slice of the 31 Gi before any agent starts.
- **Concurrent Rust builds.** `sase-core` release builds with `lto=thin`,
  `codegen-units=1` are the largest single RSS items observed (up to ~1.9 Gi each).
  Two overlapping builds plus five agents is enough to cross the line on a 31 Gi
  swapless box.
- **`pytest -n 4` worksteal.** The default fast suite shards across 4 workers at
  ~1 Gi each. Fine on athena, dangerous ×N agents on apollo.
- **Workspace / scratch accumulation.** The runbook documents a prior incident where
  37 Gi of stale `cargo-target*`/`core-target*`/recovery dirs lived in tmpfs-backed
  `/tmp` and 30 Gi of swap was consumed. Apollo's `/` currently has 51 Gi free so
  this is not the current killer, but unbounded per-workspace `cargo-targets` and
  retained logs (`tool_runs.log_max_bytes` 2 GiB aggregate, 256 MiB/run) deserve a
  periodic `sase doctor`/GC pass.

## How to confirm OOM on apollo (5 minutes, needs privs)

The single most valuable missing evidence is the kernel's verdict. On apollo:

```bash
# 1. Kernel OOM log (needs sudo or adm/systemd-journal membership):
sudo dmesg -T | grep -i -E 'out of memory|killed process|oom-kill' | tail -n 30
sudo journalctl -k | grep -i -E 'oom|killed process' | tail -n 30

# 2. Were agents exit-137 (SIGKILL) rather than clean exits?
#    Check the agent run logs / sase agent list -j for the dead agents'
#    exit codes; 137 + a matching dmesg timestamp = OOM, not a sase bug.

# 3. Memory timeline around the kill:
free -h; vmstat 5 12   # watch si/so (should stay 0 — there is no swap)
cat /proc/sys/vm/overcommit_memory /proc/sys/vm/overcommit_ratio
ulimit -a              # compare with athena's resources.ulimits deep check

# 4. Repeat the capacity math under load:
ps aux --sort=-%mem | head -n 20   # while the swarm runs
```

If `dmesg` shows `Out of memory: Killed process <pid> (<agent-runner/claude/rustc>
...)`, the diagnosis is confirmed. If instead agents exit cleanly with Python
tracebacks or provider auth/rate errors, treat this report's capacity findings as
context and pursue the logged error.

## Recommended solution

Ordered by leverage/cost. Do 1–3 now; 4–5 are the durable fixes.

### 1. Give apollo swap (highest leverage, minutes)

A swapless 31 Gi box running multi-Gi agents is simply misconfigured. Add a swap
file (example: 16–32 Gi on `/`, which has 51 Gi free) or enable zram, then verify
with `swapon --show; free -h`. This alone converts sudden mass-kills into graceful
slowdowns and matches athena's proven configuration (62 Gi RAM + 63 Gi swap). It
does not reduce peak usage — it buys time for admission control (step 2) to matter.

### 2. Keep apollo's runner cap low until swap + data exist (already partly done)

Apollo's override is already 5 vs. athena's 8 (default 10) — that was the right
instinct. Do not raise it. Consider dropping to **3–4** while running build/test
heavy swarms, via Ctrl+R in Launch Control (persistent `max_running_agents` edit) or
the override file; parked agents react within ~2 s and lowering is non-preemptive
(running agents are never killed). Revisit only after measuring peak RSS per agent
for the actual workload (step 4's accounting). Per-launch `%queue(capacity=N)` /
`weight=` can additionally serialize the known-heavy members of a swarm without
throttling the whole host.

### 3. Stop aligning peak loads on apollo (operational, immediate)

- Dispatch research swarms to athena (or split across hosts) when members will
  compile Rust or run `pytest -n 4`; use apollo for lighter read/review agents.
- Stagger heavy steps: don't start 5 members that each run `just check` /
  `cargo build --release` simultaneously. Serialize the build once and share it, or
  use `sase tool run` / monitors so heavy steps queue instead of overlapping.
- Don't run the TUI, `just check-full`, full visual suites, or CI on apollo
  concurrently with a swarm. Close idle workspaces (`sase workspace` occupancy) and
  prune stale `cargo-targets`/recovery/scratch dirs per the runbook recipe.

### 4. Make the invisible visible (short-term code/config, small)

- Add a `resources.memory` / `resources.swap` doctor check (RAM total, swap total,
  current pressure, per-host `max_running_agents` sanity) — `sase doctor` currently
  covers disk/inotify/ulimits but not the quantity that kills agents.
- Log per-agent peak RSS (runner + direct children) into the agent record at
  finalization so the next "is host X big enough for N agents?" question has data
  instead of estimates. Even a `ps`-sampled high-water mark per run would do.
- Document a per-host sizing rule next to `max_running_agents` (e.g. "budget
  ~2–3 Gi per build-capable agent; swapless hosts halve the default").

### 5. Memory-aware admission (durable fix, needs design)

Options in increasing order of machinery: (a) refuse/park launches when
`MemAvailable` is below a floor; (b) weight admission by recent peak RSS per
provider/model rather than flat 1.0; (c) run agents under cgroup memory limits with
a clean QUEUED-retry instead of SIGKILL. Any of these should be a SASE decision
record (immutable, with alternatives and reopen condition) and, per the repo's Rust
boundary rule, the shared accounting belongs in `sase-core` with Python/TUI calling
through the binding — but that is design work, not an emergency fix. Do not block
steps 1–3 on it.

## What I did not do

- I did not read any peer swarm member's report (`__cdx`/`__cld`/`__grk`/`__gem`
  for this question); only filenames were listed to pick a non-colliding stem.
  Conclusions above are my own from direct `ssh`/config/process evidence.
- I did not change any host configuration; all commands were read-only (`free`,
  `nproc`, `df`, `ps`, `sase config/agent/doctor` reads, `ssh` probes).

## Appendix: exact observations

- `ssh apollo free -h` → `Mem: 31Gi … Swap: 0B 0B 0B` (two reads, minutes apart).
- `ssh apollo nproc` → `16`. `df -h /` → `193G / 142G / 51G avail (74%)`.
- `cat ~/.sase/max_running_agents_override.json` on apollo → `limit: 5`; on athena
  → `limit: 8`. `src/sase/default_config.yml:67` → `max_running_agents: 10`.
- `ps aux --sort=-%mem` on athena (two snapshots): TUI ~3.4 Gi; runners
  0.35–1.1 Gi × ~12; pytest workers ~1.0–1.2 Gi × 4; rustc ~1.3–1.9 Gi × 2;
  `git pack-objects` ~1.1 Gi; provider CLIs (claude/codex/muse/agy) ~0.2–0.45 Gi
  each; `sase agent list`: 45 rows.
