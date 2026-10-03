# Apollo OOM-kills every SASE agent in the TUI pane

_Independent research (researcher `grk`) into why the Apollo machine keeps
killing its SASE agents, believed to be OOM. Measured live on 2026-10-03 from
Athena (`sase machine status apollo` + SSH). I did not consult the other
researchers in this swarm._

**Question:** Apollo keeps killing all of its SASE agents. Is that OOM, what
exactly is being killed, and what should we change so it stops?

## Bottom line

Yes: this is the Linux OOM killer, and it is a chronic Apollo-only failure, not
a one-off. The kernel is shooting the long-lived `tmux` pane that hosts
`sase -p tui`, and because TUI-launched agent runners are **not** escaped into
their own systemd scopes they die in the same cgroup. Axe-launched agents in
separate scopes still die in the same breath because Apollo has **31 GiB RAM
and zero swap**, so a 29 GiB peak in that pane is a machine-wide OOM.

The 16:24 UTC kill today is the smoking gun:

```
tmux-spawn-1a05ddb8-….scope: A process of this unit has been killed by the OOM killer.
… Killing process 2234090 (zsh)
… Killing process 2274752 (python3)
… Killing process 2663836 (claude)
… Consumed 1d 14h 22min CPU time, 29.0G memory peak, 0B memory swap peak.
```

TUI startup log: `agent_row_count` was **46** at 16:11 UTC and **7** after the
next successful paint. Two in-flight agents (`sase-1fs.1--1`, `4r.f1.f0`)
recorded `outcome: killed` at the 17:32 UTC follow-up OOM, to the second.

**Recommended solution:** do the host-side memory floor today (zram + swapfile,
and keep `max_running_agents` at 3–4), then land three SASE changes: always
`systemd-run --user --scope` agent runners **including from the TUI**, put
`MemoryMax` on those scopes, and fix the TUI snapshot-cache heap bloat already
measured in `research:202610/tui_freeze_gc_heap_bloat`. Resizing the droplet
from 32 GiB to 64 GiB helps only after those three, otherwise the TUI will
grow into the new ceiling too.

## What I measured

Controller is Athena. Apollo is the only enrolled remote (`sase machine list`):
alias `apollo`, SSH target `apollo`, endpoint
`https://apollo.tail297af1.ts.net`, gateway 0.36.4, fleet contract v7, hello
ok. Prior research (`research:202609/apollo_upgrade_and_machine_bootstrap`)
identifies it as a DigitalOcean CPU droplet, 200 GB virtio disk.

### Host shape (SSH, 17:40–17:45 UTC)

| Fact | Apollo | Athena (for contrast) |
| --- | --- | --- |
| RAM | 32863292 kB ≈ **31.3 GiB** | 65712596 kB ≈ **62.7 GiB** |
| Swap | **0 B** (`/proc/swaps` empty, no zram, no fstab swap) | 64 GiB nvme partition, ~19 GiB in use |
| `vm.overcommit_memory` | 0 (heuristic overcommit off) | 0 |
| `systemd-oomd` | inactive, unit not-found | not checked for this note |
| `earlyoom` / `nohang` | not installed | — |
| Disk | `/dev/vda1` 193 G, **51 G free** | — |
| Uptime | 29 d 23 h (boot = 2026-09-03 18:04 UTC) | — |
| `max_running_agents` | override **5**, no expiry, source `ace` | default 10 |
| SASE | `0.17.1+2050.gad1fee548`, core `0.36.4+1.gf50782f7e` | this workspace |

User slice cgroup (`user-1000.slice` / `user@1000.service`):

- `memory.max` = `max` (no cap)
- `memory.events`: `oom_kill 3` on both the slice and `user@1000.service`
- `sase.service`: `OOMPolicy=stop` (systemd default; **not** in the unit
  file), `OOMScoreAdjust=200` (also not in the unit file — user-manager
  default), `Restart=on-failure`

PSI memory at the quiet 17:41 snapshot was near zero (`avg10=0.00`). The
machine is fine *between* kills. The kills are spikes.

### OOM timeline (user journal, last 30 days)

All of these are `tmux-spawn-*.scope` units owned by user systemd (PID 1162
after the Sep 3 boot; PID 976 before it):

