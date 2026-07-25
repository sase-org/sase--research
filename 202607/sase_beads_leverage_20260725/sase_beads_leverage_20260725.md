# Getting More Leverage Out Of SASE Beads

Date: 2026-07-25
Consolidates: `sase_beads_leverage_20260725__a.md` (codex/gpt-5.6-sol), `sase_beads_leverage_20260725__b.md`
(claude/opus), plus independent verification by the lead researcher.
Supersedes: `202607/sase_beads_full_potential_consolidated/` (2026-07-14).

## Headline

Beads are already a strong **parallel execution engine** and you are using that part well — better than either source
report initially assumed. The unused half is everything that happens *outside* an epic run: capture, backlog, triage,
and learning.

Three things dominate:

1. **The bead store is being corrupted right now.** Five of the eleven beads `sase bead ready` returns are pytest
   fixtures that leaked into the production sidecar today. The `#bd/next` xprompt tells an agent to claim and work
   whatever `ready` returns.
2. **The standing-backlog primitive you want already exists and has been used 3 times in 2,014 beads.** A
   `--tier plan` bead is a durable, non-executable, dependency-aware work item; `sase bead update <id> --tier epic`
   promotes it to a runnable epic. Neither source report found this — both proposed building it as a new feature.
3. **The `sase_beads` skill teaches 7 of 18 verbs** and none of the six shipped capabilities that would let you use
   beads outside `sase bead work`.

None of the top three requires touching the Rust core. The highest-value beads work available today is a guard, a
document, two prompt sentences, and a habit.

## Method And The Snapshot Caveat

The store is live and moves under measurement. Three independent snapshots exist for 2026-07-25:

| | Report A (~09:55) | Report B (~09:45) | Lead (~10:20) |
|---|---:|---:|---:|
| Total | 2,014 | 2,014 | 2,014 |
| Open | 19 | 21 | 18 |
| In progress | 7 | 8 | 6 |
| Closed | 1,988 | 1,985 | 1,990 |

**Do not treat any single count as an audit fixture.** Every structural number below was re-measured by the lead
researcher against `sase/repos/plans/beads/issues.jsonl`, the event streams, the live CLI, a YAML scan of all 3,158
top-level plan files, and the upstream checkout. Where A and B disagreed, the lead measurement is given and the
discrepancy explained.

## What Is Already Working: The Scheduler

Report A's most valuable contribution, independently confirmed by the lead researcher using a different method (A read
bead dependency edges; the lead parsed `phases:`/`depends_on:` from epic plan frontmatter):

| Measure | Lead (plan frontmatter) | Report A (bead edges) |
|---|---:|---:|
| Epic graphs authored since 2026-07-15 | 86 | 92 |
| Total direct phases | 404 (avg 4.7) | 421 (avg 4.58) |
| Graphs with a parallel wave | 48 (56%) | 52 |
| Graphs with fan-in | 49 | 49 |
| Strictly linear | 38 | 33 |
| No dependency edges at all | 2 | 4 |
| Widest single wave | 11 | 11 |

Across the whole store, 1,271 beads carry at least one dependency edge. **The dependency scheduler is not an unused
feature, and "add more edges" is not the recommendation.** The useful qualitative improvement is that graphs should
express *uncertainty and convergence*, not directory boundaries: make the fan-in phase produce explicit acceptance
evidence rather than leaving cross-phase integration to the land agent as its first exercise.

Useful graph shapes:

```text
Parallel investigation
reproduce ─┬─ hypothesis A ─┐
           ├─ hypothesis B ─┼─ synthesize ─ verify
           └─ hypothesis C ─┘

Cross-cutting delivery
contract ─┬─ core implementation ─┐
          ├─ frontend / adapters ─┼─ integration ─ end-to-end evidence
          └─ migration + docs ────┘

Risk-first rollout
spike ─ decision ─ implementation ─ canary ─ rollout ─ cleanup
```

Note that the DAG is authored in the **plan file's frontmatter** (`phases:` with `depends_on:` and `size:`), not with
`dep add`. `sase bead work <plan.md>` compiles it. `dep add` is for repair, and there is still no `dep rm`.

## Findings

### F1 — The test suite writes into the production bead store (severity: highest, active)

Confirmed by the lead researcher against the live store. Five of eleven `ready` results (45%) are pytest fixtures:

| Bead | Title | PLAN link |
|---|---|---|
| `sase-97` | "Created Epic" | `.localtmp/pytest-of-bryan/pytest-0/popen-gw7/test_bead_cli_golden_contract_1/…` |
| `sase-9a` | "Created" | `plan.md` |
| `sase-9b` | "Epic" | `plan.md` |
| `sase-9c` | "Epic" | `sdd/plans/202605/roadmap.md` |
| `sase-9d` | "Epic" | `…/sase_17/.pytest_cache/tmp/pytest-of-bryan/…/test_create_plan_preserves_ext0/…` |

