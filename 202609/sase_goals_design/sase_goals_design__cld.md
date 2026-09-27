# Goals for SASE: the host binds each agent, the agent names the goal, a Goals tab collects claims to verify

*Researcher: cld · 2026-09-27 · project: sase*

## 0. Bottom line

**Build Goals.** Today SASE's unit of attention is a *process* ("agent X stopped"). What you actually check is an *outcome*. I counted agent runs on athena for the sase project over the last 7 days: **2,047 agent turns served roughly 310 outcomes** (about 6.6 turns per outcome). Almost every one of those turns can light an unread dot today. Moving attention to "an agent claims a goal is done" is the right fix.

I would change three parts of the proposal:

1. **The host binds the goal and the agent names it** (instead of agents checking `SASE_PLAN`).
   - The launcher already knows each agent's plan, session, clan, bead, and parent, so it binds a goal *before the model starts*.
   - About 90% of turns get their goal mechanically.
   - For the rest, the host creates a **draft** goal from the submitted prompt. The agent's first act is to **name** that draft or **adopt** an existing active goal.
   - Result: you never have to write goals, no agent ever runs without one, and planners pay nothing.
2. **Agents claim; you close.**
   - The finalizer decision is `keep_open` or `claim`.
   - A claim moves the goal to **Review** and notifies you. Pressing `v` closes it.
   - Evidence has three parts: artifact refs the host can resolve (which double as your jump targets), a **"check it" recipe** of steps for you, and any **gaps** the agent admits to. The host gathers most of the refs itself.
3. **A top-level Goals tab.**
   - It is a live board with three lanes: **Review · Running · Idle**.
   - Each goal opens as a card that reads **You asked → Claim → Check it → Evidence**, and every ref on it is a numbered jump.
   - An **Artifacts ▸ Goal** pane keeps history. This is the same live/history split the Agents tab and Artifacts ▸ Agent already have.

**Storage.** A **goal ledger** that cannot produce git conflicts: immutable event files plus existence markers under `goals/live/`.
- It lives in the project's shared beads sidecar repository.
- It is written through the host-owned hidden clone.
- Reads cost O(n_active), so done goals are never touched.

---

## 1. Sources and measurements

**Prior research.** `research:202609/goal_outcomes_and_verification/goal_outcomes_and_verification.md`, read through an audited `sase artifact read`.

**Code in `sase`:**
- Launch: `agent/launch_spawn.py`, `axe/run_agent_*`.
- Finalizers: `finalizers/*`, the `sase_final` skill.
- Notifications: `run_agent_runner_finalize.py`, `notifications/*`.
- Artifact links and refs: `artifact_links/*`, `sdd/_artifact_link_*`, `artifact_providers/*`.
- TUI: `tab_order.py`, `tab_bar.py`, Artifacts panes, decks, link follow, unread projection.

**Code in `sase-core`:** `finalizer/wire.rs`, `bead_action/policy.rs`, `tool_run` receipts, `bead/read.rs`.

**Decision records:**
- `host-owned-completion`
- `single-turn-agents`
- `gates-never-block`
- `receipts-prove-before-they-skip`
- `machine-link-writes-off-primary`
- `rust-core-required`
- `corpus-before-mechanism`

**New measurement.** I classified every `agent_meta.json` written in the last 7 days under `~/.sase/projects/gh_sase-org__sase` (athena only; apollo is not included):

| Launch class (7 days, athena, sase)                                 |     Turns | How the goal would be bound                  |
| ------------------------------------------------------------------- | --------: | -------------------------------------------- |
| Epic phase workers (+ their successors)                             |       623 | epic bead → plan → goal (mechanical)         |
| Epic land / epic-bead agents                                        |       216 | epic bead → plan → goal (mechanical)         |
| Other session successors (monitor, gate, code, pipe, retry)         |       622 | inherit the session's goal (mechanical)      |
| Routine (chop) runs — 2 routines                                    |       277 | the routine's standing goal (mechanical)     |
| Root clan members — 39 clans, mostly research swarms                |       133 | **one** draft per clan → first member names  |
| Plain root launches                                                 |       176 | draft → agent names or adopts                |
| **Total**                                                           | **2,047** | ≈215/week (≈30/day) need an agent to name one |

Distinct outcomes that week: 96 epics + 176 root launches + 39 root clans, about **310**. There is some overlap, because a root planner's plan can become one of the epics. Two conclusions follow:

- **Most of the work is mechanical.** Only about 10% of turns would ever touch goal authoring.
- **This is a verification-fatigue problem, not a performance problem.** About 30 new user-level outcomes arrive per day, and the active set is dozens, not thousands. The hard part is making each check fast to judge, not listing goals quickly.

---

## 2. Is this a good idea?

**Yes.** Four reasons, in order of value:

1. **Attention matches what you care about.** One goal-level signal replaces the roughly 6–7 process-level completions behind each outcome. A research swarm, an epic's phases and land agent, and a pipe chain each become **one** "ready to verify".
2. **A definition of done up front makes agents better.** An agent that has written "what will be true when done" can judge its own claim against it. The claim step then becomes a self-check rather than a formality.
3. **A project-level inventory of intents.** Nothing in SASE answers "what am I currently trying to get done?":
   - The Agents tab shows processes.
   - Beads show scheduled work.
   - Plans show designs.
   - Goals would show intents.
4. **Continuity.** Follow-ups, rejections, and relaunches accumulate on one object instead of being scattered across agent rows.

**How it could fail, and how the design responds:**

