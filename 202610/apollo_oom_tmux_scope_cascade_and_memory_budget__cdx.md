# Apollo's SASE agent OOM failures: shared tmux scopes amplify memory exhaustion

Researcher: **cdx**, independently investigating the five-researcher swarm request.
Evidence collected: **2026-10-03, approximately 17:38–17:45 UTC** (13:38–13:45 EDT).
Scope: live, nonprivileged SSH diagnostics on apollo; SASE source and installed-package inspection; chezmoi configuration; authoritative Linux and systemd documentation. No peer reports, peer chat transcripts, or peer summaries were consulted. No service restarts, configuration changes, swap changes, deliberate OOM workloads, or agent terminations were performed.

**Finding:** OOM failures are real. The strongest explanation for “all agents die” is a **systemd shutdown cascade inside a shared tmux pane cgroup**. Apollo's user manager defaults to `OOMPolicy=stop`. Agents launched from the TUI inherit its `tmux-spawn-*.scope`, because SASE's current detach helper only escapes scopes whose names begin with `sase-`. A single kernel-selected OOM victim can therefore cause systemd to terminate the other agents and the TUI in that pane. Memory exhaustion and the scope-wide response are separate problems; both should be addressed.

The exact process that triggered or was selected during each OOM remains unverified: the normal SSH account cannot read the kernel journal or `dmesg`. Available evidence supports host-wide pressure, but does not prove a particular provider has a leak.

## 1. What the machine actually shows

All machine observations below came directly from apollo, rather than from the machine running this researcher.

| Observation | Measured value | Implication |
| --- | --- | --- |
| OS | Ubuntu 24.04.3 LTS | Linux systemd/cgroup behavior applies. |
| systemd | `255.4-1ubuntu8.17` | Scope `OOMPolicy` is supported. |
| CPUs | 16 logical CPUs | Unrestricted compiler parallelism can be substantial. |
| Usable RAM | `/proc/meminfo`: `MemTotal: 32863292 kB`, approximately 31.34 GiB | Nominally a 32 GiB host, not a tiny rendezvous VM. |
| Swap | `free -h`: 0 B; `swapon --show`: empty | No swap buffer for anonymous-memory spikes. |
| Root filesystem | 193 GiB total, approximately 50 GiB available | Disk capacity would allow a modest swapfile, subject to filesystem checks. |
| Kernel OOM count | `/proc/vmstat`: `oom_kill 3` | The kernel has actually performed OOM kills during this boot. |
| User cgroup counters | `oom_kill 3`, `oom_group_kill 0`, `oom 0`, `max 0` | Three primary OOM victims; no recorded kernel group OOM in this hierarchy. |
| User slice historical peak | 32,806,154,240 bytes, approximately 30.55 GiB | Bryan's processes and their charged memory have approached almost the whole host's capacity. |
| User manager historical peak | 32,729,047,040 bytes, approximately 30.48 GiB | Most of that peak was under the user manager. |
| User-manager default | `DefaultOOMPolicy=stop` | One OOM victim can trigger a unit shutdown. |
| Current TUI scope | `OOMPolicy=stop`, `KillMode=control-group` | Remaining processes in the pane can be stopped together. |
| Limits on `user.slice`, `user-1000.slice`, `user@1000.service` | `memory.max=max`, `memory.high=max` | No current parent memory cap or throttling threshold at these levels. |
| Current TUI scope limits | `MemoryMax=infinity`, `MemoryHigh=infinity` | No current pane memory ceiling. |
| SASE service limits/policy | `MemoryMax=infinity`, `MemoryHigh=infinity`, `OOMPolicy=stop`, `KillMode=mixed` | The service has a similar potential shutdown response, but it was not the failed unit in the observed incidents. |
| Userspace OOM daemons | `systemd-oomd.service` absent; `earlyoom` inactive | Disabling systemd-oomd is not a useful fix for this observed setup. |

