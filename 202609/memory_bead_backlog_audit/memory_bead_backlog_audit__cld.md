# Audit of Open Memory Task Beads

- **Researcher:** cld (4-researcher swarm)
- **Date:** 2026-09-26
- **Tree audited:** sase `master` at `266c8b37bc`
- **Scope:** every non-closed `task(memory)` bead (`sase bead list -T memory -n 0`),
  15 in total: 12 `ready` and 3 `open`. No bead was `claimed`, `snoozed`, or
  `in_progress`.

## TL;DR

| Verdict                                           | Beads                                                          |
| ------------------------------------------------- | -------------------------------------------------------------- |
| Valid: apply now as proposed (small edits)        | `sase-18h`, `sase-12x`, `sase-16r`, `sase-st`, `sase-yd`       |
| Valid, but the proposed text needs correcting     | `sase-195` (wrong advice), `sase-148` (stale case list/count), `sase-sa` (stale path) |
| Valid, lower priority (decision-record hygiene)   | `sase-18a`                                                     |
| Valid, but blocked on an in-flight epic           | `sase-134` (on `sase-11l`), `sase-ya` (on `sase-xe.16`, and needs rescoping) |
| Already fixed on master: close, no edit needed    | `sase-sl` (fixed by `1c246dc748`, 2026-09-18)                  |
| Not memory work: close                            | `sase-xs`, `sase-xt`, `sase-xu` (message-board experiment, abandoned 2026-09-07) |

Eleven beads warrant memory edits: nine now (one of them lower priority) and two after
their blocking epics close. One bead is already satisfied. Three are not memory
recommendations at all. Two of the "valid" beads
(`sase-195`, `sase-148`) would add new errors to memory if their `proposed_change`
fields were applied word for word. The consolidated change list is at the end.

## Method

1. I listed the beads with `sase bead list -T memory -n 0 -f json` and read each one's
   description, fields, notes, and +1 evidence. I checked the status of each
   proposing epic with `sase bead read`.
2. I read every target memory note through audited `sase memory read`: `lint_and_test.md`,
   `tui_screenshot.md`, `tui_perf.md`, `xprompts.md`, `sase_beads.md`,
   `sase_artifacts.md`, `glossary:proc-shell`, `glossary:sase-monitor`, `glossary:proc`,
   `decisions:record-before-admit`, `decisions:guarded-recipes`, and `task_types:memory`.
3. I checked each claim against current source, docs, the Justfile, and git history.
   A bead counts as **valid** only when the memory text is wrong or missing something
   *today* and the code or docs confirm the proposed replacement.

## Per-Bead Findings

### 1. `sase-sl`: PNG tolerance guidance. **Already fixed; close.**

- **Claim:** memory says CI allows a "small ratio-only renderer drift tolerance" for PNG
  snapshots.
- **Today:** `lint_and_test.md` › *PNG Snapshot Tests* now says: "Comparison is exact
  pixel equality locally and in CI; do not treat CI as a tolerance lane."
  `git log -G "ratio-only"` shows the stale sentence was replaced by `1c246dc748`
  (`sase-12z.4`, 2026-09-18 18:02 EDT). That commit descends from `f7ea41d3b2`, the tree
  where the +1 reporter reproduced the problem earlier the same day, so the +1 is simply
  older than the fix.
- **Residual nuance (optional):** the Justfile says the `SASE_VISUAL_PNG_*` env vars
  "remain available as explicit escape hatches for renderer investigations and local
  iteration on non-canonical platforms." Memory does not mention them. Adding that half
  clause is optional; it doesn't need its own bead.
- **Action:** `sase bead close sase-sl -R superseded --reason "fixed by 1c246dc748 (sase-12z.4)"`.
  The bead's `path` field still says `build_and_run.md`, which no longer exists.

### 2. `sase-st`: `[[ ... ]]` closing rule and structural shorthand binding. **Valid; apply.**

- `xprompts.md` › *Invoke* still says only "`[[ ... ]]` multi-line text", with no closing
  rule.
