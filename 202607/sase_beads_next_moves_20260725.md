# SASE Beads: Next Moves (2026-07-25)

Date: 2026-07-25

## Scope And Relationship To The Prior Report

This report answers the same question as `202607/sase_beads_full_potential_consolidated/` (2026-07-14) — *am I using
beads to their full potential?* — but it is **not** a restatement. The store changed materially in the eleven days
between the two reports, and that change invalidates the prior report's headline diagnosis and reorders its
recommendations.

Everything numeric below was measured directly on 2026-07-25 against the live store
(`sase/repos/plans/beads/`, 2,014 beads) and the live CLI. Where a prior-report claim is now stale, that is stated
explicitly.

Method: live store analysis (`issues.jsonl` + `sase bead` CLI), plan-sidecar frontmatter scan (3,154 plan files),
source reading (`src/sase/bead/`, `src/sase/xprompt/`, `src/sase/default_config.yml`), git history since 2026-07-13,
and a fresh upstream check of `gastownhall/beads`.

## Headline: The Prior Report's Central Claim Is Now Obsolete

The 2026-07-14 report opened with **"Beads are a completed-work ledger, not a living memory — 0 open, 0 in progress."**

That is no longer true:

| Measure | 2026-07-14 | 2026-07-25 | Δ |
|---|---|---|---|
| Total beads | 1,479 | 2,014 | +535 |
| Open | 0 | 21 | +21 |
| In progress | 0 | 8 | +8 |
| Closed | 1,479 | 1,985 | +506 |
| Beads created in window | — | 539 in 11 days (~49/day) | — |

There is now a real standing backlog: 21 open, 8 in progress, 10 blocked with live dependency edges across five
concurrent epics (`sase-92`, `sase-94`, `sase-95`, `sase-96`, `sase-99`). Dependency depth is genuine — one bead has 8
blockers, 1,270 beads carry at least one dependency edge.

**This flips the ranking.** The prior report deferred three items — atomic claim, liveness reconcile, ready-queue
hygiene — on the explicit grounds that "the manual claim loop is essentially unused" and there is no standing backlog to
claim from. Both premises are now false. Meanwhile the capture problem it ranked #1 has partly solved itself by other
means (epic velocity), while three *new* defects appeared that only manifest once a backlog exists.

The engine also kept improving: 56 commits touched `src/sase/bead/` in the window, shipping the `claimed` status and
full claim lifecycle, phase `--size` routing, atomic multi-bead `rm`, bead-gated waits, and child epics owned by phases.
**Not one of them was a memory-half item.** The pattern from the prior report holds: the execution engine gets richer
every week; the memory, hygiene, and discoverability halves get nothing.

## Finding 1 (New, Live, Highest Severity): The Test Suite Writes Into The Production Bead Store

Five of the 21 open beads are pytest artifacts that leaked into the real store **today**:

| Bead | Created | Title | PLAN link |
|---|---|---|---|
| `sase-97` | 2026-07-25T12:19:43Z | "Created Epic" | `.localtmp/pytest-of-bryan/pytest-0/popen-gw7/test_bead_cli_golden_contract_1/…` |
| `sase-9a` | 2026-07-25T13:05:05Z | "Created" | `plan.md` |
| `sase-9b` | 2026-07-25T13:05:11Z | "Epic" | `plan.md` |
| `sase-9c` | 2026-07-25T13:05:15Z | "Epic" | `sdd/plans/202605/roadmap.md` |
| `sase-9d` | 2026-07-25T13:05:20Z | "Epic" | `…/sase_17/.pytest_cache/tmp/pytest-of-bryan/…/test_create_plan_preserves_ext0/…` |

`sase-9a`–`sase-9d` were created within 20 seconds of each other — a single parallel pytest run. `sase-97` carries
`assignee: bob`, `ChangeSpec: created_epic`, `Bug ID: BUG-9` — all fixture values. Sources: `tests/test_bead/test_cli_golden.py`
and `tests/test_bead/test_cli_changespec.py`. One PLAN path points into a *sibling workspace's* pytest cache
(`sase_17`), so the leak is not confined to one checkout.

Why this is the top item rather than a curiosity:

1. **It poisons the queue agents are told to drain.** `sase bead ready` returns 11 beads; 5 of them (45%) are this
   garbage. The shipped `bd/next` xprompt instructs an agent verbatim to *"run `sase bead ready`… claim the next ready
   bead by marking it as in-progress, complete the work associated with it, and then close the bead."* An agent running
   `#bd/next` today has a coin-flip chance of picking up a fixture bead and attempting to "implement" `plan.md`.
