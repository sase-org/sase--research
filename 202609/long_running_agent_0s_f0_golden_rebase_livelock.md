---
create_time: 2026-09-20
updated_time: 2026-09-20
status: research
---

# Why `0s.f0` Has Been Running For 7h41m On Apollo

- **Date:** 2026-09-20 · **Investigated at:** 19:16 UTC (15:16 EDT), agent still `RUNNING`
- **Subject:** `0s.f0--code`, pid 1777877, workspace `sase_16` on `apollo`
- **Question:** what caused / is causing the long runtime of the `0s.f0` sase agent?
- **Method:** live process inspection on apollo, plus quantitative analysis of the run's
  own telemetry (`tool_calls.jsonl`, `continuation_stage_diagnostics.jsonl`,
  `commit_state.json`, `final_submission.json`, `finalizers/`) and the workspace git
  reflog. No instrumentation was added and nothing in the run was disturbed.

## TL;DR

The agent is not hung, not deadlocked, and not thinking too long. It is doing real work
the whole time, and **92.5% of its wall clock is spent blocked inside `Bash` tool calls
waiting for TUI PNG-golden regeneration and visual pytest suites** — 339 of 412 minutes
of tool time (82%). Model reasoning accounts for only 33.9 minutes (7.6%).

There are two distinct causes stacked on top of each other:

1. **Blast-radius amplification (cause of the first 4.8 hours).** The assigned plan is a
   `tier: tale`, `size: medium` cosmetic change: render the ACE top-bar launch-default
   pill as `grok-4.6@high` instead of `GROK(grok-4.6)@high`. The pill became **one column
   shorter**. Because TUI goldens are compared by *exact pixel equality*, that one-column
   shift invalidated ~190 of 194 in-scope goldens. The declared commit is **123 PNG
   goldens against 5 real source/doc files**. Regenerating them costs ~54 minutes per
   run, and the agent ran that class of command **17 times inline**.

2. **A binary-conflict livelock (cause of the last 2.9 hours, and still active).** The
   agent finished and submitted its final declaration at 16:24. The host's commit
   finalizer created the commit and then failed to push: rebasing onto `origin/master`
   conflicted on the PNG goldens, which git cannot auto-merge. The host granted its
   **one and only** conflict-repair turn. The agent spent 2h32m resolving it and
   **succeeded at 18:58:25** — and then, **10 seconds later**, the push flow started a
   *fresh* rebase because upstream had advanced again during the repair. Nothing has
   landed: `pushed: false`.

The livelock is structural, not a mistake by this agent: **31 commits landed on
`origin/master` during this run, 5 of them touching 213 golden files** (one touched 170).
A repair cycle costs 1–2.5 hours; the conflict is recreated faster than it can be
repaired.

This exact failure mode was **predicted two days earlier** in this repo's own research —
see §7.

## 1. Identifying The Agent

`0s.f0` is an **agent family**, not the running process. The family has three members:

| Agent | Role | Model | Status | Duration |
|---|---|---|---|---|
| `0s.f0--plan` | root | opus | `DONE` | 343 s |
| `0s.f0` | gate shell | opus @ high | `DONE (gated)` at 11:35:06 UTC | — |
| **`0s.f0--code`** | code | **sonnet @ xhigh ← @medium** | **`RUNNING`** | **27,700 s = 7h41m** |

`0s.f0--code` started at 11:35:11 UTC (07:35 EDT) in workspace
`sase_16`. Its prompt is three lines:

```
%model:@medium
#gh:gh_sase-org__sase @plan:202609/tui_default_model_directive_label.md

The above plan has been reviewed and approved. Implement it now.
```

A fourth agent, `0s.f0.f0` (opus), has been `WAITING` on `0s.f0` since 12:49:23 UTC —
**6h27m of blocked downstream capacity**.

**Note on effort:** `%model:@medium` resolved to `CLAUDE(sonnet) @ xhigh`, which is
correct per `decisions:size-alias-effort-ladder` (built-in size aliases run at `xhigh` on
first appearance). It is tempting to blame `xhigh` for the runtime. **The telemetry rules
this out:** non-tool time across the whole run is 33.9 minutes. Effort is not a material
cause here.

## 2. Where The Time Actually Went

Derived from the run's own `tool_calls.jsonl` (465 events, 233 `ToolUse` / 232 matched
`ToolResult`, 1 still in flight) by pairing each call with its result:

- **Wall span of recorded tool events:** 7.43 h (11:35:26 → 19:01:12 UTC)
- **Sum of tool-call durations:** 6.87 h — **92.5% of the span**
- **Non-tool (model) time:** 33.9 min across 223 gaps; largest single gap 1.9 min

Tool calls: 184 `Bash`, 28 `Read`, 14 `Edit`, 5 `Skill`, 2 `Write`. All 412 minutes of
tool time is `Bash`; every non-Bash call is sub-second.

### Time by category

| Minutes | Share | Calls | Category |
|---:|---:|---:|---|
| 242.7 | 58.8% | 32 | pytest visual / test suites |
| 96.5 | 23.4% | 17 | `fix-tui-screenshots` (regen + `--check`) |
| 45.5 | 11.0% | 12 | lint / check gates |
| 9.4 | 2.3% | 24 | env / `just install` |
| 8.5 | 2.1% | 11 | bead / artifact bookkeeping |
| 5.6 | 1.4% | 55 | other |
| 4.2 | 1.0% | 32 | git / rebase-merge ops |

**TUI visual work alone = 339.2 min = 82.2% of all tool time** (76% of total wall clock).

### The ten most expensive single tool calls

| Minutes | Command (truncated) |
|---:|---|
| 53.8 | `time just fix-tui-screenshots > /tmp/fix_tui_screenshots_rebase.log` |
| 52.3 | visual pytest with a long `K='not (...)'` exclusion filter |
| 40.5 | `/tmp/run_batches.sh 13 a` |
| 34.3 | visual pytest, same `-k` filter |
| 28.7 | `git status --short && K='not (...)'` visual pytest |
| 27.3 | `/tmp/retry.sh` (visual retry harness) |
| 26.3 | `time just test-scoped` |
| 26.2 | `time sase tool run check` |
| 16.9 | `git stash push -u` + visual pytest |
| 13.2 | `just fix-tui-screenshots` (goldens count + timing) |

Twelve tool calls returned `failure`.

### Token cost

`usage.json` (written at the first final declaration, so **session 1 only**):

```
input_tokens                     250
output_tokens                108,157
cache_creation_input_tokens  263,130
cache_read_input_tokens   19,822,976
```

19.8M cache-read tokens over 148 tool calls — the context is being re-read on nearly
every turn because each long Bash result is appended to a growing transcript.

## 3. Cause 1 — A One-Column Label Change With A 123-File Blast Radius

The plan (`~/.sase/plans/202609/tui_default_model_directive_label.md`, `tier: tale`,
`size: medium`) states the goal plainly:

> The ACE top-bar calm launch-default pill names the launch default with the smallest
> string the `%model` directive would accept (`grok-4.6@high`) instead of
> `PROVIDER(model)@effort` (`GROK(grok-4.6)@high`).

The accepted declaration (`final_submission.json`) shows what that cost. The single
repository obligation carries **128 paths**:

- **123 PNG goldens** under `tests/ace/tui/visual/snapshots/png/`
- **5 real files:** `docs/ace.md`, `docs/llms.md`,
  `src/sase/ace/tui/widgets/llm_override_indicator.py`,
  `src/sase/llm_provider/model_directive_label.py`,
  `tests/ace/tui/visual/_ace_png_snapshot_startup.py`

`lint_and_test.md` states the mechanism: *"Comparison is exact pixel equality locally and
in CI; do not treat CI as a tolerance lane."* Because the pill sits in the top bar of
essentially every full-screen capture, and 680 goldens live in that directory, a
one-column narrowing reflows a strip present in almost every frame. The agent's own
commit body records the measurement: the pill is one column shorter, so in 60-column
frames the Artifacts tab label now fits.

### 3a. A large fraction of the work was not this change's fault

The agent's commit body carries an explicit disclosure:

```
SASE_UNRELATED_SCREENSHOT_UPDATES=about 160 of the regenerated goldens also absorb
pre-existing master drift that check mode reports on an unmodified tree (agents info
row [view: none] and prompt bar [Enter] launch... from the shipped
confirm_on_enter=true), not caused by the pill change
```

So ~160 of the regenerated goldens were **already stale on master before this agent
started**. The agent had to distinguish its own pixel changes from pre-existing drift,
which is why the transcript shows it building upstream-only comparison trees under
`/tmp/up` and running both trees the same way to diff per-test outcomes.

