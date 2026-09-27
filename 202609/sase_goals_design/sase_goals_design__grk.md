# Goals as a verification inbox: a UX-first design

**Recommendation:** Build Goals. Make a goal the durable *outcome* an agent pursues, bind it at launch so the user never has to type one, let agents refine or relink it, and treat an agent's `close` as an evidence-backed *claim* that stays hot until a human settles it through a real interaction gate. Put the project inventory in a first-class Artifacts **Goals** pane, make that pane the default Artifacts subtab, and give it a top-bar chip as loud as today's inbox indicator. Jump from a goal to every linked artifact and to the live Agents-tab row through projected artifact links and existing apostrophe jump hints.

This report reviews [goal_outcomes_and_verification.md](goal_outcomes_and_verification/goal_outcomes_and_verification.md) as requested, then independently inspects current launch, plan, finalizer, artifact-link, notification, agents-sidecar, beads, and TUI code. It is deliberately harsher on user experience than that earlier synthesis, because the open questions in this request are "how do I find active goals?" and "how do I jump from a goal to its agents and artifacts?" without adding prompt-crafting burden.

## 1. Is this a good idea?

Yes. The motivation is correct, and the feature is worth building if inheritance is the default.

An agent completion is a process event. Bryan currently uses those events — `JumpToAgent` notifications tagged `done` in `src/sase/axe/run_agent_runner_finalize.py`, plus unread dots projected onto Agents-tab rows in `src/sase/ace/tui/actions/agents/_notification_unread_projection.py` — as a proxy for "something I should look at." That proxy is noisy: a five-researcher swarm plus a lead produces six completions; an epic produces a planner, phases, retries, and a lander. Most of those stops do not need a human. The ones that do are *outcomes*: the synthesis is ready, the lander claims the change works, the question has an answer.

A goal is that outcome. One goal can span many agent runs. Each user-visible LLM agent has exactly one primary goal. Closing a goal is a claim that the outcome is ready to check. The human's Verify / Waive / Reject is the actual settlement.

The idea is only as good as two rules:

1. **Inheritance is the default.** Children, retries, pipes, swarm members, and epic phases join the parent's goal unless they have a distinct user-facing outcome. If every agent creates a fresh goal, the inbox is the same size as today's completion stream.
2. **Users never write a goal to launch work.** Launching an agent *is* creating or joining a goal. Agents may refine the statement. Optional `@goal:<id>` in a prompt is a power-user override.

Without those two rules the feature adds ceremony and keeps the noise.

## 2. Critique of the requested plan

The destination is right. Several of the proposed mechanisms fight SASE's existing invariants.

### 2.1 Skill-at-start is the wrong enforcement point

The sketch — every non-planner agent checks `SASE_PLAN` at the start of every conversation and invokes `/sase_new_goal` when it is unset — will not hold the "every agent has a goal" invariant.

- `src/sase/agent/launch_spawn.py` already pops inherited `SASE_PLAN` on purpose (`_remove_inherited_sase_plan_env`). Approval and attach paths set it selectively. An environment variable is a convenience, not a source of truth.
- Skills are skippable. Agents forget them, runtimes omit them, and a crash before the skill runs leaves an unbound agent.
- Four parallel researchers would create four copies of one outcome. `/sase_new_task` already exists to *prevent* that class of duplicate, and even that skill is advisory.
- The extra turn is paid on every conversation, including retries and pipes, for an invariant the launcher already has the data to establish: the submitted prompt, the plan, the bead, the parent, the eventual agent id.

A `/sase_goal` skill is still useful. It is the tool for inspect, refine, relink, and split. It is not the lock.

### 2.2 Planner exemption is unnecessary once binding is host-owned

A planner has a purpose. Give it a goal at launch. If the user asked only for a plan, the goal is plan-delivery and `sase plan propose` plus PlanApproval is the verification path (one alert, the existing gate). If the user asked to implement something and planning is the first hop, the planner inherits the implementation goal and chooses `keep_open`. There is no circularity once the host binds before the model runs.

### 2.3 "All agents" needs a visibility split

The invariant should cover every LLM agent shell, including hidden helpers. Mechanical monitor, gate, and `%proc` shells inherit goal context and are not independent claimants. Hidden and system agents bind to a parent or an internal goal and cannot close a user-visible goal without explicit delegation. The user's Goals pane lists `visibility: user` goals only. That keeps the invariant without filling the inbox with harness machinery.

### 2.4 Evidence cannot be one universal triad

A reply can evidence an answer. A plan needs its archived `plan:` ref. A code change needs the host-finalized stitch plus any verification receipts the goal's acceptance criteria require. A blanket "tests must have passed" rule makes questions and documentation goals impossible. A blanket "the agent wrote a paragraph" rule makes code goals unverifiable. Evidence is policy-sensitive, host-checked, and always includes a short "how to verify" instruction for the human.

