# Goals for SASE: lifecycle, provenance, evidence, and a fast active index

## Executive conclusion

Goals are a good addition to SASE, but only if a goal represents a durable user intent
rather than another name for an agent run, bead, or plan. The useful cardinality is:

> one goal can span many agents, retries, plans, beads, Patches, stitches, and artifacts;
> every agent run has exactly one primary goal binding.

I would **not** require agents to invoke `/sase_new_goal` at the start of a conversation.
That makes a system invariant depend on model compliance, spends a tool round trip before
useful work, races with other launches, and fails completely for crashes, hidden runners,
and handoff commands. It is also too easy to create one duplicate goal per swarm member.
SASE already controls the launch boundary and already knows the project, submitted prompt,
agent lineage, plan, bead, and parent run. Goal selection or creation belongs there, before
the provider process starts.

The design I recommend is:

1. Add `goal:<stable-id>` as a first-class artifact and store goal history as immutable,
   intent-named events in the project's existing intrinsic **agents sidecar**.
2. Build a disposable machine-local projection containing only active goals, plus a small
   pending-review projection. `sase goal list --active` reads that projection in
   `O(n_active)`; it never scans done goals or replays history on the foreground path.
3. Bind a goal at launch. Inherit it across retries, pipes, questions, monitors, child
   agents, and plan follow-ups. Reuse an active goal only from high-confidence structured
   evidence (plan, ancestry, bead/epic, explicit selection), never a silent fuzzy match.
4. Preserve exact launch-prompt provenance as content-addressed prompt snapshots. Store
   both the submitted unit prompt and its digest on the goal's creation record, then link
   the eventual canonical agent/prompt archive when it becomes available.
5. Add an unremovable `builtin@goal` finalizer after `builtin@commit`. Every normal model
   return must choose `keep_open` or `close`. Handoff commands make the equivalent choice
   atomically; crashes and kills deterministically keep the goal open.
6. Treat `close` as an **agent completion claim**, not human verification. Closing moves
   the goal from `active` to `done` and sets `verification: pending`. It emits the one
   notification that deserves user attention: “Goal ready to verify.” The user can verify,
   waive, or reopen it.
7. Let the host, not the model, validate completion evidence. A close declaration maps the
   goal's criteria to durable artifact references selected from a host-produced evidence
   catalog. For code-changing work, successful commit finalization and host-observed
   verification are required by default. The goal event embeds the accepted evidence refs;
   artifact-link projections are therefore inseparable from the state transition.
8. Add a top-level **Goals** tab between Agents and Artifacts. Its default view contains
   “Needs review” and “Active” lanes, with a goal detail deck and the existing artifact-link
   rail/trail for direct jumps into artifacts and the exact rows on the Agents tab.

This is not a small feature. It crosses the shared Rust domain, launch planning, sidecar
publication, artifact references and relations, finalizer protocol, notification policy,
and the TUI. It should be implemented as an epic with a temporary beta flag only while
partially landed, then made unconditional before the epic is considered complete.

## What I examined

The recommendation is based on the current SASE implementation, not a greenfield model.
The most consequential existing facts are:

- Tale and epic plans already require a `goal` string through the Rust-backed plan schema
  (`src/sase/sdd/plan_validate.py` and the `sase_core` plan module).
- `SASE_PLAN` is attribution for particular plan/commit paths, not a universal launch
  contract. General spawning explicitly scrubs inherited `SASE_PLAN`, while plan approval
  and agent-session attachment set it on specific paths
  (`src/sase/agent/launch_spawn.py`,
  `src/sase/main/plan_direct_approval_run.py`, and
  `src/sase/agent/_agent_session_attach_launch.py`).
- The runner already captures both `submitted_xprompt.md` and alias-resolved
  `raw_xprompt.md` before provider execution
  (`src/sase/axe/run_agent_runner_setup_prompt.py`). The original prompt is also already
  available to finalizer recovery (`src/sase/finalizers/controller.py`).
- Finalizer declarations already have the right reliability primitives: a host-issued
  context, digest-bound obligations, a turn nonce, an interprocess lock, stale-context
  rejection, ordered providers, and host execution after the model returns
  (`src/sase/finalizers/declaration.py`, `declaration_store.py`, and
  `declaration_manifest.py`).
- Artifact links already use immutable operations, reducers, a machine-local aggregate,
  projected relations, generated pages, and a TUI link rail with cross-tab navigation.
  Goal relationships should extend this system rather than invent a second graph
  (`docs/artifact_links.md` and `sase_core::artifact_link`).
