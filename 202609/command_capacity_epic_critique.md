# Critique of the sase-zm command-capacity epic

Research date: 2026-09-12. Adversarial review of the `sase-zm` epic
("Command capacity reservations and fleet load meters") and its plan
`plan:202609/command_capacity.md`, performed on athena at SASE master `9c2eb4a35`.

This is a critique, not a re-derivation. It assumes the source report
`research:202609/command_capacity_and_load_meter/command_capacity_and_load_meter.md`
and the plan are correct about *what* is being built, and asks where the approach is
likely to hurt, where the plan is factually wrong about the current tree, and what
cheaper shapes exist. Nothing here was changed in any repository.

**Overall position: the feature is worth building, but the epic as scoped is the wrong
size and the wrong shape in four specific ways.** The accounting model is sound; the
*activation* decision (athena = 32 with a static, health-blind denominator) is the
riskiest part of the epic and is currently justified by numbers that do not hold on
athena today. Several findings below are reproducible right now.

## Evidence base

Read directly: the full plan; `sase bead show` for `sase-zm`, `sase-z4`, `sase-z4.6`,
`sase-zl`, `sase-zl.13`, `sase-zn`; decision records `gates-never-block`,
`single-turn-agents`, `two-speed-verification`; `Justfile`; `tests/_suite_gate*.py`;
`tools/run_pytest`; `tests/_test_selection.py`; `src/sase/core/runner_slots/_admission.py`;
`src/sase/axe/run_agent_wait_slots.py`; `src/sase/ace/tui/widgets/agent_info_panel.py`;
`src/sase/ace/tui/actions/agents/_fleet_header.py`; `src/sase/ace/tui/models/agent_runner_slots.py`;
`src/sase/ace/tui/styles.tcss`; `src/sase/main/config_init_handler.py`;
the consolidated source research report (via `sase artifact read`).

Measured on athena, 2026-09-12: `nproc` = 64, `MemTotal` = 62.7 GiB,
`MemAvailable` = 9.9–11.8 GiB (varied across samples during the review),
swap in use = 34 GiB, root filesystem 97% full with 34 GiB free.

---

## Severity 1 findings

### R1. The plan's own worker arithmetic does not hold on athena today

The plan fixes athena's full-check price at `D=15` and states "Athena's current automatic
pytest ceiling is 14 workers for a 32-token pool." That is the *unconstrained* answer.
`tests/_suite_gate_budget.py:_calculate_default_token_budget` clamps the pool by
`MemAvailable`, and on athena right now it returns **2**, not 32:

```
cpu 64  mem_avail_kib 10386148  budget 2  worker range (2, 2)
# same function at 62 GiB available: budget 32, range (4, 14)
# at 20 GiB available:               budget 17, range (4, 8)
```

(Reproduce with `.venv/bin/python -c` against `_calculate_default_token_budget` and
`automatic_worker_range`; see "Reproduction" below.)

So the system being replaced is *currently self-throttling athena by 7x* relative to the
price the new system would charge, and it is doing so for a reason: athena is in swap.
The plan deliberately removes that feedback — "These values come from the user, not an
automatic CPU or fluctuating free-memory calculation" — and demotes memory to a
post-admission worker-width adjustment ("Additional CPU and available-memory checks may
reduce concurrency"). Admission itself becomes health-blind.

This is the single highest-risk decision in the epic, and it lands while `sase-zn`
("Fix ACE TUI typing lag on athena (memory pressure …)") is still open with three
in-progress phases, including `sase-zn.7: Attribute and fix the residual ACE heap growth`
and `sase-zn.6: Extend scratch hygiene … and disk pressure`.

**Recommendation.** Keep the explicit persistent capacity as the *policy* number, but make
the **effective** denominator `min(persistent_capacity, health_derived_ceiling)` and make
`health` one of the already-specified `capacity source` values. The plan has all the
machinery for this already: it distinguishes persistent capacity, effective capacity,
temporary override, and capacity source, and the meter is specified to show source and
an overload marker. This is a small delta that preserves the "the user decides the
number" property while keeping the one safety property the current system has.
Do not ship athena=32 without it.

### R2. Athena=32 is a memory and disk commitment nobody has priced

Measured per-agent cost on athena at the time of review: 14 live workspace runner
processes holding **7.03 GB RSS total (~500 MB median, ~950 MB peak each)**. Workspace
checkouts are **4.3 GB each**, and 35 already exist on a filesystem that is **97% full
with 34 GiB free**.

Raising `max_running_agents` from the packaged default 10 to 32 raises the *steady-state*
agent footprint from roughly 5–10 GB to roughly 16–30 GB of RSS, before a single pytest
worker is admitted, on a machine with under 12 GB available and 34 GB already swapped.
It also triples the plausible live-workspace working set against 34 GiB of free disk.

The plan treats 32 purely as a scheduling number. In practice it is a simultaneous
decision to triple agent concurrency, and none of the epic's acceptance criteria measure
the resulting resident-set or disk footprint — `acceptance` measures "cost observations
and UI performance comparison," not host memory or disk headroom.

**Recommendation.** Separate the two decisions. Land the reservation ledger, the tool
command, the profiles and the meters against athena's *existing* capacity of 10 (agents
at 1, `check-full` priced against 10 rather than 32), prove the accounting, and make the
raise to 32 its own gated change with a host-footprint measurement as its acceptance
evidence. The epic currently couples a mechanism it can prove to a policy number it
cannot.