| Failure mode | Why it's real | Response in this design |
| --- | --- | --- |
| **Verification fatigue.** You trade unread dots for about 30 "verify" requests a day. | Most root launches are questions. | Review card built for a 30-second judgment; required *Check it* steps; question goals settle when you read the answer (§6.6). |
| **Goal sprawl and rot** | About 25 ad-hoc goals/day; kept-open or crashed goals linger. | An **Idle** lane makes stalled goals visible; the agent's first step is to adopt an existing goal before creating one; `x` drops; aging badges. |
| **Mis-linking.** An agent adopts the wrong goal. | LLM similarity judgments are imperfect. | Adopting requires a written reason, shown in the goal timeline; `split` and `merge` repair it; all repairs are visible. |
| **Over-claiming** | Agents like to say "done". | The host decides eligibility, evidence must resolve, reject-with-feedback relaunches work, and claim-acceptance rate is tracked per model. |
| **Complexity.** It touches launch, finalizers, storage, TUI, and notifications. | Five subsystems. | Ship in phases behind a `goals` beta flag; keep the domain in `sase-core`. |
| **Token and latency tax** | Every turn is affected. | Turns already bound get one ~40-token line; draft turns pay one or two fast CLI calls. |

**Would I take a different approach?** I seriously considered **"claims without goals"**: a per-agent finalizer decision of "needs your attention: yes/no + evidence", with no goal object.

- **What it gets right:** some of the noise reduction, at about a fifth of the cost.
- **Where it fails:** exactly where the noise is worst. In multi-agent outcomes, a researcher cannot know the synthesis is done, and a phase worker cannot know the epic is done. It also gives you no inventory of intents.

So I keep Goals, but I sequence the claim and notification path early (§9).

---

## 3. What I'd keep and change from the prior research (`goal_outcomes_and_verification.md`)

**Keep:**
- Goals are distinct from beads, plans, and notifications.
- The host owns binding.
- A required goal finalizer runs *after* commit.
- An agent's close is a *claim* that enters review.
- Evidence is host-validated, and assertion text alone never counts.
- The domain lives in `sase-core`.
- Error and approval notification routes stay as they are.

**Your concern 1: user experience.** The prior report specifies rows and detail pages only briefly and puts the inventory inside an Artifacts pane. That answers "where is the data", not "how do I find what needs me and get to it in one keystroke". §6.5 designs this properly:
- a tab with a Review badge;
- lanes ordered by what you need to do;
- a card that puts your original ask next to the agent's claim;
- numbered jumps to every agent and artifact;
- launch-from-goal and reject-and-relaunch.

**Your concern 2: agents setting their own goals.** You read it correctly.
- **What the prior design does:** if no plan, bead, or parent goal applies, it "create[s] an ad-hoc goal from the submitted prompt", and it shows similar goals "as suggestions only".
- **Result:** the goal's text is a copy of your prompt, nobody writes a crisp outcome, and re-asking about the same thing creates duplicates unless *you* pick the goal.
- **This design:** the host guarantees a goal exists (a draft) and the *agent* writes it (`name`) or links it (`adopt`). You are never required to set a goal, though you can.

**Storage.** The prior report chose the **agents sidecar**. I would not:
1. Its sync converges because "owners mutate disjoint authority files" (`docs/agents_sidecar.md:208`). Goal state is shared and changed by several machines (created on athena, claimed on apollo, verified on the mac), which breaks that assumption.
2. It is a private, per-user repository. You asked for access for "any human/agent working on a sase project from any machine", which points at the project's shared work-state repo.
3. Prompts can stay private in the agents sidecar anyway: the goal stores only the agent ref and prompt digest (§6.4).

**TUI placement.** The prior report rejected a top-level tab because of navigation cost. I think the verification inbox justifies one tab, for three reasons:
- It needs a one-keystroke home and a count badge.
- Its layout is bespoke (lanes plus the review card), not a generic document pane.
- There is already a precedent for a live surface plus a history pane: Agents tab + Artifacts ▸ Agent.

---

## 4. Why not have agents check `SASE_PLAN` and call `/sase_new_goal`

**`SASE_PLAN` is commit plumbing, not a signal that a plan is attached:**
- It is removed on every spawn (`src/sase/agent/launch_spawn.py:86`).
- It is set only for plan-approval code successors (`axe/run_agent_exec_plan_accept.py:518-526`) and session attach (`agent/_agent_session_attach_launch.py:49`).
- It is read only by the commit flow (`workflows/commit/plan_hooks.py:165`, `commit_tracking_entries.py:87`).
- Epic phases deliberately avoid it. `bead/work_env.py:26-32` says the epic fields exist "without overloading `SASE_PLAN`".
- So the check would misclassify **839 of last week's turns** (phase and land agents) as having no plan, and they would each create a new goal.

**Checks run by the agent can't be enforced.** Every turn pays a tool call, including roughly 1,800 turns whose goal is already obvious. Nothing guarantees the agent actually runs the check.

**Parallelism breaks it.** Five researchers launched together would create five goals. Session successors would re-check on every turn.

**Children launched by agents can't inherit.**
- `parent_agent_name` is *read* in several places (`agents_sync/inventory_sources.py:277`, `launch_request_planning.py:317`), but no production code writes it into the child's `agent_meta.json`.
- The parent's context lives only in the LaunchApproval gate bundle.

**Keep the skill idea** as `/sase_goal`, but invoke it only when the host says the goal is still a draft.

---

## 5. Requirement adjustments (explicit)