| When (UTC) | What systemd logged |
| --- | --- |
| 2026-09-03 11:44 | tmux-spawn OOM |
| 2026-09-03 13:39 | tmux-spawn **plus** `dbus.service`, `gpg-agent.service`, `session.slice`, `app.slice` — machine-wide |
| 2026-09-03 14:13, 16:45, 16:58 | more tmux-spawn OOMs; 16:45 and 16:58 also hit `app.slice` / `session.slice` |
| 2026-10-01 21:15:46 | tmux-spawn OOM; 5d 17h CPU on that pane; TUI PID 2235317 starts at 21:16:10 |
| 2026-10-03 16:24:28 | tmux-spawn OOM; **29.0 G peak, 0 B swap**; SIGKILL of `zsh` + `python3` + `claude` after stop timeout |
| 2026-10-03 17:32:39 | tmux-spawn OOM; **4.3 G peak**; TUI PID 2985343 starts at 17:33:04 |

Kernel `dmesg` / `/var/log/syslog` were empty for these events from an
unprivileged SSH (`kernel.dmesg_restrict=1`). The user journal is enough: it
names the unit, the result `oom-kill`, the peak RSS, and the processes
SIGKILL'd during cleanup.

`sase.service` itself was **not** the 16:24/17:32 victim. It entered at
17:13:57 UTC (`dev_update.jsonl` also ends at 17:13 — an install restart),
`NRestarts=0`, `Result=success`. The TUI pane is what keeps dying. When the
Sep 3 13:39 event also OOM'd `session.slice` and `app.slice`, everything in
the user session died, which is the "all agents vanished" experience at its
worst.

### TUI memory, live

The TUI lives in tmux session `sase` (tmux server PID 2210, started Sep 3
18:04 UTC, the boot). Tree at 17:41 UTC:

```
tmux: server,2210
  zsh,2984398
    sase,2985343  -p tui     ← restarted 17:33:04, one minute after the last OOM
```

RSS of that fresh image, sampled over SSH:

| Elapsed | RSS | %MEM |
| --- | --- | --- |
| 10:26 | 1605 MiB | 4.8 |
| 11:10 | 1753 MiB | 5.4 |
| 12:53 | 1933 MiB | 6.0 |
| 13:48 | 1121 MiB | 3.4  (idle gen-2 GC reclaimed ~800 MiB) |
| 15:28 | 1143 MiB | 3.5 |

The containing cgroup `tmux-spawn-c5a838fd-….scope` at ~14 min of life:

- `memory.current` = 4031647744 ≈ **3.75 GiB**
- `memory.peak`    = 6273437696 ≈ **5.84 GiB**
- `memory.max`     = `max`

Process RSS is not the whole story. The pane's cgroup is already at 6 GiB
peak a quarter-hour after an OOM restart, with one muse agent running
*outside* that cgroup (axe runner PID 3000293). A 43-hour TUI (PID 2235317,
2026-10-01 21:16 → 2026-10-03 16:24) reaching a **29 GiB** cgroup peak on a
31 GiB box is the expected end of that curve.

This matches the Athena TUI-heap research
(`research:202610/tui_freeze_gc_heap_bloat`): snapshot caches keyed on
`(mtime_ns, size)` retain dozens of full artifact-index copies; RSS grew
from 1.48 GiB to 4.66 GiB in ~50 minutes **on Athena**, which has 64 GiB RAM
**and 64 GiB of swap**, so the process slows down instead of dying. Apollo
has no such cushion.

Heartbeat rows in `~/.sase/logs/tui_stalls.jsonl` on Apollo already record
`vmswap_bytes: 0` and `threshold_policy: raised`. GC is trying. It is not
enough without swap or a cgroup ceiling.

### Agents actually marked killed

`done.json` on Apollo, `outcome == "killed"`, timestamps aligned to the 17:32
UTC OOM (`finished_at` 1791048761 / 1791048765):

| Name | Project | Model | Artifact |
| --- | --- | --- | --- |
| `sase-1fs.1--1` | `gh_sase-org__sase` | muse-spark-1.3-contributor | `ace-run/202610/03/20261003132851` |
| `4r.f1.f0` | `gh_bobs-org__bob-cli` | gpt-6-astra | `ace-run/202610/03/20261003132807` |

`runs.jsonl` records both as `status: failed` with durations 228 s and 275 s.
They were short continuations, not day-long leaks of their own. They died
because the machine ran out of memory, not because those two prompts were
29 GiB.

TUI `agent_row_count` from `tui_startup.jsonl`:

- 16:11 UTC (PID 2235317, last paint before the 29 GiB kill): **44–46**
- 16:26 UTC (PID 2666835, restart after 16:24 OOM): 46, then 7 after the
  17:13 service/TUI refresh
- 17:33 UTC (PID 2985343, restart after 17:32 OOM): **8**

That is the user-visible "it killed all my agents."

