# Goals Functionality for SASE: Research, Critique, and Recommended Design

Researcher: mus (independent swarm report; no peer reports consulted)

## 0. TL;DR

The "Goals" request is a good idea aimed at a real pain point (agent-completion
noise vs. "something is done and needs my verification"), but it should **not**
be built as a brand-new parallel entity system. SASE already has ~90% of the
machinery a goal needs: **beads** (typed, lifecycle-gated, evidence-bearing,
synced work items), **plan `goal` fields** (required, Rust-validated), **host
launch context** (`SASE_PLAN`, bead assignment, finalizer obligations),
**artifact links** (typed, closed-registry relations with projections), the
**notification inbox** (typed unread rows), and **finalizers** (explicit
`bead_action: close|keep` plus prepared monitor completion).

Recommended solution: implement **Goal as a thin profile over the existing
bead store** (new `task_type = goal`, or a `GOAL` issue type if core review
demands it), **bound at launch time by the host** (not by every agent
self-checking `SASE_PLAN` each turn), **closed through a goal-aware finalizer**
with structured evidence, **surfaced as a Goals deck/section on the existing
Agents tab** (not a fourth tab), and **notified as a distinct `goal-done`
inbox row** with an explicit verify step. Details and rationale below.

Proposed adjustments to the requirements (all called out in §5):

1. Model goals on beads; do not create a second store.
2. Bind goals at launch (host-owned), not via a per-turn agent `SASE_PLAN` check.
3. Soften "ALL agents MUST have a goal" with a narrow exemption list plus
   host-minted trivial auto-goals, instead of forcing every Q&A agent through a
   goal-creation skill.
4. Require structured, partly machine-checkable close evidence (not free text).
5. Put Goals in the Agents tab as a deck/section, not a new top-level tab.
6. Treat the `O(n)` active-goals requirement as an index/filter property, and
   satisfy "any machine" via the existing bead-sync path rather than a new
   distribution mechanism.

## 1. What the request is really asking for

Restated as a contract:

- (a) Every agent has exactly one active goal; plan-backed agents inherit the
  plan's `goal`; plan-less agents create or link one.
- (b) Goals remember the originating prompt.
- (c) Agents explicitly choose keep-open vs. close at end-of-turn, with evidence
  attached on close.
- (d) Users can browse all active goals per project and jump to linked agents
  and artifacts.
- (e) Goal completion (not agent completion) drives verify-me notifications.
- (f) Active-goal reads are fast (`O(n)` in active goals) from any machine.
- (g) The whole thing is intuitive, reliable, and beautiful.

Each of these maps onto an existing SASE subsystem. That mapping is the core
finding of this report: the cheapest reliable design is composition, not a new
subsystem.

## 2. What already exists (verified in this checkout)

### 2.1 Plans already have a required `goal` field

- `src/sase/sdd/plan_validate.py` defines the validated plan record with a
  required `goal: str`, for both `tale` and `epic` tiers. The authoritative
  schema lives in `sase-core` (Rust); the Python module only rehydrates binding
  payloads.
- The authoring skill (`src/sase/xprompts/skills/sase_plan.md`) walks planners
  through tier choice, file authoring, `sase plan validate`, and `sase plan
  propose`.
- Implication: requirement "use plan goals as agent goals" is a **projection**,
  not new data entry. The plan's `goal` string plus the plan's artifact identity
  (`plan:<path>`) is already durable and content-addressed through the plan
  archive.

### 2.2 The host already binds plan + bead context at launch

- `SASE_PLAN` is set by the host when attaching/accepting a plan
  (`src/sase/agent/_agent_session_attach_launch.py`,
  `src/sase/axe/run_agent_exec_plan_accept.py`) and deliberately cleared for
  fresh spawns (`src/sase/agent/launch_spawn.py`, `src/sase/axe/run_agent_exec_finalize.py`).
  Commits also tag `SASE_PLAN` (`src/sase/workflows/commit/*`).
- Finalizer context already carries assigned-bead and plan wires
  (`src/sase/finalizers/declaration.py`, `sase.core.finalizer_wire`), and the
  `/sase_final` skill already forces an explicit `bead_action: close|keep`
  decision inside prepared monitor completion.