`sase bead show sase-97` returns `Assignee: bob`, `ChangeSpec: created_epic`, `Bug ID: BUG-9` — all literal fixture
values from `tests/test_bead/test_cli_golden.py:162-172`. `sase-9a`–`9d` were created within 20 seconds of one another
(a single parallel pytest run). One PLAN path points into **sibling workspace `sase_17`'s** pytest cache, so the leak
is not checkout-local.

Why this ranks first:

- **It poisons the queue agents are told to drain.** `bd/next` (`default_config.yml:670`) says verbatim: *"run
  `sase bead ready` … claim the next ready bead by marking it as in-progress, complete the work associated with it, and
  then close the bead."* An agent running `#bd/next` today has a coin-flip chance of trying to implement `plan.md`.
- **It consumes production IDs permanently.**
- **The precedent exists and skipped this surface.** Closed bead `sase-8g.11` — *"Keep tests out of production
  state"* — guarded the metrics DB and axe logs against unisolated pytest runs. The bead store was not covered.
- **Upstream fixed the identical failure mode one day ago.** `gastownhall/beads` `50003b803` (2026-07-24), *"refuse
  test DBs on production dolt servers (AD-01)"* — verified in the checkout.

Root cause per Report A: the test helpers change directory and mock primary-workspace resolution but do not clear
inherited `SASE_SDD_PLANS_DIR` / `SASE_SDD_BEADS_DIR`, so a launched-agent test run can target the real sidecar.

Fix shape: two-sided guard — tests set an explicit opt-in env var; the store refuses a write from a process without it
when the resolved path is the real sidecar. Cleanup is one command (`sase bead rm` gained atomic multi-remove in
`fed18866e`). **Verify the five IDs with `sase bead show` immediately before removing** — the store moves.

### F2 — The backlog primitive already exists and is unused (new; neither source report found it)

Report A recommends building a `task` bead kind, `sase bead capture`, and promotion-to-epic as feature work. Report B
defers the same idea to "watch — don't build yet." **Both missed that the mechanism already ships.**

Verified in source and against the live CLI:

- `tier` is a real stored column, not derived (`db.py`; `_apply_missing_tiers` in `jsonl.py` is a legacy backfill only).
- `sase bead work` requires `IssueType.PLAN` **and** `BeadTier.EPIC` (`cli_work_from_plan_helpers.py:103`,
  `cli_work_from_plan_resume.py:71`). A `--tier plan` bead is therefore **structurally non-executable** — it will never
  be auto-launched.
- `sase bead update <id> --tier epic` is wired (`cli_crud.py:143-144`) and promotes it to runnable.
- `list` and `search` both accept `--tier` (`parser_bead.py:107,199`). `sase bead list --tier plan --status open` is a
  backlog view that works today.

The complete loop, available now with zero feature work:

```bash
sase bead create -t "Publish X to PyPI" -T "plan(${SASE_SDD_PLANS_DIR}/202607/publish_x.md)" --tier plan   # capture
sase bead list --tier plan --status open                                     # the backlog / inbox view
sase bead dep add <backlog-bead> <blocker-bead>                              # defer behind real work
sase bead update <id> --tier epic && sase bead work <id>                     # promote and run
sase bead close <id> --reason "superseded by sase-XX"                        # resolve honestly
```

Usage in 2,014 beads: **3 beads, all closed** — `sase-26` (Mobile MVP Legend), `sase-5s`, and `sase-71`
("Publish bugyi-chops to PyPI", a genuinely good example of a durable non-executable work item). The reason it is
unused is a default, not a missing feature: `create_issue` defaults a plan bead with no explicit `--tier` to **EPIC**,
and nothing teaches `--tier plan`.

Two honest caveats:

- **It is not zero-ceremony.** `--type plan(<file>)` requires the plan file to exist (`cli_crud.py:92-97`). But you
  already produce ~2,716 tale plans via `/sase_plan`; attaching a `--tier plan` bead to one you actually intend to
  return to is a one-line addition, not a new workflow.
- **`ready` does not distinguish it.** A `--tier plan` bead with no blockers appears in `ready` alongside launchable
  epics. That is exactly F9.

This finding is the bridge between A's "capture inbox" recommendation and B's "shadow backlog" finding, and it
converts both into a practice change rather than a Rust change.

### F3 — The two most-run prompts explicitly forbid capture (Report B; confirmed verbatim)

- `bd/work_phase_bead` (`default_config.yml:709`), which every phase agent runs, ends: *"Do NOT close the parent epic.
  **Do NOT create new beads.**"*
- `bd/next` (`default_config.yml:679`): *"**IMPORTANT: Do NOT create any beads of your own.** You are meant to work the
  pre-existing ready bead that you select."*