- Epic `sase-sn` is CLOSED. `docs/xprompt.md` › *Text Blocks* (lines 741–761) confirms:
  - A block closes at the first `]]` whose next non-whitespace character is `,`, `)`,
    `}`, `|`, or the end of the region.
  - Shorthand payloads (`#name: text`, `#name:: text`, `#name(args): text`) are bound
    structurally and not re-lexed.
  - `+` decodes to a space only in the bare unquoted colon form
    (`decode_xprompt_arg_value` docstring, `src/sase/xprompt/_parsing_args.py:25-37`).
- The bead's proposed wording is accurate but long for a reference note. Compact text is
  in the change list below.

### 3. `sase-xs`, `sase-xt`, `sase-xu`: "Message board" beads. **Not memory work; close.**

- All three have `path: "N/A: operational message board; no memory file"`, and their
  proposed changes say outright that "no memory-file edit is requested." They were a
  user-authorized experiment in using a memory task bead as an append-only supervision
  log.
- All three went quiet on 2026-09-07 (last notes 00:43Z, 00:54Z, and 06:43Z), 19 days
  ago. None has a live monitor successor or a terminal "final analysis" note. The
  supervision chains died without the termination the descriptions require.
- They stay in every `-T memory` listing and triage sweep, which pollutes the memory
  backlog.
- The boards recorded one lesson worth keeping outside memory: "the memory task schema
  forces path/proposed_change fields despite no memory edit, and ordinary ready status
  would launch irrelevant memory triage." That is evidence for a dedicated board type
  (a feature idea, not a memory change).
- **Action:** close all three as `canceled`. Use a reason such as "message-board
  experiment abandoned 2026-09-07; not a memory update." If you still want a
  message-board type, file a `feature` bead through `/sase_new_task`.

### 4. `sase-ya`: New `dispatch.md` reference note. **Valid need, premature, needs rescoping.**

- Epic `sase-xe` was closed on 2026-09-08 and reopened on 2026-09-09. Its child epic
  `sase-xe.16` ("Complete remote dispatch…") is IN_PROGRESS: phase `.16.10` "Runbook
  plus live Athena-to-Apollo end-to-end proof" is OPEN, and a grandchild epic `.16.11` is
  in progress.
- Since the bead was filed, `docs/remote_dispatch.md` (a 301-line runbook, added
  `890660e257` on 2026-09-08) has come to cover install, gateway, Tailscale Serve,
  bootstrap, enrollment, and launch/operate. So the claim that "anyone … must re-derive
  it from source" is no longer true.
- Part of the proposed scope looks stale. The runbook now says "the Agents tab shows
  local and remote rows in one list", with group-by-machine, and `docs/remote_dispatch.md`
  never mentions "Focus". The bead's "Focus/Fleet running-count semantics" topic should
  be re-verified before anyone writes it. The description also uses the retired
  "family" vocabulary; agent family was renamed to agent session in `sase-17m`.
- **Action:** keep it, but add a dependency on `sase-xe.16` (or snooze it until that epic
  closes). Then rescope it to a **short** reference note that points to
  `docs/remote_dispatch.md` and records only the non-obvious agent rules:
  - exactly one `%dispatch` selector; `%dispatch:local` is reserved;
  - V1 does not combine with `%wait`, `%queue`, or `%clan`;
  - the clean, published-`HEAD` source requirement;
  - `sase machine repair` for quarantined enrollments;
  - the Launch Target picker and Machines tab do no network probe.

### 5. `sase-yd`: Decisions strand for the machine artifact-link write lane. **Valid; apply.**

- Epic `sase-y3` is CLOSED, and its related publication bead `sase-ye` is CLOSED. Every
  code anchor in the proposed record exists:
  - `resolve_machine_artifact_link_store` in `src/sase/sdd/_artifact_link_machine_store.py`
  - `hidden_sidecar_clone_dir`
  - `AccessKind.HOST_OWNED_SIDECAR` and `_hidden_sidecar_machine_context` in
    `src/sase/workspace_provider/_ownership_authorize.py`
  - `sync_primary_sidecar_role` in `src/sase/_sidecar_auto_sync.py`
  - the `primary_sidecar_link_dirt` doctor repair
- `sase_artifacts.md` does not mention the hidden-clone write lane, so the invariant is
  recorded nowhere in memory.
- It fits the decisions web: it has a claim, three rejected alternatives, a cost, and a
  reopen condition. It is also exactly the kind of rule a later agent could "simplify"
  away by committing from the primary checkout.
