# Dynamic Tool Capacity and the Agents Load UX

**Research date:** 2026-09-11

**Decision sought:** whether and how SASE should add temporary, command-scoped capacity claims; require explicit machine capacity during initialization; and redesign the Agents-tab capacity display.

## Executive decision

Proceed, with one important change to the proposed mental model: **do not rewrite an agent's base `queue_weight` while a command runs.** Add a crash-safe, command-scoped **tool lease** that temporarily raises the capacity claim of the agent's existing claim lineage. The lineage's effective claim becomes the maximum of its base claim and its active tool target. When the command exits, the lease disappears and the claim naturally falls back to its base weight.

This direction is materially better than today's static launch weights. A research agent or epic lander is usually lightweight and only occasionally invokes a costly compiler or test suite; charging it 0.25 or 2.0 for its entire life is a poor proxy for the burst that matters. Command-scoped admission places the charge at the point of actual demand, while retaining the useful default of one capacity unit per live agent.

The recommended first interface is:

```text
sase tool EXTRA -- COMMAND [ARG ...]
sase tool -q EXTRA -- COMMAND [ARG ...]   # queue
sase tool -f EXTRA -- COMMAND [ARG ...]   # force
```

`EXTRA` is the additional capacity, so on a base-one agent `sase tool 15 -- just check-full` produces a total claim of 16. `--` should be required. A normal attempt is deliberately non-blocking; when it cannot fit, it returns a distinct temporary-failure status and prints the exact queue and force retries. This works for both humans and agents without an interactive stdin prompt.

For the first policy set, use these targets on athena: `install` up to 8 total, `fmt` 2, `lint` 4, `test` 16, `test-cov` 16, and `check-full` 16. `check` should determine its target from the existing test-selection plan: 2 for a serial scoped run, 4 for middle gear, and 16 when it will escalate to the full suite. On apollo and the Mac, full-suite targets should follow the current pytest controller rather than copying `+15`: 4 total under its present defaults. These are initial reservations, not timeless truths; record requested/granted capacity and duration so they can be tuned from evidence.

In the Agents tab, remove the current left-side capacity prefix and replace the top-right fleet sentence with one local, glanceable meter:

```text
load  ▰▰▱▱▱▱▱▱  8/32
```

Use exact-looking numbers (`8/32`, `6.75/32`), quiet color below 75%, amber from 75% to below capacity, and red at or above capacity. Keep remote-machine diagnostics in the Machines view rather than mixing them into the local load indicator.

Finally, `sase init` should require a valid positive machine capacity in the selected machine overlay, just as it requires owner identity. Configure the actual overlays as athena `32`, apollo `8`, and `kellys_mbp` (the current Mac overlay name) `4`; do not hard-code those host names or values in SASE itself.

## 1. What exists now

The `sase-z4` epic changed admission from a count of agents to a weighted capacity projection. A normal agent defaults to weight 1, records are grouped by claim lineage, and the effective occupancy of a serial lineage is its maximum live weight rather than the sum of every shell in that lineage.[^1] That is the right base model: it avoids double-charging a parent, a continuation, and related control shells.

The current implementation has four details that shape the next change:

1. `max_running_agents` is still the configuration key and has a packaged integer default of 10. Missing or malformed configuration falls back to that default. The name is historical, but its current meaning is a host-wide capacity budget.[^2]
2. The Agents tab shows capacity in the left summary strip, with at least one decimal place, while the top-right header shows a long fleet sentence such as `here: athena · 7 active · 1 machine · apollo unknown`.[^3]
3. Rust owns capacity projection and candidate admission. It rejects an explicit weight change for an already-active lineage as an `active-claim-weight-conflict`.[^4]
4. The repository already has a second host-wide resource controller for pytest. It derives a token budget from CPU and available memory, reserves roughly 700 MiB per worker, and normally gives a parallel run half of the host pool, bounded by a floor of 4 and ceiling of 28.[^5]

There are also two static policies that the proposed feature should make unnecessary: the research swarm stamps `w=0.25`, while the default epic lander stamps `w=2.0`.[^6]

