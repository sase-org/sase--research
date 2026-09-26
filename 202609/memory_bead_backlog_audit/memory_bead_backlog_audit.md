# Open Memory Bead Audit: Consolidated Research

- **Type:** consolidated research report (lead). It merges four independent reports with
  the lead's own verification.
- **Date:** 2026-09-26
- **Tree:** sase `master` at `eba6b80d0`. The researchers audited `266c8b37bc`, one
  memory-init commit earlier. Every memory text quoted below was re-read at `eba6b80d0`.
- **Question:** Which open memory beads contain valid memory-update recommendations, and
  which memory file changes should Bryan make?
- **Inputs:**
  [`__cld`](memory_bead_backlog_audit__cld.md),
  [`__grk`](memory_bead_backlog_audit__grk.md),
  [`__mus`](memory_bead_backlog_audit__mus.md),
  [`__gem`](memory_bead_backlog_audit__gem.md), plus lead checks of source, memory, bead
  state, and plan `plan:202609/tool_e2_durable_handoff.md`.

## TL;DR

The scope is all 15 non-closed `task_type=memory` beads (12 `ready`, 3 `open`). No new
memory bead appeared after the researchers ran.

| Verdict                                               | Beads                                                   |
| ----------------------------------------------------- | ------------------------------------------------------- |
| Valid: apply now as proposed                          | `sase-st`, `sase-yd`, `sase-12x`, `sase-16r`, `sase-18h` |
| Valid, but the bead's own text needs correcting first | `sase-195` (wrong advice), `sase-148` (stale counts), `sase-sa` (stale path, imprecise wording) |
| Valid, lower priority                                 | `sase-18a` (decision-record hygiene)                    |
| Valid, but blocked on an in-flight epic               | `sase-134` (on `sase-11l.11`), `sase-ya` (on `sase-xe.16`; also needs rescoping) |
| Already fixed: close with no edit                     | `sase-sl` (fixed by `1c246dc74`, 2026-09-18)            |
| Not memory work                                       | `sase-xs`, `sase-xt`, `sase-xu` (abandoned message-board experiment) |

Net result: **7 existing files and 2 new decision strands can change now, closing 9
beads.** Two beads should wait on their epics, and four need no memory edit.

Three beads would put new errors into memory if their stored `proposed_change` were
applied word for word:

- `sase-195` would steer agents away from the correct `OptionList` pattern that eight
  widgets use.
- `sase-148` would freeze case counts that have already drifted.
- `sase-sa` points at a glossary location that no longer exists.

The recommended text in the final section fixes all three.

## Where The Reports Disagreed, And The Resolution

All four reports agreed on the census, on closing `sase-sl`, on `sase-134` being blocked,
and on the three message boards not being memory work. They split on the points below.
The lead checked each one directly.

### 1. `sase-195`: is the bead's replacement for rule 12 correct? **No.** (cld is right.)

grk, mus, and gem adopted the bead's text: "a guard flag cleared in `finally:` does not
work for OptionList", so use pending-echo counts instead. Only cld checked the other
`OptionList` widgets, and the source supports cld:

- Eight widgets override `watch_highlighted`:
  - `agent_list.py`, `bgcmd_list.py`, `patch_list.py`
  - `artifacts/beads_option_list.py`, `agents_navigation.py`, `commits_timeline.py`,
    `files_navigation.py`, `plans_navigation.py`
- While the guard flag is set, each override returns without calling `super()`. Textual
  8.0.1's `OptionList.watch_highlighted` is what posts `OptionHighlighted`, and the
  watcher runs synchronously inside the assignment. So no echo is ever queued, and
  clearing the flag in `finally:` is correct.
- The docstring on `AgentList.watch_highlighted` (`agent_list.py:476-500`) describes
  exactly the race in the bead, and this override is its documented fix.
- The real anti-pattern is narrower: checking the flag only in the `OptionHighlighted`
  **handler**. `CommandLinePopup` needs the message to be posted, so it counts echoes
  instead (`popup.py:312`, `353-379`). Its comment even cites "Rule 12".
- One caveat is worth recording: the override also skips Textual's
  `scroll_to_highlight()`. That is why `AgentList._set_highlighted_programmatically`
  calls it explicitly (`agent_list.py:455-462`).