- The bead's `proposed_change` is already a ready-to-paste record.

### 6. `sase-12x`: `tui_screenshot.md` resvg runtime dependency. **Valid; apply.**

- `tui_screenshot.md` › *Troubleshooting* still says "Missing visual extra: install the
  project visual dependencies."
- `pyproject.toml:45` now lists `resvg_py==0.3.3` under the base `dependencies`. The
  renderer's ImportError says: "The SASE installation is incomplete or stale. Run
  `sase update`, or reinstall the Python environment that owns the `sase` entry point"
  (`src/sase/ace/tui/visual_render.py:38-45`).
- **Incidental:** *Implementation Rules* says rasterization uses "the bundled Fira Code
  fonts". `lint_and_test.md` names the "Fira Code / DejaVu / Noto Emoji renderer stack"
  (Fira Code first, with bundled fallback). Aligning the two wording choices in the
  same edit is cheap.

### 7. `sase-134`: `%hold` row and `%queue` on stand-alone procs. **Valid; wait for `sase-11l` to close.**

- `xprompts.md`'s directive table has no `%hold` row, and nothing about `%queue` on
  `%proc` units. The feature has shipped: `%hold` became unconditional in `932e6ffae2`
  ("make %hold unconditional and retire agent_holds"), and `docs/xprompt.md` ›
  *Hold Directive* documents it fully.
- Epic `sase-11l` is still IN_PROGRESS (land continuation checkpoint `48d0a69287`).
  The bead itself says to wait for it, which is reasonable because landing repairs may
  still change details.
- **Corrections to the proposed scope:**
  - "Mandatory bounded TTL" is inaccurate. `ttl=` is optional; it defaults to
    `agent_hold_default_ttl` (`2h`) and is capped by `agent_hold_max_ttl` (`12h`). What
    is mandatory is that every hold is bounded.
  - "Family/proc terminal release" should say *session*, following the agent-session
    rename: a hold ends when its armer's session settles or its shell exits.
  - You cannot document "`%queue` on stand-alone procs" without first saying `%proc`
    exists. Today `xprompts.md` does not mention `%proc` or `%if`, which are beta
    directives behind `typed_launch_units`, or `%dispatch`. Include at least a one-line
    `%proc` row flagged beta.
  - Default weight `0` applies only to the proc's admission *check*. Once dispatched, a
    proc holds no runner capacity (`docs/xprompt.md` ~2014–2019).
- The optional decisions strand (pull model, fail-open store, session-scoped release) is
  reasonable but lower value. Do it only if `sase-11l`'s plan records the rejected
  alternatives explicitly.
- **Coordination:** `%queue` just gained a capacity multiplier (`%q:1.5x`, `6beedbc118`,
  epic `sase-19f` IN_PROGRESS). `xprompts.md` still says capacity is an "authored
  positive integer `N`". Do not fold that into `sase-134`; leave it to `sase-19f`'s land
  agent or a follow-up. The same `%queue` paragraph will be touched twice, so sequence
  the edits.

### 8. `sase-148`: `tools/AGENTS.md` ToolRun smokes paragraph. **Valid; proposed text is stale.**

- `tools/AGENTS.md:62-66` still ends: "Later-phase live owner cases remain labeled
  phase-pending unless `--live` is passed." The harness emits `not-run`
  (`NOT_RUN = "not-run"`, `tools/_smoke_tool_runs_lib.py:29`) and never emits
  `phase-pending`.
- The bead's proposed change names "three live cases … 35 cases". That count is already
  wrong. Eight cases are now live-gated: three in `_smoke_tool_runs_cases_owners.py` and
  five in `_smoke_tool_runs_cases_handoff.py`, namely
  - `dod-8-live-monitor`
  - `dod-8-live-proc`
  - `dod-13-overhead`
  - `dod-14-live-handoff-{stop,viewers,crash,delivery}`
  - `dod-14-live-monitor-handoff`
- The paragraph's contract list also leaves out the hand-off group added in `c91690efcb`.
  The two +1s (`sase-17p.land`, `sase-18j.land`) corroborate this drift.
- **Recommended text avoids counts and case IDs**, which keep drifting, and mirrors the
  harness docstring (`tools/smoke_sase_tool_runs:10-11`).
