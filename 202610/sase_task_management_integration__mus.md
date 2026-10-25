# SASE × Task Management Systems: Is a Deeper, System-Agnostic Integration Worth It, and What Would It Unlock?

Researcher: mus (`__mus`) — independent report in a 5-researcher swarm.
Date: 2026-10-25. Vault/tools observed live in workspace `sase_13`.

## TL;DR

Yes — with a narrow waist. SASE already owns half of this problem (beads as the
agent-native task store, `bead sync-external` + the `external_issue_mirror` AXE job
as the GitHub-issues precedent, gates as the human-approval primitive, monitors and
the scheduler/AXE routines as the polling-and-launch substrate, `sase run` + macros
as the launch path, artifacts as the audited evidence path). Bob-cli owns the other
half (the Obsidian vault as source of truth, the six-lane task model, `bob task
reconcile` as the derived-state reconciler, `bob query` as the machine-readable task
API, `bob ref`/Highlights sync as the reading-task pipeline, capture grammar as the
intake path). What is missing is the thin integration layer between them — and that
layer should be **task-system agnostic from day one**, because SASE's existing
external-mirror design already assumes N trackers, and Bryan's own work already
spans at least three (Obsidian/`#task` lines, GitHub issues, SASE beads).

Recommendation: build a small **Task Bridge** — one capability interface
(`list/get/claim/launch-note/complete-note`), two reference adapters (Obsidian via
`bob query` + vault writes; GitHub via the existing `sync-external` machinery),
explicit human gates at every autonomous boundary, and scheduler-owned polling. Do
not build "the Obsidian integration" as a snowflake; build the bridge with Obsidian
as adapter #1. Phase 0 (read-only propose + manual launch) is shippable in days and
de-risks everything; autonomous launch only after loop-prevention and budget caps
are proven.

## 1. What exists today (verified in-tree)

### 1.1 SASE's side

- **Beads are the agent-native task store.** `sase bead {create,list,show,ready,
  blocked,dep,note,snooze,close,export}` plus `bead_task_triage` (raises one human
  gate per ready/snoozed task) already encode "task with state, deps, notes, and a
  human triage gate." Any external task that matters to agents ends up mirrored here
  or it is invisible to planning/epic machinery.
- **The external-mirror precedent exists and runs.** `sase bead sync-external`
  ("diff an enabled project's external tracker against its beads on `external_ref`")
  plus the scheduled `external_issue_mirror` AXE job already mirror "every external
  tracker issue into a task bead," handling upstream close/reopen and writing
  attributed notes for referenced/worked/parented beads. This is the architectural
  template: poll → diff on a stable external id → create small open beads →
  reconcile closes/reopens → never clobber worked state. An Obsidian/`bob` adapter
  is a second instance of this pattern, not a new invention.
- **Launch exists.** `sase run "<prompt|macro ref>"` launches detached background
  runs from prompts, macro references (`+home ...`, `#fork(...)`), or workflows, and
  they appear in the Agents tab. A task bridge does not need a new launcher; it
  needs to *compose a prompt* (task body + repo + acceptance bar) and call `sase run`.
- **Approval exists.** `sase gate {create,list,act,answer,wait}` is the
  command-backed durable human-approval primitive; `bead_task_triage` already uses
  exactly this shape for agent-proposed work. The user's "agent proposes task
  clarification; if accepted, tag + launch" flow maps 1:1 onto gate → tag-write →
  `sase run`.
- **Polling exists.** The scheduler + AXE routines (`axe job list` shows dozens of
  steady-state jobs: triage, mirror, cleanup, digest) plus `sase monitor start` for
  slow commands are the substrate for "watch the vault, launch when tagged." No new
  daemon is needed; a new routine (e.g. `obsidian_ready_mirror`) joins the existing
  roster with the sameoperational tooling (status, maintenance mode, logs).
- **Evidence/audit exists.** `sase artifact create -p <path> -l <label>` and the
  artifact-link derivation machinery give the audited "evidence of completion"
  channel. A completion note pasted as bare Markdown is cheap; a completion note
  that resolves as an artifact ref is checkable later.

