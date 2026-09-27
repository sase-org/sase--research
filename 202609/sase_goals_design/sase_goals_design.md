# SASE Goals: outcomes the host guarantees, agents name, and you verify from one inbox

_Lead synthesis · 2026-09-27 · project: sase_

**Sources.** Five independent reports — [cdx](sase_goals_design__cdx.md),
[cld](sase_goals_design__cld.md), [grk](sase_goals_design__grk.md),
[mus](sase_goals_design__mus.md), [gem](sase_goals_design__gem.md) — plus the prior
synthesis
[goal_outcomes_and_verification](../goal_outcomes_and_verification/goal_outcomes_and_verification.md),
all read through `sase artifact read`. I also checked the contested facts myself against
`sase` @ `a5e2a34dab`, the local agent-run history on athena, and GitHub repository
metadata. Where a report was wrong, §3 says so.

---

## 0. Bottom line

**Build Goals.** All six reports (the five new ones and the prior synthesis) agree, and so
do I. Today the thing that grabs your attention is a _process_: "agent X stopped." The
thing you actually check is an _outcome_. I re-counted athena's sase runs:
**2,048 `agent_meta.json` files in the last 7 days** (404 in the last 24 h), and 841 of
them were bound to an epic bead. cld's classification of the same week gives about
**310 distinct outcomes, or ~6.6 agent turns per outcome**. Today almost every one of
those turns can light an unread dot. Goals would reduce that to about one "ready to
verify" signal per outcome.

I keep the destination you described. I change **five mechanisms**, all called out in
§2.2:

1. **The host guarantees the goal, and the agent writes it.** At launch, the host binds
   every LLM turn to a goal from facts it already has (plan, session, clan, parent,
   routine, or an explicit `%goal`). When none of those apply, it creates a **draft**
   goal, and the agent's first act is to **name** that draft or **adopt** an existing
   active goal. You never have to write a goal, and agents do set their own. The
   `SASE_PLAN` check and a mandatory `/sase_new_goal` skill are not used.
2. **Agents claim; you close.** A required `builtin@goal` finalizer makes every normal
   turn choose `keep_open` or `claim`. A claim needs three things:
   - **resolvable, clickable evidence refs**, mostly gathered by the host;
   - 1–3 **"check it" steps** for you;
   - any **gaps** the agent admits.

   The claim moves the goal to **Review** and opens one verification gate. Your
   **Verify / Reject / Drop** settles it.
3. **Goals get a top-level tab.** `Agents | Goals ⌖2 | Artifacts | Services`. Its lanes
   are **Review → Running → Idle**, and every agent and artifact on a goal is a numbered
   jump. Every agent in the Agents tab shows a goal chip. The FINAL deck gets a Goal
   card.
4. **Claims replace success pings.** A successful agent completion goes quiet. A goal
   claim is the loud signal. Errors, questions, and approvals stay unchanged.
5. **"O(n) active goals" becomes O(n _unsettled_) with honest freshness.**
   - **Storage:** goals live in a conflict-free, append-only ledger in their own `goals`
     sidecar role, initially co-hosted in the beads repository.
   - **Reads:** local and fast. Settled goals are never opened.
   - **Freshness:** a visible "synced 12 s ago" indicator, rather than a promise that
     every machine sees every change instantly.

---

## 1. Is this a good idea?

**Yes.** In order of value:

1. **Attention matches what you verify.** A research swarm, an epic's planner, phases
   and lander, or a pipe chain each becomes **one** claim instead of 5–20 completions.
2. **A definition of done up front makes agents better.** An agent that wrote down
   "what will be true when done" can judge its own claim against it.
3. **A project-level inventory of intent.** Nothing in SASE answers "what am I trying to
   get done right now?" today:
   - Agents shows processes.
   - Beads shows scheduled work.
   - Plans shows designs.

   Goals would show intent.
4. **Continuity.** Follow-ups, rejections, and relaunches accumulate on one object
   instead of scattering across agent rows.

**Would I take a different approach?** The only serious alternative is cld's
**"claims without goals"**: a per-agent finalizer flag saying "needs your attention:
yes/no + evidence", with no Goal object.
- **What it gets right:** about a fifth of the cost, and some of the noise reduction.
- **Where it fails:** exactly where the noise is worst. A researcher can't know the
  synthesis is done, and a phase worker can't know the epic is done. It also gives you
  no inventory.

So I keep Goals, but I sequence the rollout so the attention payoff arrives early (§5).

**How it could fail, and what answers it:**

| Failure mode | Why it's real | Design response |
| --- | --- | --- |
| **Verification fatigue** | Roughly 30 new user-level outcomes/day, and most root launches are questions | 30-second review card; required *check it* steps; answer-only claims settle on acknowledgement (§4.6) |
| **Goal sprawl and rot** | About 25 ad-hoc goals/day; kept-open or crashed goals linger | Inheritance by default; adopt-before-name; an **Idle** lane; aging badges; `x` drop; unnamed drafts never publish |
| **Mis-linking** | LLM "same outcome?" judgments are imperfect | Adoption needs a written reason shown in the timeline; no silent fuzzy joins; `merge` / `split` repair |
| **Over-claiming** | Agents like to say "done" | Host-computed eligibility; evidence must resolve; claims are not settlements; accept/reject rate tracked per model |
| **Goalpost shifting** | An agent can rewrite the goal to match what it did | The origin prompt is immutable, and the review card shows *You asked* next to *Claim*; criteria written by user or plan cannot be removed by an agent |
| **Complexity** | Touches launch, finalizers, storage, TUI, and notifications | Domain in `sase-core`; phased behind a `goals` flag; lineage and jump fixes first |
| **Token and latency tax** | Every turn is affected | Already-bound turns get a ~40-token line; draft turns pay ~80 tokens plus one fast CLI call |

---

## 2. Critique of the proposal

### 2.1 Why not "check `SASE_PLAN`, else run `/sase_new_goal`"

Every report rejects this, and the code agrees:

- **`SASE_PLAN` is commit plumbing, not a "has a plan" signal.**
  - `launch_spawn.py:86` pops it on every spawn.
  - It is set again only for plan-approval code successors and session attach.
  - Epic phase and land agents deliberately avoid it (`bead/work_env.py`).
  - So the check would misclassify about **840 epic turns per week** as plan-less, and
    each of them would create a new goal.