2. **It consumes real IDs.** These beads hold `sase-97` and `sase-9a`–`9d` in the production ID sequence permanently.
3. **It is accelerating.** All five appeared today; `sase bead stats` grew ~49 beads/day. Whatever rate this leaks at,
   it compounds against the ready queue.
4. **The pattern is already recognized elsewhere in SASE and unfixed here.** Closed bead `sase-8g.11` — "Keep tests out
   of production state" — did exactly this for the metrics DB and axe logs. The bead store was not covered.
5. **Upstream fixed precisely this one day ago.** `gastownhall/beads` commit `50003b803` (2026-07-24), "refuse test DBs
   on production servers (AD-01)", adds a production-port guard plus a defense-in-depth database-name firewall that
   refuses test-named stores unless the harness opts into a dedicated test lane. Independent convergence on the same
   failure mode is about as strong a signal as this kind of research produces.

The cheap fix is a two-sided guard: tests set an explicit env opt-in, and the store refuses writes from a process that
has not set it when the resolved store path is the real sidecar. Immediate cleanup is one command — `sase bead rm` gained
atomic multi-bead removal in `fed18866e`.

## Finding 2 (New): The Two Prompts That Run Most Often Explicitly Forbid Capture

The prior report's #1 recommendation was to *"bake 'file a standalone bead for any discovered follow-up' into the
`work_phase_bead` and `land_epic` xprompts."* Reading those prompts today shows the situation is worse than "the habit
is missing" — **the habit is prohibited**:

- `bd/work_phase_bead` (`default_config.yml:695`), the prompt every phase agent runs, ends: *"Do NOT close the parent
  epic. **Do NOT create new beads.**"*
- `bd/next` (`default_config.yml`), the ready-queue driver: *"**IMPORTANT: Do NOT create any beads of your own.** You
  are meant to work the pre-existing ready bead that you select."*

These prohibitions are defensible as written — they stop a phase agent from silently expanding scope. But they are
absolute, and they are attached to the two roles with the best possible view of discovered work. The result is
structural: the agents that find follow-up work are the agents forbidden from recording it. No amount of capture
*tooling* moves the needle while the prompt says no.

The prior report already identified the right shape of the fix (phase agents *propose*, the land agent files). What is
new here is that this is a **prompt edit, not a feature** — the prohibition can be narrowed from "do not create beads"
to "do not create beads for yourself to work; record discovered follow-up as a proposal in your bead notes for the land
agent" without any Rust, CLI, or schema change. `bd/land_epic` already tells the land agent to read every child bead's
notes, so the delivery channel exists today.

## Finding 3 (New): The Shadow Backlog — 273 `wip` Plan Files, 243 Invisible To Beads

Scanning all 3,154 top-level plan files in the plans sidecar:

| Plan frontmatter `status:` | Count |
|---|---|
| `done` | 2,702 |
| **`wip`** | **273** |
| `complete` (non-canonical duplicate of `done`) | 34 |
| none | 102 |
| `draft` / `handoff` / `pending` / `proposed` / `active` / `completed` / `ready` / `planned` / `new` / `PROPOSED` / `not` / `open` | 43 combined |

Only **30 of the 273 `wip` plans carry a bead**. The other **243 are in-flight-looking work that beads cannot see** —
concentrated in recent months (104 in 202607, 67 in 202605, 49 in 202604, 39 in 202606). This is a second, informal,
free-text status system running in parallel with the bead store, with 12 distinct spellings of "not done" and no
queue, no dependency edges, and no `ready` command.

Coverage by tier:

- **Tales: 2,712 plan files, 2,671 with no bead (98.5%).** Consistent with the prior report's ~87% estimate, measured
  more precisely.
- **Epics: 442 plan files vs 320 plan beads.** Even the epic path — the one beads was built for — has gaps.

The prior report's "tale policy: don't force ceremony onto tales" remains right. But 243 stale `wip` markers is not
ceremony avoidance, it is an unmanaged queue. The cheap move is not to bead every tale; it is to make plan `status:`
a *derived* view (a `sase plan` filter or a doctor check that reports `wip` plans older than N days) so the shadow
backlog becomes visible without new plumbing.

## Finding 4 (Improved, Still Broken): Plan↔Bead Linkage Fails In Both Directions

