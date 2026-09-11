---
create_time: 2026-09-11
updated_time: 2026-09-11
status: research
---

# Dynamic Tool Capacity Claims: `sase tool`, Required Machine Capacity, And A Readable Load Meter

**Research question.** Epic `sase-z4` replaced "max N agents" with "max C weighted
capacity". Bryan wants four follow-ups: (1) replace the Agents-tab fleet header with a
single `<L>/<C>` load meter and delete the duplicate one in the info panel; (2) require
each machine to declare its capacity at `sase init` (athena 32, apollo 8, mac 4);
(3) render load and capacity as integers when possible; and (4) — the big one — add
`sase tool`, a wrapper that raises an agent's weight while a slow command runs and drops
it when the command finishes, wrap the `just` verification commands with it, remove the
hard-coded `%q(w=…)` presets, and give a blocked agent a queue-or-force choice. Also:
critique the idea, push toward a stronger architecture where one exists, and end with a
recommendation.

**Verdict up front.** Build it. The core insight is correct and it fixes a measured,
real problem: SASE's admission control is blind to what an agent *does* after it is
admitted, so the single most expensive operation in the repo — `just check-full`, ~61–123
worker-minutes — is governed only by a memory note asking agents to be polite. Replacing
a social contract with a mechanical budget is the right trade.

But three things in the proposal as stated will hurt, and I recommend changing them:

1. **There is already a host-global weighted admission system for exactly this
   resource** — the pytest suite gate (`tests/_suite_gate*.py`, 1,505 lines, crash-safe
   flock leases, a 32-token pool on athena *today*). Building `sase tool` beside it
   creates two ledgers that disagree about the same 64 cores. `sase tool` should
   *subsume* it, not sit next to it.
2. **`sase tool` must not be the thing that waits.** SASE agents are single-turn
   (`decisions:single-turn-agents`) and gates never block (`decisions:gates-never-block`).
   The queue already exists and already holds the family's claim while it runs: it is
   `sase monitor`. Make the monitor capacity-aware and the "queue yourself" choice
   becomes one existing command instead of a new waiting primitive.
3. **Fixed weights (`+15`) are wrong on a 4-capacity machine.** A weight-16 claim on mac
   (C=4) is not "slow", it is `weight-exceeds-limit` — a permanent hard refusal. Tool
   demand must be a *(floor, ceiling) range clamped to the machine*, which is exactly how
   the suite gate already sizes a pytest run.

Two further findings are blocking-severity and not obvious from the outside:

- **Today's Rust policy explicitly forbids what `sase tool` needs to do.**
  `runner_capacity.rs:700` rejects a candidate that requests a weight different from its
  active lineage claim (`active-claim-weight-conflict` → decision `invalid`). Dynamic
  weight is a new core concept, not a Python wrapper over the existing one.
- **There is no head-of-line reservation anywhere in the policy.** `waiter_blockers()`
  admits strictly on "does my weight fit in free capacity". A weight-15 claim will be
  starved indefinitely by a stream of weight-1 agents. Shipping `sase tool` without a
  reservation rule ships a feature that visibly does not work on a busy host.

---

## 1. What Exists Today (Evidence)

### 1.1 Two independent capacity systems already run on athena

| | Agent capacity (`sase-z4`) | Suite gate (pre-existing) |
|---|---|---|
| Governs | how many agents may be *live* | how many pytest xdist workers may run |
| Unit | fractional "capacity units" | integer worker tokens |
| Budget | `max_running_agents: 10` (config) | computed from CPU+RAM, capped at 32 |
| Store | agent artifact dirs + `runner_slots.lock` | `/tmp/sase-pytest-tokens-<uid>/` flocks |
| Policy | Rust `runner_capacity.rs` (priority, FIFO, deference) | Python `WorkerTokenLease` (opportunistic grab) |
| On contention | park the agent, publish a queue marker | **block** with a status line every 30s |
| Crash safety | PID liveness probe | flock + heartbeat + watchdog reclaim |

Measured on athena right now: 64 CPUs, 64 GiB RAM, `MemAvailable` 34.9 GiB, load average
15.5. `_calculate_default_token_budget` therefore yields
`min(64 − 8, (34.9 GiB − 8 GiB) / 700 MiB, 32) = min(56, 36, 32) = **32**` — and the live
pool directory confirms it: 32 `token-NNN.lock` files plus `pool.lock`.

**That is the same number Bryan independently picked for athena's agent capacity.** This
is not a coincidence worth ignoring: it says the natural capacity unit is "one busy
worker" — roughly one core plus ~700 MiB, the figure `_suite_gate_budget.py` derived from
measured worker RSS (phase `sase-ib.5`: peak 500,632 KiB/worker, 700 MiB reserved for
~40% headroom). Adopt that definition and both systems can share one ledger.

### 1.2 What the heavy commands actually cost

- **Full suite, serial:** 7,412.7 s ≈ **123.5 worker-minutes** across 3,513 measured
  files (`tests/shard_timings.json`, generated 2026-09-05 on apollo).
- **`decisions:two-speed-verification`:** ~61 worker-minutes per full-suite run; the host
  admits ~200–400 such runs/day against ~46,000 worker-minutes of gated capacity — "the
  full suite alone can consume a quarter to a half of the machine's entire capacity,
  continuously."
- **`just check-full`'s `test-cost` stage alone:** ~38k items / **~90 minutes**
  uncontended (bead `sase-x4`).
- **Granted width for a governed full run on athena:** `automatic_worker_range(32)` =
  floor 4, ceiling `min(28, max(4, min(28,32)//2))` = **14**.

So a `check-full` agent really does occupy about **15 units** (1 agent + up to 14
workers). Bryan's intuition of "+15 → 16" is within one unit of the number the existing
code already computes. That is the strongest possible argument that the number should be
*derived*, not authored.

### 1.3 `just check` is not one workload — it is three, and it escalates often