| # | Your requirement | Adjusted to | Why |
| --- | --- | --- | --- |
| **R1** | Agents choose to "close" a goal, with evidence | Agents **claim** (goal → *Review*); **you** close it with *verify* | Your motivation is "notify me to verify", so the human verdict is the close. A per-project setting can let claims settle automatically if you ever want that. |
| **R2** | Agents without a plan check `SASE_PLAN` and create or link a goal | The **host binds** at launch (resolution ladder, §6.2); if nothing applies it creates a **draft**, and the agent **names** or **adopts** | The host has facts the agent lacks, the invariant is actually enforced, and there are no duplicates in swarms. |
| **R3** | Planner agents are exempt | Planners are bound too, to a draft that `sase plan propose` **names automatically from the plan's `title`/`goal`** | Zero effort for the planner, and the goal continues unchanged into coding, phases, and landing. |
| **R4** | "All sase agents MUST have a goal" | Every **LLM agent turn** is bound to exactly one *primary* goal. Non-LLM session members (monitor, gate, proc shells) inherit it and never decide. Routine runs bind to a per-routine **standing** goal. | Keeps the invariant without making shells or routines pretend to have outcomes. |
| **R5** | Plan goals serve as the agent's goal | The plan's `title`/`goal` *become* the Goal's `title`/`outcome`. The Goal object is created or named at **proposal**, not at approval. | The planner itself is bound, and one goal spans plan → code → epic → land. |
| **R6** | Evidence must be provided | Evidence is **refs the host can resolve and jump to**, plus required **Check it** steps, plus optional **gaps**. The host gathers commits, created artifacts, plan refs, and test receipts; the agent picks which matter. Tests are required only if the project opts in. | Evidence should be what you click to verify, and the agent can't fake it. A blanket test requirement would block answer and document goals. |
| **R7** | `O(n)` where n = active goals | n = **unsettled** goals: draft, running, idle, and review. Done and dropped goals cost nothing on the read path. Network bootstrap and history search are outside that guarantee. | Claimed goals must stay visible until you verify them. |
| **R8** | Every machine sees every active goal | **Local-first, sub-frame reads** with a visible **"synced N s ago"** indicator; pushes are synchronous and bounded, with an outbox when they fail. It is not globally instant. | Git cannot make an offline machine current. Stating freshness honestly is the reliable option. |
| **R9** | A Goals panel "somewhere" | A top-level **Goals** tab (live) plus **Artifacts ▸ Goal** (history) plus a goal chip, a GOAL lane, and a *by goal* grouping mode on the Agents tab | Discoverable inbox, one keystroke, same pattern as Agents vs Artifacts ▸ Agent. |
| **R10** | Goal completions replace completion notifications | Under the flag, *successful* agent completions go silent; **claims notify loudly**; goals that become **Idle** notify quietly; errors, questions, and approvals are unchanged | Otherwise you get both kinds of noise. Idle is a new, useful signal: "this intent stalled". |
| **R11** | Goals link to the original prompts | Store the origin agent ref plus the prompt **digest** (and the root prompt through lineage); each adoption adds another "also asked" prompt. Prompt *bodies* stay in the private agents sidecar. | Keeps the prompt association without publishing prompt text into a shared or public repo. Requires writing parent lineage, which is missing today. |

---

## 6. Design

### 6.1 Concept model

A **Goal** is the durable outcome behind one or more agent turns. It has:
- **Identity:** `id` (stable) and `project`.
- **Text:** `title` (≤ 60 chars) and `outcome` (what will be true when done).
- **Status.**
- **`origin`:** the agent that created it, that agent's submitted-prompt digest, the root human prompt digest (through lineage), time, and machine.
- **Optional links:** `plan` and `epic_bead`.
- **Derived data:** the **contributors** (agents bound to it), the **claims** history, and a **timeline**.

| Status | Meaning | Hot? | Lane / look |
| --- | --- | --- | --- |
| `draft` | Bound at launch, not yet named (machine-local only) | yes | `⌖` dim italic, "naming…" |
| `active` | Named; in progress or paused | yes | **Running** if any contributor is live, otherwise **Idle** (derived, not stored) |
| `review` | An agent claimed it done; waiting for you | yes | **Review** lane, amber, counted in the tab badge |
| `done` | You verified it | no | `✓` green, history |
| `dropped` | Canceled, merged, or superseded | no | dim, history |

```text
 launch ─► draft ──name / adopt──► active ◄──────── reject + feedback ────────┐
                                     │  ▲                                      │
                         claim + evidence  └── new work adopts (claim retracted)┤
                                     ▼                                         │
                                  review ──────────────────────────────────────┘
                                     │ verify (you)             drop / merge (you)
                                     ▼                             ▼
                                   done                         dropped
```

**Glyph.** `⌖` (U+2316) is unused in `src/sase` today. `◎` is already the bead **CLAIMED** status (`bead_status_presentation.py:44`), and `◉` is the Stitch pane icon (`_artifact_tab_model.py:66`), so both would collide. Status is conveyed by lane, label text, *and* color, never by color alone.

### 6.2 Binding: the host binds, the agent names

**Resolution ladder.** This runs at launch as a pure Rust function over launch facts; Python supplies the facts. The first match wins:

1. **Explicit.**
   - `%goal:<id>` binds to an existing goal. It can come from you, from the Goals tab's *launch onto goal* action, or from a parent agent.
   - `%goal:new` opts out of inheritance.
   - Add `goal` to `_KNOWN_DIRECTIVES` (`xprompt/_directive_types.py`). Tab-complete it over active goals in the prompt bar.
2. **Plan.**
   - A plan's code successor gets the plan's goal.
   - Epic phase and land agents go `SASE_EPIC_PLAN_REF`/epic bead → plan → goal.
   - The host stamps `goal_id` into the *archived* plan's frontmatter at proposal or approval, so later lookups are O(1).
