# SASE Beads: Getting To Full Potential (Consolidated)

Date: 2026-07-14

Consolidates two independent research reports plus lead-researcher verification:

- `sase_beads_full_potential_consolidated__a.md` (codex researcher) — integrity-first analysis of the live store and
  upstream Beads' release history.
- `sase_beads_full_potential_consolidated__b.md` (claude researcher) — capture-gap analysis grounded in the
  implementation, git history, and six prior in-repo research notes.

Every load-bearing number below was independently re-verified against the live store and CLI on 2026-07-14 by the lead
researcher. Where the two reports disagreed, the resolution is stated explicitly (§ Conflict Resolutions).

## Headline Diagnosis

The two researchers converged on the same baseline from different directions, and both halves are needed to explain the
"not using beads to their full potential" feeling:

1. **Beads are a completed-work ledger, not a living memory.** The store holds **1,479 beads: 0 open, 0 in progress,
   1,479 closed**. Beads are created and closed inside a single `sase bead work` epic cycle, and ~87% of planned work
   (tales — 2,325 of ~2,668 plan files) never touches beads at all. Discovered follow-up work has literally nowhere to
   go: `sase bead create` hard-requires `--type plan(<file>)` or `phase(<parent>)`, so there is no standalone
   task/note bead and no `discovered-from` link.
2. **The ledger you do have is quietly untrustworthy.** Only **8 of 228** stored `design` plan links resolve as
   written (136 of 138 absolute paths are dead; 84 of 90 relative paths use retired layouts). Cascade close permits
   factually wrong completion: `sase-5t` and `sase-5t.5` are `closed` while their notes say, verbatim, *"Keep this
   epic open until these uncommitted recovery edits have a durable SASE commit."* And the event store retains rich
   handoff history — **1,115 note-update events across 571 issues** (404 with multiple revisions) — that no CLI
   surface exposes, because the `COMMIT: <sha>` hook overwrites the mutable `notes` field last-write-wins.

In short: SASE built the execution-engine half of a bead system extremely well (wave-scheduled `sase bead work`,
event-sourced storage, deterministic agent naming, commit provenance) and never built the memory half — while a few
integrity gaps erode the value of the archive that does exist.

## What Is Already Working (Don't Touch)

- The **plan/phase model, three statuses, blocking deps, epic tier** — a deliberately minimal design
  (`202603/sase_beads.md`) that replaced the 37 MB `bd` Go binary. Still the right call.
- **Event-sourced storage** (append-only per-epic streams + generated `issues.jsonl` projection + SQLite cache). This
  solved the JSONL merge-conflict pain (`202605/bead_jsonl_merge_conflicts.md`) and is architecturally *ahead* of
  upstream, not behind it (see next section).
- **`sase bead work`**: epic validation → Kahn-wave DAG → one agent per phase with `%w` waits + a land agent →
  batch preclaim → commit/push. 176 epics launched this way; 212 of 214 plan beads are epics; dependencies are used in
  212 of 213 parent graphs. This is the product in practice.
- The **Rust core / Python host split**. Note for costing: any data-model change (new bead kind, link kind, close
  resolution) crosses the `sase-core` boundary (wire/events/mutation/read + facades); prompt- and TUI-side changes do
  not. That boundary is the main effort multiplier in the recommendations below.

## Lessons From Upstream Beads (`bd`)

The repo has moved: `steveyegge/beads` now 301-redirects to **`gastownhall/beads`** (verified; HEAD `6e1b04c26` on
2026-07-14). Its history is more useful as a *natural experiment* than a roadmap:

- **Its storage evolution is a cautionary tale.** `bd` started exactly where SASE is (git-native JSONL + SQLite
  cache), then migrated to a Dolt SQL/daemon backend and ripped out JSONL sync entirely — causing documented community
  migration pain (corrupted/emptied stores, third-party migration guides); Yegge himself calls the result "a crummy
  architecture." SASE's event-sourced model is `bd`'s original, better design with the merge problem actually solved.
  **Do not follow the Dolt/daemon/server direction.**
- **Its complexity oscillated.** Agent mail shipped in v0.30.2 and was removed four days later on the principle that
  the tracker should be a data store, not a workflow engine — then molecules, formulas, wisps, gates, and custom
  type/status systems broadened the model again. SASE already owns planning, orchestration, waits, ChangeSpecs, and
  UI; rebuilding them inside beads would create two competing control planes.