### Why TUI-launched agents share the doomed cgroup

`src/sase/detach_scope.py` only wraps a child in `systemd-run --user --scope`
when the parent unit is already SASE-owned (`sase.service`, `sase-axe*.scope`,
or `sase-*.scope`/`sase-*.service`):

```python
def _is_sase_owned_systemd_unit(unit: str | None) -> bool:
    if unit is None:
        return False
    if unit == SASE_SERVICE_UNIT:
        return True
    if unit.startswith(SASE_AXE_SCOPE_PREFIX) and unit.endswith(".scope"):
        return True
    return unit.startswith("sase-") and unit.endswith((".scope", ".service"))
```

A TUI started from tmux is in `tmux-spawn-<uuid>.scope`. That name fails the
predicate, so `launch_spawn.py`'s `detach_scope(..., unit_prefix="sase-agent")`
returns the original argv. `start_new_session=True` still `setsid`s, but
**setsid does not change cgroup**. The runner and its provider CLI (`claude`,
`muse-bin`, `codex`, …) stay in the TUI pane's scope.

Consequences:

1. The pane's `memory.peak` is TUI heap **plus every TUI-launched agent
   tree**. 29 GiB is plausible as a sum even when no single process is 29 GiB.
2. When the kernel OOM-kills one process in that scope, systemd's default
   `OOMPolicy` for the scope fails the unit and SIGKILLs the rest (the 16:24
   log: first OOM at 16:24:28, then "Stopping timed out. Killing" at 16:25:58
   of zsh, python3, and claude together).
3. Axe-launched work *does* escape: the journal is full of
   `sase-checks-<pid>-<ns>.scope` and the live muse agent at 17:41 was a
   sibling `run_agent_runner.py`, not a TUI child. Those still die under
   *global* OOM because nothing on the box has `MemoryMax` and there is no
   swap.

The unit prefix `sase-agent` is sitting in `launch_spawn.py` unused for the
exact launches the user watches in the TUI.