### 1.2 Bob's side (bob-cli + vault)

- **The vault owns the state; the CLI owns writes** (`docs/concepts/
  how-bob-fits-together.md`). Agents must respect this: read via `bob query`
  (native Dataview-DQL + Tasks-v8 engines, JSON output), write via `bob` verbs
  (`capture`, `task move/archive/reconcile`, `ref ...`), never by regex-editing
  Markdown. This is the single most important constraint in the whole design.
- **The lane model is richer than beads.** Six checkboxes — `[ ]` Ready, `[*]`
  Next, `[/]` Pending/In-Progress, `[?]` Blocked (derived, never authored), `[x]`
  Done, `[-]` Cancelled — with sticky Next/Pending (only an explicit release sends
  them back to Ready) and derived Blocked recomputed by `bob task reconcile` from
  Depends-On lines, future `scheduled` dates, and project inheritance
  (`docs/concepts/tasks-and-lanes.md`, `docs/task-status-hooks.md`). Mapping to
  bead statuses must be explicit and lossy-by-design (see §4).
- **Tags route and group.** `#task` is the Tasks global filter (rendered as a teal
  `⌗` glyph by the plugin but stored as text); `@name` suffixes route tasks to
  `~/bob/name.md`; `#q`/`@q` aliases already exist as the "Open questions" section
  tag in the Highlights pipeline (`docs/highlights-ref-sync.md` §Sections). The
  user's proposed `#ready-to-work`-style tag and `#q`-triggered Q&A both fit
  existing grammar rather than inventing syntax — but tag-vocabulary governance is
  needed so agents don't mint synonyms (`@sase`, `#sase`, `#agent`, …).
- **Reading tasks are first-class.** `bob ref {find,list,show,today,create,scan}`
  manages the `ref/` library; v2 reading tasks are `#task #ref` lines in area/
  project/inbox notes; annotation bullets containing `#task` become follow-up tasks
  with `🔖` source backlinks and `[h:: …]` provenance. A Highlights comment
  containing a question is *already* one regex away from being a task — the Q&A
  use case is pipeline completion, not greenfield work.
- **Capture is the intake contract.** Short drafts → one inbox line with creation
  metadata → review moves it. Agent-proposed tasks should enter through `bob
  capture` (or the `bob capture-*` protocol verbs), not by appending lines, so
  dedup (`capture-related`), routing, and metadata stay consistent.

## 2. Is it a good idea? (judgment)

**Yes, with three guardrails.** The connection the user senses is real: both systems
are fundamentally *queues of committable work with human review gates*, and SASE
agents are currently cut off from the richest such queue Bryan has (the vault)
while the vault is cut off from the cheapest labor pool available (agents). Every
manual copy-paste between them today is integration debt.

The case for:

1. **It removes the two most expensive hops.** Vault → prompt (user hand-composes
   agent context from a task) and agent-result → vault (user hand-files evidence
   back) are pure toil, and both are automatable without changing either system's
   semantics.
2. **The primitives already exist on both sides.** Nothing above requires a new
   launcher, a new approval system, a new scheduler, or new task grammar — only
   wiring. That is the signature of a good integration.
3. **Agnosticism is nearly free and buys the second adapter.** GitHub issues are
   already half-bridged (`sync-external`); Obsidian is the missing adapter; a
   Todoist/Things/Linear adapter later is the same interface. Building Obsidian-only
   would strand the GitHub work instead of generalizing it.

The case against / risks (all manageable, none fatal):

1. **Autonomy over a personal GTD system can corrupt the system.** A bad agent run
   that mass-retags, mass-closes, or mass-comments in `~/bob` damages years of
   trusted capture. Mitigation: read-only phases first; scoped write verbs; dry-run
   everywhere (`bob task reconcile --dry-run` is the model); per-run task caps; the
   vault stays authoritative and every agent write is a normal commit away from
   revert (`vault-git-sync`).