It also found and filed **11 beads** for genuinely pre-existing breakage (`sase-13k`,
`13l`, `13v`, `119`, `cx`, `13y`, `13z`, `140`, `142`, `143`, `144`) across **17 bead
commits between 15:58 and 16:21 UTC** — about 23 minutes of bookkeeping, plus
substantially more in the reproduction runs that justified them. Ten test cases fail on
unmodified master in this environment, and one golden (`commits_persistent_filter`,
80x24) is non-deterministic.

This is correct behavior, and the beads are valuable. It is also a large, unbudgeted
addition to a `size: medium` tale.

### 3b. The suites were run inline rather than through a monitor

`lint_and_test.md` is explicit:

> Full and targeted visual commands may require `/sase_monitor` with `TESTING` /
> `TESTED`. Increase the timeout for a full run […] **Do not run the contention harness
> or repeat full visual suites routinely.**

and

> `just check` may be run inline, but hand it to a monitor the same way **whenever it is
> taking a long time**.

Every one of the 49 visual/pytest calls in §2 ran **inline in the provider turn**. Inline
execution makes wall clock the *sum* of the runs, and it is why 92.5% of the span is
blocked I/O. Handing the 53.8-minute regeneration and the 52.3/40.5/34.3/28.7-minute
suites to `/sase_monitor` would not have reduced CPU cost, but it would have ended the
turn and freed the runner slot that `0s.f0.f0` has been waiting 6h27m for.

## 4. Cause 2 — The Binary-Conflict Livelock (Still Active)

This is the part that turned a long run into an unbounded one. The workspace git reflog
is unambiguous; read bottom-up:

```
9a99238cd HEAD@{18:58:35}: rebase (start): checkout origin/master      <-- SECOND rebase
86477f42e HEAD@{18:58:25}: rebase (finish): returning to refs/heads/master
86477f42e HEAD@{18:58:25}: rebase (continue): feat(tui): render the launch-default pill...
307872298 HEAD@{16:26:22}: rebase (start): checkout origin/master      <-- FIRST rebase
c2ac9715d HEAD@{16:26:16}: commit: feat(tui): render the launch-default pill...
d949f060e HEAD@{11:35:17}: pull --rebase --quiet: Fast-forward         <-- run begins here
```

### Timeline

| Time (UTC) | Event |
|---|---|
| 11:35:06 | `0s.f0` gate shell finishes (`gated`), launching `0s.f0--code` |
| 11:35:17 | `sase_16` fast-forwards to `d949f060e` |
| 11:44:09 | first `just check`: **mypy FAILS** after 61 s |
| 15:58–16:21 | 17 bead commits for pre-existing breakage |
| 16:23–16:24 | final declaration submitted and **accepted** (`accepted_instances: ["commit"]`) |
| 16:26:16 | finalizer creates commit `c2ac9715d` |
| 16:26:22 | push flow rebases onto `origin/master` → **conflict on binary PNG goldens** |
| 16:26:32 | host issues the **conflict-repair turn** (new provider session `e025f48f`) |
| 18:11:17 | second `just check`: mypy 78 s ✓, feature flags 100 s ✓, pyscripts 23 s ✓, test waits 31 s ✓, **symvision FAILS** after 136 s |
| 18:58:25 | `rebase (continue)` **SUCCEEDS** → `86477f42e`. The repair worked. |
| **18:58:35** | **a new rebase starts onto `9a99238cd`** — upstream moved during the repair |
| 19:01:12 | agent launches yet another `fix_tui_screenshots --check` |
| 19:16:51 | still `RUNNING` at 7h41m; `pushed: false` |

The finalizer's own outcome record confirms the failure was in the push, not the commit:

```json
{"argv": ["...", "-m", "sase", "stitch", "create", "-M", "..."],
 "duration_seconds": 45.15, "returncode": 2, "timed_out": false}
```

and `commit_state.json` carries:

```
"pushed": false,
"dispatch_error": "commit ... created locally; git push failed: git push failed and
 rebase could not resolve it: Rebase conflict syncing with origin/master.
 Conflicted files: tests/ace/tui/visual/snapshots/png/axe_chop_description_120x40.png, ...
 Could not apply 86477f42e... feat(tui): render the launch-default pill as its shortest
 %model spelling"
```

Note the SHA in that error is `86477f42e` — the *already-repaired* commit. This is the
**second** conflict, not the first.

### Why it cannot converge

Binary files have no merge driver. Any upstream commit that touches a golden this commit
also touches is an unconditional conflict, and the only way to resolve it is to
regenerate the goldens on the integrated tree — a ~54-minute operation, plus ~13 minutes
to verify.

Measured upstream velocity during this single run:

