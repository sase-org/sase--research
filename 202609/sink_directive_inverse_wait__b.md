# `%sink`: An Inverse-`%wait` Admission Barrier — Design Research (Researcher B)

**Date:** 2026-09-15
**Question:** How should SASE implement a `%sink` directive that is `%wait` in reverse —
target agents wait for the agent/proc that authored the directive — with rich target
selection (all pending agents, a hood, named agents, plus "and anything matching that
launches later"), working in both directions for stand-alone `%proc` units, and never
affecting an already-RUNNING agent?
**Deliverable:** critique of the idea, objectively beneficial modifications (explicitly
called out), and a recommended implementation.

---

## 0. Bottom line

The idea is **sound and implementable**, and the codebase already has an almost perfect
place to put it. But the proposal as written has four problems worth fixing before any
code is committed:

1. **It only solves half of its own motivating use case.** "Run a command in an
   ephemeral workspace but wait until no sase agents are running" needs *both* a
   source-side drain (wait for the current set to finish) *and* a sink-side hold (stop
   new ones from starting). `%sink` is only the second half. The first half exists for
   agents (`%queue`/`%q:1`) but is **explicitly forbidden on `%proc` units**
   (`agent_launch/mod.rs:1460`). Without fixing that, `%sink` on a proc still cannot
   express the user's example.
2. **"All currently waiting agents" must be frozen at arm time, not evaluated live.**
   WAITING/QUEUED is a transient state; a live predicate captures agents the author
   never saw and makes the affected set unpredictable and unauditable.
3. **The mechanism must be fail-open, with a mandatory TTL and an armer-liveness
   check.** A `%sink` from a proc that segfaults would otherwise wedge every new agent
   start on the host indefinitely. Two existing Rust stores (`provider_disable.rs`,
   `runner_limit_override.rs`) already implement exactly the right pattern
   (flock + schema version + `expires_at` + prune-on-read).
4. **`%sink` is the wrong name.** In dataflow a *sink* is the terminal consumer — the
   thing everything flows *into*, i.e. the thing that runs **last**. This directive
   makes the authoring launch run **first** and everything else wait. Recommend
   `%hold`. (Naming opinion, not a blocker; nothing else in the design changes.)

**Recommended implementation, one line:** a machine-scoped, TTL-bounded, flock-guarded
**hold record store** in the Rust core (modeled on `provider_disable.rs`), consulted as
one new typed blocker code inside the pure function
`runner_capacity.rs::waiter_blockers` — which every agent already passes through, and
which a RUNNING agent has already left forever. No cross-agent file mutation, no new
polling loop, no change to any other agent's authored dependency set.

---

## 1. Ground truth: how `%wait` actually works today

This matters because the proposal says "like `%wait` but in reverse", and `%wait` is
*four* different mechanisms depending on where the dependency lives. Any `%sink` design
has to pick which of them to invert.

### 1.1 The four admission gates

A launch passes through these in order:

| # | Gate | Where | Who parks | Covers every agent? |
|---|---|---|---|---|
| 1 | **Launch-plan admission** (in-request waits, `%if`, stand-alone `%proc` dispatch) | `AdmissionEngine` (`agent/launch_admission_engine.py`), planner in Rust `agent_launch/admission.rs` | the submitting process's coordinator, journal-backed | no — only multi-unit / typed launches |
| 2 | **Runner dependency wait** → status `WAITING` | `axe/run_agent_wait.py:82` `wait_for_dependencies`, called from `run_agent_runner.py:110` | the detached runner process, parked in a 2 s poll loop | **no** — skipped entirely when `not bootstrap.has_dependency_wait` |
| 3 | **Runner-slot admission** → status `QUEUED` | `axe/run_agent_wait_slots.py:344` `wait_for_runner_slot`, called from `run_agent_runner.py:173` | same runner process, host-wide flock + jittered backoff | **yes — every agent** |
| 4 | Workspace claim, then the actual provider run → `RUNNING` | `launch_agent_run` | — | — |

Two facts from `run_agent_runner.py:201` (`_run_agent`) are load-bearing for this design:

* Gate 2 runs **before** gate 3.
* Gate 3 runs **before** any real workspace claim ("Re-exec before repeat-stop
  detection, runner-slot claiming, or any workspace mutation"). So a WAITING or QUEUED
  agent is **not holding a workspace**. Holding such an agent is cheap; holding a
  RUNNING one would not be.

### 1.2 Wait state is owned by the *waiter*, and only released by third parties

The durable wait lives in the waiter's own artifact directory:

* `waiting.json` — written by the waiter (`run_agent_wait.py`, and the queue marker
  variant in `run_agent_wait_slots.py`). Holds `waiting_for`, `wait_for_artifacts`,
  `wait_for_fork_sources`, `wait_for_beads`, `wait_duration`, `wait_until`,
  `resolved_deps`.
* `ready.json` — written by the `wait_checks` lumberjack chop
  (`scripts/sase_chop_wait_checks.py`) when the dependency set resolves. The runner
  polls for it every 2 s with a 60 s direct-resolution fallback so a chop outage cannot
  strand it.

Third parties *do* write into other agents' wait state today, but **only to unblock**:

* the TUI's directive-persistence worker rewrites `waiting.json`/`ready.json` for an
  agent whose wait the user edits (`ace/tui/actions/agents/_directive_persistence.py:299`,
  `:350`);
* the kill/dismiss path releases waiters of a deleted dependency by writing their
  `ready.json` (`ace/tui/actions/agents/_killing_utils.py:110`).

There is **no** precedent for one launch writing a *new blocking* dependency into
another launch's marker. That asymmetry is not an accident; it is what makes the wait
system explainable. **Preserving it is the single most important design constraint.**

### 1.3 What `%wait` can already target

`%wait` positional / keyword targets, and how each resolves:

| Target | Syntax | Resolution |
|---|---|---|
| agent | `%wait:name` | `_resolve_agent` |
| agent family | `%wait:family` | `_resolve_family` |
| clan | `%wait:clan` | `_resolve_clan` |
| workflow | `%wait:wf` | `_resolve_workflow` |
| **tribe** | `%wait:@tribe` | `parse_tribe_reference`, `resolve_tribe_wait_binding` |
| logical unit | `%wait(unit=id)` | in-plan only |
| proc | `%wait(proc=id\|shell)` | `_resolve_proc_wait` (gate 1 only — see §1.5) |
| bead | `%wait(bead=id)` | `closed_bead_ids_for_waits` |
| time | `%wait(time=5m\|1430)` | duration or wall clock |
| **hood** | — | **not supported** |

Two observations:

* **Hood is the one grouping `%wait` cannot target.** A hood is purely lexical: a name
  is in hood `X` iff it equals `X` or is a dotted descendant `X.…`
  (`agent_identity/identity.rs:440` `agent_name_in_hood`; TUI mirror
  `ace/tui/models/agent_hoods.py:83`). That makes hood selection *cheaper* than every
  other selector — no snapshot needed, no I/O, and it works identically for agents that
  do not exist yet. Good news for `%sink(hood=…)`.
* **`%wait:@tribe` is already forward-looking.** `_resolution.py:76` passes
  `newer_than=waiter_launch_cutoff` for `@`-prefixed names, so a tribe wait resolves on
  a tribe member launched *after* the waiter. And
  `terminal_blocking_artifacts_for_name` deliberately returns `()` for `@` names, so a
  forward-looking wait never raises the terminal-blocked notification. **This is the
  existing precedent for the "future matches count too" semantics the proposal asks
  for**, including the decision not to treat an unsatisfiable-right-now forward wait as
  a fault.

### 1.4 `%queue` is the existing source-side drain, and it is agents-only

Per `sase/memory/xprompts.md` and `queue_directive.rs`, under the (sunset, on-by-default)
`queue_capacity_budget` flag, `%queue(capacity=N)` is *this launch's* admission budget:
occupied weighted load plus the candidate's weight must fit in `N`, replacing the global
`max_running_agents` for that launch only. `%q:1` is therefore **"start only when the
host is otherwise empty"** — the run-alone barrier. Authored `capacity=0` is rejected.

Critically, `%q:1` is a *source-side* condition. It does **not** stop anything else from
starting once the `%q:1` launch is running: a subsequent agent with the global limit of
4 sees occupied load 1 < 4 and starts. So `%q:1` gives you a quiet *start*, not a quiet
*window*.

And `AgentUnitWire` carries `queue_capacity` / `wait_priority` / `queue_weight`, while
**`ProcUnitWire` carries none of them** (`agent_launch/mod.rs:497`, `:1563`), with
`%queue` pushed onto `proc_forbidden_directives` at `mod.rs:1460` and reported as the
`agent-directive-on-proc` diagnostic. A stand-alone proc therefore cannot express any
capacity condition at all.

### 1.5 The proc path is genuinely asymmetric

A stand-alone `%proc` (beta flag `typed_launch_units`) is dispatched by the in-process
`AdmissionEngine` into the native proc supervisor (`agent/launch_proc_runtime.py`). Two
consequences the proposal must absorb:

* **A pending proc unit is not enumerable as an agent.** Procs live in
  `~/.sase/procs/procs.jsonl`; a proc *row* does not exist until dispatch. Before
  dispatch it is only a logical unit in an admission journal. So "all currently
  pending things" cannot include un-dispatched procs. Only lexical matching
  (`%proc` + `%id:<shell-name>`) and the "future" rule can reach them.
* **`%wait(proc=…)` is gate-1 only.** `waiting.json` has no `wait_for_procs` field, and
  `wait_checks` scans agent artifact dirs, not the proc store. ACE completion encodes
  this explicitly: `directive_completion.py:55`,
  `_WAIT_UNSUPPORTED_TARGET_KINDS = {"proc"}` — "wait dependencies resolve agent
  artifacts only, so offering a proc row here would complete a dependency that never
  releases." **So if `%sink` were implemented by injecting wait targets into other
  agents' markers, a proc could not be a sink at all** — the marker schema cannot name
  it. That is an independent argument for the barrier design in §6.

---

## 2. What the proposal asks for that does not exist

| Requirement | Exists? | Gap |
|---|---|---|
| Target specific agents by name | resolution exists (`%wait` name resolution) | no inverse application |
| Target all agents in a hood | `agent_name_in_hood` exists in Rust | no wait/selector surface for hoods anywhere |
| Target all currently WAITING agents | `PRE_RUN_WAIT_STATUSES = {WAITING, QUEUED}` (`agent/status_buckets.py:31`), classifiable via `wait_watch` | no way to act on the set |
| "…and future matches too" | `%wait:@tribe` precedent (`_resolution.py:76`) | no standing predicate store |
| Held agents must actually park | gate 3 is universal and already parks agents | no blocker code for a hold |
| Sink can be a stand-alone proc | proc supervisor + terminal statuses exist | marker schema cannot name a proc as a dependency |
| Held target can be a stand-alone proc | admission-engine eligibility exists | no hold check in the eligibility path |
| Never affect a RUNNING agent | free at gate 3 by construction | — |
| Completion in ACE + LSP | shared Rust directive contract drives both (`editor/directive.rs:532` `DIRECTIVES`; LSP `agent_catalog_for_completion`) | new directive entry, new `Hood` value role, `kind: "hood"` catalog rows |

**The two structural gaps are: (a) there is no durable "standing condition on future
launches" store; (b) `%queue` cannot reach `%proc` units.**

---

## 3. Critique of the idea

### 3.1 The motivating example needs two primitives — this is the most important finding

> "…when I want to run some command in an ephemeral workspace for some sase project but
> need to wait until no sase agents are running."

Decompose it:

* **Drain:** wait until the currently-RUNNING set finishes. `%sink` explicitly does
  *not* do this ("no agent that is running should be affected"), and that constraint is
  correct — killing or pre-empting running agents would be far worse. For an *agent*
  this is `%q:1`. For a *proc* it is **impossible today**.
* **Hold:** stop new agents from starting during the window. This is what `%sink` adds.

So `%sink` alone gives you: nothing new starts, but the five agents already running keep
running and your command races them. The user's stated goal is not met.

**Called-out modification #1 (prerequisite):** allow `%queue(capacity=N)` on `%proc`
launch units, evaluated by the admission coordinator as a wait fact derived from
`runner_capacity_snapshot()`, with a proc's default `queue_weight` of **0** (a proc
*gates on* host load but does not *consume* agent budget) and an authored `weight=`
permitted when the proc is genuinely heavy. This is a small, additive change —
`ProcUnitWire` gains three optional fields, `%queue` comes off
`proc_forbidden_directives`, and `_resolve_one_wait` gains one capacity resolver — and
it makes `%proc(...) %q:1 %sink(pending, future)` express the user's example exactly.

I deliberately did **not** recommend a `%wait(idle=…)` spelling for this, even though
`%wait` already works on proc units and already has the typed wait-fact seam. The
project explicitly migrated `runners=`/`capacity=`/`priority=` **off** `%wait` onto
`%queue` and raises targeted migration errors for the old spellings
(`xprompt/directive_diagnostics.py:35`). Re-introducing a capacity concept on `%wait`
would partially reverse a recorded decision. Capacity belongs to `%queue`.

### 3.2 `%sink` would be the first directive whose effect escapes its own launch

Every directive in `DIRECTIVES` configures the launch it appears in. `%sink` configures
*other* launches, including ones that do not exist yet. That is a real layering change,
and it has concrete hazards, all of which come from prompt text being *replayed*:

* **`%repeat:k`** already wait-chains iterations 2..N with a prepended `%wait:<prev>`
  (`agent/repeat_launcher.py:135`). A `%sink` in the repeated prompt would arm `k`
  barriers, each of which matches its siblings.
* **`#fork` / `/sase_pipe` / `sase agent restart`** replay stored prompt text. A stored
  prompt containing `%sink(pending, future)` re-arms a host-wide freeze on every
  restart.
* **`%auto`** skips the human gate. A prompt can then freeze the host with no
  confirmation step at all.
* **Prompt history rewriting** (`history/prompt_store.py`) keeps the directive text
  around indefinitely.

**Called-out modification #2:** make the barrier a **first-class durable object with its
own CLI**, and make `%sink` sugar that materializes exactly one record per launch unit,
keyed to that unit's identity. Then:

* `sase agent hold list / show / release` gives a recovery path that prompt text alone
  never can;
* replay is idempotent per identity (re-arming from the same armer replaces, not
  stacks);
* reject `%sink` together with `%repeat` in v1, and add `%sink` to
  `validate_dispatch_combinations` (`agent_launch/mod.rs:2898`) alongside `%proc`,
  `%wait`, `%queue`, `%clan`, `%id(family=)` — a remote-dispatched launch arming a
  *local* host barrier is incoherent;
* surface the enumerated affected set in `LaunchPlanWire.approval_preview`, so `%auto`
  users at least see it in the launch record.

### 3.3 The name is backwards

A *sink* is where flow terminates. `%sink` makes its author run **first**. Every reader
who knows the dataflow vocabulary will guess the opposite of the real meaning, and the
error is silent (you will not notice you have it backwards until agents park).

**Called-out modification #3:** name it **`%hold`**. `%hold:planner` reads as "hold
planner"; `%hold(hood=sase-s7, future)` reads as "hold that hood, including new
arrivals". No short alias in v1 (`%h` is `%hide`). Runner-up: `%barrier`. Avoid
`%block` (collides with the "blocked on a human" state vocabulary) and `%first`
(implies ordering among peers rather than exclusion).

This is a naming opinion; if you keep `%sink`, nothing else below changes. I use
`%hold` from here on.

### 3.4 "All currently waiting agents" is unstable as a live predicate

Between the keystroke, the launch gate, and the arm, agents move WAITING→QUEUED→RUNNING
and new ones arrive. A live `status ∈ {WAITING, QUEUED}` predicate would therefore hold
a set the author never saw, and the set would keep changing under them. It is also
unprintable in a launch preview, unauditable afterwards, and impossible to reason about
in a bug report.

**Called-out modification #4:** materialize the pending-set selector at arm time into a
frozen list of **artifact directories** (`<project>/<workflow>/<timestamp>` — the stable
identity the runner already knows about itself). Keep only the *lexical* selectors
(`name`, `hood`, `tribe`) as live predicates, because those are the ones that can
meaningfully describe an agent that does not exist yet.

**Called-out modification #5:** rename the selector `pending`, not `waiting`. The set is
WAITING ∪ QUEUED (`PRE_RUN_WAIT_STATUSES`), and `waiting` would read as only the WAITING
bucket. And use `future`, not `new` — `new` is ambiguous with "newly created bead/agent".

### 3.5 Liveness and fail-open are not optional

`%hold(pending, future)` from a proc that dies without writing a terminal status would
park every new agent start on the host until someone noticed. The hold store must be
**fail-open by construction**, on three independent axes:

1. **Mandatory TTL.** `expires_at` always set; default from config
   (`agent_hold_default_ttl`, suggest `2h`), `ttl=` overrides, with a hard cap.
   `runner_limit_override.rs:208` already validates
   `expires_at > created_at` and prunes expired state on read.
2. **Armer liveness.** On every read, resolve the armer: an agent armer with a
   `done.json` or a dead pid, or a proc armer in `TERMINAL_PROC_STATUSES`, is a dead
   record → prune. The classification logic already exists
   (`wait_watch/_classify.py`, `record_is_live`, `is_process_alive`).
3. **Unreadable store ⇒ no hold.** Malformed JSON is removed and treated as absent, the
   way `provider_disable.rs` and `runner_limit_override.rs` both do. Contrast the
   capacity snapshot, which fails *closed* (`capacity-snapshot-invalid`) — that is right
   for capacity and wrong for a hold.

Plus: `sase agent kill <armer>` and the TUI kill path must release, and `sase doctor`
should report stale holds (`doctor/checks_beads.py` is the shape to copy).

### 3.6 Deadlock, self-match, and priority inversion

* **Self-match is the likeliest real bug.** An agent named `sase-s7.worker` arming
  `%hold(hood=sase-s7)` matches itself and parks forever at gate 3. The predicate must
  exclude the armer, its family, its clan, and its dotted descendants. `%wait` already
  refuses self-waits (`wait_watch/_resolve.py`, `_target_intersects_caller`); reuse that
  shape.
* **Cross-plan cycles.** A `%hold`s B while B `%wait`s A. Detectable at plan time only
  within one plan. Across plans, detect at gate 3 (the candidate is held by an armer
  that is itself blocked on the candidate) and raise a notification — the
  `wait_checks` chop's `_upsert_terminal_blocked_wait_notification` is the exact
  precedent, including the `dedup_key` and the "kill and relaunch, or intentionally
  clear" guidance. The TTL is the backstop.
* **Priority inversion / livelock.** An armer that is itself QUEUED behind a full host
  holds everything while waiting. This terminates (running agents finish), but it can
  take a long time and looks like a hang. Mitigation: arming a hold implies a priority
  boost (`wait_priority` below `DEFAULT_WAIT_PRIORITY = 10`), and the hold does not take
  effect until the armer is past gate 3 — i.e. record the hold as *armed-pending* at
  launch and *active* at `run_started_at`. The existing `deference-window` blocker shows
  that time-conditioned blockers are already an accepted concept here.

### 3.7 Scope: project vs host, and machine

Runner slots are **host-wide** (`sase_home()/runner_slots.lock`, global
`max_running_agents`), and `wait_checks` iterates every project. So a naive "all pending
agents" is host-wide across all projects. For "run a command for *some* sase project",
that is too wide.

**Called-out modification #6:** default `scope=project` (the armer's project), with
`scope=host` as the explicit opt-in. The broad form is then always visible in the prompt
text.

Machine scope is a hard v1 limitation worth documenting: holds are per-host. `%dispatch`
sends launches to enrolled remote machines, and `machine_hood.rs` shows that remote
agents get machine-qualified hood prefixes — so a `hood=` selector could *look* like it
covers a remote hood while the store that enforces it is local. Document it; reject
`%hold` + `%dispatch` (§3.2).

### 3.8 Observability is load-bearing, not polish

A held agent that shows `QUEUED` with no visible reason will read as a SASE bug. The
runner-slot path already writes a queue marker and already threads a blocker message
into it (`run_agent_wait_slot_candidate.py`: `candidate_blocker_codes`,
`decision_blocker_message`). So the requirement is cheap **if** the hold is implemented
as a blocker code rather than as a hidden side channel:

* queue marker gains `held_by` (same writer, same file — no cross-agent write);
* Agents tab renders `QUEUED · held by <armer>`;
* `sase agent list -j` exposes it;
* one notification on arm (with the enumerated frozen set) and one on expiry-release.

### 3.9 Alternatives the proposal should be measured against

**(a) Do nothing; poll from inside a proc.**

```
%proc(bash=`sase agent wait -a -t 2h && just check-full`)
```

`sase agent wait -a` blocks until every agent *running when the command starts* reaches
a terminal state, with exit codes for failed/blocked/timeout. Zero new surface. Gets you
"run after the current batch" but not a quiet window — new agents start while you wait,
and `-a` will not see them. **Good enough if the real need is "run after the current
batch."** Worth confirming that is not the actual requirement before building anything.

**(b) Coarse host throttle.** `runner_limit_override.rs` already provides a machine-wide
temporary `max_running_agents` override with a TTL, exposed in the TUI Models panel
(`ace/tui/modals/models_panel_runner_limit.py`). Setting it to 1 for 90 minutes
approximates a freeze. Two limits: `limit >= 1` is enforced
(`runner_limit_override.rs:210`), so a true 0 freeze is not available; and there is no
CLI, only the panel. Not a substitute, but **the right UX template** for a hold panel,
and evidence that "temporary host-wide scheduling override with a TTL" is already an
accepted concept in this codebase.

**(c) CLI-only hold, no directive.**

```
sase agent hold run --pending --future --ttl 90m -- just check-full
```

All of the runtime, none of the prompt-surface/completion/LSP cost, and release is tied
to a process lifetime with a `finally` block — structurally safer than any
directive-armed record. This is the honest 20% that gets 80% of the value. **Recommend
it as phase 1** and build the directive on top once the store has proven itself.

---

## 4. Design options for the mechanism

### Option A — Push: rewrite the targets' `waiting.json`

At arm time, enumerate matching agents and append the armer to each target's
`waiting_for`. A standing rule handles future launches.

* **For:** reuses the whole existing wait pipeline (chop, runner poll, TUI wait display,
  `ready.json` release) with no new evaluation point.
* **Against, decisive:**
  * Breaks the §1.2 invariant — third parties would create *blocking* dependencies in
    other agents' markers for the first time.
  * Multi-writer races against the waiter itself, the `wait_checks` chop, the TUI
    persistence worker, and the kill-release path. The per-artifact flock in
    `_directive_persistence.py` is per-target, so an N-target arm is N non-atomic edits.
  * **Cannot express a proc as a dependency at all** (§1.5) — the marker schema has no
    `wait_for_procs`, and adding one means teaching the chop to read the proc store.
  * Misses every agent that has no `%wait` (they skip gate 2 entirely) unless you also
    *create* `waiting.json` for them, which means fabricating a WAITING state the author
    never asked for.
  * Corrupts the author's dependency set: after release, whose dependency was that?
  * `future` still needs a standing record, so you end up building Option B *anyway*,
    plus the push machinery.

### Option B — Pull: one durable hold record, consulted at gate 3 ✅

The armer writes a single record. Candidates evaluate it at the gate they already pass
through.

* **For:**
  * One writer, one record, one flock. No cross-agent mutation.
  * Gate 3 is universal, so *every* agent is covered, including ones with no `%wait`.
  * `future` is free — a later launch hits the same gate and evaluates the same record.
  * "No RUNNING agent affected" is true **by construction**: a RUNNING agent is past
    gate 3 and never returns.
  * Proc-as-armer is free — the record names the armer, whatever kind it is.
  * Revocation is one file delete.
  * The natural insertion point is a **pure function** (§5.3), so it is cheap to test.
* **Against:** two evaluation points (gate 3 for agents, gate 1 for proc targets); a new
  store to maintain; a held agent shows `QUEUED` rather than `WAITING` (arguably more
  accurate — it *is* queued at the slot gate).

### Option C — CLI-only hold (Option B's store, no directive)

Same store; armed and released by an explicit command wrapping the work. See §3.9(c).

### Option D — Do nothing (`sase agent wait -a` inside a proc)

See §3.9(a).

### Comparison

| | A push | **B pull** | C CLI-only | D nothing |
|---|---|---|---|---|
| Covers agents with no `%wait` | no | **yes** | yes | n/a |
| `future` selector | needs B too | **native** | native | no |
| Proc can be the armer | **no** | **yes** | yes | n/a |
| Proc can be held | no | yes (gate 1) | yes | n/a |
| Preserves "no third-party blocking writes" | **no** | **yes** | yes | yes |
| Race surface | N targets × 4 writers | 1 file, 1 flock | 1 file, 1 flock | none |
| Revocation | N edits | 1 delete | 1 delete | n/a |
| Fail-open story | hard | **easy (TTL + prune)** | easiest | n/a |
| Prompt surface / LSP cost | yes | yes | **none** | none |
| Rust core changes | moderate | moderate | small | none |

**Option B is the design. Option C is how to ship its first phase.**

---

## 5. Recommended solution

### 5.1 Hold record schema (new Rust module `agent_hold.rs`)

Model file-for-file on `provider_disable.rs` / `runner_limit_override.rs`: `fs2` flock,
`NamedTempFile` + `sync_all` atomic write, schema version, `deny_unknown_fields`,
prune-invalid-and-expired on read, clock and `sase_home` injected at the domain seam.

Store: `$SASE_HOME/agent_holds.json` (a map keyed by `armer_key`, so re-arming replaces
rather than stacks — this is what makes prompt replay idempotent).

```jsonc
{
  "version": 1,
  "holds": {
    "agent:sase/ace-run/2026-09-15_14-02-11": {
      "armer_kind": "agent",              // "agent" | "proc"
      "armer_key":  "agent:sase/ace-run/2026-09-15_14-02-11",
      "armer_name": "sase-s7.gatekeeper", // display only
      "armer_project": "sase",
      "created_at": 1789..., "activated_at": 1789..., "expires_at": 1789...,
      "scope": "project",                 // "project" | "host"
      "source": "%hold directive",        // provenance, mirrors provider_disable
      "match": {
        "artifact_dirs": ["sase/ace-run/2026-09-15_13-58-02", "..."],  // frozen `pending`
        "names":  ["planner", "builders"],   // agent | family | clan | workflow | proc shell
        "hoods":  ["sase-s7"],
        "tribes": ["nightly"],
        "future": true
      }
    }
  }
}
```

Evaluation for candidate `C`:

```
held(C) :=  exists active hold H such that
              scope_matches(H, C)
           && !is_armer_kin(H, C)                      // self / family / clan / descendants
           && (   C.artifact_dir ∈ H.match.artifact_dirs
               || (   (H.match.future || C.launched_at <= H.created_at)
                   && (  any name  ∈ H.match.names  resolves to C
                      || any hood  ∈ H.match.hoods  contains C   // agent_name_in_hood
                      || any tribe ∈ H.match.tribes contains C ) ) )
```

`active` = `version` current, `expires_at > now`, `activated_at` set, and the armer
still live. Unreadable or expired ⇒ not active. This yields:

* `pending` ⇒ frozen `artifact_dirs` (§3.4);
* `hood=` / name / `tribe=` ⇒ lexical predicates that already work for agents that do not
  exist yet;
* `future` ⇒ whether the lexical predicates keep applying after `created_at`
  (without it, they are additionally bounded to the arm-time cohort, matching
  `_resolution.py:76`'s `newer_than` precedent).

### 5.2 Syntax (repeatable, like `%wait`)

```
%hold:planner                                  # one named agent / family / clan / workflow
%hold:@nightly                                 # a tribe (reuses parse_tribe_reference)
%hold(pending)                                 # everything WAITING|QUEUED right now, frozen
%hold(hood=sase-s7)                            # a hood
%hold(pending, future)                         # everything now and later — the freeze
%hold(hood=sase-s7, future, ttl=90m)
%hold(pending, future, scope=host, ttl=30m)    # widest form; explicit in the text
```

* Bare `%hold` is a **hard error** with a message naming the selectors. There is no
  useful default and the dangerous reading (everything) must never be the implicit one.
* `%hold(all)` is **rejected**, with an error pointing at `pending, future`. Forcing the
  two-token form means the author always sees both halves of what they are asking for.
* Repeatable and unioned, mirroring `%wait`'s `allows_multiple: true`.
* Interactive launches surface a confirmation gate (`/sase_gate`) for
  `future && scope=host`, and for any arm whose frozen set exceeds a configured size.

### 5.3 Where the check goes — the key implementation insight

**Primary gate (agents): `runner_capacity.rs:608` `waiter_blockers`.**

This is a pure function that returns typed `RunnerCapacityBlockerWire` rows
(`capacity-condition`, `insufficient-capacity`, `deference-window`, …). Adding one
`"hold-barrier"` blocker is the whole agent-side runtime change:

```rust
// in waiter_blockers(eval)
if let Some(hold) = active_hold_for(&eval.request.holds, eval.record) {
    blockers.push(blocker(
        "hold-barrier",
        &format!("Held by {} until it completes or its hold expires.", hold.armer_name),
        None, None, None, None, None,
    ));
}
```

Why this spot is right:

* **Pure and deterministic** — hold records are passed in on
  `RunnerCapacityRequestWire`, read once under the existing `runner_slots.lock`; unit
  testable in Rust with no filesystem.
* **Universal** — every agent reaches gate 3, `%wait` or not.
* **Composes** — it stacks naturally with capacity, weight, and priority deference, and
  inherits the existing jittered-backoff retry loop and
  `notify_runner_slot_state_changed` signalling.
* **Already presented** — `candidate_blocker_codes` / `decision_blocker_message` already
  thread blocker codes and messages into the queue marker and the Agents tab.
* **Satisfies "no RUNNING agent affected" structurally**, not by a rule someone has to
  remember.

Two small wire additions are needed. `RunnerCapacityRecordWire`
(`runner_capacity.rs:44`) has `artifact_dir`, `project_name`, `agent_family` — enough for
hood matching, because `agent_name_in_hood` already derives hood membership from the
*family* name via `historical_family_scope`. But `agent_family` is `None` for a solo
agent, so exact-name and tribe matching need an explicit `name: Option<String>`.
Note `#[serde(deny_unknown_fields)]`: the Python producer
(`core/runner_slots.py::runner_slot_candidate_record`) must be updated in the same change,
and `sase-core-revision.txt` pins the coupling.

**Secondary gate (stand-alone procs as *targets*): the admission engine.**

Add a hold check to the eligibility path in `agent/launch_admission_runtime.py` — either
as a new `WaitTargetWire::Hold`-shaped fact or, more cleanly, as an eligibility predicate
alongside `%if`. Only lexical matching applies (a pending proc unit is not enumerable,
§1.5); document that `pending` never captures un-dispatched procs.

**Explicitly not touched: gate 2.** A held agent whose `%wait` deps resolve simply moves
on to gate 3 and parks there. So **no other agent's `waiting.json` is ever written by the
armer** — the §1.2 invariant survives intact.

### 5.4 Release

In priority order:

1. **Armer settles.** Agent armer: `done.json` written (hook the finalizer/completion
   path in `axe/run_agent_runner.py::_record_completion`). Proc armer: status enters
   `TERMINAL_PROC_STATUSES` (hook `procs/service.py`).
2. **Armer dies without settling.** Detected on read: dead pid and no done marker ⇒
   prune. Reuses `record_is_live` / `is_process_alive`.
3. **TTL expiry.** Prune-on-read, exactly as `runner_limit_override.rs` does.
4. **Explicit.** `sase agent hold release <armer|--all>`, plus the TUI kill/dismiss path.

On release, gate 3's next poll (2 s) admits the held candidates; no extra wakeup needed,
though `notify_runner_slot_state_changed` makes it immediate.

Scope decision for v1: release on the **arming shell's** settle, not the whole agent
family. A family chain (`--code`, `--mon`, `--gate`) can run for hours, and silently
extending a host-wide barrier across a pipe hand-off is a surprise. Document it; a later
`release=family` keyword can widen it if the need is real.

### 5.5 Completion and LSP

Both surfaces are driven by the same Rust contract, so this is mostly one table entry.

**In `sase-core`:**

* `editor/directive.rs:532` `DIRECTIVES` — add the `hold` entry:
  `syntax_forms: COLON_PAREN`, `positional_role: Some(DirectiveValueRole::Agent)`,
  `allows_multiple: true`, `keywords: HOLD_KEYWORDS`.
* `HOLD_KEYWORDS`: `hood=` (new `DirectiveValueRole::Hood`), `tribe=` (existing `Tribe`),
  `ttl=` (existing `Duration`, reuse `DURATION_SUGGESTIONS`), `scope=` (`FreeText` with
  `project` / `host` suggested values).
* `positional_suggestions`: `pending`, `future` with documentation strings — these are
  static, so they complete identically in ACE and in any LSP client with zero host
  round-trip.
* `editor/wire.rs:401` `DirectiveValueRole` — add `Hood`.
* `editor/wire.rs:593` `directive_feature_flag` — `"hold" => Some("agent_holds")`, so the
  directive is hidden from name completion until the flag is on (the exact mechanism
  already used for `%proc`/`typed_launch_units`).
* `directive_synopsis` + hover text.

**Dynamic values.** `AgentCompletionEntry` (`editor/wire.rs:260`) already carries `name`,
`status`, `project`, `kind` (`agent|family|clan|tribe`), `member_count`, `detail`,
`documentation`, and the LSP refreshes it through the host bridge with staleness
detection (`catalog_cache.rs::agent_catalog_for_completion`). So:

* extend `kind` with `"hood"` and have the Python editor helper
  (`integrations/_editor_helper_agents.py`) synthesize hood rows from the dotted prefixes
  of live agent names, with `member_count` = live members. Both surfaces get hood
  completion from one change.
* for positional agent values, rank `status ∈ {WAITING, QUEUED}` first and put the status
  in `detail` — `%hold` mostly wants pending agents, and completion should say which are.
* keep procs *in* the candidate set for `%hold` (unlike `%wait`, which excludes them via
  `_WAIT_UNSUPPORTED_TARGET_KINDS`) — a named proc shell is a legitimate hold target.

**In ACE (`sase`):** `_directive_completion_tokens.py` already special-cases `"wait"` for
comma-clause / structured-fragment handling in six places; `%hold` needs the same
treatment. Worth extracting a shared "repeatable identity-list directive" predicate in the
same change rather than adding a seventh literal `== "wait"`.

### 5.6 CLI

Per `sase/memory/cli_rules.md` — alphabetical subcommands, short alias for every long
option, no required options, colored output, and a bare group defaulting to `list`:

```
sase agent hold                  # -> list (with the delegation notice)
sase agent hold create   --pending --future --hood H --name N --tribe T --ttl D --scope S
sase agent hold list     [-j] [-p PROJECT]
sase agent hold release  ARMER | -a/--all
sase agent hold run      [same selectors] -- COMMAND ...   # arm, run, release in a finally
sase agent hold show     ARMER [-j]
```

`sase agent hold run` is the safest surface (release bound to a process lifetime) and is
the phase-1 deliverable.

### 5.7 Presentation

* Queue marker gains `held_by`; Agents tab shows `QUEUED · held by <armer>` with the
  armer as a jump target (the neighbor-navigation machinery in
  `ace/tui/models/agent_hoods.py` already handles hood-relative navigation).
* Armer's detail panel lists what it is holding, with a count chip.
* A hold panel modeled on the Models panel's runner-limit override
  (`modals/models_panel_runner_limit.py`) — same "temporary, TTL-bounded, host-wide
  scheduling override" shape, same release affordance.
* Notification on arm (enumerating the frozen set) and on expiry-release, via
  `upsert_notification` with a `dedup_key`, mirroring
  `sase_chop_wait_checks.py::_upsert_terminal_blocked_wait_notification`.
* `sase agent hold` rows in `sase doctor` when a hold is older than its expected window.

### 5.8 Feature flag

Per `sase/memory/sase_flags.md`, create with `sase flag new agent_holds -k beta` (never
by hand-editing the registry), with `--when-enabled` / `--when-disabled` /
`--remove-when` authored, and tests for **both** states. Off branch: `%hold` raises a
targeted `DirectiveError` naming the flag (mirroring
`TYPED_LAUNCH_UNITS_DISABLED_MESSAGE`), the store is never read, and
`waiter_blockers` never emits `hold-barrier`. Removal deletes the Off branch.

### 5.9 Phasing

| Phase | Deliverable | Value standalone |
|---|---|---|
| **0** | `%queue` on `%proc` units (default `weight=0`) | a proc can finally wait for a quiet host — §3.1 |
| **1** | `agent_hold.rs` store + `hold-barrier` blocker in `waiter_blockers` + `sase agent hold {create,list,release,run,show}` | full capability, CLI-only, no prompt surface |
| **2** | `%hold` directive: Rust `DIRECTIVES` entry, `Hood` value role, Python parse/extract/validate, plan-wire plumbing, `approval_preview` | prompt-authored holds |
| **3** | Completion + LSP: hood catalog rows, status-ranked agent rows, ACE clause handling | the requested editor experience |
| **4** | TUI: `held_by` rendering, hold panel, notifications, `sase doctor` check | operability |
| **5** | Proc-as-target: admission-engine eligibility check | procs held by others |

Phase 1 alone satisfies the motivating use case (with phase 0). Phases 2–3 are the
ergonomic layer. That ordering means the risky runtime lands behind a CLI you can watch,
before it lands behind prompt text that gets replayed.

### 5.10 Test obligations

* Rust unit tests on `waiter_blockers` for: hold matched by frozen `artifact_dir`; by
  hood; by name; by tribe; `future` on/off; self/family/clan/descendant exclusion;
  expired hold ignored; dead armer ignored; malformed store ⇒ fail-open; interaction with
  `capacity-condition` and `deference-window` precedence.
* Rust store tests copied from `provider_disable.rs`: concurrent arm under flock, atomic
  replace, prune-on-read for invalid and expired records, schema-version rejection.
* Python integration: a RUNNING agent is unaffected (the defining invariant); a QUEUED
  agent parks and then starts on release; an agent with no `%wait` is still held;
  a proc armer releases on terminal status; kill releases; TTL releases.
* Directive-parse tests: bare `%hold` errors; `%hold(all)` errors with the migration-style
  message; `%hold` + `%repeat` errors; `%hold` + `%dispatch` errors; repeatable union;
  round-trip through the launch plan wire.
* Completion tests in both surfaces, following the existing `%wait` cases in
  `editor/directive.rs` (lines ~2363–2805) and the ACE token tests.
* Per `sase/memory/lint_and_test.md`, `just check` before finishing and `just check-full`
  as the landing gate.

---

## 6. Modifications to the proposal, collected

Every one of these is a change to what was asked for, stated plainly:

1. **Add a prerequisite:** allow `%queue(capacity=)` on `%proc` units with default
   `weight=0`. Without it `%sink`/`%hold` does not deliver the stated use case. *(§3.1)*
2. **Make the barrier a first-class object with a CLI**, not only a directive; the
   directive materializes one record keyed to the launch unit. *(§3.2)*
3. **Rename `%sink` → `%hold`.** `sink` means the opposite of what the directive does.
   *(§3.3)*
4. **Freeze the pending-set selector at arm time** into artifact dirs; keep only
   name/hood/tribe as live predicates. *(§3.4)*
5. **Rename the selectors:** `pending` (not `waiting` — the set is WAITING ∪ QUEUED) and
   `future` (not `new`). *(§3.5)*
6. **Default `scope=project`**, with `scope=host` as an explicit opt-in. *(§3.7)*
7. **Mandatory TTL, armer-liveness pruning, and fail-open on an unreadable store.**
   *(§3.5)*
8. **Exclude the armer, its family, its clan, and its descendants** from every predicate.
   *(§3.6)*
9. **Reject `%hold` + `%repeat`, and `%hold` + `%dispatch`.** *(§3.2, §3.7)*
10. **Reject bare `%hold` and `%hold(all)`;** require `pending, future` spelled out.
    *(§5.2)*
11. **Add `tribe=` as a selector** — `%wait` already supports `@tribe` and the resolution
    machinery exists; omitting it creates a gratuitous asymmetry. *(§1.3)*
12. **Hold takes effect only once the armer is past gate 3** (`activated_at`), and arming
    implies a priority boost, to avoid the armer-holds-everything-while-queued stall.
    *(§3.6)*
13. **`held_by` in the queue marker and in the Agents tab is part of the feature**, not a
    follow-up. *(§3.8)*
14. **Also consider suggesting `%wait(hood=…)`** in the same change: hood is the one
    grouping `%wait` cannot target, the matcher already exists in Rust, and adding it to
    both directives at once keeps the two vocabularies symmetric. *(§1.3)*

---

## 7. Risks and open questions for the user

1. **Is the real requirement "hold the door" or "run after the current batch"?** If the
   latter, `%proc(bash=`sase agent wait -a -t 2h && …`)` ships today with zero new
   surface. §3.9(a).
2. **Host or project scope by default?** I recommend project; you may genuinely want host
   for a machine-wide `just check-full`.
3. **Release on arming shell or whole family?** I recommend the shell, to avoid a pipe
   chain silently extending a host-wide barrier for hours.
4. **How wide is too wide?** A configured threshold above which arming requires a
   confirmation gate needs a number. Suggest: any `future && scope=host`, or any frozen
   set above 5.
5. **Cross-machine holds are out of scope for v1** and `hood=` selectors can look
   machine-qualified (`machine_hood.rs`). Confirm that limitation is acceptable.
6. **`deny_unknown_fields` on the capacity wire** means the `name` field addition couples
   `sase` and `sase-core` revisions. Land the Rust side first, bump
   `sase-core-revision.txt`, then the Python producer.
7. **Does `%hold` belong in prompt text at all?** §3.2 is a genuine layering objection. If
   phase 1's CLI proves sufficient in practice, phases 2–3 may not be worth their cost.

---

## 8. Appendix: change inventory

**`sase-core` (`crates/sase_core/src/`)**

| File | Change |
|---|---|
| `agent_hold.rs` *(new)* | hold store; copy the shape of `provider_disable.rs` |
| `lib.rs` | `pub mod agent_hold;` + re-exports |
| `runner_capacity.rs` | `holds` on `RunnerCapacityRequestWire`; `name` on `RunnerCapacityRecordWire`; `hold-barrier` in `waiter_blockers` (:608) |
| `editor/directive.rs` | `hold` entry in `DIRECTIVES` (:532); `HOLD_KEYWORDS`; suggestions; synopsis |
| `editor/wire.rs` | `DirectiveValueRole::Hood` (:401); `directive_feature_flag` (:593); `kind: "hood"` doc (:266) |
| `agent_launch/mod.rs` | parse/plan `%hold`; `%queue` off `proc_forbidden_directives` (:1460); queue fields on `ProcUnitWire` (:497); `%hold` in `validate_dispatch_combinations` (:2898); `approval_preview` line |
| `agent_launch/admission.rs` | hold eligibility for proc units |
| `feature_flag_state.rs` | `agent_holds` registry entry (via `sase flag new`) |

**`sase` (`src/sase/`)**

| File | Change |
|---|---|
| `xprompt/_directive_types.py` | `"hold"` in `_KNOWN_DIRECTIVES` (:37) and `_MULTI_VALUE_DIRECTIVES` (:56); `PromptDirectives` fields |
| `xprompt/_directive_collect.py` | `%hold` keyword validation (mirror the `%wait` block, ~:123) |
| `xprompt/_directive_values.py` / `_directive_extract.py` | selector resolution; reuse `_parse_wait_tribe_reference` (:50) |
| `xprompt/directive_diagnostics.py` | `%hold(all)` / bare-`%hold` migration-style messages |
| `core/agent_hold_facade.py` *(new)* | thin binding over the Rust store |
| `core/runner_slots.py` | pass holds into the capacity request; add `name` to the candidate record |
| `axe/run_agent_wait_slot_candidate.py` | surface `hold-barrier` in blocker codes and the marker's `held_by` |
| `axe/run_agent_runner.py` | release the armer's hold at `_record_completion` (:~225) |
| `agent/launch_admission_runtime.py` | hold eligibility for proc units (`_resolve_one_wait`, :361) |
| `agent/launch_proc_runtime.py` / `procs/service.py` | release on terminal proc status |
| `ace/tui/widgets/_directive_completion_tokens.py`, `directive_completion.py` | `%hold` clause handling; stop excluding procs for `%hold` (:55) |
| `integrations/_editor_helper_agents.py` | `kind: "hood"` catalog rows; status-ranked agent rows |
| `ace/tui/models/_loaders/_meta_enrichment_*.py` | render `held_by` |
| `ace/tui/modals/agent_hold_panel.py` *(new)* | modeled on `models_panel_runner_limit.py` |
| `main/parser.py` + `cli/agent_hold.py` *(new)* | `sase agent hold {create,list,release,run,show}` |
| `doctor/checks_*.py` | stale-hold check |
| `default_config.yml` | `agent_hold_default_ttl`, `agent_hold_max_ttl`, confirmation threshold; any new keymap |
| docs + `sase/memory/xprompts.md` | directive table row and the `%hold` / `%queue` composition rule |

**Memory note:** the `%hold` row and the "`%q:1` drains, `%hold` holds, together they
quiesce" rule belong in `sase/memory/xprompts.md`. Per project instructions that edit must
go through `/sase_memory_write`, not a direct file change.

---

## 9. Key source references

* Runner phase order: `src/sase/axe/run_agent_runner.py:110,173,201`
* Dependency (WAITING) barrier: `src/sase/axe/run_agent_wait.py:82`
* Runner-slot (QUEUED) admission: `src/sase/axe/run_agent_wait_slots.py:344`
* **Recommended hook:** `sase-core/crates/sase_core/src/runner_capacity.rs:608`
  (`waiter_blockers`), request/record wires at `:24`, `:44`
* Wait-resolution chop: `src/sase/scripts/sase_chop_wait_checks.py`; terminal-blocked
  notification precedent in the same file
* Forward-looking tribe wait (`future` precedent):
  `src/sase/core/wait_dependency_resolution/_resolution.py:76`,
  `_index_queries.py:254`
* Third-party wait edits, release-only: `_directive_persistence.py:299,350`;
  `_killing_utils.py:110`
* Hood matcher: `sase-core/.../agent_identity/identity.rs:440`;
  `src/sase/ace/tui/models/agent_hoods.py:83`
* Directive contract (ACE + LSP): `sase-core/.../editor/directive.rs:532`;
  roles/flags at `editor/wire.rs:401,593`; catalog entry at `:260`
* `%queue` forbidden on `%proc`: `sase-core/.../agent_launch/mod.rs:1460`;
  `ProcUnitWire` at `:497`
* Store pattern to copy: `sase-core/.../provider_disable.rs`,
  `runner_limit_override.rs:208` (`is_valid_record`, `limit >= 1`)
* Pre-run statuses: `src/sase/agent/status_buckets.py:31`
* Proc-exclusion rationale in wait completion:
  `src/sase/ace/tui/widgets/directive_completion.py:55`
* `sase agent wait` (the do-nothing alternative): `sase agent wait --help`
