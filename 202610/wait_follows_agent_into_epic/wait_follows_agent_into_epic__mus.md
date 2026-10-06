# `%wait` `for_epic` Follow-On: Design Research

Researcher: mus (independent swarm report; conclusions my own).
Question: add a `for_epic=<true|false>` keyword to the `%wait` directive so a
prompt launched with `%wait(<agent>, for_epic=true)` waits for the named agent
**and** for any epic bead that agent creates, letting users launch follow-up
prompts before the epic exists instead of two-stepping through
`%wait(bead=<epic-id>)`.

## TL;DR verdict

Good idea, worth building, but **not as specified**. Three adjustments are
load-bearing; without them the feature deadlocks or silently changes existing
behavior:

1. **Default must be `false`, not `true`.** Default-`true` retroactively
   changes every existing `%wait(<agent>)` into a two-phase barrier. Ship
   opt-in; consider default-`true` only after a deprecation cycle, if ever.
2. **"May or may not create" needs terminal semantics.** An agent that
   finishes without ever creating an epic must *release* the waiter (with a
   diagnostic), never park it forever. This is the single most important
   reliability rule.
3. **The epic usually does not exist when the agent finishes.** The planner
   proposes and is SIGTERM'd; a human approves later; only then does the host
   back-fill `epic_bead_id` into the planner's `agent_meta.json`. A naive
   "when the agent is done, read its epic" check misses the primary flow
   entirely. The waiter must keep observing the finished agent's metadata
   (plus its pending-plan signal) until an epic appears or the plan is
   rejected/withdrawn.

With those three fixed, the rest — parsing, the two-phase wait barrier, and
the TUI transition display — is straightforward, and most of the link
infrastructure the proposal assumes genuinely does exist. Details and a
concrete recommended spec follow.

## 1. How `%wait` works today (verified in-tree)

- **Syntax.** `%wait` is repeatable/multi-value (`_MULTI_VALUE_DIRECTIVES` in
  `src/sase/macro/_directive_types.py`). Positional args are agent names
  (bare `%wait` resolves to the most recent named agent); parenthesized
  keywords are whitelisted in `src/sase/macro/_directive_collect.py`:
  `agent=, unit=, proc=, bead=, hood=, time=`. Anything else raises
  `DirectiveError`. There is no boolean keyword today — `for_epic=` would be
  the first, so it also needs a true/false parser (no precedent to copy).
- **Parsed shape.** `PromptDirectives.wait: list[str]` (agent names),
  `wait_beads`, `wait_hoods`, `wait_units`, `wait_procs`, `wait_duration /
  wait_until` (`_directive_types.py`). The programmatic twin is
  `PromptWaitDirective` (`agents, beads, hoods, time_token, capacity…`) in
  `src/sase/macro/_directive_edit_wait.py`, which also owns `%wait`
  re-serialization (`_format_wait_directive`) — it must round-trip the new
  keyword.
- **Persistence.** Wait spec fans out to two durable records per waiter:
  `agent_meta.json` (`wait_for`, `wait_for_beads`, `wait_for_hoods`,
  `wait_duration`, `wait_until`) via `wait_meta_patch_for_token`, and the
  polled `waiting.json` barrier (`waiting_for`, `wait_for_beads`, …) via
  `waiting_marker_patch_for_token` (both in
  `src/sase/ace/tui/actions/agents/_directive_persistence.py`). Any new flag
  must be added to **both**, plus the ops-command payload path
  (`src/sase/ops/commands/_agent_directive.py`) and the plan-gate /
  approve-result plumbing (`wait_agents / wait_beads / wait_hoods` in
  `src/sase/_plan_gate_envelope.py`, `src/sase/plan_gate.py`,
  `src/sase/llm_provider/_plan_utils.py`).