Athena has 32 physical cores, 64 hardware threads, and about 64 GiB of RAM. A capacity of 32 therefore has a useful operational interpretation: one unit is approximately one physical-core-equivalent of admitted parallel work, while memory remains an important secondary constraint.[^7]

## 2. Is the idea worth pursuing?

### The case for it

Yes. Static agent weights and command demand answer different questions:

- A base agent claim estimates the ongoing cost of keeping a provider, context, and ordinary shell work alive.
- A tool claim estimates the temporary parallel demand of a compiler, formatter, type checker, or test runner.

Conflating them makes both estimates worse. A long-lived researcher at 0.25 can still launch a 16-worker test suite; a lander at 2 can spend most of its life reading or waiting. Charging the expensive phase when it begins improves utilization and makes the displayed load more truthful.

The pattern is well established. GNU make's jobserver gives every launched command one implicit slot, lets cooperating children acquire extra slots, and requires that every acquired slot be returned even on errors.[^8] Cluster schedulers distinguish declared resource requests used for placement from actual runtime use; Kubernetes explicitly refuses placement when requests do not fit even if current CPU and memory use are low.[^9] Slurm likewise queues work until consumable CPU or memory resources become available.[^10]

### The strongest objections

The feature should not be oversold.

First, a single scalar is an **admission estimate**, not resource enforcement. Sixteen units do not stop a process from creating 64 threads or consuming all memory. Kubernetes separates scheduler requests from cgroup-enforced limits for exactly this reason.[^9] SASE should call the number `capacity units`, document the physical-core-equivalent convention, and ensure known parallel tools cap their real concurrency to the granted amount. If hard limits become necessary, cgroups or platform-specific process controls are a separate feature.

Second, guessed weights can create theater instead of control. A fixed `+15` is sound for athena's current full-suite width, but it is wrong on a four-core machine. Policies must scale by effective machine capacity and, where possible, derive from the work plan a command has already computed.

Third, two independent admission pools can fight each other. If `sase tool` reserves 16 units and `tools/run_pytest` then waits on an unrelated worker-token pool, capacity can sit idle or acquisition order can become hard to reason about. The first integration must therefore make the existing pytest controller consume the outer SASE grant rather than acquire a second host lease.

Fourth, upgrades can deadlock. If 32 base-one agents fill a 32-unit machine and all wait while retaining their base unit for a `+15` upgrade, no request can ever fit. Queueing a tool is not the same as queueing a new agent; it needs an atomic **park-and-upgrade** transition.

These are constraints on the design, not reasons to abandon it.

## 3. Recommended capacity semantics

### 3.1 Preserve base claims; add overlay leases

Treat `queue_weight` as the agent lineage's stable base claim. A tool invocation creates a separate, host-local record:

```text
tool_lease_id
owner_key / agent timestamp / project
base_weight
extra_weight
target_weight = base_weight + extra_weight
command label and argv digest
state: waiting | running | forced
requested_at / granted_at
holder PID plus process-birth identity
```

For a lineage with base weight 1 and an active `+15` lease, the lineage's effective occupied capacity is `max(1, 16) = 16`. This deliberately reuses the lineage-max invariant instead of introducing a mutable global counter. A child shell or monitor in the same serial family still does not double-charge the machine.

The lease should be a separate atomic JSON record in the host-wide runner-capacity store, linked to the owner lineage. Do not edit the original agent metadata in place: doing so creates ambiguous recovery after a crash, races with continuation metadata, and conflicts with the Rust core's current rejection of active-lineage reweighting.[^4]

All deterministic work belongs in `sase-core`: validation of positive finite fractional values, effective lineage claims, admission, queue ordering, park/grant transitions, forced-over-capacity projection, and wire records. Python remains responsible for the host boundary: file locks, atomic writes, PID/birth liveness, child process creation, signal forwarding, and cleanup.

### 3.2 Define the argument as additional capacity

The user's phrase “increase by 15” is a useful contract. Make the required positional value `EXTRA`, not a target total and not a named option:

```text
sase tool 15 -- just check-full
sase tool 0.75 -- some-command
```