3. **Session.** Pipe, questions, monitor and gate follow-ups, retries, and plan→code successors inherit the goal. `goal_id` is added to the list of metadata preserved across re-execution (`run_agent_directive_metadata.py`) and to the list successors inherit (`run_agent_helpers_artifacts.py:161-186`).
4. **Clan.** Every member of a clan launched together shares **one** goal.
5. **Parent.** Agents launched by an agent (`/sase_run`, `sase bead work` run by an agent) inherit the parent's goal. This requires actually writing `parent_agent_name` and a new `parent_goal_id` into the child's metadata. It is a prerequisite fix.
6. **Routine.** Chop runs bind to their routine's standing goal. A standing goal cannot be claimed and sits in a collapsed "Standing" group.
7. **Otherwise, a draft.** The host creates `draft` goal `⌖7k2mq` with the submitted prompt as its origin. Its display title is a prompt excerpt, with directives and xprompt refs stripped.

**Draft intake.** The host adds a short instruction only for turns bound to a draft, at `invoke_agent` right after `preprocess_prompt` (`llm_provider/_invoke.py:175-183`). That point is provider-neutral, runs on every turn, and leaves `submitted_xprompt.md` untouched.

```text
SASE GOAL: this turn is bound to draft goal ⌖7k2mq, created from your prompt.
Before other work run `sase goal list`. If an active goal already describes this
request, run `sase goal adopt 7k2mq -i <id> -w "<why it is the same outcome>"`.
Otherwise run `sase goal name 7k2mq -t "<title>" -o "<what will be true when done>"`.
```

That is about 80 tokens, plus `sase goal list` output at about 25 tokens per active goal. Turns that are already bound get a single ~40-token line instead: `SASE GOAL ⌖3fq9t — Tailnet dispatch mesh: <outcome>`. It costs almost nothing and helps the agent stay focused.

**Rules:**
- **Naming.** `name` is compare-and-swap: the first call wins. Clan siblings that call it later get `already named: "<title>"` and exit 0.
- **Adopting.**
  - The target must be unsettled.
  - Adopting a goal in `review` **retracts** its claim, because new work means it wasn't done; the timeline records this.
  - Settled targets are refused. Launch with `%goal:new` instead; the new goal gets a `supersedes`/follow-up link to the old one.
- **Allowed goal commands for agents:** `list`, `show`, `name`, `adopt`. Agents cannot create goals that aren't their own, which prevents goal spam. Discovered follow-up work stays as task beads, as today.
- **Planners.**
  - Plan-mode launches skip the intake instruction.
  - `sase plan propose` names the draft from the plan's `title`/`goal` on the host.
  - A rejected plan leaves the goal *Idle*, with the rejection recorded as feedback.
- **Fallback.** For drafts, the goal finalizer's template *requires* `name`. If a run dies still unnamed, the host names it from the excerpt and marks it `auto-named`.
- **Drafts stay machine-local until named.** An adopted draft never reaches the shared ledger, and neither does the excerpt of your prompt.

### 6.3 The goal finalizer (`builtin@goal`)

**Configuration:**
- Required: add it to `finalizers.required`. Today that list is `[]` (`default_config.yml:1749-1758`).
- Trigger: `always`.
- Order: `after: [commit]`.
- It follows the `bead_action` pattern: a closed enum plus a host policy function (`bead_action/policy.rs:61-107` → a new `decide_goal_action`).

**Context the host issues:**
- goal id, revision, status, title, and outcome;
- `can_claim`, plus the reasons if false;
- **evidence candidates the host gathered:** `@commit` (resolved after commit), `file:` artifacts created this turn, the plan ref, a covering `check` receipt on the final tree, and `@reply` (the reply snapshot);
- `draft: true|false`.

**Payload** (agent-authored):

```json
{
  "decision": "claim",
  "claim": "Active goals list in <50 ms on athena and apollo from a fresh shell.",
  "evidence": [
    {"ref": "@commit", "why": "adds the ledger reader and `sase goal list`"},
    {"ref": "file:explicit:0123…", "why": "latency measurements for 10/100/1000 settled goals"}
  ],
  "check": [
    "On apollo run `time sase goal list`; expect < 50 ms.",
    "Open the Goals tab; this goal is in Review with 3 evidence chips."
  ],
  "gaps": ["Not measured with more than 200 active goals."]
}
```

or `{"decision": "keep_open", "progress": "Phase 2 landed; phase 3 blocked on the sase-core release."}`.

**When a claim is allowed.** The host checks at submit and again at execute:
- No *other* contributor is live (running, queued, or waiting). The last agent standing claims, which is how a swarm's lead synthesizer ends up being the one that claims.
- For epic-bound goals: all phase beads are closed, or this is the land agent.
- `@commit` evidence requires that the commit finalizer actually succeeded and was not deferred.
- The revision matches; otherwise the result is `stale_final_context`, as in the existing flow.
- If `can_claim` is false, the template offers only `keep_open`.

**What evidence should be.** You asked me to think hard about this. Six principles:

1. **Navigable.** Evidence is what you will *click* to verify, so it must be artifact refs. Prose (claim, check, gaps) only frames the refs.
2. **Unforgeable.** Every ref must resolve at submit, and the host checks provenance:
   - a stitch must be authored by a contributor;
   - a file must have been created by a contributor;
   - a plan must be bound to this goal.
   Test results come only from host **receipts**. An agent-written "tests passed" is never evidence (see `receipts-prove-before-they-skip`).