### R3. One scalar for two unlike resources makes idle agents starve verification

An ordinary agent at `B=1` is an LLM-bound process: ~500 MB resident, near-zero CPU while
waiting on a provider. A pytest worker at 1 unit is a core plus ~700 MiB. The plan
prices them identically and draws them from one budget.

Consequence at athena=32 with `D=15`: **18 concurrent ordinary agents permanently
prevent any full check from being admitted** (18 + 15 = 33 > 32), even though those 18
agents are consuming almost no CPU. The machine can be simultaneously "full" for
verification and nearly idle in every physical sense. Today, `max_running_agents=10` and
the 32-token pytest pool are independent, so agent count cannot starve tests at all.

This interacts badly with the aging rule (R4) and with the fact that SASE agents are
long-lived: `decisions:two-speed-verification` records ~61 worker-minutes per full-suite
run against ~46,000 worker-minutes/day of gated capacity — that budget was sized as
*test* capacity, and the epic now asks agents to share it.

**Recommendation.** The plan rightly excludes a "general multidimensional scheduler," but
the minimum viable fix is one number: a **reserved verification floor** — a portion of
capacity (e.g. 15 units on athena) that ordinary agent launches may not consume, so one
heavy command can always eventually be admitted without freezing the fleet. This is
strictly simpler than aging protection and removes most of the need for it.

### R4. Aging protection converts one queued check into a fleet-wide launch freeze, with no backfill

The plan: after 120 seconds of capacity-blocked eligible time, "protect that oldest aged
request from all newer competing admissions, including new agents, until its frozen
target fits," and "Existing running work is never preempted."

With `D=15` on a 32-unit machine holding 18+ one-unit agents, the protected request waits
for 15 units to free. Every unit freed by a finishing agent is then *held idle* until the
target is reached, and no new agent may launch during that window. SASE agents run for
minutes to hours, so the freeze is unbounded in practice and the machine is
under-utilized for its whole duration. This is textbook head-of-line blocking plus
capacity hoarding; HPC schedulers solve it with backfill using job runtime estimates, and
SASE has no runtime estimate for an agent.

The plan's acceptance criterion ("a 120-second aged heavy request blocks later agents and
eventually runs") tests that the freeze *happens*, not that it is bounded.

**Recommendation.** Bound the protection explicitly: either (a) adopt R3's reserved
verification floor, which removes the need to freeze anything; or (b) cap the hoarding
window and admit backfill work whose *declared* maximum duration is shorter than the
projected fit time (agents would need a declared max-lifetime, which is independently
useful); or at minimum (c) make the freeze's expected duration visible in `tool status`
and on the meter, so an operator sees "athena launches frozen for the last 40 minutes"
rather than an inexplicably idle machine.

### R5. The durable ledger is leak-prone where the flock pool it replaces is leak-proof

The existing pytest gate holds capacity by holding an `flock` on a numbered token file
(`tests/_suite_gate_pool.py`). Its failure mode on a crash is *release*: the kernel drops
the lock, and the docstring says so — "a holder that dies never has to clean up after
itself." The risk is under-counting.

