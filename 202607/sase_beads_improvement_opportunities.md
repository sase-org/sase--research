---
create_time: 2026-07-14
updated_time: 2026-07-14
status: research
---

# SASE Beads — Improvement Opportunities

## Research Question

Bryan suspects SASE beads are not being used to their full potential and wants the *most impactful,
practical* improvements to consider. Steve Yegge's `beads` (`bd`) project is used as an inspiration
input — but deliberately as a *foil*, since it has a documented tendency toward over-complexity. This
note maps how SASE beads are actually built and used today, extracts the small number of genuinely
transferable ideas from `bd`'s evolution (and flags the complexity to avoid), and ends with a ranked
set of recommendations.

Sources: direct reads of the bead subsystem (`src/sase/bead/**`, the Rust `sase_core` bead module),
live inspection of the current bead store (`sase bead stats`/`list`/help), git history (146 commits
under `src/sase/bead/`, ~1433 commits mentioning "bead"), and six prior research notes in this repo
(§ Relationship to Prior Research). External `bd` material is cited under Sources.

## The One-Sentence Finding

**SASE built the *execution-engine* half of a bead system extremely well and never built the
*living-memory* half — so beads are a write-once completed-work ledger, not a durable, cross-session
record of pending and discovered work.** The highest-leverage improvements close that gap without
importing `bd`'s complexity.

The evidence is stark: the store holds **1,479 beads, of which 0 are open and 0 are in progress —
every single bead is closed** (`sase bead stats`). Beads are created *and* closed inside one
`sase bead work` epic-launch cycle. Meanwhile ~87% of all planned work (2,325 of 2,668 plan files are
`tier: tale`) never touches beads at all. Nothing pending, nothing discovered, nothing triaged ever
lives in beads.

## Current Baseline — What SASE Beads Actually Is

SASE beads is a **git-native, event-sourced, Rust-backed epic→phase execution tracker**, tightly
coupled to the SDD plan/`sase bead work` pipeline. It is a deliberately *minimal* reimplementation
built to shed the external `bd` Go binary (`202603/sase_beads.md`).

**Data model** (`src/sase/bead/model.py:9-75`; Rust `sase_core/src/bead/wire.rs`):

- Statuses: `open` / `in_progress` / `closed` (`model.py:9-13`).
- Types: only `plan` and `phase` (`model.py:15-17`). There is **no lightweight/standalone bead type**
  (no task/bug/note). `create` *requires* `--type plan(<file>)` or `phase(<parent>)`
  (`src/sase/bead/cli_crud.py`, `create` handler) — every bead must be anchored to a plan file or a
  parent plan bead.
- Tier: `plan` / `epic`, on plan beads only (`model.py:20-23`). Only `epic`-tier plan beads are
  runnable by `sase bead work`.
- Dependencies: a single, untyped, one-way "A depends on B" edge (`model.py:25-30`; Rust
  `mutation.rs add_dependency`). There is **no link taxonomy** — no `related`, no `discovered-from`;
  parent/child is structural (`parent_id`), not a dependency kind. `dep` has only `add` — **no
  `dep rm`, no `dep list`**.
- Fields: `id, title, status, issue_type, tier, parent_id, owner, assignee, created_at, created_by,
  updated_at, closed_at, close_reason, description, notes, design, model, is_ready_to_work,
  changespec_name, changespec_bug_id, dependencies`. **No priority, no labels/tags.** `notes` is a
  single last-write-wins string, not an append-only thread.

**Storage.** Canonical state is an append-only event log — one stream per root plan under
`beads/events/streams/<root>.jsonl`, reduced to a generated `issues.jsonl` compatibility projection
(9 event operations, Rust `sase_core/src/bead/events.rs`; "inspired by Fossil", `docs/beads.md`). In
this project the store lives in the `--plans` sidecar (`sase/repos/plans/beads`, split-sidecar mode);
`beads.db` SQLite is a gitignored local cache only. This event-sourced design was itself the product
of prior research (`202605/greenfield_bead_storage_architecture.md`) and resolved the earlier JSONL
merge-conflict pain (`202605/bead_jsonl_merge_conflicts.md`).