The tool validates `EXTRA > 0` and finite. The target is computed from the lineage's base claim, which remains available in diagnostics:

```text
base 1 + tool 15 = total 16
```

A target-total interface is slightly easier to nest, but it makes `16` look like an unexplained magic number and contradicts the requested “increase” behavior. Internally, always persist both extra and computed target so there is no ambiguity.

Require `--` before the command. It removes every collision between wrapper flags and child flags, makes completion deterministic, and lets `-f` mean exactly one thing.

### 3.3 One non-blocking default, two explicit retries

The default must not silently queue or silently oversubscribe. On refusal:

```text
Cannot start `just check-full`.
Machine load is 20/32; this agent needs +15 (total 16), which would reach 35/32.

Queue:  sase tool --queue 15 -- just check-full
Force:  sase tool --force 15 -- just check-full
```

Use `-q/--queue` and `-f/--force`. Return a distinct temporary-failure code (75 is conventional on Unix) and, for automation, support `-j/--json` with a stable `capacity_unavailable` code and the computed load, capacity, shortfall, and retry argv. Do not prompt on stdin: many SASE invocations are non-interactive, and an agent can reason about exact retry commands more reliably than a terminal menu.

`--force` still creates a `forced` lease and contributes to load. If load becomes `35/32`, the UI must show that truth in red. Force means “bypass admission,” not “bypass accounting.” The command should print one warning including the projected excess.

Commands that do not run inside a live SASE agent should fail with an explanation for the first release. Anonymous machine-wide leases could be useful later, but inventing an ownership/liveness model for them is unnecessary for this use case.

### 3.4 Queueing must park the base claim

When `--queue` is selected, make one atomic transition under the existing host lock:

1. Register the pending tool request with its total target.
2. Mark the current lineage's base claim parked for capacity accounting.
3. Place the request in the same capacity queue used for new agents.
4. On grant, atomically unpark the lineage and activate the tool target.
5. On cancellation, failure, or stale-holder cleanup, remove the request and restore the base claim if the agent is still live.

This prevents upgrade deadlock and reflects reality: the waiting provider consumes little of the resource the scalar is meant to represent. The TUI should show that agent as queued with a reason like `tool +15: just check-full`.

Use a single fair queue for new claims and tool upgrades. Strict FIFO is understandable but can cause head-of-line blocking when a large request prevents a small request behind it from running; Tokio documents this exact behavior for fair multi-permit semaphores.[^11] SASE already has priority/deference concepts, so the better policy is bounded bypass: preserve request time and priority, allow smaller work to pass a temporarily unfillable head request only a limited number of times, then reserve the next released capacity for the deferred request. Test starvation explicitly.

An impossible request (`target > capacity`) must never enter the normal queue because it can never be granted. Reject it with only two useful alternatives: lower the request or use `--force`.

### 3.5 Lifecycle and nesting

The wrapper must acquire before spawning the child, remain the child's parent, forward signals, mirror the child's exit code or terminating signal, and release in a `finally` path. The durable lease plus holder birth identity handles `SIGKILL` and machine restarts by allowing the next scanner to reclaim stale records. This is the command-scoped equivalent of GNU make's requirement that acquired job slots be returned under all exit paths.[^8]

For the first version, allow at most one top-level tool lease per owner lineage:

- Descendants inherit `SASE_TOOL_LEASE_ID`, `SASE_TOOL_TARGET`, and the granted capacity.
- A nested request at or below the outer target reuses the lease without another charge.
- A nested request above the outer target fails with “reserve the maximum at the outer boundary.”
- Concurrent sibling tool leases in one lineage are rejected until there is a demonstrated need and a clear additive-versus-maximum semantic.

This prevents nested hold-and-wait and makes accounting legible. It also works naturally with the required long-command workflow:

```text
sase monitor start check-full -- sase tool -q 15 -- just check-full
```

The provider can continue or end its turn while the monitor process owns the wait and eventual command. The monitor and tool must share the original claim owner key.

## 4. Capacity configuration and `sase init`

### 4.1 Require an explicit value in the selected overlay