Both prohibitions are defensible — they stop a phase agent from silently expanding scope. But they are absolute, and
they attach to the two roles with the best possible view of discovered work. **The agents that find follow-up work are
the agents forbidden from recording it.** No amount of capture tooling moves the needle while the prompt says no.

The fix is a text edit: narrow "do not create beads" to *"do not create beads for yourself to work; record discovered
follow-up as a `PROPOSED FOLLOW-UP:` line in your bead notes."* Then add to `bd/land_epic` step 1: *"collect proposed
follow-ups from child bead notes and file them (`--tier plan`)."* `bd/land_epic` already instructs the land agent to
run `sase bead show` on every child bead, so the delivery channel exists today.

Evidence this lever works: `close --reason` went from effectively zero to **72 of 1,990 closures (3.6%)** after the
prior report recommended it as a practice change, with no feature work.

### F4 — Six shipped capabilities you are not using

This is the most direct answer to "new and useful ways to use beads." Every item works today.

| # | Capability | Current usage | What it unlocks |
|---|---|---|---|
| a | `%wait(bead=<id>)` — repeatable, multi-bead agent barrier | — | Park any hand-launched agent behind any bead, **outside** `sase bead work`; gate a docs/release agent on several unrelated epics; sequence across epics with no graph relationship |
| b | `%id(<name>, bead=<id>)` — bind an ad-hoc agent to a bead | — | Full claim lifecycle (`claimed`→`in_progress`→release on death), bead section in the ACE prompt panel, and it becomes a valid `%wait(bead=…)` target. **This is what makes individual open beads workable without an epic.** |
| c | Child epics owned by phases | 12 of 320 plan beads have a parent | The sanctioned escape hatch when a phase turns out to be an epic in disguise — the normal failure mode of epic planning — without losing lineage |
| d | `--size {xsmall..xlarge}` routing to model pools | medium 110, small 55, large 10, **xsmall 0, xlarge 0**, unset 1,519 of 1,694 phases | Both ends of the cost/capability curve are unexercised: a cheap lane for mechanical phases, a heavy lane for the genuinely hard one. `bead.big_epic_phase_threshold: 5` also auto-selects `@big_epic_lander` |
| e | `--changespec` / `--bug-id` on plan beads | **4 beads, all test fixtures** | The designed seam between the bead graph and the CL/PR lifecycle: `plan → epic → phases → ChangeSpec/bug → commits → landing`. A better home for commit provenance than mutable notes |
| f | `sase bead work --dry-run` / `--json` | — | `--dry-run` previews the wave plan and changes nothing — the cheapest correctness check before any fan-in epic. `--json` makes launches scriptable |

Correction to Report B on (a) and (b): B states they are *"documented nowhere the agent will see it."* They **are**
documented — `docs/xprompt.md:1071-1072,1233-1236`, `docs/beads.md:98,406-413`, `docs/agent_families.md:193-204`,
`docs/axe.md:187`. What is true, and is the actionable part, is that they are absent from the two surfaces an agent
actually consults: the generated `sase_beads` skill (never mentions waits at all) and `sase/memory/xprompts.md` (which
documents only `%wait:<n>` and `%wait(time=…)`).

Correction to Report B on (e): B's heading says "0 uses in 2,014 beads." There are 4 (`sase-8o`, `sase-8s`, `sase-97`,
`sase-9b`) — all recognizable fixtures (`feature_epic`/`created_epic`, `BUG-9`/`12345`). Report A's phrasing is the
accurate one. The conclusion is unchanged: **zero production use.**

### F5 — The discoverability gap is the multiplier on F2 and F4

The CLI has 18 verbs: `blocked close create dep doctor init list onboard open ready resolve-conflicts rm search show
stats sync update work`.

The generated `sase_beads` skill documents **7** (`create`, `update`, `list`, `search`, `ready`, `show`, `dep add`),
mentions `work` only in prose with no usage example, and closes with the obsolete manual loop:
`create → add phases → add deps → ready → update in_progress → close`.

`sase bead onboard` is meaningfully better — it covers ~17 verbs in 29 lines — but **no agent is ever told it exists**,
its examples still use retired `sdd/plans/` and `sdd/beads/` paths, and it omits `--size`, `--model`, `--tier`,
`--changespec`, `--json`, `--dry-run`, and plan-file launch.

The gap widened while the prior report sat: `claimed`, `--size`, `rm`, and bead-gated waits all shipped since
2026-07-14. Every item in F2 and F4 is free capability blocked only by ignorance.

### F6 — The shadow backlog: 246 `wip` plans invisible to beads (Report B; confirmed and refined)

YAML scan of all 3,158 top-level plan files:

| `status:` | Count |
|---|---:|
| `done` | 2,713 |
| **`wip`** | **278** |
| `complete` (non-canonical duplicate) | 34 |
| none | 90 |
| `draft`/`handoff`/`pending`/`proposed`/`active`/`completed`/`PROPOSED`/`not started`/`planned`/`ready`/`new`/`open` | 43 combined |

Only **32 of the 278 `wip` plans carry a bead**. The other **246 are in-flight-looking work beads cannot see** —
concentrated recently (109 in 202607, 67 in 202605, 49 in 202604, 39 in 202606). Twelve distinct spellings of "not
done", no queue, no dependency edges, no `ready`.

Two refinements the lead researcher adds:

- **Split the shadow backlog by tier: 248 tales, 30 epics.** The 30 `wip` **epic** plans are the actionable subset —
  they are already decomposed and were meant to run. The 248 tales are mostly abandoned scratch, and "don't bead every
  tale" remains right.
- **Report B's "even the epic path has gaps (442 plan files vs 320 plan beads)" is an artifact.** Only **17 of 442**
  epic plan files lack a bead reference; 425 carry one, pointing at 361 distinct beads, because **64 beads are
  referenced by more than one plan file** (versioned `_1`, `_v2` re-plans of the same epic). The epic path is in good
  shape; the coverage problem is tales, and that is policy.

Tale coverage: 2,716 tale plans, 2,675 with no bead (98.5%) — consistent with the prior report's ~87% estimate,
measured precisely.

### F7 — Plan↔bead linkage fails in both directions

Reports A and B appeared to conflict here; they were measuring different denominators. Lead measurement resolves it:

| Measure | Lead | Report A | Report B |
|---|---:|---:|---:|
| Beads with a `design` link | 334 | — | 334 |
| …that resolve as written | 104 | — | 105 |
| Plan **beads** (all 320 carry a design link) | 320 | 320 | — |
| …that resolve | 104 | 103 | — |
| Broken (all beads) | 230 | — | 229 |
| Broken but basename-recoverable under the sidecar | 212 (92%) | — | 211 (92%) |
| Absolute / relative paths | 141 / 193 | — | 141 / 193 |

**Both were right.** The 334 vs 320 gap is 14 *phase* beads that also carry a design link. Rate improved sharply
(3.5% → ~31% since 2026-07-14) but the absolute broken count did not (220 → 230): new beads resolve, the historical
tail does not. Only 3 broken links point at temp/pytest paths (`sase-8q`, `sase-8s`, `sase-97`).

The reverse direction, which the prior report never checked:

- **60 of 466 bead-linked plan files (12.9%) carry a `bead_id:` that does not exist in the store** — e.g.
  `202602/axe_lumberjacks.md → sase-0xd`, `202602/claude_ask_user_question.md → sase-5qu`. Pre-migration ID-scheme
  survivors. Any tool trusting plan frontmatter to find a bead hits a hard miss ~13% of the time.
- **24 closed beads whose plan file is still `wip` or `handoff`** (`202603/unified_vcs_commit.md → sase-9`,
  `202605/blazing_fast_ace_daemon.md → sase-3i`, …).
- **0 `done` plans with a non-closed bead.** The land agent's "set `status: done`" step works in the direction it
  covers; nothing repairs the other direction.

`sase bead doctor` validates none of this. Its entire output today is `WARNING: beads.db missing`. Report A also
identified a live resolver regression worth checking: `sase-85` stores `202607/epic_clan_summary_rich.md` and the
resolver prefers the sidecar's surviving nested `plans/` directory over the actual root-level `202607/` file.

### F8 — Completion is not yet a reliable fact

Recursive parent close remains documented behavior, and the prior report's contradictory records are unchanged:
`sase-5t` and `sase-5t.5` are closed while their own notes say to keep them open until recovery edits have a durable
commit and ChangeSpec/PR; `sase-31.6` is closed while its notes say master CI still fails.

A useful archive needs more than a status enum: a close **invariant** (reject parent close with unresolved descendants;
force requires a reason and records which descendants were not done) and a **resolution** (`done` / `canceled` /
`superseded`). `close --reason` at 3.6% adoption is the manual approximation.

### F9 — History is recorded and invisible

**1,451 of 1,592 non-empty notes (91%) begin with `COMMIT`.** The commit hook overwrites the mutable `notes` field
last-write-wins, so a phase agent's verification summary or blocked-state handoff is replaced by bookkeeping the moment
a commit lands — bookkeeping that is often stale after amend or rebase.

The event streams retain everything: 343 stream files, 7,971 events, 1,560 note-update events, 916 issues with a note
update, 511 with multiple revisions. **No CLI surface exposes any of it.** There is no `sase bead history`, no
appending `sase bead note`.