**Rust vs Python.** The domain lives in Rust (`sase_core/src/bead/{wire,events,mutation,read,work,
search,cli}.rs`); Python is a thin host (CLI parsing, store resolution, VCS/agent orchestration,
telemetry) calling through `sase_core_rs` facades (`src/sase/core/bead_*_facade.py`). **Any data-model
change (a new type, a link kind, a standalone bead) crosses the Rust core boundary** — wire/events/
mutation/read in `sase-core` plus the Python facades and CLI here. That is the real cost multiplier
for several recommendations below, and it is the correct boundary per the repo's core-backend rule.

**CLI surface** (richer than the `/sase_beads` skill documents): `init, create, update, open, close,
rm, list, show, search, ready, blocked, stats, dep add, sync, doctor, onboard, resolve-conflicts,
work`. Only `search --format json` emits machine-readable output; `list`/`show`/`ready`/`stats` are
human-text only.

**`sase bead work`** (`src/sase/bead/cli_work_handler.py`, `work.py`) is the mature centerpiece: it
validates an epic-tier plan bead, Kahn-layers its phase dependency DAG into waves, renders a
`---`-separated multi-agent prompt (one segment per phase + a land agent), preclaims phases, and
launches detached agents. This is what beads are really *for* today.

**How the store is actually used** (analysis of all 1,479 records):

- **Everything is an epic.** 214 plans (212 epic-tier) + 1,265 phases; each epic owns a mostly-linear
  chain of ~6 phases.
- **`notes` is a commit ledger.** 1,043 of 1,149 non-empty notes begin with `COMMIT:` — the phase→git
  SHA audit trail. Epic beads' own description/notes are usually empty; the narrative lives in the
  linked plan `.md` (`design`).
- **Dependencies are linear.** The wave scheduler supports arbitrary DAGs, but real epics almost
  always use `phase N → N-1` chains.
- **Assignee is auto-managed** (self-id written by `preclaim`), not a human/agent assignment.
- **ChangeSpec linkage is unused** here (`changespec_name`/`changespec_bug_id` = 0/1,479).
- **The manual "claim → work → close" loop the skill documents is effectively dead** — superseded by
  `sase bead work` automation. `ready`/`blocked` and the open/in_progress statuses are transient.

**TUI.** There is **no beads tab** (tabs are `changespecs`, `agents`, `axe` — `src/sase/ace/tui/app.py:77`).
Beads appear only as decoration on running-agent rows (`src/sase/ace/tui/models/agent_bead.py`). You
cannot see, browse, or triage the backlog from the TUI. A designed-but-unbuilt proposal exists
(`202605/axe_open_bead_tree.md`).

## How Steve Yegge's `beads` Evolved — And What To Learn vs Avoid

`bd` markets itself as "a memory upgrade for your coding agent": persistent, dependency-aware,
cross-session memory so agents "handle long-horizon tasks without losing context." Its core thesis is
that **LLMs notice problems as they work but fail to act on them** — beads exist to capture that
discovered work.

**The architecture trajectory is a cautionary tale, not a roadmap.** `bd` began exactly where SASE is
now — git-native JSONL as the source of truth with SQLite as a local read cache (the Fossil pattern).
It then migrated to a Dolt (git-for-databases SQL) backend, removed the embedded mode, and in v1.0
**removed the entire JSONL sync system**, leaving Dolt-native push/pull as the only sync path. This
generated real community pain (multiple third-party SQLite→Dolt migration guides, GitHub issues where
`bd migrate` corrupts or empties data). Steve himself describes it as "a crummy architecture (by
pre-AI standards) that *requires* AI" to manage the edge cases.

