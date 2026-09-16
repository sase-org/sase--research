# Why `sase-11e.8.6.5.4` exists, and whether `sase-11e` will ever finish

_Research date: 2026-09-16, about 15:20 EDT. All times are EDT unless marked `Z`._

This follows up on `research:202609/sase_11e_nested_landing_loop.md`, written around
10:05 today. That report predicted a fourth round and explained the mechanism. This one
covers what happened since: why round 4 (`sase-11e.8.6.5.4`) was created, what changed,
and what to do now that round 4 is queued but hasn't started.

## TL;DR

- **Why round 4 exists.** The land agent for `sase-11e.8.6.5` found seven unfinished
  items, and its prompt only allows two outcomes: close a complete epic, or plan the
  remaining work. No human reviewed the plan. The note was written at 14:54, and the plan
  was archived at 14:58:08 and became a bead at 14:58:10.
- **Was it needed?** Partly. The seven items break down like this:
  - **Real, and your problem:** a doctor function that rewrites user text. It dates from
    round 0 and three landing audits missed it.
  - **Real, but caused by the fix itself:** a tribe-color regression that round 3's own
    commit introduced.
  - **A design problem, not a bug:** four items only exist because of how "job-tribe
    identity" was designed. That design guards against a user-defined `job` tribe, and
    athena has none: 1,893 stored `chop` tribe assignments, 0 `job`, and no custom `job`
    tribe in config. One of the four still matters to you (raw `job` gets saved, which
    would trigger the problem the design guards against).
  - **In scope but cosmetic:** leftover old wording in Python and Rust messages. The Rust
    part forces a new `sase-core` release before landing, which brings back the
    "published floor" wait that round 3 had just cleared.
  - **Still missing:** no round has ever recorded a green `just check-full`.
- **Should you worry?** Yes, more than this morning.
  - The signs of settling I cited earlier have reversed:
    - Phases per round went 7 → 5 → 4 → 3 → **5**.
    - The gap list grew from 3 to **7**.
    - Round 3 caused a regression.
  - Nothing has changed in how land agents are prompted or approved.
  - The owner note recommended this morning was never added.
  - A literal infinite loop is unlikely: `sase-z4` had the same 5 → 4 → 3 → 5 → 3 shape and
    closed after 4.5 days. But nothing *makes* it stop, and round 4's acceptance bar is the
    hardest yet.
- **What to do now.** Round 4's four work agents are still `QUEUED` on athena.
  1. Pause them.
  2. Write an owner decision on the epic:
     - Public `job` always means the built-in `chop` tribe.
     - The Rust wording change doesn't block landing.
     - Define exactly what `check-full` must show.
     - No round 5.
  3. Trim the phases to match that decision.
  4. Keep auto-approval out of the round-4 landing.
  The details are in section 4.
- **What prevents it long term.** A depth-aware approval gate on child epics, a "stop and
  escalate" exit for land agents, a rule that land audits can't add requirements the plan
  didn't have, and a `check-full` gate that can actually pass. None of these is filed or
  implemented yet.

## 1. Where things stand

| Round | Bead               | Created (EDT) | Phases               | Phases finished | Land audit  | Gaps found              |
| ----- | ------------------ | ------------- | -------------------- | --------------- | ----------- | ----------------------- |
| 0     | `sase-11e`         | 09-15 15:18   | 7 medium             | 17:20 → 00:39   | 09-16 01:02 | 5                       |
| 1     | `sase-11e.8`       | 09-16 01:04   | 5 medium             | 01:30 → 05:44   | 05:59       | 4                       |
| 2     | `sase-11e.8.6`     | 06:01         | 4 medium             | 06:39 → 09:24   | 09:53       | 2 areas + acceptance    |
| 3     | `sase-11e.8.6.5`   | 09:55         | 3 medium             | 11:45 → 13:07   | 14:54       | **7**                   |
| 4     | `sase-11e.8.6.5.4` | 14:58         | 4 medium + 1 small   | not started     | —           | —                       |