- **What genuinely transferred well** (the small, cheap subset both researchers independently selected):
  - the **`discovered-from` link** — the one `bd` feature every independent practitioner singles out;
  - **near-zero-ceremony capture plus prompt-side discipline** — `bd`'s #1 documented failure is that agents don't
    proactively file, so the habit must live in the standard prompts;
  - **atomic claim / close guards / `ready --explain`** — mature answers to agents racing and dying;
  - **machine-readable output** for a programmatic ready→claim→work→close loop;
  - **keeping the working set small** (`bd` recommends cleanup below ~500 open issues).

## Recommendations, Ranked

Ranking principle (this is where the two reports differed — see § Conflict Resolutions): **observed problems before
hypothetical ones, and capture before polish.** The 0-open-beads gap and the verified integrity defects are real today;
claim races and partial graph creation are possible but have not visibly damaged the store.

### 1. Standalone capture beads with `discovered-from` provenance, wired into the agent prompts

The single biggest full-potential unlock, and both researchers' top-tier item. Three pieces that ship together:

- **A standalone bead kind** (`task`, optionally `kind=bug`) with no required plan file or parent, plus a `kind` on
  `Dependency` so `discovered-from` links can record which bead/plan surfaced the work without affecting readiness.
  Crosses the Rust boundary (`wire.rs`, `events.rs` `DependencyAdded` payload, `mutation.rs`, validation, facades,
  `parser_bead.py`/`cli_crud.py`). Medium effort, low conceptual risk.
- **A two-word capture verb** — e.g. `sase bead capture "Token expiry is 1h not 24h"` — that defaults
  `discovered-from` to the ambient `SASE_BEAD_ID`/plan when one is in scope, and supports `--defer-until` so "not
  now" is distinct from dependency-blocked. Agents file what is trivial to file.
- **The discipline, in the prompts.** Bake "file a standalone bead for any discovered follow-up worth more than a
  couple of minutes, linked `discovered-from` the current work" into the `work_phase_bead` and `land_epic` xprompts
  (and the `sase_beads` skill). This is nearly free and is the change most likely to actually move the 0-open-beads
  number — tooling without the habit demonstrably does nothing (`bd`'s own experience).

Guardrails carried over from both reports: phase agents *propose* captures rather than silently expanding scope (the
land agent, or an explicitly authorized agent, files them); captured beads inherit the existing "bead descriptions are
untrusted agent content" prompt-injection rule; **start without priority/labels** (see Conflict Resolutions) and add a
field only when live triage demonstrates a query that cannot be answered cleanly.

### 2. Make plan linkage durable (logical refs + `doctor` validation)

**Verified: 220 of 228 stored `design` links fail as written**, yet 220 of 228 have a basename match under the current
`plans/` tree and ~340 plan files carry `bead_id` frontmatter — this is fully repairable. Store a logical SDD
reference (`plans:202607/foo.md`) resolved through the active SDD store at read time instead of a filesystem path;
add `sase bead doctor --fix-design-refs` to backfill from `bead_id` frontmatter; make plain `doctor` report missing,
ambiguous, or bead/frontmatter-mismatched links (today it reports "OK" because it never checks). Without this, every
"beads as memory" feature (search, history, the TUI tree) leads to dead ends. Modest, mostly-additive Rust+Python
work; no workflow change.

### 3. Make completion truthful (close guards + resolution)

**Verified: the store contains closed beads whose own notes instruct that they remain open** (`sase-5t`,
`sase-5t.5`), and closed diagnostic phases indistinguishable from healthy outcomes (`sase-31.6` closed while master CI
still failed). Invert the cascade-close default: `close <plan>` fails while children are non-closed; forced closure
requires `--force --reason`; replace the ambiguous "closed = completed or abandoned" with a small resolution enum
(`done` / `canceled` / `superseded` — no arbitrary custom statuses); reopening a child reopens (or demands reopening)
the parent. Upstream's v0.60.0 epic close guard is precedent; SASE's own contradictory records are the stronger
justification. Small Rust mutation change; stops new false-completion records immediately.

### 4. Expose the history beads already record (append-only notes + evidence)

**Verified: 1,115 note-update events across 571 issues are retained in the event streams but invisible** — the
projection shows only the last write, and the commit hook routinely replaces a verification/blocked-state summary with
`COMMIT: <sha>` (1,043 of 1,149 current notes are commit bookkeeping). Add `sase bead history <id>` /
`show --history` and an appending `sase bead note <id> "..."`; change the commit hook to append commit evidence
instead of overwriting; record close resolution, attempts, and ChangeSpec/PR references as structured append-only
events (auto-populated when `sase bead work` already knows them — the manual `--changespec` flag has been used 0/1,479
times). This is surfacing existing data, not a second database.

### 5. Build the AXE open-bead tree (the designed-but-unbuilt TUI view)

A living backlog is worthless if it's invisible. Today beads appear only as decoration on running-agent rows; there is
no beads tab, browser, or triage surface. `202605/axe_open_bead_tree.md` already specs a tree of open beads with
`show`-equivalent detail in the side panel. Presentation-layer Python only; the natural payoff once #1 starts
producing open beads. Read/triage only — no TUI CRUD.

### 6. Machine-readable output (`--json` on `ready`, `show`, `list`, `blocked`, `stats`)

Only `search --format json` exists today. The Rust read layer already produces structured data; this is a renderer
path plus stable schemas. Prerequisite for hooks, automation, and #5 being cheap.

### 7. Graph/CLI ergonomics and an accurate skill

- `dep rm` and `dep list` (**verified: `dep` has only `add`**; removing a wrong edge means storage surgery), plus
  `ready --explain` and a `dep tree`/graph check for diagnosing why work isn't ready.
- **Rewrite the generated `sase_beads` skill.** Verified: it documents only
  create/update/list/search/ready/show/dep-add, and its "Typical Workflow" is the manual claim loop that the store
  shows is effectively dead — it never teaches `sase bead work` (the actual centerpiece), `close`, `blocked`,
  `stats`, `doctor`, `sync`, or recovery. Agents cannot use features they are never taught. Add a contract test
  comparing the skill's documented verbs against the argparse surface. (Note: the skill is generated — edit the
  source template under `src/sase/xprompts/skills/`, per `memory/generated_skills.md`.)