From the live selection-health store (`~/.sase/test-selection/sase/`, 16 scoped runs):

| outcome | count | duration | width |
|---|---|---|---|
| escalated to the governed full lane | **10 / 16 (62%)** | (full lane cost) | 4–14 |
| ran scoped at middle-gear width 4 | 4 | 146 s – 1,337 s | 4 |
| ran scoped serial | 2 | 652 s | 1 |

Every escalation fired on a *change-set* rule — `justfile`, `src-data-asset`,
`contract-set-only`, `core-identity-changed`, `packaging-config` — all of which are known
from the diff **before a single test runs**. That matters enormously for Bryan's question
about a dynamic weight for `just check`: the information needed to size the claim is
already computed, already persisted to a manifest, and already used to pick a width. A
static weight for `just check` would be wrong roughly two runs in three.

### 1.4 The lease machinery this feature would inherit is already limping

- **`sase-x4` (OPEN, large):** `just check-full` hangs silently at `test-cost`; a cost
  lease holder heartbeated for 2 h 1 m, then went silent for 2 h 53 m, and the holder
  watchdog never self-reclaimed. The host-wide gate stayed wedged.
- **`sase-w7`:** a deterministic failing test of the same stale-live-holder reclaim path.
- **Observed now:** `/tmp/sase-pytest-tokens-1000/` holds **311 leftover `.progress`
  sidecars** dated 2026-09-05 through 2026-09-11 — graceful release cleans up, crash
  release does not.

Design conclusion, stated early because it drives everything: **liveness must be proved
by something the kernel enforces, not by a heartbeat a wedged process stops writing.**
`flock` on a per-claim file is that thing; it is released by process death, unconditionally.

### 1.5 The Rust policy refuses dynamic weight today

`crates/sase_core/src/runner_capacity.rs`, `build_candidate_decision()`:

```rust
} else if let Some(claim) = active_claim {
    let active_weight = claim.occupied_capacity;
    if candidate.queue_weight_explicit && !weights_equal(requested_weight, active_weight) {
        blockers.push(blocker("active-claim-weight-conflict",
            "Serial continuation requested a different explicit weight than its active lineage claim.", …));
        decision = "invalid".to_string();
```

An agent that already holds 1.0 and asks for 16.0 gets `invalid`. There is no amend path.
And `waiter_blockers()` has no reservation concept at all: the only capacity blockers are
`weight-exceeds-limit` (weight > C) and `insufficient-capacity` (weight > C − occupied).
Ordering affects *display bucket* and *deference* only.

### 1.6 The UI as it stands

- `agent_info_panel.py:379` `_append_capacity_prefix` renders `0.0/10.0` — always with a
  forced decimal, because `format_capacity_value(..., minimum_decimal=True)` appends
  `.0`.
- `_fleet_header.py:45` builds `here: athena · 7 active · 1 machine · apollo unknown`,
  right-aligned in `#agents-fleet-status` (`width: 1fr; content-align: right middle`).
- The agents-pane **PNG golden corpus is already stale** from `sase-z4.4`: 44 failed / 12
  passed on a 12-file subset, every diff confined to that one status-strip row (noted on
  `sase-z4` and `sase-z4.6.5`). Any change here must regenerate goldens deliberately —
  which is an argument for doing the UI change *once*, now, with this work.

---

## 2. Critique: Should Bryan Build This At All?

### 2.1 Yes — because the alternative is a memory note

`decisions:two-speed-verification` is unusual among the decision records: it is the only
one whose enforcement mechanism is *prose in an agent's context window*. "An agent that
'just runs the full suite to be safe' is not being careful; it is taking capacity from
every sibling workspace." That sentence exists because nothing stops the agent. Every
downstream symptom the record lists — long gate waits, contention flakes, the
`test-visual-contention` baselines needing a 26-worker/2-CPU harness to reproduce real
failures — is a symptom of unpriced demand.

`sase tool` prices it. That is a genuine architectural improvement, not a nicety.

Secondary benefit that is easy to undersell: **it makes the capacity rescale safe.** Going
from `max_running_agents: 10` to capacity 32 is only sane if heavy work self-declares. A
flat cap of 32 agents with no tool accounting would be strictly worse than today. The two
halves of this proposal are load-bearing for each other, and neither should ship alone.

### 2.2 But four things in the proposal are wrong as stated

**(a) It duplicates the suite gate.** If `just check-full` claims 15 agent-capacity units
*and* 14 suite-gate tokens, athena has two ledgers describing the same 64 cores, with
different arithmetic, different crash semantics, and different waiting behavior. Every
future bug in this area becomes "which one was right?". This is the single biggest
architectural risk and the easiest to avoid.

**(b) It asks an agent to wait.** `decisions:single-turn-agents` and
`decisions:gates-never-block` are explicit: a SASE agent run is one provider turn, and
continuation is always mechanical. "The agent should be presented with two choices:
1) Queue itself…" has no mechanism behind it unless the agent ends its turn. It already
has one: `sase monitor start -s TESTING -S TESTED -- just check-full` is *already* the
mandated way to run `check-full`, it already ends the turn, the supervisor is already
detached, and the monitor already bridges family liveness so the claim is held across the
handoff. The queue is a solved problem wearing a different name.

**(c) Fixed weights do not survive the fleet.** `+15` on athena (C=32) is a fair share.
On apollo (C=8) it is `weight-exceeds-limit` — the claim can *never* be satisfied, at any
time, so `just check-full` on apollo would be permanently refused and every agent would
learn to pass `--force`. On mac (C=4) likewise. The moment `--force` becomes habitual the
feature is dead. Weights must clamp.

