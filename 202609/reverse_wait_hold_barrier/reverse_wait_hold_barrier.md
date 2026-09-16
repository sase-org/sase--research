# `%sink` — a reverse-`%wait` admission barrier (consolidated)

**Date:** 2026-09-15
**Inputs:** independent reports A (`reverse_wait_hold_barrier__a.md`, "durable
admission fence" design) and B (`reverse_wait_hold_barrier__b.md`, "hold record
store" design), plus lead-researcher verification of every load-bearing code claim
in `sase` @ `53ba46064` and `sase-core` @ current linked checkout.

**Request:** add a `%sink` directive that is `%wait` in reverse — selected agents
wait for the agent/proc that authored the directive — with selection of all
currently-waiting agents, a hood, exact names, and future matching launches;
working in both directions for stand-alone `%proc` prompts; never affecting an
already-RUNNING agent. Critique the idea, call out beneficial modifications, and
recommend a solution.

---

## 1. Verdict on the idea, and where the reports agree

The feature is sound, well-motivated, and implementable — both researchers reached
that conclusion independently, and every structural claim they relied on verifies
against the code. They also agree on the essentials:

- **Do not write into other launches' wait state.** Third parties today touch
  another agent's `waiting.json`/`ready.json` only to *release* it
  (`_directive_persistence.py`, `_killing_utils.py`); no precedent exists for a
  third party adding a *blocking* dependency, and both reports treat preserving
  that invariant as the top design constraint. A "push" implementation (rewrite
  each target's dependency list) fails on races, on agents that skip the
  dependency phase entirely, on procs (the marker schema cannot name a proc as a
  dependency — `directive_completion.py:58` exists precisely because of this),
  and still needs a standing record for future matches anyway.
- **Enforce at the admission boundary the targets already pass through.** "No
  running agent is affected" should hold *by construction*, not by rule: a target
  that has crossed the run boundary never re-evaluates admission, so a check at
  that boundary can never touch it.
- **The rule must be a durable host-side record**, because future matches arrive
  from other prompts that per-plan admission state cannot see.
- **One shared Rust editor contract drives both ACE and LSP completion**
  (`editor/directive.rs` `DIRECTIVES`, `editor/wire.rs` roles/catalog), so the
  requested prompt-widget + external-editor support is mostly one metadata entry
  plus a new `Hood` value role and `kind: "hood"` catalog rows. Verified: no
  `Hood` role exists today, and hood is the one grouping `%wait` cannot target
  even though the matcher already exists in Rust
  (`agent_identity/identity.rs:440` `agent_name_in_hood`).
- **Scope defaults to the armer's project**, with `scope=host` explicit. Runner
  slots are host-wide, so the naive reading of "all waiting agents" is every
  project on the machine — too wide to be the default.
- **Reject the directive with `%dispatch`** (a host-local barrier cannot fence a
  remote scheduler; `validate_dispatch_combinations`, `agent_launch/mod.rs:2898`)
  and **with `%repeat`** (`repeat_launcher.py` replays the prompt per iteration
  with `%wait:<prev>` prepended — verified — so a repeated `%sink` would arm k
  overlapping barriers).

Where they disagree is mechanism weight, naming, the drain half of the motivating
use case, release scope, and failure philosophy. Sections 3–4 resolve those.

## 2. The critique both the proposal and the reports must absorb

**2.1 The motivating example needs two primitives, and `%sink` is only one of
them.** "Run a command after no agents are running" decomposes into a *drain*
(wait for the currently-running set to finish) and a *hold* (stop pre-run and new
launches from starting). `%sink` is the hold. The drain already exists for agents
— `%q:1` is the documented run-alone barrier (`%queue` capacity budget: occupied
load + candidate weight must fit in N) — but `%queue` is **forbidden on `%proc`
units** (verified: `proc_forbidden_directives`, `agent_launch/mod.rs:1460`;
`ProcUnitWire` carries no queue fields). Report A solved this with a
`drain=true` keyword on `%sink` (running matches become prerequisites of the
armer); report B solved it by allowing `%queue` on proc units. B's decomposition
is the right one: the project already migrated capacity semantics off `%wait`
onto `%queue` with targeted migration errors (verified,
`directive_diagnostics.py:35` and the xprompts memory note), so re-inventing a
second drain vocabulary inside `%sink` would blur a recorded boundary. Named
running agents can already be drained with plain `%wait` (which proc units
support), and `sase agent wait -a -t 2h` (verified, exists with timeout and
project scoping) covers "wait for the current batch" ad hoc. A's `drain=`
keyword remains a coherent v2 extension if selector-scoped drain of *unnamed*
running agents proves needed.

**2.2 This would be the first directive whose effect escapes its own launch.**
Every current directive configures the launch it appears in. `%sink` configures
other launches, including future ones — and prompt text gets *replayed*
(`%repeat`, `#fork`, `/sase_pipe` restarts, prompt history). The barrier must
therefore be a first-class durable object keyed to the arming unit's identity
(re-arming replaces, never stacks) with its own CLI for list/show/release —
prompt text alone can never provide a recovery path.

**2.3 "All currently waiting agents" must be frozen at arm time.** WAITING/QUEUED
(`PRE_RUN_WAIT_STATUSES`, `status_buckets.py:31`) is transient; a live status
predicate captures a set the author never saw and cannot audit. Freeze the
pending-set selector into artifact directories at arm time; keep only lexical
selectors (name, hood, tribe) live, because only those can describe an agent
that does not exist yet. The `%wait:@tribe` machinery is the existing precedent
for forward-looking matching (verified: `_resolution.py:76` passes
`newer_than=waiter_launch_cutoff` for `@` names and suppresses the
terminal-blocked notification for them).

**2.4 Fail-open is not optional.** An armer that segfaults without a terminal
status must not wedge every launch on the host. Report A's durable journal with
"eventual reconciliation" under-specifies this; report B's answer is correct and
already has two file-for-file precedents in the Rust core (verified:
`provider_disable.rs`, `runner_limit_override.rs` — flock, schema version,
`deny_unknown_fields`, `expires_at > created_at` validation, prune-on-read of
expired/invalid records). Mandatory TTL, armer-liveness pruning on read, and
unreadable-store-means-no-hold. A hold is a scheduling courtesy, not a
correctness invariant; the wrong failure mode is a frozen host, not an early
release. Audit needs are met by the record itself, the arm/expiry
notifications, and `sase agent hold list` — not by fail-closed semantics.

**2.5 Self-match is the likeliest real bug.** `%sink(hood=sase-s7)` authored by
`sase-s7.worker` matches its own author. Exclude the armer, its family, its
clan, and its dotted descendants from every predicate (mirroring `%wait`'s
self-wait refusal).

**2.6 The name is backwards.** In dataflow a *sink* is the terminal consumer —
the thing that runs last. This directive makes its author run *first* and
everything else wait. Report B's rename to **`%hold`** is objectively clearer
(`%hold:planner`, `%hold(hood=sase-s7, future)` read as what they do), costs
nothing else in the design, and avoids a silent reversed-meaning trap. This is
a called-out modification; if `%sink` is kept, nothing below changes. No short
alias in v1 (`%h` is `%hide`, and broad scheduling effects should be visible).

## 3. Resolved disagreements

**3.1 Mechanism — pull-model hold store (B), not materialized reverse edges
(A).** A's journal materializes per-target blocker edges, reserves completion
identities early, and runs cycle detection over a global completion graph. B's
store holds one record per armer; each candidate evaluates the store at the gate
it already passes through. Verification decides this cleanly in B's favor:

- Gate 3 (runner-slot admission) is universal and its blocker evaluation is the
  *pure function* `waiter_blockers` (`runner_capacity.rs:608`, verified), which
  already returns typed blocker codes (`capacity-condition`,
  `insufficient-capacity`, `deference-window`) that flow into the queue marker
  and Agents tab via `candidate_blocker_codes`/`decision_blocker_message`
  (verified). One new `hold-barrier` blocker code is nearly the whole agent-side
  runtime change.
- The atomicity report A demands ("whichever happens first wins") already exists
  structurally: `wait_for_runner_slot` receives `record_run_started_at` as its
  claim callback (verified, `run_agent_runner.py::_admit_and_launch`), so
  reading hold records under the existing `runner_slots.lock` during claim *is*
  A's compare-and-transition linearization point, with no new lock.
- `future` matching is free in the pull model — a later launch hits the same
  gate and reads the same record. In the push/edge model it requires the
  standing-record machinery anyway.
- A RUNNING agent has left gate 3 forever, so the "never affect running work"
  requirement holds by construction.

A's design contributions that survive into the recommendation: the linearized
whichever-first-wins invariant (met as above), source exclusion from its own
selection, terminal-outcome-agnostic release (ordering, not success gating),
and the observation in 3.5 below about proc completion semantics.

**3.2 Release scope — the sase agent (family generation), not the arming
shell.** A said family; B said shell, worried a `--code → --mon → --gate` pipe
chain silently extends a host barrier for hours. New verification settles this
for A: `%wait` on a bare agent name already resolves through
`family_candidate_for_root` (`wait_dependency_resolution/_index_queries.py`),
which requires **all members of the current family generation** to resolve and
is explicitly handoff-aware (`_family_handoff_state`/`handoffs_present`). The
glossary likewise defines a *sase agent* as the family, and the request says
"the target agents wait for the **agent**." Releasing a hold at first-shell
settle while a `%wait` on the same name still blocks would make the two
directives disagree about when the same agent "completes." So: release when the
armer's family generation settles (any terminal outcome — success, failure,
kill, skip, loss); the mandatory TTL bounds B's long-chain worry, and a
`release=shell` keyword can narrow it later if a real need appears. For a proc
armer, release on terminal proc status (hook the proc service settlement path).

**3.3 Activation time — active from arm, not from the armer's run start.**
Report B proposed recording holds as armed-pending at launch and active only at
the armer's `run_started_at`, to avoid a queued armer holding the host while it
waits. That rule contradicts B's own recommended composition: in
`%proc(...) %q:1 %hold(pending, future)`, the proc drains at gate 1 while the
hold keeps new arrivals out — if the hold only activates when the proc
dispatches, new launches keep starting, occupied load never drains, and the
armer starves. The quiesce window *requires* the hold to be active while the
armer is still pre-run. Resolve it this way: the hold is **active from arm
time**; the armer is structurally exempt from all holds it kins (3.4's
exclusion) and arming implies a priority boost (below `DEFAULT_WAIT_PRIORITY`,
riding the existing priority/deference machinery, verified present) so the
armer clears admission quickly. The armer-parked-on-a-slow-`%wait` hazard that
motivated B's rule is real but is exactly what the TTL (which runs from arm
time), the arm notification, and `held by <armer>` visibility bound.