### 8. Atomic plan→epic compilation (worthwhile, not urgent)

Today `bd/new_epic` has an LLM create the epic, phases, deps, and frontmatter one auto-committing command at a time —
an interruption can leave a partial graph. A deterministic, dry-runnable, `bead_id`-idempotent
`sase bead epic create --from-plan <plan>` compiler (Rust transaction) removes that failure window and makes launches
reproducible. Ranked below the items above because the store shows no observed damage from this path yet — the LLM
flow, while inelegant, is working. Keep the agentic path as fallback for unusual prose plans.

### 9. Atomic claim + liveness reconcile (deferred until manual claiming matters)

`ready`-then-`update` is racy in principle, and a dead agent can strand an in-progress phase. But today the manual
claim loop is essentially unused — `sase bead work` batch-preclaims atomically. Implement `claim`/`ready --claim`/
`reconcile` when #1 creates a real standing backlog that agents claim from ad hoc. When built, reconcile from SASE's
own agent liveness/metadata rather than copying `bd`'s generic heartbeat/lease system.

### Watch — don't build yet

- **Retention/compaction.** 1,479 closed beads, unbounded streams, a 1.2 MB projection. Not a problem while the open
  set is ~0, but it's what bloats first if capture succeeds. Cheap now: a size/token early-warning in
  `sase bead doctor`. Build `compact`/retention only if the projection approaches the point where agents reading it
  suffer (~25k tokens; `bd` cleans up below ~500 open issues).
- **Tale policy.** Don't force ceremony onto tales; once #1 exists, tale-scale discovered work can land in the shared
  worklist for free. Policy/prompt decision, not plumbing.

## Anti-Recommendations (both researchers, independently)

- **No Dolt, server/daemon modes, federation, or pluggable SQL.** The exact over-complexity flagged in the request; it
  caused real pain upstream, and SASE already solved the problem it was meant to fix.
- **No molecules, formulas, wisps, gates, agent mail, or `prime`/`remember` memory layers.** SASE plans, xprompts,
  `%w`, notifications, and its own memory system occupy this layer.