For now, retain the key `max_running_agents`. Renaming it to `machine_capacity` immediately after the weighted migration would add compatibility work without changing behavior. Use “machine capacity” in UI and prose, and schedule a key rename only if the old name remains materially confusing after the feature settles.

However, stop treating the packaged default as satisfying initialization. `sase init` should regard an identity-complete selected overlay with no locally declared `max_running_agents` as incomplete. The validation contract should be:

- present in the selected machine overlay itself;
- numeric, positive, finite;
- integral for the initial prompt and schema, even though tool/agent weights remain fractional;
- reported as drift by `sase init --check` and structured output;
- repaired interactively by `sase init`.

The existing owner-identity flow is the right template: plan read-only changes first, require a TTY when a value is missing or invalid, preserve unrelated YAML, and deploy through the same chezmoi-aware path.[^2]

Prompt with a suggestion, but require explicit confirmation:

```text
Machine capacity units [32]:
```

Prefer detected physical cores when reliably available. Logical `os.cpu_count()` is 64 on athena and would suggest twice the intended value, so it is not a safe universal default.[^7] If physical-core detection is unavailable, offer no guessed number and explain that one unit is approximately a physical-core-equivalent. `--yes` in a non-interactive environment must not invent the value; it should report the exact overlay key that needs configuration.

Apply these real configuration changes in the chezmoi source:

| Selected overlay | Capacity |
|---|---:|
| `sase_athena.yml` | 32 |
| `sase_apollo.yml` | 8 |
| `sase_kellys_mbp.yml` | 4 |

The Mac's configured machine name is currently `kellys_mbp`, not literally `mac`.[^12] These are personal fleet values and belong in those overlays, never in package conditionals keyed on host names.

### 4.2 Migration behavior

Avoid bricking every pre-existing installation on upgrade. For one compatibility release:

- ordinary agent admission may retain the current fallback of 10, with a once-per-command warning that `sase init` must record explicit capacity;
- `sase tool` should fail closed when capacity is unconfigured, because admitting a deliberately heavy command against an accidental fallback defeats the feature;
- the TUI should show `load —/—` plus a configuration warning rather than presenting fallback 10 as an intentional machine choice;
- a later release can remove the fallback after fleet overlays and documentation have migrated.

Temporary runtime overrides should continue to work. The denominator in the Agents tab must always be the **effective** capacity used by admission, while diagnostics can disclose whether it came from the machine overlay or an override.

## 5. The Agents-tab design

### 5.1 One load indicator, in one stable place

Remove `_append_capacity_prefix()` from the left AgentInfoPanel summary. That area should return to visible agent/status counts. The top-right header becomes a Rich `Text` renderable built from the already-cached local capacity snapshot:

```text
load  ▰▰▱▱▱▱▱▱  8/32
```

This is preferable to either bare `8/32` or a sentence:

- `load` names the quantity and removes ambiguity with agent counts;
- eight fixed-width segments expose pressure preattentively;
- the exact ratio remains available for precise reading;
- the whole element is shorter and more stable than the current fleet sentence.

At narrow widths, drop the bar before dropping the exact value, yielding `load 8/32`. The label is dim, filled segments and numerator use the pressure color, empty segments and denominator are muted, and the slash is dim. Suggested thresholds:

- below 75%: quiet cyan/neutral, not a warning;
- 75% through below 100%: amber;
- 100% and above: bold red;
- over capacity: append a compact `!` and preserve the real numerator, for example `35/32 !`.

The current 50% yellow threshold makes an intentionally half-utilized machine look unhealthy. Reserve warning colors for genuine scarcity.

Render integers when the value is mathematically integral and otherwise trim insignificant trailing zeros: `8/32`, `6.75/32`, `0.25/4`. Because load is a floating-point sum, normalize values within the same bounded comparison tolerance used by capacity accounting before formatting; do not use raw `float.is_integer()` and do not alter the stored value. Preserve scientific notation only for extreme magnitudes.

Unknown states should be explicit: `load —/32` when occupancy cannot be projected, and `load —/—` when capacity is unconfigured. Never turn uncertainty into zero.

