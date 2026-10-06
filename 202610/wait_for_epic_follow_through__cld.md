# `%wait(…, for_epic=)`: letting a wait follow an agent into the epic it creates

_Researcher: cld · 2026-10-06 · Scope: the `sase` repo (`src/sase`, `docs/`) plus a
read-only look at the linked `sase-core` repo. All paths are repo-relative. Line numbers
are from the current `master` (`620e5310d4`). Behavior marked "by code reading" was
traced but not executed._

---

## TL;DR

- **The idea is good, and the default-on choice is right.** Today `%wait:planner`
  releases at a halfway point: the plan was approved, or at best the epic's phase agents
  were launched. That is almost never what a person means by "start after that agent's
  work". If the default follows the agent into its epic, a mistake means a waiter starts
  _late_. If it doesn't, a mistake means it starts _early_, on top of unfinished work.
  Starting late is the cheaper mistake, so it should be the default.
- **Your hunch that "the links already exist" is only partly true.** The bead's
  `created_by` field is durable. The per-run record from agent to epic is not: it is a
  best-effort back-fill into `agent_meta.json` under the key `epic_bead_id`. For every
  phase and land worker, that same key means _"the epic I work on"_.
  - A naive implementation keyed on `epic_bead_id` would deadlock every epic. The land
    agent's `%wait:<epic>.1` would follow into `<epic>`, which only the land agent
    itself can close.
  - The artifact-link graph can't be the source of truth either. Planners are usually
    not published, so their links never appear.
- **Recommended design, in four parts:**
  1. **Epic ledger.** Write an authoritative record of the epic into the creating run's
     artifact directory at the moment the epic becomes durable.
  2. **Per-occurrence keyword.** Parse `for_epic` separately for each `%wait(...)`
     directive, apply the default at launch, and store the result as an explicit list.
     Waiters that are already parked, or were written before this feature, never change
     meaning.
  3. **Promotion step in the resolver.** When an armed agent target resolves and it
     created an epic, turn that part of the wait into an ordinary **bead wait on the
     epic**. Pin it there and record where it came from. This reuses every existing
     piece of bead-wait machinery.
  4. **TUI hand-off token.** A teal `↪` that reads as "this wait moved into an epic":
     `WAITING ↪ ◐ sase-7k 2/5`.