At the initial inspection, apollo had approximately 28 GiB available and memory PSI `some avg10=0.00`. Free memory after a kill does not describe the pre-kill state. A later sample had only approximately 3 GiB literally free but approximately 27.6 GiB **available**, mostly because reclaimable filesystem cache had grown; that is not by itself memory exhaustion.

Cgroup peaks include descendants and charged cache, and are lifetime maxima, not time-aligned RSS samples. The counters and peak strongly support actual pressure, but cannot independently identify the culprit. The kernel documentation explains the distinction between `oom`, `oom_kill`, group events, and the memory interfaces. [Linux cgroup v2 memory interfaces](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files).

## 2. The shutdown cascade is visible in the journal

The user journal was readable even though the system/kernel journal was not. It identifies three affected tmux scopes during the current boot:

| First OOM message, UTC | Failed unit | Subsequent evidence |
| --- | --- | --- |
| 2026-10-01 21:15:46 | `tmux-spawn-a291e399-ade7-4fe8-b893-7e5080702b60.scope` | Unit failed as `oom-kill` at 21:16:09. |
| 2026-10-03 16:24:28 | `tmux-spawn-1a05ddb8-e19b-4439-9e24-e3e8a3367627.scope` | Stop timeout at 16:25:58; systemd explicitly SIGKILLed `zsh`, `python3`, and `claude`; unit reported a **29.0 GiB peak**, zero swap. |
| 2026-10-03 17:32:39 | `tmux-spawn-d263949a-07c1-42bd-b1b8-457137a334ea.scope` | Unit failed as `oom-kill` at 17:33:03; reported **4.3 GiB peak**, zero swap. |

The second incident provides the clearest causal evidence:

```text
16:24:28 ... A process of this unit has been killed by the OOM killer.
16:25:58 ... Stopping timed out. Killing.
16:25:58 ... Killing process 2234090 (zsh) with signal SIGKILL.
16:25:58 ... Killing process 2274752 (python3) with signal SIGKILL.
16:25:58 ... Killing process 2663836 (claude) with signal SIGKILL.
16:25:58 ... Failed with result 'oom-kill'.
16:25:58 ... 29.0G memory peak, 0B memory swap peak.
```

Thus some agent deaths were **systemd's follow-on cleanup**, not necessarily separate kernel OOM selections. Three kernel OOM victims can explain many more dead processes. The journal only proves the affected scopes; it does not prove literally every SASE agent on the host died.