### 2.5 UX was underspecified, and that is the actual product

The earlier outcomes research treated the TUI as a presentation of a data model. The request in front of us is the reverse: Bryan needs a daily loop that replaces Agents-tab unread dots. If the Goals inventory is the sixth Artifacts subtab after stitches, patches, beads, agents, and files, it will be as undiscoverable as beads already are for this job. The design has to answer, in keystrokes:

- How do I see every active goal for *this* project?
- How do I jump from that row to a running agent on the Agents tab, even if the row is grouped or collapsed?
- How do I jump to the report, plan, stitch, or prompt that evidences it?
- How do I verify without also being dinged for every helper that stopped?

Those questions are the feature.

### 2.6 Agents already can set goals, if launch binds and the skill refines

The worry that "users would always need to set the goal explicitly" is the failure mode of an operator-first binding order. If step one of launch is "wait for the human to pick a goal," the prompt-crafting burden is real. If step one is "the host creates or joins a goal from the plan, the parent, or the submitted prompt," the user types the same prompt they type today. The agent then sees `Your primary goal is: …` in its instructions and may refine or relink. That is agents setting goals, with zero extra prompt syntax required.

## 3. Explicit adjustments to the requirements

These are the changes I would make to the original request. Each is a requirement change, called out so it can be accepted or rejected on purpose.

| # | Original | Adjustment | Why |
| --- | --- | --- | --- |
| A1 | Non-planner agents check `SASE_PLAN` and run `/sase_new_goal` | The **launcher** binds exactly one primary goal before the model is invoked. `/sase_goal` is optional mid-run. | Skills cannot police an invariant; the launcher already knows prompt, plan, parent, and agent id. |
| A2 | Planner agents are exempt | Planners bind too. Plan-delivery goals close through PlanApproval; implementation goals stay open. | Removes circularity without a special case. |
| A3 | "Ideally" link to an existing active goal | **Inherit by default.** Create a new goal only when there is no parent/plan/bead/session goal and no explicit `@goal:` / `%goal()`. | Stops goal sprawl from turning this into the same notification firehose. |
| A4 | Users might need to state the goal | Users never have to. Host derives a title and outcome from `plan.goal`, parent goal, or a one-line summary of the submitted unit prompt. Agents may refine. | Directly removes prompt-crafting burden. |
| A5 | Agent `close` closes the goal | Agent `close` is a **claim**. Status becomes `needs_review` and stays in the hot set until a human Verify / Waive / Reject gate settles it. | Matches the stated motivation: alert me when an agent *claims* an outcome is complete. |
| A6 | A new Goals panel "somewhere" | A built-in Artifacts **Goals** pane, made the **default Artifacts subtab**, plus a top-bar `goals:` chip, plus Agents-tab goal chips and a `by_goal` grouping mode. | Reuses the Artifacts shell (query, relations, jumps, project scope) while remaining as discoverable as today's unread dots. A fourth top-level tab is a later promotion if dogfood says the chip is too quiet. |
| A7 | Store wherever is convenient | A dedicated builtin **`goals` sidecar**, with `live/` snapshots for unsettled goals. Prompt *bodies* stay in the private agents sidecar; goals hold locators and digests. | The agents sidecar "is never exposed to launched agents or copied into numbered workspaces" (`docs/agents_sidecar.md`). The request requires every agent and every machine to read active goals quickly. Those two facts cannot share one private store. |
| A8 | O(n) on active goals, done goals free | Hot set is **unsettled** goals: `active` plus `needs_review`. Settled states (`verified`, `waived`, `canceled`, `superseded`) leave `live/`. | A claimed-complete goal is exactly the verification inbox; it must stay hot. Settled history must not. |
| A9 | Notify on newly done goals | One `GoalVerify` **interaction gate** per published claim, transported as a notification, with `JumpToGoal`. Successful agent completion stops creating default `done` unread dots. Failures, questions, and approvals keep their own routes. | Dismissing a notification is already defined as browsing state, not a decision (`docs/notifications.md`). Verification has to be a gate, like PlanApproval. |
| A10 | All agents have a goal | All **LLM agent shells** have a primary goal. Mechanical shells inherit context and cannot claim. Hidden agents are `visibility: internal` and omitted from the default pane. | Preserves the invariant without UI clutter. |

## 4. What already exists (and should be reused)

Tale and epic plans already require a `goal` string: "Outcome the plan is designed to achieve" (`sase-core` `plan/validate.rs`, Python adapter `src/sase/sdd/plan_validate.py`). That string is the seed for a plan-backed Goal artifact, persisted as a stable `goal_id` on the plan once Goals exist. Legacy plans get a deterministic id from `(plan ref, goal text)` so every new agent launched from them binds without a backfill rewrite of history.