3. **Proportional.** The minimum depends on the kind of claim (table below).
4. **Actionable.** At least one `check` step is required. It is the most valuable part of the notification, because it turns "done!" into a two-minute task.
5. **Honest.** `gaps` gives the agent a sanctioned place to admit limits; they render in amber.
6. **Gathered by the host.** The agent picks from candidates rather than building evidence up, which cuts both token cost and fabrication risk.

| Claim shape | Minimum evidence | Host adds / checks |
| --- | --- | --- |
| Answer / review | `@reply` (host snapshots the reply as an artifact) | digest, bound to the closing turn |
| Research / document | the `research:`/`plan:`/`file:` ref | produced or last updated by a contributor |
| Plan only | `plan:` ref | proposal/approval state; no duplicate PlanApproval alert |
| Code / config | `@commit`, or a stitch/Patch by contributors | covering-receipt verdict, or an **untested** badge |
| Operational (deploy, machine fix) | a `file:` log/output artifact, or a receipt | — |

Every claim needs at least one resolvable ref, at least one check step, and a claim of 280 characters or fewer.

The review card shows an **evidence strength** badge, strongest first: `tested` (covering receipt on the final tree) › `committed` › `documented` › `answered`.

**Deliberately not required:**
- **Universal test receipts.** They would block answers and documents, and would push agents to game results or never claim.
  - Projects can opt in with `goals.require_receipt_for_code: true`.
- **An LLM verifier pass before you're notified.** It doubles cost; keep it as a later per-project policy.

**What execution does:**
- **Claim:**
  1. Append a `claimed` event (claim id, evidence refs and digests, strength) and publish it.
  2. Then emit **one** notification, deduplicated on `goal:<id>:claim:<n>`.
- **`keep_open`:** append a `progress` event, with no notification. The exception is when no contributor remains live: the goal is now **Idle** and you get a quiet notice.

**Handoffs:**
- Plan, monitor, pipe, and questions handoffs make no decision; the successor inherits the goal.
- A prepared monitor completion carries the decision in its manifest: on green it claims; on red it becomes `keep_open` with the monitor failure as its progress note.
- The single declaration-recovery turn also asks for the goal payload.
- A crash or kill makes no decision, so the goal becomes Idle and the existing error notification gains a goal chip.

**Skill change.** `sase_final` gains one paragraph: *"Claim only if the goal's outcome is true now and you can point at evidence; otherwise keep it open with a one-line progress note."*

### 6.4 Storage: the goal ledger

**Layout.** It lives in the project's beads sidecar repo, as a sibling of the bead store:

```text
goals/
  STORE.json                          schema fence
  live/<id>                           existence marker — one per UNSETTLED goal (the hot index)
  items/<id>/events/<ulid>.json       immutable events — the only source of truth
```

**The invariant: nothing is ever edited in place.**
- Writers only add event files with unique names, and add or delete markers.
- So a git rebase cannot hit a content conflict.
- The only possible conflict is a marker race (for example reopen vs. verify). The sync step resolves it by reducing that one goal's events: a marker exists exactly when the goal's reduced status is unsettled.
- There is no committed derived state to regenerate, which is simpler than the bead store's semantic stream merge.

**Read path (O(n_active)):**
- `sase goal list` reads `goals/live/`, giving n markers, then reduces `items/<id>/events/` for each one.
  - Cost is O(n × e), where e is events per goal (typically 5–30).
  - Settled goals' directories are never opened.
- A machine-local projection `~/.sase/projects/<key>/goals-hot.json`, keyed by directory signatures, makes a warm read one file plus n stats. The TUI refreshes it off the event loop.
- A Rust fast path, like `bead_fast_path`, skips Python parser startup.
- Targets, to be measured rather than asserted:
  - `sase goal list` p50 < 30 ms end to end;
  - TUI refresh < 2 ms at n = 100;
  - both flat as settled history grows 10×.
- `sase goal show <id>` for a settled goal is O(1) by path.
- History search (Artifacts ▸ Goal) builds a lazy index off the event loop and is explicitly outside the O(n) contract.

**Write path:**
- A Rust `sase_core::goal` module validates each transition against the reduced state and the event's `basis`.
- It writes into the **host-owned hidden clone** (`~/.sase/projects/<key>/repos/beads`), per `machine-link-writes-off-primary`.
- It commits `chore(goals): …` and pushes, with a time limit.
- On non-fast-forward: fetch, rebase (conflict-free), re-validate the basis, push again, with bounded retries.
- On failure: queue in the outbox, show a **`↑ unpublished`** chip, and let the auto-sync job retry.
- The local user sees the change immediately. Other machines see it on their next pull: the 30 s `sidecar_auto_sync` tick with publisher hints, plus a TTL-gated background fetch triggered by `sase goal list`. `sase goal list --fresh` does a synchronous fetch.

**Concurrency semantics.** Every event records the event it was computed from (its `basis`).
- Two claims on the same basis: the first by ULID wins, and the second is recorded as superseded.
- A drop that races a claim: the drop wins, because it is your intent.
- An adopt that races a verify: the adopt is recorded as a late attachment with a diagnostic, and the goal stays done.
- Conflicts always resolve toward the human's decision and are always shown, never silent.

**IDs.** Five random Crockford base32 characters (`7k2mq`), checked for uniqueness against `live/` and `items/`. The ref is `goal:7k2mq`.

**Privacy.**
- The ledger holds titles, outcomes, claims, and refs — the same class of data as plan titles and bead notes already in that repo.
- The origin prompt is stored only as an **agent ref plus digest**. The body stays in the private agents sidecar.
- Naming a goal adds a new trigger that publishes the creating agent's prompt into the agents sidecar. Today the prompt is published mainly on commit or plan approval (`docs/agents_sidecar.md`), so a question-only agent's prompt would otherwise never leave the machine.
- Projects without a beads sidecar use the same ledger format in a machine-local git repo (`~/.sase/projects/<key>/goals/`), labeled *local-only*. The invariant still holds everywhere.