- **Evaluation.** Two cooperating evaluators read the same barrier:
  the `wait_checks` chop (`src/sase/scripts/_chop_wait_checks_run.py`) writes
  `ready.json`; the runner itself (`src/sase/axe/run_agent_wait.py`,
  `run_agent_wait_deps.py`) re-resolves directly as a fast path/fallback so a
  chop outage cannot strand waiters. Both converge in
  `dependency_resolution_status()` (`src/sase/core/wait_dependency_resolution/_resolution.py`),
  which ANDs every dimension: agent names (`index.is_resolved`), hoods,
  and beads (`closed_bead_ids_for_waits` in `src/sase/bead/wait_status.py` —
  a bead wait releases only on bead **closure**, not creation).
- **TUI display.** The agent detail header renders one styled lane per wait
  dimension — `agents, tribes, beads, hoods, time`, plus runner-slot capacity
  (`build_wait_lanes` in
  `src/sase/ace/tui/widgets/prompt_panel/_agent_wait_section.py`). Bead lanes
  already show per-bead status badges. This is where the phase transition must
  surface.

## 2. How "the epic bead an agent created" is recorded today

The proposal's assumption ("we already have the infrastructure") is
**mostly true**, with one gap that matters:

- **Canonical write path (exists).** When a plan is approved and the host
  launches the epic, `_update_epic_launch_metadata()` in
  `src/sase/bead/epic_launch.py` back-fills `epic_bead_id` (+
  `epic_started_at`, `plan_committed`, `sdd_plan_path`) into the **planner
  agent's own `agent_meta.json`** and nudges the artifact index. This is
  exactly the agent→epic link the waiter needs, and it is written to the
  record the waiter already knows how to find (the waited-on agent's artifact
  dir, resolvable through the existing wait index).
- **Second copy (exists).** `agents_sync/bead_links.py` derives
  `epic_bead_id` from published run metadata, and the `agent-bead` projection
  rule (`src/sase/artifact_links/projection/_agent_bead.py`) emits
  `agent --implements--> bead` edges from `bead_id / epic_bead_id /
  phase_bead_id` fields. Useful for audit and agent pages; **not** suitable as
  the waiter's discovery source (projection/publish lag, sidecar sync delays).
- **The gap: non-host creation paths.** The back-fill lives in
  `finish_epic_launch` (host approval flow). An agent that creates an epic
  some other way — e.g. running `sase bead work <plan>` itself via
  `create_and_launch_epic_from_plan()` (`src/sase/bead/epic_from_plan.py`) —
  does not get `epic_bead_id` written into its own `agent_meta.json` by that
  path. Before building `for_epic`, audit every epic-creation entry point and
  route them all through one canonical "record epic id on creator meta"
  helper (extracted from `_update_epic_launch_metadata`). Otherwise the
  feature works for TUI-approved plans and silently never triggers for
  CLI/agent-driven epic creation — the worst kind of unreliability: partial.
- **Freshness.** The waiter must read the waited-on agent's `agent_meta.json`
  **from disk at poll time**, not from a cached scan row: `ArtifactCandidate`
  in the wait index carries no bead fields, and any snapshot caches it. Disk
  read of one small JSON per poll is cheap and always current.

## 3. Critique of the plan as stated

### 3.1 Default `true` when an agent name is present — do not do this

This is the most dangerous clause. `%wait(<agent>)` is existing, working
syntax with settled semantics (release when the agent resolves). Flipping its
meaning to a two-phase barrier:

- changes behavior for every existing prompt, stored macro, skill, and
  `#fork`-implied wait without the author opting in;
- converts all current "wait for a coder/runner that never makes epics" uses
  into waits that now depend on the no-epic release path (Section 3.2) being
  perfect — any bug there hangs previously-working flows;
- makes the bare `%wait` ("most recent agent") form newly fragile, since the
  user may not even know which agent they waited on.

**Adjustment: default `false`; `for_epic=true` is always explicit.**
The "error and/or diagnostic warnings if used without an agent name" clause is
right and should be a hard `DirectiveError` at parse time (matching how
unknown `%wait` keywords already fail), plus a TUI wait-modal validation that
disables the toggle unless at least one agent target is selected. Keep the
explicitness; drop the implicit default.

### 3.2 "May or may not create" must terminate — specify the no-epic release