- **An invariant can't depend on the model.** Skills can be skipped, fail, or be missing
  from a runtime. Nothing guarantees the check runs. Every turn would pay a tool call,
  including the ~90% whose goal is already obvious.
- **Parallel agents break it.** Five researchers launched together would create five
  goals.
- **Lineage is missing.** `parent_agent_name` is *read* in several places
  (`launch_request_planning.py`, `agents_sync/inventory_sources.py`, the list builders),
  but no production path writes it into a child's `agent_meta.json`. The requester is
  known only inside the LaunchApproval bundle.

**Keep the skill idea** as `/sase_goal`, used when the host says "your goal is still a
draft." The host still enforces the invariant.

### 2.2 Explicit requirement adjustments

| # | Your requirement | Adjusted to | Why |
| --- | --- | --- | --- |
| **R1** | Agents decide to close a goal and provide evidence | Agents **claim** (goal → *Review*); **you** settle it (*Verify / Reject / Drop*). Answer-only claims settle when you open the answer (§4.6). | Your stated motivation is "tell me what to verify," so your verdict is the close. |
| **R2** | Agents without a plan check `SASE_PLAN` and create or link a goal | The **host binds** at launch through a resolution ladder (§4.2). If nothing applies, it creates a **draft**, and the agent **names** it or **adopts** an active goal. | The host has facts the agent lacks. The invariant is actually enforced, and swarms don't create duplicates. |
| **R3** | Planner agents are exempt | Planners are bound too. `sase plan propose` names or refines their goal from the plan's `title`/`goal`. PlanApproval is the decision point for plan-only requests. | No special case, and one goal spans plan → code → phases → land. |
| **R4** | "All sase agents MUST have a goal" | Every **LLM agent turn** has exactly one *primary* goal. Mechanical members (monitor, gate, `%proc`) inherit it and never decide. Hidden helpers inherit their parent's goal. Routine (chop) runs bind to a per-routine **standing** goal that can't be claimed. | Keeps the invariant without making shells or routines fake outcomes. |
| **R5** | The plan's `goal` is the agent's goal | Yes, through a stable `goal_id` the host stamps into the archived plan at proposal. The plan's `goal` text becomes the Goal's *outcome*. | Text matching is fragile. An id makes later lookups O(1). |
| **R6** | Evidence is provided on close | Typed **resolvable refs** (mostly gathered by the host) plus **check-it steps** plus **gaps**. Test receipts are required only by project policy. | You click evidence to verify, and the agent can't forge it. A blanket test rule blocks answer and document goals. |
| **R7** | `O(n)`, n = active goals | n = **unsettled** goals: draft, active, and review. Settled goals are never opened on the read path. Bootstrap and history search are outside the contract. | Claimed-but-unverified goals *are* your inbox, so they must stay hot. |
| **R8** | Every human and agent on every machine sees active goals | Local-first reads with a visible **sync watermark**. Claims and settlements push synchronously, with an outbox when a push fails. Not globally instant. | Git can't make an offline machine current. Honest freshness is the reliable promise. |
| **R9** | A Goals panel "somewhere" | A top-level **Goals** tab, a Goals inbox tab (so the top-bar `inbox:` chip shows `⌖N`), and on the Agents tab a goal chip, a FINAL-deck Goal card, and a *by goal* grouping mode. | One keystroke, a badge, and jumps in both directions. |
| **R10** | Done goals notify you instead of agent completions | Behind the flag: successful completions go **silent**, claims notify **loudly**, goals going Idle notify **quietly**, and errors, questions, and approvals are unchanged. | Otherwise you'd get both kinds of noise. |
| **R11** | Goals link to the original prompts | The origin is the creating agent's ref plus its **submitted-prompt digest** and, for fan-outs, the root prompt digest. Each adoption adds an "also asked" entry. Prompt *bodies* stay in the agents sidecar prompt archive. | Keeps the association without copying prompt text into every row. |
| **R12** *(new)* | — | **Your follow-ups are goal events.** A follow-up prompt to an agent whose goal is in Review retracts the claim, with your prompt recorded as the feedback. A follow-up after the goal is Done starts a new goal linked to the old one with `follows`. | This is how you already work. "Reply to the agent" becomes "reject with feedback" for free. |

---

## 3. Where the reports disagreed, and how I resolved each