Rule 12 is still defective, because it never says *where* to check the flag. But the
fix must keep both working patterns. Use the text in change A4 below.

### 2. `sase-ya`: write `dispatch.md` now, or defer? **Defer.** (cld and gem are right.)

grk wanted a compact note now, and mus gave no firm position. The bead store shows the
subsystem is still moving:

- `sase-xe` was reopened and is `OPEN`.
- `sase-xe.16` is `IN_PROGRESS`. Its phase `.16.10`, "Runbook plus live Athena-to-Apollo
  end-to-end proof", is still `OPEN`, and child epic `.16.11` is in progress.
- `sase-133` (Agents-tab parity) is `IN_PROGRESS`. Its 2026-09-19 landing audit found
  that production gateway presentation "still does not reproduce owner rows". The bead's
  "Focus/Fleet running-count semantics" topic is exactly that surface.
- The bead also predates `docs/remote_dispatch.md`, a 301-line runbook added
  2026-09-08. It uses the retired "family" vocabulary; `sase-17m` is renaming that to
  *session*.

**Resolution:** make `sase-ya` depend on `sase-xe.16`. Then rescope it to a short
pointer note (change C2).

### 3. `sase-148`: how do the `tools/` provider copies get updated?

The reports gave three different answers:

- grk and gem: hand-edit all five files.
- mus: the copies are hardlinks.
- cld: `sase memory init` regenerates them.

The lead verified cld's answer:

- The five files have different inodes (561879–561883) and identical MD5s, so they are
  byte copies, not hardlinks.
- `sase memory init` calls `agent_doc_shim_plans(root, include_root=False)`
  (`src/sase/main/init_memory/root_planning.py:531`). That walks every project
  `AGENTS.md` discovered in subdirectories and rewrites its `CLAUDE.md`, `GEMINI.md`,
  `QWEN.md`, and `OPENCODE.md` as copies.

**So edit `tools/AGENTS.md` only, then run `sase memory init`.**

The case count needs the same care. gem's text ("three live cases… all 35 cases") copies
the bead's stale `proposed_change`. Eight cases are live-gated today:

- In `_smoke_tool_runs_cases_owners.py`: `dod-8-live-monitor`, `dod-8-live-proc`, and
  `dod-13-overhead`.
- In `_smoke_tool_runs_cases_handoff.py`: the four `dod-14-live-handoff-*` cases and
  `dod-14-live-monitor-handoff`.

The recommended text names the groups rather than counts or IDs, which is also how the
harness docstring describes them (`tools/smoke_sase_tool_runs:10-11`).

### 4. `sase-sa`: which file, and what wording?

- **File.** mus says to edit `sase/sase.yml`. That is wrong: the glossary moved to a
  memory web in `df956212b` (2026-08-24), and `sase/sase.yml` no longer has glossary
  terms. The target is `sase/memory/glossary/proc-shell.md`.
- **Wording.** The current parenthetical, "A session-attached proc shell
  (`shell_kind: "proc"`) is a sase monitor", suggests that `shell_kind: "proc"` implies
  a monitor. grk's proposed text keeps that implication.
  - In fact, stand-alone `%proc` units carry `shell_kind: "proc"` too. That is the
    `ProcSubmitRequest` default (`src/sase/procs/request.py:40`), and
    `launch_proc_runtime.py:267-281` does not override it. Their distinguishing marks
    are origin `xprompt-proc` and having no session.
  - `%proc` is a beta directive behind `typed_launch_units`, so the definition should
    say so.
  - cld's wording handles both points.

### 5. The message boards (`sase-xs`, `sase-xt`, `sase-xu`): close or keep?

- grk and mus said leave them alone; mus said until their supervision chains terminate.
- cld and gem said close them.
- The last notes are from 2026-09-06 and 2026-09-07 (the final one from
  `016.fork_repair` at 02:43 EDT on 2026-09-07). That is 18–19 days of silence, and no
  terminal "final analysis" note was ever written. The chains are dead, not still
  running.
- They carry `open` status, not `ready`, so they don't trigger `TaskTriage`. But they sit
  in every `-T memory` listing and inflate the memory backlog.