As specified, a waited-on agent that never creates an epic leaves the waiter
parked forever (bead waits release only on closure; a nonexistent bead never
closes). The spec even acknowledges optionality ("may or may not create")
without resolving it. **Rule: when the waited-on agent reaches terminal state
with no epic linked and no plan still pending approval, the epic phase
resolves *vacuously* and the waiter proceeds, recording a diagnostic**
(e.g. `blocked_on` cleared, diagnostic `"<agent> finished without creating an
epic; for_epic satisfied vacuously"`). This preserves today's effective
behavior for non-planner agents and makes the feature safe to attach broadly.
The vacuous release must be as visible in the TUI as a normal release (a
dismissable "no epic was created" note, not silence).

### 3.3 The timing gap that breaks the naive implementation

Naive reading: "wait for agent to finish, then wait for its epic." But the
dominant real flow is:

1. Planner agent writes plan, calls propose → **planner is SIGTERM'd**
   (`handle_plan_propose_command` in
   `src/sase/main/plan_propose_handler.py` — propose kills the runner).
2. Plan sits as a pending approval (see `PendingPlan` / `pending_plans()` in
   `src/sase/main/plan_pending.py`) for minutes to hours.
3. Human approves → host launches epic → **only now** is `epic_bead_id`
   back-filled into the (long-dead) planner's meta.

So at "agent done" time there is usually **no epic yet**, and step 2 is
unbounded. The waiter needs a three-state machine per for_epic agent target,
not two phases:

- **STATE A — agent running:** behave exactly like today's agent wait.
- **STATE B — agent terminal, epic known:** behave exactly like today's
  `%wait(bead=<epic>)` (release on closure).
