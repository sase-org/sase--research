# SASE Goals: an outcome control plane and verification inbox

## Executive recommendation

Build Goals, but change the proposed enforcement and completion semantics.

A Goal should be a durable project outcome that can outlive any one agent, plan,
workspace, or machine. Every new LLM-backed SASE agent should have exactly one primary
Goal binding before the provider starts. The launcher should establish that binding;
an instruction that asks the model to invoke `/sase_new_goal` cannot enforce the
invariant reliably.

The low-friction design is:

1. Reuse a Goal from deterministic context (an explicit Goal reference, an associated
   plan, a parent/session/handoff, a repeat or fan-out root, or one unambiguous linked
   bead).
2. Otherwise create a provisional Goal from the exact submitted launch prompt. This
   gives the agent a valid Goal without asking the user to write one.
3. Let the agent confirm or refine the human-readable objective, criteria, and title.
   Preserve the original prompt as immutable intent so refinement cannot erase what the
   user actually asked for.
4. Require a non-removable `builtin@goal` finalizer on every normal agent return. Its
   choice is **Keep open** or **Claim complete**, not “silently infer completion from
   agent exit.”
5. Treat an agent's close choice as an evidence-backed completion claim. It moves the
   Goal to **Ready to verify** and creates the one notification that deserves the
   user's attention. A human **Verify**, **Waive**, or **Reject and reopen** action
   settles the claim. Only verified/waived/canceled/superseded Goals are cold history.
6. Give Goals a first-class top-level TUI tab, not merely a buried Artifacts subpane.
   The default view is a project-scoped verification inbox followed by active work,
   with one-key jumps to live Agents rows and linked artifacts.

This is a good feature idea. It corrects a real category error in the current product:
an agent stopping is a process event, while the user cares about an outcome. The main
risks are goal spam, agents moving their own goalposts, privacy expansion from archiving
every launch prompt, and distributed conflicts. All four are manageable if Goals are
host-bound, revisioned, provenance-rich, and explicitly reviewed.

## Research basis

I reviewed the requested prior synthesis,
`research:202609/goal_outcomes_and_verification/goal_outcomes_and_verification.md`, via
the audited artifact reader before starting this analysis. I did not inspect any
researcher-suffixed peer report.

I then inspected these code snapshots:

- `sase` at `e75840b0c9f665a7b22b6bbd2a107f17e63df89d`
- `sase-core` at `2fb5c5722e557edfb782d2caa4cbce3326ea90fe`
- the research sidecar at `00cf4bdc50e6a61a8bde97fc5459b7eccaf31a6e`

The relevant present-day facts are:

- Tale and epic plans already require a non-empty `goal` string in the Rust-backed
  plan validator (`sase-core/crates/sase_core/src/plan/validate.rs`, exposed through
  `src/sase/sdd/plan_validate.py`). They do not yet have a durable Goal identity.
- `submitted_xprompt.md` is explicitly documented in code as the launch-boundary
  prompt before alias or xprompt expansion (`run_agent_runner_setup_prompt.py`). This
  is the correct immediate prompt provenance source. `raw_xprompt.md` has different
  semantics and should not be relabeled “original prompt.”
- Ordinary nested launches deliberately remove inherited `SASE_PLAN`
  (`agent/launch_spawn.py`); plan/session paths selectively restore it. Therefore an
  agent-side “if `SASE_PLAN` is absent, create a Goal” check would misclassify valid
  descendants and would miss other structured inheritance paths.
- The low-level launch wire has no Goal field. Most of the launch domain is already
  mirrored across Python and `sase-core`, so Goal binding belongs at that boundary,
  not in a provider-specific prompt shim.
- The finalizer framework already provides a host-issued run identity, turn nonce,
  authenticated plan digest, context digest, ordered instances, required instances,
  repository obligations, and structured outcome evidence. Today the default config
  selects only `commit`, with no required finalizer. The context builder treats
  external finalizers as payload-requiring, while built-ins have special trigger and
  template behavior.
- Plan, question, monitor, gate, and pipe-style handoffs intentionally bypass the
  normal finalizer declaration. Goal continuity has to be handled by those host-owned
  handoff transactions rather than assuming every agent can make a final declaration.
- Successful user agents currently generate a `JumpToAgent` completion notification
  tagged `done` in `run_agent_runner_finalize.py`. This is exactly the attention signal
  that Goals should replace for successful runs. Failures and decisions remain
  separately valuable.
- The TUI currently has `Agents | Artifacts | Services`. Artifacts already has several
  fixed panes plus provider-defined document panes. Artifact-link following already
  tries to reveal a loaded agent in the live Agents tab first and falls back to the
  archived Agent artifact pane. Goals can reuse this mature navigation path.
- The artifact-kind and relation registries are closed in `sase-core`. A first-class
  `goal:` reference and projected Goal relations require deliberate wire/schema work.
- The agents sidecar already owns global agent identities and the canonical prompt
  archive, but prompt publication today is centered on agent-backed commits and
  approved planner runs. Ad-hoc answer/review agents need a new publication path.

These facts make the feature feasible, but they rule out the simplest version of the
proposed `/sase_new_goal` approach.