- `tools/AGENTS.md` is a directory-scoped agent instruction file, not a
  `sase/memory/` note. Its provider shims (`tools/CLAUDE.md`, `GEMINI.md`, `OPENCODE.md`,
  `QWEN.md`) are byte-identical copies with the same git blob, not hardlinks in this
  checkout, so `sase memory init` must regenerate them.

### 9. `sase-16r`: `fix-tui-screenshots` partial-success contract. **Valid; apply.**

- Commits `7f019258b1`, `716291a9fd`, `890058e803`, and `4be75a3d41` are all on master.
  The contract is confirmed in `_HELP_EPILOG` (`tests/ace/tui/visual/_visual_maintenance_cli.py:58-82`)
  and the Justfile `check-full` comment:
  - update mode exits 0 with status `clean`, `applied`, or `partial`;
  - a WARNING block, and manifest fields `skipped` and `pruning_skipped_reason`;
  - `-n` becomes `SASE_PYTEST_WORKERS`, while `-n` in `PYTEST_ADDOPTS` is a usage error;
  - the lock wait is bounded (default 2 h);
  - `--check` stays strict.
- Neither `lint_and_test.md` › *PNG Snapshot Tests* nor `tui_screenshot.md` › *Golden
  Maintenance* mentions `partial`. An agent could read a `partial` exit 0 as "goldens
  current". That is the highest-impact gap in this set.
- Epic `sase-169` is still IN_PROGRESS, but its land agent filed this bead after the
  documentation commit (`4be75a3d41`), so the contract is settled. Related bead `sase-16q`
  (the other `lint_and_test.md` edit) is CLOSED, so there is no collision.
- The bead's `path` field lists only `lint_and_test.md`, but the change also covers
  `tui_screenshot.md`.

### 10. `sase-18a`: Fail-closed `sase tool run -H` decision strand. **Valid; lower priority.**

- `decisions:record-before-admit` claims "recording stays fail-open even where admission
  later becomes fail-closed."
- `docs/tool.md:205-209` and `src/sase/tool/handoff.py:86,111`
  (`# reservation is fail-closed`) confirm the change: explicit `-H` refuses to start
  when its reservation cannot be committed (exit 1, "nothing was started"). Foreground
  runs and monitor-start reservations stay fail-open.
- Under the web's immutability rule, the right fix is a new strand plus a second
  "superseded in part" mark on `record-before-admit`, which already carries one from
  `guarded-recipes`.
- Priority is lower because `-H` refuses inside agents, so no agent *runs* it. The
  record exists to stop a future `sase tool` implementer from "fixing" `-H` back to
  fail-open. The Why, Cost, and Reopen text should come from plan decision 3 of
  `plan:202609/tool_e2_durable_handoff.md`, not be invented.

### 11. `sase-18h`: `just check` skips `toobig`. **Valid; apply (XS).**

- `lint_and_test.md` says `just check` "runs every whole-repo lint gate plus …" and
  describes `just check-full` as "every lint gate + the full test suite". Neither is
  true.
- The Justfile (`:713-716`, `:748`) says: "The `toobig` line-count gate is deliberately
  not a `check`/`check-full` stage … It still runs in `just lint`, which CI's lint and
  master-gate jobs run, and on demand via `just toobig`." The `check` recipe body
  (`:729-745`) has no toobig stage.

### 12. `sase-195`: `tui_perf.md` rule 12 (guard flag vs. queued `OptionHighlighted`). **Valid defect; proposed fix is wrong.**

- Rule 12 today: "Set a guard flag and clear it synchronously (`finally:`) — clearing via
  `call_later` races the queued echo." It never says **where** to check the flag.
  `CommandLinePopup` shows that a flag checked in the `OptionHighlighted` handler never
  matches, because Textual 8.0.1's `OptionList.watch_highlighted` calls `post_message`
  (a queued message), so the handler runs after the `finally:` has already cleared the
  flag.