**Why not the other options:**

| Option | Verdict |
| --- | --- |
| Goals as **beads** | Reads are O(total). Bead reads replay every stream (`bead/read.rs:66-86`), and the store has 6,451 issues, 5,993 of them closed. Bead scheduling and close semantics are also the wrong fit. Link goals to beads instead. |
| **Agents sidecar** | Breaks its disjoint-owner convergence model, and it is per-user rather than per-project (§3). |
| **Plans sidecar** | Would work, but it is a month-sharded document corpus with human-owned checkouts. Goals are lifecycle state, like beads. |
| **New `goals` sidecar role** | Clean, but needs a new repository per project, plus clone, sync, and authorization setup. The ledger format doesn't care where it lives, so promote it later if its privacy needs to differ from beads. |
| **SQLite** | Excellent as a local read model, but it has no git sync. It is an option for the machine-local projection only. |

### 6.5 The TUI

**Tab bar.** `Agents   Goals ⌖2   Artifacts   Services`.
- Goals sits *after* Agents, because goal↔agent is the most common jump.
- The badge counts goals in **Review** and is hidden at 0.
- Touch points: `TAB_ORDER` (`tab_order.py:31`) and `tab_bar.py` labels.
- New keys go into `default_config.yml`, per the gotchas note.

**The Goals tab:**

```text
╭─ Goals · sase ──────── ⌖2 review · 3 running · 1 idle ──╮╭─ ⌖ Goals feature research report ─────────────── REVIEW ─╮
│ REVIEW ─────────────────────────────────────────────── ││ ⌖7k2mq · sase · opened 2h ago · claimed 3m ago          │
│ ▸⌖ Goals feature research report       3m   ✓✓✓✓●      ││                                                          │
│  ⌖ Fix flaky bead sync test           41m   ✓          ││ YOU ASKED   "I want to add a new "Goals" functionality   │
│ RUNNING ────────────────────────────────────────────── ││             to sase. Goals should be associated with…"   │
│  ⌖ Tailnet dispatch mesh · epic        2h   ✓✓●○       ││             p full prompt · +1 more ask                  │
│  ⌖ Deck paging polish                  8m   ●          ││ OUTCOME     A recommended, critiqued design for Goals.   │
│  ⌖ Answer: why is apollo sync slow?    1m   ●          ││ CLAIM       research.2r.lead · 3m ago · documented       │
│ IDLE ───────────────────────────────────────────────── ││             The synthesis recommends host-bound goals…   │
│  ⌖ Apollo memory pressure              1d   ✗          ││ CHECK IT    1  Read §11 "Recommended solution".          │
│    "OOM repro still unclear"                           ││             2  Confirm the ledger home fits apollo.      │
│                                                        ││ EVIDENCE    [1] ▤ research:202609/goals/goals.md         │
│                                                        ││             [2] ▤ research:202609/…/goals__cld.md        │
│                                                        ││ GAPS        ⚠ No prototype; latencies are targets.       │
│                                                        ││ AGENTS      [3] ✓ .cld  [4] ✓ .cdx  [5] ✓ .grk  [6] ● .lead │
│ synced 12s ago                                         ││ TIMELINE    created · named · 4 progress · claimed       │
╰────────────────────────────────────────────────────────╯╰─ v verify  r reject  l launch  x drop  $ follow  p prompt ─╯
```

**Layout choices:**
- **Lanes are ordered by what you should do:**
  - **Review** — verify it.
  - **Running** — just watch.
  - **Idle** — decide whether to relaunch or drop.
- **Row anatomy:** `⌖` + title + age + **contributor pips**, where `●` means running, `○` waiting, `✓` done, and `✗` failed. At most five pips, then `+n`. Idle rows show their last progress note.
- **The card is built for a 30-second judgment.**
  - It reads *You asked → Outcome → Claim → Check it → Evidence → Gaps*, which is the comparison you actually make.
  - Every agent and ref is a numbered chip, reusing the link rail: `1-9` / `$` follow it.
  - Agent chips go through `_follow_loaded_agent` → `reveal_agent_navigation_target`, so a jump opens collapsed folds. If the Agents filter hides the agent, it falls back to Artifacts ▸ Agent.
  - The YOU ASKED prompt text comes from the agents sidecar prompt archive, through the origin agent ref and digest.

**Keys:**

| Key | Action |
| --- | --- |
| `v` | Verify: close as done, with an optional note |
| `r` | Reject: feedback prompt, then an optional *Relaunch with feedback* that pre-fills `%goal:<id>` + your note + `@goal:<id>` |
| `l` | Launch an agent onto this goal (prompt bar pre-filled with `%goal:<id>`) |
| `x` | Drop |
| `e` | Edit title/outcome |
| `m` | Merge into another goal |
| `a` | Jump to the newest live contributor on the Agents tab |
| `p` | Open the origin prompt in the pager |
| `n` | New goal (optional; you never *have* to) |
| `/` | Filter |
| `P` | All projects |
| `h` | Toggle a collapsed "done in the last 24 h" lane |

**Empty state:** *"No active goals. Every agent you launch gets one automatically — press `n` to set one yourself."*