**Recommendation:** close them as `canceled`. This was your experiment, so the decision
is yours.

### 6. How to author decision strands (`sase-yd`, `sase-18a`)

gem's drafts would not match the web's conventions:

- gem invented frontmatter keys: `type: decision`, `status: accepted`, `deciders`, and
  `links:`. Per `docs/memory.md` › *Strand supersession*, a strand keeps supersession
  inside a free-form `metadata:` mapping (`status`, `superseded_by`). Links are authored
  inline as `[[...]]`.
- gem also proposed hand-writing a "> **Partly superseded** by …" header. `sase memory
  read` already prints that as a status line; nobody authors it.
- gem's `-H` "Reopens when" condition (a "zero-latency in-memory reservation…without
  SQLite") has no source.
- The real rationale is decision 3 of `plan:202609/tool_e2_durable_handoff.md`. That
  plan also says outright that it left the strand as a follow-up. Its text is used in
  change B1.

### 7. Smaller splits

- **`sase-16r`: full contract in both notes, or once?** grk wanted the full `partial`
  contract repeated in `tui_screenshot.md`. The recommendation here puts it once in
  `lint_and_test.md` › *PNG Snapshot Tests* and adds a one-sentence pointer in
  `tui_screenshot.md`. Duplicated memory costs tokens and drifts apart.
- **`sase-sl`: mention the `SASE_VISUAL_PNG_*` escape hatches?** cld offered it as
  optional; grk said no. Skip it. `docs/development.md` covers it, and memory's job here
  is to say CI is exact.
- **`sase-134`: are the proposed scope details correct?** Only cld checked them. See
  C1 for the corrections, including that `ttl=` is optional (default `2h`, cap `12h` in
  `default_config.yml:85-86`).

## Per-Bead Findings

Each finding below was confirmed by at least two researchers, and every quoted memory
line was re-read by the lead through audited `sase memory read`.

| Bead       | Target (actual)                                   | Evidence that memory is stale today                                                                                                                                                                                                                                                                                                                                                              | Verdict              |
| ---------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------- |
| `sase-sl`  | `lint_and_test.md` (bead says `build_and_run.md`) | Already says "Comparison is exact pixel equality locally and in CI; do not treat CI as a tolerance lane" (`1c246dc74`, 2026-09-18). The bead's +1 came from `f7ea41d3b2`, earlier that day.                                                                                                                                                                                                       | Close, no edit       |
| `sase-st`  | `xprompts.md` › Invoke                            | Says only "`[[ ... ]]` multi-line text". `docs/xprompt.md` › Text Blocks (~741–761) has the close rule and structural shorthand binding. `sase-sn` is closed.                                                                                                                                                                                                                                  | Apply                |
| `sase-yd`  | new `decisions/machine-link-writes-off-primary.md` | No strand exists. The code is in the tree: `resolve_machine_artifact_link_store`, `hidden_sidecar_clone_dir`, `AccessKind.HOST_OWNED_SIDECAR`, `sync_primary_sidecar_role`, and the `primary_sidecar_link_dirt` doctor repair. `sase-y3` is closed.                                                                                                                                          | Apply                |
| `sase-12x` | `tui_screenshot.md` › Troubleshooting             | Still says "Missing visual extra: install the project visual dependencies". But `resvg_py==0.3.3` is a base dependency, and `visual_render.py:38-45` tells the user to run `sase update`.                                                                                                                                                                                                      | Apply                |
| `sase-16r` | `lint_and_test.md` + `tui_screenshot.md`          | Neither note mentions exit-0 `partial`, the WARNING block and manifest `skipped` list, `-n` becoming `SASE_PYTEST_WORKERS`, the bounded lock wait, or strict `--check`. The commits are on master, and `_visual_maintenance_cli.py:58-82` plus the Justfile document all of it. Highest-impact gap: an agent can read `partial` as "goldens current". | Apply (both notes)   |
| `sase-18h` | `lint_and_test.md`                                | Says `just check` runs "every whole-repo lint gate" and `check-full` runs "every lint gate". The Justfile (`:713-716`, `:748`) excludes `toobig` from both.                                                                                                                                                                                                                                  | Apply                |
| `sase-195` | `tui_perf.md` rule 12                             | Never says where to check the flag. The bead's replacement is too broad (see disagreement 1).                                                                                                                                                                                                                                                                                                | Apply A4, not bead text |
| `sase-148` | `tools/AGENTS.md` (instruction file, not `sase/memory/`) | Lines 65–66 still say "phase-pending". The harness emits `not-run` (`_smoke_tool_runs_lib.py:29`). The bead's counts are stale (see disagreement 3). It has two +1s.                                                                                                                                                                                                                    | Apply A6, not bead text |
| `sase-sa`  | `glossary/proc-shell.md` (bead says `sase/sase.yml`) | Still says "a named supervised proc belonging to a sase agent". Stand-alone `%proc` shells belong to no agent (see disagreement 4).                                                                                                                                                                                                                                                         | Apply A5             |
| `sase-18a` | new strand + `decisions/record-before-admit.md`   | The record still says "recording stays fail-open even where admission later becomes fail-closed". But `docs/tool.md:205-209` and `src/sase/tool/handoff.py` make explicit `-H` fail-closed. The record already carries one partial-supersede mark, from `guarded-recipes`.                                                                                                                    | Apply B1 (lower priority) |
| `sase-134` | `xprompts.md` directive table + `%queue` paragraph | There is no `%hold` row, even though `%hold` has been unconditional since `932e6ffae` (2026-09-18). `sase-11l.11` is still `IN_PROGRESS`: all five children are closed, but landing has been blocked on the check-full gate since 2026-09-19. The bead itself says to wait.                                                                                                                | Defer (C1)           |
| `sase-ya`  | new `dispatch.md`                                 | The gap is real, but the subsystem is in flux (see disagreement 2).                                                                                                                                                                                                                                                                                                                         | Defer + rescope (C2) |
| `sase-xs`/`xt`/`xu` | none (`N/A: operational message board`)  | Their proposed changes say "no memory-file edit is requested". They have been idle since 2026-09-07.                                                                                                                                                                                                                                                                                       | Not memory work      |