**3.4 Cycle handling — proportionate, not a global graph.** A wanted full
completion-graph cycle rejection under a global lock, including re-checking on
every future materialization. That is the most expensive part of A's design and
protects against a rare condition with a cheap backstop. Adopt three layers
instead: (a) at arm time, reject self/kin matches (2.5); (b) at plan time,
reject in-plan cycles (the typed planner already sees both units); (c) at gate
3, detect the observable deadlock — candidate held by an armer that is itself
blocked on the candidate — and raise the existing terminal-blocked-style
notification (`sase_chop_wait_checks.py` precedent, with `dedup_key`), with the
TTL as the guarantee of forward progress.

**3.5 Pending procs — document the limitation, don't rebuild proc identity.**
Verified: a stand-alone proc gets its `proc_id` only at dispatch
(`launch_proc_runtime.py`/`procs/ids.py`); before that it is a logical unit in
one plan's admission journal, not enumerable by other launches. A proposed
reserving durable proc completion identities before admission — correct
long-term but a large change. For v1, B's position stands: the frozen `pending`
snapshot cannot capture un-dispatched procs; lexical selectors (a proc shell's
`%id` name) and `future` still hold them, because proc *targets* are checked at
the admission-engine eligibility path before dispatch. Consequence: drop A's
`proc=<id>` selector — a proc ID exists only once the proc is dispatched
(running), and running work must never be held, so the selector could never
match anything holdable. Proc targeting is by shell name.