**Round 4 status on athena** (`sase agent list`, about 15:15):

- `.1` (gpt-5.5), `.2` (sonnet), `.3` (gpt-5.5), and `.4` (sonnet) are `QUEUED`.
- Acceptance `.5` (sonnet) is `WAITING` on them.
- `sase-11e.8.6.5.4.land` (claude-fable-5) is `WAITING`.

**Cost so far:**

- About 24 hours of wall-clock time.
- In the SASE repo alone, 18 commits cite `sase-11e`, touching 292 files (+5,752 / −2,061).
- Round 3 added three commits: `66e20c1c24` (33 files), `9759e5afe8` (14 files, +347), and
  `e17d4e0c0a` (6 files).
- There are more commits in `sase-core`, `sase-telegram`, and `chezmoi`.

**The earlier recommendations weren't applied:**

- `sase-11e.8.6.5` has only the land agent's note, and no owner decision.
- `bd/land_epic` (`src/sase/default_config.yml:1710`) is unchanged.
- The land segment still gets `%auto` (`src/sase/bead/work.py:475`).
- No bead tracks a depth limit or approval gate. I searched beads for "nested epic",
  "child epic", "auto-approv", "landing loop", and "epic depth".

## 2. Why `sase-11e.8.6.5.4` was created

### 2.1 How it happened

The rules are the same as this morning:

- **Step 3 of `bd/land_epic`:** "Unresolved issues caused by this epic remain epic work:
  plan and finish them before closing."
- **The only allowed non-close outcome:** "If steps 1-2 uncover remaining work, use your
  /sase_plan skill to plan it."
- **Auto-approval:** land agents always run with `%auto`, so the plan is approved as soon
  as it is proposed. `plan_propose_handler.py:160` then stamps the running epic as
  `parent_bead`.

Plans-repo history shows no pause for review:

- `0c496029` 14:58:08: "Archive approved plan routine_job_identity_diagnostic_residuals"
- `19fea14b` 14:58:23: "Link approved epic plan to its bead"

The land agent had no allowed way to stop and ask. Round 4 was the only outcome its rules
permitted.

### 2.2 What the round-3 audit found, and where each item came from

I spot-checked each item against current `master` (`06a53a0e51` / `b5f51b192e`).

| # | Gap (from the `sase-11e.8.6.5` land note)                                                                                                         | Where it came from                                                                                                                                                                                                   | Needed for you?                                                                                                                                                                              |
| - | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5 | `sase doctor` runs a whole-string `chop→job` / `lumberjack→routine` replace (`src/sase/doctor/checks_axe.py:190`, `_public_axe_text`)               | **Round-0 defect.** Added by `d2d30944dc` (phase `sase-11e.3`). Round 0's audit flagged doctor rewriting a path. Round 1's audit said "unsafe whole-string output substitution is fixed," but only status was fixed. Two more audits missed doctor. | **Yes.** It rewrites IDs, script names, user names, and legacy config paths, which the root plan forbids.                                                                                     |
| 4 | The neighbor modal loses the built-in tribe color for `@job`; wait-lane and panel-collapse lookups ignore context                                  | **Introduced by round 3.** `9759e5afe8` made `named_tribe_identity_colors` use its own input labels as "stored tribes." The phase note describes this as a fix, but callers pass public labels.                      | A real regression, but only for configs that color the tribe under the legacy `chop` key. Bundled defaults and your config use `job`, so you probably don't see it. I didn't check on screen. |
| 1 | `%id(tribe=job)`, `%clan(tribe=job)`, the TUI tribe modal, and AXE proposal text save the raw word `job` in agent metadata                          | A side effect of the **context-dependent identity design** (§2.3)                                                                                                                                                    | **Yes, as a latent bug.** The first launch that writes raw `job` creates "independent `job`" evidence, and later `@job` waits and forks stop matching your 1,893 `chop` agents. Athena has 0 such rows today. |
| 2 | A rejected tribe write leaves partial state (the collision check runs after `write_agent_meta`)                                                    | Same design                                                                                                                                                                                                          | **Low.** It needs a config defining both `ace.tribes.chop` and `ace.tribes.job`, and neither your config nor the bundled defaults does.                                                        |
| 3 | The runner's wait fast path checks one project, while fork and wait-checks check all projects; `clan_tribe` is ignored as evidence                 | Same design                                                                                                                                                                                                          | **Only with an independent `job` identity**, and none exists on athena.                                                                                                                      |
| 6 | Old wording in Python: the digest's `Lumberjack:` label, `no fresh chop probe`, `per-chop env`, backfill "chop budget", `JobReport` errors, launch-log labels, help text, and the routine editor | Root-plan scope ("errors, logs, notifications, editors"), found by a deeper sweep. I confirmed three of the sites in source.                                                                                          | In scope, but cosmetic. Could reasonably be a task.                                                                                                                                          |
| 7 | Old wording in Rust: `sase-core` `axe_chop` validation and target messages, plus the PyO3 `"chop result"` label                                   | Same scope                                                                                                                                                                                                           | Cosmetic, and **expensive to process** (§3.2).                                                                                                                                                |
| — | No green `just check-full` recorded                                                                                                               | Every round. `sase-11e.8.6.5.3` recorded only `just check`. `sase-j0` (check-full red on budgets, +38) is still open.                                                                                                | **Yes.** This is the landing gate (`decisions:two-speed-verification`).                                                                                                                        |