A WIP tale (`202607/drop_bead_commit_note.md`) correctly proposes stopping the `COMMIT: <sha>` overwrite and documents
that no consumer relies on the field (ChangeSpecs already carry the durable post-rebase commit). That is the right
immediate fix, but it does not restore overwritten history, expose events, or derive flow metrics — and the event store
already contains enough to become a lightweight process-observability system with no backend change.

### F10 — Triage views mostly exist already; only `ready` is missing filters (new; refines Report A)

Report A recommends building six action-oriented views. The lead researcher verified that **five of the six already
exist as flag combinations**:

| View | Command today |
|---|---|
| Launchable epics | `sase bead list --tier epic --status open` ✅ |
| Backlog / inbox | `sase bead list --tier plan --status open` ✅ (see F2) |
| Claimed / waiting | `sase bead list --status claimed` ✅ |
| Blocked, with blockers named | `sase bead blocked` ✅ (verified: prints `[blocked by: …]`) |
| Needs attention | — (requires the doctor work in R4) |
| **Ready *phases* only** | **✗ `sase bead ready` accepts no arguments at all** |

So A's recommendation shrinks from "build six views" to **"add `--type`/`--tier` filters to `ready`, and teach the
other five."** `sase bead ready --type phase` alone would have made F1 far less dangerous.

The genuinely missing machine surface remains: only `search --format json` and `work --json` exist. `ready`, `list`,
`show`, `blocked`, and `stats` have no JSON, and there is no documented exit-code contract.

### F11 — Beads are single-project (new; in neither source report)

`sase project list` shows three enabled projects with launch enabled — `sase`, `actstat` (`gh_bbugyi200__actstat`), and
`bob-cli` (`gh_bobs-org__bob-cli`). **Only `sase` has a bead store.** The epic/phase orchestration, dependency waves,
claim lifecycle, and land-agent workflow are available to the other two via `sase bead init`, and neither is using any
of it.

This is worth a deliberate decision rather than drift. If `actstat`/`bob-cli` work is small and serial, no beads is the
right answer and should be stated. If either has multi-phase work, `sase bead work <plan.md>` is available today. Note
that `sase-71` ("Publish bugyi-chops to PyPI") shows the current workaround: another project's work tracked as a bead
in the `sase` store, which loses per-project `ready` and stats.

### F12 — Chops are the unused scheduling substrate for bead hygiene (new)

`sase_chop_bead_claim_checks` is the **only** bead-touching chop (`default_config.yml:444`). Chops already provide the
scheduled-execution substrate — `hook_checks`, `mentor_checks`, `orphan_cleanup`, `stale_running_cleanup`,
`error_digest`, and more all run on intervals.

Nothing runs `sase bead doctor`, nothing reports stale open beads, and nothing surfaces the `wip`-plan shadow backlog.
Once R4 makes `doctor` meaningful, a hygiene chop is near-free and turns every one-time cleanup in this report into a
standing regression guard.

## Upstream Delta Check (`gastownhall/beads`)

Verified in the checkout at HEAD `508d35921` (2026-07-25); 236 commits since 2026-07-14. Direction: replica-aware
leases, `granted_node` provenance, Dolt-backed conflict tests, domain-aware three-way auto-merge, `bd sync` as a
federation loop, cross-replica reclaim guards.

**Do not follow.** SASE's event-sourced store already solves the problem this machinery exists to manage. Three small
items transfer, all commit-verified:

1. **`50003b803` (2026-07-24)** — *"refuse test DBs on production dolt servers (AD-01)"*: direct precedent for F1,
   landed one day ago.
2. **`6e8af8bf8` (2026-07-24)** — `bd update --if-assignee/--if-status` compare-and-set guards. The motivation:
   *"the fleet's most common bug class is check-then-act on assignee/status — read state, then issue a blind update,
   and lose to a racing writer in the gap."* SASE's `ready`-then-`update` loop has exactly this shape, and unlike on
   2026-07-14 it is now a loop over real beads.
3. **`f94ea5bfe` (2026-07-24)** — exit codes as a machine contract (`bd sync` returns 0/1/2/3 with distinct meanings
   plus a `--json` envelope, so a timer can branch without parsing prose).

Report A additionally notes upstream's `bd todo` design reinforces the right product shape: a convenience layer over
normal task records, not a parallel store. That is precisely what F2 shows SASE already has in `--tier plan`.

## Use Beads Better Starting Today (No Feature Work)

1. **Dry-run before every fan-in epic.** `sase bead work path/to/epic.md --dry-run` previews the wave plan and changes
   nothing. Pair with `sase bead show <epic-id>`, `sase bead blocked`, `sase bead doctor`, `sase bead sync --status`.
2. **Capture with `--tier plan`.** Attach a non-executable bead to any tale plan you actually intend to return to.
   `sase bead list --tier plan --status open` is your backlog. Promote with `update --tier epic`, then `work`.