The plan replaces this with durable JSON reservations plus a reconciler, and forbids the
one backstop the current system has: **"No age-only expiry for a living holder."** The
current gate has three age backstops that exist because of observed incidents —
`_DEFAULT_STALE_SECONDS` = 30 min without a heartbeat, `_DEFAULT_MAX_HOLD_SECONDS` = 4 h
absolute, `_DEFAULT_TIMEOUT_SECONDS` = 45 min bounded acquisition — and
`tests/_suite_gate_env.py` documents the motivating case: "far shorter than the 27-hour
scoped run that motivated the bound."

The new failure mode is the inverse and much worse: a leaked reservation of 15 units on a
32-unit machine permanently removes half the machine, and the epic simultaneously removes
the 45-minute acquisition timeout ("omitted queue timeout waits until grant/cancellation").
A leak plus an unbounded wait is a silent, permanent fleet stall.

**Recommendation.** Do not replace the crash-safe primitive — layer on it. Keep one
kernel-held `flock` per reserved unit (or one per reservation with the unit count in its
metadata) as the *liveness floor*, so capacity can never leak past process death, and use
the durable JSON record for identity, attribution, generation, argv, fingerprints and
reconciliation. The plan's objection to flock — that a handle can survive `exec` and
descriptor duplication — is an argument that flock is insufficient proof of *child* death,
not an argument against using it as the anti-leak floor. Additionally: keep a
`max_hold`-style age cap as a loud diagnostic and an operator-visible "reclaimable"
marker even if it never auto-reclaims, and give `-T/--queue-timeout` a non-infinite
default.

---

## Severity 2 findings

### R6. Parked monitors hold workspaces that the capacity meter reports as free

Inside an agent, `-q` "always means a durable monitor handoff, even if it fits
immediately." The handoff releases `B`, parks the monitor at demand 0, and "Retain
workspace ownership throughout a parked wait." Queued reservations "do not fill the load
meter," and an omitted queue timeout "waits until grant/cancellation."

So N agents that queue heavy work produce N parked monitors, each holding a 4.3 GB
workspace checkout and a supervisor process, while the meter reads **0/32**. A new agent
passes capacity admission and then cannot obtain a workspace. The headline deliverable of
the epic — "make every enabled machine's load clear in Agents" — would display an idle
machine that cannot start work.

**Recommendation.** Two cheap fixes, both within the plan's existing surfaces:
(1) render queued demand as a distinct, non-filling marker on the capsule
(e.g. `8/32 ⇥30`) so blocked-but-idle is legible; and (2) make workspace tenure a
first-class part of the reservation record and refuse/park on workspace exhaustion with
the same typed diagnostic, rather than letting it surface as an unrelated launch failure.

### R7. `-q` inside an agent burns a provider turn even when the command fits

The plan's rationale for unconditional handoff is `decisions:single-turn-agents` and "Do
not run the command while the predecessor is still doing uncounted work." But when the
command fits, the inline run is *fully counted* at `B+D` — there is no uncounted work and
no accounting benefit. The handoff is pure cost: one killed provider turn, one successor
launch, one context reload, per verification.

Meanwhile the plain (no-flag) invocation exits 75 on refusal without starting a child, so
an agent that guesses wrong in the other direction burns a turn discovering the refusal
and then must re-issue with `-q`. The guidance phase will teach "always use `-q`", which
maximizes the cost.

**Recommendation.** Make the default invocation do the right thing in one turn: run
inline if it fits, otherwise automatically reserve, hand off, and park — with
`--no-queue` to opt into the exit-75 refusal and `-q` retained only as "always hand off."
This eliminates both the wasted-refusal turn and the gratuitous handoff, and it is
consistent with `single-turn-agents` (the handoff is still mechanical; the agent never
waits).

### R8. `recipe-admission` is scoped to seven recipes; the bypass surface is ~53

The plan correctly observes that "a wrapper only inside the body of `check` is too late
because `_setup` can compile Rust," then concludes the fix is to "refactor into public
admitted entry points and private implementation stages" for "the seven named public
recipes."

Counted in the current `Justfile`: **53 public recipes** take `_setup`, `_setup-visual`,
`_setup-demos`, or `_setup-terminal-smoke` as a dependency — every `test-*` lane,
`lint`, `fmt*`, `validate`, `selection-health`, `selection-backtest`, `demos`, and a dozen
`bench-*`/`*-perf-check` recipes. `install`, `install-visual`, `build`, `rust-install`,
`rust-dev-install`, `rust-lsp-install` are additional independently-callable expensive
entry points. The plan's own enforcement requirement — "The rollout must demonstrate no
supported path can acquire the old independent budget after activation" — cannot be met
by wrapping seven of them, and every recipe added later is a silent new bypass.