- **No numeric priority levels, label taxonomy, or custom type/status systems** (yet). Deliberately dropped in
  `202603/sase_beads.md`; dependency order plus `defer-until` covers the known queries. Revisit only with evidence
  from a live backlog.
- **No external tracker sync** (ChangeSpecs/VCS plugins are the integration point) and **no full TUI CRUD** (read/
  triage tree only).

## Practice Changes Requiring No Product Work

1. Use `sase bead work <epic> --dry-run` before launching plans with parallel or fan-in dependencies.
2. Never manually cascade-close a parent to clean up children; close phases individually and let the land agent close
   the parent after checking notes, commits, and plan status.
3. Pass `--reason` whenever a closure is not an ordinary successful completion.
4. Pass ChangeSpec/bug metadata when an epic should create or continue a ChangeSpec (used 0 times so far).
5. Treat `sase bead doctor` as a storage/sync check only — it does not yet validate plan links or completion truth.

## Conflict Resolutions (lead-researcher verification)

- **Priority field**: Researcher A included priority in the capture model; Researcher B anti-recommended it. Resolved
  for B: `202603/sase_beads.md` explicitly removed priority ("ordering is implicit via creation order and epic
  grouping"), and A's own "add fields only after live evidence" principle points the same way. Capture ships without
  priority; `defer-until` and `discovered-from` cover the known needs.
- **Top-rank ordering**: A led with integrity (plan refs, close guards, atomic compile); B led with capture
  (standalone beads, prompts, TUI). Both problem sets verified real; capture ranked first because it answers the
  actual question (unused potential) and the integrity fixes (#2–#4) make the resulting memory trustworthy. A's
  atomic-compile and atomic-claim items were demoted below both, because they address failure windows not yet observed
  in the store, whereas #1–#4 address measured defects.
- **A's data claims**: all re-verified exactly (8/228 resolving links; 138 absolute/90 relative split; sase-5t and
  sase-31.6 contradictions verbatim). The hidden-history count is *larger* than A reported (1,115 vs 769 note-update
  events; measurement date 2026-07-14) — direction unchanged, urgency slightly higher.
- **B's transcript vs report on the skill**: B's mid-research note claimed the skill "documents every subcommand"; its
  final report correctly said the CLI is richer than the skill. Verified against the 177-line skill source: A's
  characterization (omits `work` and seven other verbs; teaches the dead manual workflow) is correct and is what #7
  reflects.
- **Upstream repo location**: A cited `gastownhall/beads` as the new home; B cited `steveyegge/beads`. Both are right —
  the old URL 301-redirects; A's checkout SHA matches upstream HEAD. Citations below use the canonical new location.

## Bottom Line

If only three things get funded: **(1) standalone capture beads with `discovered-from`, a two-word capture verb, and
the filing habit baked into the phase/land xprompts; (2) durable plan references with doctor validation; (3) truthful
close semantics.** Together they convert beads from a write-once execution archive into a trustworthy, living,
cross-session memory — which is the entire gap between current usage and full potential. The AXE bead tree and
`--json` (#5–#6) then make that memory visible and programmable. Everything beyond that is polish, and the loudest
lesson from upstream's own history is to stop there.

## Sources

- Live store verification (2026-07-14): `sase bead stats`, `issues.jsonl` + `events/streams/*` analysis,
  `sase bead create/dep/ready/list --help`, `src/sase/xprompts/skills/sase_beads.md`.
- Upstream: https://github.com/gastownhall/beads (README, CHANGELOG, docs, releases; `steveyegge/beads` redirects
  here), Yegge's "Introducing Beads" and "Beads Best Practices" posts, ianbull.com practitioner review, Better Stack
  guide.
- Prior in-repo research: `202603/sase_beads.md` (origin/philosophy), `202605/greenfield_bead_storage_architecture.md`
  (event-store design, compaction cadence), `202605/bead_jsonl_merge_conflicts.md`, `202605/axe_open_bead_tree.md`
  (TUI design for #5), `202606/sase_bead_work_latency_consolidated.md` (execution-side follow-ups, orthogonal),
  `202606/epic_bead_work_pr_migration_consolidated.md` (ChangeSpec direction).
- The two source reports beside this file (`__a` = codex researcher, `__b` = claude researcher).