- **The bead goes too far.** Its proposed text, "a guard flag cleared in `finally:` does
  not work for OptionList", contradicts the pattern that already works in at least five
  widgets: `AgentList`, `BgCmdList`, `PatchList`, `BeadsOptionList`, plus the artifacts
  `*_navigation` lists.
  - Those widgets set the flag, **override `watch_highlighted`, and return without
    calling `super()`** while the flag is set (`agent_list.py:476-500`,
    `bgcmd_list.py:457-471`, `beads_option_list.py:49-52`).
  - The watcher runs synchronously inside the assignment, so the echo is never posted
    and the `finally:` clear is correct.
  - The docstring on `AgentList.watch_highlighted` describes exactly the race the bead
    reports, and this pattern is its fix.
- **Caveat worth recording:** the override also skips Textual's `scroll_to_highlight()`.
  That is why `AgentList._set_highlighted_programmatically` calls it explicitly, and a
  plausible reason `CommandLinePopup` counts echoes instead.
- Applying the bead's text as written would steer agents away from the dominant, correct
  pattern. The corrected rewrite below keeps both patterns and names the real
  anti-pattern.

### 13. `sase-sa`: Glossary "Proc Shell". **Valid; bead path is stale.**

- The strand still says "a named supervised proc belonging to a sase agent."
- Stand-alone `%proc` units submit a `ProcSubmitRequest` with
  `origin=xprompt_proc_origin()` (`"xprompt-proc"`) and no session
  (`src/sase/agent/launch_proc_runtime.py:267-281`).
  `src/sase/ace/tui/models/agent_proc_shells.py` projects them as their own Agents-tab
  rows.
- **Path correction:** the bead points to `sase/sase.yml` `glossary.terms`, but the
  glossary migrated to a memory web in `df956212be` (2026-08-24). The target is now
  `glossary/proc-shell.md`.
- **Precision correction:** stand-alone proc shells *also* carry `shell_kind: "proc"`
  (the `ProcSubmitRequest` default, `src/sase/procs/request.py:40`). So the current
  parenthetical "A session-attached proc shell (`shell_kind: "proc"`) is a sase
  monitor" wrongly suggests that `shell_kind: "proc"` implies a monitor. What tells the
  two cases apart is session attachment or origin, not `shell_kind`.
- `%proc` is still beta (`typed_launch_units`, kind `beta`), so the definition should say
  so.
- `glossary:sase-monitor` ("a session-attached proc shell…") remains accurate.

## Recommended Memory File Changes

Route each edit through `/sase_memory_write`, which needs your explicit permission. Then
run `sase memory init` and confirm `sase memory init --check` is clean. Close each bead
with `sase bead close <id> --note "<what changed>"`. Edits to the same file are grouped
so each file is touched once.

### A. Apply now

**A1. `lint_and_test.md`** (closes `sase-18h` and half of `sase-16r`)

1. Code block comments:
   - `just check`: "Agent default: whole-repo lint gates **except `toobig`** + a
     diff-scoped test lane…"
   - `just check-full`: "every lint gate **except `toobig`** + the full test suite +
     local TUI screenshot update…"
2. *Two-Speed Verification*, first sentence: "`just check` runs every whole-repo lint
   gate **except `toobig`** plus a diff-scoped test lane…". Then add:
   > Neither `just check` nor `just check-full` runs the `toobig` line-count gate: CI
   > enforces it through `just lint`, `just toobig` runs it on demand, and the
   > `toobig_split` routine owns the resulting splits.
3. *PNG Snapshot Tests*: add after the paragraph that ends "…never writes goldens.":
   > Update mode (`just fix-tui-screenshots`, `just update-visual-snapshots`, and the
   > update stage of local `just check-full`) applies every golden it can prove and
   > exits 0 with status `clean`, `applied`, or `partial`. `partial` means some nodes or
   > goldens were skipped (failing tests, unstable captures, concurrent edits, or stale
   > removal skipped on incomplete evidence); those goldens are unchanged and **not known
   > to be current**. After a `partial` run, read the WARNING block or the manifest's
   > `skipped` list and `pruning_skipped_reason`; never read `counts:` alone as "nothing
   > to update". `-n N` after `--` becomes the governed `SASE_PYTEST_WORKERS` request
   > (`-n` in `PYTEST_ADDOPTS` is a usage error). A second run in the same checkout waits
   > for the maintenance lock (bounded, default 2 h). `--check` stays strict: it never
   > writes and exits 1 on required drift.