- **31 commits** landed on `origin/master` between 11:30 and 19:00 UTC (~4/hour)
- **5 of them touched golden files**, for **213 golden-file changes** total:

| Upstream commit | Goldens touched |
|---|---:|
| `9a56fc129` fix(visual): integrate the metadata-only Agents default with the screenshot corpus | **170** |
| `1d3bef894` fix(visual): refresh the Services-tab goldens left stale during sase-12z.5 | 18 |
| `4d63f55b3` feat(ace): number notification tabs 1-9/0 with direct digit jump | 15 |
| `9316a24e5` feat(service): run `!` background commands as transient oneshot service procs | 9 |
| `e99bd48ac` test(fleet): run the parity oracle on the production family shape | 1 |

**Repair cycle ≈ 1–2.5 h. Golden-touching commits arrive every ~2 h.** The repair is not
reliably faster than the churn, so each success is immediately invalidated — which is
precisely what the 10-second gap at 18:58:25 → 18:58:35 shows.

### The host will not grant another repair turn

`finalizers/commit/conflict_repair_prompt.main.md` states:

> This is the **single** conflict-repair turn for this repository during this run.

and

> after this declaration is accepted, the host executes remaining declared repository
> obligations once in a bounded continuation and **will not start another
> conflict-repair turn**.

The agent has already consumed that turn. Its work is currently reachable only as commit
`86477f42e` plus an uncommitted tree.

### Current state (19:16 UTC)

- `HEAD` detached mid-rebase onto `9a99238cd`; `.git/rebase-merge` present, `msgnum 1 / end 1`
- **0 unmerged paths** — the agent has re-resolved the second conflict already
- **623 modified + 2 added** files in the working tree
- 2 stashes (`gh_sase-org__sase-ace`, `gh-workflow-1789837869`)
- `pushed: false` — after 7h41m, **nothing has landed**

## 5. Contributing Factor — Host Saturation

`apollo` is a 16-vCPU / 31 GiB DigitalOcean box, up 17 days. During the investigation:

- load average **12.80 / 12.99 / 11.71** at 19:10, falling to **4.41** at 19:16 as the
  visual run completed
- **7 visual workers** from `sase_16`'s venv at **~93% CPU each** — ~6.5 cores for this
  one agent's `fix_tui_screenshots --check`
- concurrently: 4 agent runners, 2 `claude -p` provider processes, the `sase-13t` epic
  clan (`sase-13t.land` waiting on 6 members), `sase axe routine` workers for hooks /
  waits / telegram, and a `sase tui --restart-service` process at 24% CPU that has been
  up for 1d 3h

Visual snapshot capture is CPU-bound font rendering against a pinned Fira Code / DejaVu /
Noto Emoji stack. Running it at load ~13 on a shared 16-core host inflates every one of
the 17 golden runs. This amplifies the runtime; it does not explain it.

## 6. What Is *Not* The Cause

Ruling these out explicitly, because each is a plausible first guess:

- **Not a hang or deadlock.** Every phase transition is timestamped and progressing; the
  in-flight command completed during the investigation.
- **Not `xhigh` effort.** Non-tool time is 33.9 min of 7.43 h (7.6%).
- **Not a stuck gate or unanswered question.** `waiting_for` is empty for `0s.f0--code`;
  no interaction request is pending.
- **Not `just check-full`.** The agent correctly used `sase tool run check`, per
  `decisions:check-full-is-explicit`. Its lint gates cost 45.5 min total — 11%.
- **Not runner-slot queueing.** `runner_slot_queue_position` and
  `runner_capacity_blockers` are null/empty; the agent holds a slot and is executing.
- **Not the agent ignoring instructions.** It read the required memory, filed beads for
  pre-existing breakage rather than papering over it, disclosed unrelated golden churn in
  the commit body, and successfully repaired a 177-file binary conflict.

## 7. This Was Predicted Two Days Ago

`202609/fix_tui_screenshots_command/fix_tui_screenshots_command.md` (2026-09-18) reached
this conclusion before the incident:

> With ~56 commits/day landing and 587 of 674 ACE goldens being full 120×40 screens, any
> chrome change fans out across hundreds of PNGs and **concurrent agents invalidate each
> other's refreshes within hours.**

and researcher B's companion report:

> With ~56 commits/day landing concurrently, **even diligent agents invalidate each
> other's goldens.** The most important addition is a **non-agent backstop**: a scheduled
> GitHub Actions "screenshot ratchet" that regenerates the goldens on master and pushes a
> golden-only commit […] This also moves the regeneration cost off the host, which is the
> resource `decisions/two-speed-verification` says is scarce.

