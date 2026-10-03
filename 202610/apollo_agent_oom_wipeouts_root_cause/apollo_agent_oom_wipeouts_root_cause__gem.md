# Root Cause Analysis and Remediation: Cascading OOM Agent Teardowns on Apollo

**Author:** Researcher `gem` (Independent Investigation)  
**Host Analyzed:** `apollo` (`apollo.tail297af1.ts.net`, Linux 6.8.0-138-generic, Ubuntu 24.04 LTS, 16 CPUs, 31 GiB RAM, 0B Swap)  
**Date:** 2026-10-03  
**Status:** Completed Report  

---

## 1. Executive Summary

On host `apollo`, SASE agents have repeatedly experienced sudden, catastrophic terminations where **all running agents simultaneously die with status `FAILED` (`outcome: killed`, exit code 143 / SIGTERM)**. 

Our investigation confirms that while the root trigger is indeed memory exhaustion (an Out-Of-Memory / OOM event), the reason **all** agents die at once—along with the SASE Text User Interface (TUI)—is an architectural collision between Ubuntu 24.04's systemd tmux scoping, systemd's default `OOMPolicy=stop`, and an incomplete cgroup escape check in SASE's `detach_scope.py`.

### Key Findings
1. **The Physical Trigger (Zero Swap):** Apollo possesses 31 GiB of physical RAM but **0 bytes of swap space**. Under concurrent workloads (Rust compilations via `cargo`, `symvision` analysis, multiple LLM harness sessions, and pytest executions), anonymous heap memory spikes. With zero swap, the Linux kernel cannot page out anonymous memory and is forced to dump pagecache (dropping from ~17.5 GiB down to 2.7 GiB). When pagecache is exhausted, direct memory reclaim fails, and the kernel OOM killer is invoked.
2. **The Shared Blast Radius (Systemd Tmux Scopes):** Under Ubuntu 24.04 with systemd 255, tmux spawns every pane in a transient systemd scope named `tmux-spawn-<uuid>.scope`. By default, systemd scopes enforce `KillMode=control-group` and `OOMPolicy=stop`.
3. **The SASE Bug (`detach_scope.py`):** SASE's detached launcher (`src/sase/detach_scope.py`) was intended to isolate background agent runners into dedicated scopes via `systemd-run --user --scope`. However, it contained a restrictive guard: it only escaped if the parent process was *already* in a SASE-owned systemd unit (`sase.service` or starting with `sase-`). When the user runs `sase -p tui` from a tmux pane, the parent unit is `tmux-spawn-<uuid>.scope`. Because this does not start with `sase-`, `detach_scope()` **silently refuses to escape**. Every agent launched from the TUI remained trapped in the single `tmux-spawn-<uuid>.scope` sharing fate with the TUI and all other sibling agents.
4. **The Cascading Kill:** When any single process inside the tmux pane (such as a build or test) triggers the kernel OOM killer, systemd marks the entire `tmux-spawn-*.scope` as `Failed with result 'oom-kill'` and sends SIGTERM to the entire control group. This wipes out the TUI and every agent running under it at the exact same second.

---

## 2. Incident Anatomy & Timeline

Live diagnostic logs and metrics on `apollo` revealed multiple cascading kill incidents today (2026-10-03).

### Incident 1: 16:24:28 UTC (12:24:28 EDT)
- **Scope Involved:** `tmux-spawn-1a05ddb8-e19b-4439-9e24-e3e8a3367627.scope` (the tmux pane hosting the ACE TUI).
- **Peak Memory Consumed:** **29.0 GiB** (out of 31 GiB physical RAM).
- **Concurrently Running Agents in that Scope:**
  - `gh_bobs-org__bob-cli` workspace 10 (`bob-cli-3u.land`, model `opus` / Claude, running for ~24 min)
  - `gh_bobs-org__bob-cli` workspace 12 (`4r.f0`, model `gpt-6-astra` / Codex)
  - `gh_sase-org__sase` workspace 10 (`4s.f0`, model `gpt-6-astra` / Codex)
- **Systemd Journal Output:**
  ```text
  Oct 03 16:24:28 apollo systemd[1162]: tmux-spawn-1a05ddb8-e19b-4439-9e24-e3e8a3367627.scope: A process of this unit has been killed by the OOM killer.
  Oct 03 16:25:58 apollo systemd[1162]: tmux-spawn-1a05ddb8-e19b-4439-9e24-e3e8a3367627.scope: Stopping timed out. Killing.
  Oct 03 16:25:58 apollo systemd[1162]: tmux-spawn-1a05ddb8-e19b-4439-9e24-e3e8a3367627.scope: Failed with result 'oom-kill'.
  Oct 03 16:25:58 apollo systemd[1162]: tmux-spawn-1a05ddb8-e19b-4439-9e24-e3e8a3367627.scope: Consumed 2h 45min CPU time, 29.0G memory peak.
  ```