4. Optional (the `sase-sl` residue): after "do not treat CI as a tolerance lane", add
   "`SASE_VISUAL_PNG_*` tolerances exist only as explicit local escape hatches for
   renderer investigation."

**A2. `tui_screenshot.md`** (closes `sase-12x` and the other half of `sase-16r`)

1. *Troubleshooting*: replace the "Missing visual extra" bullet with:
   > Renderer import error (`resvg_py`): `resvg_py` is a base runtime dependency, so a
   > missing import means the SASE install is incomplete or stale. Run `sase update` or
   > reinstall the environment that owns the `sase` entry point. Do not fall back to a
   > second renderer.
2. *Golden Maintenance*: add one sentence plus a link, so the contract is not
   duplicated:
   > The update form can exit 0 with status `partial` and leave some goldens untouched;
   > read its WARNING block before treating goldens as current (details in
   > [[lint_and_test.md]] › PNG Snapshot Tests).
3. Optional: in *Implementation Rules*, change "the bundled Fira Code fonts" to "the
   bundled Fira Code / DejaVu / Noto Emoji font stack" to match `lint_and_test.md`.

**A3. `xprompts.md` › Invoke** (closes `sase-st`)

- Replace the Args bullet's tail with:
  > …quoted comma/special values, `[[ ... ]]` multi-line text. A `[[` block closes at
  > the first `]]` followed (after optional whitespace) by `,`, `)`, `}`, `|`, or the end
  > of the args; any other `]]` is content. Quote the value when a literal `]]` must
  > precede one of those terminators.
- Append to the Shorthands bullet:
  > Line shorthands (`#name: text`, `#name:: text`, `#name(args): text`) bind their
  > payload structurally and are never re-lexed as `[[...]]`, so commas, `]]`, `+`, and
  > unbalanced parens in prose stay literal. `+` means a space only in the bare unquoted
  > `#name:a,b` colon form.