The runner already stores the launch-boundary prompt as `submitted_xprompt.md` before xprompt expansion. That is the "original prompt" to associate with a newly created goal. `raw_xprompt.md` is alias-resolved; expanded system instructions are not the origin. Canonical prompt publication today happens mainly for agent-backed commits and approved plans (`docs/agents_sidecar.md`). Answer-only goals need a host publication path for a content-addressed prompt snapshot, or the origin locator will be missing on another machine.

Finalizers already have host-issued, digest-bound context, a turn nonce, required instances, ordered execution, and a `bead_action` precedent (`crates/sase_core/src/finalizer/wire.rs`, `src/sase/default_config.yml`: `defaults: [commit]`, `required: []`). A normal goal-bound run adds required `builtin@goal` after `builtin@commit`, even on a clean tree. Prepared monitor completion already carries a predeclared host-completion intent (`docs/monitors.md`); it should also carry a predeclared goal action.

The artifact relation registry is closed (`docs/artifact_links.md`, `crates/sase_core/src/artifact_link/relation.rs`). Goal links need a deliberate schema extension. Projected relations (`produced-by`, `launched`, `awaits`) are the right pattern for agent↔goal and claim↔evidence: they are derived from durable bindings, cannot be hand-deleted, and already feed the TUI relation rail and apostrophe jump hints.

The TUI has exactly three top-level tabs, Agents first (`src/sase/ace/tui/tab_order.py`). Artifacts has a contract-driven shell: query bar, grouping, marks, copy, relations, project scope, empty states (`docs/artifacts_pane_contract.md`, `docs/artifacts_pane_visual_grammar.md`). Fixed subtabs today are `agents, stitches, patches, beads, files` with default `stitches` (`src/sase/ace/tui/_artifact_tab_model.py`). Agents-tab grouping is Project / Date / Status / Machine (`agent_grouping_modal.py`). Cross-entity jumps already exist: notification `JumpToAgent`, artifact relation rail, apostrophe hints, `jump_to_agent_patch`.

Beads are the cautionary tale for storage. They are the right *shape* (event log + projection + sidecar + CLI + TUI pane) and the wrong *object* (scheduling, size, phase ancestry, close-on-commit). `sase bead list` is already careful to default to active statuses; closed history is opt-in (`docs/beads.md`). Goals should be even stricter: the foreground list must be physically unable to see settled files.

Interaction gates already are the product for "a human must decide." Plan, epic, question, launch, sudo, and task-triage approvals store the reviewed content in `~/.sase/interaction_requests/<kind>/<id>/` and use the notification row as a transport projection (`docs/notifications.md`). Remote attention already polls a pending inventory across enrolled machines. Goal verification belongs on that path.

Linear's Initiatives are a useful analog for *layering*: issues stay issues, initiatives sit above them as the thing leadership actually looks at, with a health column and an Active view ([Linear Initiatives](https://linear.app/docs/initiatives), [Introducing Initiatives](https://linear.app/changelog/2024-06-25-introducing-initiatives)). SASE already has beads (issues) and agents (execution). Goals are the initiative-sized layer, scoped to a single outcome rather than a quarter.

## 5. Recommended model

### 5.1 Identity and fields

A goal is a first-class artifact `goal:<id>` with an opaque stable id. The title may change; the id may not.

| Field | Notes |
| --- | --- |
| `id` | Opaque, stable. |
| `title` | Short, mutable. |
| `outcome` | One-paragraph statement of what "done" means. Seeded from `plan.goal` or the submitted prompt. |
| `acceptance` | Optional structured criteria. Code goals often have them; answer goals often do not. |
| `status` | See lifecycle. |
| `visibility` | `user` or `internal`. |
| `project` | Project key. |
| `origin_prompt` | Locator + SHA-256 of the **submitted unit prompt** of the creating agent. Never the expanded system prompt. |
| `origin_root` | Optional upstream/root prompt or group digest for transformed fan-outs (swarms). |
| `plan_ref` | Optional `plan:…`. |
| `bead_ref` | Optional `bead:…`. |
| `primary_agents` | Bindings: agent global name, role (`creator`, `contributor`, `coordinator`), attached-at. |
| `revision` | Monotonic. Finalizer submissions are revision-checked. |
| `claim` | Present in `needs_review`: claim text, evidence refs+digests, verify steps, limitations, claiming agent, claimed-at. |
| `sync` | Watermark: last successful publish, pending-local, conflict. |

Do not inline potentially private prompt bodies in list rows or in the goals sidecar. Show a one-line preview and an explicit Open prompt action that resolves the locator.

### 5.2 Lifecycle

```text
active ── close claim + host-validated evidence ──▶ needs_review
  ▲                                                   │    │
  └── reject + feedback (goal stays active) ──────────┘    └── verify/waive ──▶ verified/waived
active ── cancel / supersede ──────────────────────────────────────────────────▶ canceled/superseded
```