- **Consequence:** All three agents recorded `status: failed`, `outcome: killed` in `runs.jsonl` within an 8-second window (12:24:30 to 12:24:38), with exit code 143 (SIGTERM). The TUI process (PID 2666835) was torn down.

### Incident 2: 17:32:39 UTC (13:32:39 EDT)
- **Scope Involved:** `tmux-spawn-d263949a-07c1-42bd-b1b8-457137a334ea.scope` (the restarted tmux pane hosting the ACE TUI).
- **Concurrently Running Agents in that Scope:**
  - `gh_sase-org__sase` workspace 12 (`sase-1fs.1--1`, model `muse-spark-1.3-contributor`)
  - `gh_bobs-org__bob-cli` workspace 10 (`4r.f1.f0`, model `gpt-6-astra` / Codex)
- **Tool Execution Context:**
  - At `17:32:12 UTC`, agent `sase-1fs.1--1` launched a `Bash` tool call to execute project checks/compilations.
  - At `17:32:39 UTC`, memory pressure peaked (`psi_memory_some` rose to 0.83).
- **Systemd Journal Output:**
  ```text
  Oct 03 17:32:39 apollo systemd[1162]: tmux-spawn-d263949a-07c1-42bd-b1b8-457137a334ea.scope: A process of this unit has been killed by the OOM killer.
  Oct 03 17:33:03 apollo systemd[1162]: tmux-spawn-d263949a-07c1-42bd-b1b8-457137a334ea.scope: Failed with result 'oom-kill'.
  Oct 03 17:33:03 apollo systemd[1162]: tmux-spawn-d263949a-07c1-42bd-b1b8-457137a334ea.scope: Consumed 3h 49min CPU time, 4.3G memory peak, 0B memory swap peak.
  ```
- **Consequence:** Both `sase-1fs.1--1` and `4r.f1.f0` were instantly sent SIGTERM:
  - In `gh_sase-org__sase_ace-run-261003_132851.txt`:
    `Error running LLM provider command (exit code 143)` ... `received SIGTERM; flushed session logs`
  - In `gh_bobs-org__bob-cli_ace-run-261003_132807.txt`:
    `Received SIGTERM - agent was killed`
  - The TUI process was killed, and the user had to restart it at 17:33:16 UTC (`pid: 2985343`).

---

## 3. Host Metrics & Evidence from Apollo

### Memory & Swap Status
Checking the memory subsystem via `free -h` and `sysctl`:
```text
               total        used        free      shared  buff/cache   available
Mem:            31Gi       4.2Gi        23Gi       4.2Mi       4.6Gi        27Gi
Swap:             0B          0B          0B
```
- `vm.swappiness = 60`
- `vm.overcommit_memory = 0`
- `vm.overcommit_ratio = 50`

### Memory Pressure and Direct Reclaim (`sar`)
Inspection of historical SAR metrics (`sar -r` and `sar -B`) surrounding the two incidents demonstrates catastrophic pagecache eviction and direct reclaim:

```text
Time (UTC)   kbmemfree   kbbuffers    kbcached    pgscank/s  pgscand/s   pgsteal/s
16:20:00     4,523,580   2,751,608  17,959,972         0.00       0.00        0.00
16:30:00    24,524,140     667,832   2,726,176      9354.67    1393.00    19379.13  <-- Incident 1 (15 GB cache purged)
...
17:30:01     6,830,428   2,494,524  17,036,420         0.00       0.00        0.00
17:40:00    24,421,892     652,644   3,383,288     16091.04     936.58    25342.78  <-- Incident 2 (14 GB cache purged)
```
- `pgscand/s` represents **direct reclaim**—where user application threads are paused by the kernel to scan and discard pages because the background pageout daemon (`kswapd`) cannot free memory fast enough.
- In both windows, direct reclaim spiked (`936` to `1393` pages/sec), cache was forcefully purged by ~14–15 GiB, and the kernel OOM killer intervened.