Round 3 did clear two things:

- The published floor: `sase-core-rs>=0.34.37`, pinned at `f822ebd`.
- The upgrade fixture across both flag states.

### 2.3 Why the tribe work keeps coming back

The root plan asked for something small (`plan:202609/axe_routines_jobs.md`):

- "`job`, displayed `@job`: resolve to the existing built-in automation identity; preserve
  historical assignments."
- "Detect an independently configured `job` tribe collision **and report it**."

The land audits then raised the requirement:

- **Round 1's plan** added "distinguish ordinary customization of the built-in automation
  tribe from an independently configured pre-existing `job` tribe."
- **Round 2's plan** said "mutation and targeting remain unsafe for an independent
  historical job tribe."

The result is a context-dependent alias. `@job` means the built-in `chop` tribe *unless*
stored data shows a separate `job` tribe. Once the meaning depends on stored data, two
things follow:

- **Every reader must use the same evidence**: wait fast path, wait-check job, fork,
  completion, colors, collapse, and query.
- **Every writer is part of that evidence**: `%id`, `%clan`, the TUI modal, and AXE
  proposals.

Each round fixed the callers its plan named. The next auditor then found the next reader
or writer. Gaps 1–4 in round 4 are that same pattern again. Worse, the design creates the
very problem it guards against: if any writer saves the public word `job` as-is, that
record *becomes* the "independent `job` identity."

Your data doesn't need any of this:

- Athena's `~/.sase/agent_tribes.json` has 1,893 `chop` assignments and **zero** `job`.
- None of 11,375 `agent_meta.json` files on athena has `tribe` or `clan_tribe` set to `job`.
- Your athena config defines only a `research` tribe.
- The bundled defaults define `job` and no separate `chop`.

The collision the whole design protects against has never occurred on your machines.

## 3. Should you worry that `sase-11e` goes on forever?

### 3.1 What changed since this morning

| Signal                             | This morning                        | Now                                                                                                                                              |
| ---------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Phases per round                   | shrinking (7 → 5 → 4 → 3)           | **grew** (3 → 5)                                                                                                                                 |
| Gaps per audit                     | narrowing                           | **grew** (2 + acceptance → 7)                                                                                                                    |
| Regressions caused by a repair     | none seen                           | **one** (`9759e5afe8` tribe colors)                                                                                                              |
| Published-floor blocker            | resolved on its own                 | **back**: phase `.4` changes Rust, and the plan says a missing wheel is "a real landing blocker"                                                  |
| Full landing gate                  | never recorded                      | still never recorded                                                                                                                             |
| Implementer vs. auditor models     | `@medium` vs. `@large` / `@xlarge`  | round 4: acceptance on **sonnet**, land on **claude-fable-5**                                                                                    |
| Owner intervention                 | recommended                         | none recorded                                                                                                                                    |