| Question | Positions | Resolution | Reasoning and evidence |
| --- | --- | --- | --- |
| **Who writes the goal's text?** | The host summarizes the prompt (grk, mus, gem); the host creates a provisional goal that the agent confirms at the finalizer (cdx); the host creates a draft that the agent names at the start of the turn (cld) | **cld's draft → name/adopt**, with a finalizer fallback and host auto-naming as the last resort | This directly answers your worry that agents can't set their own goals. The Running lane shows a real title while the agent works. Adoption happens *before* evidence exists. There is no LLM call in the launch path. |
| **Storage home** | Agents sidecar (cdx, mus, gem, prior); beads repo (cld); a new goals sidecar (grk) | A new **`goals` sidecar role**, co-hosted initially in the beads repository under `goals/` and splittable later | See the next four points. |
| ↳ agents sidecar | — | Rejected as the canonical store | It is project-scoped and multi-owner. cld's "per-user" claim is wrong. But it converges only because "owners mutate disjoint authority files," and it rebuilds root, user, machine, hood, session, and agent pages after every pull (`docs/agents_sidecar.md` ~L203–210). Shared mutable goals break the first property and would pay the second cost on every goal write. It is also a history-publication store, not live work state. |
| ↳ privacy | cld and grk argue a privacy difference between repos | **Not a differentiator here** | `gh api` reports `sase-org/sase--agents`, `--beads`, `--plans`, and `--research` as **public**. The agents sidecar already publishes prompts publicly. grk's "agents can't see the agents sidecar" is true only at the file level: `sase goal list` would read a hidden host clone either way. |
| ↳ beads repo vs a new repo | cld co-hosts; grk wants its own lock (the precedent is beads splitting out of plans) | Co-host first; the role indirection allows a split | The beads repo is the project's shared work state, already has a hidden host clone (`~/.sase/projects/<key>/repos/beads`), and already gets `sidecar_auto_sync` hints. Split only when commit contention is *measured* (`corpus-before-mechanism`). |
| **Hot record shape** | A mutable `live/<id>.json` snapshot (cdx, grk, mus, gem); an empty marker plus immutable events (cld) | **Markers + immutable events + a machine-local projection** | Snapshots edited in place can hit content conflicts when two machines touch one goal. Unique event files and marker add/delete can't. gem's "move `active/` → `settled/`" is not atomic under concurrent edits. |
| **TUI placement** | A top-level tab (cdx, cld); the default Artifacts subtab plus a top-bar chip (grk, mus, gem, prior) | **A top-level Goals tab** in second position. Its body reuses Artifacts-pane components. No separate Artifacts ▸ Goals pane in v1: history is a lazily loaded lane inside the tab. | Your main complaint is discoverability, and this tab replaces Agents unread dots as the daily loop. As a subtab, it would displace `stitches` (the current `DEFAULT_ARTIFACTS_SUBTAB`) and still take two hops. The review card is bespoke. The tab's costs (tab persistence, goldens, keymap) are one-time. The Goals inbox tab gives grk's top-bar prominence for free. |
| **Verification transport** | A `JumpToGoal` notification (cdx, cld, mus, gem); a `GoalVerify` interaction gate (grk) | **A `GoalVerify` interaction gate** whose notification row has action `JumpToGoal`. The ledger stays canonical, and the gate is only the transport. | Gates already provide the TUI, mobile, Telegram, and typed CLI decision paths, Remote Attention across machines, and the rule that "read/dismissed is never a decision" (`docs/notifications.md`). A Reject branch's gate follow-up can relaunch onto the goal. Gates are created by the host after the turn, so `gates-never-block` holds. |
| **Answer-only claims** | Settle when you read them (cld); require an explicit `v` (grk) | **Acknowledgement is the default**, recorded as `done · acknowledged`, not `verified`. It fires when you *open the answer*, not when you dismiss the row, and it can be undone. | This keeps about 25 answers a day from becoming chores, and never claims a verification that didn't happen. It also addresses grk's accidental-verify worry. |
| **Claim authority** | "The last live contributor claims" (cld); declared owner/contributor/reviewer roles (cdx, grk) | **Host-derived** from launch structure plus liveness (§4.5) | It is deterministic, and no agent declares its own authority. |
| **Terminal states** | `verified`/`waived`/`canceled`/`superseded` plus `conflicted` (cdx, grk, gem); `done`/`dropped` (cld) | `done` {verified, acknowledged} and `dropped` {canceled, merged, superseded}. Waive becomes "verify with note." Conflicts are diagnostics, not a state. | Fewer states for you to learn, while the flavors keep the audit trail. |
| **Code evidence** | gem requires a clean test receipt for every code claim | A receipt is required only under `goals.require_receipt_for_code`. Otherwise the claim shows an **untested** badge. | A blanket requirement would push agents to game results or never claim. |

**Other corrections to researcher claims:**
- gem's `◈ ACTIVE` glyph already appears in 14 `src/sase` files. `⌖` appears in none, `◎` is the bead *claimed* status, and `◉` is the Stitch pane icon, so use `⌖`.
- gem's "read time < 1 ms" and "~30 KB" are unmeasured.
- Receipts are **machine-local** (glossary: *Receipt*). No report handled this: a claim must *embed* a receipt summary so other machines can render it (§4.5).

---

## 4. Design

### 4.1 Concept and lifecycle

A **Goal** is the durable outcome behind one or more agent turns. It has:
- **Identity:** `goal:<id>`, where the id is five Crockford base32 characters such as `7k2mq`, plus `project`.
- **Text:** `title` (≤ 60 chars) and `outcome` (one sentence saying what will be true when done).
- **Optional criteria,** each tagged with its source: `user`, `plan`, or `agent`.
- **An immutable `origin`:** the creating agent's ref, its submitted-prompt digest, the root prompt digest, the machine, and the time.
- **Optional links:** a `plan` and beads.
- **`revision`.**
- **Derived data:** contributors, claims, and a timeline.

**Intent vs. objective** (cdx) is the guard against moving goalposts:
- The origin prompt never changes, and the title, outcome, and criteria are revisioned.
- An agent may add or clarify criteria. It may not remove criteria written by the user or the plan.
- Every edit appears in the timeline, and the review card always shows *You asked* next to *Claim*.

| Status | Meaning | Hot? | Where it appears |
| --- | --- | --- | --- |
| `draft` | Bound at launch, not yet named. Machine-local only. | yes | dim italic `⌖ naming…` |
| `active` | Named, and in progress or paused | yes | **Running** if any contributor is live, otherwise **Idle**. This is derived from local and remote agent inventory, not stored. |
| `review` | An agent claimed it; waiting for you | yes | **Review** lane, counted in the tab badge |
| `done` | Settled: `verified` or `acknowledged` | no | history |
| `dropped` | Settled: `canceled`, `merged`, or `superseded` | no | history |

```text
 launch ─► draft ──name / adopt──► active ◄─────── reject + feedback / your follow-up ──┐
                                     │  ▲                                              │
                   claim + evidence  │  └── another agent adopts it (claim retracted) ─┤
                                     ▼                                                 │
                                  review ──────────────────────────────────────────────┘
                                     │ verify / acknowledge (you)     drop / merge (you)
                                     ▼                                    ▼
                                   done                                dropped
```

Goal status is not agent status. A failed or killed agent leaves the goal `active`, and
the goal becomes Idle once no contributor is live.

### 4.2 Binding: the host binds, the agent names

Binding resolution is a **pure Rust function over launch facts**, and Python supplies the
facts. It runs after the project, workspace, and planned agent identity are known, and
before the provider is spawned. The first match wins:

1. **Explicit.**
   - `%goal:<id>` binds this launch to an existing unsettled goal. It can come from you, from the Goals tab's *launch onto goal* action, from a reject-and-relaunch, or from a parent agent.
   - `%goal:new` opts out of inheritance.
   - Add `goal` to `_KNOWN_DIRECTIVES` (`xprompt/_directive_types.py`) and tab-complete it over active goals.
   - `@goal:<id>` only **cites** a goal: it expands to the goal's card text and does not bind.