Two more items share `xprompts.md` › `%queue` and should be sequenced with it, but
neither is part of this batch:

- Epic `sase-19f` (`%q:<M>x` capacity multiplier; plumbing commit `6beedbc11`) is
  `IN_PROGRESS`. When it lands, the note's positive-integer capacity wording becomes
  stale. That is `sase-19f`'s land agent's job, not `sase-134`'s.
- The agent-session rename (`sase-17m`, in progress) means `sase-134` and `sase-ya` both
  need "family" rewritten as "session" before anyone applies them.

## Bead Housekeeping (No Memory Edits)

The memory task type requires your explicit permission before any bead closes. Record
path and scope corrections as notes, because `sase bead update` has no task-field flag.

| Bead                            | Action                                                                                                                                                                                  |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sase-sl`                       | `sase bead close sase-sl -R done -r "exact-pixel CI sentence landed in lint_and_test.md by 1c246dc74 (sase-12z.4)"`                                                                      |
| `sase-xs`, `sase-xt`, `sase-xu` | If you agree: `sase bead close sase-xs sase-xt sase-xu -R canceled -r "message-board experiment abandoned 2026-09-07; not a memory update"`. Optionally file a `feature` bead through `/sase_new_task` for a dedicated board type. That is the one lesson the boards recorded. |
| `sase-134`                      | `sase bead dep add sase-134 sase-11l.11`, and add a note with the C1 corrections                                                                                                        |
| `sase-ya`                       | `sase bead dep add sase-ya sase-xe.16`, and add a note with the C2 rescope                                                                                                              |
| `sase-sa`, `sase-195`, `sase-148`, `sase-16r` | Add a note: "use the consolidated text in `research:202609/memory_bead_backlog_audit/memory_bead_backlog_audit.md`" (actual path; scope includes `tui_screenshot.md` for `sase-16r`) |

## Recommended Memory File Changes

Each bead you hand to a worker is its own write authorization, because the bead
describes the change. Point each worker at the text below rather than at the bead's
stored `proposed_change`. After the edits, run `sase memory init`, confirm `sase memory
init --check` is clean, and close each bead with a `--note` describing what changed.

The edits are grouped so each file is touched once.

### A. Apply now

**A1. `sase/memory/lint_and_test.md`** closes `sase-18h` and the main half of
`sase-16r`.

1. Recipe code block comments:
   - `just check`: "Agent default: whole-repo lint gates **except `toobig`** + a
     diff-scoped test lane…"
   - `just check-full`: "every lint gate **except `toobig`** + the full test suite…"
   - Leave `just lint`'s "(… symvision, toobig, …)" alone; it is correct.
2. *Two-Speed Verification*. Change the first sentence to "`just check` runs every
   whole-repo lint gate **except `toobig`** plus a diff-scoped test lane…", then add:
   > Neither `just check` nor `just check-full` runs the `toobig` line-count gate: CI
   > enforces it through `just lint`, `just toobig` runs it on demand, and the
   > `toobig_split` routine owns the resulting splits.
3. *PNG Snapshot Tests*. Keep the exact-pixel sentence, and add after "…never writes
   goldens.":
   > Update mode (`just fix-tui-screenshots`, `just update-visual-snapshots`, and the
   > update stage of local `just check-full`) applies every golden it can prove and
   > exits 0 with status `clean`, `applied`, or `partial`. `partial` means some nodes or
   > goldens were skipped (failing tests, unstable captures, concurrent edits, or stale
   > removal skipped on incomplete evidence). Those goldens are unchanged and **not
   > known to be current**. After a `partial` run, read the WARNING block or the
   > manifest's `skipped` list and `pruning_skipped_reason`; never read `counts:` alone
   > as "nothing to update". `-n N` after `--` becomes the governed
   > `SASE_PYTEST_WORKERS` request (`-n` in `PYTEST_ADDOPTS` is a usage error). A second
   > run in the same checkout waits for the maintenance lock (bounded, default 2 h).
   > `--check` stays strict: it never writes and exits 1 on required drift.

**A2. `sase/memory/tui_screenshot.md`** closes `sase-12x` and the pointer half of
`sase-16r`.

1. *Troubleshooting*: replace the "Missing visual extra" bullet with:
   > Renderer import error (`resvg_py`): `resvg_py` is a base runtime dependency, so a
   > missing import means the SASE install is incomplete or stale. Run `sase update` or
   > reinstall the environment that owns the `sase` entry point. Do not fall back to a
   > second renderer.
2. *Golden Maintenance*: add:
   > The update form can exit 0 with status `partial` and leave some goldens untouched;
   > read its WARNING block before treating goldens as current (contract in
   > [[lint_and_test.md]] › PNG Snapshot Tests).
3. Optional: in *Implementation Rules*, change "the bundled Fira Code fonts" to "the
   bundled Fira Code / DejaVu / Noto Emoji font stack". This matches `lint_and_test.md`.

**A3. `sase/memory/xprompts.md` › Invoke** closes `sase-st`.

- End the Args bullet with:
  > …quoted comma/special values, `[[ ... ]]` multi-line text. A `[[` block closes at
  > the first `]]` followed (after optional whitespace) by `,`, `)`, `}`, `|`, or the
  > end of the args; any other `]]` is content. Quote the value when a literal `]]`
  > must precede one of those terminators.
- Append to the Shorthands bullet:
  > Line shorthands (`#name: text`, `#name:: text`, `#name(args): text`) bind their
  > payload structurally and are never re-lexed as `[[...]]`, so commas, `]]`, `+`, and
  > unbalanced parens in prose stay literal. `+` means a space only in the bare unquoted
  > `#name:a,b` colon form.