### Cgroup Hierarchical OOM Events
Inspection of `/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/memory.events`:
```text
low 0
high 0
max 0
oom 0
oom_kill 3
oom_group_kill 0
```
- `oom 0` confirms that no individual cgroup memory limit was configured or breached (`memory.max` was set to `max`).
- `oom_kill 3` records the hierarchical propagation of the three global kernel OOM events into the user service cgroup.

---

## 4. Root Cause Analysis: The Three Intersecting Factors

### Factor 1: Lack of Swap Space (The Trigger)
On Linux, memory consists of:
1. **File-backed pages (Pagecache):** Binaries, shared libraries, cached files. These can be evicted and re-read from disk without swap.
2. **Anonymous memory:** Heaps, stacks, modified memory from Python, Rust, LLM client subprocesses. **Anonymous memory cannot be paged out without swap.**

When multiple SASE agents execute in parallel, anonymous memory grows rapidly. Because Apollo has **0B swap**, the kernel's only mechanism to satisfy memory allocation requests is to reclaim pagecache. When pagecache is depleted to a critical threshold where active executables cannot be evicted, the kernel has no choice: it invokes `out_of_memory()`.

### Factor 2: Ubuntu 24.04 Tmux Scopes & Default OOMPolicy (The Blast Radius)
On Ubuntu 24.04 (systemd 255), tmux creates each pane inside a transient scope:
```text
CGroup: /user.slice/user-1000.slice/user@1000.service
        └─tmux-spawn-<uuid>.scope
```
Querying the scope configuration on Apollo confirms:
```text
$ systemctl --user show tmux-spawn-*.scope -p OOMPolicy -p KillMode
OOMPolicy=stop
KillMode=control-group
```
- **`OOMPolicy=stop`**: When *any single process* in the unit is killed by the OOM killer, systemd considers the unit to have failed.
- **`KillMode=control-group`**: When the unit fails or stops, systemd sends `SIGTERM` (followed by `SIGKILL`) to **every remaining process in the cgroup**.

### Factor 3: SASE's `detach_scope.py` Escape Flaw (The Structural Bug)
In `src/sase/agent/launch_spawn.py`, SASE attempts to detach every launched agent:
```python
with timer.stage("detach_scope"):
    scoped_launch = detach_scope(
        prepared.argv,
        description="SASE agent runner",
        unit_prefix="sase-agent",
    )
    if scoped_launch.argv != prepared.argv:
        prepared = replace(prepared, argv=scoped_launch.argv)
```
However, in `src/sase/detach_scope.py`:
```python
parent_unit = _current_systemd_unit(proc_root=proc_root)
if not _is_sase_owned_systemd_unit(parent_unit):
    return _DetachScopeCommand(
        command,
        start_new_session=start_new_session,
        parent_unit=parent_unit,
    )
```
And:
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
When `sase -p tui` is launched inside tmux, `parent_unit` is `tmux-spawn-<uuid>.scope`.
- `_is_sase_owned_systemd_unit("tmux-spawn-....scope")` returns **`False`**!
- `detach_scope()` returns `escaped=False` without wrapping the command in `systemd-run --user --scope`.
- Consequently, every agent runner (`run_agent_runner.py`), its LLM provider processes (`muse`, `codex`, `claude`), and all tools executed by agents run **inside the TUI's `tmux-spawn-*.scope`**.

When a single memory-heavy command triggers an OOM event, systemd tears down the entire scope. The TUI and every single running agent are killed at the same moment.

---

## 5. Review of Current Remediation Work

In the codebase on Apollo, an active bead and plan already target this exact defect:
- **Plan File:** `sase/repos/plans/202610/detach_scope_user_manager_escape.md`
- **Active Workspace:** `sase_10` on Apollo is actively authoring and verifying the fix under bead `sase-1fs.1` / tale `4t`.

### The Core Software Changes in the Plan:
1. **Escape Condition Expansion:**
   Modify `detach_scope.py` so that on Linux, it escapes if `systemd-run` is available AND either:
   - The parent unit is SASE-owned (`sase.service` or `sase-*`), OR
   - The user systemd manager is reachable (`_user_manager_reachable()`, verified by checking if the cgroup contains `user@<uid>.service` or `$XDG_RUNTIME_DIR/systemd/private` exists).
   This ensures that any launch from a tmux pane (`tmux-spawn-*.scope`), SSH session, or desktop terminal is detached into a dedicated `sase-agent-<uniquifier>.scope`.
2. **`OOMPolicy=continue` on SASE Scopes:**
   When invoking `systemd-run --user --scope`, append `--property=OOMPolicy=continue` whenever systemd >= 243. This ensures that even if an agent's sub-process (e.g. a compiler or test binary) is killed by the OOM killer, systemd will **not** tear down the agent's runner or sibling processes.