**Agents tab integration:**
- An identity-header chip `⌖ <title>`, colored by status, with one key to open that goal on the Goals tab.
- A **GOAL** lane in the Context card, above the existing PLAN lane (`prompt_panel/_agent_display_header.py`). It shows title, status, outcome, and *this* turn's decision (claimed, or kept open with its progress note).
- A new **by goal** grouping mode in the `o` picker (`GroupingMode` in `agent_groups/_buckets.py`). Banners are goal titles, ordered Review → Running → Idle.
- With the flag on, the ✅ unread marker for successful completions is retired in favor of goal-level signals. ❌ failures stay exactly as they are.

**Artifacts ▸ Goal:**
- A history and search pane covering all goals, settled included.
- It uses the same card renderer as the Goals tab.
- It mirrors Artifacts ▸ Agent.

**Link graph:**
- **New kind.** `goal:` becomes a built-in artifact kind: a Rust catalog entry plus a resolver.
- **New relations** (sase-core registry):
  - `pursues`/`pursued-by` (agent → goal), projected from the agent metadata's `goal_id`.
  - `evidences`/`evidenced-by` (ref → goal), projected from claim events.
- **Reused relations:**
  - `implements` for plan/bead → goal.
  - `supersedes` for merges and follow-up goals.
- These are projections (like the existing agent→bead rule in `artifact_links/projection/_entry.py`), so no link-event writes happen per agent.
- **Citing vs binding.** `@goal:<id>` in a prompt *cites* a goal (it expands to the goal's card text). `%goal:<id>` *binds* the agent to it.

**Prerequisite fix.** `handle_jump_to_agent` does a linear scan of `app._agents` and never reveals collapsed rows (`actions/agents/_notification_handlers.py:17-50`). Goal jumps must use the reveal path, and fixing JumpToAgent the same way is cheap.

### 6.6 Attention and notifications

| Event | Today | With Goals (flag on) |
| --- | --- | --- |
| Agent turn succeeds | `JumpToAgent` tagged `done` → ✅ unread + chime (`run_agent_runner_finalize.py:469`) | Silent; stays visible in history |
| **Agent claims a goal** | — | **`JumpToGoal`**, tag `review`, loud. Notes carry the claim and Check-it steps; deduplicated per claim |
| Goal becomes Idle | — | Quiet `idle` notice with the last progress note |
| Agent fails | `ViewErrorReport` ❌ | Unchanged, plus a goal chip; the goal becomes Idle |
| Plan proposed | PlanApproval | Unchanged; a plan-only goal's claim is suppressed as a duplicate |
| Questions, gates, sudo | unchanged | unchanged |

- **Question goals.** For claims whose only evidence is `@reply`, a config field `goals.answer_claims: ack | verify` defaults to `ack`: reading or dismissing the notification settles the goal as done. You "verify" an answer by reading it, and this keeps roughly 25 questions a day from becoming a verification chore.
- **Across machines.** `RemoteAttention` deduplicates on goal id plus claim id.
- **Telegram.** A follow-up in `sase-telegram` can add inline **✓ Verify / ✗ Reject** buttons, which makes verifying from your phone a single tap.

### 6.7 CLI (`sase goal`, bare → `list`; options alphabetical, every long option with a short alias)

```text
sase goal adopt ID -i/--into GOAL -w/--why TEXT      # agent: merge my draft into an active goal
sase goal doctor [-r/--repair]                       # rebuild markers from events (never on the hot path)
sase goal drop ID -w/--why TEXT                      # human
sase goal list [-a/--all-projects] [-f/--fresh] [-j/--json] [-s/--status S]
sase goal merge ID -i/--into GOAL                    # human
sase goal name ID -o/--outcome TEXT -t/--title TEXT  # agent: name my draft (compare-and-swap)
sase goal new -o/--outcome TEXT -t/--title TEXT      # human (agents: refused)
sase goal reject ID -m/--message TEXT [-l/--launch]  # human; -l relaunches with feedback
sase goal reopen ID -m/--message TEXT                # human
sase goal show ID [-j/--json]
sase goal verify ID [-m/--message TEXT]              # human
```

The status-changing verbs (`verify`, `reject`, `drop`, `reopen`, `merge`) are refused inside an agent run, mirroring the bead rule that agents never hand-edit status. Claims happen only through the finalizer.

Agent-facing `list` output is one compact line per goal:
`⌖ 7k2mq  review   Goals feature research report   5 agents · 3m`

### 6.8 The Rust / Python boundary

**`sase-core`:**
- goal wire and domain types;
- IDs, event schema, and reducer;
- transition, eligibility, and evidence validation (`decide_goal_action`);
- ledger I/O and the hot index;
- fast-path `list`/`show`;
- binding resolution, as a pure function over launch facts;
- the finalizer obligation and payload wire;
- the `goal` ref kind, relations, and projection rules.

**`sase` (Python):**
- launch orchestration and prompt injection;
- the `sase plan propose` hook;
- finalizer glue;
- notifications;
- the TUI;
- skill text.

Each binding sase calls needs the `sase-core-revision.txt` pin moved forward.

---

## 7. Alternatives considered

| Alternative | Why it loses |
| --- | --- |
| Agent checks `SASE_PLAN` → `/sase_new_goal` | Misclassifies epic agents, can't be enforced, duplicates goals in swarms (§4). |
| Host-only ad-hoc goals from the prompt (prior research) | Titles are copies of the prompt, there is no outcome statement, and duplicates arise when you re-ask. |
| A host-side small-model "goal namer" at launch | Puts an LLM dependency and 1–2 s into the deterministic launch path; the agent already has the context to name its goal for free. Revisit only if agents name goals badly. |
| Claims without Goals (per-agent attention flag) | Cheap, but fails on multi-agent outcomes and gives no inventory (§2). |
| Goals as beads | O(total) reads and scheduling semantics that don't fit (§6.4). |
| Goals pane inside Artifacts only | Wrong home for a daily inbox; no badge; buried among five-plus panes. Kept as the *history* pane. |
| Goals as a nav section on the Agents tab | Crowds the densest tab and competes with agent selection for the detail area. The *by goal* grouping mode gives the useful half of it. |

## 8. Risks and mitigations

- **Mis-adoption.**
  - The reason is required and shown in the timeline.
  - `merge` and `split` repair mistakes.
  - Track "merges per 100 goals" as a quality metric.
- **Claims left in Review indefinitely.**
  - They stay hot until you act on them.
  - Show aging badges.
  - Consider `goals.review_lapse_days` → a distinct `lapsed` settled state, never an automatic *verify*.
- **Sync lag misleads you.** "Synced N s ago" is always visible, the `↑ unpublished` chip shows pending pushes, and `--fresh` forces a fetch.
- **The beads repo is public for managed projects.** Goal titles become as public as plan titles; prompts do not. See open question 3.
- **Standing goals clutter the board.** Collapse them into one group and exclude them from counts.
- **Dependence on missing lineage.** Parent-to-child goal inheritance needs `parent_agent_name`/`parent_goal_id` to be written. This is scheduled as phase 0.

## 9. Rollout

Create the flag with `sase flag new goals` as epic scaffolding: it is removed before the epic lands.

| Phase | Deliverable | User-visible? |
| --- | --- | --- |
| **P0** | Prerequisites: write parent lineage into child metadata; reveal-path jump for JumpToAgent; a prompt-publication trigger | no |
| **P1** | `sase-core` ledger, reducer, and fast CLI; binding ladder, drafts, and injection; the `/sase_goal` skill; `goal_id` in metadata; plan-propose naming | CLI only |
| **P2** | `builtin@goal` (required, after commit), `sase_final` update, prepared-monitor support, `JumpToGoal` | notifications |
| **P3** | Goals tab, Agents chip/lane/grouping, Artifacts ▸ Goal, `goal:` kind and relations | yes |
| **P4** | Attention cutover (silence successful completions), answer-ack, Idle notices; soak; remove the flag | yes |

**Metrics:**
- claims per day;
- verify, reject, and lapse rates per model;
- median time-to-verify;
- adopt vs. name ratio;
- merges per 100 goals;
- Idle-goal age;
- notification volume before vs. after;
- `sase goal list` p50/p95 as settled history grows (should stay flat).

**Acceptance tests:**
- Every new LLM turn has a `goal_id`.
- A 5-member swarm yields exactly one goal.
- Epic phases can never claim; only the land agent can.
- A claim is refused while other contributors are live.
- `@commit` is refused when the commit was deferred.
- An adopted draft never appears in the shared ledger.
- Concurrent events from two clones rebase without conflict.
- A marker race resolves by reduction.
- List latency stays flat as settled goals grow 10×.
- One claim produces exactly one notification across retries and machines.

## 10. Open questions for you

1. Should question-type claims settle when you read them (`ack`, my default) or require an explicit `v`?
2. Is the Goals tab in second position right, and do you want a direct key for it?
3. Are you comfortable with goal titles, outcomes, and claims living in the beads repo, which is public for managed GitHub projects? The alternative is a `goals.visibility: private` switch that keeps the ledger local-only or in a private repo.
4. Should routine runs have standing goals (my recommendation), or be the one documented exemption?
5. For work spanning several repos (sase plus sase-core), the goal lives in the *launching* project. Is that acceptable?
6. Should claims left unreviewed lapse after N days?

## 11. Recommended solution

1. **Model.** Build **Goals** as a first-class, Rust-owned `goal:` artifact with a lifecycle of draft → active (Running/Idle) → review → done/dropped.
2. **Binding.** At launch, the **host binds every LLM turn to exactly one goal**, using plan, session, clan, parent, or routine facts, or an explicit `%goal`.
   - Where nothing applies, it creates a machine-local **draft**. The agent's first act is to **name** it or **adopt** an existing active goal.
   - Planners get their draft named automatically from the plan's `title`/`goal`.
   - Users never have to write a goal, and can always choose one.
3. **Finalizer.** A required **`builtin@goal`** finalizer, ordered after commit, makes every normal turn choose `keep_open` (with a progress note) or `claim`.
   - A claim is accepted only when the agent is the last live contributor (and, for epics, the land agent).
   - It must carry **refs the host can resolve** (drawn mostly from candidates the host gathered: `@commit`, created artifacts, plan, receipts, `@reply`), **Check it** steps, and any **gaps**.
   - A claim moves the goal to **Review** and sends one notification. **You close it** with verify, or reject it (optionally relaunching with your feedback).
4. **Storage.** Goals live in a **goal ledger** that cannot conflict: immutable events plus `live/` markers, in the project's beads sidecar repo, written through the hidden host-owned clone.
   - Reads are **O(n_active)**, with a machine-local projection, a Rust fast path, and visible freshness.
   - Origin prompts are linked by agent ref and digest and kept private.
5. **Surfaces.** A **Goals tab** (Review · Running · Idle; *You asked → Claim → Check it → Evidence* cards; numbered jumps to every agent and artifact; `v`/`r`/`l`/`x`), plus Agents-tab goal chips, a GOAL lane, and *by goal* grouping, plus **Artifacts ▸ Goal** for history.
6. **Attention.** Successful agent completions go quiet; **goal claims are the loud signal**; Idle goals notify softly; errors and approvals are unchanged.
7. **Delivery.** Ship in five phases behind a `goals` beta flag, with lineage and jump fixes first, and measure claim quality and notification volume before removing the flag.