**(d) Starvation is not a tail risk here; it is the default.** With C=32 and a steady
population of weight-1 agents, a weight-15 claim needs 15 simultaneous free units. Without
a reservation rule, the probability of that gap appearing falls off a cliff as the machine
fills, and the heavy claim waits behind arbitrarily many light ones. This is the classic
HPC problem; Slurm answers it with FIFO + backfill + reservations. SASE has the FIFO
ordering already (`runner_slot_waiter_sort_key`) and uses it for *display*; it needs it for
*admission*.

### 2.3 The social failure mode is the one that actually kills it

Every capacity system dies the same way: the escape hatch becomes the norm. If `just
check` — the command every agent is told to run before finishing its turn — can *fail*
because the machine is busy, then within a week every agent prompt will contain
`--force`, and the ledger will describe a fiction.

The rule that prevents this is a policy split, not a technical one:

> **`just check` degrades. `just check-full` queues.**

`just check` must always run, at whatever width it can get, down to serial at weight 1.
That is not a compromise — it is *exactly* what the middle gear already does
(`tests/_test_selection_gear.py`: "It never queues… a grant that is not available right
now is not taken"). Only `check-full` (and the deliberate host-starving harnesses) should
ever refuse.

### 2.4 Sequencing concern

`sase-z4.6.5.4` is still `IN_PROGRESS`; the agents-pane PNG corpus is red on clean master
from `sase-z4.4`'s status-strip change. Landing a *new* status-strip design on top of an
unaccepted one compounds that debt. Recommendation: treat the `<L>/<C>` meter as the
change that **settles the final status-strip text and regenerates the corpus once**, and
land it either inside the remaining `sase-z4` acceptance or immediately after it closes —
not in parallel with it.

---

## 3. Recommended Architecture

### 3.1 One unit, one ledger

> **A capacity unit is one busy worker: ~1 CPU and ~700 MiB.** An agent that is thinking,
> reading, and editing costs **1**. A command that will run N parallel workers costs **N**
> for as long as it runs. A machine's capacity is how many busy workers it can host.

This definition is already implicit in `_suite_gate_budget.py`. Making it explicit gives
every number in this design a derivation instead of a vibe, and it explains athena=32
(its measured worker budget) without hand-waving.

All claims — agent claims and tool claims — live in **one ledger**, evaluated by **one
policy** in `sase_core`. The pytest token pool becomes a consumer of that ledger rather
than a peer of it.

### 3.2 Tool claims are records, not weight mutations

Do **not** amend the agent's `queue_weight`. That path is blocked by
`active-claim-weight-conflict`, and unblocking it would entangle dynamic demand with the
lineage/inheritance rules that `sase-z4.6.5.1` just spent a phase making authoritative.

Instead add a second record kind to the capacity request:

```rust
pub struct ToolClaimWire {
    pub claim_id: String,        // ulid
    pub label: String,           // "just check-full"
    pub profile: Option<String>, // "check-full"
    pub weight: f64,             // granted units (NOT including the agent's own 1.0)
    pub pid: i64,
    pub live: bool,              // flock-derived, computed by the Python scanner
    pub owner_artifact_dir: Option<String>, // the agent that holds it, for display
    pub started_at: String,
    pub expires_at: Option<String>,
    pub forced: bool,            // admitted via --force; never counted as consent
}
```

`RunnerCapacityRequestWire` gains `tool_claims: Vec<ToolClaimWire>` (schema bump; the wire
uses `deny_unknown_fields`). Occupancy becomes `Σ agent claims + Σ live tool claims`.
Nothing about lineage, serial families, or inheritance changes. `sase tool` acquires and
releases *its own* record and never touches the agent's.

This is strictly simpler than mutating weights, and it gives the UI something it otherwise
could not have: the ability to say *which* claims are heavy work versus agents (§5.3).

### 3.3 Crash safety: flock, not heartbeats

Each claim is a file in `$SASE_HOME/tool_claims/<claim_id>.json`, held open with an
exclusive `flock` for the command's lifetime.

- **Release** = close the FD. The kernel guarantees it, including on `SIGKILL`, OOM-kill,
  and a wedged-but-alive parent being killed by a monitor timeout.
- **Liveness** = a reader can `flock(LOCK_EX|LOCK_NB)` the file. Success means the holder
  is gone ⇒ ignore the record and unlink it.
- **Second belt** = `expires_at` (default 4 h, configurable, `check-full` gets 6 h). A
  claim past TTL is ignored even if the flock is somehow still held.
- **No heartbeats.** `sase-x4` is precisely the failure mode where a process is alive,
  holding the resource, and not heartbeating; the watchdog then has to decide whether to
  steal from a live process, which it got wrong. flock never has to make that judgment.

Inherit the *good* parts of `WorkerTokenLease`: `make_inheritable()` + `execv` so the
claim survives the wrapper handing off to the real command, and the PID-guarded adopt
logic that stops xdist children from releasing their controller's grant.

### 3.4 Re-entrancy: claim once, wherever the claim is made

`tools/run_pytest` already solves this with `descendant_exemption()` — "An ancestor's lease
already paid for this width." Reuse the pattern: `sase tool` exports
`SASE_TOOL_CLAIM_ID` / `SASE_TOOL_CLAIM_WEIGHT`; a nested `sase tool` for the same profile
is a no-op pass-through, and a nested one for a *larger* profile upgrades in place rather
than stacking.

This is what makes the next decision safe.

### 3.5 Where the wrapping actually goes — and this is a deviation from the ask

The request says "wrap all of the `just` commands listed at the top of
`sase/memory/lint_and_test.md` using the `sase tool` command." I read two possible
meanings and recommend the second:

- **(a) Agents type `sase tool run -- just check`.** Call-site discipline. Works right up
  until an agent forgets, CI doesn't, a human doesn't, and the ledger silently
  under-counts. It also adds a fourth command-wrapping verb to a CLI that already has
  `monitor`, `proc`, and `gate`.
- **(b) The recipes claim internally, and `sase tool` is the primitive plus the escape
  hatch.** `just check` is unchanged at the call site. `tools/run_pytest` already holds a
  lease; it swaps `WorkerTokenLease` for the shared ledger. The lint-only stages get a
  small `tools/claim` shim. Every caller — agent, human, CI, monitor — is accounted for
  with no discipline required.

**Recommend (b)**, with (a) fully supported because the claim is re-entrant. `sase tool`
remains a real, documented, first-class command — it is how *non-`just`* slow work gets
priced (`sase tool run -- cargo build --release`, `sase tool run -- vhs demos/…`), how an
agent inspects the ledger, and how `--force` is expressed. But the twelve commands in
`lint_and_test.md` should not require an agent to remember a prefix, because the failure
mode of forgetting is invisible.

Practical consequence: `sase/memory/lint_and_test.md` needs **no new prefix instruction**,
only a short paragraph explaining that `check`/`check-full` are now priced and what a
refusal means. That is a better memory note than one that adds a ritual.

---

## 4. The `sase tool` Interface

### 4.1 Surface

Following `memory:cli_rules` — options are never required, required values are
positionals, every long option has a short alias, subcommands sorted:

```
sase tool list                  # registered profiles, weights, and current holders
sase tool run [opts] -- CMD…    # run CMD under a capacity claim
sase tool show <profile>        # one profile's floor/ceiling/TTL and its rationale
sase tool status                # live ledger: who holds what, and for how long
```

`sase tool` bare delegates to `list` per the default-`list` convention in
`_default_list_subcommands()`.

```
sase tool run options:
  -f, --force        Run now, over capacity. Audited, surfaced in ACE, and recorded on
                     the claim as forced=true.
  -l, --label TEXT   Row label for `sase tool status` and the ACE meter tooltip.
  -n, --dry-run      Print the claim that would be made and exit 0.
  -p, --profile NAME Use a named weight profile instead of inferring from the command.
  -q, --queue        Do not run now; hand this turn to a monitor that waits for capacity.
  -t, --timeout DUR  Max hold before the claim self-expires (default: profile's TTL).
  -w, --weight N     Exact units. Overrides the profile's (floor, ceiling).
```

**On `--` and `-f`:** the concern in the request — that `-f` could be swallowed by the
wrapped command — is fully answered by the `--` separator, which `sase monitor start`
already uses. Everything before `--` belongs to `sase tool`; everything after is the
command, verbatim. No `-- -f` gymnastics needed. Positional `--` is also what
`memory:cli_rules` implies: the required value (the command) is a positional.

### 4.2 The refusal message is the feature

Most of this design's value is realized or destroyed in one error message. It must be
specific, honest about *who* is holding capacity, and copy-pasteable:

```
✗ not enough capacity on athena for `just check-full`

  needs   15 units (1 agent + up to 14 test workers)
  free     6 units        held 26 / 32

  who is holding it
    9.0   9 agents
   13.0   just check-full   sase-zk.3      1h04m   (expires in 4h56m)
    4.0   just check        sase-zm.1      3m11s

  your options
    queue it   (ends this turn; a monitor waits, then runs it)
      sase monitor start -s TESTING -S TESTED -- just check-full

    force it   (oversubscribes athena; other agents will slow down)
      sase tool run -f -- just check-full

    watch it   sase tool status --follow
```

Three deliberate choices: the queue option is listed **first** and is a command that
already exists; `--force` names its cost in the same breath; and the holders are named so
"the machine is busy" is falsifiable rather than a shrug.

### 4.3 Queueing = the monitor, not a new waiter

`sase monitor start` gains capacity awareness:

1. The CLI resolves the profile for the command it was handed (`just check-full` →
   profile `check-full`).
2. The **detached supervisor** — not the agent — acquires the claim, blocking with the
   existing waiting/timeout message shape borrowed from `_suite_gate_messages.py`.
3. On grant it `execv`s the command with the claim FD inherited; on release it unlinks.
4. The agent's turn already ended at step 1. Nothing blocks.

`sase tool run -q/--queue` is sugar for the same thing, so an agent that reached for
`sase tool` first is redirected without a second concept.

Why this is strictly better than a new queue: the monitor already owns the command's
process group, already streams output, already has a timeout, already supports a follow-up
agent (`-n`), already appears in ACE as a family member, and — critically — the family's
own claim already survives the handoff. A new waiting primitive would have to re-derive
every one of those.

### 4.4 Starvation: aging reservations (required, not optional)

Add to `waiter_blockers()`:

> A waiter whose *only* capacity blocker is `insufficient-capacity`, and whose
> `slot_requested_at` is older than `reservation_after_seconds` (default 120), becomes a
> **reserving waiter**. Its shortfall is subtracted from free capacity when evaluating any
> *lighter* candidate, which is then blocked with a new `capacity-reserved` blocker.
> Reservations are capped at `reservation_max_seconds` (default 1800) and at most one
> reservation is active at a time (the oldest, highest-priority waiter wins).

Properties worth stating: it is bounded (a bug cannot wedge the host past 30 minutes); it
is fair (FIFO + existing priority ordering decides who reserves); it needs no duration
estimates; and it fixes a latent bug that already exists for `%q(w=2)` landers today,
independent of `sase tool`.

The blocker code is also a UI affordance: an agent refused with `capacity-reserved` gets a
*different, better* message — "`just check-full` (sase-zk.3) is waiting for 15 units;
you'd jump the queue" — which is the honest reason and discourages `--force` far more
effectively than "machine busy".

### 4.5 Compatibility with the suite gate — the phased trick

Do **not** try to migrate the suite gate in the same change. Instead:

- **Phase 1.** `sase tool`/`run_pytest` sets `SASE_TEST_GATE_GOVERNED_BY=sase-tool:<id>`
  plus an exact `SASE_PYTEST_WORKERS=<granted>`. `tools/run_pytest` treats that exactly
  like today's `descendant_exemption()`: the ancestor already paid, take no tokens, skip
  the "ungoverned run" warning. **One accounting authority from day one, no pool
  migration.**
- **Phase 2.** Delete the `/tmp` token pool and its budget computation; the ledger's
  clamp-to-capacity grant replaces `fit_request_to_budget`, and `tests/_suite_gate*.py`
  collapses to a thin adapter. This also retires `sase-x4`'s and `sase-w7`'s reclaim path
  by deleting it.

Phase 1 is small and reversible; Phase 2 removes ~1,500 lines and an open bug class.

---

## 5. Weights

### 5.1 Express demand as a range, not a scalar

Every profile declares `floor` (below which the command is not worth running in parallel),
`ceiling` (the widest it can usefully go), and `ttl`. The granted weight is

```
granted = clamp(ceiling, floor, capacity − reserve)      # reserve defaults to 1 unit
effective_workers = granted            # the command runs at exactly the width it paid for
```

This single rule gives Bryan three things at once: the machine-relative behavior apollo
and mac need, the "no unaccounted demand" property the suite gate exists to enforce, and
the elimination of the magic number — `check-full`'s "15" is `automatic_worker_range(32)`'s
ceiling, not an authored constant.

### 5.2 Recommended profile table

Weights below are the **claim including the running agent's own 1.0**, evaluated on athena
(C=32). The `(floor, ceiling)` column is what actually ships.

| command | (floor, ceiling) | athena claim | apollo (C=8) | mac (C=4) | basis |
|---|---|---|---|---|---|
| `just install` | (2, 2) | 2 | 2 | 2 | uv/pip: network + disk, briefly parallel |
| `just fmt` / `just fix` | (1, 2) | 2 | 2 | 2 | ruff-format + prettier; seconds |
| `just lint` | (2, 4) | 4 | 4 | 3 | mypy is the long pole; ruff parallelizes |
| `just check` | **adaptive** | 2 → 5 | 2 → 4 | 2 → 3 | §5.3 |
| `just check-full` | (5, 15) | **15** | 7 | 3 | 1 + `automatic_worker_range` ceiling 14 |
| `just test` | (5, 15) | 15 | 7 | 3 | same lane as check-full's suite |
| `just test-cov` | (5, 13) | 13 | 7 | 3 | coverage adds ~30–50% RSS/worker |
| `just test-visual` | (5, 13) | 13 | 7 | 3 | Pillow rasterization is memory-bound |
| `just test-scoped` | adaptive | 2 → 5 | 2 → 4 | 2 → 3 | today's middle gear, generalized |
| `just test-slow` | (3, 9) | 9 | 5 | 3 | smaller item count, long tails |
| `just demos` | (4, 4) | 4 | — | — | five `vhs` renders, CPU-bound |
| `just rust-check` / `rust-test` | (4, 9) | 9 | 5 | 3 | **not in the memory note today, and the single hungriest job in the tree** — `cargo` fans out to `nproc` by default |
| `just test-contention` / `test-visual-contention` | (C−1, C−1) | 31 | 7 | 3 | the Justfile says outright that it "starves the host on purpose" |

Three notes on this table:

- **`just check-full` = 15 validates Bryan's number** and, better, derives it. If athena's
  worker budget changes (more RAM, a resize), the claim tracks it automatically.
- **`just rust-*` is the biggest gap in the current memory note.** `cargo build` of
  `sase_core` will happily consume every core and is invisible to both existing ledgers.
  Recommend adding it to `lint_and_test.md` and to the profile table in the same change.
- **The contention harnesses should claim `C−1`.** They currently rely on the operator
  knowing not to run them on a shared host; the Justfile comment even says so. Pricing
  them is a one-line win.

### 5.3 `just check`: adaptive, and the data is already there

This is the part of the request that deserves the most design, and the answer is that the
machinery already exists — it just needs to be given a budget instead of a token pool.

Today's `test-scoped` has three gears: serial (no lease), middle gear (one non-blocking
try for ≤4 tokens), and escalate-to-full-lane. Generalize to four, keyed on the selection
manifest that is computed *before any test runs*:

| stage | claim | when |
|---|---|---|
| 1. lint gates | **2** | always; held for the fmt/ruff/mypy/symvision/toobig block |
| 2a. selection empty / tiny | **2** (unchanged) | `selected_count` small, projected serial seconds under budget |
| 2b. serial-budget exceeded | try to upgrade to **2 + min(4, free)**; take what's offered | today's middle gear, but the width is the grant |
| 2c. change-set rule escalated | try to upgrade to the `check-full` profile; **if refused, fall back to 2b** | the 62% case |

The three properties that make this safe:

1. **It reads `tools/select_tests` output, which is free.** The manifest already carries
   `selected_count`, `max_serial_seconds`, `timings`, `rules_fired`, and `escalated`.
   Nothing new needs to be measured.
2. **Upgrades never fail the run.** A refused upgrade degrades the width; it does not
   raise. This is the `just check` degrades / `check-full` queues split from §2.3, and it
   is the difference between a feature agents trust and one they route around.
3. **Every outcome is already recorded.** `manifest_with_gear()` writes the granted width
   and the refusal reason to the health store, so `just selection-health` can report how
   often the budget bound `just check` — turning "what weight should check get?" into a
   question with an ongoing answer rather than a one-time guess.

One refinement worth taking: when stage 2c escalates, prefer to **queue via monitor rather
than silently degrade** if the change-set rule was `contract-set-only` or
`core-identity-changed` — those are the rules that mean "this diff really does need the
full suite", and running a degraded scoped lane instead is a correctness risk, not just a
slower run. Emit a clear line telling the agent to re-run under a monitor.