- Implication: the natural home for goal binding is this same launch-time,
  host-owned channel. The host already decides which bead and which plan an
  agent works on; adding "which goal" there is a small extension of a trusted
  path, whereas asking every agent to self-diagnose goal-lessness each turn is a
  new unreliable path (see §4.2).

### 2.3 Beads are already goals with lifecycle, evidence, and sync

- `src/sase/bead/model.py`: `IssueType` (`PLAN`/`PHASE`/`TASK`), `Status`
  (`open`/`claimed`/`ready`/`snoozed`/`in_progress`/`closed`), `Resolution`
  (`done`/`canceled`/`superseded`), typed `BeadLink`s, append-only `BeadNote`
  log, and `TaskPlusOneEvidence` (timestamp + reporter + note + normalized
  artifact refs, validated).
- CLI evidence handlers exist (`src/sase/bead/cli_crud_evidence.py`: `+1` and
  `note` commands for attributed supplementary evidence); close/settle paths
  exist (`close_gate_settle.py`, close-history codec).
- Stores are per-project and locatable (`src/sase/bead/store_locator.py`:
  `canonical_beads_dir_for_project`, open/closed queries), with git-backed sync
  machinery (`sync.py`, `_sync_git.py`, outbox/publication). Cross-machine
  agent work is an active, supported concern in this repo (see the
  `agents_across_machines*` research threads under `sase/repos/research/`).
- TUI already renders bead touches and bead-hint targets
  (`src/sase/ace/tui/bead_touches*.py`, `bead_hint_targets.py`).
- Implication: a separate goals table would duplicate lifecycle states,
  close gates, evidence codecs, sync, and TUI affordances. A goal is, to first
  order, a bead whose success criterion is user verification.

### 2.4 Artifact links are a closed registry with projections

- `docs/artifact_links.md`: relations (`related`, `supersedes`, `implements`,
  `derives-from` writable; `cites`/`read` observational; `produced-by`,
  `launched`, `awaits` read-only projections). Direction matters; `blocks` /
  `depends-on` are deliberately reserved for `sase bead dep`.
- Agent reads already project `read` edges; stitches project `produced-by`;
  jobs project `launched`; wait relationships project `awaits`.
- Implication: goal↔agent and goal↔artifact navigation should be **new
  projected rows** (or one carefully added writable relation such as
  `pursues`), not ad-hoc fields. The "jump from Goals panel to any agent or
  artifact" requirement is then free: it reuses the existing link-follow,
  neighborhood, and suggest machinery.

### 2.5 Notifications already distinguish "needs attention" from raw completion

- `docs/notifications.md`: durable JSONL inbox, typed gate-backed rows, unread
  vs. dismissed views, per-tab mark-read with danger confirmation, remote
  attention inventory.
- The pain point in the request is real and well-diagnosed: agent-completion
  signals (and Agents-tab unread dots) fire for every agent, but the user only
  cares when an agent *claims a goal is complete*. That is a signal-separation
  problem, and the inbox already supports typed rows — so the fix is a new row
  type with verify semantics, not a new notification channel.
- TUI tab order is currently exactly three tabs
  (`src/sase/ace/tui/tab_order.py`: `("agents", "artifacts", "services")`).
  Adding a fourth top-level tab touches tab cycling, bindings, persistence of
  legacy tab ids, and every tab-scoped behavior. A section/deck inside Agents
  is an order of magnitude cheaper and keeps goal→agent jumps local.

### 2.6 Agent prompts are already recorded

- `src/sase/agents/` has `cli_prompts.py` / `cli_show.py` / `cli_list.py`;
  launch prompts are durable enough to display. So "associate the goal with the
  original prompt" does not need a new capture pipeline — it needs a pointer
  (agent id → launch prompt record) stored or projected at goal-creation time.

## 3. Is this a good idea?

**Yes, with the adjustments in §5.** The underlying judgment is correct:

- Agent completion ≠ goal completion. Collapsing them produces exactly the
  notification fatigue described.
- Forcing an explicit keep-open/close decision at end-of-turn converts silent
  drift ("agent ended, did it actually do the thing?") into an auditable claim.
- A per-project active-goal view is the missing user-level counterpart to the
  existing per-agent views.