That report also measured the gate as already failed: `visual-test` red in **60 of the
last 60** scheduled Full CI runs. The `0s.f0--code` run is the predicted failure mode
arriving in its most expensive form — a chrome change owned by an agent that must both
regenerate the corpus *and* win a rebase race against it.

The recommended ratchet would have prevented this specific incident on two independent
counts: master's goldens would not have been ~160 files stale when the agent started, and
regeneration would not have been on the critical path of a host-capacity-bound turn.

## 8. Conclusions

1. **Proximate cause:** 82% of tool time is TUI PNG-golden regeneration and visual pytest
   suites, all run inline, for a cosmetic one-column label change that touched 123
   goldens against 5 real files.
2. **Root cause:** exact-pixel binary goldens covering full screens give trivial UI
   changes an enormous, unmergeable blast radius. At ~4 commits/hour on master with
   periodic golden churn, the regenerate-and-rebase cycle is slower than the rate at
   which its own conflict is recreated. That is a livelock, and `0s.f0--code` is in it.
3. **Aggravating factors:** ~160 pre-existing stale goldens and 10 tests already failing
   on master, which the agent had to diagnose and file (11 beads) before it could trust
   its own diff; host load ~13 on 16 cores inflating all 17 golden runs; and the choice
   to run hour-long suites inline rather than through `/sase_monitor`, which also kept
   `0s.f0.f0` blocked for 6h27m.
4. **Current risk:** the single conflict-repair turn is spent, the second rebase is
   mid-flight, and `pushed: false`. Without intervention this run is more likely to end
   with its work stranded in `86477f42e` plus a 625-file dirty tree than to land.

### Fixes, in order of leverage

1. **Land the scheduled screenshot ratchet** from the 2026-09-18 research. It is the only
   proposal that addresses the root cause, and it moves regeneration off host capacity.
2. **Give golden-only rebase conflicts a resolution strategy that does not require full
   regeneration** — e.g. resolve goldens as "regenerate after rebase" via a merge driver
   or a post-rebase regeneration hook, instead of treating 177 binary conflicts as
   semantic ones needing a repair turn.
3. **Make the conflict-repair budget match the cost of the repair.** One turn is
   reasonable for a text conflict and structurally insufficient for a golden corpus whose
   repair takes longer than the interval between conflicts.
4. **Route full visual suites through `/sase_monitor` in practice, not just in memory
   guidance.** Consider making `fix-tui-screenshots` refuse to run inline in an agent
   turn above some expected duration.
5. **Reduce golden surface area.** 587 of 674 goldens being full 120×40 screens is what
   converts a top-bar change into a corpus-wide rewrite; narrower captures for chrome
   would cut the fan-out directly.

## Appendix — Evidence Paths

On `apollo`, artifacts dir
`~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/20/20260920073506/`:

| File | What it established |
|---|---|
| `tool_calls.jsonl` | 465 events; per-call durations, the 92.5%/7.6% tool-vs-model split, category breakdown, two provider sessions |
| `continuation_stage_diagnostics.jsonl` | both `just check` batches; mypy fail at 11:45, symvision fail at 18:17:55 |
| `final_submission.json` | accepted declaration; the 128-path obligation (123 PNG) |
| `final_submission_attempts.jsonl` | `accepted` at 16:24:40 |
| `commit_state.json` | commit message, `pushed: false`, full `dispatch_error` naming `86477f42e` |
| `commit_results.json` | 17 bead commits 15:58–16:21, `create_commit` at 18:40:32 |
| `finalizers/commit/attempt-1.main.outcome.json` | `sase stitch create` returncode 2, 45.15 s, not timed out |
| `finalizers/commit/conflict_repair_prompt.main.md` | the single-repair-turn contract |
| `usage.json` | 19.8M cache-read tokens (session 1 only) |
| `live_reply.md` | in-flight narration (draft; quoted only as intent, not fact) |

Workspace `~/.local/state/sase/workspaces/sase-org/sase/sase_16`: reflog, `HEAD`,
`.git/rebase-merge/{msgnum,end,onto}`, `git status --porcelain`, `git log origin/master`
churn counts.

Reference memory consulted via `/sase_memory_read`: `lint_and_test.md`, `tui.md`,
`tailnet.md`. Prior research: `202609/fix_tui_screenshots_command/`.