**The lesson for SASE is a strong negative signal.** SASE's current event-sourced-JSONL + Rust-core
model *is* `bd`'s original, well-loved, low-complexity design — and SASE already solved the merge
problem the git-native model has (event streams + `resolve-conflicts`). Chasing `bd`'s newer
Dolt/server/daemon direction would re-introduce exactly the over-complexity Bryan flagged, for
problems SASE does not have. **Do not follow `bd`'s storage evolution.**

**The genuinely transferable ideas from `bd` are small and cheap:**

1. **`discovered-from` dependency links.** `bd` has four link types (`blocks`, `parent-child`,
   `related`, `discovered-from`); every independent practitioner singles out `discovered-from` as the
   killer feature — *"when your agent is fixing a bug and notices a memory leak in an unrelated
   service, it files it as `discovered-from:bd-abc123`… now tracked, linked to discovery context."*
2. **A trivially cheap capture verb + the discipline to use it.** `bd`'s #1 documented friction is
   that **agents don't proactively file** — "you provide the discipline." Their best practice: file a
   bead for any work taking more than ~2 minutes, and nudge the agent to do so.
3. **Machine-readable `ready --json`** for a programmatic ready→claim→work→close→discover loop.
4. **Keep it out of scope.** `bd`'s own docs are emphatic: no UI, no planning system, no
   orchestration in the tracker; and keep the working set small (they cleanup below ~200–500 issues,
   because agents grep the JSONL and it "fails past ~25k tokens").

Everything else `bd` has (Dolt, daemon, federation, message/threading, molecules, gates, wisps,
`prime`/`remember` memory, 80-field schema, numeric priority levels) SASE already deliberately
rejected in `202603/sase_beads.md`, and that judgment still holds.

## The Core Gap

`bd` and SASE beads have diverged into two different tools:

| | Steve Yegge `bd` | SASE beads |
|---|---|---|
| Primary role | Living memory of **pending & discovered** work | Deterministic **epic→phase execution + commit ledger** |
| Typical state | Backlog of open/ready items | 0 open / 0 in-progress / 1,479 closed |
| Capture cost | `bd create "…" -t bug` (one line, no plan) | Requires a plan file or parent plan bead |
| Discovered work | First-class (`discovered-from`) | No place to put it |
| Coverage of work | Broad (any task) | Epics only; 87% of work (tales) excluded |

SASE nailed the half `bd` is weakest at (deterministic multi-agent execution, wave scheduling,
event-sourced provenance to commits). It captures ~none of the half `bd` is *for* (durable memory of
what still needs doing). "Not using beads to their full potential" is precisely this: **beads are a
completed-work archive, not a worklist.**

---

## Recommendations (Most Impactful First)

### Tier 1 — Highest impact: make beads a living memory of discovered work

**R1. Add a lightweight standalone bead (a `task`/`note` type with no required plan file), plus a
`discovered-from` link.**
This is the single highest-leverage change. Today an agent that notices a bug, a TODO, or follow-up
work mid-task has **nowhere to put it** — the `--type plan(...)`/`phase(...)` requirement forces a
plan file, so the work is lost (hence 0 open beads and a notes field that only ever records commits).
Allowing a standalone bead — `sase bead create -t "Token expiry is 1h not 24h" --type task` with
`parent_id = None` — plus a `discovered-from` dependency kind that records *which* bead/plan surfaced
it, unlocks the actual "coding-agent memory" value.

- *Why it's the right one:* it targets the proven gap (discovered work is uncaptured), it is the one
  `bd` idea every practitioner praises, and it stays inside SASE's minimal philosophy (one new type,
  one link kind — not a new backend).
- *Cost / where:* crosses the Rust core boundary. Add the type + a `kind` on `Dependency`
  (`sase_core/src/bead/{wire,events,mutation}.rs` — `DependencyAdded` payload, validation in
  `wire.rs`/`model.py:57-75`), relax the phase/plan-only invariants for standalone beads, thread it
  through `src/sase/core/bead_*_facade.py` and `cli_crud.py`/`parser_bead.py`. Medium effort,
  low conceptual risk.