## Critique of the requirements and explicit adjustments

### What is right

The core motivation is strong. One outcome may span a planner, multiple implementation
agents, retries, monitors, and a lander. Conversely, one agent may finish cleanly
without producing anything that requires human attention. Making process completion the
attention unit creates noisy unread indicators and makes users reconstruct intent from
agents and chats. A Goal restores the missing stable unit.

The request also correctly insists on project-wide, cross-machine discovery and on
fast active reads. If Goals are only fields in `agent_meta.json`, they will be invisible
to other machines and impossible to browse after local cleanup. If Goals are found by
scanning all historical agents or beads, latency will grow with history.

### Adjustment 1: enforcement belongs to the host, not a skill

Do not require every non-planner to invoke `/sase_new_goal` at conversation start.
Skills can be skipped, fail, be unavailable in a runtime, or race. Parallel agents can
all decide to create the same Goal. The check also cannot correctly infer lineage from
`SASE_PLAN` because that variable is deliberately scrubbed at launch boundaries.

Provide a generated `/sase_goal` skill for inspection, refinement, rebinding, splitting,
and manual creation, but make it optional. The invariant is enforced by the launch
transaction. `SASE_GOAL_ID` can be exposed to the child as a convenient carrier, but
the authenticated launch record and agent metadata are authoritative. OpenTelemetry's
context specification is a useful analogy: cross-cutting values are propagated across
logically associated execution units, while baggage is only a carrier and has explicit
security hazards if sensitive data is propagated indiscriminately
([Context](https://opentelemetry.io/docs/specs/otel/context/),
[Baggage](https://opentelemetry.io/docs/concepts/signals/baggage/)).

### Adjustment 2: planners are not exempt

A planner has an outcome context and should be bound to it. Before a plan exists, the
planner uses the provisional/request Goal. When a plan is proposed or approved, the
host attaches a stable `goal_id` to the plan and uses the plan's required `goal` text as
the canonical outcome description for that Goal.

This does **not** mean the planner claims the implementation outcome complete merely
because a plan exists. A planner usually keeps the Goal open and contributes the plan
artifact. If the user's request was explicitly “produce a plan and stop,” the Goal's
acceptance policy can be plan-delivery and the validated plan can support a completion
claim. The distinction belongs in Goal criteria/policy, not in a blanket planner
exemption.

### Adjustment 3: “close” becomes “claim complete”

An LLM can provide a claim and evidence; it cannot authoritatively verify that the
world now matches the user's intention. Even cryptographic artifact attestations prove
provenance and integrity, not that an artifact is correct or secure—a limitation GitHub
calls out explicitly in its artifact-attestation documentation
([GitHub artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)).

Therefore the agent-facing choice should be:

- `keep_open`: record progress, why the Goal remains open, and a next step; or
- `claim_complete`: state the achieved outcome, map durable evidence to criteria, give
  the human a short verification recipe, and disclose limitations.

`claim_complete` moves the Goal to `ready_to_verify`; it does not erase it from the hot
set. Human verification moves it to terminal `verified` (or `waived`). This is similar
to the useful part of Kubernetes finalization: a requested terminal transition remains
visible until its required controller work is satisfied, instead of disappearing at
the moment it is requested
([Kubernetes finalizers](https://kubernetes.io/docs/concepts/overview/working-with-objects/finalizers/)).

### Adjustment 4: performance is over unsettled Goals, not merely “active” Goals

The foreground set is:

- `draft`
- `active`
- `ready_to_verify`
- `conflicted`
- locally `publication_pending`

Terminal `verified`, `waived`, `canceled`, and `superseded` Goals are excluded. The
complexity target should be stated as **O(number of unsettled Goals returned)**, with
selected-Goal detail proportional only to that Goal's bounded links. A ready-to-verify
claim must remain hot because it is precisely the work the user needs to see.

Also separate query complexity from synchronization. A Git-backed system cannot make an
offline machine globally current, and a first clone necessarily transfers some amount
of history. The product should promise local-fast reads plus an honest sync watermark,
not imaginary instantaneous global consistency.

### Adjustment 5: “all agents” means all LLM turns, not every mechanical process

Every provider-backed agent turn should have one primary Goal. `%proc` commands,
monitor supervisors, and other mechanical shells do not need independent user-facing
Goals. A gate/monitor successor that invokes an LLM inherits the Goal. Hidden helpers
normally inherit a parent Goal with contributor authority; genuinely independent
internal work can use an internal Goal hidden from the default list.

This avoids polluting the product with Goals such as “wait for process 1234.”

## Product model

### Goal identity and immutable intent

Use an opaque project-scoped artifact identity such as `goal:<ulid>`. The ID is stable;
the title can change.

A Goal needs two deliberately separate concepts:

1. **Intent** — immutable provenance: the exact originating submitted prompt(s), their
   digests, creator, project, and transformation lineage.
2. **Objective** — a concise, revisioned human/agent description of the desired
   outcome plus acceptance criteria.

This separation prevents an agent from “completing” work by rewriting the Goal to match
what it happened to do. The original intent remains visible in the review panel.
Criteria carry provenance (`user`, `plan`, `agent`, or `policy`). An agent may add or
clarify criteria, but may not delete or weaken user-, plan-, or policy-authored criteria.
Semantic weakening cannot be perfectly machine-detected, so every objective revision
is visible in the event history and in the completion review.

A bounded hot Goal snapshot should contain approximately:

```yaml
goal_id: 01K...
project: gh_sase-org__sase
revision: 7
state: active
title: Add outcome-oriented Goals to SASE
objective: Users can track and verify project outcomes across agents and machines.
criteria:
  - id: c1
    text: Every new LLM agent has one primary Goal before provider invocation.
    source: user
created_by: bbugyi200.athena.agent-name
created_at: 2026-09-27T...
updated_at: 2026-09-27T...
origin_prompt_ref: prompt:sha256:...
attention_rank: 1
contributors_count: 5
artifacts_count: 3
active_claim_id: null
sync_state: published
```

Do not put unbounded contributor, artifact, event, or prompt bodies in this hot record.
Counts and at most a few preview identities are enough for the list; the detail loader
reads the selected Goal's indexes.

### Lifecycle

```text
                 agent claim + validated durable evidence
 draft ──> active ───────────────────────────────────────> ready_to_verify
              ^                                                   │
              │                     reject + feedback             │ verify/waive
              └───────────────────────────────────────────────────┘
                                                                  │
                                                                  v
                                                        verified / waived

 active ── explicit human cancellation ──> canceled
 active ── merge/replacement ─────────────> superseded
 any unsettled state + incompatible concurrent mutations ──> conflicted
```

Do not overload agent execution status into Goal status. Agent failed, agent stopped,
and agent waiting remain execution facts. A failure leaves the Goal active and may add
an operational error indicator.

### One primary Goal, many contributors

Each LLM agent has exactly one primary Goal binding. A Goal can have many agents and
artifacts. Secondary Goal references may appear as context, but only the primary Goal
receives the agent's finalizer decision.

The binding also carries an authority role:

- `owner`: may submit an outcome-level completion claim.
- `contributor`: may attach contribution evidence and keep open, but cannot close the
  umbrella Goal unless authority is explicitly transferred.
- `reviewer`: may add review evidence but cannot claim implementation complete.

This matters for swarms. Four researchers should not generate four “Goal complete”
notifications before a lead synthesizes their work. Their reports are contribution
evidence; the lead or designated coordinator owns the outcome claim. W3C PROV's
separation of entities, activities, agents, and application-specific roles is a useful
model for preserving who produced evidence and what role they played
([PROV primer](https://www.w3.org/TR/prov-primer/)).

## Launch-time binding without user burden

### Resolution order

Resolve a Goal before process spawn in this order:

1. Explicit Goal reference from the launch surface (`@goal:<id>`, a Goal-row launch,
   or a future `%goal:<id>` directive).
2. Associated plan's persisted `goal_id`.
3. Parent/session/retry/pipe/gate/monitor/handoff inheritance.
4. Fan-out, `%alt`, swarm, and `%repeat` root Goal.
5. Exactly one active Goal linked to an assigned bead/epic.
6. Exact content identity for an already-recorded launch request, used only for
   idempotent retries.
7. Otherwise create a provisional Goal whose immutable intent is the exact submitted
   unit prompt.

Never silently bind on fuzzy semantic similarity. A wrong merge is worse than a
duplicate because it corrupts provenance and may allow the wrong agent to close an
unrelated outcome. Semantic matches can be shown as non-blocking suggestions in launch
preview or `/sase_goal`, with an explicit merge/rebind action.

### Transaction boundary

Goal resolution should happen after project selection, directives, admission, and
planned identity are known, but before the provider process is spawned:

```text
parse launch
  -> select project/workspace and planned agent identity
  -> resolve/create Goal and persist a durable local event/outbox request
  -> write authenticated goal binding into launch wire + agent metadata
  -> spawn provider with SASE_GOAL_ID as convenience context
```

If the Goal event cannot be durably recorded or queued, fail the launch. If the remote
is unavailable after durable local recording, launch in visibly `publication_pending`
mode and retry; do not pretend every other machine can already see it. A failed spawn
adds a terminal `launch_abandoned` event and automatically removes a brand-new empty
draft from the hot set.

The `AgentLaunchRequestWire`/typed unit schema should carry structured `goal_binding`
data, not smuggle it through arbitrary `extra_env`. The Rust core validates the binding
shape, project identity, role, source, and revision. Python performs I/O and process
orchestration.

### Letting agents set their own Goals safely

The provisional Goal removes work from the user while preserving agent authorship:

- The launch prompt context names the bound Goal, its state, objective, criteria, and
  whether the objective is provisional.
- `/sase_goal` lets the agent list active Goals, rebind before producing evidence,
  refine the objective, or split newly discovered work.
- The required Goal finalizer forces the agent to confirm/refine the provisional
  objective before either final action.
- Immutable intent and criterion provenance remain visible, so confirmation cannot
  rewrite history.

The user can still set an explicit Goal when desired, but never has to add boilerplate
to an ordinary prompt.

## Plan integration

Add an optional host-managed `goal_id` to the strict plan schema. The existing required
`goal` string remains the readable outcome; the ID supplies durable identity.

- A planner starts on the incoming provisional/explicit Goal.
- On proposal, the host validates the plan, attaches the same `goal_id`, and proposes a
  revision using the plan's `goal` text. This is one transaction with plan publication.
- A coder launched from the plan binds through `goal_id`, not by testing `SASE_PLAN` or
  matching text.
- Legacy plans without `goal_id` get a deterministic Goal association when first
  launched. Persist that association in Goal storage; do not rewrite an immutable
  historical plan merely to backfill metadata.
- A plan associated with a different explicit Goal causes a visible rebind/merge
  decision. Do not silently discard the agent's prior Goal if it already has evidence.

The plan Goal remains open across planner completion, approval gates, coder successors,
phase agents, landers, and recovery agents. Host-owned handoffs transfer the binding
atomically. A plan rejection keeps or cancels the Goal according to the human choice;
it is not automatically a successful outcome.

## Prompt provenance

“Original prompt” needs a precise definition. Store two immutable snapshots where they
differ:

- **Root submitted prompt**: the user/workflow launch request before segmentation.
- **Agent unit prompt**: the exact launch-boundary prompt used for this agent before
  alias/xprompt expansion—the semantics of today's `submitted_xprompt.md`.

For a direct launch they are usually identical. In a swarm, fan-out, or successor they
are not. Each agent-to-Goal association records its unit prompt; the Goal keeps its
earliest/root intent prompt and the transformation relationship. Effective expanded
instructions can remain diagnostic artifacts, but must not be presented as the user's
original text.

Make prompt objects content-addressed and immutable. Store refs and digests in Goal
events; never rely on numbered-workspace paths. Goal list rows and notifications must
not include full prompt bodies.

This change materially broadens prompt publication: the agents sidecar currently
publishes canonical prompts mainly for commit-backed and approved-planner paths, while
Goals cover answer-only and failed work too. Treat that as a privacy migration. The
sidecar must be private/consented, documentation must state that all Goal-bound launch
prompts may be published, and disabled sidecars must show `local only` rather than
quietly claiming cross-machine availability. OpenTelemetry's warning that propagated
baggage can leak to unintended downstream resources is directly relevant here; a Goal
ID is safe context, but the prompt body is not context baggage.

## Completion evidence and the required Goal finalizer

### Finalizer contract

Add a built-in provider and require it in default configuration:

```yaml
finalizers:
  defaults: [commit, goal]
  required: [goal]
  instances:
    commit:
      use: builtin@commit
    goal:
      use: builtin@goal
      after: [commit]
      max_attempts: 2
```

The host-issued Goal obligation should include:

- Goal ID, state, revision, objective, and criteria
- binding role and closure eligibility
- live required contributors/blockers
- immutable prompt provenance
- prevalidated evidence candidates from this turn
- project evidence policy
- symbolic result tokens for preceding finalizers

The agent submits one of these shapes:

```json
{
  "action": "keep_open",
  "basis_revision": 7,
  "progress": "The storage model is implemented; TUI work remains.",
  "next_step": "Add the Goals tab and cross-tab reveal tests.",
  "contribution_evidence": ["artifact:current-response"]
}
```

```json
{
  "action": "claim_complete",
  "basis_revision": 7,
  "claim": "Active Goals load independently of settled history.",
  "criteria": [
    {
      "criterion_id": "c1",
      "evidence": ["receipt:tool-run-123", "stitch:current:repo-ab12"],
      "explanation": "The benchmark and landed implementation cover the hot path."
    }
  ],
  "verification": {
    "summary": "Run the active-list benchmark with 0 and 100,000 settled Goals.",
    "expected": "p95 changes by no more than the agreed tolerance."
  },
  "limitations": []
}
```

The current finalizer declaration is prepared before `builtin@commit` produces a
stitch. Symbolic host tokens such as `stitch:current:<repo-obligation-id>` are therefore
necessary. The Goal provider resolves them after commit succeeds. The same pattern
applies to the current response, which may not be captured as a durable transcript
artifact until the provider turn has ended.

If commit is deferred/failed, a code-change completion claim cannot use the missing
stitch token. The Goal finalizer either keeps the Goal open or fails into the existing
recovery path. It must not issue a ready-to-verify notification with evidence that does
not exist.

### Evidence requirements

Require evidence to be **durable, attributable, resolvable, and criterion-specific**.
Free-form “tests passed” prose is explanation, not evidence.

| Goal/output type | Minimum primary evidence | Additional host checks |
| --- | --- | --- |
| Answer or review | Host-captured final response/transcript snapshot | Bound to the claiming agent and exact turn digest |
| Research/document | Explicit registered file/artifact ref | Content digest resolves; relevant section or finding named |
| Plan delivery | Strictly validated archived `plan:` ref | Plan is published; approval state is shown separately |
| Code change | Host-produced stitch/Patch ref | Commit finalizer succeeded; changed repositories are covered |
| Verified code policy | Tool/monitor receipt plus code artifact | Receipt covers the correct revision and is unexpired |
| Operational change | Tool-run receipt and immutable observed-state artifact | Target and observation time are explicit |

Every claim also needs a short verification instruction and an explicit limitations
list (which may be empty). Do not require a test command for inherently non-code Goals.
Conversely, do not let an agent waive a user/policy-required check on its own closing
turn.

The host can verify existence, digest, provenance, policy coverage, and relationship to
the claiming run. It cannot verify semantic truth in general. That is why the UI needs
the final human action.

### Atomic claim visibility

The canonical `completion_claimed` event must embed the accepted evidence refs and
digests. Goal state must not transition to `ready_to_verify` unless that event is
durable. Artifact-link graph rows are a projection from the event, not the sole source
of truth.

This ordering matters:

```text
validate finalizer payload
  -> resolve host tokens and evidence digests
  -> publish claim event + updated hot snapshot
  -> commit/push or durably queue publication
  -> project artifact links
  -> emit one idempotent JumpToGoal notification
```

If graph projection lags, the Goal detail still has working canonical evidence refs and
shows the link rail as rebuilding. If publication cannot be durably queued, the Goal
stays active and the finalizer reports failure.

### Handoffs and abnormal exits

- Plan, question, gate, and pipe handoffs transfer the binding and record `kept_open`
  host-side. They do not manufacture an explicit model choice after the model has
  already handed off.
- Prepared monitor completion includes the intended Goal action. Green resolves and
  executes the claim; red keeps the Goal open and launches recovery.
- Crash, kill, timeout, or provider failure keeps the Goal open and records an
  abnormal-exit contribution event.
- A retry or recovery inherits the same Goal.
- A contributor without closure authority receives an actionable finalizer diagnostic
  if it tries to claim the umbrella Goal complete.

## Storage, synchronization, and O(n) reads

### Reuse the agents sidecar repository, but create an independent Goals lane

Initially use the existing private agents sidecar rather than requiring every project
to configure a second repository. Goal provenance already needs the agent identities
and prompt archive stored there. Co-location permits one privacy policy and fewer sync
transactions.

Do **not** squeeze Goals into owner manifests or make Goal publication conditional on an
agent having a commit. Add an independent project-scoped namespace, publisher, and
outbox, for example:

```text
goals/
  schema.json
  events/v1/<shard>/<event-id>.json       # immutable canonical events
  live/<shard>/<goal-id>.json             # bounded unsettled snapshots only
  pages/<shard>/<goal-id>.md               # generated browseable artifact page
  prompts/sha256/<prefix>/<digest>         # immutable submitted prompt objects
```

On settlement, the same repository commit adds the terminal event and removes the
`live/` snapshot. History remains in immutable events and generated/VCS history, while
ordinary active reads never enumerate it.

Revisit a separate Goals sidecar only if measurements show that prompt/Goal publication
load, privacy policy, or access control diverges materially from agent history. A
separate sidecar has a clean conceptual boundary but immediately adds clone, consent,
sync, repair, and operational failure surfaces.

### Local materialized view

Each machine maintains a rebuildable `goals-live.sqlite` (or equivalently compact
single-file projection) containing only unsettled rows. The CLI and TUI read it without
network activity. Synchronization updates it off-thread from `goals/live/`; a fresh
machine can rebuild it by scanning only live snapshots.

SQLite partial indexes demonstrate the general mechanism for keeping an index limited
to qualifying rows, thereby reducing index size and improving reads/writes
([SQLite partial indexes](https://sqlite.org/partialindex.html)). Here an even stronger
shape is possible: keep terminal rows out of the hot database entirely and use a
separate on-demand history path.

List complexity is:

- O(n) to return/render `n` unsettled Goals;
- O(1) lookup by Goal ID;
- O(k) selected detail for that Goal's bounded `k` links/events page;
- no scan of settled Goals on startup, refresh, or keypress.

Store display rank (`ready_to_verify` first, then activity order) in an index so the
reader does not sort all rows on every keypress. The TUI paints the cached snapshot,
does no disk I/O in render handlers, and performs refresh/sync via pump-free background
work in accordance with the existing TUI performance rules.

### Concurrency and conflict handling

Every mutating event includes `goal_id`, `event_id`, actor, machine, idempotency key,
and `basis_revision`. Apply revision checks with the same intent as HTTP `If-Match`,
whose purpose is preventing lost updates from concurrent state changes
([RFC 9110, If-Match](https://www.rfc-editor.org/rfc/rfc9110.html#name-if-match)).

The publisher:

1. acquires the bounded machine-sidecar lock;
2. pulls/rebases;
3. installs immutable events;
4. reduces the union against the claimed basis revision;
5. regenerates affected live snapshots/pages deterministically;
6. commits and pushes with bounded non-fast-forward retry;
7. updates the local hot projection.

Commutative attachments can coexist. Conflicting objective edits or incompatible
terminal decisions do not use last-write-wins; the Goal enters `conflicted`, stays hot,
and names both events for resolution. Concurrent completion claims can coexist as claim
objects, but human verification chooses an explicit claim ID.

### Measurable performance contract

Replace “lightning fast” with acceptance thresholds on reference hardware:

- `sase goal list --active --json` p95 below 50 ms at 1,000 unsettled Goals.
- TUI highlight-to-paint p95 below the existing 16 ms target.
- Cached Goals first paint below 100 ms and never blocked on network sync.
- Increasing settled history from 0 to 100,000 changes hot-list p95 by at most 10%.
- Cold hot-projection rebuild reads only `goals/live`, verified by file-open tracing.
- Sync lag and first-clone duration are measured and displayed separately rather than
  counted as query latency.

The exact numerical thresholds can be tuned after a baseline, but tests must explicitly
vary terminal history while holding the live set constant. That proves the user's real
requirement.

## Artifact identity and links

Add `goal:` as a first-class artifact kind in `sase-core`, with resolver context for
the selected project's Goal store. Add only relations with clear direction:

- `agent:<name> pursues goal:<id>` / inverse `pursued-by`
- `<artifact-ref> supports goal:<id>` / inverse `supported-by`
- `plan:<path> defines goal:<id>` / inverse `defined-by`

These rows are projected from durable Goal binding, claim, and plan-association events;
users should not hand-edit them. The Goal event remains canonical, and the artifact
aggregate is the navigation/read model.

The Goals tab can reuse the existing relation rail and trail. For agent targets, keep
the current behavior: reveal the loaded/running agent on the Agents tab; if it is not in
the live inventory, fall back to the archived Agent pane under Artifacts. This directly
satisfies the requirement to jump from a Goal to a running agent without creating a
parallel navigation system.

## TUI: make Goals a first-class place

I recommend a top-level tab:

```text
Agents | Goals ② | Artifacts | Services
```

Keep Agents as the initial default during rollout to preserve current muscle memory,
but put Goals beside it and remember the user's last tab. A top-level surface is
justified because Goals are not merely files to browse: they are the project outcome
queue and the new attention center. Burying them among Agent, Stitch, Patch, Bead,
provider-document, and File panes would make the most important new answer—“what still
matters?”—several navigation steps away.

The underlying Goal is still an artifact and participates in the shared relation rail.
“Top-level tab” is a presentation decision, not a second data model.

### Suggested layout

```text
 GOALS  sase                         synced 18s ago   2 READY · 5 ACTIVE
 ┌──────────────────────────────────┬─────────────────────────────────────────┐
 │ READY TO VERIFY                  │ Add outcome-oriented Goals to SASE      │
 │ ▶ Add outcome-oriented Goals  4m │ READY TO VERIFY · claim 01K...          │
 │   Repair fleet sync          22m │                                         │
 │                                  │ Outcome                                 │
 │ IN PROGRESS                      │ Users track and verify outcomes across  │
 │   Reduce CI feedback time     1h │ agents and machines.                    │
 │   Improve artifact links      3h │                                         │
 │   Answer deployment question  5h │ Acceptance                              │
 │                                  │ ✓ Every agent has one primary Goal       │
 │                                  │ ✓ Settled history is off the hot path    │
 │                                  │                                         │
 │                                  │ Evidence                                │
 │                                  │ [stitch] feat: add Goal domain          │
 │                                  │ [receipt] just check · pass             │
 │                                  │ [agent] sase-x.land                     │
 │                                  │                                         │
 │                                  │ Verify                                  │
 │                                  │ Run the history-independence benchmark. │
 └──────────────────────────────────┴─────────────────────────────────────────┘
 v Verify   r Reject/reopen   Enter Open   $ Links   p Original prompt
```

The left pane has two stable lanes:

1. **Ready to verify** — always first; this is the attention inbox.
2. **In progress** — draft/active/conflicted, with conflicts pinned above ordinary
   active rows.

Each compact row shows textual state, title, age, contributor count, and evidence count.
The detail pane shows objective, source-tagged criteria, latest claim/progress, evidence,
verification instructions, limitations, contributing agents, plans/beads, and a
collapsed original-prompt preview. Prompt bodies open explicitly; they never flood the
list.

Key actions:

- `Enter`: open the highlighted chip/ref; agent chips reveal live Agents rows.
- `$`: use the standard relation rail; `Ctrl+O`/`Ctrl+Shift+O` preserve trail history.
- `v`: verify the selected claim.
- `w`: verify with waiver/reason.
- `r`: reject and reopen with feedback; optionally offer a successor launch.
- `p`: open original prompt provenance.
- `/`: filter titles, status, agents, plan/bead, or artifact refs.
- project scope defaults to the current project, with an explicit All enabled projects
  view.

Goal mutations from the TUI are durable procs, not fire-and-forget event-loop work.
List refreshes use cached snapshots and change tokens. Selection is revalidated after
every await. States use icons **and text**, not color alone, consistent with WCAG's rule
that color must not be the only way to convey status
([WCAG use of color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color)).

### Agents-tab integration

Every agent detail header gets a compact Goal chip with state and role:

```text
Goal  ◐ Add outcome-oriented Goals to SASE · contributor
```

Activating it jumps to the Goal. Add `by goal` as an Agents grouping/filter mode only
after the binding is stable; do not rebuild the whole Agents surface merely to ship the
first Goal view.

## Notifications and attention

Emit one idempotent `JumpToGoal` notification only after a `completion_claimed` event
is durably published. Use `(goal_id, claim_id)` as its deduplication identity. The row
contains the claim summary and verification hint, and Enter opens the Goal review
detail.

Change successful process completion behavior:

- ordinary successful agent exit: visible in Agents history, no default unread dot,
  toast, or bell;
- Goal completion claim: one Ready-to-verify notification and Goals badge increment;
- agent failure: retain error attention;
- question, plan approval, launch approval, sudo, and custom gates: retain their
  decision-specific attention;
- `keep_open`: no interruptive notification, though progress is visible on the Goal;
- duplicate/retried publication: no duplicate notification.

This is not merely aesthetic. An empirical interruption study found that people often
compensate by working faster but experience more stress, frustration, time pressure,
and effort ([Mark, Gudith, and Klocke, “The Cost of Interrupted Work”](https://ics.uci.edu/~gmark/chi08-mark.pdf)).
Goal claims are a much higher-signal interruption boundary than process exits.

Do not mark a Goal verified when its notification is read or dismissed. Reading is an
attention state; verification is a domain action. Status changes should also be exposed
programmatically without stealing focus, aligning with WCAG status-message guidance
([WCAG status messages](https://www.w3.org/WAI/WCAG21/Understanding/status-messages)).

## CLI and skill surface

Ship a complete CLI so the TUI is not the only control path:

```text
sase goal list [--active|--ready|--all] [-p PROJECT] [--json]
sase goal show <goal-ref>
sase goal create --objective ... [--criterion ...]
sase goal attach <goal-ref> --agent|--plan|--bead ...
sase goal refine <goal-ref> --basis-revision N ...
sase goal claim <goal-ref> ...
sase goal verify <goal-ref> --claim <id>
sase goal reject <goal-ref> --claim <id> --feedback ...
sase goal reopen|cancel|supersede ...
sase goal sync [-p PROJECT]
```

`list` and `show` are local-fast and never pull implicitly. `sync` is explicit. Mutating
commands publish or durably queue and report sync state honestly.

The generated `/sase_goal` skill should teach inspection, explicit rebinding, and manual
Goal lifecycle operations. Update the source template under
`src/sase/xprompts/skills/`; do not hand-edit deployed provider copies. The universal
provider instructions and `/sase_final` template should explain the required Goal
decision. There is no need for a mandatory `/sase_new_goal` skill.

## Implementation boundary and sequence

Shared behavior belongs in `sase-core`: Goal wire records, state transition reducer,
revision/conflict rules, evidence-policy validation, artifact kind/relation definitions,
launch binding validation, notification action data, and hot-projection schemas. Python
owns Git/outbox I/O, hidden-sidecar transactions, CLI glue, finalizer orchestration, and
Textual presentation. Add bindings through `sase_core_rs` and ratchet
`sase-core-revision.txt` before Python callers land.

### Phase 1: domain and storage

- Define Goal IDs, intent/objective/criteria, roles, events, claims, states, revisions,
  and size bounds in `sase-core`.
- Add `goal:` artifact refs and projected relation registry entries.
- Build the independent agents-sidecar Goals publisher/outbox and deterministic reducer.
- Build the terminal-history-independent local hot projection and read-only CLI.
- Add privacy policy/migration diagnostics.

### Phase 2: launch invariant and provenance

- Extend low-level and typed launch wires with `goal_binding`.
- Resolve/create before spawn across direct CLI/TUI launch, plan approval, bead work,
  child launches, swarms, `%alt`, `%repeat`, sessions, retries, dispatch, gates, pipes,
  questions, monitors, and hidden helpers.
- Capture root and unit prompt objects and persist the agent-to-Goal association.
- Add `goal_id` plan association and legacy-plan adoption.
- For agents already running during upgrade, lazily create a provisional Goal when
  final context is first published. Do not fabricate Goals for all terminal history.

### Phase 3: finalizer and evidence

- Add required `builtin@goal` ordered after commit.
- Extend final context with Goal obligations and evidence candidates.
- Add symbolic post-commit/current-response evidence tokens.
- Implement keep-open and claim-complete validation, authority, policy, and concurrency.
- Handle handoffs and prepared monitor completion explicitly.

### Phase 4: attention cutover

- Add idempotent `JumpToGoal` notification and review actions.
- Stop default successful `JumpToAgent` completion attention.
- Preserve error and decision notifications.
- Provide a temporary compatibility flag and migration of unread success rows.

### Phase 5: TUI

- Add the top-level Goals tab, cached provider, two-lane list/detail view, project
  scoping, evidence chips, original prompt, and verification actions.
- Add agent Goal chips and cross-tab reveal/fallback.
- Reuse relation rail/trail and durable proc infrastructure.
- Benchmark startup, idle ticks, j/k paint, active-list refresh, and selected detail.

## Critical acceptance tests

1. Every newly launched LLM agent has exactly one authenticated primary Goal before
   provider invocation; mechanical procs do not create Goals.
2. Direct, plan, bead, swarm, alt, repeat, session, child, retry, remote-dispatch,
   gate, pipe, question, and monitor paths preserve the intended binding and role.
3. The stored unit prompt digest exactly matches the pre-expansion submitted launch
   boundary; swarm root provenance remains separately reachable.
4. An ordinary prompt with no explicit Goal creates one without user interaction.
5. Deterministic lineage reuses a Goal; fuzzy similarity never silently joins Goals.
6. Plan proposal associates a stable Goal ID and retains the plan's required goal text.
7. Every normal return submits exactly one keep-open or claim-complete decision; crash
   and handoff behavior is host-defined and keeps the Goal safe.
8. A completion claim cannot publish with missing, mutable, cross-project, stale, or
   policy-insufficient evidence.
9. A code claim made before commit resolves only after the actual host stitch exists.
10. Two machines mutating one revision cannot lose an event or choose a winner by wall
    clock; incompatible changes surface as a hot conflict.
11. A published claim emits at most one notification across retries and machines.
12. Reading/dismissing the notification does not verify the Goal.
13. Goal-to-agent navigation reveals a running agent on Agents and falls back to the
    archived Agent artifact when necessary.
14. Adding 100,000 settled Goals does not materially change active-list latency or TUI
    file opens.
15. Sidecar-disabled/privacy-unacknowledged projects clearly show local-only Goals and
    never publish prompt text unexpectedly.

## Alternatives considered

### Goals as task beads

Rejected. Beads schedule work and carry task/phase lifecycle semantics. A Goal is an
outcome and verification boundary that may span beads, plans, agents, and answers. One
bead per answered question would inflate the tracker and make active reads depend on a
history-oriented store. Link Goals to beads instead.

### One Goal per agent

Rejected. It would reproduce current completion noise under a different name and lose
the ability for a planner, workers, retries, and a lander to contribute to one outcome.

### Agent metadata as canonical storage

Rejected. Workspace-local metadata is valuable evidence but cannot provide project-wide
cross-machine lifecycle, concurrency, or history-independent active reads.

### Artifact links alone

Rejected. Links provide navigation, not a revisioned state machine, authority policy,
completion claims, verification decisions, or atomic evidence requirements.

### A separate Goals sidecar now

Deferred. It offers the cleanest isolation, but it adds one more repository, consent
decision, hidden clone, sync loop, repair path, and distributed transaction. Reuse the
agents sidecar's privacy and prompt locality first while giving Goals an independent
namespace and publisher. Split only with measured evidence.

### A central Goal service

Deferred. It could provide stronger online consistency and truly history-independent
bootstrap, but it creates an availability, authentication, deployment, and offline
dependency unlike the current Git-sidecar architecture. Design the Goal wire/events so
the service can become another backend later.

### Goals only as an Artifacts pane

Rejected for the primary UX. It is technically economical, but it hides the new
verification inbox among many artifact categories. Goals should remain first-class
artifacts underneath while receiving a top-level operational view.

## Risks and safeguards

- **Goal spam:** deterministic inheritance, contribution roles, automatic abandonment
  of failed empty drafts, explicit duplicate suggestions, and merge/supersede tools.
- **Goalpost shifting:** immutable intent, source-tagged criteria, revision history,
  protected human/plan/policy criteria, and review-time objective diff.
- **False confidence:** call it a claim, validate provenance/policy rather than truth,
  require a verification recipe, and keep human settlement explicit.
- **Notification volume:** only outcome claims interrupt; successful process exits do
  not. Contributor agents normally keep the shared Goal open.
- **Stuck Goals:** stale/orphaned indicators, blocked-agent links, cancel/supersede
  controls, and periodic health diagnostics; never auto-verify based on age.
- **Privacy:** setup-time consent, private sidecar guidance, no prompt bodies in rows or
  notifications, and an explicit local-only mode.
- **Distributed conflicts:** immutable events, idempotency keys, revision preconditions,
  deterministic reduction, and visible conflicts instead of last-write-wins.
- **Performance regressions:** separate hot/cold storage, bounded snapshots, cached
  local projection, no network on reads, and settled-history scaling benchmarks.

## Recommended solution

Implement a first-class `goal:` domain in `sase-core` and make one primary Goal binding
a launch-time invariant for every LLM-backed SASE agent. Reuse Goals only from explicit
or deterministic lineage; otherwise have the host create a provisional Goal from the
exact submitted prompt so users never need to author Goal boilerplate. Preserve that
prompt as immutable intent, let the agent refine a separate objective, and attach a
stable `goal_id` when a plan's required `goal` becomes available.

Store immutable Goal events, prompt objects, and bounded unsettled snapshots in an
independent `goals/` lane of the existing private agents sidecar, with a durable outbox
and a local hot projection that reads only unsettled Goals. Add a required
`builtin@goal` finalizer after commit. It must choose Keep open or Claim complete; a
claim needs durable criterion-mapped evidence, verification instructions, and disclosed
limitations. Publish the claim and canonical evidence atomically, then project artifact
links and emit one `JumpToGoal` notification. Human Verify/Waive makes the Goal terminal;
Reject reopens it.

Present this as a top-level `Goals` tab beside Agents: Ready to verify first, In
progress second, with direct chips to live/archived agents, plans, beads, stitches,
receipts, reports, and the original prompt. Retire default successful agent-completion
attention while preserving failures and decision gates. This design makes Goals
intuitive enough to disappear into ordinary prompting, reliable enough to survive
multi-agent and multi-machine work, fast enough that settled history is off the hot
path, and prominent enough to become the user's actual verification inbox.