The prior report measured 8 of 228 `design` links resolving. Today:

| Measure | 2026-07-14 | 2026-07-25 |
|---|---|---|
| Beads with a `design` link | 228 | 334 |
| Links that resolve as written | 8 (3.5%) | **105 (31.4%)** |
| Broken links | 220 | **229** |
| Broken but basename-recoverable under `plans/` | 220 | **211 of 229 (92%)** |

Real improvement in *rate*, no improvement in *absolute count* — new beads resolve, the historical tail does not. Split
today: 141 absolute paths, 193 relative.

The new measurement is the **reverse direction**, which the prior report did not check:

- **60 plan files carry a `bead:` frontmatter ID that does not exist in the store** — e.g. `202602/claude_ask_user_question.md`
  → `sase-5qu`, `202602/vcs_plugins_v3_1.md` → `sase-svxv`, `202602/axe_lumberjacks.md` → `sase-0xd`. These are
  pre-migration ID-scheme survivors. Any tool that trusts plan frontmatter to find a bead hits a hard miss 13% of the
  time (60 of 454 bead-linked plans).
- **25 closed beads whose plan file is still `wip` or `handoff`** — `202606/finish_sase_4j_publish.md` (`sase-4j`),
  `202606/prompt_command_completion.md` (`sase-4o`), `202606/log_panel.md` (`sase-4t`), and 22 more.
- **0 done plans with a non-closed bead.** The land agent's "set `status: done` in the plan frontmatter" step works in
  the direction it covers; nothing repairs the other direction.

`sase bead doctor` still validates none of this. Its entire output today is `WARNING: beads.db missing`. The
`sase doctor` integration (`src/sase/doctor/checks_beads.py`) adds one genuinely good new check — claimed beads with no
resolvable agent artifact — but nothing about link integrity.

## Finding 5 (Confirmed, Unchanged): History Is Recorded And Invisible

1,587 beads carry notes; **1,447 of them (91%) begin with `COMMIT`**. The commit hook still overwrites the mutable
`notes` field last-write-wins, so a phase agent's verification summary or blocked-state handoff is replaced by
bookkeeping the moment the commit lands. The event streams retain every revision; no CLI surface exposes them. There is
still no `sase bead history`, no appending `sase bead note`.

One thing did improve without a feature: **`close --reason` is now used 71 times** (3.6% of closures), up from
effectively zero. The prior report listed "pass `--reason` when a closure is not an ordinary completion" as a
practice change; it partly took. That is evidence the practice-change lever works.

## Finding 6: Shipped Capabilities You Are Not Using

This is the direct answer to "new and useful ways to use beads." Every item below **already works today** — no feature
work required. Most are invisible because the generated `sase_beads` skill does not mention them.

### 6a. `%wait(bead=<id>)` — beads as a cross-agent synchronization primitive

`src/sase/xprompt/_directive_values.py` implements `%wait(bead=<id>)`, and multiple beads can gate one agent
(`%wait(bead=sase-87.1, bead=sase-87.2)`). The agent blocks until those beads close. This is a general-purpose barrier
that works **outside** `sase bead work` — any hand-launched agent can wait on any bead.

It is documented nowhere the agent will see it: `sase/memory/xprompts.md` documents only `%wait:<n>` and
`%wait(time=…)`. The `sase_beads` skill never mentions waits at all.

*Usage patterns this unlocks:* park a follow-up agent behind an in-flight epic phase without joining its clan; gate a
docs or release agent on several unrelated epics; sequence work across two different epics that have no bead-graph
relationship.

### 6b. `%id(<name>, bead=<id>)` — bind an ad-hoc agent to an existing bead

`resolve_launch_bead_id` accepts a `bead=` keyword on `%id`. A manually launched agent can adopt a bead, which gives it
the full claim lifecycle (`claimed` → `in_progress` → released on death), the bead section in the ACE prompt panel, and
makes it a valid target for someone else's `%wait(bead=…)`.

*This is the missing piece for using beads outside epics.* Today beads are effectively only reachable through
`sase bead work`. With `%id(…, bead=…)`, the 21 open beads become launchable individually, by hand, with full runtime
integration — which is exactly what a standing backlog needs and what did not matter when the backlog was empty.

### 6c. `bd/next` — a ready-queue driver that only became viable this month