### 5.2 Preserve diagnostics elsewhere

Replacing `here: athena · … · apollo unknown` removes useful fleet health information along with clutter. Move it, do not discard it:

- machine identity, remote reachability, last observation, and per-host capacity belong in the Machines tab;
- an exceptional fleet problem may place one small warning glyph next to the local load meter, with details in the Machines view;
- “needs you” remains visible in the existing agent status counts rather than being duplicated in the header.

The load is always the local host's global admitted load, regardless of list filter, selected agent, or fleet display mode. The numerator must therefore come from the unfiltered runner projection, not visible rows.

No render path should read files, run a process, scan agents, or poll remote machines. The background refresh already computes and caches runner capacity; carry that snapshot into the header, return Rich `Text`, and refresh only when the runner-capacity token changes. This preserves the TUI responsiveness contract.[^13]

For a selected agent with a live lease, add a secondary detail line such as `Tool: just check-full · +15 · total 16`. Do not overload the global header with command names.

## 6. Initial policy for the seven `just` commands

### 6.1 Principle

The wrapper's generic mechanism belongs to SASE; command policy belongs beside the SASE repository's verification tooling. Do not build a global table inside the CLI that recognizes strings such as `just check-full`. A small repository-owned preflight helper can inspect configured capacity and, for `check`, the existing selection plan, then emit the requested extra capacity and actual parallelism ceiling.

Capacity is a reservation for the whole invocation in the first release. Phase-specific leases would reclaim capacity while `check-full` runs serial lint stages, but they also introduce mid-command parking and more failure states. Start with acquire-at-entry as proposed, instrument it, and split phases later if measured idle reservation is material.

### 6.2 Recommended starting values

| Command | Target on athena | Extra on base 1 | Policy and rationale |
|---|---:|---:|---|
| `just install` | 8 | 7 | Rust builds and dependency installation can fan out and consume memory/I/O. Use `min(8, C)` and cap Cargo/build jobs to the grant. A warm no-build path may request only 2 after preflight. |
| `just fmt` | 2 | 1 | Ruff can parallelize, but Markdown/docs stages are modest and much work is serial. |
| `just lint` | 4 | 3 | Whole-repo Ruff, mypy, Symvision, and validators are sustained but mostly sequential stages. Four units admits useful overlap without pricing it like pytest. |
| `just check` | 2, 4, or 16 | 1, 3, or 15 | Decide before acquisition from the existing selection result: serial scoped, middle gear, or full escalation. This is the most valuable dynamic policy. |
| `just check-full` | 16 | 15 | Matches the intended two-way share of athena and the current pytest controller's half-pool automatic ceiling. |
| `just test` | 16 | 15 | Same parallel runner and worker-width economics as the full test stage. |
| `just test-cov` | 16 initially | 15 | Same worker model, with higher memory/I/O. If memory observations are poor, reduce worker width and reservation together rather than claiming more scalar units while still launching 16 workers. |

For full-suite commands, derive the target from the existing pytest automatic range, bounded by machine capacity. Under today's controller this yields approximately:

| Machine capacity | Full-suite total | Extra on base 1 | Maximum concurrent full suites by admission |
|---:|---:|---:|---:|
| 32 (athena) | 16 | 15 | 2 |
| 8 (apollo) | 4 | 3 | 2 |
| 4 (Mac) | 4 | 3 | 1 |

This exactly provides the requested athena behavior without pretending `+15` is portable. The four-unit floor on the Mac is inherited from the current test controller; measurements may show that a two-worker target is a better interactive default.

For `check`, run selection/preflight before the lease but do not execute expensive gates. The selector already distinguishes serial scoped work, a 2–4-worker middle gear, and escalation to the full lane.[^5] Convert its decision to total targets 2, 4, and the computed full-suite target. If the plan changes or cannot be read, choose the conservative full target rather than under-accounting.

### 6.3 Integrate, do not stack, the pytest gate

When `sase tool` grants a lease, export the target/grant to descendants. `tools/run_pytest` should treat that grant as its maximum worker width and skip acquiring its separate `WorkerTokenLease`; outside a tool lease it should preserve the current worker gate for CI, humans, and backwards compatibility. This gives one admission decision while retaining the measured memory math and non-agent safety net.