2. **Session.** Pipe, questions, monitor and gate follow-ups, retries, and plan→code successors inherit the goal. Add `goal_id` to the metadata preserved across re-execution and to the fields successors inherit.
3. **Plan.** A plan's `goal_id` binds the agent. Epic phase and land agents resolve it through the epic bead → plan → `goal_id` chain.
4. **Clan.** Every member of a clan launched together shares **one** goal. The first member to name it wins.
5. **Parent.** Agents launched by an agent (`/sase_run` → LaunchApproval) inherit the parent's goal. **Prerequisite:** actually persist `parent_agent_name` and a new `parent_goal_id` into the child's metadata.
6. **Bead.** `sase bead work` on a bead linked to exactly one unsettled goal binds to that goal.
7. **Routine.** Chop runs bind to their routine's **standing goal**. It can't be claimed and sits in a collapsed "Standing" group.
8. **Otherwise, a draft.** The draft's display title is a prompt excerpt, with directives and xprompt refs stripped.

**Where the binding lives:**
- It is carried as a structured `goal_binding` on the launch wire, not smuggled through `extra_env`.
- It is persisted as `goal_id` in `agent_meta.json`.
- It is exposed as `SASE_GOAL_ID` for convenience only. As with `SASE_PLAN`, the env var is not the source of truth.

**Rules:**
- **No silent fuzzy joins.** A wrong merge is worse than a duplicate, because it corrupts provenance and can let the wrong agent close an unrelated outcome.
- **Settled goals can't be rebound.** Binding to a settled goal is refused. Launch with `%goal:new`, and the new goal gets a `follows` link.

### 4.3 What the agent sees

**Already-bound turns** get one line (about 40 tokens) in their instructions:

```text
SASE GOAL ⌖3fq9t — Tailnet dispatch mesh: every enrolled machine accepts %dispatch.
```

**Draft-bound turns** get an intake block (about 80 tokens). It is injected at the
provider-neutral point right after prompt preprocessing and leaves
`submitted_xprompt.md` untouched:

```text
SASE GOAL: this turn is bound to draft goal ⌖7k2mq, created from your prompt.
Before other work run `sase goal list`. If an active goal already describes this
request, run `sase goal adopt 7k2mq -i <id> -w "<why it is the same outcome>"`.
Otherwise run `sase goal name 7k2mq -t "<title>" -o "<what will be true when done>"`.
```

**Rules:**
- **Allowed agent commands:** `list`, `show`, `name`, and `adopt`. Agents cannot create goals other than their own draft, which keeps goal spam out. Discovered follow-up work stays as task beads.
- **Naming is compare-and-swap.** Clan siblings that call it later get `already named: "<title>"` and exit 0.
- **Adopting** a goal that is in `review` retracts its claim, because new work means it wasn't done.
- **Plan-mode launches skip the intake block.** `sase plan propose` names the goal, or refines its outcome, from the plan's `title`/`goal` and records the edit with source `plan`.
- **Fallback:**
  - A draft's goal finalizer *requires* a `name` in its payload.
  - If a run dies unnamed, the host names the goal from the excerpt and shows an `auto-named` badge.
- **Drafts stay machine-local until named.** An adopted draft never reaches the shared ledger, and neither does its prompt excerpt.

### 4.4 How common work shapes play out

| Shape | What happens | Pings you get |
| --- | --- | --- |
| **A question** | 1. The host creates a draft.<br>2. The agent names it "Answer: which env var names the assigned bead".<br>3. The agent claims with `@reply` evidence.<br>4. Opening the answer acknowledges it. | 1 |
| **A research swarm** (like this one) | 1. The clan shares one draft, and the first member names it.<br>2. The researchers are wait-dependencies of the lead, so they are contributors and `keep_open`.<br>3. The lead claims with report refs. | 1 |
| **Plan → epic** | 1. The planner is bound, and `propose` stamps `goal_id` on the plan.<br>2. PlanApproval:<br>• An approval that launches implementation → the goal continues.<br>• A plan-only acceptance → `done` (the approval *was* the verification, so there is no second alert).<br>• A rejection → active/Idle, with your feedback.<br>3. Phase agents are contributors.<br>4. The land agent claims with `@commit` plus a receipt. | PlanApproval + 1 |
| **Your follow-up to an agent** | • If the goal is in Review: the claim is retracted and your prompt becomes the feedback.<br>• If the goal is Done: a new goal is created with a `follows` link. | per new claim |
| **A routine run** | Bound to the routine's standing goal. It never claims, and its findings become task beads. | 0 |
| **A crash or kill** | No decision. The goal becomes Idle, and the existing error notification gains a goal chip. | error only |

### 4.5 The goal finalizer and what "evidence" must mean

**Configuration.** The key settings are `required: [goal]` and `after: [commit]`:

```yaml
finalizers:
  defaults: [commit, goal]
  required: [goal]        # today: required: [] (default_config.yml:1753)
  instances:
    commit: { use: builtin@commit, after: [], max_attempts: 2, refusal: defer }
    goal:   { use: builtin@goal,  after: [commit], max_attempts: 2 }
```

It triggers on every normal return, including clean trees. It follows the `bead_action`
pattern: a closed enum plus a host policy function, `decide_goal_action`, in
`sase-core`.

**What the host sends the agent (the obligation):**
- the goal's id, revision, status, title, outcome, and criteria;
- `draft: true|false`;
- `can_claim`, plus the reasons if false;
- **evidence candidates** the host gathered:
  - `@commit`, resolved after commit;
  - `file:` artifacts created this turn;
  - the plan ref;
  - a covering `check` receipt on the final tree;
  - `@reply`, the host's snapshot of the reply.

**The agent's payload:**

```json
{ "decision": "claim",
  "claim": "Active goals list in <50 ms from a fresh shell on athena and apollo.",
  "evidence": [
    {"ref": "@commit", "why": "adds the ledger reader and `sase goal list`"},
    {"ref": "file:explicit:0123…", "why": "latency table for 10/100/1000 settled goals"}],
  "check": ["On apollo run `time sase goal list`; expect < 50 ms.",
            "Open the Goals tab; this goal is in Review with 2 evidence chips."],
  "gaps":  ["Not measured above 200 active goals."] }
```

Or, to keep the goal open:
`{"decision": "keep_open", "progress": "Phase 2 landed; phase 3 blocked on the sase-core release."}`.
Draft-bound turns also include `"name": {"title": …, "outcome": …}`.