**3.6 Adjacent defect worth an independent bead.** A verified finding from
report A that B missed: same-plan logical waits resolve as soon as the target
unit has *any* launch outcome (`admission.rs::resolved_wait_outcome`,
`phase.outcome()` — `Launched` counts), so `%wait(unit=<proc>)` today means
"proc submitted," while an external `%wait(proc=…)` polls to terminal status.
Two spellings of "wait for this proc" have different completion semantics. The
hold design must not inherit this (hold release keys off *terminal* settlement
only), and the inconsistency itself deserves a task bead independent of this
feature.

## 4. Recommended solution

Implement the directive as **sugar over a first-class, TTL-bounded, fail-open
hold store in the Rust core**, consulted as one new typed blocker at the two
admission boundaries that already exist. Name it `%hold` (keep `%sink` only if
the name is dear; nothing else changes).

**Store** (`crates/sase_core/src/agent_hold.rs`, modeled on
`provider_disable.rs`/`runner_limit_override.rs`): `$SASE_HOME/agent_holds.json`,
flock + atomic replace + schema version + prune-on-read. One record per armer
key (agent generation or proc), holding: armer kind/key/display name/project,
`created_at`/`expires_at` (TTL mandatory; config default ~2h, `ttl=` override
with a hard cap), `scope` (`project`|`host`), and a match block:
frozen `artifact_dirs` (the `pending` snapshot), live `names` (agent | family |
clan | workflow | proc shell), `hoods`, `tribes`, and `future`. A record is
active iff schema-current, unexpired, and the armer is still live (dead pid
without a done marker, or terminal proc status ⇒ prune). Unreadable store ⇒ no
hold.