**A4. `sase/memory/tui_perf.md` rule 12** closes `sase-195`. Use this text, not the
bead's.

> 12. **Guard programmatic widget updates.** A programmatic `OptionList.highlighted = X`
>     makes Textual's `watch_highlighted` post an `OptionHighlighted` message, which is
>     *queued*. Silence the echo at its source: set a guard flag around the assignment
>     and override `watch_highlighted` to return without calling `super()` while the
>     flag is set (`AgentList`, `BgCmdList`, `PatchList`, `BeadsOptionList`). The
>     watcher runs synchronously, so clearing the flag in `finally:` is correct there.
>     The override also skips Textual's `scroll_to_highlight()`, so scroll explicitly
>     (`AgentList._set_highlighted_programmatically`). A flag checked only in the
>     `OptionHighlighted` *handler* never matches, because it is already cleared when
>     the queued echo arrives. When the message must still be posted, count pending
>     echoes per row and drop echoes whose `Option` is no longer in the list
>     (`CommandLinePopup._pending_echoes` / `user_highlight_index`). `clear_options()`
>     posts no echo.

**A5. `sase/memory/glossary/proc-shell.md`** closes `sase-sa`. Do not edit
`sase/sase.yml`.

> A proc shell is a named supervised proc (`shell_kind: "proc"`) with durable output and
> lifecycle state. It is either **session-attached**, meaning a sase monitor that belongs
> to the agent session that started it and may carry timeout, workspace-claim, and
> follow-up policy, or **stand-alone**, meaning a beta `%proc` launch unit dispatched with
> origin `xprompt-proc`. A stand-alone proc shell belongs to no agent or session,
> allocates no agent runner, and appears in the Agents tab as its own row kind, counted
> separately from agents. A gate shell's execution-phase proc does not make it a proc
> shell: it stays `shell_kind: "gate"` throughout, pending or executing.