**Eligibility (`can_claim`).** The host checks it at submit time and again at execution
time. All of these must hold:
- The goal is `active`, or is a draft being named in this same payload.
- **The agent's role allows claiming.** Roles are derived from launch structure, never declared by the agent:

  | Agent | Role | Can claim? |
  | --- | --- | --- |
  | Epic phase worker | contributor | no |
  | Epic land agent | owner | yes |
  | Agent that another pending agent on the same goal waits on (e.g. researchers under a lead) | contributor | no |
  | Routine run | — | no |
  | Everyone else | owner | yes |

- **No other contributor is live** (running, queued, or waiting).
- `@commit` evidence requires that `builtin@commit` succeeded and was not deferred.
- The basis revision is current. Otherwise the result is `stale_final_context`, as in the existing flow.

If `can_claim` is false, the payload template offers only `keep_open`.

**What evidence must be.** Combining all six reports gives six properties:

1. **Navigable.** Evidence is what you will *click* to verify, so it must be artifact refs. Prose (claim, check, gaps) frames the refs but never replaces them.
2. **Unforgeable.** Every ref must resolve at submit time, and its provenance must tie back to this goal:
   - a stitch must be authored by a contributor;
   - a file must have been created by a contributor;
   - a plan must be bound to this goal.

   Test results come only from host **receipts**. An agent-written "tests passed" is not evidence (`receipts-prove-before-they-skip`).
3. **Proportional.** The minimum depends on the kind of claim; see the table below.
4. **Actionable.** 1–3 **check it** steps are required. They turn "done!" into a two-minute task, which makes them the most valuable part of the notification.
5. **Honest.** `gaps` gives the agent a sanctioned place to admit limits, and they render as warnings.
6. **Gathered by the host.** The agent mostly *selects* from candidates rather than building evidence up, which cuts both tokens and fabrication risk.

| Claim shape | Minimum evidence | Host adds or checks |
| --- | --- | --- |
| Answer / review | `@reply` (the host snapshots the reply as an artifact) | Digest bound to the closing turn |
| Research / document | The `research:` / `file:` / other document ref | Produced or last updated by a contributor |
| Plan only | `plan:` ref | Approval state; PlanApproval is the decision, with no duplicate alert |
| Code / config | `@commit`, or a stitch/Patch by contributors | Covering-receipt verdict, or an **untested** badge |
| Operational (deploy, machine fix) | A `file:` output/log artifact, or a receipt | Target and observation time are explicit |

Every claim also needs a claim sentence of ≤ 280 chars. If the goal has criteria, each
criterion must either map to evidence or appear in `gaps`. The review card shows an
**evidence strength** badge, strongest first: `tested` › `committed` › `documented` ›
`answered`.

**Timing and cross-machine details that the reports mostly missed:**
- **Symbolic tokens.** `builtin@commit` hasn't made the stitch when the agent submits, and the reply isn't a durable artifact until the turn ends. So `@commit` and `@reply` are symbolic tokens that `builtin@goal` resolves *after* commit. If commit was deferred or failed, a code claim cannot publish, and the goal stays open.
- **Receipts are machine-local.** The `claimed` event therefore **embeds a receipt snapshot**: tool, verdict, fingerprint, tree SHA, and time. The ref still resolves on the claiming machine, and every other machine can render the snapshot.

**Deliberately not required:**
- **Universal test receipts.** Projects can opt in with `goals.require_receipt_for_code: true`.
- **An LLM verifier pass before you're notified.** It doubles cost. Keep it as a later per-project policy.

**How a claim executes:**
1. Validate the payload.
2. Resolve tokens and digests.
3. Append a `claimed` event (claim id, refs, digests, receipt snapshots, strength) and commit it to the hidden clone. From this point the claim is durable.
4. Create **one** `GoalVerify` gate and its notification, idempotent on `goal:<id>:claim:<n>`.
5. Push, with a time bound. If the push fails, queue it in the outbox and show an `↑ unpublished` chip.
6. Update the link projections.

**Handoffs and abnormal exits:**
- **Handoffs** (plan, questions, monitor, pipe, gate) make no decision; the successor inherits the goal.
- **Prepared monitor completion** carries a predeclared goal decision. Green claims, with the monitor's receipt as evidence. Red becomes `keep_open`, with the failure as the progress note, and recovery launches.
- **The single declaration-recovery turn** also asks for the goal payload.

**Skill text.** `sase_final` gains one paragraph: *"Claim only if the goal's outcome is
true now and you can point at evidence; otherwise keep it open with a one-line progress
note."*

### 4.6 Attention and verification

| Event | Today | With Goals (flag on) |
| --- | --- | --- |
| Agent turn succeeds | `JumpToAgent` tagged `done` → ✅ unread dot + chime (`run_agent_runner_finalize.py:469`) | **Silent**; stays visible in history |
| **Agent claims a goal** | — | **`GoalVerify` gate** with a `JumpToGoal` row, tag `goal`, loud. It carries the claim and the check-it steps. It lands in its own inbox tab, so the top bar reads `inbox: ⌖2 …` |
| `keep_open` | — | Silent; progress appears on the goal |
| Goal becomes Idle (no live contributor) | — | Quiet notice with the last progress note |
| Agent fails | `ViewErrorReport` ❌ | Unchanged, plus a goal chip |
| Plan proposed, questions, gates, sudo | unchanged | unchanged. A plan-only goal's claim is suppressed as a duplicate. |

**Gate branches.** The `GoalVerify` gate has three:
- **Verify:** optional note.
- **Reject:** your feedback is required. Its follow-up can relaunch onto the goal, pre-filled with `%goal:<id>`, your note, and `@goal:<id>`.
- **Drop.**

Because it is a gate, reading or dismissing the row is **never** a decision, and the
same decision is available in the Goals tab, `sase goal verify`, mobile, and Telegram,
with Remote Attention deduplicating on goal id + claim id.

**Answer-only claims.** These are claims whose only evidence is `@reply`. They default to
`goals.answer_claims: ack`:
- *opening the answer* from the row or the card settles the goal as
  `done · acknowledged`;
- `u` undoes that for a while;
- `verify` makes you press `v` instead.

**Who gets pinged.** The claim notifies the goal's origin owner. Other humans on the
project see it in their Review lane.

**Cutover.** It happens in two steps behind the flag:
1. Ship `GoalVerify` gates alongside today's `done` notifications.
2. Retire the success `JumpToAgent(done)` notification and its Agents-row unread
   projection. Unread success rows are migrated.

Failures, held workspaces, questions, approvals, sudo, and triage are unchanged.