The risks are also real and should shape the design:

- **Goal spam.** A hard "every agent, every turn" rule mints thousands of
  trivial goals ("answer question", "read file") that drown the Goals view and
  make `O(n)` meaningless because `n` explodes. The value is in *user-meaningful*
  goals; the design must keep trivial work cheap (auto-goals) while keeping the
  view filtered to what needs verification.
- **A second work-item system.** If goals duplicate beads, every future feature
  (snooze, triage, dependencies, cross-project queries, TUI affordances) must be
  built twice, and the two systems will drift. This is the single largest
  architectural risk in the request as written.
- **Agent self-enforcement.** Agents are the least reliable enforcement point
  (they vary by provider, can be interrupted, and optimize for finishing fast).
  Host-side binding and finalizer validation are reliable; agent-side checks are
  advisory.
- **Rust boundary.** Per `sase/memory/rust_core_backend_boundary.md` and the
  `rust-core-required` decision, shared behavior belongs in `sase-core` with no
  Python fallback, and binding changes require moving the
  `sase-core-revision.txt` pin. A brand-new core entity (new tables, new sync
  protocol) is therefore a multi-repo project; a bead-profile design keeps
  phase 1 largely Python-side with a small core review.

## 4. Critique of the specific proposal

### 4.1 "Associate goals with original prompts" — agree, via pointer not copy

Storing the full prompt text on the goal duplicates the launch record and rots
when prompts are long or contain attachments. Store a stable pointer instead:
`origin_prompt_ref` → the agent's launch-prompt record (plus the launching
agent/human identity and timestamp). The Goals view can expand it on demand
through the existing prompt-display path. Copying the text is acceptable only as
a denormalized preview (first ~240 chars) for list rendering.

### 4.2 "Every agent checks SASE_PLAN at the start of EVERY conversation" — don't do this

This is the weakest part of the proposal. Concretely:

- It runs on the agent's dime (tokens, latency) on every turn, including pure
  Q&A, read-only probes, monitors, and nested helpers.
- It inverts the trust boundary: the host knows the launch context with
  certainty; the agent must infer it from one env var that is legitimately
  unset in many flows (fresh spawns pop it; commit/finalize paths clear it).
- It forks behavior by provider and prompt: some agents will skip the check,
  some will loop on it, some will mint duplicate goals for the same work.
- Planner agents are already exempted in the proposal, which concedes the
  point: exemptions multiply (monitors, replanners, `with_feedback` children,
  sudo-gated helpers), and each exemption is another branch agents must get right.

Better: **the launcher assigns the goal the way it already assigns the bead
and the plan.** The agent receives `SASE_GOAL` (or a goal block inside the
finalizer context) the same way it receives `SASE_PLAN`. The `/sase_new_goal`
skill becomes a *fallback* for genuinely unbound sessions (e.g. a human
directly chatting with no launch context), not the primary path. Enforcement
moves to `sase final submit` validation: no goal binding + no exemption ⇒ the
submission is rejected with a repair hint, exactly like stale-context and
missing-repository-decision failures today.

### 4.3 "Require create-or-link for all plan-less agents" — agree, with auto-goal escape hatch

The create-or-link instinct is right (reuse > proliferation), but "ideally link
to an existing active goal" needs tooling to be real: link search must be
one command (`sase goal list --active`, fuzzy match on title) with `O(active)`
cost, or agents will always create. And for trivial sessions, even one
skill invocation is too much: the host should mint a lightweight auto-goal
(`Answer user question: <first line of prompt>`, kind `trivial`) at launch
when the launcher classifies the session as Q&A. The agent then just completes
it. This preserves the invariant (every agent has a goal) without taxing every
"what does this flag do?" exchange.

### 4.4 "Close evidence linked to the goal" — agree, but define evidence strictly

"Provide evidence" is too vague to enforce. Free-text "I tested it" fields
become rubber stamps within a week. Evidence for goal-close should be a small
structured manifest (mirroring the existing `TaskPlusOneEvidence` shape:
timestamp + reporter + note + normalized refs) with at least:

1. **Verification pointer (machine-checkable, required for code goals):** the
   command that proves the claim (`just check`, a named test, a build) plus its
   result (exit code / summary), or a durable ref to the monitor run that went
   green. Prepared monitor completion (`sase final prepare` + `verify` monitor)
   already produces exactly this artifact — goal-close should accept a verify
   ref directly.
2. **Artifact refs (required):** ≥1 normalized artifact reference (commit /
   stitch / bead / file / plan) the verifier can open. Reuse
   `normalize_artifact_ref_list` semantics so refs stay deduplicated and
   followable.
3. **Claim summary (required, short):** one line (≤240 chars, matching the
   artifact-link `why` convention) stating what "done" means, so the Goals view
   and the notification render without opening the full record.
4. **Human verify step (for user-facing goals):** closing proposes; a
   `goal-done` inbox row disposes (verified / rejected → reopen). Agent close
   without user verify should mark `done-pending-verification`, not final,
   for goals flagged `needs_human_verify` (the default for plan-backed work).

What evidence should *not* be: screenshots-by-default, full log dumps inline
(link them), or provider self-attestation alone.

### 4.5 "Goals panel with artifact-link jumps" — agree on function, not on placement

A browsable active-goals surface with one-key jumps to linked agents/artifacts
is clearly right, and artifact links are the right jump mechanism (they already
encode followability, neighborhoods, and suggestions). But a fourth top-level
tab is the most expensive placement: it disturbs `TAB_ORDER`, tab cycling,
persisted tab state, and tab-scoped notification behavior. The Agents tab
already owns agent rows, decks/cards, bead touches, and completion affordances
— a **Goals deck (or section) at the top of Agents**, reusing deck/card
rendering and the existing link-follow keys, delivers the navigation with a
fraction of the blast radius. Graduate to a tab only if the deck proves
cramped after real use.

### 4.6 Notifications motivation — the strongest part; sharpen it

Replacing "every completion pings me" with "only claimed goal completions ping
me" is the highest-value sentence in the request. Two refinements:

- The notify-on-close event should fire on **claim of done** (agent's goal
  finalizer says close + evidence accepted), not on final verified state —
  otherwise the user is never woken to do the verifying.
- Verification must be an explicit inbox action (verify / reject-reopen), and
  bulk-mark-read must be safe: goal-done rows should behave like other
  gate-backed rows (confirm before dismiss), so `R` cannot silently eat a
  verify request.

### 4.7 "Lightning fast, O(n) in active goals" — restate as an index property

`O(active)` is the right target but it is almost free given the data model:
`status != closed` filtering over an indexed store is inherently independent
of done-goal count, provided done goals are excluded by index rather than
scanned. The real performance questions are elsewhere: (a) cross-machine
freshness (sync lag dominates read cost — reuse bead sync; do not build a
second sync), (b) TUI render cost when active goals number in the hundreds
(page the deck, reuse the existing paged-deck work), and (c) agent link/search
cost at session start (one indexed query, cached per project). State the
requirement as: "listing active goals never reads closed-goal bodies; p95
local list <100ms at 1k active goals; cross-machine staleness bounded by the
existing bead-sync interval."

## 5. Adjustments to the requirements (explicit list)

| # | Original | Adjusted | Why |
|---|----------|----------|-----|
| A1 | New Goals entity/store | Goal = bead profile (`task_type: goal`, possibly promoted to `IssueType.GOAL` later) | No second lifecycle/sync/TUI stack; inherits close gates, evidence codecs, artifact links, notifications |
| A2 | Agent checks `SASE_PLAN` every turn; invokes `/sase_new_goal` | Host binds goal at launch (`SASE_GOAL` + finalizer context); skill is fallback only | Reliable enforcement point; no per-turn agent tax; matches existing `SASE_PLAN`/bead binding |
| A3 | ALL agents MUST have a goal, no exceptions | Invariant kept, but: exempt mechanical roles (monitors, replanners, pure probes) via launcher-set exemption, and auto-mint `trivial` goals for Q&A | Prevents goal spam that would destroy the view's value |
| A4 | Evidence TBD | Structured manifest: verification pointer + artifact refs + one-line claim; human-verify flag defaults on for plan-backed goals | Rubber-stamp "evidence" is worse than none; machine-checkable pointers compose with `verify` monitors |
| A5 | New "Goals" TUI panel/tab | Goals deck/section on Agents tab reusing deck/card + link-follow | Avoids `TAB_ORDER`/cycling/persistence churn; keeps goal→agent jumps local |
| A6 | `O(n)` + any-machine access | Index-excludes-closed + reuse bead sync; quantify p95/staleness | The formula as stated is trivially satisfiable and under-specifies the real constraints |
| A7 | (implied new relation needs) | Add one relation if needed (`pursues`: agent→goal), project the rest | Keeps the closed registry closed; jumps reuse neighborhood/suggest |