`#bd/next` picks the next ready non-epic bead, claims it, works it, closes it. With 0 open beads it was dead code;
with 21 open beads it is a working "drain the backlog" verb. Two caveats before leaning on it: Finding 1 (it will pick
fixture beads) and Finding 2 (it forbids capture).

### 6d. Phase `--size` routing — half the range is unused

`--size {xsmall,small,medium,large,xlarge}` routes phases to model pools via role aliases
(`xsmall_phase_worker`, `big_epic_lander`, `default_config.yml:492`). Actual usage across 2,014 beads: `medium` 110,
`small` 55, `large` 10, **`xsmall` 0, `xlarge` 0**, unset 1,839. The two ends of the cost/capability curve — the cheap
lane for mechanical phases and the heavy lane for the genuinely hard one — have never been exercised. Related:
`bead.big_epic_phase_threshold: 5` auto-selects `@big_epic_lander` for epics with ≥5 authored phases.

### 6e. `--changespec` / `--bug-id` — 0 uses in 2,014 beads

`sase bead create --changespec <name> --bug-id <id>` attaches a ChangeSpec to a plan bead (`cli_crud.py:72-117`;
plan-beads only, `--bug-id` requires `--changespec`). Epic plan frontmatter carries `changespec:` and `bug_id:` fields
too. Usage: **zero**, unchanged from the prior report despite the flags being surfaced. This is the designed seam
between the bead graph and the CL/PR lifecycle, completely unexercised.

### 6f. Child epics owned by phases — recursive decomposition, barely used

`sase-7z` shipped child epics owned by phases and `sase-7z.5` associates proposed epics with parent beads;
`sase bead work --parent <bead>|top-level` and `plan(<file>,<parent_id>)` express it. Usage: **12 plan beads have a
parent** out of 320. ID depth shows 57 beads at depth 2 and 3 at depth 3, so the machinery works. When a phase turns out
to be an epic in disguise — which is the normal failure mode of epic planning — this is the sanctioned escape hatch
instead of stuffing it back into one phase or filing an unrelated top-level epic.

### 6g. `sase bead work --json` and `--dry-run`

`work` is the only verb with `--json` (one machine-readable result object) and the only one with `--dry-run` (preview
the wave plan, change nothing). `--dry-run` before any epic with fan-in dependencies remains the cheapest correctness
check available. `--json` makes launches scriptable — the prerequisite for chaining epic launches from a hook or a
future `sase task`.

### 6h. `sase bead onboard` is much better than the `sase_beads` skill

The skill documents 7 verbs (`create`, `dep`, `list`, `ready`, `search`, `show`, `update`) and mentions `work` only in
prose, with no usage example. The CLI has 18: `blocked close create dep doctor init list onboard open ready
resolve-conflicts rm search show stats sync update work`. `sase bead onboard` documents nearly all of them — but no
agent is ever told it exists, and its examples still use retired `sdd/plans/` and `sdd/beads/` paths, and omit
`--size`, `--model`, `--changespec`, `--json`, `--dry-run`, and plan-file launches.

The prior report ranked the skill rewrite #7. Since then the CLI grew `claimed`, `--size`, `rm`, and bead-gated waits —
**the documentation gap widened while the report sat**. Agents cannot use what they are never taught, and every item in
6a–6g above is invisible from the skill alone.

## Upstream Delta Check (`gastownhall/beads`, HEAD `508d35921`, 2026-07-25)

298 commits in the eleven days since the prior report's check. The direction confirms the prior report's
anti-recommendation emphatically: replica-aware leases, `granted_node` provenance, Dolt-backed conflict tests,
domain-aware three-way auto-merge, `bd sync` as a federation loop, cross-replica reclaim guards. **Do not follow.**
SASE's event-sourced store already solves the problem this machinery exists to manage.

Three small items do transfer:

1. **`bd update --if-assignee/--if-status` compare-and-set guards** (`6e8af8bf8`). The commit message states the
   motivation plainly: *"the fleet's most common bug class is check-then-act on assignee/status — read state, then issue
   a blind update, and lose to a racing writer in the gap."* SASE's `ready`-then-`update` loop has exactly this shape,
   and — unlike on 2026-07-14 — it is now a loop with 21 real beads in it.
2. **AD-01 test-store firewall** (`50003b803`) — direct precedent for Finding 1, landed 2026-07-24.
3. **Exit codes as a machine contract.** `bd sync` returns 0/1/2/3 with distinct meanings plus a `--json` envelope, so a
   timer can branch without parsing prose. SASE has one `--json` verb and no documented exit-code contract.