- *Guardrail:* bead descriptions are already treated as untrusted agent-generated content
  (`CLAUDE.md`, prompt-injection rule). Standalone beads filed by agents must inherit that same
  untrusted status — do not let a discovered-work bead become an authorization channel.

**R2. Give capture near-zero ceremony, and make filing discovered work a standard agent habit.**
Tooling without discipline does nothing — this is `bd`'s #1 friction and SASE's 0-open-beads is the
same failure. Two moves that reinforce R1:

- A two-word capture verb, e.g. `sase bead note "<title>"` (thin sugar over R1's standalone create,
  defaulting `discovered-from` to the current `SASE_BEAD_ID`/plan when one is in scope). Ergonomics
  matter: agents file what is trivial to file.
- Bake "**file a standalone bead for any discovered follow-up work worth >~a couple minutes, linked
  `discovered-from` the current work**" into the standard agent instructions — specifically the
  land-agent xprompt (`land_epic`) and the phase-work xprompt (`work_phase_bead`), and/or a
  post-run hook, so it fires at exactly the moment agents currently drop discovered work on the floor.
- *Cost / where:* mostly prompt/workflow, not code — `src/sase/bead/xprompts.py` tag resolution +
  the xprompt bodies + `src/sase/xprompts/skills/sase_beads.md`. Low effort, high leverage, and it is
  the change most likely to actually move the 0-open-beads number.

**R3. Surface the open-bead backlog in the ACE TUI (build the already-designed AXE bead tree).**
A living backlog is worthless if the human never sees it. Today beads are invisible except as
per-running-agent decoration. `202605/axe_open_bead_tree.md` already specs a tree of all open beads
across projects on the AXE tab, with `sase bead show`-equivalent detail in the side panel, respecting
the existing "navigation does no disk reads" invariant. Building it closes the loop
capture → **visible** → triage → `sase bead work`/close, and it is the natural payoff once R1/R2 start
producing open beads.

- *Cost / where:* Python/TUI only (presentation layer — stays this side of the core boundary):
  `src/sase/ace/tui/actions/axe_display/*`, `widgets/bgcmd_list.py` (already renders nested trees).
  Medium effort; design already exists.

### Tier 2 — Worth doing: make the loop programmable and coherent

**R4. Add `--json` to `ready`, `show`, and `list`.**
A discovered-work memory is most valuable when agents and the TUI can drive it programmatically
(ready → claim → work → discover → close). Only `search` emits JSON today (`cli_query.py`). This is a
small, self-contained addition (the Rust `read.rs` already produces the structured data; it just
needs a JSON renderer path) and it is a prerequisite for R3 and for any future automation/hook that
reasons over the backlog.

**R5. Decide, explicitly, whether tales should ever produce a bead.**
87% of planned work (tales) never touches beads, by design. That is largely fine — but it means the
backlog can never be a *complete* picture of outstanding work. Once R1 exists, revisit whether
tale-scale discovered work and important tale follow-ups should be recordable as standalone beads
(they now can be, cheaply). Recommendation: don't force ceremony on tales, but *allow* their
discovered work to land in the same shared worklist via R1. This is a policy/prompt decision, not new
plumbing.

**R6. Small `dep` ergonomics: `dep rm` and `dep list`.**
`dep` is add-only; removing a mistaken dependency currently means editing state directly. With typed
links from R1 in play, add `dep rm` and `dep list` (and let `dep add` take an optional `--kind`).
Minor, but removes a real papercut and rounds out the link model.

### Tier 3 — Watch, don't build yet

**R7. Retention/compaction of closed streams — monitor, defer.**
1,479 closed beads, unbounded event streams, and a 1.2 MB / 1,479-line `issues.jsonl` projection that
agents may grep. This is **not a problem today** because the working set (open beads) is ~0, but if
R1/R2 succeed and a real living backlog accumulates, the projection is what will bloat first. `bd`
cleans up below ~500 issues for exactly this reason, and SASE's own
`202605/greenfield_bead_storage_architecture.md` already specs compaction cadence. Recommendation:
add a size/token check to `sase bead doctor` now (cheap early-warning), and only build a
`sase bead compact`/retention command if the projection approaches ~25k tokens in practice.