3. **Bind hand-launched agents to beads.** `%id(<name>, bead=<id>)` gives an ad-hoc agent the full claim lifecycle;
   `%wait(bead=<id>)` parks any agent behind any bead, including across unrelated epics.
4. **Treat size as a budget, not prose.** `xsmall` = observation-only/mechanical; `small` = one focused change with
   obvious verification; `medium` = substantial direct implementation from a precise description; `large` = needs a
   planning handoff or child epic; `xlarge` = deliberate progressive elaboration. Warning signs: a `small` whose
   description has multiple independent deliverables; a `medium` where the worker must first decide the architecture;
   an `xlarge` used merely to request a stronger model. Prefer size-derived routing over explicit per-phase `--model`
   (currently 88 beads pin `codex/gpt-5.3-codex-spark` directly) — it is a cleaner policy surface and makes later
   calibration possible.
5. **Escalate to a child epic on a rule, not a mood.** Delegate when a phase discovers multiple independently
   schedulable deliverables, when the architecture cannot be responsibly fixed in the original description, or when it
   needs its own landing boundary. Not merely because a phase is inconvenient. Threshold ≈ `large`/`xlarge`.
6. **Attach ChangeSpec metadata to real PR-backed epics.** Put `changespec:`/`bug_id:` in the approved plan. Beads own
   execution topology; ChangeSpecs own the delivery/commit lifecycle — a better home for commit provenance than
   mutable notes.
7. **Use `search` as the archive index.** `sase bead search "claim" --format full --limit 5`,
   `sase bead search "CI" --status closed --type phase --format full --limit 10`. Treat results as leads, not proof,
   until F7 and F8 are fixed.
8. **Close honestly.** Use `close --reason` whenever completion is not an ordinary successful delivery. Adoption went
   0 → 72 with no feature work; it is the manual form of the resolution semantics R7 would formalize.
9. **Run a weekly retrospective.** Which open/in-progress beads are older than expected? Which phases were reopened or
   retried? Which `small` phases became plans and which `large` phases finished directly? Which child epics were
   healthy discovery vs. poor initial decomposition? Which closed beads hide cancellation/supersession in their notes?

## Ranked Recommendations

Ranking principle: **stop active corruption, then make the capability you already own reachable, then instrument it.**

### 1. Stop the test suite writing to the production bead store, and purge the leaked beads

Highest severity, smallest fix, actively worsening. Two-sided guard: test harnesses set an explicit opt-in env var and
clear inherited `SASE_SDD_PLANS_DIR`/`SASE_SDD_BEADS_DIR`; the store refuses a write from a process without the opt-in
when the resolved path is the real sidecar. Follow `sase-8g.11`'s precedent and upstream AD-01 for shape. Then verify
and remove the fixtures (`sase bead rm` supports atomic multi-remove). **Do this before running `#bd/next` again.**

### 2. Rewrite the generated `sase_beads` skill around the real lifecycle

Was #7 in the prior report; promoted because the gap widened (7 documented verbs vs 18; `claimed`, `--size`, `rm`, and
bead-gated waits all shipped since) and because F2 and F4 are pure capability blocked only by ignorance. Structure it
as `approved plan → dry-run → compile → launch → claimed/waiting → retry/delegate → evidence → land`. Must cover:
`work` with real examples and `--dry-run`/`--json`; **`--tier plan` capture and `update --tier epic` promotion**;
five-size policy; child epics; `close --reason`, `open`, `blocked`, `stats`, `doctor`, `onboard`, `rm` warnings; and —
most valuably — **`%wait(bead=…)` and `%id(…, bead=…)`**, which belong in `sase/memory/xprompts.md` as well. Edit the
source template at `src/sase/xprompts/skills/sase_beads.md` per `memory/generated_skills.md`, then regenerate and
deploy; do not hand-edit provider copies. Add a contract test comparing documented verbs against the argparse surface
so this cannot silently rot again. Pure documentation; zero Rust; largest capability-per-hour ratio on this list.

### 3. Narrow the capture prohibition in `bd/work_phase_bead` and `bd/next`, and file follow-ups in `bd/land_epic`