- **STATE C — agent terminal, epic unknown:** the state the proposal misses.
  Stay parked **iff** a plan from that agent is still pending approval (or the
  agent's meta shows a submitted-plan marker without a verdict); poll the
  agent's `agent_meta.json` for a newly-appearing `epic_bead_id`. Leave STATE C
  when (i) `epic_bead_id` appears → go to B; (ii) the plan is
  rejected/withdrawn/expired with no epic → vacuous release per 3.2;
  (iii) agent terminal + no plan ever pending + no epic → vacuous release
  immediately (don't even enter C visibly).

Without STATE C, the feature works only for the minority flow where the
agent itself lives to see its epic launched — and fails precisely the
planner-approval flow in the motivating example.

### 3.4 Keyword naming and parsing

House style for `%wait` keywords is bare nouns (`bead=, hood=, unit=, proc=,
time=, agent=`). `for_epic=` is grammatical but off-style; `epic=true|false`
fits better and reads naturally next to `bead=`. **Adjustment: accept
`epic=` as the canonical spelling** (it also future-proofs an `epic=created`
mode, Section 3.6); accept `for_epic=` as a deprecated-tolerant alias only if
cheap — otherwise pick one and document it. Either way it is the first
boolean `%wait` keyword, so it needs: strict `true/false/1/0/yes/no`
normalization, a clear `DirectiveError` on anything else, per-target vs
global scoping decided explicitly (recommendation: one flag for the whole
directive — per-agent flags like `%wait(a, for_epic=true)` mixed with
`%wait(b)` in the same prompt are UI-hostile; a single `%wait(a, b,
epic=true)` applying to all named agents is predictable), and
round-tripping in `_format_wait_directive` / `PromptWaitDirective`.

### 3.5 Failure semantics need stating

Today an agent wait releases on the waited-on agent's *successful* resolution
(`WAIT_SUCCESS_OUTCOMES`-family in `wait_dependency_resolution/_types.py`).
For for_epic, define: waited agent **fails** + pending plan exists →
stay in STATE C (the plan may still be approved; failure of the planner
doesn't retract the proposal). Waited agent fails + no pending plan + no epic
→ vacuous release with a failure-flavored diagnostic (do not propagate the
failure: the waiter waited for the *epic*, and there is definitively none).
Waited agent fails + epic exists → proceed to STATE B normally (epic closure
is independent of the planner's exit code). Also define the cycle guard: if
the epic's own work graph ends up containing the waiter (e.g. the waiter was
meant to be a phase worker), waiting for epic *closure* deadlocks by
construction — detect waiter-dir-inside-epic-membership at evaluation time
and fail loudly rather than hang. (This is another reason Section 3.6's
`created` mode matters.)

### 3.6 The goal says "launch earlier" — closure-wait doesn't start anything earlier

Worth being precise about what the proposal actually buys. Old flow: user
waits for planner → learns epic id → launches prompt with
`%wait(bead=<epic>)` → prompt **starts** at epic closure. New flow: user
launches prompt immediately with `%wait(<agent>, for_epic=true)` → prompt
**starts** at epic closure. Same start time; the win is authorship ergonomics
(one step, no bead-id plumbing, no waiting around to launch) — real, but it
is not earlier execution. If earlier *execution* is ever wanted (phase
workers, land agents, anything that needs the epic to *exist* but not to be
*closed*), that is a different release condition: release when the epic is
**created** and inject the id (e.g. as an output variable / `wait` namespace
entry, alongside the existing `agents[…].plan_file` synthesis). **Adjustment:
ship boolean `epic=true` = closure semantics (exact equivalence with today's
manual `bead=` flow, which makes it easy to reason about and test); reserve
the spelling `epic=created` for a follow-up**, and design the parser + TUI
lane so that third state slots in later. Do not try to ship both modes at
once.

### 3.7 TUI: "very clear" needs a concrete design, not a brighter color

The transition agent-done → epic-wait is a *causal* story ("because planner X
finished, you are now waiting for epic s-123"), and the TUI should narrate it,
not just relabel a badge. Concretely, in `build_wait_lanes`:

- **Phase A:** existing `agents` lane unchanged (`waiting for planner-x
  [Running]`).
- **Phase C (epic unknown):** keep the `agents` lane showing the terminal
  agent (`planner-x [Done]`) and add a second lane, e.g. `epic: watching
  planner-x for a created epic…` (or `…plan pending approval`). This makes
  "stopped waiting for the agent, now waiting for what it creates" literal.
- **Phase B:** `agents` lane shows the done agent dimmed/struck; the `beads`
  lane gains the epic id with its live open/closed badge (existing
  `_append_wait_bead_status_badge` machinery), ideally annotated with source:
  `s-123 (from planner-x)`.
- **Vacuous release:** a transient notice chip (`planner-x finished; no epic
  created — proceeding`), plus the diagnostic in the wait record, so "it
  started and I don't know why" never happens.
- Also update `wait_spec_label` (`_wait_helpers.py`) and the wait modal: the
  modal needs an "also wait for created epic" toggle gated on ≥1 agent
  target, with a one-line explainer of closure semantics and the no-epic
  release. Without the modal change the feature is CLI-prompt-only, which
  halves its audience.

### 3.8 Smaller reliability notes

- **Evaluation points.** The expansion agent→epic must be implemented once in
  shared code both evaluators call (the `dependency_resolution_status` /
  `confirm_dependency_resolution` layer or a pre-expansion step in
  `run_agent_wait_deps` reused by the chop), never twice divergently. Note the
  runner reads `waiting.json` + `ready.json` while the chop writes them —
  dynamic expansion that only lives in one evaluator will flap.
- **Cross-project.** `closed_bead_ids_for_waits` already routes full bead ids
  across enabled projects; the epic discovery read (planner meta) is
  artifact-dir-local so it inherits no new cross-project problem. State this
  in the design so nobody re-solves it.
- **Retention/archival.** If the waited-on agent's artifacts age out
  (`agent_artifact_run_retention.py`, dismissed-completion archives) mid-wait,
  STATE C must not crash on a vanishing meta: treat unreadable meta + no
  known epic as "evidence gone" → vacuous release with diagnostic, and say so.
- **Tests to demand:** planner-finishes-then-approval-arrives (STATE C →
  B); plan rejected (C → release); agent never plans (immediate vacuous
  release); epic closes (B → start); agent fails with pending plan (stay in
  C); boolean parse errors; `epic=` with no agent name errors; TUI lane
  snapshots for A/C/B/release.

## 4. Recommended solution

**Spec: `%wait(<agent> [, <agent>…] [, epic=true])`.**

1. **Syntax & validation** (`_directive_collect.py`, `_directive_values.py`,
   `_directive_extract.py`): add `epic` to `%wait`'s `supported_keys`; strict
   boolean parse (`true/false`, accept `1/0/yes/no`, reject else with
   `DirectiveError`); `epic=true` with zero agent names (positional or
   `agent=`) is a `DirectiveError` ("`epic=` requires at least one `%wait`
   agent target"); applies to all agent targets on the directive;
   orthogonal to `bead=/hood=/time=` (they AND as today). Keep the user's
   `for_epic=` spelling as a hidden alias only if zero-cost; otherwise ship
   `epic=` alone. **Default `false`.**
2. **Plumbing**: new `wait_epic: bool` on `PromptDirectives` and
   `PromptWaitDirective` (+ `_format_wait_directive` round-trip); persist on
   both `agent_meta.json` (`wait_for_epic: true`) and `waiting.json` via the
   two `_directive_persistence.py` patch builders and the
   `ops/commands/_agent_directive.py` payload; carry through plan-gate
   approve results as `wait_epic` alongside `wait_agents` (no new bead id is
   known at approval time — the flag *is* the payload).
3. **Link hardening (pre-req)**: extract the `epic_bead_id` back-fill from
   `_update_epic_launch_metadata` into a shared helper and call it from every
   epic-creation path, including agent-run `sase bead work` launches — verify
   each path with a test that creates an epic and reads the creator's meta.
   Waiter discovery reads the waited-on agent's `agent_meta.json` from disk
   at poll time (never the projection DB).
4. **Evaluation**: implement the A→B→C state machine (Section 3.3) in one
   shared helper used by both the `wait_checks` chop and the runner fallback;
   pending-plan detection reuses the existing pending-planqueries
   (`plan_pending.py`) keyed by agent; vacuous release always emits a
   diagnostic; add the epic-membership cycle guard from 3.5.
5. **TUI**: phase-aware lanes per 3.7 (`agents` + transitional `epic` lane
   reusing the bead-badge machinery, source-annotated `bead (from agent)`);
   wait-modal toggle + explainer; `wait_spec_label` update; transient notice
   on vacuous release.
6. **Rollout**: ship default-false with diagnostics; add a `--dry-run`-style
   `sase` affordance or log line showing what `%wait` *would* have waited for
   under `epic=true` so users can preview; defer `epic=created` (early-start
   mode) to a follow-up once closure semantics prove out.

**Why this shape:** closure semantics make `epic=true` exactly equivalent to
the manual two-step flow users run today, so behavior is predictable,
testable (assert waiter start time == epic close time), and explainable in one
sentence: *"%wait(planner, epic=true) is %wait(planner) followed
automatically by %wait(bead=<whatever epic planner created>), and a no-op if
planner never creates one."* Everything else — the default, the terminal
semantics, STATE C, the link audit — exists to keep that sentence true in the
flows users actually run.

## 5. Open questions for the lead / other swarm reports to check me on

- Is there truly no existing boolean `%wait`/`%queue` keyword parser to reuse?
  I found none; if one exists my "first boolean" claim — and part of the parse
  estimate — is wrong.
- Does plan **rejection** reliably clear every pending-plan signal the waiter
  would key on? If rejection leaves residue, STATE C needs its own timeout
  backstop (recommend one regardless, e.g. 24h, configurable).
- Should `epic=true` also follow `phase_bead_id` (phase workers that spawn
  sub-epics?) or strictly `epic_bead_id`? I recommend strictly epic, with
  phases out of scope for v1.
- The `{{ wait.* }}` / `agents[…]` Jinja namespaces expose waited agents'
  outputs — should the discovered epic id be injected there at start time so
  the prompt body can reference it? That closes the loop on "pass that epic
  bead ID" ergonomics and is probably cheap once discovery exists. Recommend
  yes if cheap.