**A6. `tools/AGENTS.md` › ToolRun smokes** closes `sase-148`. Edit this file only;
`sase memory init` regenerates the four provider copies. Replace the paragraph's last
sentence and extend its contract list:

> …it talks to the real store and CLI for catalog, foreground run, signals, lost-run
> recovery, fail-open recording, hand-off, and query contracts. Cases that need the real
> monitor/proc supervisors or a cold-start timing measurement are labeled `not-run`
> unless `--live` is passed; `--live` runs them too.

Do not add case counts or IDs; they have drifted twice already.

**A7. New strand `sase/memory/decisions/machine-link-writes-off-primary.md`** closes
`sase-yd`.

- Use the bead's `proposed_change` as the body: the claim, the three rejected
  alternatives, the cost, the reopen condition, the implementing code, and the plan link
  `plan:202609/machine_link_mutations_off_primary.md`.
- Add `[[sase_artifacts.md]]` as a link, since link-maintenance agents read that note.
- Create the strand through the Memory panel (`gm`). The panel validates frontmatter and
  updates the descriptor roster. Alternatively, copy an existing decisions strand's
  frontmatter. Do not use gem's invented `type:`/`deciders:`/`links:` keys.

### B. Apply when convenient (lower priority)

**B1. New strand `sase/memory/decisions/explicit-handoff-fails-closed.md`, plus a
second partial-supersede mark on `decisions/record-before-admit.md`.** This closes
`sase-18a`.

Why it is lower priority: `-H` refuses to run inside an agent (exit 2), so agents never
*run* it. The record exists to stop a future `sase tool` implementer from "fixing" `-H`
back to fail-open.

New strand. Its claim and why come from decision 3 of
`plan:202609/tool_e2_durable_handoff.md`:

- **Claim.** Explicit `sase tool run -H` is fail-closed: if the ToolRun reservation
  cannot be committed, nothing starts, and the command exits 1 naming the foreground
  form. Foreground `sase tool run` stays fail-open. A monitor start's reservation stays
  fail-open, falling back to E1.5 wrapping with one reason line. Once a hand-off is
  accepted, later recording failures (observe, sample, finish) stay fail-open and are
  reported as incomplete evidence, never replayed.
- **Why.** The printed run id is the only handle a `-H` caller gets, so it must be
  durable. A monitor's id is already durable, and a foreground run streams to its
  caller.
- **Cost.** When the ledger cannot be written, `-H` callers must retry or use the
  foreground form.
- **Reopens when.** `-H` gains a durable handle that does not depend on the ToolRun
  reservation. The plan states no reopen condition, so this one is the lead's
  suggestion; confirm it before writing.
- Link `[[decisions/record-before-admit]]` and `[[decisions/guarded-recipes]]`.

On `record-before-admit.md`:

- Make `metadata.superseded_by` a list containing both `decisions/guarded-recipes` and
  the new slug. Leave `metadata.status: superseded-in-part` as it is.