3. **`OOMPolicy=continue` on `sase.service`:**
   Add `OOMPolicy=continue` to `sase.service` in `src/sase/service/platform_units.py` so the service host does not crash if a background routine child process is OOM-killed.
4. **Kill Provenance Telemetry:**
   Implement `classify_runner_kill` and OOM evidence collection (`oom_kill_delta` from cgroup `memory.events`) so external systemd kills are explicitly recorded in `done.json` as `kill_source: "external"` rather than appearing as user-initiated terminations.

---

## 6. Recommended Comprehensive Solution

To permanently resolve both the **root trigger** (running out of RAM) and the **cascading blast radius** (killing all agents at once), we recommend a three-tiered solution:

### Tier 1: Host-Level Operational Fix (Immediate Action on Apollo)

Even with proper cgroup isolation, a host with 0B swap will frequently hit the kernel OOM killer during parallel agent operations. Creating swap space provides the kernel with the necessary headroom to page out idle memory and buffer I/O bursts.

Apollo's root disk (`/dev/vda1`) has **51 GiB of available storage**. 

**Action: Provision a 16 GiB swap file on Apollo:**
```bash
# 1. Allocate a 16 GiB swap file
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 2. Make it persistent in /etc/fstab
if ! grep -q '/swapfile' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# 3. Configure sysctl to prefer RAM while allowing paging under pressure
sudo tee /etc/sysctl.d/99-sase-memory.conf << 'EOF'
# Prefer physical RAM; only page out cold anonymous memory under pressure
vm.swappiness = 15
# Maintain a healthy pagecache buffer
vm.vfs_cache_pressure = 50
EOF

sudo sysctl --system
```

*Expected Result:* Prevents sudden pagecache starvation and kernel OOM panics during concurrent agent builds and tool calls.

---

### Tier 2: Land the SASE Cgroup Isolation Architecture (Software Fix)

Ensure that the implementation currently in `sase_10` (implementing `plans/202610/detach_scope_user_manager_escape.md`) lands and is deployed to Apollo:

1. **Verify `detach_scope.py` User-Manager Escape:**
   When running under tmux, verify that `detach_scope()` returns `escaped=True` and wraps invocations in:
   ```bash
   systemd-run --user --scope --quiet --collect \
     --unit=sase-agent-<pid>-<timestamp> \
     --description="SASE agent runner" \
     --property=OOMPolicy=continue -- <command>
   ```
2. **Update Installed `sase.service` Unit:**
   After landing `OOMPolicy=continue` in `render_systemd_unit`, reload and restart the user service:
   ```bash
   sase service restart
   systemctl --user daemon-reload
   ```
3. **Verify Agent Isolation:**
   Confirm using `systemctl --user status` that active agents now appear in their own distinct `sase-agent-*.scope` branches rather than nested inside `tmux-spawn-*.scope`.

*Expected Result:* Complete blast-radius containment. If one agent or test runs wild, only that process or unit is affected. The TUI and all other agents remain running.

---

### Tier 3: Concurrency & Per-Agent Resource Governance (Preventative Guardrails)

To prevent multiple concurrent agents from starving the host's 31 GiB memory:

1. **Per-Agent Cgroup Memory Caps (Future Enhancement):**
   Once agents escape into their own `sase-agent-*.scope`, SASE can configure a soft memory limit (`MemoryHigh`) or hard limit (`MemoryMax`):
   ```text
   --property=MemoryHigh=16G --property=MemoryMax=24G
   ```
   This ensures a runaway compilation or test suite is throttled by the kernel before it consumes all physical RAM.
2. **Parallelism Governors:**
   Ensure build and test tools honor machine CPU/memory constraints:
   - For `cargo`: ensure `CARGO_BUILD_JOBS` is bounded (e.g. 8 jobs rather than 16 on a 32 GiB machine).
   - For `pytest`: avoid high `-n` concurrency when running alongside active agent models.

---

## 7. Conclusion

The killing of all SASE agents on Apollo was not a mysterious bug in the LLM models or individual scripts; it was a **systemd fate-sharing cascade** triggered by **zero swap** and an **overly restrictive cgroup escape filter** in SASE.

By provisioning a 16 GiB swap file on Apollo and landing the `detach_scope` user-manager escape with `OOMPolicy=continue`, Apollo will be fully protected against both OOM triggers and cascading agent teardowns.