- The agents sidecar is already the canonical cross-machine home for agent identity and
  prompt archives, and it already handles content-addressed objects, per-owner authority,
  pull/recompute/retry, and a durable publication outbox (`docs/agents_sidecar.md`).
- Successful agent completion currently creates a `JumpToAgent` user notification with a
  `done` tag (`src/sase/axe/run_agent_runner_finalize.py`). This is the attention signal
  Goals are intended to replace, not merely supplement.
- ACE's performance rules prohibit synchronous I/O and history-scaled work on the event
  loop or startup path. Cached data should paint immediately, refresh in a worker, and be
  patched selectively.

The storage recommendation also follows established systems practice. W3C PROV separates
activities, entities, and agents, and permits several agents to be associated with one
activity; that is a better conceptual fit than equating a goal with one agent
([W3C PROV Primer](https://www.w3.org/TR/prov-primer/)). CQRS guidance recommends a
query-optimized projection distinct from the write model, while explicitly warning about
staleness and synchronization
([Microsoft CQRS pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)).
Event-sourcing guidance recommends intent-named immutable events, versioned schemas, and
compensating events instead of rewriting history
([Microsoft Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)).
Materialized views are disposable caches and their acceptable staleness must be explicit
([Microsoft Materialized View pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/materialized-view)).

## Critique of the proposal

### What is strong

The motivation is sound. Agent completion is an execution fact, not an intent-level
milestone. A research swarm may complete four agents while producing only one result the
user should review. An epic may complete many phases before its outcome is ready. A quick
answer may have no commit or bead but still completely satisfy its intent. Moving the
attention signal from “a process stopped” to “the intended outcome is claimed complete” is
the right abstraction.

The performance requirement is also exactly right. A goal dashboard will be consulted far
more often than goal history. Its hot path should be proportional to what can still change,
not to the lifetime number of completed goals.

Requiring explicit end-of-turn intent is valuable. It prevents SASE from treating a polite
final answer as proof that a larger outcome is finished, and it provides a natural place to
record remaining work and evidence.

### Where I would change the requirements

#### 1. Enforce the invariant at launch, not through a first-turn skill

The proposed `SASE_PLAN` check plus `/sase_new_goal` is useful as a sketch, but it is not a
reliable enforcement point:

- the model can forget or call it after already doing work;
- plan association is broader than whether one environment variable survived a particular
  launch path;
- retries, handoffs, hidden agents, workflow steps, and crashes do not fit the normal
  conversation-start shape;
- several swarm members can race and create near-identical goals;
- making every agent enumerate active goals adds latency and prompt/tool traffic even when
  inheritance is unambiguous.

The host must compute a `GoalBindingPlan` as part of typed launch planning and persist the
binding after the concrete agent identity is known but before provider invocation. The
provider receives `SASE_GOAL_ID`, goal text in its instructions, and the same data in
`agent_meta.json`. A `/sase_goal` skill can remain useful for showing, refining, or
explicitly splitting a goal, but it must not carry the invariant.

#### 2. Do not create one top-level goal per agent

The system should guarantee a binding for every run, not a distinct visible goal for every
run. Helpers inherit the parent's goal. Retries and recovery turns retain it. Plan phases
share the plan goal. Internal maintenance agents attach to an internal/system goal and do
not pollute the user dashboard. This distinction is necessary for the feature to remain
intuitive after the first large swarm.

#### 3. Separate “done” from “verified”

An agent is well placed to claim that its goal is complete, but it cannot turn that claim
into independent human verification. Use two axes:

```text
work_status: active | done
verification: none | pending | verified | waived
```

An agent's `close` decision produces `done/pending`. Human acceptance produces
`done/verified`; an explicit human choice can produce `done/waived`; rejected evidence
produces a compensating `reopened` event and returns to `active/none`. This lets the desired
notification mean exactly “please verify this claimed outcome.” GitHub Checks similarly
distinguishes a completed status from conclusions such as success, failure, and
`action_required`, demonstrating the value of not collapsing terminal execution and the
meaning of its result into one boolean
([GitHub Checks API](https://docs.github.com/en/rest/guides/using-the-rest-api-to-interact-with-checks)).

#### 4. “All agents explicitly decide” needs defined abnormal and handoff semantics

A killed process cannot decide. Nor does a successful `sase plan propose`, monitor,
question, gate, or pipe follow the normal finalizer path. The enforceable rule should be:

> Every normal provider return submits `keep_open` or `close`. Every intentional handoff
> command atomically records `keep_open`, `transfer`, or a prepared close intent. Every
> abnormal termination records a host-authored attempt outcome and keeps the goal open.

This preserves the spirit of the requirement without pretending a crash made a decision.

#### 5. Define freshness, not impossible global immediacy

“Available from any machine” and “lightning fast” can be achieved with a published source
of truth plus local projections, but a Git-backed multi-machine system cannot guarantee
simultaneously instant global visibility, offline operation, and strongly consistent reads.
I recommend local-fast/eventually-consistent reads with an explicit freshness watermark.
Goal mutations should publish synchronously with the existing bounded pull/rebase/push
retry before they report success. TUI reads should never wait for that network path: they
paint the local projection, show `synced at`/`stale` state, and refresh in the background.

#### 6. Evidence must be host-observed, not persuasive prose

A free-text “tests passed” field is not evidence. The finalizer should expose an eligible
evidence catalog derived from run artifacts, tool/monitor receipts, explicit snapshots,
plan refs, and commit-finalizer results. The agent may select refs and explain their
relevance, but cannot invent a path, exit status, or stitch. A code-changing goal should
not close merely because a commit exists: successful verification is required unless the
goal had a human-set `verification: not_required` policy before the closing turn.

## Domain model

### Goal versus neighboring concepts

| Concept | What it represents | Lifecycle owner |
| --- | --- | --- |
| Goal | A desired user-visible outcome and its completion claim | user intent + goal finalizer |
| Agent | One execution attempt or contributor | runner |
| Plan | A proposed route to an outcome | planning workflow |
| Bead | A schedulable work item, issue, or phase | bead workflow |
| Patch | A review/landing lane | VCS provider |
| Artifact | Durable evidence or context | artifact subsystem |

This boundary matters because beads are the most tempting alternative. Reusing beads would
avoid a new store, but it would make every answered question and internal helper a task
tracker record, conflate “work still scheduled” with “outcome not achieved,” and make a
single goal spanning many beads awkward. Goals should link to beads, not become beads.

### Identity and cardinality

- A goal has an opaque stable ID, for example `goal:sase-g7k3m9d2q4`. The title is editable
  and never part of identity.
- IDs should be deterministic for idempotent creation where possible: hash the project key
  and the launch unit's stable idempotency key or canonical plan ref. Explicit human-created
  goals can use a random 96- or 128-bit identifier.
- Every agent run has exactly one `primary_goal_id`.
- A goal may have any number of attached agents and artifacts.
- A run may mention other goals as ordinary artifact references, but only one primary goal
  drives finalization and notification.
- A done goal cannot accept a new run silently. Launch must explicitly reopen it or create a
  follow-up goal linked as related/superseding.

### Compact current record

The reduced record should contain roughly:

```yaml
schema_version: 1
goal_id: sase-g7k3m9d2q4
project_key: gh_sase-org__sase
title: Add reliable project goals
objective: >-
  Give every SASE agent a durable intent and notify the user only when that
  intent is claimed complete.
work_status: active
verification: none
visibility: user
created_at: 2026-09-26T...
updated_at: 2026-09-26T...
revision: sha256:...
creator:
  run_id: ...
  agent_ref: agent:bryan.athena.research.2m.cdx
origin_prompts:
  - role: submitted_unit
    sha256: ...
    object_ref: ...
plan_ref: plan:202609/...
criteria:
  - id: outcome
    text: The requested outcome is delivered.
    evidence_policy: deliverable
closure_policy:
  verification_required: true
  eligible_role: coordinator
```

This is a projection, not the authoritative mutable file.

### Immutable event stream

Store intent-named, schema-versioned events such as:

- `goal_created`
- `agent_attached`
- `plan_attached`
- `objective_refined`
- `criterion_added` / `criterion_revised`
- `attempt_finished_keep_open`
- `completion_claimed`
- `verification_accepted`
- `verification_waived`
- `goal_reopened`
- `goal_superseded`

Each event contains `goal_id`, content digest, actor, timestamp, `basis_revision`, causal
run/agent identity, and its typed payload. Events should record intent (“completion was
claimed with these refs”), not only a state assignment (“status became done”). Corrections
are compensating events; published events are never edited.

`basis_revision` gives optimistic concurrency. A close prepared against stale criteria or
newly attached work must fail and refresh finalizer context. When independently published
events are discovered concurrently, the reducer should fail safe to **active/conflicted**,
never pick a close by wall-clock order. This is preferable to a false completion alert.

## Launch-time assignment

Goal assignment should be a typed part of every launch slot in `sase_core`, with Python
performing only the I/O and sidecar transaction. Resolve in this order:

1. **Plan identity.** If the launch is associated with a plan, use its stored `goal_id`, or
   lazily create a deterministic goal from the canonical plan ref and required `goal` text
   for a legacy plan.
2. **Explicit operator choice.** A launch request field, TUI selector, CLI option, or a new
   `%goal(<id>)` directive names an existing active goal. `%goal(new)` explicitly forces a
   split. The typed field should be canonical; the directive is prompt syntax for it.
3. **Lineage inheritance.** Retry, resume, pipe, question follow-up, monitor recovery,
   agent-session child, and parent-launched helper inherit the requester's goal by default.
4. **Structured project evidence.** An exact shared epic/bead, Patch, or canonical plan can
   yield one high-confidence active candidate. If several candidates remain, interactive
   launch asks; noninteractive launch creates a new goal rather than guessing.
5. **New ad hoc goal.** Create one from the exact submitted unit prompt, with a deterministic
   title preview and a default criterion appropriate to an answer-style run.

Do not use semantic similarity as an automatic linker. It is useful for suggestions, but a
wrongly merged goal can be closed by unrelated evidence and is more damaging than a
duplicate. A later `sase goal suggest` or merge workflow can use prompt similarity without
putting it on the correctness path.

The assignment transaction should complete after agent naming and prompt capture but before
provider invocation:

1. calculate/confirm the binding;
2. persist the prompt object and goal event locally;
3. publish the sidecar transaction with a bounded non-fast-forward retry;
4. write `goal.json` and `agent_meta.json.goal_id` in run artifacts;
5. export `SASE_GOAL_ID` and render the goal into provider instructions;
6. start the provider.

If step 2 fails, launch fails closed: the invariant was not established. If the remote is
temporarily unavailable, policy must be explicit. My default would also fail closed for a
new user-visible goal because otherwise another machine cannot satisfy the stated access
requirement. A permanent `goals.offline_policy: queue` configuration could trade that
guarantee for offline availability, while visibly marking the goal `local-only`; it should
not be a silent fallback.

### Planner and plan behavior

Planner agents do not need an exemption. They receive a launch-bound goal like every other
run. `sase plan propose` then performs an intentional goal handoff:

- validate the plan's required `goal` text;
- inject a stable `goal_id` into archived plan metadata (or a canonical `GOAL` header);
- refine the existing goal's objective from the approved plan goal while retaining history;
- attach `plan:<path>` as the definition source;
- record the planner's `transfer/keep_open` decision;
- pass `SASE_GOAL_ID` explicitly to the coder or epic phases.

Every phase of an epic shares the same overall goal. Phase agents normally keep it open.
The host marks closure eligibility only when required plan members and phase beads are
terminal and no other required contributor remains active. The last eligible normal
finalizer can then claim completion. If the existing epic topology cannot provide an agent
with enough context to assess the whole result, add a small coordinator/summary member; do
not auto-close solely because a phase count reached zero.

For new plans, I would add explicit acceptance criteria to the plan schema. A required
`goal` sentence is an objective, not a completion contract. Keep this light—one to eight
short criteria, stable IDs, and an evidence policy—not a second detailed specification.
Legacy plans receive a single default criterion and can be refined when next activated.

## Prompt provenance

The creator association should survive even when an answer has no commit and the agent
page is never otherwise published. At goal creation:

- snapshot the exact per-agent submitted prompt bytes into a content-addressed object in
  the agents sidecar;
- record its SHA-256 and role (`submitted_unit`);
- optionally record the alias-resolved `raw_xprompt` digest as a second role, without
  confusing it with the original;
- record the creator run ID and eventual global `agent:` identity;
- when a canonical prompt archive entry is later published, project/link it without
  replacing the immutable creation provenance.

Do not copy the expanded system prompt or AGENTS instructions into the goal. They are
runtime context, can be very large, and may contain host details. The submitted user/unit
prompt is the provenance the requirement asks for. Multi-prompt launches should additionally
record the parent launch/group digest so sibling provenance can be reconstructed without
claiming that every member received the full swarm text.

Prompt content has the same privacy implications as the existing agents sidecar. Goal
initialization must respect its private visibility and disabled state. The Goals list shows
only a title and digest/creator metadata; opening the original prompt is an explicit detail
action. A project with cross-machine goals enabled but no publishable agents sidecar should
fail `sase goal doctor` and refuse strict cross-machine goal creation rather than quietly
pretend it is shared.

## Storage and `O(n_active)` access

### Durable truth

Reuse the intrinsic agents sidecar rather than introduce a sixth project repository. Goals,
agents, and prompt objects share a privacy boundary and are updated at the same lifecycle
points. A possible layout is:

```text
goal-events/v1/<goal-shard>/<event-digest>.json
goal-prompts/objects/sha256/<prefix>/<sha256>
goals/<goal-id>/README.md              # deterministic generated page
goals/README.md                        # bounded current index, if desired
```

Content-addressed event/object paths make independent writers additive. As with agent
publication, pull/rebase must regenerate shared pages before a bounded push retry. The event
bytes are canonical; Markdown pages are projections.

### Machine-local read models

Maintain under the project machine state, not in the workspace:

```text
~/.sase/projects/<key>/goals-active-v1.json
~/.sase/projects/<key>/goals-review-v1.json
~/.sase/projects/<key>/goal-events-outbox.json
```

`goals-active-v1.json` contains only compact summaries whose current `work_status` is
`active`, plus a `source_frontier_digest`, `generated_at`, and sync watermark. Listing parses
one bounded file and walks exactly those rows: `O(n_active)` time and space. `show <id>` uses
a per-goal reduced snapshot or direct map lookup. `goals-review-v1.json` contains only
`done/pending` claims, so the attention queue is independent of all verified history.

Every accepted mutation updates the relevant goal snapshot and patches the active/review
projection under one machine-local lock. It must not replay every historical event. Full
replay is reserved for `sase goal doctor --fix`, schema migration, or background sync.
Losing a projection is safe because it is rebuildable from durable events. The foreground
query can report `stale: true` while serving the last valid snapshot; it must never scan the
sidecar as a fallback on a TUI keypress.

This meets the precise performance requirement: done-and-verified goals add bytes to durable
history, but add no row and no iteration to the active query. The one caveat is repair cost,
which is intentionally off the foreground path.

### Cross-machine convergence

- Goal commands that mutate durable state use the hidden machine-owned sidecar clone, not a
  numbered workspace's nested clone.
- A successful create/attach/close reports success only after durable publication receipts
  exist, with an outbox for recoverable interruption.
- `sase agent sync` can drain goal publication too, while `sase goal sync` offers a focused
  command.
- The scheduler performs periodic fetch/reduce. The TUI checks a cheap change token and
  schedules a pump-free worker only when the token changes.
- Every view displays the last successful sync time and whether local writes are pending.
- A close event prepared against an old goal revision is rejected like a stale finalizer
  context and retried through one bounded recovery turn.

If sub-second global propagation later proves necessary, keep the Rust goal command/reducer
contract and add a gateway transport. Do not make a network service a prerequisite for the
initial local-first implementation.

## Artifact-reference and link model

Add `goal` as a live, reserved artifact-reference kind in `sase_core`, resolved through the
agents/goals sidecar. It should reject fragments, have completion support, and render the
generated goal page. Add narrowly semantic, projection-owned relations:

| Relation | Direction | Meaning |
| --- | --- | --- |
| `pursues` / `pursued-by` | `agent -> goal` | this agent run contributes to this goal |
| `defines` / `defined-by` | `plan -> goal` | this plan supplies the approved goal definition |
| `evidences` / `evidenced-by` | `artifact -> goal` | this durable artifact supports a completion criterion |

The first two project from durable goal/agent/plan fields. `evidences` projects from an
accepted `completion_claimed` event. Users should not manually remove these derived facts;
they change the goal record or reopen/replace the claim. Existing `related`, `supersedes`,
and `derives-from` remain available for contextual links.

Embedding accepted evidence refs inside the closure event has an important atomicity
property: the reducer cannot produce `done` without also producing the artifact-link rows.
There is no window in which a goal is closed but its evidence links failed to write. The
artifact-link aggregate and Goal page can be rebuilt from the same durable truth.

## The goal finalizer

### Selection and ordering

Add a trusted built-in provider and make it unremovable:

```yaml
finalizers:
  defaults: [commit]
  required: [goal]
  instances:
    commit:
      use: builtin@commit
      after: []
      max_attempts: 2
      refusal: defer
    goal:
      use: builtin@goal
      after: [commit]
      max_attempts: 2
      refusal: fail
```

`builtin@goal` should be in core/Python, not a shell command or optional plugin. The
finalizer context gains a `goal` obligation containing the bound goal ID, current revision,
closure eligibility, criteria, and an eligible evidence catalog. Because the instance is
always required for a normal goal-bound run, `sase final context` always requires a goal
payload even when no repository is dirty.

This provider runs after commit so the executor can attach actual stitch and Patch results.
Later mutation cannot silently invalidate its evidence: if the controller reactivates
commit or the goal revision changes, the context digest changes and goal finalization is
re-evaluated.

### Declaration shape

A compact payload could be:

```json
{
  "action": "close",
  "summary": "Implemented the goal and verified the supported workflows.",
  "criteria": [
    {
      "criterion_id": "outcome",
      "result": "met",
      "evidence_refs": [
        "stitch:sase@0123456789abcdef0123456789abcdef01234567",
        "tool:verify-4f91"
      ]
    }
  ],
  "residual_risks": []
}
```

For `keep_open`, require a bounded reason and optional next-step text:

```json
{
  "action": "keep_open",
  "reason": "The report is complete, but the synthesis agent has not run.",
  "next_step": "Synthesize the four researcher reports."
}
```

The action names should match the user's mental model even if the stored event is called
`completion_claimed`.

### Evidence rules

The final context should enumerate evidence the host can attest, including:

- the current agent response/run artifact and its digest;
- registered explicit file/research artifacts;
- plan, bead, Patch, and agent refs associated with the goal;
- commit-finalizer stitch results;
- prepared-monitor results and `sase tool run` verification receipts;
- durable test/report artifacts produced by configured finalizers.

Validation rules:

1. Every current criterion is `met`; `not_applicable` is allowed only when the criterion or
   goal policy already permits it, not as a closing-turn self-waiver.
2. Every referenced item resolves to the eligible catalog or to a resolvable durable
   artifact whose digest is captured at acceptance.
3. At least one deliverable/outcome ref is required. The original prompt is scope, not
   evidence.
4. If repositories changed, every required repository finalizer succeeded, no deferral or
   unresolved dirty state remains, and at least one host-observed successful verification
   receipt is required unless a pre-existing human policy says otherwise.
5. The agent response can satisfy an answer goal's deliverable criterion. It is not by
   itself sufficient verification for a code-change goal.
6. The agent must disclose residual risks. An empty list is an explicit assertion, not an
   omitted field.
7. Goal revision and closure eligibility must still match immediately before publication.

On acceptance, the host writes/publishes one `completion_claimed` event containing the
evidence selection, derives the `evidences` links, updates projections, and only then emits
the notification. If publication fails, the goal remains active and the run does not report
full completion.

### Handoffs and failures

- `sase plan propose`: attach the plan, keep open, and transfer to the approved follow-up.
- `sase pipe`: successor inherits the same goal; record transfer before terminating.
- `sase questions` / gates: keep open and record waiting state, without a done notification.
- `sase monitor start`: the prepared final declaration already contains the close/keep
  choice; successful verification authorizes host completion, failure keeps the goal open
  and launches recovery.
- retry/recovery: inherit the goal and prior evidence; do not create a new one.
- kill/crash/provider failure: host records an aborted/failed attempt, keeps the goal active,
  and may still send an operational failure notification.
- hidden helper success: no user completion notification and no close authority unless the
  launch explicitly delegated it.

## Notification policy

Once goal binding is universal, successful agent completion should stop being an attention
notification by default. It remains visible in Agents history, but it should not create an
unread item merely because one contributor stopped successfully.

Emit a user notification for:

- `active -> done/pending`: **Goal ready to verify**, action `JumpToGoal`, dedup key
  `goal:<id>:claim:<revision>`;
- goal/recovery failure that needs intervention;
- a finalizer deferral, publication failure, or evidence conflict;
- an explicitly configured operational alert.

Do not emit one for `keep_open` success. If the user rejects a claim, reopening should
update/dismiss the claim notification and optionally offer “launch follow-up on this goal.”
Reading a contributor's Agent row must not mark the goal verified. Notification read state,
goal verification, and agent dismissal are separate actions.

The wording matters. “Goal complete” overstates what happened. “Goal ready to verify” or
“Agent claims goal complete” tells the user why attention is needed.

## TUI design

### Placement

Goals deserve a top-level tab, not merely an Artifacts subtab. They are live intent and the
new attention surface, whereas Artifacts is a record browser. Keep Agents as the default and
use:

```text
Agents | Goals | Artifacts | Services
```

The top bar can show a small accent badge for pending review without making ordinary active
count an alarm.

### Layout

The default Goals tab should be a calm two-column workspace:

```text
┌ Needs review (1) / Active (3) ─────┬ Goal detail ──────────────────────────┐
│ ⚑ Add reliable project goals       │ Add reliable project goals            │
│ ● Improve remote dispatch      2a  │ ACTIVE · synced 12s ago               │
│ ● Answer storage question      1a  │                                       │
│                                    │ Objective                             │
│                                    │ Completion criteria                   │
│                                    │ Contributors                          │
│                                    │ Evidence / linked artifacts           │
│                                    │ Recent attempts and next step         │
└────────────────────────────────────┴───────────────────────────────────────┘
```

Rows should show status glyph, concise title, age, contributor count, plan/bead markers,
and a stale/local-only badge only when relevant. The detail deck should put objective and
criteria before chronology. Evidence is grouped by criterion, not dumped as an undifferentiated
graph.

Reuse the existing LinkRail, full links panel, and 32-hop back/forward trail. Selecting an
`agent:` link switches to Agents and restores the precise project/query/row on back. Other
refs go to the matching Artifacts pane. `$` remains the general link action; Enter follows
the highlighted contributor/evidence row. A review claim offers Verify, Reopen, and Waive
as deliberate actions with confirmation and an optional note.

History should not load by default. An explicit “Done” filter or search reads a separate
bounded/paginated history index. Thus adding years of completed goals cannot slow first
paint, arrow navigation, or the active list.

### Performance implementation

- Paint the cached active/review projection immediately.
- Never fetch, glob, parse sidecar events, or run subprocesses on the Textual event loop.
- Refresh through a thread worker/pump-free task and revalidate tab/selection after it
  returns.
- Patch changed rows and detail cards; rebuild only when grouping membership changes.
- Debounce detail rendering, never list highlighting.
- Give the goal projector a cheap mtime/source-frontier change token so quiet auto-refresh
  ticks do almost no work.
- Measure p95 key-to-paint under the existing `<16 ms` target and add startup/idle trace
  assertions before enabling the tab by default.

## CLI and agent experience

Suggested commands:

```text
sase goal list [--active|--review|--done] [-j]
sase goal show [<goal-id>|current] [-j]
sase goal create --title ... --objective ... [--criterion ...]
sase goal attach <goal-id> [--agent ...|--plan ...]
sase goal reopen <goal-id> --reason ...
sase goal verify <goal-id> [--note ...]
sase goal waive <goal-id> --reason ...
sase goal sync [--check]
sase goal doctor [--fix]
```

Do not offer a routine `close` CLI to agents; their close goes through the stale-safe
finalizer. Human closure/verification is a different authority and should be named as such.

At provider startup, instructions should include a small immutable block:

```text
Goal: Add reliable project goals
Goal ref: goal:sase-g7k3m9d2q4
Your role: contributor (may keep open; close currently eligible: no)
```

The generated `/sase_final` skill then explains the required goal payload from the host
template. A generated `/sase_goal` skill can explain `show current`, criteria refinement,
and explicit split/relink flows. I would not call it `/sase_new_goal`, because new creation
is the exceptional branch and the name encourages duplication.

## Reliability, safety, and observability

Key invariants to test in Rust and at integration boundaries:

1. A new provider process cannot start without a persisted goal binding.
2. A normal return cannot complete without exactly one goal decision.
3. No close transition exists without at least one accepted durable evidence ref.
4. A stale goal revision cannot close.
5. Concurrent attach versus close resolves open/conflicted, never falsely done.
6. A handoff records its goal transition before it kills the runner.
7. A retry, recovery, and monitor completion retain the same goal ID.
8. A plan-backed launch uses the plan goal and stable ID across every phase.
9. Active listing reads no done-goal event or page.
10. A closure notification is emitted only after durable goal publication.
11. Suppressing a routine success notification never suppresses failures or deferrals.
12. Rebuilding projections from events yields byte-identical active/review state.

Add telemetry for assignment source, create/link latency, active-list parse latency,
projection rebuild time, stale-context rejections, evidence rejection reason, publication
lag, close-to-notification latency, and reopen rate. Reopen rate is the most meaningful
quality signal: a high rate suggests criteria or evidence policy is too weak.

`sase goal doctor` should diagnose missing prompt objects, dangling agent/plan/evidence
refs, invalid reducers, orphaned/tampered events, active projection drift, unpublished
outbox items, sidecar freshness, impossible lifecycle combinations, and agents missing a
binding after the feature's cutover version.

## Alternatives considered

### Mandatory `/sase_new_goal` at conversation start

Rejected as the invariant mechanism. It is model-dependent, slow, duplication-prone, and
does not cover abnormal termination or non-conversation runners. Keep a skill only for
manual goal management.

### Reuse beads

Rejected. Beads schedule work; goals represent outcomes and attention. A goal may span many
beads or none. Reusing beads would make everyday questions and helpers pollute task state.

### Treat an agent session or clan as the goal

Rejected. Sessions describe execution topology. A goal must survive retries, cross machine
boundaries, replanning, and a change in topology; multiple independent sessions may pursue
one goal.

### Mutable Markdown file per goal

Rejected as authoritative truth. It is pleasant to read but produces concurrent-edit
conflicts, loses intent history, and makes safe close/attach races difficult. Generate the
Markdown page from immutable events instead.

### Replay every goal event for each list

Rejected because done history would directly violate `O(n_active)`. Rebuildable active and
review projections are the correct hot-path boundary.

### New goals sidecar repository

Not recommended initially. It gives clean ownership but adds configuration, consent,
cloning, sync, and failure modes. The agents sidecar already owns the sensitive prompt and
agent records that goals must reference. Revisit only if write volume or access control
diverges materially.

### Central online goal service

Not recommended for v1. It could provide stronger freshness and serialization, but it would
make ordinary local agents depend on service availability. Keep the Rust contracts
transport-neutral so the fleet gateway can be added later.

## Implementation shape

This should be an epic, approximately in these seams:

1. **Rust goal domain and wire contract**
   - goal IDs, events, reducer, lifecycle policy, optimistic revisions, projection records;
   - `goal` artifact kind and the three relations;
   - Python bindings and schema/version fixtures.
2. **Durable store and fast projection**
   - agents-sidecar event/prompt-object publication, locks, outbox, sync, doctor;
   - active and review projectors with performance tests;
   - read-only CLI first.
3. **Launch binding and provenance**
   - typed `GoalBindingPlan` on every launch unit;
   - inheritance and structured candidate matching;
   - prompt snapshots, env/meta fields, plan `goal_id`, legacy-plan lazy adoption;
   - fail-closed invariant tests for every launch path.
4. **Goal finalizer and evidence**
   - `builtin@goal`, required ordering, manifest template and validation;
   - host evidence catalog, commit/monitor receipts, handoff semantics;
   - atomic completion event and projected links.
5. **Notifications and TUI**
   - goal-review notification and routine-success suppression;
   - top-level Goals tab, detail deck, link rail/trail, review actions;
   - startup, navigation, refresh, and idle performance measurements.
6. **Cutover and hardening**
   - doctor/migration behavior for legacy agents/plans;
   - fleet compatibility checks and schema negotiation;
   - remove the temporary beta branch and make goal binding unconditional.

Because early phases would otherwise expose partially functional user behavior, an epic may
use a default-off beta flag while those phases land. Per SASE's flag policy, the epic should
delete the off branch and remove the flag before declaring the feature complete; this is not
a permanent preference. During migration, old archived agents remain explicitly “legacy /
unbound.” Do not synthesize a goal for every historical run or scan history at startup.

## Explicit requirement adjustments

I recommend adopting these changes to the stated requirements:

1. Replace “each non-planner agent invokes `/sase_new_goal`” with “the host durably binds
   every provider run to a goal before provider invocation.” Planners follow the same rule.
2. Interpret “all agents have a goal” as exactly one primary binding, not one newly created
   visible goal per agent. Helpers and retries inherit.
3. Interpret agent “close” as `done/verification-pending`; human verification remains a
   separate transition.
4. Require explicit decisions on normal returns and atomic decisions on intentional
   handoffs; crashes/kills automatically keep open with host-authored failure evidence.
5. Require host-resolvable evidence mapped to completion criteria. Self-report alone is
   sufficient only when the response itself is the deliverable, such as an answer goal.
6. Add lightweight acceptance criteria, including to new plans. Without them, evidence can
   prove activity but not satisfaction of the intended outcome.
7. Define cross-machine access as immediate local reads plus explicit sync freshness and
   durable publication on mutations. Do not claim strong real-time consistency from Git.
8. Show pending-review done goals in their own small projection; verified done history must
   never affect active-list performance.
9. Suppress routine successful agent-completion notifications only after goal binding and
   goal-close notifications are reliable; preserve failures, deferrals, and operational
   alerts.

## Recommended solution

Build Goals as a first-class, event-sourced project intent in `sase_core`, persisted in the
agents sidecar and exposed through an active-only materialized projection. Bind goals at the
host launch boundary, not inside the model. Carry one stable goal across planning,
implementation, swarms, retries, and handoffs. Make `builtin@goal` a required finalizer that
forces `keep_open` or `close`, validates a structured completion claim against host-observed
durable evidence, and runs after commit. Store accepted evidence in the closure event so its
artifact links and state transition are atomic. Treat closure as `done/pending verification`,
emit one “Goal ready to verify” notification, and replace routine successful-agent unread
signals with this intent-level signal. Present active and pending-review goals in a dedicated,
fast Goals tab that reuses SASE's existing link rail and cross-tab navigation.

That design satisfies the core idea while avoiding its main failure modes: duplicate goals,
model-enforced invariants, false completion, history-scaled reads, and a second disconnected
relationship system.