**Syntax** (repeatable and unioned, like `%wait`):

```text
%hold:planner                               # exact agent/family/clan/workflow
%hold:@nightly                              # tribe
%hold(pending)                              # all WAITING|QUEUED now, frozen
%hold(hood=sase-s7)                         # lexical hood match
%hold(pending, future, ttl=90m)             # the freeze
%hold(pending, future, scope=host, ttl=30m) # widest form, explicit in the text
```

Bare `%hold` and `%hold(all)` are hard errors naming the selectors (the
dangerous reading must never be implicit). `future && scope=host`, or a frozen
set above a configured size, raises a confirmation gate on interactive
launches and always lands in `approval_preview` with the enumerated capture
("captures 4 waiting + 2 queued; skips 3 running").

**Enforcement.** Agents: one `hold-barrier` blocker inside
`waiter_blockers` (`runner_capacity.rs:608`), with hold records passed in on
`RunnerCapacityRequestWire` and read once under `runner_slots.lock`; the record
wire gains a `name` field for exact/tribe matching (couples the Python producer
in `core/runner_slots.py` — land Rust first, bump `sase-core-revision.txt`).
Stand-alone proc targets: the same predicate in the admission-engine
eligibility path before dispatch. Gate 2 (`waiting.json`) is untouched: no
third party ever writes a blocking dependency into another launch's marker.
Semantics: active from arm time (3.3); armer + kin excluded (2.5); release on
family-generation / terminal-proc settlement, any outcome (3.2); a settled
armer's `future` rule expires rather than blocking later arrivals vacuously.