2. **Loops.** Agent completes task → writes note → note triggers launch → agent
   relaunches on its own output. Both SASE (receipts prove before they skip;
   idempotent reconcile) and bob (`reconcile` is idempotent; Blocked is derived)
   already design against re-entry, but the bridge must add its own guards:
   launched-by markers, terminal-state short-circuit, and "never launch on a task
   whose last writer was the bridge unless a human touched it since."
3. **Cost and attention.** Unattended launch burns quota (`muse_quota_burn` prior
   research is cautionary) and every proposal consumes review attention. Mitigation:
   budget caps per day, proposal batching (one gate per N proposals, mirroring
   `bead_task_triage`), confidence thresholds, and quiet hours. The scheduler
   already has maintenance mode; the bridge must honor it.
4. **Fidelity loss in status mapping.** Six lanes + freshness + review tiers do not
   fit bead open/closed + snooze. Accept a documented lossy mapping (Ready/Next →
   open; Pending → in-progress note, not a status; Blocked → bead blocked/dep;
   Done/Cancelled → closed with reason) rather than extending either model.

Verdict: proceed, agnostic core, Obsidian-first, gates at every autonomous step,
no autonomous launch until the read-only + manual-launch phases earn trust.

## 3. Proposed shape: the Task Bridge (system-agnostic core)

Keep the waist narrow — one interface, adapters at the edges:

```
 External systems                Bridge core                  SASE
┌─────────────┐   list/get    ┌────────────────┐  mirror  ┌──────────┐
│ Obsidian/bob │◄────────────►│                ├─────────►│  beads   │
│  (adapter 1) │  claim/note  │  Task Bridge   │  launch  │ sase run │
├─────────────┤  transition  │  (poll+diff+   ├─────────►│  gates   │
│ GitHub issues│◄────────────►│   propose)     │  evidence│ artifacts│
│  (adapter 2) │              └────────────────┘          └──────────┘
└─────────────┘        ▲ scheduler routine + budget + loop guards
```

- **Capability interface** (every adapter implements): `list_ready` (poll query) /
  `get(task)` / `propose_edit(task, diff)` → gate / `claim(task, agent_id)` /
  `post_note(task, markdown, artifact_ref?)` / `transition(task, lane)` — with
  dry-run on all mutating calls. Adapters translate to native verbs (`bob query` /
  `bob capture` / `bob task …`; GitHub API / `sync-external`).
- **Identity:** stable external id per system (vault: note-path + block id, e.g.
  `Projects/seedlings.md#^label-trays`; GitHub: issue number; beads:
  `external_ref`). The mirror diffs on this key — exactly as `sync-external` does.
- **Direction discipline:** the external system owns task truth; beads own
  agent-execution truth. The bridge copies and links, never merges state machines.
  Status mapping is documented and lossy (see §2.4).
- **Loop guards (non-negotiable):** launched-by marker on claimed tasks;
  ignore tasks whose last mutation was the bridge's own (unless human-touched
  since); terminal states never relaunch; per-system daily launch budget; global
  kill switch via scheduler maintenance mode.
- **Prompt composition, not a new launcher:** the bridge builds a prompt (task
  text + note context + block links + acceptance bar + "file evidence as artifact
  ref + post completion note") and calls `sase run` with a macro (`+home`,
  `#research_swarm`, per-task-type templates). This is where "plan-and-implement
  vs. research-swarm" becomes a per-task routing choice.

## 4. Use cases, ranked

### Tier 0 — the user's three, assessed

1. **Tag → auto-launch → completion note + Pending (`[/]`).** Sound, and the
   flagship. Mechanics: tag (e.g. `#sase` / `@sase`, to be governed) → routine
   polls `bob query` → mirror bead (`external_ref`) → `claim` (prevents double
   launch) → `sase run` with composed prompt → on success, `post_note` with
   artifact ref + `transition` to `[/]` (Pending = "work started in Obsidian,"
   sticky — correct semantics for "agent did it, human to verify") rather than
   `[x]`; human check-off stays manual. Open design point: whether claim sets
   `[*]` (Next) first so the task visibly leaves Ready during execution.