## Ranked Recommendations

Ranking principle: **stop active corruption first, then unblock the backlog that now exists, then make it
discoverable.** This differs from the prior report's ordering because the store's state changed — items it deferred on
"no standing backlog" grounds are now live, and a new active defect outranks everything.

### 1. Stop the test suite from writing to the production bead store, and purge the five leaked beads

Highest severity, smallest fix, actively worsening. Two-sided guard: test harnesses set an explicit opt-in env var, and
the store refuses a write from a process without it when the resolved path is the real sidecar. Then
`sase bead rm sase-97 sase-9a sase-9b sase-9c sase-9d` (atomic multi-remove shipped in `fed18866e`) to clear the ready
queue. Follow `sase-8g.11`'s precedent for metrics/logs and upstream's AD-01 for the firewall shape. **Do this before
running `#bd/next` again.**

### 2. Rewrite the generated `sase_beads` skill — and teach the six unused capabilities

Was #7 in the prior report; promoted because the gap widened (7 documented verbs vs 18; `claimed`, `--size`, `rm`, and
bead-gated waits all shipped since) and because everything in Finding 6 is free capability blocked only by ignorance.
Must cover: `work` with real examples, `close --reason`, `open`, `rm`, `blocked`, `stats`, `doctor`, `onboard`,
`--size`, `--model`, `--changespec`, and — most valuably — **`%wait(bead=…)` and `%id(…, bead=…)`**, which belong in
`sase/memory/xprompts.md` as well. Edit the source template at `src/sase/xprompts/skills/sase_beads.md`
(per `memory/generated_skills.md`), and add a contract test comparing documented verbs against the argparse surface so
this cannot silently rot again. Pure documentation; zero Rust; largest capability-per-hour ratio on this list.

### 3. Narrow the capture prohibition in `bd/work_phase_bead` and `bd/land_epic`

A prompt edit, not a feature. Change "Do NOT create new beads" to "do not create beads for yourself to work; record any
discovered follow-up as a `PROPOSED FOLLOW-UP:` line in your bead notes." Add to `bd/land_epic` step 1: "collect
proposed follow-ups from child bead notes and file them." `bd/land_epic` already reads every child bead's notes, so the
channel exists. This delivers most of the prior report's #1 with none of its Rust cost, and it is the prerequisite for
a standalone capture bead ever being used. (The `close --reason` adoption — 0 → 71 uses — is evidence the
practice-change lever works here.)

### 4. Make `sase bead doctor` validate what it claims to check

Today it emits only `WARNING: beads.db missing`. Add: design links that do not resolve (229 today, 211 basename-
recoverable), plan `bead:` frontmatter IDs absent from the store (60), closed beads whose plan is still `wip` (25), and
beads whose PLAN path points into a temp/pytest directory (the Finding 1 detector). Pair with
`--fix-design-refs` to backfill from the 92% that are basename-recoverable. This is the prior report's #2 and #3
merged and re-scoped to *detection first* — cheap, additive, and it turns three of this report's findings into standing
regression guards instead of one-time cleanups.

### 5. Make the 21 open beads individually launchable and the shadow backlog visible

Two halves of "the backlog now exists, so make it workable":

- **Launchable:** document and use `%id(<name>, bead=<id>)` (6b) so any open bead can be worked by a hand-launched
  agent with full claim lifecycle — not only through `sase bead work`. Combine with `%wait(bead=…)` to sequence work
  across epics.
- **Visible:** a report of `wip` plan files older than N days (243 have no bead at all), so the shadow backlog stops
  being 12 spellings of "not done" scattered across 3,154 files. A doctor check or `sase plan` filter, not a schema
  change. Do **not** bead every tale.

### 6. Build the ACE open-bead tree

Was #5 in the prior report, when the tree would have rendered zero rows. With 21 open, 8 in progress, and 10 blocked
with real dependency edges, it now has content on day one. `202605/axe_open_bead_tree.md` already specs it.
Presentation-layer Python only; read/triage only, no TUI CRUD.

### 7. `--json` on `ready`, `list`, `show`, `blocked`, `stats` (+ documented exit codes)

Only `search --format json` and `work --json` exist. The Rust read layer already produces structured data. Prerequisite
for hooks, for #6 being cheap, and for anything scripting the backlog. Adopt upstream's discipline of exit codes as a
machine contract while you are in there.