**Presentation.** Queue marker gains `held_by` (written by the candidate's own
runner — same writer, same file); Agents tab shows `QUEUED · held by <armer>`;
`sase agent list -j` exposes it; one notification on arm (enumerating the
frozen set) and one on expiry-release; a stale-hold `sase doctor` check; a TUI
panel modeled on the runner-limit override panel.

**Completion/LSP** (one shared contract): `hold` entry in `DIRECTIVES` with
`positional_role: Agent`, static positional suggestions `pending`/`future`,
keywords `hood=` (new `DirectiveValueRole::Hood`), `tribe=`, `ttl=` (existing
`Duration`), `scope=`; `directive_feature_flag` mapping `"hold" →
"agent_holds"` (the exact `%proc`/`typed_launch_units` gating mechanism,
verified); `kind: "hood"` rows synthesized in the editor helper from live name
prefixes; agent rows ranked WAITING/QUEUED-first with status in `detail`;
procs *included* in `%hold` candidates (unlike `%wait`). ACE's
`_directive_completion_tokens.py` needs its wait-style clause handling
generalized rather than a seventh `== "wait"` literal.

**Delivery order** (each phase lands value alone):

1. **Phase 0 (prerequisite):** allow `%queue(capacity=)` on `%proc` units,
   default `weight=0`, so a proc can drain the host. Without this the
   motivating use case is not met by any hold design.
2. **Phase 1:** `agent_hold.rs` + `hold-barrier` blocker + `sase agent hold
   {create,list,release,run,show}` per CLI rules, where `hold run` arms, runs a
   command, and releases in a `finally` — full capability, no prompt surface,
   and the risky runtime proves itself behind a watchable CLI before it lives
   in replayable prompt text.
3. **Phase 2:** the `%hold` directive (parse, plan wire, digests,
   `approval_preview`, `%repeat`/`%dispatch` rejection), behind a beta
   `agent_holds` flag created with `sase flag new` and tested in both states.
4. **Phase 3:** completion + LSP (Hood role, hood catalog rows, ranked rows,
   ACE clause handling).
5. **Phase 4:** TUI `held_by`, hold panel, notifications, doctor check.
6. **Phase 5:** proc-as-target eligibility check.

**Testing** (merge of both matrices): all four armer/target kind combinations;
WAITING, QUEUED, and pending-proc targets held, RUNNING never affected (the
defining invariant); arm-versus-claim race in both lock orders; every selector
incl. hood component boundary (`foo` matches `foo.bar`, never `foobar`);
self/family/clan/descendant exclusion; `future` before and after armer
settlement; TTL, dead-armer, kill, and malformed-store fail-open release;
multiple holds on one target; the gate-3 deadlock notification; both feature
flag states; ACE/LSP parity; `%repeat`/`%dispatch` rejection. Run `just check`
before finishing and `just check-full` as the landing gate.

**Called-out modifications to the original request**, consolidated: rename
`%sink` → `%hold` (2.6); split drain out of the directive into `%queue`-on-procs
(2.1); first-class store + CLI with the directive as sugar (2.2); freeze
`pending` at arm time, selectors named `pending`/`future` (2.3); mandatory TTL,
fail-open, armer-liveness pruning (2.4); armer-kin exclusion (2.5); default
`scope=project` (§1); reject `%repeat`/`%dispatch` combos (§1); family-scoped
release (3.2); active-from-arm with priority boost (3.3); no `proc=<id>`
selector (3.5); `held_by` visibility is part of the feature, not polish. Also
worth doing in the same effort: `%wait(hood=…)`, since the matcher exists and
hood is the one grouping `%wait` cannot target.

**One question before phase 2:** if the real recurring need turns out to be
"run after the current batch" rather than "hold the door," `%proc` +
`sase agent wait -a -t 2h && <cmd>` (with phase 0's `%q` for load gating)
already covers it with zero new prompt surface. Phase 1's CLI usage is the
cheap experiment that answers whether the directive phases are worth their
cost.