A prompt edit, not a feature. Phase agents record `PROPOSED FOLLOW-UP:` in bead notes; the land agent (which already
reads every child's notes) files them as `--tier plan` beads. This delivers most of the prior report's #1 with none of
its Rust cost, and F2 means the destination already exists. The `close --reason` 0 → 72 adoption is evidence the
practice-change lever works.

### 4. Make `sase bead doctor` validate what it claims to check

Today it emits only `WARNING: beads.db missing`. Add, in detection-first order: PLAN paths pointing into temp/pytest
directories (the F1 standing guard); design links that do not resolve through the **production resolver** the TUI and
plan-opening surfaces use (230 today, 212 basename-recoverable); plan `bead_id:` frontmatter absent from the store
(60); closed beads whose plan is still `wip` (24); `wip` plans older than N days with no bead (246). Pair with
`--fix-design-refs` to backfill from the 92% that are basename-recoverable. Cheap, additive, and it converts four
one-time cleanups in this report into standing regression guards. Then schedule it as a chop (F12).

### 5. Adopt the `--tier plan` backlog loop, and add filters to `ready`

Two halves of "the backlog now exists, so make it workable":

- **Practice:** use `--tier plan` for captured follow-ups and `list --tier plan --status open` as the inbox
  (F2). Start with the 30 `wip` **epic** plans — they are already decomposed and were meant to run. Leave the 248 `wip`
  tales alone; do not bead every tale.
- **Product:** `sase bead ready --type phase|--tier epic`. `ready` accepts no arguments at all today, and five of A's
  six proposed triage views already exist as `list`/`blocked` flag combinations (F10). This is a much smaller change
  than "build a triage system."

### 6. Build the ACE open-bead tree

Was #5 in the prior report, when it would have rendered zero rows. With ~18 open, ~6 in progress, and 7 blocked with
real dependency edges, it has content on day one. `202605/axe_open_bead_tree.md` already specs it. Presentation-layer
Python only; read and triage, **no TUI CRUD**.

### 7. Expose history, and make completion truthful

Two halves of "the archive should be trustworthy":

- **History:** finish `202607/drop_bead_commit_note.md` (stop the `COMMIT:` overwrite), add `sase bead history <id>`
  and an appending `sase bead note`, and recover overwritten notes from the event streams where they survive
  (1,560 note-update events, 511 issues with multiple revisions).
- **Truthful close:** reject parent close with unresolved descendants; require force + reason for exceptional closure
  and record which descendants were not done; add `done`/`canceled`/`superseded` resolution; make reopening a child
  reopen or explicitly invalidate the parent's resolution.

### 8. `--json` on `ready`, `list`, `show`, `blocked`, `stats`, plus documented exit codes

Only `search --format json` and `work --json` exist. The Rust read layer already produces structured data. Prerequisite
for hooks, for #6 being cheap, and for anything scripting the backlog. Adopt upstream's exit-codes-as-contract
discipline (`f94ea5bfe`) while you are in there.

### 9. `dep rm` / `dep list` / `dep tree`, and compare-and-set on `update`

`sase bead dep` still has only `add` — removing a wrong edge means storage surgery, and 1,271 beads now carry edges.
Add `--if-status`/`--if-assignee` guards to `update` (upstream `6e8af8bf8`) to close the `ready`-then-`update` race,
which was theoretical on 2026-07-14. Add `ready --explain` and a wave/critical-path view reusing `work --dry-run`.
Stop there unless live usage proves a need for more link types.

### 10. Exercise the unused seams: `--changespec`/`--bug-id`, `xsmall`/`xlarge`, and beads in other projects

Practice, not product. Zero production use of the ChangeSpec seam; zero uses of `xsmall`/`xlarge` in 175 sized phases.
Try each on the next epic before concluding they are wrong — a designed integration with no usage data is evidence of
an untried design, not a bad one. Separately, decide deliberately whether `actstat` and `bob-cli` should run
`sase bead init` (F11) rather than letting single-project usage persist by drift.

### 11. Turn bead events into flow metrics

`sase bead stats --flow --since …` over the existing event streams: queue wait (create → first execution), execution
time, blocked time, critical-path delay, reopen/retry/delegation rate, phase duration and defect rate **by size and
model role**, authored-wave plan vs. realized concurrency, WIP age, throughput, forced-closure count. This is what makes
the weekly retrospective answerable from commands instead of manual event-stream analysis, and what would finally
calibrate the five-size ladder empirically. Ranked last because it is the only item that needs the others done first to
be trustworthy — but it is the highest-ceiling item on the list.

### Watch — Don't Build Yet

- **A dedicated standalone `task` bead kind.** F2 shows `--tier plan` covers most of it. Ship R3 and R5 first; if
  notes-based follow-up proposals actually get filed and acted on, the residual ceremony (requiring a plan file) is
  worth removing with `sase bead capture`. If they do not get filed, dedicated tooling would not have been used either.
- **Retention/compaction.** 2,014 beads, 1.6 MB projection, 5.0 MB event streams, ~49 beads/day. Not urgent while the
  open set is ~20, but the growth rate is now measurable. A size/token early-warning in `doctor` is the cheap hedge.

## Anti-Recommendations (Both Reports Agree; Reaffirmed With Verified Evidence)

- **No Dolt, daemons, leases, replicas, or federation.** 236 upstream commits in 11 days went almost entirely here.
  SASE's event-sourced store already solves what that machinery manages.
- **No molecules, formulas, wisps, gates, or agent mail.**
- **No priority levels or label taxonomy yet.** Still no query the dependency graph and `search` cannot answer.
- **No beading of tales.** 2,675 tales without beads is a policy, not a bug. Fix the *visibility* of `wip` plans and
  the 30 `wip` epics instead.
- **No full TUI CRUD.** Read and triage only.
- **No new link types in advance.** If a second non-blocking relationship proves necessary after `discovered-from`,
  `validates` is the best candidate because it connects explicit evidence to delivery. Do not add a taxonomy
  speculatively.

## Corrections To The Source Reports

Recorded so the merged record is accurate; neither report's conclusions change materially.

| Claim | Source | Correction |
|---|---|---|
| `%wait(bead=…)` / `%id(…, bead=…)` "documented nowhere the agent will see it" | B | Documented in `docs/xprompt.md`, `docs/beads.md`, `docs/agent_families.md`, `docs/axe.md`. Absent from the `sase_beads` skill and `sase/memory/xprompts.md` — which is the actionable part |
| `--changespec`/`--bug-id`: "0 uses in 2,014 beads" | B | 4 uses, all test fixtures. A's phrasing is accurate. Conclusion (zero production use) unchanged |
| "442 epic plan files vs 320 plan beads — even the epic path has gaps" | B | Only 17 of 442 lack a bead ref; 64 beads are referenced by multiple versioned plan files. The epic path is fine |
| "60 of 454 bead-linked plans" | B | 60 of 466 (12.9%); the frontmatter key is `bead_id:` (431 uses) far more often than `bead:` (35) |
| 103/320 vs 105/334 design links resolving | A vs B | Both correct; different denominators. 334 beads carry a design link, of which 320 are plan beads and 14 are phases |
| "298 upstream commits in 11 days" | B | 236 verified in the checkout since 2026-07-14. Direction and the three cited commits are all confirmed |
| Store counts (19/7 vs 21/8 open/in-progress) | A vs B | Neither is wrong; the store moves. Lead snapshot: 18/6. Use as a range, not a fixture |
| Six new triage views should be built | A | Five already exist as `list`/`blocked` flag combinations; only `ready` filters are missing |
| A standalone task kind + `capture` + promotion must be built | A (rec 2), B (watch) | `--tier plan` + `update --tier epic` already provides the durable non-executable backlog item and its promotion path. Used 3 times in 2,014 beads |
| `size: huge` in a plan file | lead (investigated, not a defect) | `202607/smoke_test_invalid_size.md` is a deliberate negative-path smoke fixture, not a validation gap |

## Sources

- **Both source reports** in this directory: `…__a.md` (codex/gpt-5.6-sol), `…__b.md` (claude/opus), and the prior
  `202607/sase_beads_full_potential_consolidated/` (2026-07-14, all three files).
- **Live store, 2026-07-25 ~10:20 EDT:** `sase bead stats|ready|list|blocked|show|doctor|onboard|--help`; direct
  analysis of `sase/repos/plans/beads/issues.jsonl` (2,014 records) and `beads/events/streams/*.jsonl`
  (343 files, 7,971 events).
- **Plan sidecar scan:** YAML parse of all 3,158 top-level plan files across `202602`–`202607` (tier, status,
  `bead_id`/`bead`, `phases:`/`depends_on:`/`size:`), cross-referenced against the store.
- **Source:** `src/sase/bead/` (`cli_crud.py`, `cli_work_from_plan_helpers.py`, `cli_work_from_plan_resume.py`,
  `db.py`, `jsonl.py`, `model.py`, `work.py`), `src/sase/main/parser_bead.py`,
  `src/sase/xprompt/_directive_values.py`, `src/sase/doctor/checks_beads.py`, `src/sase/sdd/plan_validate.py`,
  `src/sase/default_config.yml` (`bd/*` xprompts at 645-711, chops at 410-470),
  `src/sase/xprompts/skills/sase_beads.md`, `tests/test_bead/test_cli_golden.py`,
  `tests/test_bead/test_cli_changespec.py`.
- **Docs:** `docs/beads.md`, `docs/xprompt.md`, `docs/agent_families.md`, `docs/axe.md`, `docs/sdd.md`;
  `sase/memory/xprompts.md`, `sase/memory/generated_skills.md`.
- **Upstream:** `gh:gastownhall/beads` at HEAD `508d35921` (2026-07-25), verified commits `50003b803` (AD-01
  test-store firewall), `6e8af8bf8` (CAS update guards), `f94ea5bfe` (`bd sync` exit-code contract).
- **Earlier SASE research:** `202603/sase_beads.md`, `202605/axe_open_bead_tree.md`,
  `202605/greenfield_bead_storage_architecture.md`, `202605/bead_jsonl_merge_conflicts.md`.
- **Project inventory:** `sase project list` (three enabled projects; one bead store).

No bead records were created, edited, closed, reopened, or removed during this research.