- Add a second paragraph, beside the existing mark:
  > _Superseded in part:_ "recording stays fail-open" no longer holds for explicit
  > `sase tool run -H`, which fails closed when its reservation cannot commit. See
  > [[decisions/explicit-handoff-fails-closed]]. Foreground and monitor-start recording
  > remain fail-open.
- Do not reword the accepted body. Do not hand-write a "Partly superseded by" header;
  `sase memory read` renders that.

### C. Deferred: apply after the blocking epic closes, and re-verify first

**C1. `sase/memory/xprompts.md` directive table and `%queue` paragraph** (`sase-134`,
after `sase-11l.11` closes).

- Add a `%hold` row: a pre-admission barrier on *other* work. Matching agents stay
  `QUEUED`, and undispatched `%proc` units stay pending. Running work is never touched.
- Add a short paragraph covering:
  - selectors: name, `@tribe`/`tribe=`, `hood=`, `pending`, `future`
  - `scope=project|host`
  - `ttl=` is optional; it defaults to `agent_hold_default_ttl` (2 h) and is capped by
    `agent_hold_max_ttl` (12 h). So every hold is bounded, but the TTL is not
    "mandatory" as the bead says.
  - a hold ends on release, when its armer's **session** or shell ends, or at TTL
  - a broken store fails open
  - bare `%hold` is an error, and there is no alias (`%h` stays `%hide`)
  - `%hold` does not combine with `%repeat` or `%dispatch`
  - the imperative form is `sase agent hold create|run|list|show|release`
- Add a beta `%proc` row (behind `typed_launch_units`) with one sentence: `%queue` on a
  `%proc` gates dispatch on a capacity check (an omitted weight counts as `0`), but a
  dispatched proc holds no runner capacity.
- Mirror the then-current `docs/xprompt.md` › *Hold Directive*, not the bead's
  description.
- Sequence this edit with `sase-19f`'s `%q:<M>x` update, which touches the same
  paragraph.
- Write the optional decisions strand (pull model, fail-open store, session-scoped
  release) only if `plan:202609/hold_landing_repairs.md` or the `sase-11l` plan records
  the rejected alternatives.

**C2. New `sase/memory/dispatch.md`** (`type: reference`; `sase-ya`, after
`sase-xe.16` closes).

Write a short pointer note to `docs/remote_dispatch.md` that records only the rules an
agent would otherwise get wrong:

- exactly one `%dispatch:<alias>` selector, and `local` is reserved
- v1 remote launch does not combine with `%wait`, `%queue`, `%clan`, or an active
  `%hold`
- remote launch requires a clean source with `HEAD` published
- a quarantined enrollment is recovered with `sase machine repair`; do not assume a
  local uncommitted tree exists on the target
- the Launch Target picker and the Machines tab do no network probe

In the same edit, add a one-line `%dispatch` row to the `xprompts.md` directive table
that links `[[dispatch.md]]`. Before writing, re-verify every Focus/Fleet count claim
against the landed `sase-133`, and use session vocabulary.

### Summary

| Group                  | Files                                                                                                                                  | Beads closed                                            |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| A (now)                | `lint_and_test.md`, `tui_screenshot.md`, `xprompts.md`, `tui_perf.md`, `glossary/proc-shell.md`, `tools/AGENTS.md`, new `decisions/machine-link-writes-off-primary.md` | `sase-18h`, `sase-16r`, `sase-12x`, `sase-st`, `sase-195`, `sase-sa`, `sase-148`, `sase-yd` |
| B (when convenient)    | new `decisions/explicit-handoff-fails-closed.md`, `decisions/record-before-admit.md`                                                    | `sase-18a`                                              |
| C (after epics)        | `xprompts.md`, new `dispatch.md`                                                                                                       | `sase-134`, `sase-ya`                                   |
| No edit                | none                                                                                                                                   | `sase-sl`; `sase-xs`/`xt`/`xu` if you agree            |

Do not do any of the following:

- recreate `build_and_run.md`
- edit `sase/sase.yml` for glossary terms
- promote any new note or strand to `type: core`
- hand-edit `AGENTS.md` or the `tools/` provider copies
- copy `docs/xprompt.md` or `docs/remote_dispatch.md` wholesale into memory