- **Requirement adjustments** are called out in [§3](#3-requirement-adjustments-called-out)
  (A1–A9). The recommendation is in [§9](#9-recommended-solution).

---

## 1. What exists today

### 1.1 How `%wait` is parsed

- **Validation is in Python.** In `src/sase/macro/_directive_collect.py:130-152`, the
  parenthesized form accepts exactly `{agent, bead, hood, proc, time, unit}`. Anything
  else raises `DirectiveError("Unsupported keyword on %wait: …")`.
  - Duplicate keywords inside one occurrence are rejected (`reject_duplicate_named_args`
    for `wait`).
  - So repeated keywords already require separate `%wait(...)` directives. That gives a
    natural scope for a per-occurrence modifier such as `for_epic=`.
- **The colon form `%wait:a,b` never parses keywords** (`_directive_collect.py:218-227`).
- **Completion and the LSP come from Rust.** The editor-facing keyword list is
  `WAIT_KEYWORDS` in `sase-core`
  (`crates/sase_core/src/editor/directive/metadata.rs:547`; the `wait` entry is at
  `:680`). It drives both TUI completion and `sase-macro-lsp`.
  - A `DirectiveValueRole::Bool` role already exists. `%proc(workspace=)` uses it at
    `:339`, and `%if(should_run=)` uses it at `:368`.
  - The editor diagnostics do **not** check `%wait` keyword combinations today.
    `directive_diagnostics` (`crates/sase_core/src/editor/diagnostics.rs:355`) only
    flags unknown directives.
- **Two tests pin the exact keyword tuple:** `tests/test_macro_directive_contract.py:54`
  and `crates/sase_core_py/src/editor_completion/tests/surfaces.rs:690`.

### 1.2 How a waiter is released

- **The wait set is not fixed at launch.** The runner writes `waiting.json`
  (`src/sase/axe/run_agent_wait.py:163-184`).
  - Both releasers re-read that marker on every check: the AXE `wait_checks` chop (10 s,
    with an fs trigger) and the runner's own 60 s fallback.
  - The TUI `w` edit already rewrites the marker in place, under a per-artifact lock
    (`src/sase/ace/tui/actions/agents/_directive_persistence.py:341-393`).
  - **So rewriting the wait at runtime is already how this code works**, not a new idea.
- **What counts as success for a named wait.** The newest run of that name, or every
  member of the clan, session, or workflow, must end with one of
  `{completed, noop, epic_approved, plan_committed}`
  (`src/sase/core/dismissed_agent_completion.py:33-35`). Any failure keeps the waiter
  parked; nothing cascades.
- **The resolver already knows the concrete runs behind a name.** It builds a
  `WaitEntity` whose `members` carry `artifact_dir` and `outcome`
  (`src/sase/core/wait_dependency_resolution/_index_entities.py:96-147`; the candidate
  types are in `_types.py:22-44`).
  - Today, though, `dependency_resolution_status`
    (`src/sase/core/wait_dependency_resolution/_resolution.py:14-117`) only asks
    `index.is_resolved(name)` and gets back a yes/no.
- **What a planner wait means today.** The epic-launch monitor runs **inside the
  planner's own session**: `_epic_launch_lane` is at `src/sase/bead/epic_launch.py:270`,
  and the monitor sets `start_status="EPIC APPROVED"` and `stop_status="EPIC CREATED"`
  at `:228-229`.
  - By code reading, `%wait:planner` therefore releases once the epic exists and its
    phases have been launched.
  - On the fallback path, where no lane resolves and a detached proc runs instead
    (`epic_launch.py:251`, `:317`), the wait can release as soon as the outcome is
    `epic_approved`.
  - Neither path waits for the epic to **close**. `docs/axe.md` says so explicitly: _"A
    wait on an epic-approved planner waits for that planner, not for the host-owned
    epic it launched; use bead waits or a wait on the launched epic clan for that."_
- **Bead waits** require status `closed` and fail closed when a store is missing or
  unreadable (`src/sase/bead/wait_status.py`; `docs/axe.md`, the `wait_for_beads`
  paragraph).
  - Bead waits don't add up children. They don't need to: a bead with any open
    descendant **cannot be closed**, except through `--force` with a `canceled` or
    `superseded` resolution (`docs/beads.md:1575-1603`).
  - **So "the top epic is closed" already means "the whole tree is done",** nested
    child epics included.

### 1.3 How an epic gets created, and who gets credit

- **Canonical path** (`/sase_plan`):
  1. `sase plan propose` stamps `proposed_by = acting_agent_name()` into the plan
     (`src/sase/main/plan_propose_handler.py:165-168`).
  2. The approval gate starts the host-owned monitor, which runs
     `sase bead work <plan> --artifacts-dir <planner artifacts>`.
  3. That calls `create_and_launch_epic_from_plan`
     (`src/sase/bead/epic_from_plan.py:67`). It creates the epic at `:140` with
     `created_by` set to the plan's `proposed_by`, commits `bead_id: <epic>` into the
     plan at `:228`, and then launches work at `:237`.
  - Inside the monitor, the agent's environment is cleared, so the plan's `proposed_by`
    is the only identity carried through.
  - An epic created before the plan-link commit is **deleted on failure**, so the
    durable point is right after `:228`.
- **Back-fill.** `finish_epic_launch` → `_update_epic_launch_metadata`
  (`src/sase/bead/epic_launch.py:415-449`) writes `epic_bead_id`, `epic_started_at` and
  `plan_committed` into the planner's `agent_meta.json`.
  - It is best-effort. Every exception is swallowed, and it does an unlocked
    read-modify-write.
  - It runs only after the launch succeeds, and only when `--artifacts-dir` was passed.
- **The overloaded key.** Phase and land workers receive `epic_bead_id` from
  `SASE_EPIC_BEAD_ID` (`EPIC_WORK_ENV_METADATA_NAMES`,
  `src/sase/axe/run_agent_directive_metadata.py:41`, consumed at `:174`).
  - So `epic_bead_id` means **"the epic I created"** for a planner and **"the epic I
    belong to"** for a worker.
  - When a phase worker hands its phase off to a child epic, the back-fill **overwrites**
    its parent-epic ID with the child's ID (by code reading). That corrupts
    `wait_own_bead_ids` (`src/sase/ace/tui/actions/agents/_wait_helpers.py:161`), the
    TUI "own" Beads row, and the `agent-bead` link projection.
- **Artifact links.** `agent-bead` (`src/sase/artifact_links/projection/_agent_bead.py`)
  emits `agent:<n> implements bead:<id>` from **published** agent metadata. It covers
  `bead_id`, `epic_bead_id` and `phase_bead_id`, all under one relation, so "created"
  can't be told apart from "works on".
  - Full publication covers only hoods that have at least one primary-repository commit
    (`docs/agents_sidecar.md`, "Scope and reconciliation"). A planner whose phases live
    in the `<epic>.*` hood normally has no commits, so **it is never published.**
  - The relation registry is closed. No `created` relation exists.
- **In-turn creation** (`sase bead create -T 'plan(...)' -r epic`) runs in the agent's
  own process and credits the acting agent. Today it writes **nothing** to that agent's
  artifacts.

### 1.4 How waiting looks in the TUI

- **Agent row.** `WAITING` in bold amethyst `#AF87FF`, followed by status-count tokens
  such as `✓1 ▶2`. A single bead wait instead renders `◐ sase-7k`, with the ID in
  `#FF87D7`. See `src/sase/ace/tui/wait_status_presentation.py` and
  `src/sase/ace/tui/widgets/_agent_list_render_agent_status.py:194-252`.
- **Detail panel.** A tagged `Wait:` block with lanes `[agents] [tribes] [beads] [hoods]
  [time] [capacity]` (`src/sase/ace/tui/widgets/prompt_panel/_agent_wait_section.py:104-339`).
  - **There is a precedent for showing a binding:** tribe waits render
    `@review → bound-name ✓`, with the arrow in dim `#AF87FF`.
- **Epic colour.** `EPIC CREATED` is already teal `#5FD7AF`
  (`src/sase/ace/tui/widgets/prompt_panel/_workflow_render.py:52`).
- **Jinja precedent.** `{{ agents["p--plan"].plan_file }}` is synthesized for a waited-on
  planner row (`docs/macros.md`, "Template Context";
  `src/sase/agent/output_variable_context.py:253`).

---

## 2. Critique: is this a good idea?

**Yes.** Three reasons, in order of importance:

1. **It fixes a mismatch in meaning, not just a convenience gap.**
   - An epic is the only way an agent's work leaves the agent:
     - a tale's coder stays in the planner's session, so today's waits already cover it;
     - a task bead is deferred work, which nobody should wait for.
   - So "wait for agent X" should naturally include "and the epic X handed its work to".
     That makes the epic-specific name honest rather than a special case.
2. **It removes a manual sync step that costs real time.** Today you watch for the epic
   ID and launch later. With this feature you launch both prompts together.
3. **Waiting costs almost nothing.** A parked waiter defers its workspace claim (it gets
   `workspace_num=0` until it is released), so hours of follow-through hold no checkout.

**The risks are real, and they drive the adjustments in §3:**

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| Identifying "the epic X created" | `epic_bead_id` is overloaded; the planner is usually unpublished; the back-fill is best-effort | An authoritative ledger plus an independent fallback (§4.3) |
| Deadlock | A waiter that follows into an epic it is itself part of can never release; with the default on, this would hit every epic's land agent if keyed on `epic_bead_id` | A dedicated ledger, plus a structural subtree guard (§4.4) |
| Meaning changes silently | Existing parked waiters and generated `%wait`s (`%repeat` chains, AXE `wait_on`, land waits, mobile "wait for" prompts) would change behavior | Apply the default at launch and store it; old markers never follow (A3) |
| Hours of invisible parking | An epic can take hours; users must see *why* a waiter hasn't started | The `↪` hand-off token, epic progress, and a transition toast (§4.6) |
| The epic never closes | A failed land agent leaves the waiter parked for good (same as `bead=` today) | Extend the existing terminal-blocker notification (§4.4) |
| Canceled epics | A forced cancel closes the epic, which releases a `bead=` waiter today | Keep that consistency, but say so loudly (open question Q1) |

**Would I take a different approach?** The surface you proposed (a boolean keyword,
on by default) is the right one. I would change the **mechanism** in two ways:

- Don't rely on the artifact-link graph to find the epic. Write one synchronous, local,
  authoritative record when the epic is created, and *derive* links from it.
- Don't compute "following" from scratch on every check. **Promote** the wait into an
  ordinary bead wait once, pinned, with provenance recorded. Bead waits already have
  sync hints, fail-closed reads, status glyphs, `awaits` link projection, run-now, and
  TUI editing. Promotion gets all of that for free.

The alternatives I rejected are in [§5](#5-alternatives-considered).

---

## 3. Requirement adjustments (called out)

| # | Your requirement | Adjustment | Why |
| --- | --- | --- | --- |
| **A1** | Default `true` "when an agent name is provided" | The default applies to every **agent-shaped target in the same `%wait` occurrence**: positionals, `agent=`, a bare `%wait` resolved to the last agent, `@tribe` targets, and session/clan/workflow names. It does **not** apply to `hood=`, `bead=`, `proc=`, `unit=`, `time=`, or a `<base>--plan` planner-row alias. | `for_epic` changes how an *agent* wait finishes. A `--plan` alias deliberately resolves at plan submission and has no member runs to follow. |
| **A2** | Error and/or diagnostic without an agent | **Both, and with identical wording:** a hard `DirectiveError` at launch, an Error-severity editor diagnostic in Rust (the LSP and TUI prompt bar share it), and a strict `true`/`false` value check (case-insensitive, matching `%if(should_run=)`). | `%wait` already hard-fails invalid keywords, so a warning-only path would be inconsistent. |
| **A3** | (implicit) Default applies everywhere | Apply the default **at parse time** and store it as a positive list (`wait_for_epics_of`) in `agent_meta.json` and `waiting.json`. **Markers without the field never follow.** | Waiters already parked, and older artifacts, keep their meaning. There is no flag-day flip mid-wait. |
| **A4** | "the epic bead that agent created" | Follow **every** epic created by **any run** behind the resolved target: session turns (planner, gate, monitor, tale coder) and clan members. | The planner's epic is launched by a *session member*, and a tale coder can propose its own epic. Following only the root run would miss both. |
| **A5** | (unspecified) Re-runs of the agent | **Pin:** once the wait follows into epic E, later runs of the same agent name can't redirect it. | Predictable. This matches how "wait released" already never re-parks. |
| **A6** | (unspecified) Which epics | Follow only the **top-level** epics the run created. Nested child epics are covered because the top epic can't close with open descendants. Don't follow task beads. | Simpler and correct. |
| **A7** | (unspecified) Self-dependency | **Never follow** into an epic whose subtree contains the waiter's own epic or phase bead. Record a diagnostic instead. | Rules out deadlock, whatever the metadata says. |
| **A8** | (unspecified) Hoods | `for_epic` is rejected when the occurrence's only targets are hoods (v1). | This is what "without an agent name" means; hood members could be supported later. |
| **A9** | "make the links consistent" | Make the **ledger** authoritative and use it to *drive* the links (`awaits` for the waiter for free; `produced-by` for the epic, optional). The wait never depends on the link graph. | The link graph only covers published agents and is rebuilt on demand, so it can't gate a scheduler. |

---

## 4. Design

### 4.1 Syntax and meaning

```text
%wait:planner                          # follows planner into any epic it creates (default)
%wait(planner, reviewer)               # both targets follow
%wait(planner, for_epic=false)         # release when planner finishes, even if it launched an epic
%wait(planner, time=30m)               # follow, then a 30m floor after everything resolves
%wait(planner)  %wait(bead=sase-87.2)  # follow planner AND require bead sase-87.2 closed
```

- **Scope is the occurrence.** `%wait(a, b, for_epic=false)` opts both `a` and `b` out;
  `%wait:a` together with `%wait(b, for_epic=false)` mixes them. This uses the
  per-occurrence grammar that already exists.
- **The colon form takes no keywords**, so it always gets the default. Opting out needs
  the parenthesized form.
- **Conflicts are errors.** If the same target is armed in one occurrence and opted out
  in another, launch fails with
  `Conflicting for_epic= for %wait target 'planner' (true in one %wait, false in another)`.
- **The name.** `for_epic` reads as an extension of "wait for…": "wait for planner, not
  for its epic". Keep it.
  - `epic=` would collide in people's heads with `bead=<id>`.
  - A new sigil (`%wait:planner!`) would add a second way to say the same thing.

### 4.2 Validation messages (launch-time and editor, identical wording)

| Case | Message |
| --- | --- |
| No agent target in the occurrence | `%wait(for_epic=…) needs an agent target in the same %wait — e.g. %wait(planner, for_epic=false). bead=, hood=, and time= waits never create epics.` |
| Bad value | `Invalid %wait for_epic= value 'yes': use true or false.` |
| Conflict | as in §4.1 |
| Explicit `for_epic=true` | No diagnostic (being explicit is fine) |

- **Editor completion.** Add a `for_epic` `DirectiveKeywordSpec` with
  `DirectiveValueRole::Bool` and its own suggestions. Don't reuse `BOOL_TRUE_FALSE`; its
  documentation text is about workspace leases.
  - `true`: _"Also wait for any epic these agents create (default)"_
  - `false`: _"Release when these agents finish, even if they launched an epic"_
- **Argument hint:** `":agent or (agent, bead=, hood=, time=, for_epic=)"`.

### 4.3 The epic ledger: one authoritative agent→epic record

**What it is.** A new append-only file, `created_epics.json`, in the **creating run's
artifact directory**. Each entry records:

```json
{"epics": [{"bead_id": "sase-7k", "project": "sase", "plan_ref": "…/plans/202610/foo.md",
            "created_at": "2026-10-06T14:31:58Z", "via": "bead_work"}]}
```

**Writers.** Both write atomically under the per-artifact lock and log on failure. Both
are best-effort only in the sense that they never fail the launch.

1. **`create_and_launch_epic_from_plan`**, immediately after `plan_link_committed`
   succeeds (`src/sase/bead/epic_from_plan.py:228`) and before `launch_work`.
   - This is the first moment the epic can't be rolled back.
   - Pass `artifacts_dir` through from `src/sase/bead/cli_work_entry.py:79` as an
     `on_epic_durable` callback, so the function's interface stays narrow.
2. **`handle_bead_create`**, when an agent itself runs `sase bead create … -r epic`. The
   process has `SASE_ARTIFACTS_DIR`; see `src/sase/bead/cli_crud_create.py`.

**Readers, in priority order.** The wait resolver tries these for each member run of a
resolved target:

1. the ledger;
2. the `bead_id:` frontmatter of the plan the run proposed, found through that run's
   plan-path marker. This is independent of the ledger and covers ledger write failures
   and a later manual `sase bead work`;
3. legacy `epic_bead_id`, **only if** the run carries no `phase_bead_id` and no
   `epic_plan_ref`. This keeps planners from before the ledger working and never
   confuses them with workers.

**Fix the overloaded field at the same time.** `_update_epic_launch_metadata` should stop
writing `epic_bead_id` and write `created_epic_bead_ids` instead. Readers that treat
`epic_bead_id` as "the planner's epic" should move to the ledger. Readers that treat it
as "the epic I belong to" (`wait_own_bead_ids`, the `agent-bead` projection) keep their
meaning, and the child-epic overwrite bug goes away.

### 4.4 Resolver state machine

Per armed target, persisted in `waiting.json` as `wait_epic_follows[]`:

```text
            target resolves,               target resolves,
            no epic signal                 ledger/plan names epic(s)
  ARMED ───────────────────────► NONE      ARMED ─────────────────► FOLLOWING(E…)
    │        (released as today)                                       │  epic ids appended to
    │                                                                  │  wait_for_beads (pinned)
    │ target resolves, a member outcome is                             ▼
    │ epic_approved but no epic id yet                       all E closed → released
    ▼                                                        (normal bead-wait path)
  AWAITING_EPIC ──(ledger/plan bead_id appears)──► FOLLOWING(E…)
    │
    └─(grace exceeded, launch settled without an epic, e.g. skip mode)──► stays parked +
       one terminal-blocker notification ("approved epic was never launched; run
       `sase bead work <plan>` or run-now")
```

**Details:**

- **Where it lives.** Add a query, `index.resolved_entity(name)`, that returns the
  resolved members. Put the follow logic in a new
  `src/sase/core/wait_dependency_resolution/_epic_follow.py`, and have
  `dependency_resolution_status` return `epic_follow` proposals alongside
  `blocked_on`. One resolver is shared by the chop, the runner fallback, and the TUI's
  dependency badges, so all three agree by construction.
- **Promotion.** The chop, or the runner fallback, persists each proposal under the same
  lock TUI edits use:
  - append the epic IDs to `wait_for_beads` in both `waiting.json` and
    `agent_meta.json`;
  - add the target to `resolved_deps`, which pins it;
  - record `{target, run artifact_dir, epic_ids, followed_at}`.

  It then re-checks right away, so a fast epic that has already closed releases in the
  same tick.
- **Free side effects of promotion:**
  - `sidecar_auto_sync` starts hinting the beads role (it scans live `wait_for_beads`);
  - fail-closed bead reads apply;
  - the published waiter gets `agent:W awaits bead:sase-7k`;
  - TUI run-now and `w` editing just work.
- **The AWAITING_EPIC state.**
  - On the normal path the monitor is a session member, so the target can't resolve
    before EPIC CREATED, and by then the ledger exists. AWAITING_EPIC therefore matters
    mainly on the fallback proc path, in `skip` approval mode, and after ledger failures.
  - It also closes a race that exists **today**: a scan between the planner's
    `epic_approved` done marker and the monitor joining the session can release a
    planner wait early.
- **Deadlock guard (A7).** Skip any epic E where one of the waiter's own beads
  (`epic_bead_id`, `phase_bead_id`, `%id(bead=)`) equals E or starts with `E.`. Bead IDs
  are hierarchical, so this is a prefix check. Record a diagnostic.
- **Epic that never closes.** Extend `terminal_blockers`
  (`src/sase/scripts/_chop_wait_checks_terminal.py`). If the followed epic's land agent
  (clan `<epic>`) has a terminal failure, upsert one notification that names the waiter,
  the epic and the land agent.

### 4.5 Persisted fields (a summary)

| Where | Field | Written by | Purpose |
| --- | --- | --- | --- |
| `agent_meta.json`, `waiting.json` | `wait_for_epics_of: [names]` | the runner, at launch | Which targets are armed (positive list; absent means never follow) |
| `waiting.json` | `wait_epic_follows: [{target, state, run, epic_ids, since}]` | chop or runner | Runtime state and provenance for the TUI and CLI |
| `waiting.json`, `agent_meta.json` | `wait_for_beads` (+ the followed IDs) | chop or runner | Reuse the bead-wait machinery |
| the creator's artifacts | `created_epics.json`; `agent_meta.created_epic_bead_ids` | `sase bead work`, `sase bead create` | Authoritative agent→epic record |

- The Rust scanner wires must project the new marker and meta fields: `WaitingMarkerWire`
  and `AgentMetaWire` in `src/sase/core/agent_scan_wire_markers.py`, mirrored in
  `sase-core`.
- The flag-gated typed-launch planner's `WaitTargetWire`
  (`src/sase/core/agent_launch_wire_records.py:124-133`) needs `for_epic` on `agent`
  targets.

### 4.6 TUI and CLI presentation

**Agent row.** The hand-off glyph `↪` (U+21AA, single-width) is bold teal `#5FD7AF`, tying
it to the existing `EPIC CREATED` colour. Bead tokens reuse the existing glyphs and
styles.

```text
WAITING ▶1                    planner running; follow armed (no extra noise — it's the default)
WAITING ↪ epic…               planner finished with EPIC APPROVED; epic being created
WAITING ↪ ◐ sase-7k 2/5       following epic sase-7k; 2 of 5 phases closed (dim progress)
WAITING ▶1 ↪ ◐1               one agent still running, one epic already followed
```

**Detail panel, `[agents]` lane.** The hand-off is shown in place, like the tribe
binding `@review → name ✓`. A followed epic is **not** repeated in the `[beads]` lane.

```text
Wait: [agents] planner ▶ · then any epic it creates
Wait: [agents] planner ✓ ↪ epic launching… (EPIC APPROVED 14:02)
Wait: [agents] planner ✓ ↪ sase-7k ◐ 2/5 phases · following since 14:32
      [beads]  sase-87.2 ○
Wait: [agents] research ✓ · agent only               # explicit for_epic=false
```

**Making the transition obvious** (your fourth bullet):

- **Row.** The row changes from `▶1` to `↪ ◐ sase-7k`, and the glyph differs from every
  existing status glyph.
- **Toast.** The TUI already refreshes when `waiting.json` changes. On the
  `FOLLOWING` transition it shows one toast: _"`W` now waits on epic `sase-7k` (created
  by `planner`)"_.
- **Timeline.** Add an `EPIC FOLLOW` milestone at `followed_at` in the waiter's timeline,
  next to the existing `EPIC` milestone.
- **Epic side.** The epic's bead detail and clan summary can list "awaited by `W`",
  using the `awaited-by` inverse of the projected `awaits` link.

**Other surfaces:**

- **`w` wait modal.** Each agent row gets a `↪ epic` toggle, on by default. The
  `PromptWaitDirective` dataclass gains `agents_without_epic`, so kill-and-relaunch
  rewrites emit `%wait(a, b)` + `%wait(c, for_epic=false)`. If the toggle gets a new
  key, update `src/sase/default_config.yml`.
- **CLI.** `sase agent list` JSON gains `wait_for_epics_of` and `wait_epic_follows`.
  `sase agent wait` rows read "`W` waits on epic `sase-7k` (from `planner`)"
  (`src/sase/agents/_wait_live_rows.py`). The text summaries in
  `src/sase/ace/tui/models/agent_tribe_summary.py` read "waiting for planner's epic
  sase-7k".

### 4.7 At prompt time

The waiter's executable prompt is rendered **after** the wait releases, so the followed
epic is known by then. Synthesize the epic the same way `agents["p--plan"].plan_file` is
synthesized:

- `{{ agents["planner"].epic_bead_id }}` (first followed epic) and
  `{{ agents["planner"].epic_bead_ids }}`.
- `{{ wait.epics }}`: every followed epic, in order.

This lets a follow-up prompt say "review what landed in epic
`{{ agents["planner"].epic_bead_id }}`" without knowing the ID when you write it. That
was the original pain point.

### 4.8 Artifact links (optional, phase 3)

- **`awaits` is free.** The waiter gets `agent:W awaits bead:<epic>` automatically,
  because promotion writes `wait_for_beads`.
- **Creation edge, optional.** Add a projection, `bead-created-by`, that emits
  `bead:<epic> produced-by agent:<created_by>` for plan beads whose `created_by` is an
  agent's global name.
  - Source it from the **bead store** (durable and synced), not from published agent
    metadata. Then it exists even for planners that are never published.
  - Check first whether a link may point at an `agent:` ref that has no published page.
- None of this is on the wait's critical path.

### 4.9 Edge cases

| Scenario | Behavior |
| --- | --- |
| The agent finishes with no plan, or with `plan_committed` | Released as today (`NONE`) |
| A tale plan; the coder hands off inside the session | Waits for the coder (as today); follows any epic the coder creates |
| The epic plan is rejected | `plan_rejected` keeps the waiter parked until a later successful run (as today) |
| Epic approved, then the launch fails | The monitor fails, so the waiter stays parked; the TUI shows `↪ epic launch failed` |
| Epic approved in `skip` mode | `AWAITING_EPIC`; a later manual `sase bead work` is picked up through the plan's `bead_id`; one notification after the grace period |
| One run creates several epics, or the session has several | All of them are followed |
| Nested child epics | Covered, because the top epic can't close before them |
| An epic is closed as `canceled` or `superseded` | Released (same as `bead=`); the toast and notification say "closed as canceled" (see Q1) |
| The planner is re-run after the follow | Ignored (pinned, A5) |
| The waiter belongs to the followed epic's tree | Not followed; diagnostic (A7) |
| `%wait:p--plan` | Resolves when the plan is submitted; nothing to follow |
| `%wait:@tribe`, a clan, a session | Follows the epics of the bound entity's members |
| `%repeat:k` chains (`src/sase/agent/repeat_launcher.py:195`) | Default on: run k waits for run k−1's epic (intended; mention it in the docs) |
| The epic lives in another project | Already handled by full-ID routing in bead waits |
| The marker predates the feature | Never follows (A3) |
| TUI run-now | Releases immediately, as today |

---

## 5. Alternatives considered

1. **A target keyword, `%wait(epic=planner)`, opt-in only.** It composes neatly with
   `bead=` and `hood=`, but it can't express "on by default". It would also make two
   spellings for one idea once the default flips. Rejected.
2. **`%wait:@epic` (tribe, next-entity).** It already works without knowing the epic ID,
   but it binds to *whichever* epic clan launches next. With two planners in flight, it
   races. It also waits for the clan's agents, not for the bead to close. Rejected.
3. **Drop `epic_approved` from the success outcomes globally.** That gives the same
   default with no keyword, but there is no opt-out for "start once the plan is
   approved" (for example, a parallel research agent that reads the plan). Rejected.
4. **Planner-side chaining** (the planner declares what follows it). This needs the
   follow-up written into the planner's prompt before launch, which is the opposite of
   "launch earlier". Rejected.
5. **Look the epic up through the artifact-link graph.** The graph only covers published
   agents, is rebuilt on demand, and its relation for this case is ambiguous
   (`implements`). It is unfit to gate a scheduler. Rejected as the mechanism; kept as a
   by-product.
6. **Bead-store lookup by `created_by` only.** Agent names are reused across runs, the
   store needs a sync, and phases inherit `created_by`. Usable as a tie-breaker, not as
   the main source.
7. **Recompute the follow on every check (stateless).** That is simpler on paper, but a
   re-run of the target could redirect a waiter, the TUI would have to re-derive the
   epic on every refresh, and none of the bead-wait machinery would apply. Promotion
   wins.

---

## 6. Where the code changes land

**`sase-core`** (open it with `sase repo open sase-core`; afterwards move
`sase-core-revision.txt` forward):

- `crates/sase_core/src/editor/directive/metadata.rs`: add the `for_epic` entry to
  `WAIT_KEYWORDS`, a `FOR_EPIC_SUGGESTIONS` list, and the new argument hint.
- `crates/sase_core/src/editor/diagnostics.rs`: add `wait_directive_diagnostics` (no
  agent target, bad value, conflict) next to `queue_directive_diagnostics`.
- Wire records for the agent scan (`WaitingMarkerWire`, `AgentMetaWire`) and the
  typed-launch `WaitTargetWire`.
- Tests: `crates/sase_core_py/src/editor_completion/tests/surfaces.rs:690`.

**`sase`:**

- **Parsing:**
  - `src/sase/macro/_directive_collect.py:130-152`: per-occurrence `for_epic` capture.
  - `src/sase/macro/_directive_values.py`: the bool check and the no-agent check.
  - `src/sase/macro/_directive_extract.py`: apply the default and detect conflicts.
  - `src/sase/macro/_directive_types.py:211-217`: add
    `PromptDirectives.wait_for_epics_of`.
- **Runner:**
  - `src/sase/axe/run_agent_directives_flow.py`: `WaitResolution`.
  - `src/sase/axe/run_agent_directive_metadata.py:237-250`: the meta key.
  - `src/sase/axe/run_agent_wait.py:163-184`: the marker key.
  - `src/sase/axe/run_agent_wait_deps.py`: promotion in the fallback path.
- **Resolver:** `src/sase/core/wait_dependency_resolution/`: `_index_queries.py`
  (`resolved_entity`), a new `_epic_follow.py`, `_resolution.py`, and `_types.py`.
- **Chop:** `src/sase/scripts/_chop_wait_checks_run.py` (promote under lock, then
  re-check) and `_chop_wait_checks_terminal.py`.
- **Ledger:**
  - `src/sase/bead/epic_from_plan.py`: write at `:228`, before `:237`.
  - `src/sase/bead/cli_work_entry.py`: thread `artifacts_dir` through.
  - `src/sase/bead/cli_crud_create.py`: the in-turn epic case.
  - `src/sase/bead/epic_launch.py:415`: stop overwriting `epic_bead_id`.
- **TUI:**
  - `src/sase/ace/tui/wait_status_presentation.py`
  - `src/sase/ace/tui/widgets/_agent_list_render_agent_status.py`
  - `src/sase/ace/tui/widgets/prompt_panel/_agent_wait_section.py`
  - the loaders `_meta_enrichment_wire.py` and `_meta_enrichment_filesystem.py`
  - `src/sase/ace/tui/models/_agent_state_queue.py`
  - `src/sase/ace/tui/actions/agents/_wait_helpers.py`
  - the wait modal
  - `src/sase/macro/_directive_edit_wait.py`
- **CLI and Jinja:** `src/sase/agents/_wait_live_rows.py`,
  `src/sase/integrations/_agent_list_entry_builder.py`, `src/sase/agents/cli_list.py`,
  and `src/sase/agent/output_variable_context.py`.
- **Docs:**
  - `docs/macros.md`: the wait section and the completion matrix.
  - `docs/axe.md`: rewrite the "epic-approved planner" sentence.
  - `docs/ace.md`: Wait state and the row tokens.
  - `docs/agent_sessions.md`, `docs/beads.md`, and `docs/artifact_links.md` if the link
    projection is added.
  - `CHANGELOG.md`: the default change.
- **Tests:**
  - `tests/test_macro_directive_contract.py:54`
  - `tests/test_macro_directive_completion_parity.py:302-317`
  - resolver unit tests for every row of §4.9
  - an end-to-end **regression: a land agent with `%wait:<epic>.N` under the new default
    must still release**.

> **Boundary note.** Wait resolution is still Python today (`src/sase/core/…`), so the
> follow logic belongs next to it. Under the project's Rust-core rule, the contract,
> diagnostics, and wire types must go to `sase-core`. If wait resolution moves to Rust
> later, `_epic_follow.py` moves with it.

---

## 7. Rollout (three phases, no feature flag needed)

| Phase | What ships | Visible to the user? |
| --- | --- | --- |
| **1 — Ledger** | `created_epics.json` writers and readers; `epic_bead_id` un-overloaded (bug fix) | No |
| **2 — Opt-in follow** | Keyword, diagnostics, resolver, promotion, TUI, CLI, docs; **default `false`**: only an explicit `for_epic=true` follows | Yes, complete and opt-in |
| **3 — Flip the default** | Default `true` for newly launched waiters; Jinja `epic_bead_id`/`wait.epics`; optional link projection; CHANGELOG | Yes |

- **Why there's no flag.** Each phase is complete and safe on its own, and
  `for_epic=false` stays a permanent choice rather than a deprecated branch. Under the
  `sase_flags` policy, that makes it a keyword, not a flag.
- **If you would rather land phases 2 and 3 together,** use one `beta` flag on the
  default only, as epic scaffolding, and remove it in the land phase.

---

## 8. Open questions for you

- **Q1 — Canceled epic.**
  - Option (a): a followed epic closed as `canceled` or `superseded` releases the waiter,
    which matches `bead=` today.
  - Option (b): it stays parked as a blocker.
  - **I recommend (a) with a loud toast.** Parking forever on canceled work is worse
    than a clearly flagged release.
- **Q2 — `sase agent wait` CLI.** Should it get `--for-epic/--no-for-epic` with the same
  default, so the imperative and declarative waits agree? I recommend yes, as a
  follow-up.
- **Q3 — The approval dialog's "Wait for" field.** Its flat grammar
  (`src/sase/wait_spec.py`) would inherit the default. Does it need an opt-out spelling,
  or is "edit later in `w`" enough?
- **Q4 — Transition notice.** TUI toast plus timeline only, or also a silent
  notification-inbox entry (useful for mobile and Telegram)?

---

## 9. Recommended solution

Build **`for_epic` as a per-occurrence boolean keyword on `%wait(...)`, on by default for
agent-shaped targets**. Underneath, it is an **"epic follow-through" that promotes the
wait into a pinned bead wait**:

1. **Make the agent→epic link authoritative first.**
   - `sase bead work` writes `created_epics.json` into the creating run's artifact
     directory at the moment the epic becomes durable (after the plan-link commit,
     before phases launch).
   - `sase bead create -r epic` does the same for an epic an agent creates in its own
     turn.
   - Stop overloading `epic_bead_id`.
   - The plan's `bead_id:` frontmatter is a second, independent source.
2. **Parse and validate strictly.**
   - Accept `for_epic=true|false` only together with an agent target in the same `%wait`.
   - Reject it with an identical hard error and Error-severity editor diagnostic
     otherwise, and also reject conflicts and non-boolean values.
   - Apply the default at launch and store it as `wait_for_epics_of`. Markers without
     that field never follow.
3. **Resolve through one shared state machine:** ARMED → NONE | AWAITING_EPIC |
   FOLLOWING.
   - When an armed target's member runs resolve and the ledger (or plan) names epics,
     append those IDs to `wait_for_beads`, pin the target in `resolved_deps`, and record
     provenance in `wait_epic_follows`.
   - From then on, the existing bead-wait machinery does the work: sync hints,
     fail-closed reads, `awaits` links, run-now and `w` editing.
   - Guard against deadlock with a subtree check, and extend terminal-blocker
     notifications for epics that can never close.
4. **Make the hand-off visible.**
   - Row: `WAITING ↪ ◐ sase-7k 2/5`.
   - Detail panel: `[agents] planner ✓ ↪ sase-7k ◐ 2/5 phases · following since 14:32`.
   - One toast when the transition happens, and an `EPIC FOLLOW` milestone in the
     timeline.
   - `{{ agents["planner"].epic_bead_id }}` so the follow-up prompt can name the epic it
     waited for.
5. **Ship in three safe phases** (ledger, then opt-in, then flip the default), with a
   regression test proving the epic land agent still releases under the new default.

You get what you asked for: launch the follow-up prompt next to the planner and forget
about it. The new default can't strand or deadlock the epic machinery, and you can always
see why a waiter hasn't started yet.