`sase.service`'s `OOMPolicy=stop` is a second foot-gun for the *service*
tree: if the kernel ever picks an axe routine inside `app.slice`/`sase.service`
(OOMScoreAdjust=200 makes that *more* likely than the TUI's adj=0), systemd
stops the whole service host, scheduler, gateway, and every axe lane, then
`Restart=on-failure` brings an empty control plane back 5 s later. That is
not today's 16:24/17:32 path, but it is how a future OOM becomes "the
machine forgot how to run agents."

### Contributing load, not the root cause

- **Concurrency cap is already 5** (`~/.sase/max_running_agents_override.json`).
  Five provider CLIs plus a multi-GiB TUI plus `just check` workers is still
  enough to fill 31 GiB.
- **Axe** uses the packaged `max_agent_runners: 3` / `max_hook_runners: 3`.
  Nine `sase axe routine run …` processes were alive, each ~60–80 MiB. Noise,
  not the 29 GiB.
- **`just check` / pytest-xdist** on this repo can request large worker
  pools (`Justfile` visual-contention comments talk about a 26-worker pool).
  A lander that runs `just check` or `just check-full` inside a TUI-launched
  agent is a realistic way to *add* another 10–20 GiB in seconds. I did not
  catch a live pytest-xdist on Apollo during this window.
- **Detach-scope OOM tests today.** User journal between 16:31 and 17:22 UTC
  shows `sase-oomtest-*.scope` and several `sase-detach-oom-test-*.scope`
  ("SASE detach-scope OOMPolicy regression"). Those sit on the same 31 GiB
  with no swap and can have pushed the 17:32 event. They do **not** explain
  Sep 3, Oct 1, or the 16:24 29 GiB kill.
- **Workspace disk** (`~/.local/state/sase` = 43 G, 21 `sase_*` clones) is a
  disk number. It is not RSS.

## Causal chain

```
Apollo = 32 GiB DO CPU droplet, no swap, overcommit=0, no systemd-oomd
    │
    ├─ TUI in a 29-day tmux pane, snapshot-cache heap growth (known)
    │     cgroup peak 5.8 GiB at 14 min of life today; 29 GiB at 43 h on Oct 3
    │
    ├─ TUI-launched agents stay in tmux-spawn-*.scope
    │     detach_scope() refuses to systemd-run unless parent is already sase-*
    │
    └─ First allocation that can't be reclaimed
          kernel OOM killer (no oomd to pick a leaf)
          systemd fails the tmux-spawn scope
          SIGKILL zsh + TUI + every provider still in that cgroup
          global pressure also SIGKILLs axe-scoped agents
          TUI restarts; agent_row_count collapses
```

Athena survives the same TUI bug because it has twice the RAM and a 64 GiB
swap partition. Apollo has neither.

## Alternatives considered

1. **Only raise `max_running_agents` down to 1.** The 43-hour TUI alone
   reached 29 GiB. A cap of 1 still OOMs; it just takes longer.
2. **Only resize the droplet to c-32 (64 GiB).** Previous Apollo research
   already notes DigitalOcean will do that in place. Without swap and without
   cgroup ceilings the TUI will grow into 64 GiB the same way it grew into
   32 GiB. Do the resize *after* the isolation and swap floor, or in parallel,
   not instead.
3. **Only restart the TUI on a timer.** Cheap mitigation, already happening
   involuntarily via OOM. A 4 GiB RSS watchdog is a good bandage, not a fix.
4. **Enable `systemd-oomd` alone.** Better than the kernel killer (it prefers
   the largest leaf under memory pressure), but with `memory.max=max` and no
   swap it still has to kill *someone*, and today's someone is the TUI pane
   that owns the agents.
5. **Set `OOMScoreAdjust=-500` on the TUI** so agents die first. Protects the
   pane, sacrifices work, does not prevent the 29 GiB allocation. Use as a
   preference *inside* cgroup limits, not as the only knob.

## Recommended solution

Do these in order. 1–3 are host changes on Apollo (root for swap/zram and
oomd; the rest is user systemd). 4–7 are SASE code. 8 is optional capacity.

### 1. Give Apollo a memory floor today (ops, ~15 min, reversible)

The disk has 51 GiB free; `zramctl`, `mkswap`, and `swapon` are already
installed.

- **zram 8 GiB** (compressed RAM swap, cheap, no disk wear):
  `zramctl --find --size 8G --algorithm zstd && mkswap /dev/zramN && swapon /dev/zramN`
  Persist with `zram-tools` or a systemd unit. This is the highest-leverage
  single change: Athena's TUI already pages rather than dying.
- **swapfile 16 GiB** on `/` as the second tier (`dd`/`fallocate`, `mkswap`,
  `swapon`, fstab). Keep swappiness modest (20–40) so zram is used first.
- Confirm with `swapon --show` and `free -h`. No droplet resize, no reboot
  required for the swapfile.

Until this lands, every 29 GiB spike is a hard kill.

### 2. Stop the TUI from being the OOM target (ops, same day)

- Restart `sase -p tui` when RSS exceeds ~4 GiB, or daily, until the heap
  fix ships. The image already emits `tui_memory_heartbeat` with `rss_bytes`.
- Keep the ACE runner-capacity override at **3 or 4** on Apollo (currently 5).
  Lowering it does not fix the TUI, but it cuts concurrent provider CLIs.
- Do not run `just check-full` or a 26-worker visual lane on Apollo while
  the TUI is up. Dispatch heavy verify to Athena, or wrap it in
  `sase tool run` on a host that has swap.
- Set a user drop-in for `sase.service`:

  ```ini
  [Service]
  OOMPolicy=continue
  OOMScoreAdjust=100
  ```

  `continue` means one OOM-killed child does not take down axe, gateway, and
  the scheduler. Leave the TUI at `OOMScoreAdjust=0` or negative so the
  control plane dies after agents, not before.

### 3. Prefer leaf kills over session kills (ops)

Install and enable `systemd-oomd` (or `earlyoom` if oomd stays unpackaged).
With swap present, oomd can kill a single `sase-agent-*.scope` under memory
pressure instead of waiting for the kernel to pick the TUI pane and then
having systemd SIGKILL the rest of `tmux-spawn`.

Optional but strong: a user-slice `MemoryHigh=24G` / `MemoryMax=28G` so
Apollo's 31 GiB never goes through the kernel OOM path at all. Reclaim
starts at 24 GiB; the cap is below the 29 GiB peak we already observed.

### 4. Always scope agent runners, including from the TUI (code, this is the SASE bug)

Change `detach_scope()` so the question is not "am I inside `sase.service`?"
but "is this child already in its own `sase-agent-*.scope`?"

- Call `systemd-run --user --scope --collect` for every agent runner whose
  parent is `tmux-spawn-*.scope`, `session-*.scope`, `app.slice`, or
  `sase.service`.
- Keep escaping from `sase.service` (current behavior) so `OOMPolicy=stop`
  cannot fold the control plane.
- Pass at least:

  ```
  --property=MemoryMax=6G
  --property=MemoryHigh=4G
  --property=OOMPolicy=kill
  --property=OOMScoreAdjust=300
  ```

  One runaway `claude` then hits a 6 GiB ceiling and dies alone. The TUI
  pane survives. Tune the bytes in `sase_apollo.yml` — 6 GiB × 4 running
  agents = 24 GiB, which fits a 32 GiB box with zram.

`launch_spawn.py` already passes `unit_prefix="sase-agent"`. The wrap is
what is skipped. Tests in `tests/test_detach_scope.py` should cover a fake
parent unit of `tmux-spawn-….scope` and assert `systemd-run` is on argv.

The `sase-detach-oom-test-*` scopes in today's journal show this exact
regression is already being poked. Land it against the TUI parent, not only
against `sase.service`.

### 5. Fix the TUI heap bloat (code, already researched)

Do not rediscover this. `research:202610/tui_freeze_gc_heap_bloat` measured
the snapshot-cache keying bug (mtime/size keys, cap-by-count not
cap-by-identity, ~40 MiB per extra artifact-index copy). On Athena that is
a freeze. On Apollo it is an OOM. Shipping that fix is the only way the TUI
stops *needing* a 4 GiB babysitter.

Until it ships, the heartbeat log on Apollo is enough to drive a restart
policy (step 2).

### 6. Tell the user it was OOM (code, small)

`done.json` already has `outcome: "killed"`. It does not say why. When the
runner's cgroup `memory.events.oom_kill` increments, or the process dies
SIGKILL while the unit result is `oom-kill`, record `outcome: "oom_killed"`
(or a reason field) and toast it. Right now the TUI just empties.

`docs/tool.md` currently says "OOM kills are not observable from the
ledger." That is true of `sase tool stats`. It is false of systemd user
journals and cgroup `memory.events`. Wire one of those.

### 7. Do not default `OOMPolicy=stop` for the service host (code, one line)

`src/sase/service/platform_units.py` `render_systemd_unit()` emits no
`OOMPolicy`. systemd then defaults to `stop`. Add `OOMPolicy=continue` (and
an explicit `OOMScoreAdjust`) to the rendered unit so every machine, not
just Apollo, keeps axe/gateway up when a child is killed.

### 8. Optional capacity: in-place resize to 64 GiB

DigitalOcean will resize this droplet CPU+RAM in place (see
`research:202609/apollo_upgrade_and_machine_bootstrap`, c-16 → c-32, disk
stays 200 GB). Do it **after** steps 1 and 4, or with them. 64 GiB + zram +
per-agent `MemoryMax` is a comfortable second dev box. 64 GiB with the TUI
still uncapped and agents still in `tmux-spawn` repeats this incident at a
higher watermark.

## What I did not verify

- Kernel OOM victim comm/pid from `dmesg` (needs root;
  `kernel.dmesg_restrict=1`). systemd's 29.0 G peak and the SIGKILL list are
  sufficient.
- Whether the 29 GiB peak is mostly anonymous TUI heap, mostly `claude`, or
  file cache. Cgroup peak includes reclaimable file pages; even if a third
  was cache, 20 GiB anon on a 31 GiB no-swap host still OOMs.
- A full procfs capture *during* a 29 GiB spike — by the time SSH landed,
  the pane was already dead and the box was at 3.7 GiB used.
- Exact origin of `OOMScoreAdjust=200` on `sase.service` (not in the unit
  file, not written by sase Python). Treated as the user-manager default.

## Sources

Live, 2026-10-03, Apollo unless noted:

- `sase machine list|status|show apollo`
- SSH: `free`, `/proc/meminfo`, `/proc/pressure/memory`, `/proc/swaps`,
  `lsblk`, `df`, `ps`, `pstree`, `/proc/<tui>/smaps_rollup`,
  `/sys/fs/cgroup/user.slice/user-1000.slice/**/memory.*`
- `journalctl --user` 2026-09-01 → now, `oom-kill` / `OOM killer`
- `~/.sase/logs/tui_startup.jsonl`, `tui_stalls.jsonl`, `runs.jsonl`
- `~/.sase/max_running_agents_override.json`
- `~/.config/systemd/user/sase.service`, `~/.config/sase/sase_apollo.yml`
- `done.json` for `20261003132851` and `20261003132807`
- Code: `src/sase/detach_scope.py`, `src/sase/agent/launch_spawn.py`,
  `src/sase/service/platform_units.py`
- Prior research: `research:202610/tui_freeze_gc_heap_bloat`,
  `research:202609/apollo_upgrade_and_machine_bootstrap`