### 4.7 Storage, sync, and genuinely O(n) reads

**Layout.** The `goals` sidecar role maps by default into the beads repository:

```text
goals/
  STORE.json                         schema fence
  live/<id>                          empty marker — one per UNSETTLED goal (the hot index)
  items/<id>/events/<ulid>.json      immutable events — the only source of truth
```

**Invariant: nothing is edited in place.**
- Writers only add uniquely named event files and add or delete markers, so a rebase can never hit a content conflict.
- The only possible race is on a marker (for example, reopen vs. verify). The sync step resolves it by reducing that goal's events: a marker exists exactly when the goal's reduced status is unsettled.
- There is no committed derived state to regenerate.

**Events:**
- `created`
- `named`
- `edited`
- `adopted`
- `agent_attached`, written only for session roots, because successor turns inherit implicitly
- `progress` (≤ 280 chars)
- `plan_attached`
- `claimed`
- `claim_retracted`
- `settled` (with its flavor)
- `reopened`
- `merged`

Every event records actor (`<username>.<machine>`), `basis` (the event it was computed
from), and an idempotency key.

**Write path:**
- `sase_core::goal` validates each transition against the reduced state and the basis.
- Python writes into the **host-owned hidden clone** (`~/.sase/projects/<key>/repos/beads`), in the spirit of `machine-link-writes-off-primary`.
- **Claims and human settlements push synchronously**, with a time bound, a fetch → rebase (conflict-free) → revalidate → push retry loop, and the outbox plus `↑ unpublished` chip on failure.
- Attach and progress events are appended locally at once and **batched** into the `sidecar_auto_sync` tick, which keeps commit churn low: at today's volume that is roughly 100–300 small events a day.

**Read path:**
- `sase goal list` does a `readdir(live/)`, giving n markers. It then reduces each live goal's events: O(n × e), where e is bounded per goal. Settled goals' directories are **never opened**.
- A machine-local projection, `~/.sase/projects/<key>/goals-hot.json`, is keyed by directory signatures. It makes a warm read one file plus n stats, and it is rebuildable from `live/` alone on a fresh machine.
- A Rust fast path, like `bead_fast_path`, skips Python startup.
- The TUI paints the cached projection on the event loop and refreshes it off-thread, per the TUI performance rules.

**Performance contract.** Measured, not asserted:

| Metric | Target |
| --- | --- |
| `sase goal list` p50 | < 30 ms |
| `sase goal list` p95 | < 50 ms at 1,000 unsettled goals |
| TUI projection refresh | < 2 ms at n = 100 |
| Highlight → paint | within the existing 16 ms budget |
| Growing settled goals from 0 to 100k | changes hot-list p95 by ≤ 10% |
| Cold rebuild | opens only `live/` and live goals' `items/` (proved with file-open tracing) |

**Not covered by the O(n) promise:**
- first-clone time;
- `sase goal doctor` repair;
- history search (a lazy index built off the event loop).

**Freshness:**
- The Goals tab shows `synced 12s ago`.
- `sase goal list` triggers a TTL-gated background fetch.
- `--fresh` fetches synchronously.

**Concurrency rules.** Deterministic, always shown, never silent:
- Two claims on the same basis: the first by ULID wins, and the second is recorded as superseded.
- A drop that races a claim: the drop wins, because it is your intent.
- An adopt that races a verify: the adopt is recorded as a late attachment with a diagnostic, and the goal stays done.

**Hygiene.** n is bounded by the unsettled set, but kept-open goals that nobody returns to
would grow it. Show aging on Idle rows and offer a "stale: drop?" nudge after
`goals.idle_nudge_days`. Never auto-verify. Unnamed drafts whose run died are auto-named
and go Idle rather than vanishing.

**Local-only mode.** Projects without a beads or goals sidecar use the same ledger format
in a machine-local git repo (`~/.sase/projects/<key>/goals/`), clearly labeled
*local only*.

### 4.8 Prompt provenance and privacy

**What counts as "the original prompt":**
- **Unit prompt:** the creating agent's `submitted_xprompt.md`, the launch-boundary prompt before alias or xprompt expansion. `raw_xprompt.md` is alias-resolved and is *not* the original.
- **Root prompt:** for fan-outs and swarms, the root launch prompt before segmentation. It is recorded separately.
- **Also asked:** each adoption adds that agent's unit prompt.

**How prompts are stored:**
- The goal stores **agent ref + digest**. Bodies stay in the agents sidecar's content-addressed prompt archive.
- **New publication trigger:** naming a goal publishes the creator's prompt. Today prompts publish mainly on commit or plan approval, so a question-only agent's prompt would otherwise never leave its machine.
- Rows and notifications **never** contain prompt bodies. The card shows a two-line preview, and `p` opens the full text.

**Visibility.** All four sase sidecars are public on GitHub today. So goal titles,
outcomes, and claims would be as public as bead and plan titles already are, while
prompts keep their current exposure. Offer `goals.visibility: local` for projects that
need otherwise, and document what a goal publication discloses.

### 4.9 Artifact identity, links, and jumps

**The `goal:` kind.** `goal:` becomes a built-in artifact kind in `sase-core`: a catalog
entry plus a resolver that reads the project's ledger. `sase artifact read goal:<id>`
renders the card.

**New relations.** The relation registry is closed, so these are deliberate schema
additions. All of them are **projected** from durable facts, so no link-event writes
happen per agent:

| Relation (inverse) | Source → target | Projected from |
| --- | --- | --- |
| `pursues` (`pursued-by`) | agent → goal | `goal_id` in agent metadata |
| `evidences` (`evidenced-by`) | artifact → goal | `claimed` events |
| `defines` (`defined-by`) | plan → goal | the plan's `goal_id` |
| `follows` (`followed-by`) | goal → goal | follow-up goals |

Merges reuse `supersedes`. Keep `implements` for plan, agent, and stitch → bead.

**Jumps:**
- Every agent and ref on a goal card is a **numbered chip** that reuses the relation rail. `1`–`9`, `$`, and `Ctrl+O` trail history all work.
- **Agent chips** go through `reveal_agent_navigation_target`. It switches to Agents, expands collapsed groups, and clears a blocking filter with a toast. If the agent is not in live inventory, it falls back to Artifacts ▸ Agent.
- **Prerequisite fix, verified in code:** `handle_jump_to_agent` (`actions/agents/_notification_handlers.py`) linearly scans `app._agents`, sets `current_idx`, and never reveals collapsed rows. `JumpToGoal` must use the reveal path, and fixing `JumpToAgent` the same way is cheap.