### 3.2 Why round 5 is likely if you do nothing

Round 4's acceptance phase (`.5`) must do all of the following:

- Extend the widest fixture matrix so far.
- Wait for release-plz to publish a new `sase-core-rs` with phase `.4`'s message changes,
  then ratchet the floor and pin.
- Run `just check-full` green through `/sase_monitor`. That gate has been red on
  budgets for a month (`sase-j0`).

If any one of these fails, or the Fable land agent finds one more reader of tribe evidence
or one more old-word string, the rules require round 5, and it is approved automatically.
The three open-ended themes (tribe identity, wording, acceptance) have each come back in
all five rounds.

### 3.3 Base rates

The store has 621 root plan beads, and 60 of them grew child epics.

**Roots that reached depth 3 or more:**

| Root       | Depth | Child epics | Phases per round   | Outcome                                            |
| ---------- | ----- | ----------- | ------------------ | -------------------------------------------------- |
| `sase-ns`  | 3     | 3           | —                  | closed in 0.1 days                                 |
| `sase-xy`  | 3     | 4           | —                  | closed in 0.7 days                                 |
| `sase-zt`  | 3     | 3           | —                  | closed in 1.6 days                                 |
| `sase-z4`  | 4     | 4           | 5 → 4 → 3 → 5 → 3  | closed in 4.5 days (its later rounds were core-pin and published-package proof) |
| `sase-zw`  | 3     | 3           | 7 → 6 → 7 → 7      | **still open after 4.1 days**, not shrinking       |
| `sase-11e` | 4     | 4           | 7 → 5 → 4 → 3 → 5  | open after 1.0 day                                 |
| `sase-xe`  | 6     | 11          | branching          | **still open after 10 days**, 7 unfinished child epics |

**Share of roots reaching depth 2 or more, by creation month:** 0 before July, 1 of 182
in July, 6 of 185 (3%) in August, and **9 of 67 (13%) in September**. This is a systemic
trend, not a one-off.

**Verdict.** `sase-11e` looks most like `sase-z4`: same shape, same release-and-floor tail.
That suggests it can finish, probably in one or two more rounds and a day or more. But
`sase-zw` and `sase-xe` show chains that stop shrinking. Only a human decision guarantees an
end.

## 4. Getting `sase-11e` back on track now

Do these steps on **athena**, before the queued phases start.

1. **Pause round 4.**
   - Command:
     `sase agent hold create -p -n sase-11e.8.6.5.4.1 -n sase-11e.8.6.5.4.2 -n sase-11e.8.6.5.4.3 -n sase-11e.8.6.5.4.4 -n sase-11e.8.6.5.4.land -T 12h`
     - `-p` freezes the named agents that are waiting or queued right now.
     - `-T` sets how long the hold lasts; after that it releases on its own.
   - The `hold` command landed today (`520c7dbf41`) and I haven't tested this exact usage.
     Check `sase agent hold list` afterward. If it doesn't hold them, kill the queued agents
     instead.
2. **Record an owner decision** with `sase bead note sase-11e.8.6.5.4 "..."`. The land
   agent must "review the epic bead's own notes" and confirm each was addressed.
   Suggested text:
   - **OWNER DECISION — final round. No further child epics under `sase-11e`.**
   - **Tribe semantics:** public `job` / `@job` always means the built-in `chop`
     identity. Config that defines both `ace.tribes.chop` and `ace.tribes.job` is a
     validation error reported by config and doctor. Independent historical `job` tribes
     are out of scope, because none exist.
   - **Required tribe work (only this):**
     - (a) Every tribe writer (`%id`, `%clan`, TUI modal, AXE proposals) stores `chop`
       for public `job`, and validates before writing.
     - (b) The `9759e5afe8` color regression is reverted or fixed, with a test.
   - **No more stored-evidence unification.**
   - **Doctor:** delete `_public_axe_text` and render canonical text at its owners,
     with a test proving IDs, script names, and paths pass through unchanged.
   - **Wording:** fix the Python items in gap 6 that are listed in the plan. The Rust
     wording change (phase `.4`) lands on its own and does **not** block landing, and a
     message-only core change does not require a floor raise.
   - **Landing gate:** `just check-full` at a recorded SHA. Failures confined to the
     `sase-j0` cost-budget checks are accepted with that evidence.
   - **Anything else** goes to a task through `/sase_new_task` and doesn't block landing.
     If the gate can't be met, record a blocker note and stop without proposing a plan.
