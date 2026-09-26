# SASE Goals: host-owned outcomes as the verification inbox

**Researcher:** `research.2m.grk`  
**Date:** 2026-09-26  
**Status:** Independent design research. Not an implementation plan.  
**Workspace inspected:** `sase_41` (sase + linked `sase-core`)

---

## Verdict

The motivation is sound and the feature is worth building. Agent completion is the wrong attention signal. Goal completion — an explicit, evidence-backed claim that a stated outcome is done — is the right one.

The sketched implementation is not. Requiring agents to notice `SASE_PLAN`, invoke a new skill, and create or link a goal at the start of every conversation fights SASE's host-owned, single-turn architecture. It will be skipped, duplicated, and slow. Goals should be bound by the host at launch, closed by a required finalizer, stored as a hot set of live outcomes, and presented as a verification inbox — not as a second issue tracker and not as an agent-side ritual.

**Build Goals. Do not build `/sase_new_goal` as a mandatory conversation-start skill.**

---

## 1. Is this a good idea?

Yes, with the adjustments in [§4](#4-adjusted-requirements).

Today the user is notified when an *agent* finishes. That is a process event. What they actually need is a *product* event: "the outcome I asked for is claimed complete; here is what to look at." Those are different:

| Agent finished | Goal claimed complete |
| --- | --- |
| A planner proposed a plan | The plan exists (PlanApproval already covers this) |
| A clan member finished one slice | The shared outcome may still be open |
| A monitor or pipe successor exited | Nothing for a human to verify |
| A question-answering agent replied | The answer is ready to read |
| An implementation agent committed and exited | The change is ready to inspect |

The Agents-tab unread marker and the notification `done` tab both project from user-agent completion notifications (`docs/notifications.md`). That is why they are noisy: every visible agent that reaches a terminal state flags the human, including work that does not need review.

Goals give SASE a place to hang that distinction. They also give every agent a durable "why," which plans already have (`goal:` is required on tale/epic frontmatter since the `202608` schema cutover) and ad-hoc agents currently lack.

This is not a substitute for beads. Beads track work items (plan, phase, task) with triage, sizes, descendants, and a 6,000+ row store. Goals track *outcomes the human may need to verify*. One epic can have many phase beads and one goal. One ad-hoc question has no bead and still needs a goal.

---

## 2. Critique of the sketched plan

### 2.1 Agent-side goal creation at conversation start will not work

The prompt suggests: every non-planner agent checks `SASE_PLAN` at the start of every conversation, and if it is unset, invokes `/sase_new_goal` to create or link a goal.

That design fails several constraints that are already decided and loaded into every agent:

- **Agents are single-turn** (`decisions:single-turn-agents`). A skill that must run before "real work" either burns the only turn on bookkeeping or is skipped so the work can happen.
- **Skills are advisory.** There is no host enforcement that a skill ran. Agents skip skills constantly. A required outcome that lives behind a skill is not required.
- **The host already knows whether a plan is associated.** `SASE_PLAN` is injected by the host for plan-approval follow-ups (`src/sase/axe/run_agent_exec_plan_accept.py`) and session-attach launches (`src/sase/agent/_agent_session_attach_launch.py`), and is *stripped* from nested launches unless re-supplied (`src/sase/agent/launch_spawn.py::_remove_inherited_sase_plan_env`). Asking the model to re-detect an env var the host set is theatre.
- **Planner exemption is messy.** Planner shells are identified by host metadata (`PLAN_CHAIN_PLAN_SUFFIX` / `--plan` in `src/sase/plan_chain.py`), not by "this agent intends to call `/sase_plan`." A model cannot reliably know it is a planner at turn start. Planners also need a goal: *author a plan for X*. `sase plan propose` is the close. PlanApproval is the verification. Exempting them creates a hole and a special case.
- **Linking to an existing goal at turn start is a token and judgment tax.** Listing every active goal, embedding them, and asking the model to match is slow, expensive, and wrong often enough to create duplicate goals. Inheritance (session, clan, plan, explicit `%goal`) is the reliable match. Semantic search is not.

Lived counterexample: this researcher (`research.2m.grk`) launched with `SASE_PLAN` unset. Under the sketched rule, the first actions of this turn would have been "create or link a goal" rather than research. The three sibling researchers would have done the same, producing four goals for one swarm outcome. The host already knew this was a named clan member of a research swarm. That is the binding the host should have made.

### 2.2 "All sase agents MUST have a goal" is too broad as stated

SASE "agents" on the Agents tab include agent shells, monitor shells, gate shells, and `%proc` shells (`docs/architecture.md`, `docs/ace.md`). Hidden background agents (summarize-hook, fix-hook, mentor) already write *silent* completion notifications. Repeat slots, pipe successors, and land/phase workers are further specializations.

A monitor that ran `just check` does not need its own goal. A PlanApproval gate shell does not. A hidden hook does not. Forcing a goal onto every row would recreate the noise this feature is meant to kill.

The requirement that is actually justified: **every user-visible work agent shell is bound to a goal before it is admitted.** Mechanical shells inherit or are exempt. See [A1](#a1-bind-work-agent-shells-not-every-row).

### 2.3 Goals are not beads, and must not be stored like beads

It is tempting to add a `goal` bead type. Beads already have status, close-with-note, artifact refs, cross-machine git sync, a TUI pane, and a notification panel. They are the wrong shape:

- Task beads require size, catalog type, and TaskTriage. "Answer this question" is not a task bead.
- `sase bead list` / `stats` reduce the *entire* event store. In this project that is **6,320 issues, of which 5,859 are closed (93%)**. `sase bead stats` took **26.6 seconds** in this workspace. That is the opposite of "done goals have no effect on performance."
- Bead close means "this work item is finished." Goal close should mean "please verify this outcome." Collapsing those two verbs will make both worse.
- Closing never cascades; epics have descendants; land agents own parent close. That policy is correct for work tracking and wrong for a verification inbox.

Beads stay. Goals sit beside them. A plan bead remains the executable epic; the plan's `goal:` field becomes (or links to) the Goal artifact the human watches.

### 2.4 A fourth main TUI tab would fight the chrome

sase's TUI has three tabs by design: **Agents | Artifacts | Services** (`docs/ace.md`). Artifacts already hosts Agent, Stitch, Patch, Bead, Plan, Research, and File panes, with a contract-driven shell, query bar, relations, and link-follow (`$` rail, `Ctrl+O` trail). Goals belong there as a built-in pane, plus a grouping mode and header block on the Agents tab — not as a fourth top-level tab.

### 2.5 What the sketch gets right

- Reuse plan `goal:` when a plan is associated. That field is already required, already rendered in agent detail (`ace: show associated plan goals in agent details`), and already the outcome statement.
- A **new finalizer** for keep vs close, with evidence on close. This matches host-owned completion (`decisions:host-owned-completion`) and the existing `bead_action: keep|close` pattern on `builtin@commit`.
- **Notify on goal close**, not on agent complete. That is the actual user need.
- **Artifact links** as the jump graph from a goal to agents, prompts, plans, stitches, and files. The link rail and cross-tab follow already exist.
- **O(n) in the hot set**, where done (human-settled) goals do not participate. That requirement is the storage design, and it is non-negotiable given bead-store reality.
- **Cross-machine access** for anyone working the project. Durable state belongs in a git sidecar with a machine-local hot projection, following artifact links and beads — not in `~/.sase` agent metadata alone.

---

## 3. Current landscape (evidence)

### Plans already have goals; agents already show them

Tale and epic frontmatter require `goal:` (`docs/sdd.md`). ACE already resolves an associated plan for the selected agent (`src/sase/ace/tui/models/agent_associated_plan.py`) from `plan_path` / `archived_plan_path` / `sdd_plan_path` / `epic_plan_ref` / bead ids, and renders the goal in the detail header with responsive wrapping. Session completion for `#fork` already surfaces "the goal for a tale or plain plan."

What is missing is a *standalone* Goal identity for agents without a plan, a keep/close verb, evidence, and a verification notification.

### `SASE_PLAN` is a host launch binding, not an agent checklist

| Path | What happens |
| --- | --- |
| Plan approval follow-up | Host sets `SASE_PLAN` to the committed or archived plan file, then launches the coder with `@plan:…` (`run_agent_exec_plan_accept.py`) |
| Session attach | Host copies the parent's plan into `SASE_PLAN` when present |
| Nested `sase run` / spawn | Host **deletes** inherited `SASE_PLAN` unless the new launch supplies one |
| This researcher | `SASE_PLAN=unset` |

The host is already the authority for plan association. Goal association should use the same door.

### Finalizers are the right close mechanism

Configured in `finalizers:` (`src/sase/default_config.yml`): `defaults: [commit]`, `required: []`, instances with `use`, `after`, `max_attempts`, `refusal`. `%final` selects instances; required instances cannot be removed. The agent submits a declaration; the host executes.

The commit finalizer already asks `bead_action: keep|close` when `assigned_bead` is present (`FinalizerAssignedBeadWire` in sase-core). A goal finalizer is the same shape: host publishes an `assigned_goal` in the finalizer context; the manifest must say `keep` or `close`; `close` carries evidence; the host mutates the store and notifies.

### Attention today is completion-shaped

- Successful visible user-agent completions carry the `done` tag and land in the Done notification tab.
- Agents-tab unread is projected from those notifications (plus epic-launch / monitor-settlement rows).
- Selecting the agent row dismisses the notification.
- Hidden agents are silent.

Replacing that projection with "goal entered `needs_review`" is a small, high-leverage change once goals exist. Until then, do not silently drop completion unread or the user loses the only inbox they have.

### Artifact identity and links are ready to extend

Reserved kinds: `stitch`, `patch`, `bead`, `agent`, `file`, plus `tool` (reserved, no public projection). Document roles (`plan`, `research`, …) are provider-backed. There is no `goal` kind and no `prompt` kind in the compiled catalog; archived prompts live in the hidden agents sidecar and are reached from plan `PROMPT` headers.

The link registry is closed. Writable: `related`, `supersedes`, `implements`, `derives-from`. Projected: `produced-by`, `launched`, `awaits`. Observational: `cites`, `read`. Jump UX (`$` rail, numbered follow, `Ctrl+O` trail) is pane-agnostic.

### Cross-machine and performance precedents

- **Beads:** git sidecar, event streams, sqlite/jsonl projections, background refresh (`sdd.bead_refresh`, TTL 120s). Fast enough for occasional CLI; **not** fast enough for a TUI hot path that must ignore closed rows (26s stats over 6,320 issues).
- **Artifact links:** durable events + machine-local aggregate; machine writes stay off the primary (`decisions:machine-link-writes-off-primary`).
- **Patches:** active file vs archive file. Closed records leave the hot set.
- **Notifications:** JSONL of everything; unread is a filter. Fine at inbox scale; the wrong lesson for a store that will accumulate years of closed goals.
- **Agent artifact index:** Rust-owned, upsert-on-write, query without a full scan. The right *shape* for a hot goals index.
- **Fleet attention:** remote pending decisions already poll independently of the visible Agents list (`docs/notifications.md`). Goal-review rows should ride that inventory.

### Rust-core boundary

Anything the TUI, CLI, editor, and mobile gateway must agree on belongs in `sase_core` (`sase/memory/rust_core_backend_boundary.md`, `docs/rust_backend.md`). Goal identity, lifecycle, hot-index reads, launch binding, finalizer payload validation, and notification tagging are core. Pane widgets, keybindings, and chrome stay in Python.

---

## 4. Adjusted requirements

These replace or narrow the original bullets. Each is an intentional product change, not a restatement.

### A1. Bind work-agent shells, not every row

**Original:** All sase agents MUST have a goal.

**Adjusted:** Every **user-visible work agent shell** is bound to a goal before admission. Exempt: monitor shells, gate shells, `%proc` shells, hidden/silent agents, and host-owned settlement rows. Clan members, session members, and repeat slots **share** the unit's goal rather than each inventing one. Planner shells **are** bound: their goal is "author a plan for \<request\>."

### A2. Host binds at launch; agents do not self-onboard

**Original:** Non-planner agents check `SASE_PLAN` and invoke `/sase_new_goal`.

**Adjusted:** The launch path binds a goal the same way it binds a workspace, model, and (when present) `SASE_PLAN`. Binding order is in [§6](#6-launch-time-binding). A launch that cannot bind fails closed (or, for interactive TUI, prompts the user) — it does not start a goal-less agent and hope. An optional `/sase_goal` skill exists for *retitle / relink / list* during the turn, never as a mandatory first action.

### A3. Many agents, one goal

**Original:** Implied 1:1 (every agent has a goal; create if missing).

**Adjusted:** The cardinality is **many-to-one**. A clan, a session, an epic's phases, and a `%repeat` chain share one Goal. The unit of human attention is the goal, not the agent. Creating a new goal is the fallback when nothing to inherit exists and the prompt did not name one.

### A4. "Done" for performance means human-settled, not agent-claimed

**Original:** O(n) in active goals; done goals have no effect.

**Adjusted:** The hot set is `active` ∪ `needs_review`. Agent close moves a goal to `needs_review` and **keeps it hot** — otherwise the verification inbox vanishes. `verified`, `canceled`, and `superseded` leave the hot set. O(n) with n = live outcomes the human might still care about, typically dozens, not thousands.

### A5. Close is a proposal; the human settles it

**Original:** Agent closes the goal with evidence; notify the user to verify.

**Adjusted:** Agent `close` means **propose done**. The host validates evidence, moves the goal to `needs_review`, and notifies. The human **verifies**, **rejects** (reopens with a note, optionally relaunching), or **cancels**. Do not auto-archive on agent close. Do not start with a heavy confirmation gate for every kind; use unread-until-ack for informational goals and a stronger ack for implementation (see [§8](#8-notifications-and-human-settlement)).

### A6. No fourth main tab

**Original:** A new Goals panel somewhere.

**Adjusted:** A built-in **Artifacts ▸ Goals** pane (inventory), **Agents-tab grouping `BY_GOAL`**, a **goal block** in agent detail (generalizing the plan-goal header), a **`verify` notification tab**, and a **top-bar chip** for `needs_review`. Same jump machinery as today's link rail.

### A7. Do not replace beads, plans, or PlanApproval

PlanApproval, EpicApproval, and TaskTriage remain the review surfaces for those objects. Closing a planner goal does **not** emit a second "please verify" notification; the approval gate *is* the verification. Closing a tale/epic implementation goal *does* notify, because that is the gap today.

### A8. Ship behind a beta flag; sunset completion unread later

User-reaching behavior. Flag `goals` (`beta`, default off) via `sase flag new`. While off, today's completion unread and `done` tab are unchanged. After the Goals inbox is trusted, a later phase makes completion notifications silent by default (sunset), with Goals as the attention surface.

---

## 5. Recommended product model

### What a Goal is

A Goal is a first-class artifact, `goal:<id>`, meaning:

> An outcome a human asked for, that one or more agents are pursuing, that can be claimed complete with evidence, and that may need human verification.

It is **not** a plan, a bead, an agent, or a prompt. Those *link* to it.

### Fields (hot record)

| Field | Role |
| --- | --- |
| `id` | Stable, `sase-g<n>` (project prefix + short id). Artifact ref `goal:sase-g12`. |
| `title` | One line, imperative or outcome-shaped. From plan `goal:`, else from the launch prompt. |
| `statement` | Optional longer outcome text (plan `goal:` when it is more than a title). |
| `kind` | Closed: `question`, `implementation`, `research`, `plan`, `review`. Drives evidence rules and settlement UX. |
| `status` | `active`, `needs_review`, `verified`, `canceled`, `superseded`. |
| `project` | Project key. |
| `origin_prompt` | Archived prompt identity (agents-sidecar path / prompt snapshot id). **Required.** |
| `plan_ref` | `plan:…` when derived from a plan. |
| `bead_id` | Optional associated plan/phase/task bead. |
| `bound_agents` | Names currently or historically bound (hot record keeps live ones). |
| `evidence` | Present only in `needs_review` and later: claim, refs, verify-for-human, closer agent, timestamp. |
| `created_at` / `updated_at` | Timestamps. |

IDs stay opaque like beads. Titles are the UI. Do not use slug-from-title as identity.

### Kind catalog (small, closed)

| Kind | Typical origin | Default close evidence | Settlement |
| --- | --- | --- | --- |
| `question` | Ad-hoc Q&A prompt | Agent transcript (`agent:<name>`) + claim | Unread until read/ack |
| `research` | Research swarm / report | Report artifact ref + claim | Unread until the report is opened or acked |
| `plan` | Planner shell | Proposed plan ref; close is implicit in `sase plan propose` | PlanApproval / EpicApproval (no extra notify) |
| `implementation` | Plan follow-up, `#commit`/`#pr` work | ≥1 stitch or file snapshot + verify-for-human steps; tool-run receipt when a check ran | Explicit ack (key or short gate) |
| `review` | Reviewer / mentor-like user agent | Notes artifact or transcript + claim | Unread until read/ack |

### Lifecycle

```
launch binds ──► active ──► (keep: still active)
                    │
                    ├── close + valid evidence ──► needs_review ──► verified   (cold)
                    │                                   │
                    │                                   └── reject ──► active (hot, note appended)
                    │
                    └── cancel ──► canceled (cold)
supersede ──► superseded (cold)
```

**Host rule for `close`:** refuse if any other non-terminal work-agent shell is still bound to this goal. The last finisher closes; everyone else `keep`s. The error names the still-running binders so the agent can resubmit `keep`. This makes clan/session/epic behavior correct without asking the model to invent policy.

**Epic policy:** phase workers `keep`. The land agent (or the last remaining phase if there is no land) may `close`. Host-enforced via the live-binder rule plus role: a phase agent that tries to close an epic goal while siblings are running is refused; if it is truly last, close is allowed.

**Planner policy:** `sase plan propose` is an implicit `close` of the planner goal, evidence = the archived plan. No goal-finalizer extra notify. Approval of the plan **creates** (or binds) the implementation/research goal from `goal:` for the follow-up.

### Cardinality examples

| Launch | Goal |
| --- | --- |
| `+sase what does X do?` | New `question` from the prompt |
| `%auto` tale planner then coder | Planner: `plan` goal. Coder: new `implementation` goal from plan `goal:` |
| Epic phases + land | One `implementation` goal from plan `goal:`; all phases + land bound to it |
| Research swarm of four | One `research` goal; all members bound |
| `%repeat:3` | One goal; all iterations bound; last iteration may close |
| Session `--plan` then `--code` | Plan goal then implementation goal, same session, different goals |
| `#fork` of an agent with a live goal | Inherit that goal |

---

## 6. Launch-time binding

This is the heart of reliability. Binding happens in the launch path (typed `LaunchPlan` when `typed_launch_units` is on; otherwise the same logical step in today's spawn path), **before** the provider process starts.

### Resolution order

1. **Explicit** `%goal:<id>` / `@goal:<id>` in the launch prompt (user or templated).
2. **Session inherit** — attach/`session=` parent has a goal.
3. **Clan inherit** — `%clan` / `clan=` members share the declarer's goal; the first surviving member creates if needed, later members join (same "first surviving member claims the clan" pattern used for typed launches).
4. **Plan** — `SASE_PLAN` or an `@plan:` that will be associated: use or create the Goal for that plan's `goal:` field. Planner shells get a `plan`-kind goal instead, titled from the user request.
5. **Bead** — `%wait(bead=)` / assigned bead: title from the bead, kind `implementation` (or `review` if the prompt is a review).
6. **Mint** — derive `title` from the first meaningful line of the user prompt (stripped of directives and refs), `kind` from heuristics (question mark / "what"/"why" → `question`; research swarm / `research:` → `research`; VCS rollover `#commit`/`#pr` → `implementation`; else `question` for read-only, `implementation` for dirty-work rollovers). Always record `origin_prompt`.

No semantic "find a similar active goal" at launch. If the user wanted an existing one, they name it. If the agent notices a duplicate mid-turn, `/sase_goal link` (or `sase goal link`) is available; the finalizer can also warn.

### What the agent sees

- `SASE_GOAL=sase-g12`
- `SASE_GOAL_TITLE=…`
- `SASE_GOAL_KIND=research`
- Prompt injection of `@goal:sase-g12` (same pattern as `@plan:` for coders), so the statement and links expand.
- Finalizer context includes `assigned_goal` analogously to `assigned_bead`.

The agent does **not** need to "check SASE_PLAN at the start of every conversation." The goal is already there, the way the workspace and model already are.

### Interactive TUI launch

If the user is launching from the prompt bar and the resolver would mint a new goal, show the derived title in the launch preview (and allow `%goal:` completion against the hot set). Do not add a blocking extra modal on the default path; the derived title is almost always "what I just typed." A later polish can add a picker.

### Agent-initiated launches

`LaunchApproval` prompts inherit the requester's goal unless the requested prompt names another. A helper launched to "review the implementation" should usually **share** the implementation goal (`kind` stays; the helper is another pursuer) or mint a `review` sub-goal only if we later add parent/child goals. **v1: share. No goal tree.**

---

## 7. Finalizer and evidence

### Instance

New builtin provider `builtin@goal`, instance id `goal`.

```yaml
finalizers:
  defaults: [commit, goal]
  required: [goal]   # when assigned_goal is present; host can make this conditional
  instances:
    commit:
      use: builtin@commit
      ...
    goal:
      use: builtin@goal
      after: [commit]
      max_attempts: 2
      refusal: fail
```

`after: [commit]` so evidence can include stitches this turn produced. Required when `assigned_goal` is in the context (work-agent shells). Exempt shells never see the obligation.

Trigger: `Always` for bound work agents (not `DirtyRepository` — question agents have nothing dirty and still must keep/close).

Handoffs (`sase plan propose`, monitor, pipe, questions) skip the declaration today. **Exception:** `sase plan propose` performs the implicit planner-goal close in the propose path (host-owned, not a declaration). Monitor/pipe successors inherit the goal and do not settle it.

### Payload

```json
{
  "action": "keep | close | cancel",
  "progress": "one line; required for keep if the title would otherwise be stale",
  "claim": "one-line outcome that is now true; required for close",
  "evidence_refs": ["agent:research.2m.grk", "research:202609/….md"],
  "verify_for_human": [
    "Open @research:202609/sase_goals_host_owned_verification__grk.md",
    "Read the Verdict and Adjusted requirements"
  ],
  "reason": "required for cancel"
}
```

Limits: claim ≤ 240 chars (same as link `why`); `evidence_refs` ≤ 16, each must resolve; `verify_for_human` 1–5 lines, each ≤ 240 chars.

### What evidence should be

Evidence has to survive a skeptical human and a later agent. Prose-only "I did the thing" is not evidence. The host must be able to **resolve** every ref and attach it to the goal before flipping status.

**Minimum by kind:**

| Kind | Minimum refs | Host checks |
| --- | --- | --- |
| `question` | The closing `agent:<name>` (host may auto-insert) | Agent exists; claim non-empty; ≥1 verify step (often "read the reply") |
| `research` | ≥1 `research:` or `file:` report this run produced or cited | Ref resolves; preferably `produced-by` / `derives-from` the closer |
| `plan` | The proposed `plan:` (implicit on `plan propose`) | Plan archived and valid |
| `implementation` | ≥1 `stitch:` from this session **or** `file:` snapshot of the change, plus verify steps that name what to look at | Stitch resolves; if a `tool:` check ran, attaching the receipt is rewarded but not required in v1 (E4 receipts are the future hook) |
| `review` | Transcript or notes artifact | Resolves |

**Always require `verify_for_human`.** That list *is* the notification body. It is the difference between "agent finished" and "here is how to verify." Good steps are concrete (`open @goal:sase-g12`, `read the diff of stitch:…`, `run the demo in …`). Bad steps are "make sure it works."

**Reject close when:**

- another live work agent is still bound
- any `evidence_ref` does not resolve
- kind minimum not met
- `verify_for_human` empty
- claim empty
- the agent tries to close a `plan`-kind goal without going through `plan propose` (host closes that path itself)

**`keep`** is cheap: no evidence required. Optional `progress` note is appended to the goal's log. This is the common case (phase workers, clan members, intermediate session turns).

**`cancel`** requires `reason`, moves to cold `canceled`, does not notify as "verify this" (optional low-priority notice).

### Relation to `bead_action`

Keep them independent in v1. An epic lander may `bead_action: close` and `goal_action: close` in one declaration; a phase worker typically `keep` / `keep`. Do not infer one from the other. Coupling is a later convenience, not a v1 invariant.

### Prepared monitor completion

If a monitor is used as the last proof (`sase final prepare` + verify profile), a successful monitor may carry a prepared `goal_action: close` with evidence refs captured before the monitor started (e.g. the report path). On green, the host applies it. On red, the goal stays `active`. Same pattern as prepared commit completion (`docs/monitors.md`).

---

## 8. Notifications and human settlement

### Fire on `needs_review`, not on agent complete

When a goal enters `needs_review`:

- Write a notification tagged `verify` (and `presentation.panel: verify`).
- Icon/color: distinct from Done and Gates (recommendation: `◎` / a gold that is not the Done `#` and not the unread-agent yellow).
- Title: the goal title. Body: `claim` + `verify_for_human` + links.
- Jump target: Artifacts ▸ Goals, that row selected (and the link rail armed). Secondary jump: the closing agent on the Agents tab.

Do **not** fire for `plan`-kind closes (PlanApproval already did). Do **not** fire for `keep`. Do **not** fire for exempt shells.

### Settlement UX by kind

- **question / research / review:** unread notification; jumping to the goal or opening the primary evidence artifact marks the notification read. An explicit `v` (verify) on the Goals pane sets `verified` and drops the row from the hot set. If the user only reads and moves on, a later pass can treat "read + dismissed" as verify; v1 should still require `v` so "I glanced" ≠ "I accept."
- **implementation:** same pane, but `v` is the ack; optional confirm toast naming the claim. A full GoalVerification *gate* is reserved for a later phase if ack-without-looking becomes a problem. Do not start there; the user currently lives in unread-and-jump, and a gate on every landed change would be heavier than today's Done tab.

**Reject** (`r` on the Goals pane or notification): status back to `active`, note recorded, optional relaunch of a successor with the rejection note. This is the "you claimed done and I disagree" path that completion notifications cannot express.

### Agents-tab unread, after cutover

While `goals` is on: a finished work-agent row is unread **only if it is the closer of a `needs_review` goal** (or the user toggled `U`). Other completions are silent. That is the whole point.

While `goals` is off: today's behavior.

### Fleet

`needs_review` notifications are pending attention. They belong in the remote attention inventory so a goal closed on apollo can be verified from the laptop, using the existing Attention panel (`docs/notifications.md`).

---

## 9. TUI: intuitive, reliable, beautiful

Do not add a fourth main tab. Compose Goals from surfaces the user already knows.

### 9.1 Artifacts ▸ Goals pane (inventory)

Built-in pane, same shell as Beads/Plans (`docs/artifacts_pane_visual_grammar.md`):

- **Strip:** insert after Bead (work-tracking cluster: Bead, Goal, then document panes). Icon `◎`. Accent: a gold that is distinct from Stitch `#FFD700` and unread-agent yellow — recommendation `#E6B800` (test against dark `#121212` / light `#E0E0E0` like the provider palette).
- **Default query:** `status:active,needs_review` (hot set only). `status:verified` is opt-in and reads the cold archive, never on the first paint.
- **Row:** status glyph · kind · title · live agent count · age. `needs_review` rows wear the unread treatment (bold / gold gutter).
- **Detail:** statement, origin prompt, plan/bead, bound agents, evidence block, `verify_for_human` as a checklist, Links table.
- **Empty state:** "No live goals. New work agents bind a goal at launch." No `/sase_new_goal` call to action.
- **Keys:** Enter follows the primary link (closer agent if `needs_review`, else origin prompt or plan). `v` verify, `r` reject, `$` link rail. Copy targets: `reference`, `title`, `handoff`, `json`, `id`.
- **Grouping:** `by_status`, `by_kind`, `by_project`. Default `by_status` so `needs_review` is a block at the top.
- **Performance:** the pane reads **only** the hot index. No archive walk on refresh. Off the event loop (`tui_perf.md`).

This is the panel the user asked for.

### 9.2 Agents tab

- **Row subtitle:** goal title when bound (today's plan-goal detail moves up one level of visibility). `needs_review` paints the same unread chrome the completion marker uses now.
- **Grouping `BY_GOAL`:** add to the cycle after `BY_STATUS`. Groups are goal titles; unbound/exempt shells fall into "No goal." Folding a goal hides its agents. This is the "jump to any agent on the Agents tab linked to that goal" view, and it will feel native.
- **Detail header:** extend the associated-plan block into an **associated-goal** block: title, status, kind, one-line statement, then plan/bead as secondary. Reuse the responsive wrapping already built for plan goals.
- **Link rail:** when a goal is bound, `$` includes `goal:…` as a first-class neighbor.

### 9.3 Notification chrome

- New panel tab `verify` (priority between Gates and Errors, ~55). Top-bar chip counts `needs_review` only.
- Done tab remains for completion events until the sunset phase.

### 9.4 What not to build in v1

- A Goals *deck* (`DeckId.GOALS`) — three decks (main/files/tools) are enough; the detail header block covers the selected agent's goal.
- Goal trees / sub-goals / OKR nesting.
- A prompt-bar "goal picker" modal on every launch.
- Semantic duplicate detection at mint time.

---

## 10. Storage: O(n) hot set, durable events, host-owned writes

### Why not each existing store

| Store | Why it loses |
| --- | --- |
| Bead event store | Closed rows dominate; list/stats scan everything; 26s in this project |
| Plan markdown | Goals without plans; status machine; TUI mutation |
| Agent `agent_meta.json` | Machine-local; dies with dismiss; not a project object |
| Notification JSONL | Inbox, not source of truth; cannot be the graph other machines query |
| Document sidecar as markdown corpus | Gets a pane for free, loses a real lifecycle and hot index |

### Recommended layout

**Durable (sidecar, git, cross-machine):**

A `goals/` tree. Prefer the **plans sidecar** (`sase/repos/plans/goals/`) for v1:

- Plans clones already exist in every numbered workspace.
- Plan-derived goals naturally sit next to the plan files that defined them.
- Avoids a schema-4 beads-style sidecar adoption (heavy: store record, init, auto_clone, old-install rejection).
- Avoids bead-store lock contention (the reason beads got their own sidecar).

Layout:

```
goals/
  events/streams/<goal-id>.jsonl   # append-only
  archive/<YYYYMM>/<goal-id>.json  # cold projection after verify/cancel/supersede
```

Do **not** put a growing `issues.jsonl` of all goals in the hot path.

**Hot (machine-local, TUI/CLI/agent list):**

```
~/.sase/projects/<project-key>/goals/active.jsonl
```

One compact record per hot goal. Rebuildable from events. List/get-active reads **only this file**. Close-to-`needs_review` updates a line; verify/cancel **deletes the line** and writes the archive projection. That is O(n) with n = hot goals, and closed history cannot affect it.

Rust core owns: event append, reduce-one-stream, hot-index upsert/delete, list-hot, get. Python owns: CLI chrome, TUI widgets, launch/finalizer glue.

**Writes:** host-owned, off the agent's primary/workspace clone — same decision as artifact-link machine writes. `sase goal …` talks to the host publisher (hidden clone + outbox). Agents never `git commit` goal files in the numbered workspace. This is what makes cross-machine sync reliable instead of a merge-conflict factory.

**Read path for agents:** `sase goal list` (hot index, default) must return in well under the CLI fast-path budget. No sidecar fetch on the list path; background refresh (copy `sdd.bead_refresh`: mode `background`, TTL ~120s) updates the hidden clone and rebuilds the hot index. Stale-while-revalidate is acceptable; blocking pull is not.

**Fleet:** the hot index is per machine. After sync, each machine's index converges. `needs_review` notifications are the cross-machine *attention* channel and must not wait on git.

### Artifact kind

Add reserved live kind `goal` to `artifact_ref/kinds.rs`:

- `argument_summary`: `goal:<id>`
- `offered_in_completion`: true
- generated page (like beads/agents), not a hand-edited markdown file

Document-provider pane is the wrong implementation (goals are not a glob of markdown). Built-in adapter, like Beads.

### Link relations

Keep the registry small. **v1 projected + derived, one new writable slug only if needed.**

| Edge | How |
| --- | --- |
| `agent:<name> pursues goal:<id>` | **New projected relation** `pursues` / `pursued-by`, from the binding (like `implements` from `bead_id`) |
| `goal:<id> derives-from plan:<path>` | Derived when the goal is minted from a plan |
| `goal:<id> derives-from` origin prompt | Derived; prompt identity as the target (even if prompt is not a public kind, store the agents-sidecar locator and render it on the goal page) |
| Evidence refs | Stored on the close event; also `related` or, better, a projected `evidenced-by` from the close record. Prefer **not** inventing `evidenced-by` in v1: render evidence from the goal record itself, and let the existing `$` rail list those refs as jump targets without a new slug |

If `pursues` is too much registry churn, project `agent implements goal` — but `implements` is documented as plan→bead and the direction examples would lie. **Add `pursues`.** It is the accurate verb, and the rail becomes "agents pursuing this goal" in one hop.

`cites` continues to record that an agent prompt mentioned `@goal:`.

---

## 11. CLI, skill, and xprompts

### CLI (`sase goal`, default list)

| Command | Role |
| --- | --- |
| `sase goal list` | Hot set. Default. Fast. `--status` can add cold with an explicit archive read. |
| `sase goal show <id>` | Full record + links |
| `sase goal read <id> -r …` | Audited, via `sase artifact read goal:…` |
| `sase goal link <id>` | Bind current agent (or `--agent`) to an existing hot goal |
| `sase goal update <id> --title …` | Retitle; does not mint |
| Humans: `sase goal verify \| reject \| cancel` | Settlement |

No agent-facing `sase goal create` on the default path. Minting is launch-owned. A hidden/debug create can exist for recovery, not for the skill.

Alphabetical flags, short aliases, beautiful list output (`cli_rules.md`). Completion kind `goal` for hot ids.

### Skill `/sase_goal` (optional, never mandatory)

List hot goals, link, retitle. **Not** invoked at conversation start. Not a substitute for host binding. Generated like other bundled skills (`sase/memory/generated_skills.md`).

### Directive

`%goal:<id>` / `%goal(<id>)` binds at launch. Completes against the hot set. Document in the directive matrix.

---

## 12. Worked examples

### This research swarm

Host mints one `research` goal at the lead launch: *Recommend how to implement SASE Goals.* Members `research.2m.cdx|mus|gem|grk` inherit via clan. Each `keep`s (the lead synthesizes). Lead `close`s with `evidence_refs` of the four `__*.md` reports plus the synthesis, and `verify_for_human`: "read the synthesis; spot-check one researcher report." Notification lands on `verify`. Bryan opens Artifacts ▸ Goals, follows the report links, presses `v`.

Under the original sketch, four researchers each run `/sase_new_goal` because `SASE_PLAN` is unset. Four goals. Four Done-like pings. The feature would have failed its own motivation on day one.

### Ad-hoc question

`+sase how does SASE_PLAN get set?` → mint `question` *Explain how SASE_PLAN is set.* Agent answers, `close`s, host attaches `agent:<name>`. Notification. Bryan reads the reply, `v`. No bead, no plan, no noisy "agent done" besides this.

### Tale `%auto`

Planner goal *Author a plan for X* closes on propose (PlanApproval fires, no goal-verify notify). On approve, host mints `implementation` from `goal:` and binds the coder. Coder implements, `close`s with stitches + "open the PR; run the demo." That notify is the one Bryan wants.

### Epic

One `implementation` goal from `goal:`. Eight phase agents `keep`. Land `close`s. One verification, not eight.

---

## 13. Implementation shape (for a later epic, not this report)

This is **epic** work, beta-flagged (`goals`). Suggested phases, each sized as a real coding unit:

1. **Core store + kind + CLI list/show** (Rust hot index + events; Python CLI). No TUI. No launch change.
2. **Launch binding** + `SASE_GOAL` + `@goal:` expansion + `%goal` directive.
3. **Finalizer `builtin@goal`** + evidence validation + live-binder close rule.
4. **Notifications + `verify` tab** + Agents-tab unread projection when flag on.
5. **Artifacts ▸ Goals pane** + link rail + `v`/`r`.
6. **Agents `BY_GOAL` grouping** + detail header block.
7. **Fleet attention** for `needs_review`.
8. **Sunset** completion-unread default (separate flag or the same flag's second behavior), only after 5–6 are trusted.

Do not land 8 before 5. Do not land 3 without 1–2 (a finalizer with nowhere to write is theatre).

---

## 14. Risks

| Risk | Mitigation |
| --- | --- |
| Agents `keep` forever; nothing enters `needs_review` | Required finalizer; missing payload fails the turn (recovery), same as commit declarations |
| Agents `close` everything to be safe | Live-binder rule; kind evidence minima; reject empty verify steps |
| Duplicate goals for the same prompt | Host mint + inherit; no agent create; explicit `%goal` |
| Hot index drift vs sidecar | Rebuild from events; doctor; backfill job like artifact links |
| Merge conflicts on goal files | Host-owned publisher, off primary; append-only events |
| Flag-off users lose nothing | Completion unread unchanged until sunset |
| Goal title quality on mint | First prompt line is good enough; `/sase_goal` retitle; TUI preview |
| Confusion with beads | Copy, empty states, and docs say "outcome to verify" vs "work item" |
| TUI perf | Hot file only; off event loop; no archive on first paint |

---

## 15. Recommended solution (short)

**Goals are host-owned outcome records.** The host binds every user-visible work-agent shell to a goal at launch (inherit session/clan/plan/bead, else mint from the prompt). Plan `goal:` becomes that plan's Goal. Many agents share one goal. A required `builtin@goal` finalizer asks `keep | close | cancel`. `close` is a proposal: host-checked evidence (resolvable refs + `verify_for_human`) moves the goal to `needs_review` and notifies a `verify` inbox. The human verifies or rejects. The TUI shows live goals in Artifacts ▸ Goals and groups Agents `BY_GOAL`. Storage is append-only sidecar events plus a machine-local hot `active.jsonl` so listing is O(n) in live goals; verified/canceled rows cannot touch that path. Writes stay on the host publisher. Ship as beta `goals`. Do not require a conversation-start skill. Do not use the bead store. Do not add a fourth main tab. Do not notify on planner-goal close. Do not treat agent completion as the attention signal once this inbox exists.

That is the design I would implement.