### 4.10 The TUI

```text
 Agents   Goals ⌖2   Artifacts   Services                                inbox: ⌖2 ⚑1
╭─ Goals · sase ─────── 2 review · 3 running · 1 idle ─╮╭─ ⌖ Goals feature design ─────────── REVIEW ─╮
│ REVIEW                                               ││ goal:7k2mq · opened 2h ago · claimed 3m ago  │
│ ▸⌖ Goals feature design              3m  ✓✓✓✓✓●     ││                                              │
│  ⌖ Fix flaky bead sync test         41m  ✓          ││ YOU ASKED  "I want to add a new "Goals"      │
│ RUNNING                                              ││            functionality to sase. Goals…"    │
│  ⌖ Tailnet dispatch mesh · epic      2h  ✓✓●○       ││            p full prompt · +1 also asked     │
│  ⌖ Deck paging polish                8m  ●          ││ OUTCOME    A critiqued, recommended design   │
│  ⌖ Answer: why is apollo sync slow   1m  ●          ││ CLAIM      research.2r.lead · documented     │
│ IDLE                                                 ││            Host-bound goals, agent-named…    │
│  ⌖ Apollo memory pressure            1d  ✗          ││ CHECK IT   1 Read §7 "Recommended solution"  │
│    "OOM repro still unclear"                         ││            2 Confirm the storage choice      │
│ ▸ Standing (2) · Done today (5)                      ││ EVIDENCE   [1] ▤ research:…/sase_goals_design│
│                                                      ││            [2] ▤ research:…/…__cld.md        │
│                                                      ││ GAPS       ⚠ No prototype; targets only      │
│                                                      ││ AGENTS     [3] ✓ cdx [4] ✓ cld … [8] ● lead  │
│ synced 12s ago                                       ││ TIMELINE   created · named · 5 progress · …  │
╰──────────────────────────────────────────────────────╯╰─ v verify  r reject  x drop  l launch  p prompt╯
```

**Tab placement.** `TAB_ORDER` becomes `("agents", "goals", "artifacts", "services")`.
Goals sits next to Agents because goal ↔ agent is the most common jump. Its badge counts
**Review** goals and is hidden at 0. Agents stays the startup tab during the rollout.

**Lanes.** They are ordered by what you should do:
- **Review:** verify it.
- **Running:** just watch.
- **Idle:** relaunch or drop.
- **Standing** and **Done today** are collapsed. *Done today* loads lazily from history.

**Rows.** `⌖` + title + age + contributor pips (`●` running, `○` waiting, `✓` done,
`✗` failed), at most five pips and then `+n`. Idle rows show their last progress note.

**The card.** It is built for a 30-second judgment and reads **You asked → Outcome →
Claim → Check it → Evidence → Gaps → Agents → Timeline**, which is the comparison you
actually make. The same renderer draws the Agents-tab Goal card.

**Keys** (register them in `src/sase/default_config.yml`, per the gotchas note):

| Key | Action |
| --- | --- |
| `v` | Verify, with an optional note |
| `r` | Reject with feedback, then optionally relaunch |
| `x` | Drop |
| `l` | Launch an agent onto this goal |
| `e` | Edit title/outcome |
| `m` | Merge into another goal |
| `a` | Jump to the newest live contributor |
| `p` | Open the origin prompt |
| `n` | New goal (optional) |
| `/` | Filter |
| `P` | All projects |
| `h` | Toggle the history lane |

**Agents tab integration:**
- **Identity header:** a `⌖ <title>` chip colored by status. One key opens the goal.
- **FINAL deck:** a **Goal** instance card. The FINAL deck and generic FINAL instance cards just landed (`482ec80ff9`, `6ad0539cfc`, `e75840b0c9`), so this is a *goal enricher* rather than a new widget. It shows this turn's decision, the claim, and evidence chips.
- **Grouping:** a **by goal** mode in the `o` picker. Banners are ordered Review → Running → Idle, and internal goals collapse.
- **Unread markers:** ✅ unread for successes is retired under the flag. ❌ stays.

**Visual grammar:**
- **Glyph:** `⌖` (U+2316), which is unused in `src/sase`.
- **Accent:** one new color, chosen against the existing pane palette (stitches `#FFD700`, beads `#D787FF`, agents `#0062FF`, patches `#00D7AF`, files `#FFAF5F`, plans `#AF87FF`) and checked in the visual snapshots.
- **Status:** always text plus glyph, never color alone. Gaps use the warning color.
- **Motion:** none beyond the existing unread mark.
- **Order:** rows keep a stable order so the inbox doesn't jump under your cursor.

**Empty state:** *"No active goals. Every agent you launch gets one automatically —
press `n` to set one yourself."*

### 4.11 CLI and skill

Bare `sase goal` runs `list`. Options are alphabetical, and every long option has a short
alias (see the `cli_rules` memory):

```text
sase goal adopt ID -i/--into GOAL -w/--why TEXT      # agent: merge my draft into an active goal
sase goal doctor [-r/--repair]                       # rebuild markers/projection (never on the hot path)
sase goal drop ID -w/--why TEXT                      # human
sase goal list [-a/--all-projects] [-f/--fresh] [-j/--json] [-s/--status S]
sase goal merge ID -i/--into GOAL                    # human
sase goal name ID -o/--outcome TEXT -t/--title TEXT  # agent: name my draft (compare-and-swap)
sase goal new -o/--outcome TEXT -t/--title TEXT      # human (refused inside agent runs)
sase goal reject ID -m/--message TEXT [-l/--launch]  # human; -l relaunches with feedback
sase goal reopen ID -m/--message TEXT                # human
sase goal show ID [-j/--json]
sase goal verify ID [-m/--message TEXT]              # human (resolves the GoalVerify gate)
```

**Status verbs are human-only.** `verify`, `reject`, `drop`, `reopen`, and `merge` are
refused inside agent runs, mirroring the rule that agents never hand-edit bead status.
Claims happen only through the finalizer.

**Agent-facing `list` output** is one compact line per goal:
`⌖ 7k2mq  review  Goals feature design  5 agents · 3m`.