3. **Trim the phases to match.**
   - **Keep `.1`** (tribe writes), but simplified by the decision above.
   - **Keep `.3`** (Python wording and doctor).
   - **Keep `.5`** (acceptance).
   - **`.2`** (evidence unification): either close it with
     `sase bead close sase-11e.8.6.5.4.2 --resolution canceled --reason "owner decision: fixed job alias; display regression moves to .1"`,
     or leave it with the note narrowing it to the color fix.
   - **`.4`** (Rust wording): either let it run as a non-blocking change, or cancel it and
     file a small task.
   - Closing a phase whose agent is held or killed interacts with `.5`'s `%w` wait, and I
     haven't tested that. If you cancel `.2` or `.4`, check that `.5` is admitted afterward.
     If it isn't, rerun `sase bead work sase-11e.8.6.5.4`. That reassigns only the
     phases that aren't closed yet.
4. **Keep auto-approval out of the landing.** This is the step that guarantees no round 5.
   - The waiting land agent carries `%auto`, and so does anything `sase bead work`
     relaunches. Before releasing the hold, kill `sase-11e.8.6.5.4.land`.
   - After `.5` closes, launch `#bd/land_epic:sase-11e.8.6.5.4` yourself without `%auto`.
     Any child plan it proposes will then wait in your plan-approval queue.
   - One land agent can close the whole chain. After closing round 4, the prompt walks up
     through `.8.6.5` → `.8.6` → `.8` → `sase-11e` while each remains complete. At an
     incomplete ancestor it only writes a note and stops; it never plans more work there.
5. **Release the hold** with `sase agent hold release` (see `-h` for choosing the hold)
   once steps 2–4 are done.
6. **If the round-4 audit still finds leftovers**, don't approve a round-5 plan. Put the
   items in task beads, and close the chain from the bottom up with normal closes. Use
   `--force` only for a real `canceled` or `superseded` decision.

A simpler alternative is to note-only step 2 and let round 4 run as-is. It's cheaper today,
but it keeps phase `.2`'s open-ended evidence work and phase `.4`'s release wait. Those are
the two things most likely to produce round 5.

## 5. Preventing this in the future

The list from this morning still applies. Here it is again, reordered by what round 4
taught.

1. **Put a human gate on nested child epics.** This is still the most important fix, and
   still unfiled.
   - Drop `%auto` from the land segment (`src/sase/bead/work.py:475`) when the epic already
     has a plan-bead parent.
   - Or force a plan-approval gate in `plan_propose_handler.py` (around line 160) when the
     stamped `parent_bead` is at or beyond a configured depth, for example
     `bead.nested_epic_auto_approve_max_depth: 1`.
2. **Give land agents a sanctioned stop, and stop them from adding requirements.** In
   `bd/land_epic`:
   - **Stop and escalate** when the epic is already a child at the depth limit, or when a
     theme repeats from the parent's landing note.
   - **Check completion against the approved root plan's acceptance criteria.** Hardening
     beyond them (like the independent-`job` design) goes to task beads or needs owner
     approval.
   - **Only real regressions and named unmet criteria** count as "caused by this epic."
3. **Avoid context-dependent aliases in renames.** A public alias whose meaning depends on
   global stored state turns every reader and writer into a place that can disagree. Prefer
   a fixed alias plus a validation error for the conflicting case. Planners should mark
   such a design as `xlarge` and give it its own epic, separate from the mechanical rename.