Eventually, extract the useful worker-budget calculation into a shared policy provider and let it request a generic SASE tool lease directly. Do not delete the existing suite gate before standalone and CI invocations have an equivalent safety path.

Update the command block at the top of `sase/memory/lint_and_test.md` so agent-facing instructions invoke the wrapper. Keep the raw Just recipes usable for bootstrap and non-agent development. Because that file is durable SASE memory, its implementation must follow the memory edit-and-publish workflow, not an ordinary direct edit.[^5]

Remove all four `w=0.25` stamps from the research swarm template and the `w=2.0` stamp from the epic lander. Their tests and generated/deployed copies must be updated through the xprompt generation flow.[^6] Afterward both types begin at base 1 and pay for heavy work only while the tool lease exists.

## 7. Failure cases and required tests

The implementation is only trustworthy if these cases are first-class:

| Case | Required behavior |
|---|---|
| Child exits 0/nonzero | Release lease; return identical exit status. |
| Child dies by signal | Forward/reflect signal; release lease. |
| Wrapper receives interrupt | Terminate/forward according to existing subprocess policy; release lease. |
| Wrapper is killed | Stale PID/birth identity causes later reclamation. |
| Machine reboots | Durable stale lease never contributes after liveness reconciliation. |
| Capacity changes while waiting | Re-evaluate atomically; reject now-impossible requests. |
| Capacity changes below a running lease | Let it finish, display overload, admit nothing else unless forced. |
| Forced run | Count it; display over-capacity; clean it up normally. |
| 32 agents all request upgrades | Parked bases prevent deadlock; bounded-bypass queue prevents starvation. |
| Tool nested below outer target | Reuse outer lease without double charge. |
| Tool nested above outer target | Fail before spawning. |
| Two sibling tool invocations | Reject in v1 with owner/lease diagnostics. |
| Fractional weights | Compensated summation and tolerant formatting produce stable comparisons and concise display. |
| Unconfigured capacity | Ordinary compatibility behavior warns; tool launch fails closed; TUI shows unknown. |
| Filtered/fleet TUI views | Header numerator remains the same host-global load. |

Add Rust property tests for projection conservation, maximum-by-lineage, upgrade admission, park/grant/cancel, forced overload, impossible requests, fairness, and floating-point boundaries. Add Python integration tests with real subprocesses for locks, atomic records, PID reuse, signals, and exit propagation. Add TUI text and PNG coverage at `0/32`, `8/32`, `24/32`, `32/32`, `35/32`, `6.75/32`, and unknown states.

Roll this out only after the active `sase-z4` repair work is green. Temporary upgrades exercise the same lineage, stale-record, waiter-ordering, and floating-point boundaries that the repair phases are stabilizing; layering them onto a partially repaired base would make failures much harder to attribute.[^1]

## 8. Suggested implementation sequence

1. **Configuration contract:** extend init planning/execution/schema/tests; add 32/8/4 to the real machine overlays; expose configured-versus-fallback origin in the runtime snapshot.
2. **Rust model:** add tool lease wires and pure projection/admission/queue transitions, including park-and-upgrade and forced claims.
3. **Host adapter and CLI:** add atomic storage, liveness, `sase tool EXTRA --`, `--queue`, `--force`, JSON output, signal/exit fidelity, and completions.
4. **TUI:** move the cached load snapshot to the top-right Rich meter; remove the left prefix; relocate fleet diagnostics; add lease detail and visual tests.
5. **Verification integration:** connect repository preflight policies, export grants to pytest, update the memory command block, and measure reservations.
6. **Remove static weights:** update research-swarm and epic-lander source templates, generated artifacts, defaults, and tests.
7. **Tune from evidence:** record requested target, queue duration, run duration, peak worker count, and whether the run used the reserved width. Revisit the table after several weeks.

Do not combine all seven steps into one landing. The Rust model and subprocess lifecycle deserve an independently reviewable phase before policy and visual polish.