### 5.4 Removing the authored presets

**Epic lander `%q(w=2.0)` (`default_config.yml:1562`) — remove. Unambiguously correct.**
The 2.0 existed as a proxy for "landers run `check-full`". With `check-full` self-pricing
at 15, the proxy is both wrong (too small by 7×) and redundant.

**Research swarm `%q(w=0.25)` — remove, with a caveat worth recording.**

The arithmetic works out neutral:

| | old (C=10) | new (C=32) |
|---|---|---|
| 4 swarm members | 4 × 0.25 = 1.0 unit = **10%** of the machine | 4 × 1.0 = 4 units = **12.5%** |

So the capacity rescale absorbs the removal almost exactly. The caveat: a research agent
is provider-bound — it waits on network and reads files — and under "1 unit = 1 busy
worker" it genuinely costs less than 1. Removing 0.25 is a real, if small, systematic
over-count of provider-bound work.

Recommendation: remove the hard-coded 0.25 (it duplicates what `sase tool` now measures
and it was authored as a guess), but **keep the `%q(w=…)` mechanism** and treat any future
number as a *class* default on the xprompt, revisited with data from `sase tool status`
rather than intuition. If the fleet later grows genuinely idle agent classes, the honest
fix is a second, lower baseline for provider-bound agents — not scattering fractions
through xprompts.