**A4. `tui_perf.md` rule 12** (closes `sase-195`; use this corrected text, not the
bead's)

> 12. **Guard programmatic widget updates.** A programmatic `OptionList.highlighted = X`
>     makes Textual's `watch_highlighted` post an `OptionHighlighted` message, and that
>     message is *queued*. Silence the echo at its source: set a guard flag around the
>     assignment and override `watch_highlighted` to return without calling `super()`
>     while the flag is set (`AgentList`, `BgCmdList`, `PatchList`, `BeadsOptionList`).
>     The watcher runs synchronously, so clearing the flag in `finally:` is correct
>     there. The override also skips Textual's `scroll_to_highlight()`, so scroll
>     explicitly (`AgentList._set_highlighted_programmatically`). A flag checked only in
>     the `OptionHighlighted` *handler* never matches, because it is already cleared
>     (by `finally:` or a racing `call_later`) when the echo arrives. When the message
>     must still be posted, count pending echoes per row and drop echoes whose `Option`
>     is no longer in the list (`CommandLinePopup._pending_echoes` /
>     `user_highlight_index`). `clear_options()` posts no echo.

**A5. `glossary/proc-shell.md`** (closes `sase-sa`; first update the bead's path field)

> A proc shell is a named supervised proc (`shell_kind: "proc"`) with durable output and
> lifecycle state. It is either **session-attached**, meaning a sase monitor that
> belongs to the agent session that started it and may carry timeout, workspace-claim,
> and follow-up policy, or **stand-alone**: a beta `%proc` launch unit dispatched
> natively with origin `xprompt-proc`. A stand-alone proc shell belongs to no agent or
> session, allocates no agent runner, and appears in the Agents tab as its own row kind,
> counted separately from agents. A gate shell's execution-phase proc does not make it
> a proc shell: it stays `shell_kind: "gate"` throughout, pending or executing.

**A6. `tools/AGENTS.md` › ToolRun smokes** (closes `sase-148`; regenerate the shims with
`sase memory init`)

> …it talks to the real store and CLI for catalog, foreground run, signals, lost-run
> recovery, fail-open recording, hand-off, and query contracts. Cases that need the real
> monitor/proc supervisors or a cold-start timing measurement are labeled `not-run`
> unless `--live` is passed; `--live` runs them too.

Do not name case counts or IDs here; they have already drifted twice.

**A7. New strand `decisions/machine-link-writes-off-primary.md`** (closes `sase-yd`)

Use the bead's `proposed_change` verbatim as the record body: claim, three rejected
alternatives, cost, reopen condition, implementing code, and a link to
`plan:202609/machine_link_mutations_off_primary.md`. Add `[[sase_artifacts.md]]` as a
neighbor link, since that note is where an agent doing link maintenance will be reading.

### B. Apply when convenient (lower priority)

**B1. New strand for `-H` fail-closed, and a partial-supersede mark on
`decisions/record-before-admit.md`** (closes `sase-18a`)

- Suggested slug: `handoff-fails-closed`.
- Claim: explicit `sase tool run -H` starts nothing unless its ToolRun reservation
  commits, because the printed run id is the caller's only handle. Foreground runs and
  monitor-start reservations stay fail-open, because the terminal or the monitor id is
  already durable.
- Take the Why, Cost, and Reopen text from plan decision 3 of
  `plan:202609/tool_e2_durable_handoff.md`.
- On `record-before-admit`, add the new slug to its `superseded_by` metadata and add a
  second "_Superseded in part:_" paragraph that narrows only the "recording stays
  fail-open" clause.

### C. Deferred: re-verify when the blocking epic closes

**C1. `xprompts.md` directive table and `%queue` paragraph** (`sase-134`; add a
dependency on `sase-11l`)

When `sase-11l` closes:

- Add a `%hold` row: pre-admission barrier on *other* work; matching agents stay
  `QUEUED` and undispatched `%proc` units stay pending; running work is never touched.
- Add a short paragraph covering:
  - selectors: name, `@tribe`/`tribe=`, `hood=`, `pending`, `future`;
  - `scope=project|host`;
  - `ttl=` defaults to 2 h and is capped at 12 h;
  - a hold ends on release, when its armer's session or shell ends, or at TTL;
  - a broken store fails open;
  - bare `%hold` is an error; there is no alias (`%h` stays `%hide`); no `%repeat` or
    `%dispatch`;
  - imperative form: `sase agent hold create|run|list|show|release`.
- Add a beta `%proc` row (behind `typed_launch_units`) and one sentence: `%queue` on a
  `%proc` gates dispatch on a capacity check (an omitted weight counts as `0`) but never
  holds a claim.
- Sequence this after `sase-19f`'s `%q:<M>x` multiplier update, which touches the same
  paragraph.

**C2. New `dispatch.md` reference note** (`sase-ya`; add a dependency on `sase-xe.16`)

After `sase-xe.16` lands, write a **short** pointer note to `docs/remote_dispatch.md`
that lists only the agent-relevant rules (see finding 4). Re-verify the Focus/Fleet
claims before writing them, and use session vocabulary rather than family. Consider
adding the `%dispatch` row to `xprompts.md` in the same edit.

### D. Bead housekeeping (no memory edits)

| Bead                            | Action                                                                                                          |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `sase-sl`                       | Close `-R superseded`: fixed by `1c246dc748`                                                                    |
| `sase-xs`, `sase-xt`, `sase-xu` | Close `-R canceled`: abandoned message-board experiment, not a memory update                                    |
| `sase-sa`                       | Update the `path` field to `glossary/proc-shell.md` before work starts                                          |
| `sase-16r`                      | Note that `tui_screenshot.md` is also in scope                                                                  |
| `sase-195`                      | Note that the proposed text is superseded by A4 (the `watch_highlighted` override pattern is correct)          |
| `sase-148`                      | Note that eight live cases exist now, and that the paragraph should not enumerate them                          |
| `sase-134`                      | Add a dependency on `sase-11l`, and note the TTL/session corrections and the `sase-19f` sequencing              |
| `sase-ya`                       | Add a dependency on `sase-xe.16`, and note the rescoping to a short pointer note                                |

Net result:

- **Now (A1–A7 and B1):** 7 existing files edited (`lint_and_test.md`,
  `tui_screenshot.md`, `xprompts.md`, `tui_perf.md`, `glossary/proc-shell.md`,
  `tools/AGENTS.md`, `decisions/record-before-admit.md`) plus 2 new decision strands.
  These close 9 beads.
- **Later (C1, C2):** 2 beads wait on their epics.
- **No edit:** 4 beads close outright.
