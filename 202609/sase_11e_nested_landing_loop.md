# Why `sase-11e` keeps growing child epics, and how to stop it

_Research date: 2026-09-16, about 10:05 EDT. All times are EDT unless marked `Z`._

## TL;DR

- **Why `sase-11e.8.6.5` exists.** The land agent for `sase-11e.8.6` found work that was
  still unfinished. Its prompt (`bd/land_epic`) says unresolved work the epic caused
  "remain[s] epic work: plan and finish them before closing." It may not close an
  incomplete epic or force-close one, and it has no way to stop and ask you. Land agents
  also start with `%auto`, so the plan it proposed was approved and launched about two
  seconds later with no human review. Given the rules it runs under, the agent had only
  one legal move.
- **Was the work actually needed?** About half of it.
  - Needed: live error and log messages still use the old words, and the full landing
    check (`just check-full`) has never been recorded as passing.
  - Not needed for you: the tribe-identity work protects against an independent,
    user-made `job` tribe. Your config doesn't have one.
  - Already fixed on its own: the "published floor" blocker. The fixed `sase-core-rs`
    release (0.34.36) reached PyPI at 09:47, six minutes before the land note at 09:53.
    The floor probe now reports it as ready to raise.
- **Should you worry?** Somewhat, but it isn't a runaway yet.
  - Signs it is converging: phase counts are shrinking (7 → 5 → 4 → 3), and each round
    closes most of its list.
  - Signs it may not stop: the same three themes (tribe identity, message wording,
    acceptance) come back every round. The bar is open-ended ("every reachable
    message", "every tribe operation"). Nothing in the system limits how deep the nesting
    can go.
  - Precedent: `sase-z4` went four levels deep and closed. `sase-xe` is six levels deep
    and still open after 10 days.
- **What to do now.** Before the round-3 land agent runs, decide what "done" means and
  write it down, and take auto-approval out of its path.
- **What to do long term.** Put a human approval gate (or a depth limit) on nested child
  epics, give land agents a sanctioned "stop and escalate" exit, fix the acceptance
  criteria when the plan is written, and make the full landing gate reliably passable.

## 1. What happened

| Round | Bead             | Created (EDT) | Phases                                       | Phases finished | Land audit           |
| ----- | ---------------- | ------------- | -------------------------------------------- | --------------- | -------------------- |
| 0     | `sase-11e`       | 09-15 15:18   | 7 (all size medium)                          | 17:20 → 00:39   | 01:02, found 4 gaps  |
| 1     | `sase-11e.8`     | 09-16 01:04   | 5                                            | 01:30 → 05:44   | 05:59, found 4 gaps  |
| 2     | `sase-11e.8.6`   | 09-16 06:01   | 4                                            | 06:39 → 09:24   | 09:53, found 2 gaps + acceptance |
| 3     | `sase-11e.8.6.5` | 09-16 09:55   | 3 (`.1` and `.2` in parallel, then `.3`)     | in progress     | pending              |

About 18.5 hours of wall-clock time so far. In the SASE repo alone, 15 commits cite
`sase-11e`, touching 239 files (+5,158 / −1,932). There are more commits in `sase-core`,
`sase-telegram`, and `chezmoi`.

**How each child epic got approved.** Each child plan was archived in the plans repo
within about a second of its `create_time`:

- `routine_job_identity_diagnostic_completion`: created 09:55:14, archived 09:55:15,
  bead `sase-11e.8.6.5` created 09:55:17, phases pre-claimed 09:56:43.
- The two earlier rounds show the same pattern.

This is by design. `render_multi_prompt` in `src/sase/bead/work.py` adds `%auto` to every
land agent. `plan_propose_handler.py` then stamps `parent_bead` and the plan is approved
immediately.

**The canceled-then-reopened episode.** `sase-11e` was canceled at 15:31 on 09-15 ("go
with Batch") and reopened at 15:41 ("Routine still works better"). That was before any
phase work finished, and the implementation follows the reopened decision. It is not a
cause of the nesting.

## 2. Why `sase-11e.8.6.5` was created

The `sase-11e.8.6` landing audit (bead note, 13:53Z) listed the following. I spot-checked
the source at `b9c28f25e8`.

1. **Job-tribe operations don't all use the new context-aware resolver.**
   - Round 2 added a resolver that uses config layers (the new `layers=` path) and that
     correctly rejects a config holding two distinct entries, `ace.tribes.chop` and
     `ace.tribes.job`.
   - But `set_tribe` (`src/sase/ace/agent_tribes.py:139`) passes only
     `stored_tribes`/`current_tribe`, never config layers. It can't see a collision
     that lives only in config.
   - About ten callers still use plain `parse_tribe_reference` (for example
     `scripts/_agent_chat_from_name_sources.py:153` and `agent/wait_watch/_resolve.py:527`).
     That means a wait (which knows about stored tribes) and the fork that follows it (which
     doesn't) can resolve `@job` to different identities.
   - Phase `sase-11e.8.6.2`'s close note says it covered "assignment/query/wait
     targeting." That overstates what was done.
2. **Live messages still use the old words.** Confirmed in source:
   - `conflicting chop context aliases` (`axe/chop_script_context.py:51`)
   - `could not resolve chop environment` (`axe/chop_runner_script.py:222`)
   - `Lumberjack '…' stopped` (`axe/lumberjack.py:548`)
   - `ChopNotFoundError` / `AmbiguousChopError` text, which the TUI passes through
     unchanged

   Phase `sase-11e.8.6.3` fixed the templates its plan named explicitly. It did not do
   the open-ended "audit every reachable message" part.
3. **Acceptance was incomplete.**
   - The upgrade fixture from `sase-11e.8.6.4` covers only the happy path using the new
     names. It skips the promised matrix: both flag states, edits, contextual tribe
     collisions, TUI diagnostics, timeouts, environment scrubbing, and link navigation.
   - No passing `just check-full` run was recorded. That phase's note lists `just check`
     only.
   - The published dependency floor couldn't be raised yet: the audit saw
     `ratchet_core_window` still reporting 0.34.35 as the newest complete release.

**Verdict.** Mechanically, yes: under the current rules the child epic was the only legal
move. On substance, only partly:

| Item                                                  | Legitimately unfinished?                                                                                           |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Message wording (item 2)                              | **Yes.** The approved root plan puts errors, logs, and notifications in scope.                                   |
| Full landing gate (part of item 3)                    | **Yes.** `decisions:two-speed-verification` makes `check-full` the landing gate.                                  |
| Wider acceptance matrix (part of item 3)              | Partly. It is written into every plan, but its breadth keeps growing.                                             |
| Contextual tribe identity (item 1)                    | **Weak for you.** Your `ace.tribes` has one automation tribe (`job`) and no separate `chop` or custom `job`, so the collision can't happen in your config. I didn't inspect athena's tribe-assignment store for historical `job` rows. |
| Published floor (part of item 3)                     | **Already fixed on its own.** The 0.34.36 wheels were uploaded 13:47:38–13:47:47Z. `tools/probe_core_floor --advisory` now returns `stale_actionable` (the declared floor, 0.34.35, lacks 20 capabilities that the published 0.34.36 has), and `ratchet_core_window --report-only` now proposes moving the lock to 0.34.36. |

A human reviewer would likely have reduced this round to one small wording phase plus
acceptance, and filed the tribe edge case as a task.

## 3. Why the chain keeps growing

### 3.1 The same themes keep coming back

| Theme                           | Round 0                                     | Round 1      | Round 2        | Round 3          |
| ------------------------------- | ------------------------------------------- | ------------ | -------------- | ---------------- |
| Job/chop tribe identity         | `.4` (alias in Python only; follow-up proposed) | `.8.3`   | `.8.6.2`       | `.8.6.5.1`       |
| Old-word messages               | `.3`, `.4`                                  | `.8.4`       | `.8.6.3`       | `.8.6.5.2`       |
| Acceptance / full gate          | `.7`                                        | `.8.5`       | `.8.6.4`       | `.8.6.5.3`       |
| Config normalization and edits  | `.1`, `.4`                                  | `.8.1`, `.8.2` | `.8.6.1`     | resolved         |
| CI core pin                     | n/a                                         | found at landing | `.8.6.4`   | resolved         |
| Unsafe whole-string substitution | `.3`, `.4`                                 | `.8.4`       | resolved       | n/a              |

Some themes are finished; the three open-ended ones are not. Tribe identity, message
wording, and acceptance have each gone around four times.

### 3.2 Structural causes, most important first

1. **No human checkpoint and no depth limit.**
   - Land agents always get `%auto`, so a child plan is approved the moment it is
     proposed.
   - Nothing counts how deep the nesting is or notices that a theme is repeating.
   - The 2026-08-15 change `87a569884f` ("resume nested epic landing handoffs") made
     nested landings resume their parents cleanly. It didn't add any limit.
2. **The land agent has no "stop" exit.**
   - `bd/land_epic` allows three outcomes: close (only if truly complete), force-close
     as `canceled` or `superseded`, or plan more work. Forcing is explicitly forbidden as
     a way to push a landing through.
   - There's no "raise a question for the owner" branch before planning another child.
     The only stop-and-report instruction applies to *ancestor* closure after a child
     lands.
3. **The finish line is open-ended.**
   - Each plan lists specific failing examples, then adds a clause like "audit every
     reachable message" or "every job tribe operation," plus a large acceptance matrix.
   - Workers fix the named examples and close their phases. The next auditor digs into
     the open-ended clause and always finds another layer. Every plan also carries the
     earlier plans' requirements forward ("Their compatibility decisions remain in
     force"), so the requirements only grow.
4. **The auditors use stronger models than the implementers.**
   - Size-medium phases go to `@medium` (`codex/gpt-5.5 | claude/sonnet | grok-4.6`
     at `@xhigh`).
   - Land agents use `@large`, or `@xlarge` for epics with at least 5 phases (the
     shipped aliases resolve to Opus / GPT-5.6-sol).
   - This is a likely contributing factor, not a proven one: a stronger reviewer
     systematically finds what a weaker implementer missed or overstated (see the
     `.8.6.2` note).
5. **The full landing gate never actually runs green inside the chain.**
   - Every acceptance phase is told to run `just check-full` through `/sase_monitor`.
     None of the three recorded a full green run: `.8.5` ran "the full pytest cost lane
     from just check-full," and `.8.6.4` ran `just check` only.
   - `sase-j0` (`check-full` red on test-cost budgets, 38 +1s, open since 08-10) shows the
     gate has been unreliable on the shared host for a month.
   - If acceptance can't produce the evidence, every land agent will correctly refuse to
     close, and will plan acceptance again.
6. **External waits are handled as code work.** Waiting on a PyPI release was turned into
   a phase-level "blocker" inside a child epic. The release landed minutes later. If a
   release had been genuinely late, an acceptance phase that can't raise the floor would
   fail its land audit and produce another round.
7. **The root epic's scope was large.**
   - A rename across 5 repositories, split into 7 medium phases, even though the plan
     itself calls authoring it "xlarge work."
   - The hardest part (built-in tribe alias semantics with collision safety) was bundled
     with mechanical renaming. So the long pole kept blocking closure of everything else.
   - I couldn't retrieve the original prompt locally (`sase agent prompts show` found no
     archive entry on this machine), so I can't tell whether you explicitly asked for the
     collision-safety requirement or the planner added it. The approved root plan does
     include it.

## 4. Should you worry?

**Moderately.** The evidence cuts both ways.

**Signs it will settle:**

- Phase counts are shrinking.
- Each round's landing audit reports narrower gaps: round 0 flagged whole subsystems
  bypassing the Rust projection; round 2 flagged a missing `layers=` argument and
  specific strings.
- Several themes are closed for good (config edits, CI pin, unsafe substitution).
- Round 3 runs its two work phases in parallel, so it should be faster.

**Base rates (all 634 root plan beads in the store):**

- 62 (about 10%) grew child epics.
- 7 went three or more levels deep. Of those:

| Root       | Depth | Child epics | Outcome                                                    |
| ---------- | ----- | ----------- | ---------------------------------------------------------- |
| `sase-ns`  | 3     | 3           | closed the same day                                        |
| `sase-xy`  | 3     | 4           | closed after 1 day                                         |
| `sase-zt`  | 3     | 3           | closed after 2 days                                        |
| `sase-z4`  | 4     | 4           | closed after 4 days; later rounds were "core pin / published-package proof," like here |
| `sase-zw`  | 3     | 3           | still open since 09-12 ("Complete the remaining retention landing contracts") |
| `sase-11e` | 3     | 3           | this epic                                                  |
| `sase-xe`  | 6     | 11          | still open since 09-06                                     |

Every root at depth 3 or more was created in August or September, so the pattern is
recent and becoming more common.

**Signs it may not stop:**

- Round 3's acceptance phase must, all at once:
  - produce a green `check-full` at a recorded SHA,
  - raise the published floor through the supported workflow, and
  - cover the widest matrix so far.
- If any of these is missed, or if the auditor finds one more old-word string or one
  more `parse_tribe_reference` caller, the rules require `sase-11e.8.6.5.4`, and it will
  be approved automatically.

## 5. Getting `sase-11e` back on track now

These agents run on **athena**; do the steps there. The round-3 land agent
(`sase-11e.8.6.5.land`) is waiting for phases `.1`–`.3`.

1. **Decide what "done" means and write it on the epic.** The land prompt tells the land
   agent to read the epic bead's own notes and confirm each one was addressed, so an
   owner note is the most direct lever. Be aware it is a strong nudge, not a guarantee:
   the prompt's "remaining work is epic work" rule still applies. Suggested content for
   `sase bead note sase-11e.8.6.5 "..."`:
   - **OWNER DECISION: this is the final child epic.** Landing requires exactly:
     - (a) the listed message owners use routine/job wording, with a regression test for
       each;
     - (b) `set_tribe` and the wait→fork path agree on identity, with one test for each
       (no further caller audit);
     - (c) `sase-core-rs` floor raised to 0.34.36 through the supported ratchet;
     - (d) `just check-full` green at a recorded SHA, where failures confined to the
       `sase-j0` test-cost budget gate are accepted with that evidence.
   - **Anything else goes to a task.** Any other old-word text or edge case is filed with
     `/sase_new_task` and does not block closure.
   - **Do not open another child epic.** If (a)–(d) can't be met, record a blocker note
     and stop without proposing a child epic.
2. **Take auto-approval out of the path (the guaranteed lever).**
   - Stop the waiting land agent (`sase agent kill sase-11e.8.6.5.land`).
   - After phases `.1`–`.3` close, launch the land prompt yourself without `%auto`
     (`#bd/land_epic:sase-11e.8.6.5`). Any child plan it proposes will then wait in your
     plan-approval queue instead of launching.
   - Don't re-run `sase bead work sase-11e.8.6.5` to recover: that re-adds `%auto`.
   - I haven't exercised this manual relaunch path end to end.
3. **Cut the tribe edge case unless you actually need it.**
   - Your config has no independent `job` tribe. If athena's tribe-assignment store also
     has no historical `tribe: job` rows, the contextual-resolution work is purely
     defensive.
   - Consider settling for "config validation reports the collision," and filing the
     assignment/fork follow-through as a task.
4. **Tell acceptance the floor is unblocked.** 0.34.36 is on PyPI and
   `probe_core_floor --advisory` says the floor can move. Acceptance should run the
   supported window ratchet, not treat this as a blocker.
5. **If round 3's audit still finds gaps**, don't let a round 4 start automatically.
   - File the leftovers as task beads.
   - Close the chain normally from the bottom up (`sase-11e.8.6.5` → `sase-11e.8.6` →
     `sase-11e.8` → `sase-11e`). The descendant guard allows this once every phase is
     closed. Each close still needs the epic-symbols check, `just symvision`, and the
     plan's `status: done`.
   - Use `--force` only for a real `canceled` or `superseded` decision.

## 6. Preventing this in the future

Ordered by impact.

1. **Put a human gate on nested child epics.**
   - Make land-agent auto-approval depth-aware. For example, in `render_multi_prompt`
     (`src/sase/bead/work.py`), omit `%auto` when the epic already has a plan-bead
     parent. Or, in `plan_propose_handler.py`, force a plan-approval gate when the
     stamped `parent_bead` is at or beyond a configured depth.
   - Expose the threshold as config (for example
     `bead.nested_epic_auto_approve_max_depth: 1`).
   - This one change turns an unbounded loop into a bounded one that you review.
2. **Give land agents a sanctioned escalation exit in `bd/land_epic`.**
   - Before planning more work, the agent compares the remaining-work list with the
     parent's landing note. If a theme is repeating, or the epic is already a child at
     the depth limit, it writes a blocker note and raises a question or gate instead of
     proposing a plan.
   - Also let land agents route "new, non-regression discoveries" to task beads without
     blocking closure. Right now "caused by this epic" is read broadly enough that
     everything blocks.
3. **Freeze acceptance criteria when the plan is written.**
   - Epic plans should end with a numbered, checkable definition of done: named failing
     examples plus exact commands.
   - Land agents judge completion against that list and treat anything beyond it as a
     follow-up.
   - Discourage open-ended clauses like "audit every reachable message" unless they come
     with a mechanical check, such as a grep-based lint whose allowlist is reviewed at
     plan time.
4. **Make the landing audit's failing examples into tests first.**
   - Child-plan phases should write the audit's failing examples as tests that fail
     before changing code.
   - Close notes should list each example and the test that proves it, so claims like
     `.8.6.2`'s "assignment/query/wait targeting" can be checked.
5. **Make the full landing gate passable and owned by one agent.**
   - Fix or recalibrate `sase-j0`, or define a standard "known-red budget" exception the
     land agent may accept with evidence.
   - Consider having the land agent (or one dedicated acceptance phase at `@large`)
     own the monitor-based `check-full` run, so the evidence comes from the same agent
     that rules on it.
6. **Keep external waits out of child epics.** Treat "wait for release X on PyPI" as a
   `/sase_monitor` or `%w`-style wait on the landing, not as unfinished code work that
   justifies a new plan.
7. **Scope epics so the hard part stands alone.**
   - For renames, split "change user-visible wording" (mechanical and quick to verify)
     from "alias and identity semantics with collision safety" (hard, and open-ended at
     the edges).
   - Then the easy part can land even if the hard part needs more rounds.
8. **Close the model gap where it matters.** Route acceptance phases, and phases in child
   epics, to `@large`. Or accept that `@medium` implementers need test-first examples
   from the audit (item 4).
9. **Make depth visible.** Add a routine job, or an Agents/Artifacts indicator, that
   notifies when an epic reaches depth 2 or more or has been open more than about
   12 hours, so you notice before round 3.

## Evidence consulted

- **Beads:** `sase bead show` / `history` / JSON notes for `sase-11e`, `sase-11e.8`,
  `sase-11e.8.6`, `sase-11e.8.6.5`, all 19 phase beads, and `sase-j0`. A store-wide scan
  of 735 plan beads for child-epic depth.
- **Plans:** `plan:202609/axe_routines_jobs.md`,
  `plan:202609/axe_routine_job_landing_repairs.md`,
  `plan:202609/routine_job_final_contract_repairs.md`,
  `plan:202609/routine_job_identity_diagnostic_completion.md`, plus the plans repo
  commit timestamps.
- **Source:**
  - `src/sase/default_config.yml` (`bd/land_epic`, `bd/work_phase_bead`, lander model
    defaults)
  - `src/sase/bead/work.py` (land segment `%auto`)
  - `src/sase/main/plan_propose_handler.py` and `plan_approve_handler.py` (how
    `parent_bead` is stamped and auto-approval is resolved)
  - `src/sase/ace/agent_tribes.py:139`, the `parse_tribe_reference` callers, and the
    message sites cited above
  - `git log -S` for when the land-prompt rules were introduced (`2ec86131dc`,
    `87a569884f`)
- **Tools:** `tools/ratchet_core_window --report-only`, `tools/probe_core_floor --advisory`,
  `sase config show -k ace` / `-k llm_provider`.
- **Memory:** `sase_beads.md`, `lint_and_test.md`, `decisions:two-speed-verification`.
- **Not available:** the land agents' chat transcripts (they ran on athena and weren't
  mirrored here) and the original prompt archive entry.