---

## 6. Required Machine Capacity At `sase init`

### 6.1 Follow the machine-name pattern exactly

`config_init_handler.py` is a good template and Bryan's instinct to reuse it is right. The
pattern is: compute a suggestion → prompt with it in brackets → validate → write to the
machine overlay → surface drift through `InitPlan` actions so `sase init --check` and
`sase doctor` both report it.

```
Existing machine names: athena, apollo
Machine name [athena]: athena

Machine capacity is how many busy workers this machine can host. One ordinary agent
costs 1 unit; `just check-full` costs about 15. athena has 64 CPUs and 64 GiB RAM,
so a computed budget is 32.

Machine capacity [32]: 32
```

The suggestion should be `_calculate_default_token_budget(cpu_count, mem_available_kib)` —
the *same function* that sizes the pytest pool. On athena that prints 32 with no tuning;
on apollo (4 vCPU / 8 GiB, per `202609/temporary_high_capacity_test_machine.md`) it prints
~4, and Bryan's chosen 8 is a deliberate 2× oversubscription that the prompt should accept
without argument. That is correct: capacity is a *policy* informed by hardware, not a
hardware readout. The prompt's job is to make the hardware-derived number free and the
override one keystroke.

### 6.2 Register it as an init step, not a hard runtime requirement

Add it to `iter_init_command_specs()` — either as a second action inside the existing
`config` spec (preferred: it is owner/machine identity) or as a new `capacity` spec.

**Do not make `require_machine_capacity()` raise at admission time.** Machine name can
raise because an agent without an identity cannot be named at all; capacity has a safe,
computable fallback. A fresh or partially-migrated machine should keep working with the
computed default and be *loudly* marked as uninitialized:

- `sase init --check` → an action: "athena has no declared capacity (using computed 32)".
- `sase doctor` → WARN, with the exact `sase init config` next step.
- ACE meter (§7) → the denominator renders dim-italic with a `~` prefix: `8/~32`.

That last one is the good part: "your capacity is a guess" becomes visible in the place
Bryan looks every day, which is a much stronger forcing function than a startup error and
cannot brick a machine.

### 6.3 Report capacity across the fleet

`machines_pane_rendering.py:_capacity_label()` currently returns `"not reported"` for every
remote machine. Since §7 deletes the fleet text from the Agents tab, its information needs
a better home, and this is it: have each machine report `{capacity, load, tool_claims}` in
its hello/status payload so the Machines pane shows `apollo 3/8`, `mac offline`,
`athena 17/32` — real fleet capacity instead of a placeholder. This turns the header
removal from a loss into an upgrade.

### 6.4 On the config key

`max_running_agents` is now a misnomer — it is not a count of agents. I'd rename to
`machine_capacity` with `max_running_agents` retained as a deprecated alias (there are
~20 Python call sites, the JSON schema, the ACE editor modal, and docs). This is genuine
clarity but low urgency; it is a fine candidate to defer to a follow-up task rather than
bundle into an already-large epic. Also note the accessor validates `type(value) is int`,
so a fractional *capacity* is rejected today even though fractional *weights* are
accepted — worth relaxing to a positive finite float for symmetry.

---

## 7. The `<L>/<C>` Indicator

### 7.1 What to delete, and what must not be lost

Delete `_append_capacity_prefix` from `agent_info_panel.py` (the duplicate), and replace
`_unified_agents_status_text()` in `_fleet_header.py`. But that string carries four things,
and two of them are load-bearing:

| element | keep? | where it goes |
|---|---|---|
| `here: athena` | conditionally | shown only when >1 machine is enrolled |
| `7 active` | no | already in the info-panel bracket (`N running`) |
| `1 machine` | no | Machines pane (§6.3) |
| `apollo unknown` | **yes — this is a health signal** | collapses to a `⚠` glyph on the meter; full text in the tooltip / on click |

Silently dropping a machine-health diagnostic to make room for a number would be a
regression. One amber glyph costs 2 cells and keeps it.

### 7.2 The meter

Right-aligned in `#agents-fleet-status`, ~24–28 cells:

```
athena  ████▓▓▓▓▓▓▓▓░░░░  17/32
```

Reading it: **bar for pressure, number for precision, rightmost is most precise.** The
segmented bar answers "how full?" in peripheral vision; the numbers answer "exactly how
full?" when you look.

Design details, each doing a specific job:

- **Two-tone fill is the point.** `█` = agent claims, `▓` = tool claims, `░` = free. This
  makes the one question the new feature creates — *why* is the machine full? — answerable
  without opening anything. `████░░░░░░░░ 4/32` (four agents, idle box) and
  `████▓▓▓▓▓▓▓▓░░░░ 17/32` (four agents plus a `check-full`) read completely differently at
  a glance, which is exactly right. It degrades to one tone when no tool claims exist.