### Anti-Recommendations (things the research says *not* to do)

- **Do not adopt Dolt / a versioned-SQL or server/daemon backend.** It is the exact over-complexity
  Bryan flagged, it caused real pain in `bd`'s own community, even its author calls it "crummy," and
  SASE already solved the merge problem it was meant to fix. SASE's event-sourced model is `bd`'s
  *original, better* design.
- **Do not add numeric priority levels, message/threading, molecules, gates, wisps, federation, or a
  `prime`/`remember` memory layer.** Priority was deliberately dropped (`202603/sase_beads.md`) and
  ordering-by-dependency is sufficient; the rest are `bd` features SASE consciously shed. SASE already
  has its own memory system.
- **Do not build full CRUD bead editing in the TUI.** A read/triage tree (R3) is enough; editing stays
  in the CLI.

## Relationship to Prior Research

This note builds on, and does not repeat, existing beads research in this repo:

- `202603/sase_beads.md` — origin: why SASE replaced the 37 MB `bd` Go binary with a lean model, and
  the deliberate decision to drop priority/extra types/compaction. **Still authoritative; R1–R7
  respect it.**
- `202605/greenfield_bead_storage_architecture.md` — the event-sourced storage design that was
  adopted. Already covers compaction cadence (feeds R7).
- `202605/bead_jsonl_merge_conflicts.md` — the merge pain the event store resolved. Reinforces the
  "don't chase Dolt" anti-recommendation.
- `202605/axe_open_bead_tree.md` — the designed-but-unbuilt TUI bead tree (this is R3).
- `202606/sase_bead_work_latency_consolidated.md` — `sase bead work` latency follow-ups (serial
  launch, blocking push, dry-run scanning ~18.5k files). Orthogonal to this note but the highest-value
  *execution-side* work if that path is the priority instead.
- `202606/epic_bead_work_pr_migration_consolidated.md` — the ChangeSpec/PR-attached epic direction
  (the `changespec_*` fields, currently 0/1,479 populated).

## Bottom Line

If you do only one thing: **R1 + R2** — a lightweight standalone bead with a `discovered-from` link
and a one-line capture verb wired into the standard agent prompts. That is the smallest change that
converts beads from a completed-work archive into the living, cross-session memory they were always
meant to be, and it is the one idea worth borrowing from `bd` without borrowing its complexity. **R3**
(the AXE bead tree) is the natural next step to make that memory visible and triageable; **R4** makes
it programmable. Everything past that is polish — and the loudest lesson from `bd`'s own history is to
stop there.

## Sources

- Steve Yegge, "Introducing Beads: A coding agent memory system" — https://steve-yegge.medium.com/introducing-beads-a-coding-agent-memory-system-637d7d92514a
- Steve Yegge, "Beads Best Practices" — https://steve-yegge.medium.com/beads-best-practices-2db636b9760c
- beads README — https://github.com/steveyegge/beads/blob/main/README.md
- beads CHANGELOG (SQLite→Dolt trajectory) — https://github.com/steveyegge/beads/blob/main/CHANGELOG.md
- Independent practitioner review (ianbull) — https://ianbull.com/posts/beads/
- Better Stack, "Beads: A Git-Friendly Issue Tracker for AI Coding Agents" — https://betterstack.com/community/guides/ai/beads-issue-tracker-ai-agents/
- Community SQLite→Dolt migration guide (evidence of migration pain) — https://gist.github.com/leonletto/606e8afbb3603870d14b4123707416a2
- Internal: `src/sase/bead/**`, `sase_core/src/bead/**`, live `sase bead stats`/`list`, and the six prior research notes listed above.