### 8. `dep rm` / `dep list`, and compare-and-set on `update`

`sase bead dep` still has only `add` — removing a wrong edge means storage surgery, and 1,270 beads now carry edges.
Add `--if-status`/`--if-assignee` guards to `update` (upstream `6e8af8bf8`) to close the `ready`-then-`update` race,
which was theoretical on 2026-07-14 and is now a loop over 21 real beads. Both were deferred in the prior report on the
grounds that manual claiming was unused; that premise expired.

### 9. Exercise `--changespec`/`--bug-id` and the unused `--size` ends (practice, not product)

Zero uses of the ChangeSpec seam in 2,014 beads; zero uses of `xsmall`/`xlarge`. Try each on the next epic before
concluding they are wrong — a designed integration with no usage data is not evidence of a bad design, only of an
untried one.

### 10. Append-only notes and `sase bead history`

The prior report's #4, unchanged and still real (91% of notes are commit bookkeeping over 1,587 beads). Demoted only
because it is pure archive value: it improves the record of work already done, while #1–#5 affect work in flight.

### Watch — Don't Build Yet

- **Retention/compaction.** 2,014 beads and a growing projection at ~49 beads/day. Still not urgent while the open set
  is ~21, but the growth rate is now measurable and it was not before. A size/token early-warning in `sase bead doctor`
  is the cheap hedge.
- **Standalone capture bead kind.** The prior report's #1. Still the right eventual shape — but recommendation #3 tests
  the hypothesis for free. If notes-based follow-up proposals get filed and acted on, build the bead kind; if they do
  not, the tooling would not have been used either.

## Anti-Recommendations (Reaffirmed With Fresh Evidence)

- **No Dolt, daemons, leases, replicas, or federation.** 298 upstream commits in 11 days went almost entirely here.
  SASE's event store already solves it.
- **No molecules, formulas, wisps, gates, or agent mail.**
- **No priority levels or label taxonomy yet.** Still no query the dependency graph cannot answer.
- **No beading of tales.** 2,671 tales without beads is a policy, not a bug. Fix the *visibility* of `wip` plans
  instead.
- **No full TUI CRUD.** Read and triage only.

## Bottom Line

The prior report diagnosed an empty ledger and prescribed capture. Eleven days later the ledger is not empty — 21 open,
8 in progress, 539 beads created in the window — so the binding constraints moved. In priority order they are now:
**(1)** the test suite is actively corrupting the production store and poisoning the queue `#bd/next` drains;
**(2)** the skill teaches 7 of 18 verbs and none of the six genuinely useful capabilities that already ship —
`%wait(bead=…)`, `%id(…, bead=…)`, child epics, size routing, ChangeSpec attachment, `work --json/--dry-run`;
**(3)** the two most-run prompts forbid the capture habit outright, which is a text edit away from being fixed.

None of the top three requires touching the Rust core. That is the real headline: the highest-value beads work
available right now is a guard, a document, and two prompt sentences.

## Sources

- Live store, 2026-07-25: `sase bead stats|ready|list|blocked|show|doctor|onboard|--help`, direct analysis of
  `sase/repos/plans/beads/issues.jsonl` (2,014 records).
- Plan sidecar scan, 2026-07-25: 3,154 top-level plan files across `plans/2025??`–`plans/202607` (tier, status, `bead:`
  frontmatter, cross-referenced against the store).
- Source: `src/sase/bead/` (`cli_crud.py`, `model.py`, `db.py`), `src/sase/xprompt/_directive_values.py`,
  `src/sase/doctor/checks_beads.py`, `src/sase/default_config.yml` (`bead:` config, `bd/*` xprompts),
  `src/sase/xprompts/skills/sase_beads.md`, `tests/test_bead/test_cli_golden.py`, `tests/test_bead/test_cli_changespec.py`.
- Git history: 56 commits touching `src/sase/bead/` since 2026-07-13.
- Upstream: `gh:gastownhall/beads` HEAD `508d35921` (2026-07-25); commits `50003b803` (AD-01 test-store firewall),
  `6e8af8bf8` (CAS update guards), `f94ea5bfe` (`bd sync` exit-code contract); `CHANGELOG.md` unreleased section.
- Prior in-repo research: `202607/sase_beads_full_potential_consolidated/` (2026-07-14, all three files),
  `202605/axe_open_bead_tree.md`, `202603/sase_beads.md`.