- **Fractions get a partial block.** A load of 6.75 renders the 7th cell as `▊`. This is
  where fractional weights finally become legible instead of noisy, and it is why the bar
  earns its width.
- **Integers by default.** `format_capacity_value(..., minimum_decimal=False)` for both
  numerator and denominator: `8/32`, not `8.0/32.0`. Fractional load renders trimmed:
  `6.75/32`. The existing function already does this — only the call site's flag changes.
- **Color from the existing palette.** Reuse `_usage_indicator_palette`'s ten-bucket
  gradient (inverted: bucket from *remaining* fraction). It is already contrast-validated
  at ≥5.00:1 dark / ≥4.66:1 light, already handles light and dark themes, and reusing it
  makes the Agents tab and the provider-usage badges read as one system instead of two
  people's color choices. Do not invent a fourth palette.
- **Never color alone.** Bar length carries the same information as hue.
- **Over-capacity is loud.** `--force` can push L above C. Render the bar fully saturated
  red with a trailing `!`: `████████████ 34/32 !`. Forcing should be visible to the person
  whose machine it is.
- **Reservations are visible.** When a heavy claim is reserving (§4.4), show the reserved
  shortfall as a distinct dim hatch in the free region and append `· 1 waiting 15`. An
  agent that sees this understands why its own small claim was refused.
- **Uninitialized capacity.** `8/~32` with the denominator dim-italic (§6.2).
- **Health.** `athena ⚠ ████░░░░░░░░ 8/32`, amber `⚠` only when diagnostics exist.
- **Clickable.** Clicking opens the Machines pane. `#agents-fleet-status` is already a
  `Static` in a `Horizontal`; `AgentInfoPanel` already implements a click-to-open pattern
  (`FilterClicked`), so this is an established gesture, not a new one.
- **Tooltip** = the full old string plus the top holders: exactly the body of §4.2's "who
  is holding it" block. Nothing is lost; it is one hover away instead of permanently
  consuming a row.

Narrow-terminal degradation, in order: drop the machine name → shrink the bar 12→8→6 cells
→ drop the bar, keep `17/32`. The numbers are the last thing standing.

### 7.3 Where `queued` stays

Leave the queued count in the info-panel bracket (`[3 running · 2 queued · 1 failed]`).
Moving it to the meter would crowd the one element that must stay instantly readable, and
the bracket is already where counts live.

### 7.4 PNG goldens