- `active` and `needs_review` are **unsettled**. They live in `live/` and are the O(n) set.
- `verified`, `waived`, `canceled`, `superseded` are **settled**. They leave `live/`.
- A crash or kill cannot choose. The host records failed/aborted work and keeps the goal `active`.
- `sase pipe`, questions, gates, and plan proposal are intentional handoffs: they transfer or keep the binding in the host-owned handoff transaction.
- Prepared monitor completion carries a predeclared choice. Green may claim `close` if still eligible; red keeps `active` and launches recovery.
- A sibling or phase may not claim outcome-level close while required contributors are still live. A designated coordinator (swarm lead, epic lander) makes that claim.

### 5.3 One primary goal per agent

Each LLM agent has exactly one primary goal, persisted in agent metadata and exposed as `SASE_GOAL_ID` (convenience, like `SASE_BEAD_ID`). Other goals may be linked as context. Only the primary goal receives that run's finalizer decision.

## 6. Binding: host at launch, agents refine

### 6.1 Launch resolution order

The launcher resolves in this order and always ends with a bound goal before the model runs:

1. Explicit `@goal:<id>` / `%goal(<id>)` in the submitted prompt, if that goal is unsettled.
2. Associated plan's persisted `goal_id` (or a deterministic create from the plan ref plus its required `goal` text).
3. Parent / session / pipe / recovery / swarm-leader inheritance.
4. Unique structured bead or epic identity when it already has a goal.
5. Create an ad-hoc goal from the submitted unit prompt (title + outcome summary).

Semantic matches against other active goals are **suggestions injected into the agent instructions**, never silent joins. Fuzzy text similarity must not merge two user intents.

Reject binding to a settled goal. The operator may reopen, or the launcher may create a follow-up goal linked with `supersedes`.

### 6.2 What the agent sees

Agent instructions include:

- The primary goal id, title, and outcome statement.
- A compact index of other *user-visible unsettled* goals in this project, truncated if the set is large (id, title, status). The full set is always one `sase goal list` away.
- Instructions that they may refine the statement, adopt a better existing goal, or split a distinct outcome, using `/sase_goal`.
- The requirement that the finalizer must choose `keep_open` or `close`.

They do **not** start the conversation with a mandatory skill invocation.

### 6.3 The `/sase_goal` skill (optional, mid-run)

Commands, all host-validated:

```text
sase goal list                          # unsettled, current project, O(n_live)
sase goal show <id>
sase goal adopt <id>                    # relink this agent; old goal stays active
sase goal update <id> --title --outcome # refine; bumps revision
sase goal split <id> -t "…"             # create a child/sibling; this agent may move
sase goal suggest                       # host-ranked semantic suggestions, no write
```

Create without going through launch is allowed for a distinct discovered outcome, and should reuse the `/sase_new_task` discipline: search first, prefer adopt. A newly created mid-run goal becomes this agent's primary only after `adopt`.

### 6.4 Worked examples

**Ad-hoc question, no plan.** User types "What is the env var for the assigned bead?" Host creates `goal:…` with outcome "Answer which env var names the assigned bead." Agent answers, finalizer `close` with the response artifact as evidence and verify step "Read the answer; confirm it names `SASE_BEAD_ID`." One GoalVerify gate. Same number of alerts as today, better payload.

**This research swarm.** User prompt creates one goal, "Recommend how to implement SASE Goals." Five researchers and a lead inherit it. Researchers `keep_open` with progress "wrote `__grk.md`." Lead `close` with the synthesis plus researcher reports as evidence. One claim, one gate.