4. **Freeze a numbered definition of done in each plan.**
   - Child plans currently say "their compatibility decisions remain in force," so
     requirements pile up with each round. Require child plans to list which parent
     criteria are still unmet instead.
   - Open-ended clauses ("every reachable message") need a mechanical check, such as a
     grep lint with an allowlist reviewed when the plan is written.
5. **Write the audit's failing examples as tests first, at the call site.** `9759e5afe8`
   passed its own tests and still broke the neighbor modal, because the test used a
   different caller. Phases should reproduce each named example through the production
   caller before changing code.
6. **Make the landing gate passable.** Fix or recalibrate `sase-j0` (open a month, +38),
   or define a standard "known-red budget" exception the land agent may accept. Have the
   agent that judges the landing (the land agent, or an acceptance phase at `@large`) run
   `check-full` itself. Four rounds in a row were told to run it, and none recorded a
   green result.
7. **Keep release waits out of child epics.** A core change that only edits messages
   doesn't need a floor raise. When a real wait on PyPI is needed, it belongs in a
   `/sase_monitor` wait on the landing, not in a phase that fails its audit.
8. **Close the model gap on the phases that decide landing.** Round 4 runs acceptance on
   sonnet and landing on Fable 5. Route acceptance phases, and every phase inside a child
   epic, to `@large`.
9. **Make depth visible.** 13% of September roots reached depth 2 or more. Send a
   notification (or show a TUI badge) when an epic reaches depth 2 or has been open
   more than about 12 hours, so you can step in before round 3, not after round 4.

## Evidence consulted

- **Beads:**
  - `sase bead show` for `sase-11e`, `.8`, `.8.6`, `.8.6.5`, `.8.6.5.1`–`.3`,
    `.8.6.5.4`, and `.8.6.5.4.1`–`.5`.
  - `sase bead search` for prevention work.
  - A store-wide JSON export (741 plan beads, all phase beads) for depth, phase counts,
    and per-month rates.
  - `sase bead show sase-j0`.
- **Plans** (read through `sase artifact read`):
  - `plan:202609/axe_routines_jobs.md`
  - `plan:202609/axe_routine_job_landing_repairs.md`
  - `plan:202609/routine_job_final_contract_repairs.md`
  - `plan:202609/routine_job_identity_diagnostic_completion.md`
  - `plan:202609/routine_job_identity_diagnostic_residuals.md`
  - Plans-repo commit timestamps.
- **Prior report:** `research:202609/sase_11e_nested_landing_loop.md`.
- **Source:**
  - `src/sase/default_config.yml` (`bd/land_epic`, bundled `ace.tribes`)
  - `src/sase/bead/work.py` (`%auto` on phase and land segments)
  - `src/sase/main/plan_propose_handler.py`
  - `src/sase/doctor/checks_axe.py` (`_public_axe_text`)
  - `src/sase/axe/run_agent_directive_metadata.py`
  - `src/sase/axe/run_agent_wait_deps.py`
  - `src/sase/ace/tui/models/tribe_display.py`
  - `src/sase/notifications/senders.py`
  - `src/sase/doctor/checks_external_mirror.py`
  - `src/sase/axe/chop_doctor.py`
  - `git show 9759e5afe8`
  - `git log` for the epic's commits and churn
- **Athena, read-only over SSH:**
  - `sase agent list`
  - Tribe values in `~/.sase/agent_tribes.json` and in all `agent_meta.json` files
  - `~/.config/sase/sase.yml` tribes
- **CLI help:** `sase agent hold` and `sase agent hold create`.
- **Memory:** `sase_beads.md`, `tailnet.md`, `glossary:Agent Family`.
- **Not checked:**
  - The land agents' chat transcripts.
  - The `sase-core` sources for gap 7. I relied on the plan's citations and didn't open
    that repo.
  - A visual check of the color regression.
  - The hold, cancel, and manual-relaunch sequence in §4.