## 6. Recommended solution

### 6.1 Data model: goal-backed beads

Phase 1 (Python-side, no core migration):

- New reserved `task_type` slug `goal` in the task-type catalog (alongside
  `bug`/`ci`/`feature`/`flake`/`memory`), with fields:
  `title`, `kind` (`plan-derived` | `linked` | `created` | `trivial-auto`),
  `origin` (`agent_id`, `prompt_ref`, `plan_ref?`, `created_by`, `created_at`),
  `needs_human_verify` (bool, default true except `trivial-auto`),
  `status`/`resolution` inherited from bead lifecycle,
  `close_evidence` (structured manifest per §4.4, stored as validated note/evidence rows).
- Plan-backed agents don't mint a bead at all when the plan already has one:
  the plan's `goal` string + `plan:<ref>` identity *is* the goal, projected as a
  goal row. Only plan-less agents get goal beads. This keeps `n` small and
  truthful.
- Phase 2 (if warranted): promote to `IssueType.GOAL` in `sase-core` with the
  `sase-core-revision.txt` pin moved accordingly, per the Rust boundary rule.
  Do not start here.

Why beads and not JSONL: sync, close gates, `+1`/note evidence, `sase bead
dep` ordering, touched/read tracking, and TUI bead affordances all come free,
and the "any machine" requirement rides the bead-sync path that
multi-machine support already maintains.

### 6.2 Binding: host-owned, launch-time

- Launcher (`launch_spawn`, axe exec paths) resolves goal in order:
  1. plan attached → goal = plan projection;
  2. explicit `--goal` / handoff payload → link existing;
  3. fuzzy match flag (`--goal-match`) → agent-suggested link, host-confirmed;
  4. else mint (or for Q&A, auto-mint `trivial`).
- Agent environment gains `SASE_GOAL` (goal ref) mirroring `SASE_PLAN`; the
  finalizer context gains a goal obligation block. `sase final submit`
  validates: bound goal or recorded exemption, else fail-closed with a repair
  hint pointing at `sase goal link|create`.
- `/sase_new_goal` skill exists but is documented as the fallback path
  (direct human chat with no launch context), titled accordingly so agents
  don't reach for it when the host already bound them.

### 6.3 Completion: goal-aware finalizer

- Extend the declaration manifest with `goal_action: keep | close` (mirroring
  `bead_action`) plus `goal_evidence` (the §4.4 manifest). Prepared-monitor
  completion accepts a verify-monitor ref as the verification pointer, so the
  common "tests went green, close the goal" flow is one ref, not a form.
- Agent `close` on a `needs_human_verify` goal transitions to
  `done-pending-verification` and emits a `goal-done` inbox row; only the
  user's verify action (or an exempt auto-verify for `trivial`) reaches
  terminal `closed/done`. Reject reopens with a note containing the reason.
- Evidence rows are linked into the artifact graph (goal `implements`/`cites`
  the verification artifacts), so the Goals view "why is this done?" jump
  works through standard link-follow.

### 6.4 Reads: active-goal index

- `sase goal list --active` (and the TUI provider behind the deck) reads only
  the open-status index; closed-goal bodies are never opened. This is the
  `O(active)` guarantee, stated as code, not aspiration.
- Agent link/search path is one indexed query at session start (host-side,
  cached per project refresh), not a per-turn agent scan.
- Cross-machine: no new transport. Goal rows are bead rows; freshness follows
  bead sync. Document the staleness bound instead of promising "lightning"
  without a number.

### 6.5 TUI: Goals deck on Agents

- A Goals deck/section atop the Agents tab: one card per active goal
  (title, kind chip, linked-agent count, verify-state), expanding to linked
  agents and artifacts via existing link-follow keys. Reuse deck/card/paging
  components (and the recent paged-deck UX work) rather than inventing goal
  widgets.