**Epic implementation.** User asks to implement a feature. Host creates the implementation goal from the prompt (or from the plan's `goal` once a planner proposes). Planner `keep_open`. Phase agents inherit. Lander `close` with stitch token + `just check` receipt. One claim at the end.

**User names a goal.** Prompt contains `@goal:7f3a`. Launcher binds that unsettled goal. No new goal is created.

## 7. Closure evidence and the goal finalizer

### 7.1 Placement

Add non-removable `builtin@goal`, ordered **after** `builtin@commit`, required even on a clean tree. The host issues a goal obligation containing id, revision, outcome class, acceptance criteria, closure eligibility (no live required contributors, goal still `active`, revision current), and evidence *candidates* (artifacts this run produced, "current commit result" token, monitor receipts).

Every normal provider return chooses:

```json
{ "action": "keep_open", "progress": "…", "next": "…" }
```

or

```json
{
  "action": "close",
  "claim": "one sentence of what is now true",
  "evidence": [
    { "kind": "artifact", "ref": "research:202609/goals_ux_first_design__grk.md", "why": "…" },
    { "kind": "host_commit", "token": "current_commit_result" },
    { "kind": "receipt", "tool_run": "…" }
  ],
  "verify": ["Open the report and confirm the recommended store is a goals sidecar."],
  "limitations": "Did not implement the TUI."
}
```

`keep_open` does not notify. `close` is validated again at execution time; stale revision, failed commit, failed monitor, or newly live contributors reject the declaration and recover.

Because `builtin@commit` has not created the stitch at submit time, the agent selects pre-existing refs plus the host token `current_commit_result`. The goal finalizer resolves that token to the actual `stitch:<sha>` after commit succeeds. A reply-only run similarly lets the host publish the response snapshot before the claim is visible remotely.

### 7.2 Minimum evidence by outcome class

| Outcome class | Minimum durable evidence | Host checks | Typical verify hint |
| --- | --- | --- | --- |
| Answer / review | Captured response or transcript artifact, digest-bound to this run | Artifact exists and is associated | "Read the answer." |
| Research / document | Registered `research:` / `file:` / other document ref | Ref resolves to the produced version | "Read the named section; confirm the recommendation." |
| Plan delivery | Validated archived `plan:` ref | Proposal/approval handoff state; suppress a duplicate PlanApproval chime | Existing PlanApproval is the review. |
| Code / operational change | Host-finalized stitch or immutable output, plus any receipts the acceptance criteria require | Commit finalizer succeeded; refs and receipts exist | "Check the stitch; confirm `just check` receipt; smoke the path named in the claim." |

Required for **every** close, regardless of class:

1. A one-line claim of what is now true.
2. At least one resolvable durable evidence item.
3. One to three human verification steps.
4. Disclosed limitations.

The agent may explain why evidence supports the claim. It cannot manufacture a successful command, a missing artifact, or a verification policy. A self-written "tests passed" sentence is not a receipt. The agent cannot waive its own acceptance criteria on the closing turn; a human waiver is an explicit gate choice.

`close` publishes a `completion_claimed` event containing accepted refs and their digests. The artifact-link projection is derived from that event, so a claim cannot appear without its evidence links. Notification / gate emission follows durable publication and is idempotent on the claim id.

### 7.3 What I would require, and why this bar

The evidence bar is "a human can check this in under a minute with the links in front of them." That is the product. Stronger (every close needs a command witness) excludes legitimate answers. Weaker (a paragraph of assertion) makes the verification inbox a second chat transcript. Linking the claim to host-resolved artifacts, and making the human's next click land on those artifacts, is the whole UX.

## 8. Durable storage and genuinely fast reads

### 8.1 Put goals in their own sidecar

Prefer a new builtin sidecar role `goals`, sibling to `plans` and `beads`.

The agents sidecar is the wrong canonical home. It is a hidden machine-owned clone, private by default, "never exposed to launched agents or copied into numbered workspaces" (`docs/agents_sidecar.md`). The request is that every agent, and every human on every machine, can list active goals quickly. A store agents cannot see cannot satisfy that. Extending agents publication to leak goal records into workspaces would also punch a hole in a privacy boundary that exists for prompt bodies and hood snapshots.

Beads are the wrong object. They encode scheduling, size, phase ancestry, and close-on-commit. Making every answered question a bead would inflate a tracker already dominated by closed records. Link a goal to a bead when work is scheduled; keep the outcome record separate.

A separate goals sidecar has a real operational cost (another clone, lock, sync, doctor). That cost is the same class of cost SASE already accepted when beads moved out of the plans repo so hot writes would not serialize (`docs/beads.md` storage section). Goals will be written at every launch and every claim; they deserve their own lock.

Layout:

```text
live/<id>.json          # unsettled snapshot only; this is the O(n) set
events/<id>.jsonl       # append-only; not scanned for list
archive/<id>.json       # settled snapshot; not scanned for list
pages/<id>.md           # generated artifact page, lazy
schema.json
README.md
```

Immutable, schema-versioned events (`created`, `agent_attached`, `plan_attached`, `statement_updated`, `completion_claimed`, `verification_accepted`, `rejected`, `reopened`, `canceled`, `superseded`) carry actor, basis revision, and an idempotency key.

A publication is one git transaction: new events + updated `live/` snapshot (or `live/` delete + `archive/` add) + any prompt-locator objects. Local lock, `basis_revision` check, pull/recompute on non-fast-forward, push with bounded retry. Concurrent claims on the same goal reopen `active` with a conflict diagnostic rather than last-write-wins. Report success only once the shared write is confirmed. A failed publication must not emit a "ready to verify" gate.

Prompt *bytes* stay in the agents sidecar's content-addressed object store when they are published at all. The goal record stores `prompts/<YYYYMM>/<name>.md` or `files/objects/sha256/…` locators plus the digest. Answer-only runs need a host path that publishes that snapshot without requiring a code commit.

### 8.2 The O(n) promise, stated honestly

Foreground `sase goal list` (and the TUI's first paint of the Goals pane) reads **only** `live/`: one bounded JSON record per unsettled goal. It does not open `events/`, does not open `archive/`, does not filter history, and does not `git pull`.

That is O(n) in the number of unsettled goals. It is the same idea as a [SQLite partial index](https://www.sqlite.org/partialindex.html) over `status IN ('active','needs_review')`, and the same idea as keeping hot rows in their own table ([partial-index performance writeups](https://mvpfactory.io/blog/sqlite-partial-indexes-and-expression-indexes-in-the-query) show an unsynced/hot subset index an order of magnitude smaller than a full one). A directory of live snapshots is the simplest physical form of that split and needs no query planner.

Honesty about what O(n) does *not* cover:

- First clone of the sidecar still transfers git history.
- Repair and `sase goal doctor` may replay events off the foreground path.
- Cross-machine freshness is "local-fast, explicitly dated." Show a sync watermark. Strict shared launch/close requires a successful publish. Projects that have not initialized a consented goals remote run in local-only mode or refuse the shared guarantee.

A machine-local compact projection (gitignored SQLite or a single `~/.sase/cache/goals/<project>.json`) may sit in front of `live/` for the TUI. It must be rebuildable from `live/` alone, including on a fresh machine, without replaying settled history. TUI reads the cache on the event loop and refreshes off-thread (`sase/memory/tui_perf.md`: never block the pump, show cached data instantly, coalesce).

Avoid sorting the entire hot set on every keypress if strict linear complexity matters; store display order in the projection, or keep two already-ordered partitions (`needs_review`, `active`).

### 8.3 Agent access

`sase goal list` is the API. It materializes the goals sidecar on demand the way `sase bead` materializes beads, then reads `live/`. Subsequent calls are directory reads. Injecting the primary goal into instructions means most agents never list at all. Relink and suggest pay the O(n) list once.

## 9. UX walkthrough (the actual product)

This is the daily loop the feature exists to create.

### 9.1 Finding every active goal for this project

**Zero extra navigation when you already live in the TUI.**

The top bar already has an `inbox:` chip (`src/sase/ace/tui/widgets/notification_indicator.py`). Add a sibling `goals:` chip for the **current project**:

```text
inbox: ⚑2  goals: ◉3 ◐12
```

- `◉N` is `needs_review` (attention). Accented.
- `◐N` is `active` (in progress). Dimmer.
- Click, or `g` from normal mode, switches to Artifacts → Goals with the current project scope already applied.

**Inside the Goals pane** (default Artifacts subtab, `DEFAULT_ARTIFACTS_SUBTAB = "goals"`):

- Shared Artifacts chrome: pane brief, query bar, identity/scope header, state/count lane, list/detail split, relation rail, footer hints (`docs/artifacts_pane_visual_grammar.md`).
- Default grouping: two lanes, **Needs review** first, then **In progress**. Settled goals are absent unless the query asks for them (`status:verified` / `status:all`), and that query reads `archive/` explicitly so the default path stays O(n_live).
- Default project scope is the current project, matching every other Artifacts pane.
- Compact row: status glyph, title, contributor count, last activity age, and when `needs_review` a one-line claim preview.
- Empty state, in the contract's `PaneEmptyState`: title `No active goals`, body `New work gets a goal at launch. Nothing in this project is waiting.`
- Query language is the shared Artifacts dialect: `status:needs_review`, title words, `agent:foo`, `plan:…`. Startup still injects `limit:<ace.page_size>`.

**CLI**, because the TUI must not be the only control path:

```text
sase goal list              # unsettled, current project
sase goal list -s review    # needs_review only
sase goal show <id>
sase goal verify <id>       # opens the same gate as the TUI
sase goal reopen <id>
```

### 9.2 Jumping from a goal to artifacts and agents

This is a first-class Artifacts pane with `PaneCapability.RELATIONS` on, so the existing relation rail, trail, and apostrophe jump hints work.

On the selected goal, the list-column relation rail and the detail **Links** block show projected chips:

| Chip | Relation | Jump |
| --- | --- | --- |
| Agents pursuing it | `agent → pursues → goal` | Switch to the **Agents tab**, select that agent, expand any Project/Date/Status/Machine group that currently hides the row |
| Plan | `plan → defines → goal` | Artifacts → Plans, that plan |
| Bead | `goal → tracks → bead` (or `implements` inverted) | Artifacts → Beads |
| Origin prompt | `goal → originates-from → prompt` | Open the prompt artifact / preview |
| Evidence (when claimed) | `artifact → evidences → goal` | Open that report, stitch, file, or transcript |

Apostrophe jump hints cover every chip. `Enter` on the goal focuses detail. A dedicated `o` opens the *primary* evidence (the claim's first evidence ref, or the origin prompt if still `active`). Copy `y` copies `goal:<id>`.

The Agents-tab jump has to work when the target row is grouped, collapsed, on another machine group, or filtered out of the current Agents query. The action should: switch tab, if the current Agents query hides the row then stash and clear the blocking filter with a toast ("cleared query to show agent"), expand the ancestor groups, select the row, and focus it. This is the reliability requirement hiding inside "use artifact links."

### 9.3 Agents tab: the other direction

Keep Agents as the live-work home. Add:

- A truncated **goal title chip** on each user-visible agent row (after the name, before runtime). Click / a bound key jumps to that goal in the Goals pane.
- A `by_goal` grouping mode in the existing grouping modal (`p/d/s/m` today). Groups are goal titles, with a `needs_review` group pinned first. Agents whose goal is internal stay in an "Internal" bucket that is collapsed by default.
- Selected-agent header already has decks and cards; a small Goal card repeats outcome, status, and a Verify action when `needs_review`.

Unread **completion** dots on agent rows go away for successful runs. The replacement is the `goals:` chip plus the GoalVerify gate in the inbox. Failure dots and question/approval dots stay.

### 9.4 Verifying

One published `completion_claimed` event produces one `GoalVerify` interaction gate, transported as a notification with action `JumpToGoal`. The gate bundle contains the claim, the verify steps, the evidence refs, the original-prompt preview, and three decisions: **Verify**, **Waive**, **Reject and reopen**. Reject records feedback and offers a successor launch; it does not silently force one.

Reading or dismissing the notification is browsing state, as with every other gate. The pending bundle remains reachable through `sase gate list` / the Goals pane Verify action / mobile and Telegram, using the same remote-attention inventory already polled for questions and approvals.

Plan-delivery goals reuse PlanApproval and do not emit a second GoalVerify chime. Operational failures stay on the error route.

For answer goals, the gate *is* the review surface: the answer is in the detail pane, the verify step is "read this," and `y` verifies. That is equal in effort to today's "open the completed agent," with a precise reason the ping existed.

### 9.5 Visual grammar (beautiful, in the existing language)

Reuse the Artifacts shell. Do not invent a second layout system.

- **Accent:** a single new color, distinct from stitches gold `#FFD700`, beads purple `#D787FF`, agents blue `#0062FF`, patches teal `#00D7AF`, files orange `#FFAF5F`, plans `#AF87FF`. Candidate: `#FF87AF` (rose) or `#87FFAF` (mint). Use it in the pane-brief gutter, the `goals:` chip, and status glyphs. Readable status text always accompanies color (`tui` memory: never color alone).
- **Glyphs:** `◐` active, `◉` needs_review, `✓` verified (history only), `–` waived, `×` canceled. Match the density of bead status glyphs (`docs/beads.md`) without copying their colors.
- **Needs-review rows** carry the same class of unread mark Agents rows use today, so the lane is scannable.
- **Detail** is a short stack, not a wall: outcome, claim (if any), "How to verify" checklist, Links chips, origin-prompt preview with Open, limitations.
- **Motion:** none beyond the existing unread mark. A pulse on every live goal would make the pane unreadable.
- **Onboarding:** the pane brief (summary/full/`D` cycle) explains in one line that goals are outcomes, created at launch, and that `◉` is the thing to check.

## 10. Artifact kind, relations, and schema work

Add `goal` as a live artifact kind (`docs/artifact_references.md` live kinds table). `@goal:<id>` completes in the prompt bar, expands in prompts, and is a legal `sase artifact read` target (generated page).

Closed registry additions, all **projected** from durable goal events (same written_by as `produced-by` / `launched` / `awaits`):

| Relation | Inverse | Source → target | Derived from |
| --- | --- | --- | --- |
| `pursues` | `pursued-by` | `agent` → `goal` | launch/adopt binding |
| `evidences` | `evidenced-by` | artifact → `goal` | `completion_claimed` |
| `originates-from` | `originated` | `goal` → prompt artifact | create |
| `defines` | `defined-by` | `plan` → `goal` | plan `goal_id` |

Keep `implements` for plan/agent/stitch → bead. Do not overload it to mean "agent works on goal." Direction matters and the registry's examples are how agents learn the graph.

This is a `sase-core` wire change: goal model, transitions, evidence validation, kind rules, relation slugs. Python orchestrates I/O, sidecar publication, TUI, and the `/sase_goal` skill. A new binding ratchets `sase-core-revision.txt`.

## 11. Attention cutover

Do this as an explicit two-step so the inbox never has both fires.

1. Ship GoalVerify gates and the Goals pane **alongside** existing `done` completion notifications, behind a feature flag.
2. Flip the flag: successful user-agent completion no longer emits `JumpToAgent` with `tags=["done"]` and no longer projects unread onto agent rows. Failures, held workspaces, questions, approvals, sudo, and task-triage are unchanged.

Idempotency: one claim id, one gate, across retries and machines. Remote attention uses the same pending inventory path as other gates (`docs/notifications.md` Remote Attention). A stale or partial host inventory must not settle a missing GoalVerify row.

## 12. Alternatives considered

**Fourth top-level tab (`Agents | Goals | Artifacts | Services`).** Maximum prominence, and it matches how Bryan uses Agents unread today. Cost: tab-order persistence, `-t` CLI, golden screenshots at 120×40, mobile chrome, keymap cycling, another default-startup debate. The Artifacts shell already provides the inventory, query, relations, and jumps Goals need. I would start with Goals-as-default-Artifacts-pane plus a top-bar chip, and promote to a top-level tab only if dogfood shows people cannot find it. The chip is the bet that prominence can live in the header the way `inbox:` already does.

**Goals pane inside Agents.** Local jumps, familiar tab. A project-wide verification inbox then depends on which agent is selected, and the Agents tab is already dense with decks, cards, clans, and machines.

**Canonical state in the agents sidecar.** Attractive because prompts and agent identities already live there. Rejected because that sidecar is private and not in the workspace; agents cannot list it. Goal *locators* for prompts can point into it; goal *records* cannot hide in it.

**Goals as a bead type.** Reuses lifecycle, sync, TUI, CLI. It also reuses close-on-commit, size, phase ancestry, and a list path that has to work hard to ignore closed history. Answer goals are not tasks. Link instead.

**Mandatory `/sase_new_goal` at conversation start.** Stated in the request as one idea. Rejected in §2.1.

**Auto-verify when the user opens the answer.** Tempting for Q&A. Too easy to mark verified by accident while hunting for something else. Keep the one-key Verify on the gate; for answer goals that key is the whole review.

**Silent fuzzy join of new prompts onto similar active goals.** Will merge unrelated intents. Suggestions only.

## 13. Implementation sequence

This is `xlarge` work in the SASE size sense (`sase/memory/sase_sizes.md`): several phases, distinct agents, explicit dependencies. An epic, not a tale.

1. **Core + sidecar.** Goal wire model, transitions, prompt provenance, artifact identity, relation slugs, publication protocol in `sase-core`. Python binding, revision ratchet. Independent publisher and `live/` projection. Tests: two-machine same-goal races, interrupted publication, cold-machine bootstrap, stale projection, privacy-disabled / local-only policy, `list` complexity against growing `archive/`.
2. **Launch binding.** Direct runs, plan approval, bead work, swarms, children, retries, pipes, monitors, gates, hidden helpers. Backfill active plans deterministically. Leave historical completed agents unbound. Test: every *new* LLM agent starts with exactly one primary goal and a durable creator-prompt locator.
3. **Finalizer.** Required `builtin@goal` after commit; prepared-monitor and handoff handling; evidence by outcome class; host token for current commit; eligibility. Tests: close-before-commit, failed monitor, deferred commit, duplicate submit, concurrent close/reopen, sibling still live.
4. **Attention.** GoalVerify gate, `JumpToGoal`, explicit verify/waive/reject; then retire success-completion unread. Dedup by claim id across machines.
5. **TUI.** Goals pane as default Artifacts subtab, top-bar chip, Agents goal chips, `by_goal` grouping, relation jumps that can select a grouped Agents row, screenshot goldens, frame-budget and p95 `goal list` measurements on each supported machine. Empty, error, and `needs_review` states; desktop and the 120×40 screenshot viewport.

Acceptance the user can feel on day one: launch a question without typing a goal, see it in the Goals pane, watch the agent close with the answer as evidence, get one GoalVerify ping, press `g`, jump to the agent and back, verify. Launch a two-agent swarm on one prompt, see one goal with two contributors, one claim from the lead.

## 14. Recommended solution

Build Goals as a **host-bound outcome artifact** with this shape:

- **Create/join at launch**, from plan `goal` / parent / explicit `@goal:` / submitted prompt. Users do not type a goal. Agents may refine or relink through `/sase_goal`.
- **Inherit by default** so a swarm or an epic is one outcome, and the inbox shrinks.
- **Required `builtin@goal` finalizer** after commit: `keep_open` (quiet progress) or `close` (evidence-backed claim). Evidence is a typed, host-checked bundle plus a human "how to verify" list; a stitch is attached via a host token because it does not exist at submit time.
- **Human settlement** through a `GoalVerify` interaction gate. `needs_review` stays in the hot set. Settled goals leave it.
- **Dedicated `goals` sidecar** with `live/<id>.json` as the only foreground read set, so list is O(n_unsettled) and agents can actually see it. Prompt bodies remain in the private agents sidecar behind locators.
- **UX:** Goals as the default Artifacts pane, a top-bar `goals:` chip for the current project, Agents-tab goal chips and `by_goal` grouping, projected artifact links with apostrophe jumps that can land on a grouped Agents row. Replace successful `done` unread with this inbox.

That is the design I would implement. The original request's destination — every agent has a goal, close requires evidence, a panel lists active goals, jumps are artifact links, attention moves from "an agent stopped" to "an outcome is ready" — survives. The enforcement point, the store, the meaning of "done," the planner special case, and the amount of UX specificity do not.