The plan's diagnosis points at the right fix and then walks away from it: **`_setup` is the
choke point.** Putting admission inside `_setup` and inside
`tools/run_pytest` / the xdist conftest hook covers all 53 recipes in two places, makes
the invariant maintainable by construction, and lets public `sase tool run` wrappers
merely *widen* an envelope rather than be the sole creator of one.

**Recommendation.** Invert the enforcement: admission in `_setup` + `run_pytest`/conftest
as the mandatory floor; public wrappers acquire the larger peak envelope and nested
`_setup` reuses it. Keep the seven-recipe refactor only where a public recipe genuinely
needs a bigger envelope than its stages. This also shrinks `recipe-admission` from an
under-sized "medium" phase to something a medium phase can actually finish.

### R9. Serial work is still free, and the cap raise multiplies the hole

The plan prices the bounded serial scoped stage at `D=0` inline, and permits bounded
serial lint at `D=0` "when that extra cannot fit" — i.e. precisely when the machine is
busiest. The existing gate has the same hole by design ("Nothing here bounds a serial run
— a run of width one takes no tokens"), but today it is capped by
`max_running_agents=10`.

At athena=32, 32 agents each running `just check` inline are 32 concurrent `mypy`
processes and 32 concurrent `ruff` invocations at `D=0` total charged demand. `ruff` is
rayon-parallel over all cores by default and nothing in the `Justfile`, `pyproject.toml`,
or the recipes pins `RAYON_NUM_THREADS` (verified by grep). `mypy` is single-process but
memory-heavy. This is the exact thundering herd the epic exists to prevent, re-created
inside the epic's own zero-priced lane, at 3.2x today's multiplicity.

**Recommendation.** Either give the serial lane a small non-zero floor (e.g. `D=0.5`) so
that 32 concurrent serial checks are not free, or — cheaper and more honest — pin the
thread budgets (`RAYON_NUM_THREADS`, prettier/keep-sorted concurrency) for the `D=0` lane
*before* the lane is allowed to be free, and make that pinning a `profiles`-phase
deliverable rather than a conditional aside inside step 2 of the dynamic-check policy.

### R10. Three different meanings of "weight" across one command surface

- `queue_weight` / `%q(w=…)`: an agent's **base total**, immutable at launch.
- `sase tool run -w N`: "additional units for an active agent, **total** units when there
  is no active provider baseline" — the same number means `B+N` inline and `N` in a
  monitor. The plan states this explicitly: "`-w 0.25` contributes 0.25 in a monitor and
  B+0.25 inline."
- `sase monitor start -w N`: an explicit **total**.

The same flag letter carries increment semantics in one context and total semantics in
another, silently selected by whether a provider baseline exists. This will be a durable
source of mis-sized reservations by both humans and agents, and it is cheap to fix before
anything ships.

**Recommendation.** Name the two things differently — `--extra`/`-x` for command demand
and `--total`/`-w` where a total is meant — or make `-w` always a total and derive the
increment. Either way, always print both `B+D` and `D` in `tool status`, dry-run, and
refusals (the plan already does this in the refusal specimen; make it universal).

### R11. Short-option letters collide with `sase monitor start` and the global parser

`sase tool run` is specified with `-q -f -w -p -n -j -r -t -T`. Against the existing
`sase monitor start --help`:

| Letter | `sase tool run` | `sase monitor start` |
| ------ | --------------- | -------------------- |
| `-f`   | `--force`       | `--completion REF`   |
| `-n`   | `--dry-run`     | `--next TEXT`        |
| `-p`   | `--profile` (cost) | `--profile` (outcome) |
| `-r`   | `--resume`      | `--reason TEXT`      |
| `-t`   | `--timeout`     | `--timeout`  ✓       |
| `-T`   | `--queue-timeout` | `--tail-lines N`   |

Five of eight collide, and the epic's central idiom composes these two commands
(`sase monitor start … -- sase tool run …`). `-f` additionally collides with the global
`sase -f/--enable-feature`.

**Recommendation.** Pick letters that do not collide across the two commands the epic
teaches together (`-Q` for queue-timeout, `-R` for force/override, `-X` for dry-run, etc.),
or accept the collisions deliberately and document them in the `guidance` phase's monitor
skill rewrite. Do not discover this during `cli`.

### R12. The meter specimen does not fit the widths its acceptance criteria require

The plan's specimen row, measured:

```
[athena · here] ▰▰▱▱▱▱▱▱  8/32   [apollo] ▰▰▰▱▱▱▱▱  3/8   [kellys_mbp] ▱▱▱▱▱▱▱▱  0/4
```

is **84 display columns**. The acceptance criterion is "Keep the ratio readable at
70/80/120 columns with the configured three-machine fleet." Ratios-only is 52 columns;
dropping the `here` accent gets it to 45. But `#agents-fleet-status` shares its single row
with the left status strip built by `AgentInfoPanel._build_display_text` (agent count,
capacity, `[N running · N queued · N needs you]`, proc-shell badge, neighbors badge,
filter text), which is comfortably 45–60 columns on its own. **At 70 and 80 columns the
two cannot coexist on one row even in the ratios-only fallback.**

The plan therefore requires multi-row wrapping at exactly the widths where it also
requires "a stable header height for a given width/fleet membership so routine load
updates do not move selection" — those are compatible only if height is a pure function
of (width, fleet membership) and never of load, which the ratio-width change
(`8/32` → `12.5/32`) violates unless the ratio field is width-reserved.

**Recommendation.** Specify a reserved-width ratio field (right-aligned, sized for the
widest representable value incl. `—/—` and `~`) in the `meters` phase contract, and add a
70/80-column three-machine PNG *with a populated left strip and an active filter* to the
required scene list. The current scene list does not say the left strip is populated.

### R13. Also-hidden header path the plan does not mention

The plan says "The existing `_update_agents_header` fleet-visibility condition and fixed
one-line CSS must change" to keep the local capsule visible. There is a third hide path
it does not name: `styles.tcss` has

```
#agents-view.-onboarding-active #agents-header { display: none; }
```

`#agents-header` is also `height: 1; max-height: 1`. Both need changing, and the
onboarding case needs a deliberate decision (probably: still hidden, but say so).

---

## Severity 3 findings and plan-accuracy defects

### R14. `ProviderInfoPanel` does not exist

The plan instructs: "Remove `ProviderInfoPanel._append_capacity_prefix` and its call."
There is no `ProviderInfoPanel` anywhere in `src/` or `tests/`. The method is
`AgentInfoPanel._append_capacity_prefix` at
`src/sase/ace/tui/widgets/agent_info_panel.py:379`, called at line 447. Minor, but it
suggests part of the plan's source-evidence pass was written from memory, which is worth
knowing when trusting its other symbol-level claims.

### R15. `check-full` is priced as if it ran `just test`; it runs `test-cost`

The `check-full` recipe runs `just test-cost` (cost-attribution lane, heavier plugin),
then `check_test_cost_budgets`, then `selection-health --fail-on-new-flake`. The plan's
demand table prices `check`, `check-full`, `test`, and `test-cov` identically at
`D=15/3/1`. `test-cov` (coverage) in particular has materially higher per-worker memory
than `test`.

**Recommendation.** The `profiles` phase should measure `test`, `test-cov`, and
`check-full` separately before freezing one number for all three, and the initial table
should say explicitly that it is a *policy floor*, not a measurement, for the two lanes it
did not measure.

### R16. The repo-specific price table lives in Rust, so every tuning iteration costs a release

The plan puts "profile decisions" in Rust core and describes "versioned SASE-repository
profiles" with an initial demand table keyed to this repository's recipe names
(`check-full`, `test-cov`, `rust-install`). It simultaneously wants iterative tuning:
"tune from fresh evidence," "Record other tuning as versioned profile/config changes with
before/after evidence."

Those two pull against each other, and against `rust_core_backend_boundary`: a
repository's recipe-name-to-price table is *configuration*, not shared backend behavior.
Encoding it in `sase_core` means every price change requires a core commit, a release-plz
version, a PyO3 rebuild, a published-wheel floor bump, and a coordinated SASE bump — for a
number the plan expects to change repeatedly.

**Recommendation.** Core owns the profile *schema*, the arithmetic, the fingerprinting,
and the matching algebra. The table itself ships as versioned data — `default_config.yml`
or a `profiles.yml` in the repo it prices — validated against the core schema. This
preserves "policy in Rust" in the sense that matters (one implementation, one set of
rules) while making tuning a one-line config change.

### R17. Ledger placement needs an explicit decision against Syncthing and tmpfs

`sase_home()` is `~/.sase`, and the existing admission lock is `~/.sase/runner_slots.lock`.
The existing pytest pool defaults to `/tmp/sase-pytest-tokens-$UID`, which on athena is
tmpfs. Commit `32879ff7f` — "Reclaim athena now and move SASE_TMPDIR off tmpfs **and out
of Syncthing**" (`sase-zn.1`, landed yesterday) — establishes that SASE state has already
been found inside a Syncthing-replicated path on this host once. A high-churn,
frequently-rewritten reservation ledger replicated to apollo and the Mac would produce
`.sync-conflict-*` files inside the authoritative capacity directory; a tmpfs ledger
trades that for RAM consumption on the machine the epic is trying to protect.

Athena's `~/.config/syncthing/config.xml` currently declares a second folder at path `~`
with an empty folder id (likely inert), so this is a hazard to *verify*, not a confirmed
defect. Either way the epic should state the ledger's location and its
durability/replication requirements explicitly rather than inheriting `sase_home()` by
default.

### R18. `max_running_agents` is genuinely unset on athena — the plan handles this correctly

For the record, because it validates one of the plan's requirements:
`~/.config/sase/sase_athena.yml` has no `max_running_agents` key, so athena is running on
the packaged default of 10. The plan's "source-aware validation: a packaged default …
does not satisfy explicit selected-machine initialization" will correctly flag athena as
uninitialized at `sase init --check` time. Good.

---

## Sequencing and structure

### S1. Both declared prerequisites are unfinished, and both have spawned remediation epics

`sase-zm.2` (contracts) depends on `sase-z4`; `sase-zm.5` (monitors) depends on `sase-zl`.
As of this review:

- `sase-z4` is `IN_PROGRESS`. Its landing review found reproduced defects (decimal
  boundary rejection at limit, parallel-predecessor double-counting 2.0 as 4.0,
  pre-stamped successor bypass, missing queued serial children in the TUI, parked ordering
  ignoring capacity shortfall) and spawned `sase-z4.6`, which has itself spawned
  `sase-z4.6.5: Finish weighted-capacity acceptance`. That is **two nested remediation
  epics** on the accounting contract `sase-zm` builds on.
- `sase-zl` is `IN_PROGRESS` with `sase-zl.13` open and four of its ten phases still
  running, including host-finalizer recovery — a TypeError in the real
  `launch_followup_agent` call path was confirmed 7 hours before this review.

`sase-zm` then adds 14 medium phases whose critical path is
`baseline → contracts → leases → fair-queue → monitors → cli → profiles →
pytest-admission → recipe-admission → guidance → acceptance` — an 11-deep serial chain
that cannot start its second link until a two-level-nested remediation epic finishes.

**Recommendation.** Do not start `sase-zm.2` on an estimate of when `sase-z4.6.5` lands.
Either (a) hold the epic and let `baseline` collect fixtures only, as the plan already
allows, or (b) re-scope so that the phases with no prerequisite dependency —
`initialization` (depends only on `contracts` for shape), `fleet-snapshots`/`meters`
(read-only observability), `cli` surface design — land first behind a read-only,
non-enforcing ledger. Observability of the current weighted load is independently
valuable and would have surfaced R1/R2 before they became an activation decision.

### S2. `acceptance` is not a medium phase

Its stated scope: combined Linux **and macOS** lifecycle matrix, fakey concurrency,
packaging, cold and warm bootstrap, version cutover **and rollback**, stale-peer matrix,
cost calibration, UI performance comparison, and staged per-machine deployment to three
machines — two of which the plan itself concedes may be unreachable ("Offline/unavailable
apollo or Mac activation remains an explicit outstanding prerequisite"). As written the
phase cannot close.

**Recommendation.** Split activation into per-machine closable units with athena first,
and define epic completion as "athena activated, apollo/Mac prepared and explicitly
pending," so the epic is not held open by a machine being off.

### S3. The drain-based cutover requires a fleet-wide quiesce that may never converge

The cutover protocol is: pause new legacy launches, let legacy agents, monitors, and
pytest holders finish, verify the old pool is drained, then switch. On athena, `sase agent
list` reports 71 agents across several concurrently-running epics, and the plan forbids
killing active work to reach the barrier. A full quiesce of a machine that is
continuously launching epic phase workers is an indefinite pause.

**Recommendation.** Use a dual-write transition instead of a quiesce. During the window,
new-protocol holders acquire *both* the legacy flock tokens and the new ledger units; the
legacy pool stays the binding constraint for tests, the ledger runs in shadow, and the
final switch is a flag flip with no drain required. This is strictly safer than a global
pause, satisfies "never switch ledgers underneath live commands," and turns
`acceptance`'s riskiest step into a verification step.

---

## What the plan gets right (do not relitigate these)

- Reservations tied to an authoritative claim owner with generation, boot identity, and
  process-birth identity — correct, and the PID-reuse concern is real.
- Immutable `queue_weight` with authored/inherited provenance preserved.
- Rejecting in-place hold-and-wait upgrades and requiring stage transitions only after
  descendants exit — this is the rule that prevents the classic nested-build deadlock.
- Requiring the `--` delimiter and preserving argv exactly without an implicit shell.
- Refusing to infer success from a shell string containing `just check-full`, and feeding
  `sase-zl` typed records rather than a numeric 75.
- Independent per-machine denominators with no combined "44" — correct and important.
- Making capacity initialization source-aware so a packaged default cannot satisfy it.
- Removing the dead `%q(w=2.0)` lander weight and the four `w=0.25` swarm weights only at
  the end, coupled to the admission system landing.

---

## Reproduction

```sh
# R1 — athena's actual pytest budget right now
cd <sase workspace>
.venv/bin/python -c "
import os
from tests._suite_gate_budget import (
    _calculate_default_token_budget, automatic_worker_range,
    _read_mem_available_kib, _MEMINFO_PATH)
mem = _read_mem_available_kib(_MEMINFO_PATH)
b = _calculate_default_token_budget(cpu_count=os.cpu_count(), mem_available_kib=mem)
print('cpu', os.cpu_count(), 'mem_avail_kib', mem, 'budget', b, automatic_worker_range(b))"

# R2 — per-agent RSS, workspace size, disk headroom
ps -eo rss,args --no-headers | grep 'sase_[0-9]*/\.venv/bin/python' \
  | awk '{s+=$1; n+=1} END {print n, "procs", s/1024, "MB"}'
du -sh ~/.local/state/sase/workspaces/sase-org/sase/sase_20
df -h ~

# R8 — public recipes that inherit an expensive _setup dependency
grep -cE '^[a-zA-Z][a-zA-Z0-9_-]*( [^:]*)?:.*_setup' Justfile

# R9 — no thread pinning for the zero-priced serial lint lane
grep -rn 'RAYON_NUM_THREADS' Justfile pyproject.toml tools/ ; echo "exit=$?"

# R12 — specimen width
python3 -c "
import unicodedata as u
s='[athena · here] ▰▰▱▱▱▱▱▱  8/32   [apollo] ▰▰▰▱▱▱▱▱  3/8   [kellys_mbp] ▱▱▱▱▱▱▱▱  0/4'
print(sum(2 if u.east_asian_width(c) in 'WF' else 1 for c in s))"

# R14 — the symbol the plan names does not exist
grep -rn 'ProviderInfoPanel' src tests ; echo "exit=$?"
grep -n '_append_capacity_prefix' src/sase/ace/tui/widgets/agent_info_panel.py
```

---

## If you only change three things

1. **Make the effective denominator health-aware (R1) and decouple the athena=32 raise
   from the mechanism (R2).** This is the difference between an epic that makes load
   legible and an epic that makes athena thrash.
2. **Put admission in `_setup` and `run_pytest`, not in seven recipe wrappers (R8).** Two
   choke points instead of fifty-three, and the "no supported path can acquire the old
   budget" criterion becomes provable instead of aspirational.
3. **Keep `flock` as the anti-leak floor under the durable ledger, and give the queue a
   default timeout (R5).** The system being replaced cannot leak capacity; the replacement
   as specified can, permanently, on a 32-unit machine, with no age backstop and no
   bounded wait.