This matches the documented `OOMPolicy=stop` behavior. `continue` leaves other processes in the unit running after an OOM victim; `stop` shuts down the remaining unit; `kill` additionally asks the kernel to treat the unit as a group. The observed `memory.oom.group=0` does not protect against systemd's `stop` response. [systemd's scope manual](https://manpages.debian.org/unstable/systemd/systemd.scope.5.en.html#OOMPolicy=).

## 3. Why SASE agents share the pane's fate

The primary source checkout inspected was SASE commit `598928da70fd37ef9b9ed1265fc50ed4018fbc0d`. I also inspected the installed Python package on apollo, version `0.17.1`, and confirmed the relevant helper matches this behavior.

Relevant source locations:

- `src/sase/agent/launch_spawn.py:346`: agent launch calls `detach_scope(..., unit_prefix="sase-agent")`.
- `src/sase/detach_scope.py:59`: the helper checks the current systemd unit, then returns the original command when that unit is not considered SASE-owned.
- `src/sase/detach_scope.py:125`: ownership includes `sase.service` and names beginning `sase-`; it excludes `tmux-spawn-*.scope` and ordinary login/terminal scopes.
- `src/sase/detach_scope.py:75`: the actual `systemd-run --user --scope` command does not explicitly select `OOMPolicy`.
- `src/sase/service/platform_units.py:36`: generated Linux service units also omit `OOMPolicy`, so inherit the manager default.

Live process membership corroborated the source:

```text
TUI:             PID 2985343, approximately 1.5–1.7 GiB RSS
agent runner:    PID 3000293, approximately 222 MiB RSS
provider client: PID 3004812, approximately 235 MiB RSS (muse)

All three:
/user.slice/user-1000.slice/user@1000.service/
  tmux-spawn-c5a838fd-5a0f-4113-97b9-9f5f7f9f8a5a.scope
```

The runner was already reparented to PID 1. That is useful evidence that process detachment does not imply cgroup isolation. `setsid`/`start_new_session=True` creates a Unix session/process group; it does not move a child into a separate memory/OOM unit.

The TUI's inspected environment had no `SASE_DETACH_SCOPE_DISABLE` or legacy disable variable. The guard's narrow unit-name check alone explains the missing escape; there is no need to hypothesize a disabled feature.

The active `sase.service` is in a different cgroup, had zero automatic restarts since its 17:13:57 UTC start, and was running after the 17:32 incident. Its approximately 1.8 GiB recorded peak is far below the failed 29 GiB pane. Restarting this service alone would neither isolate TUI-launched agents nor repair the shared tmux scope.

## 4. What could be consuming the memory

**Confirmed:** the agent capacity budget on apollo is `max_running_agents: 10`; AXE's separate `max_hook_runners` and `max_agent_runners` are both 3. The chezmoi apollo overlay has no machine-specific reduction. Inspected chezmoi revision: `855a98ef6aa35df2dd10bff6563f7a697952da9a`, file `home/dot_config/sase/sase_apollo.yml`.

These are runner/count budgets, not measured memory reservations. Workflow Python/bash steps and AXE runners are outside the ordinary agent budget. Explicit per-launch `%queue(capacity=N)` can replace the global admission budget. Lowering the global setting is non-preemptive and cannot alone guarantee a physical-memory limit. Source: `docs/configuration.md`, section `max_running_agents`.

**Confirmed:** recorded heavy commands can use approximately 6 GiB each. I queried the native ToolRun ledger through `sase tool runs` and `sase tool show`, extracting resource/timing metadata rather than agent transcripts.

| ToolRun ID | Start UTC, Oct 3 | Largest process RSS | Sampled process-tree peak | Time before first recorded stage |
| --- | --- | --- | --- | --- |
| `2f455bf567187bf779dc6a9cebc6c7e3` | 13:04:45 | 5.98 GiB | 6.18 GiB | approximately 22 minutes |
| `13e2561c8304a4d487ee843740921e8c` | 16:50:03 | 6.02 GiB | 6.08 GiB | approximately 24 minutes |
| `d888223364119e8f9ff04c0a6e7e07b7` | 17:25:45 | 2.07 GiB | 3.28 GiB | approximately 4 seconds |

These were `check` runs. The first two reached lint stages and failed before running pytest, so their 6 GiB peaks cannot fairly be blamed on xdist workers. Large preparation costs matter: `Justfile` `_setup` may rebuild the Rust binding before the first recorded stage, and `launch_spawn.py` gives each launch its own Cargo target/build directories. Apollo also has incremental compilation disabled by default. Repeated cold builds are a **plausible** source of memory and CPU demand. The ledger does not attach the maximum to an executable or a specific preparation substep; these data do **not** prove rustc was the original OOM victim.

The sampled memory PSI maxima for these three runs were only 1.08%, 0.30%, and 0.83%. The 17:25 check settled at 17:32:08 UTC, **31 seconds before** the 17:32:39 OOM message. None of these selected runs directly records the decisive OOM interval. Their value is demonstrating demand magnitude, not proving temporal causation.

**Inference:** several simultaneous 6 GiB tool trees plus provider clients, TUI, scheduler, and other processes can exceed 31.34 GiB even while staying within ten agent slots. Four such tool trees consume approximately 24 GiB before those other consumers. A host with no swap has little room to absorb a coincident spike.

**Possible, unproven:** TUI memory growth or a provider-specific leak. The current TUI had a 1.86 GiB high-water mark; short observations fluctuated rather than showing a monotonic rise. This is worth profiling but is insufficient to name a leak. A 29 GiB pane peak is an aggregate, not proof the TUI itself occupied 29 GiB.

The pytest pool already has memory-aware sizing: `tests/_suite_gate_budget.py:96` takes the minimum of CPU and memory budgets, reserving 8 GiB and estimating 700 MiB per worker. On an otherwise idle 16-CPU apollo, the CPU side permits 14 tokens, with a default fair-share ceiling of 7 per run. That pool does not reserve memory for independent compiler/linter processes, and the 700 MiB figure is an estimate, not a hard per-worker cap. Fixing this incident requires attention beyond pytest parallelism.

## 5. The remaining diagnostic gap

`journalctl -k` reported that the account cannot see system messages, and `dmesg` failed with “Operation not permitted.” `/var/log/kern.log` and `/var/log/syslog` are readable only by root/adm. No privilege escalation was attempted.

Use the reviewed `sase sudo request` workflow for one bounded, read-only kernel-log collection. The important command argv is:

```json
[
  "/usr/bin/journalctl", "--kernel", "--no-pager",
  "--since", "2026-10-01 20:45:00 UTC",
  "--until", "2026-10-03 17:35:00 UTC",
  "--grep", "invoked oom-killer|oom-kill|Out of memory|Killed process"
]
```

The request should target `machine: "apollo"`, use `output_to_agent: "full"` for these bounded ordinary diagnostics, and explain why the normal account is insufficient. Preserve the OOM's invoking task, selected victim, `constraint`, `task_memcg`, RSS breakdown, and any cgroup limit. The invoking task, biggest consumer, and selected victim may be different processes.

Expected discriminators: global `CONSTRAINT_NONE` versus `CONSTRAINT_MEMCG`, and victim names such as rustc, mypy, provider clients, or the TUI. If the original failed scopes had a limit that is no longer present, kernel evidence can correct the current inference of global exhaustion. Current unlimited ancestors, global `oom_kill=3`, and zero cgroup-limit events make global pressure the leading explanation.

During the next normal workload, collect low-overhead process RSS/cgroup membership, `MemAvailable`, PSI, and `memory.events` deltas. Add per-agent and per-heavy-tool process-tree demand where available. Keep a short rolling window at 2–5 second intervals so an exited process is not absent from the only snapshot. Do not dump full process environments, prompts, credentials, or provider transcripts.

## 6. Proposed fixes and how to validate them

1. **Isolate detached work from the TUI's scope.** Extend the launch boundary to escape tmux/login/terminal scopes when a user systemd manager is available, not just SASE-named scopes. Each agent/monitor/proc that must survive its launcher needs its own scope. Explicitly pass `--property=OOMPolicy=continue` on SASE-created scopes and set `[Service] OOMPolicy=continue` for the service host. Preserve test-disable guards, Darwin behavior, and clearly report unsupported-systemd/fallback cases. Code in existing subprocess/platform adapters can remain thin Python glue; shared resource-admission policy belongs in the Rust core.

   Setting the policy only on newly created SASE scopes is insufficient until tmux-launched agents actually enter those scopes. Conversely, moving agents into scopes without choosing the policy leaves each agent vulnerable to its own tool child causing a unit shutdown. The agent supervisor still needs to detect and report a killed child; `continue` does not make an OOM successful.

2. **Provide a scoped immediate workaround for the TUI.** Launch a replacement TUI in an explicitly configured scope:

   ```bash
   systemd-run --user --scope --quiet --collect \
     --property=OOMPolicy=continue \
     /home/bryan/.local/share/uv/tools/sase/bin/sase -p tui
   ```

   This stops the automatic whole-pane cleanup response for that new scope, but does not protect the TUI or any agent from being selected by the kernel. It also does not retroactively move existing agent processes. Arrange it when current work can be drained; do not kill the tmux server or restart all running agents as a diagnostic step.

3. **Reduce apollo's workload budget while collecting evidence.** Start with the machine-specific overlay below, then verify the merged effective settings and any active temporary override:

   ```yaml
   max_running_agents: 3
   axe:
     max_hook_runners: 1
     max_agent_runners: 1
   ```

   Serialize memory-heavy verification/builds initially, even when three light agents can remain active. Avoid per-launch capacity overrides that defeat the host limit. A count of three is a conservative initial operating choice, not a measured safe universal maximum.

   For every relevant launch path, start with `CARGO_BUILD_JOBS=2`; for pytest, use a shared six-token pool, floor two, and ceiling three (`SASE_TEST_GATE_SLOTS=6`, `SASE_PYTEST_WORKER_FLOOR=2`, `SASE_PYTEST_WORKER_CEILING=3`). These are tuning starting points. Export them consistently to TUI launches, scheduler launches, and tool commands; setting them in one unrelated SSH shell is insufficient. Use the existing token pool rather than disabling accounting. Cargo documents that `CARGO_BUILD_JOBS` bounds concurrent compiler processes, with explicit `--jobs` taking precedence. [Cargo build.jobs](https://doc.rust-lang.org/cargo/reference/config.html#buildjobs).

4. **Add an 8 GiB swap buffer after reviewing storage details.** Use the privileged SASE gate to create, permission, initialize, enable, and persist a swapfile only after checking filesystem suitability and existing `/etc/fstab`. Approximately 50 GiB free makes 8 GiB plausible. Verify active swap after the change and after reboot. Swap buys time for transient anonymous-memory spikes; it does not establish a sustainable workload budget. If pressure stays high or latency becomes unacceptable, move heavy work to athena or resize apollo.

5. **Add real containment and memory admission after isolation.** A sensible candidate is a dedicated workload slice with a throttling threshold around 22 GiB and a hard limit around 26 GiB, leaving host/control-plane reserve. Treat those values as hypotheses to validate, not final production limits. Keep the TUI/control plane outside the bounded heavy-work subtree and give independently recoverable work separate units. Budget all projects, hooks, monitors, builds, and tests that share the machine. A per-tool RSS peak is a better demand input than one unweighted agent slot.

   `MemoryHigh` throttles/reclaims; `MemoryMax` is an emergency hard boundary that can cause local OOM kills. Applying a common hard limit to today's shared TUI pane would reproduce the broad failure inside a smaller limit. [systemd resource controls](https://www.man7.org/linux/man-pages/man5/systemd.resource-control.5.html).

Acceptance checks should verify behavior, not merely configuration text:

- A TUI-launched agent's `/proc/PID/cgroup` differs from the tmux pane's; two agents have distinct scopes.
- `systemctl --user show <scope> -p OOMPolicy` returns `continue` for created scopes; the generated service policy survives re-initialization.
- A controlled regression test in a **small disposable cgroup** kills one allocation-heavy child while a sentinel/sibling agent and its launcher survive. Exercise tmux-parent launches and service-parent launches; do not stress the host to test this.
- The SASE owner reports the failed child accurately, settles or recovers it, and does not leak runner/workspace claims or leave an endlessly running zombie agent.
- A representative heavy workload stays below the chosen reserve, no global OOM counter increments, and all launch paths honor the effective agent/tool budgets. Check PSI and swap activity as well as available RAM.

## Recommended solution

**Prioritize cgroup isolation and explicit `OOMPolicy=continue`, then lower apollo to three ordinary agents with one heavy build/check at a time and add 8 GiB of swap.** The shutdown cascade is directly evidenced and has a concrete source-level explanation, so it can be fixed without guessing which provider leaks. Obtain the bounded kernel log to identify the actual OOM victim and pressure constraint, then use measured process-tree demand to tune limits or justify a larger VM. Longer term, enforce a host-wide memory budget for heavy tools in the Rust core and keep each recoverable job separate from the TUI and service control plane. Increasing RAM alone would leave the same “one victim takes the pane down” defect in place.