2. **Agent proposes task clarification → accept → tag → launch.** Sound, and the
   highest-leverage review-saver once tuned. Mechanics: low-confidence parse or
   missing acceptance criteria → `propose_edit` → batched human gate (one gate per
   proposal, `bead_task_triage`-style) → accept applies the edit through `bob`
   verbs + adds the launch tag → flow (1). The research-swarm variant (proposal =
   "this needs a `#research_swarm` run first, requirements are the swarm's
   output") is the elegant version: plan-then-execute without human re-typing.
   Requires confidence calibration and proposal budgets or it becomes nagware.
3. **Highlights `#q` questions → auto-answered in place.** Sound but narrowest.
   Mechanics: section-tagged `@q`/`#q` annotation → routine detects unanswered
   question blocks in `ref/` notes → scoped research run (question + highlight
   context + paper metadata only, not the whole vault) → answer appended to the
   same note/section with provenance (`🔖` backlink + model/run id). Needs: answer
   quality bar (cite page/quote), "don't answer twice" idempotence, opt-in per
   note (some questions are *for Bryan*, not for the agent — a `#q-agent` vs `#q-me`
   split or frontmatter opt-out avoids answering rhetorical/strategic questions),
   and PDF-write discipline (answers go to the Obsidian note, never back into the
   PDF marker).

### Tier 1 — natural extensions (high value, same machinery)

4. **Morning plan → agent lane.** `bob plan` already computes today's budget and
   Today/Next/Pending; the bridge can propose "these 3 Ready tasks fit today's
   budget and are agent-shaped; launch before standup" as one batched gate.
5. **Research-swarm-as-task-type.** Any task tagged `#research` (or routed by the
   bridge's classifier) launches the `#research_swarm` macro swarm instead of a
   coder run, with the swarm's synthesized report filed as the completion artifact.
   Makes the user's second bullet a routing rule, not a special case.
6. **Decomposition proposals.** Agent reads an oversized task, proposes child
   tasks + Depends-On lines (`⛓️ DEPENDS ON:`), human accepts, children become
   individually launchable. Uses `bob task move` + dependency-line verbs; mirrors
   SASE epic/phase decomposition into the vault.
7. **Blocked-cause investigation.** On derived `[?]` (dependency, future schedule,
   project inheritance), agent proposes the unblock (draft the missing prereq,
   confirm the date, surface the blocking project state) instead of Bryan
   discovering it at review time.
8. **Stale-task triage.** Freshness buckets (NEW/ROTTEN) + open-lane scan →
   "reconfirm, reschedule, or cancel?" batched gate. Mirrors `bead_stale_cleanup`
   for the vault. High attention-value, zero autonomy risk (propose-only).
9. **Capture → bead for code tasks.** `bob capture` lines classified as
   code/sase-shaped auto-propose a mirrored bead with repo context, so `sase run`
   can pick up inbox work without Bryan re-filing it as a bead.
10. **Completion evidence as artifacts.** Every auto-run files its diff/report/log
    as an artifact ref linked from the vault note — converts "agent says done"
    into checkable proof and feeds the artifact-link lineage work already in tree.

### Tier 2 — agnostic payoffs (why system-agnostic matters)

11. **GitHub ↔ Obsidian unification.** Same bridge, two adapters: a GitHub issue
    and an Obsidian task describing the same work converge on one bead
    (`external_ref` on both), ending the "where did I track that?" split.
12. **Cross-system deduplication.** `capture-related`-style similarity + bead text
    search → "this inbox task duplicates issue #412" proposal. Works across any
    two adapters.
13. **Portable review queue.** One triage surface (gates) for proposals from all
    systems; adding Linear/Todoist later changes no core code.
14. **Personal → team escalation.** A vault task that outgrows personal scope
    becomes a GitHub issue (or bead epic) with history carried as notes — the
    bridge as a promotion path, not just a mirror.

### Explicit non-goals (v1)

- Bidirectional status sync with conflict auto-resolution (mirror + gated
  proposals only; last-writer-wins automation is how vaults get corrupted).
- Agent-owned lane transitions beyond claim (`[*]`), completion-note + `[/]`,
  and human-approved edits. No agent `Done`, no agent `Cancelled`, no agent
  archive — `bob task archive` stays human-invoked.
- New task grammar. Use `#task`, `@route`, `#q`, block IDs, Depends-On lines as
  they exist; govern the two new tags (`#sase`-family) in docs, not code.

## 5. Risks and mitigations (summary table)

| Risk | Mitigation |
|---|---|
| Vault corruption by mass writes | Scoped verbs, per-run caps, dry-run default, git revert path, read-only phase first |
| Launch loops on own output | Launched-by markers, bridge-write short-circuit, terminal-state guard, budget caps |
| Quota burn from unattended launch | Daily launch budget, quiet hours, confidence threshold, scheduler maintenance honor |
| Review nagware | Batched gates, snooze-by-default, per-system proposal budgets |
| Status-mapping fidelity loss | Documented lossy map; never extend either model in v1 |
| Tag-vocabulary sprawl | Govern `#sase`/`@sase` + `#q-agent` split in `docs/` + capture contract |
| Answering questions meant for Bryan | Opt-in routing for Q&A; per-note opt-out; provenance-stamped answers |
| Cross-system identity collisions | `external_ref` namespaced per adapter (`bob:<path>#<block>`, `gh:<n>`) |

## 6. Suggested phasing

- **Phase 0 (days): read-only.** `bob query`-backed `list_ready` + CLI report of
  "what would launch"; zero writes; calibrates the ready-classifier and earns
  trust. Ship the capability interface + Obsidian adapter skeleton.
- **Phase 1: propose-only.** `propose_edit` → batched gates; manual `sase run`
  from accepted proposals; completion notes pasted manually. Proves the review
  ergonomics before any autonomy.
- **Phase 2: gated auto-launch.** Scheduler routine + claim + `sase run` +
  artifact-backed completion note + `[/]` transition, under daily budget and
  human-touched-since guard. The flagship use case, live.
- **Phase 3: Q&A + decomposition + stale triage.** Same substrate, new prompt
  templates and poll queries. Research-swarm routing lands here.
- **Phase 4: second adapter (GitHub convergence).** Generalize `sync-external`
  into the bridge's GitHub adapter; cross-system dedup and escalation follow.

## 7. Open questions for the lead

1. Tag vocabulary: one tag (`#sase`) with sub-routes, or a family (`#sase-code`,
   `#sase-research`, `#sase-q`)? Who governs it — capture contract or docs page?
2. Should claim promote to `[*]` (visible commitment) or stay Ready until completion?
3. Is `[/]`-on-completion right, or should agent-completed tasks go to a distinct
   human-check state (freshness stamp, `@verify` route) instead of overloading
   Pending?
4. Per-day launch budget and quiet hours: what numbers earn unattended operation?
5. Q&A opt-in default: answer all `#q` or only `#q-agent`, and per-note opt-out?

## Sources inspected

- Live: `sase bead --help`, `bead sync-external --help`, `sase run/tool/gate/
  monitor/scheduler/axe job list --help`; `src/sase/{bead,axe,macros}/` listings.
- `bob --help`, `bob task --help`, `bob query --help` (installed `bob` binary).
- bob-cli checkout (via `sase repo open bob-cli`): `README.md`, `AGENTS.md`,
  `docs/concepts/{tasks-and-lanes,how-bob-fits-together}.md`,
  `docs/{task-tag-marks,task-status-hooks,highlights-ref-sync,ref}.md`.
- SASE memory: core instructions (beads/scheduler/gates/monitors) as rendered in
  this session's bundle; decisions/glossary webs consulted by descriptor only
  (no strand reads needed for this report's claims).

*Independence note: this report was written without locating, opening, or consulting
any peer swarm report (`__cdx/__cld/__grk/__gem`), per the brief.*