This change *will* move every agents-pane golden — but they are already red from
`sase-z4.4`. Doing the regeneration once, here, with someone actually inspecting the PNGs,
is strictly better than the status quo and better than two separate regenerations. Budget
for it explicitly; do not let it become another bulk `--sase-update-visual-snapshots` by an
unrelated agent (both `sase-z4` note #3 and `sase-z4.6.5` note #1 warn about exactly that).

---

## 8. Risks And Open Questions

| risk | severity | mitigation |
|---|---|---|
| Heavy claims starved by light agents | **high, certain** | aging reservations (§4.4); ship together, not after |
| Two ledgers disagree | **high** | Phase-1 `SASE_TEST_GATE_GOVERNED_BY` exemption (§4.5) |
| `--force` becomes habitual | **high** | `just check` degrades instead of failing (§2.3); forced claims flagged in the ledger, the meter, and `sase tool status` |
| Leaked claims wedge the machine | medium | flock liveness + TTL + no heartbeats (§3.3); `sase doctor` GC of dead claim files |
| Fixed weights unusable on small machines | medium | clamp-to-capacity grant (§5.1) |
| Weights are advisory; non-SASE processes are invisible | medium | a `sase doctor` check comparing claimed load to 1-minute load average — athena is at 15.5 right now with a nominal ledger that knows nothing about it; drift is worth a WARN |
| Landing on unaccepted `sase-z4` work | medium | sequence after `sase-z4.6.5.4`; make the meter the change that settles the strip and regenerates goldens (§2.4) |
| `/tmp` pressure | low but present | `/tmp` is a 32 GiB tmpfs at 94% on athena today; the claim directory belongs in `$SASE_HOME`, not `/tmp` |

**Open questions for Bryan.**

1. **Should capacity be one dimension or two?** Everything above collapses CPU and memory
   into one scalar. `_suite_gate_budget` already computes both and takes the `min`, so a
   memory-heavy/CPU-light command (`test-visual`) is mispriced. One scalar is the right
   *first* answer — two-dimensional bin packing is a large step up in complexity for a
   single-user fleet — but it is the first thing to revisit if visual-lane contention
   persists.
2. **Does `just check-full` want a *fixed* fair share or the whole machine when idle?**
   The current `_DEFAULT_AUTOMATIC_FAIR_SHARE_RUNS = 2` reserves room for a second
   concurrent run. With a real ledger you could instead grant greedily and release, which
   would make a lone `check-full` on an idle athena roughly 2× faster. That is attractive
   but requires shrinking a live claim, which is the one thing flock-held tokens make
   awkward. Recommend keeping fair-share for v1.
3. **Should a forced claim be allowed to exceed capacity, or only to jump the queue?** I
   recommend allowing genuine over-capacity (the operator sometimes knows the holders are
   idle) but rendering it as an alarm state, never as normal.
4. **How does a *remote* agent's tool claim reach athena's ledger?** Out of scope here,
   but once §6.3 reports capacity across the fleet, the natural next question is whether
   dispatch should consider remote load. Worth a note, not a phase.

---

## 9. Recommended Solution

Build it, in this order. Each phase is independently landable and independently useful.

**Phase 0 — finish `sase-z4` acceptance.** Close `sase-z4.6.5.4`. Do not start the meter
work in parallel with the stale-golden repair.

**Phase 1 — capacity, declared and derived (Rust + config + init).**
Add `capacity` to `sase init config` with a computed suggestion from
`_calculate_default_token_budget`; write it to the machine overlay; report drift through
`InitPlan`/`sase doctor`; keep the computed fallback at runtime and mark it as a guess in
the UI. Set athena 32, apollo 8, mac 4. Relax the accessor to a positive finite float.
*No behavior change for agents.*

**Phase 2 — the ledger and the claim primitive (Rust core + `sase tool`).**
`ToolClaimWire` + `tool_claims` on the capacity request (schema bump); occupancy includes
live tool claims; **aging reservations with `capacity-reserved`**; flock-backed claim files
in `$SASE_HOME/tool_claims/`; `sase tool list|run|show|status` with `-f/--force` after
`--`; the refusal message from §4.2.

**Phase 3 — the monitor is the queue.**
`sase monitor start` resolves a profile and has the *supervisor* acquire the claim,
blocking with a suite-gate-style waiting message. `sase tool run -q` is sugar for the same
handoff. This is what makes "queue yourself" a real option instead of a suggestion.

**Phase 4 — price the real workloads.**
Profile table from §5.2 in config. `tools/run_pytest` claims through the ledger and takes
the `SASE_TEST_GATE_GOVERNED_BY` exemption so nothing is double-counted. `just check`
becomes adaptive per §5.3 and **never fails on a busy host**. Add `just rust-*` and the
contention harnesses to the table and to `lint_and_test.md`. Remove `%q(w=2.0)` from the
lander and `%q(w=0.25)` from the research swarm.

**Phase 5 — the meter.**
Replace `_unified_agents_status_text` with the two-tone capacity meter; delete
`_append_capacity_prefix`; flip `minimum_decimal=False`; reuse
`_usage_indicator_palette`; preserve machine health as a `⚠` glyph; click opens the
Machines pane; report capacity+load across the fleet so the Machines pane shows real
per-machine numbers. Regenerate the PNG corpus once, deliberately, inspecting the diffs.

**Phase 6 (follow-up, not epic scope).**
Retire the `/tmp` token pool and collapse `tests/_suite_gate*.py` to an adapter — which
also closes `sase-x4` and `sase-w7` by deleting their code path. Rename
`max_running_agents` → `machine_capacity` with an alias.

**What I changed from the request, and why, in one list:**

1. The recipes claim internally; `sase tool` is the primitive and the escape hatch, not a
   prefix agents must remember. *(Forgetting a prefix is an invisible failure.)*
2. `sase monitor` is the queue; `sase tool` never waits. *(Agents are single-turn.)*
3. Weights are `(floor, ceiling)` clamped to machine capacity, not scalars. *(15 is
   unsatisfiable on apollo and mac.)*
4. `just check` degrades to a narrower width; only `check-full` refuses. *(Otherwise
   `--force` becomes the default and the ledger becomes fiction.)*
5. Aging reservations ship with the feature. *(Without them, heavy claims are starved by
   construction, and this is already a latent bug for `%q(w=2)`.)*
6. The fleet header's *health* content is preserved as a glyph, and its *machine* content
   moves to a Machines pane that finally reports real per-machine capacity. *(Deleting a
   health signal to make room for a number is a regression.)*
7. `check-full`'s weight is derived from `automatic_worker_range`, not authored — which
   happens to produce 15, validating the original intuition while making it
   self-maintaining.

---

## Appendix: Evidence Index

| claim | source |
|---|---|
| athena suite-gate budget is 32 | `tests/_suite_gate_budget.py`; 32 `token-*.lock` in `/tmp/sase-pytest-tokens-1000/`; `nproc`=64, `MemAvailable`=34.9 GiB |
| governed full run gets 4–14 workers | `automatic_worker_range(32)`, `_DEFAULT_AUTOMATIC_CEILING=28`, `_DEFAULT_AUTOMATIC_FAIR_SHARE_RUNS=2` |
| full suite ≈ 123.5 worker-minutes | `tests/shard_timings.json` (3,513 files, 2026-09-05, apollo) |
| ~61 worker-min/run; ~46,000 worker-min/day capacity | `sase/memory/decisions/two-speed-verification.md` |
| `test-cost` ≈ 38k items / ~90 min uncontended | bead `sase-x4` |
| 62% of local `just check` runs escalated | `~/.sase/test-selection/sase/`, 16 scoped records |
| middle gear: non-blocking, ≤4 tokens, records its grant | `tests/_test_selection_gear.py` |
| dynamic weight is rejected today | `crates/sase_core/src/runner_capacity.rs` `build_candidate_decision` → `active-claim-weight-conflict` |
| no head-of-line reservation | `crates/sase_core/src/runner_capacity.rs` `waiter_blockers` |
| heartbeat reclaim is already broken | beads `sase-x4`, `sase-w7`; 311 stale `.progress` sidecars in the pool dir |
| re-entrancy precedent | `tools/run_pytest` `descendant_exemption()`; `SASE_TEST_GATE_DISABLED` |
| `0.0/10.0` forced decimal | `agent_info_panel.py:379` + `format_capacity_value(minimum_decimal=True)` |
| fleet header string | `src/sase/ace/tui/actions/agents/_fleet_header.py:45` |
| PNG corpus stale from `sase-z4.4` | `sase-z4` note #3; `sase-z4.6.5` note #1 |
| machine-name init pattern | `src/sase/main/config_init_handler.py:161` `_prompt_machine_name` |
| remote capacity unreported | `machines_pane_rendering.py:_capacity_label` |
| lander weight 2.0 | `src/sase/default_config.yml:1562` |
| apollo = 4 vCPU / 8 GiB | `research:202609/temporary_high_capacity_test_machine.md` |
| CLI conventions | `sase memory read cli_rules.md` |
| agents are single-turn; gates never block | `decisions:single-turn-agents`, `decisions:gates-never-block` |
| core backend belongs in `sase-core` | core memory `rust_core_backend_boundary` |