## 9. Final recommendation

Build the feature. It corrects a real modeling error—charging an agent's identity for a command's transient cost—and makes machine capacity useful beyond launch-time admission.

The recommended product contract is:

- every initialized machine explicitly declares capacity (athena 32, apollo 8, current Mac overlay 4);
- every live agent starts with a base claim of 1 unless a user deliberately specifies otherwise;
- `sase tool EXTRA -- COMMAND` creates a temporary lineage overlay, never mutates the base claim;
- a failed immediate attempt offers exact queue and force retries;
- queueing atomically parks the base claim, shares the global fair scheduler, and cannot accept impossible requests;
- forced work remains counted and visibly over capacity;
- parallel tools honor the grant, so the number is more than decorative;
- the Agents tab has one stable top-right `load` meter and no duplicate capacity display;
- full-suite work targets half of capable hosts (`16` on athena), while `check` chooses 2/4/full from its selection plan;
- research and lander launch-time weight overrides are removed.

That design is intuitive at the command line, honest in the TUI, recoverable after crashes, and compatible with the weighted-lineage architecture already being repaired. Most importantly, it creates a general resource-admission primitive without making SASE pretend to be an operating-system resource controller.

## Sources

[^1]: SASE internal records: epic bead `sase-z4`, “Weighted agent capacity, queue admission, and Agents load visibility,” and durable plan snapshot `plan:202609/weighted_queue_capacity.md`, accessed 2026-09-11; follow-on repair plan `plan:202609/weighted_capacity_landing_repairs.md`.
[^2]: SASE source at revision `f9680bc65`: `src/sase/default_config.yml`, `src/sase/config/_settings.py`, `src/sase/main/config_init_handler.py`, and `src/sase/config/identity.py`, inspected 2026-09-11.
[^3]: SASE source at revision `f9680bc65`: `src/sase/ace/tui/widgets/agent_info_panel.py`, `src/sase/ace/tui/actions/agents/_fleet_header.py`, and `src/sase/ace/tui/styles.tcss`, inspected 2026-09-11.
[^4]: `sase-core`, `crates/sase_core/src/runner_capacity.rs`, especially claim grouping, compensated occupancy, candidate decisions, and the `active-claim-weight-conflict` contract, inspected through the configured SASE repository checkout on 2026-09-11.
[^5]: SASE source at revision `f9680bc65`: `sase/memory/lint_and_test.md` (audited memory read), `Justfile`, `tests/_suite_gate_budget.py`, and `tools/run_pytest`, inspected 2026-09-11.
[^6]: SASE `src/sase/default_config.yml` epic-lander xprompt and `sase-research-artifacts` `src/sase_research_artifacts/xprompts/research_swarm.md`, inspected through configured SASE repository checkouts on 2026-09-11.
[^7]: Local host inventory sampled 2026-09-11 with `lscpu` and `/proc/meminfo`: AMD Ryzen Threadripper 3970X, 32 cores, 64 threads, 65,712,596 KiB total memory. Available memory is time-varying and was used only to confirm memory is a real scheduling dimension.
[^8]: GNU Project, [“Job Slots (GNU make)”](https://www.gnu.org/software/make/manual/html_node/Job-Slots.html), GNU make manual, accessed 2026-09-11.
[^9]: Kubernetes Documentation, [“Resource Management for Pods and Containers”](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/), accessed 2026-09-11.
[^10]: SchedMD, [“Consumable Resources in Slurm”](https://slurm.schedmd.com/cons_tres.html), accessed 2026-09-11.
[^11]: Tokio, [“Semaphore in `tokio::sync`”](https://docs.rs/tokio/latest/tokio/sync/struct.Semaphore.html), fairness and `acquire_many`, accessed 2026-09-11.
[^12]: Chezmoi configuration source: `home/dot_config/sase/sase_athena.yml`, `sase_apollo.yml`, and `sase_kellys_mbp.yml`, inspected through the configured linked repository on 2026-09-11.
[^13]: SASE reference memory `tui_perf.md` (audited read), plus the current cached runner-capacity refresh path, inspected 2026-09-11.