- Jump behavior: goal card → agent row (same tab), goal card → artifact
  (Artifacts tab / pager), goal evidence → verification artifact. All through
  artifact-link neighborhoods, so `suggest` keeps working.
- Beauty notes (cheap, high-leverage): stable goal short-ids for spoken
  reference ("goal a3f"), one-line claim as the card subtitle, verify-state as
  color (not text), and an empty-state that teaches ("No active goals — launch
  something or press … to mint one") rather than an empty box.

### 6.6 Notifications: `goal-done` rows replace completion-watching

- New inbox row type `goal-done`: goal title + one-line claim + evidence links,
  actions verify / reject-reopen / open-goal. Gate-backed (confirm before
  dismiss), exemption-aware (`trivial-auto` goals never notify).
- Explicitly bless the migration: users who currently watch completions switch
  to watching `goal-done`; agent-completion signals stay but are reclassified
  as low-priority (no unread dot by default) once goals ship, so attention
  actually moves.
- Remote attention inventory includes `goal-done` rows with owning-machine
  labels, same as other gate rows.

### 6.7 Rollout sketch

1. Goal bead type + `sase goal {create,link,list,show}` CLI + `SASE_GOAL`
   launch plumbing + finalizer validation (fail-closed) — all behind existing
   patterns; no TUI yet (CLI list proves the index).
2. `goal_evidence` manifest + `goal-done` inbox rows + verify/reopen actions.
3. Goals deck on Agents reusing link-follow; paging; empty-state copy.
4. Measure: active-list p95, sync staleness, goal-spam rate (`trivial` share),
   verify latency; promote to core `IssueType` only if the profile chafes.
5. Flip completion signals to low-priority once `goal-done` proves sufficient.

## 7. Open questions for the lead

- Should `trivial-auto` goals appear in the Goals deck at all, or only in a
  "show trivial" toggle (default off)? I recommend default-off.
- Should one agent ever hold two active goals (e.g. epic phase + emergent
  sub-goal)? I recommend exactly-one primary goal with additional goals
  reachable via links, to keep the finalizer decision unambiguous.
- Should rejecting verification reopen the goal bead, the underlying plan bead,
  or both? I recommend goal-only by default, with a one-key "also reopen plan
  bead" action.
- New relation slug: is `pursues` (agent→goal) worth adding to the closed
  registry, or is projected `implements` sufficient? I lean to one explicit
  slug for query clarity, pending registry-owner review.

## 8. Sources consulted (this checkout; peer reports explicitly not consulted)

- `src/sase/sdd/plan_validate.py` — required plan `goal`, Rust-backed validation.
- `src/sase/xprompts/skills/sase_plan.md`, `sase_final.md` — plan authoring;
  finalizer declaration + prepared monitor completion + `bead_action`.
- `src/sase/agent/_agent_session_attach_launch.py`,
  `src/sase/agent/launch_spawn.py`, `src/sase/axe/run_agent_exec_plan_accept.py`,
  `src/sase/axe/run_agent_exec_finalize.py` — `SASE_PLAN` lifecycle.
- `src/sase/bead/model.py`, `cli_crud_evidence.py`, `store_locator.py`,
  `close_gate_settle.py` — bead types, status/resolution, evidence, stores.
- `docs/artifact_links.md`, `docs/notifications.md` — closed relation
  registry + projections; typed inbox, unread/dismissed, remote attention.
- `src/sase/ace/tui/tab_order.py` — three-tab order (Agents/Artifacts/Services).
- `src/sase/finalizers/declaration.py`, `catalog.py` — finalizer context,
  submission, provider catalog.
- `src/sase/agents/cli_prompts.py` et al. — launch-prompt records.
- `sase/memory/rust_core_backend_boundary.md` (via AGENTS.md reference) and
  `sase-core-revision.txt` — Rust-first boundary and pin mechanics.

---

*Report ends. Recommendation: build Goals as a bead profile with host-owned
binding, structured close evidence, a Goals deck on Agents, and `goal-done`
verify notifications — not as a new entity system with per-turn agent
self-checks.*