**The `/sase_goal` skill** is generated from `src/sase/xprompts/skills/` and teaches
list/show/name/adopt. There is **no** mandatory `/sase_new_goal`.

### 4.12 Rust / Python boundary

- **`sase-core`:**
  - goal wire and domain types, ids, events, and the reducer;
  - transitions, eligibility, and evidence validation (`decide_goal_action`);
  - binding resolution;
  - ledger I/O, the hot projection, and the `list`/`show` fast path;
  - the finalizer obligation and payload wire;
  - the `goal` ref kind, relations, and projection rules.
- **Python:**
  - launch orchestration and prompt injection;
  - the `plan propose` hook;
  - finalizer glue, the outbox, and notifications/gates;
  - the TUI;
  - skill text.
- Every binding sase calls needs the `sase-core-revision.txt` pin moved forward.

---

## 5. Rollout, metrics, and acceptance

**Flag.** Create a `goals` flag (`sase flag new goals`) as epic scaffolding, removed
before the epic lands. This is `xlarge` work: an epic.

| Phase | Deliverable | Visible to you? |
| --- | --- | --- |
| **P0** | Prerequisites: write parent lineage into child metadata; reveal-path `JumpToAgent`; a prompt-publication trigger | no |
| **P1** | In `sase-core`: the ledger, reducer, projection, and fast CLI. Then the binding ladder, drafts, injection, `/sase_goal`, `goal_id` in metadata, and plan-propose naming. | CLI only |
| **P2** | `builtin@goal` (required, after commit), the `sase_final` update, prepared-monitor support, `GoalVerify` gate + `JumpToGoal` (running *alongside* `done` pings) | notifications |
| **P3** | The Goals tab, the Agents chip / FINAL Goal card / by-goal grouping, the `goal:` kind and relations | yes |
| **P4** | Attention cutover (silence successes), answer ack, Idle notices; soak; remove the flag | yes |

**Metrics:**
- claims per day;
- verify, reject, acknowledge, and lapse rates per model;
- median time-to-verify;
- adopt vs. name ratio;
- merges per 100 goals;
- Idle-goal age;
- notification volume before vs. after;
- `sase goal list` p50/p95 as settled history grows (it should stay flat).

**Acceptance tests:**
1. Every new LLM turn has exactly one `goal_id` before the provider starts. Mechanical procs create none.
2. Direct, plan, bead, swarm, `%alt`, `%repeat`, session, child, retry, dispatch, gate, pipe, question, and monitor paths all preserve the intended binding and role.
3. A five-member swarm yields exactly one goal and one claim.
4. Epic phases can never claim; the land agent can. A claim is refused while another contributor is live.
5. The stored unit-prompt digest matches `submitted_xprompt.md`, and swarm root provenance is separately reachable.
6. `@commit` is refused when commit was deferred. Missing, cross-project, or stale evidence blocks the claim, and no gate is created.
7. One claim produces exactly one gate/notification across retries and machines. Reading or dismissing it does not settle it.
8. Concurrent events from two clones rebase without conflict, and a marker race resolves by reduction.
9. Adding 100k settled goals doesn't materially change hot-list latency or the TUI's file opens.
10. A goal → agent jump reveals a grouped or collapsed live row and falls back to the archived Agent pane.
11. An adopted draft never appears in the shared ledger.
12. A local-only project is labeled as such and never publishes.

---

## 6. Open questions for you

1. **Answer claims:** is `ack` on opening the answer the right default, or do you want an explicit `v` for everything?
2. **Tab:** is second position right, and do you want a direct key for Goals? Should it become the startup tab after the soak?
3. **Visibility:** are you comfortable with goal titles, outcomes, and claims being as public as bead and plan titles already are?
4. **Routines:** standing goals (my recommendation), or the one documented exemption?
5. **Cross-repo work** (for example sase + sase-core): the goal lives in the *launching* project. Acceptable?
6. **Stale reviews:** should unreviewed claims lapse after N days into a distinct settled flavor? Never an auto-verify.

---

## 7. Recommended solution

1. **Model.** Build Goals as a first-class, Rust-owned `goal:` artifact:
   - lifecycle `draft → active (Running/Idle) → review → done / dropped`;
   - an immutable origin prompt kept separate from a revisioned title, outcome, and criteria.
2. **Binding.** The **host binds every LLM agent turn to exactly one goal** before spawn:
   - It uses explicit `%goal`, session, plan `goal_id`, clan, parent, bead, or routine facts.
   - Otherwise it creates a machine-local **draft**, and the agent's first act is to **name** it or **adopt** an existing active goal.
   - Planners get their goal named from the plan.
   - Your follow-ups retract or chain goals.
   - You never have to write a goal, and you can always pick one.
3. **Finalizer.** A required **`builtin@goal`**, ordered after commit, makes every normal turn choose `keep_open` (with a progress note) or `claim`.
   - Claims are allowed only when host-derived role and liveness permit.
   - A claim must carry **resolvable, provenance-checked refs** (mostly host-gathered: `@commit`, created artifacts, plan, receipts, `@reply`), **1–3 check-it steps**, and **gaps**.
   - Receipts are embedded as snapshots, and tests are required only by policy.
4. **Verification.** A claim moves the goal to **Review** and opens one **`GoalVerify` gate** (TUI, CLI, mobile, Telegram).
   - **You** verify, reject (optionally relaunching with feedback), or drop.
   - Answer-only claims settle on acknowledgement.
   - Successful agent completions go quiet. Errors and decisions keep their routes.
5. **Storage.** A conflict-free **goal ledger**: immutable events plus `live/` markers.
   - It is a `goals` sidecar role, co-hosted in the beads repository, written through the hidden host clone, and split out only if contention is measured.
   - Reads are O(n_unsettled) through a local projection and a Rust fast path, with visible sync freshness.
   - Prompts are linked by ref and digest.
6. **Surfaces.** A top-level **Goals** tab:
   - Review · Running · Idle lanes;
   - *You asked → Claim → Check it → Evidence* cards;
   - numbered jumps to every agent and artifact.

   On the Agents tab: goal chips, a FINAL-deck Goal card, and *by goal* grouping. The top-bar inbox gets a `⌖N` Goals tab.
7. **Delivery.** Five phases behind a `goals` flag:
   - lineage and jump fixes first;
   - claims running alongside today's pings before the cutover;
   - claim quality, notification volume, and flat latency measured before the flag is removed.
