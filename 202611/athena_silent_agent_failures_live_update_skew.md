# Silent Agent Failures on Athena: Live Code Swaps Under Running Agents

_Research report · 2026-11-03 · host: athena_

## TL;DR

- **What happened.** At **10:56:12 today (2026-11-03)**, the automatic `sase update` fast-forwarded the primary checkout at `~/projects/github/sase-org/sase` from `a1a07efff8` to `ced5901dd5`. That commit is "feat(axe): finish staged-handoff kill-path landing", landed by `sase-1pj.8.1.land`. It removed two keyword arguments from functions in the staged-handoff path: `require_capture` from `capture_monitor_handoff()` and `persist_chat` from `handle_gate_marker()`.
- **How it broke running agents.** The global `sase` tool is an **editable install** of that checkout. Any runner process that was already alive kept the old modules in memory, but imported the new versions from disk the first time it lazily imported them. Within 2.5 minutes, three in-flight agents crashed at the moment the host adopted their staged handoff:
  - `sase-1n6.11.1` (muse) at 10:56:53
  - `178.w0--plan` (claude/opus) at 10:57:03
  - `17a--3` (codex/gpt-6-luna) at 10:58:51
- **Why it looked silent.** A FAILED notification did fire for each crash, but nothing else caught it:
  - The update-skew auto-restart healer only looks for import and attribute errors, so it classified all three as "not skew" and stayed idle (`nothing_eligible`). This gap is now filed as `sase-1r4`.
  - The staged successors the agents had prepared never launched.
  - The work they carried was never committed.
  - One monitor still sits in `staged` state and shows in the "Running" bucket.
  - Downstream epic phases waited for about six hours with no error anywhere.
- **The same mechanism hit on Nov 1.** You started the reboot at 07:26, 18 minutes after a 25-commit auto-update at 07:07:59. Monitors that got SIGTERM tried to settle using a mix of old and new code, and settlement crashed on Python and Rust binding skew. Their follow-ups never launched. Seven of the eight `.f0` recovery agents launched at 13:17 then failed on a bead-claim conflict. **Five beads are still `in_progress` today, owned by agents that died 2.5 days ago.**

**Verdict on the suspicion.** Your prompt didn't say what you suspected, so I tested every candidate event in this machine's recent history (next section).

- **Confirmed** if you suspected a SASE code update or upgrade landing under running agents.
- **Partly confirmed** if you suspected the Nov 1 reboot. It stranded agents silently, but its damage was made worse by the same code-skew bug.
- **Ruled out:** your manual `just install` runs and today's `chez update` don't correlate with any failure.

## Candidate events, tested

Each event below comes from shell history, the journal, or the primary checkout's reflog.

1. **Automatic `sase update` fast-forward at 10:56:12 today: CONFIRMED root cause of today's failures.**
   - The primary checkout's reflog shows `merge origin/master: Fast-forward` to `ced5901dd5` at 10:56:12.
   - The AXE scheduler restarted at 10:56:40, as it does after every update.
   - Three agents whose runners booted before 10:56:12 crashed between 10:56:53 and 10:58:51 with `TypeError: … got an unexpected keyword argument …`, naming exactly the parameters `ced5901dd5` removed.
2. **The 2026-11-01 07:26 reboot (`reboot` in shell history): CONFIRMED as an earlier, separate cause of silent strandings, compounded by the same skew bug.**
   - systemd stopped 29 `sase-agent-*.scope` runner scopes at 07:26:27.
   - Seven of them did not exit within the stop timeout and were SIGKILLed at 07:27:57 (`Stopping timed out. Killing.`), so they never wrote `done.json`.
   - You already knew about this reboot. It's the subject of `16p` on Nov 1. The new finding is that its recovery is still incomplete; see "Residual damage".
3. **Your `just install` runs at 07:25:16 and 11:25:28 today: RULED OUT.**
   - No agent failure, kill, or skew error falls near either time.
   - The 10:56 crashes happened 30 minutes *before* the 11:25 install.
4. **`chez update -v -a` at 15:48:04 today: RULED OUT.**
   - Agent failures after 15:48 are ordinary work failures, such as `bob-cli-gj.2.1.4` monitors exiting 101 and 2 on a duplicate `note_pull` field in bob-cli, which `17p.f0` diagnosed.
   - None of them involve config, skills, or provider CLIs.
5. **AXE scheduler restarts with no `stop` record (8 today): NOT a cause.**
   - `~/.sase/axe/lifecycle.jsonl` shows `start` events at 06:38, 09:15, 10:39, 10:56, 12:35, 14:20, 15:47, and 16:17 with no matching `stop`.
   - Each one follows a primary fast-forward by about 30 seconds, so it is the update restarting the scheduler.
   - Agent runners live in their own systemd scopes and survive these restarts. None of today's crashes is a kill: all three have Python tracebacks.
6. **Daylight-saving change on 2026-11-01 02:00: NOT a cause.** No failure clusters at the DST boundary, and timestamps in `done.json` and the artifact directory names are consistent.
7. **OOM kills and disk pressure: NOT a cause.**
   - There are no OOM kills in the journal since Oct 31.
   - `/` is 64% full.
   - Load is high (11 to 15) but nothing was killed for it.

## Today's incident, step by step

### Timeline (2026-11-03, America/New_York)

- **09:36:09:** `178.w0--plan` boots on sase `323a91d69f` and starts planning the v0.19.0 release epic.
- **09:53:05:** `sase-1n6.11.1` boots in workspace `sase_11` and works on `sase-core` `release_steward`.
- **10:50:37:** `ced5901dd5` is committed by `sase-1pj.8.1.land`. That agent reports completion at 10:55:12.
- **10:53:12:** `17a--3` boots on sase `a1a07efff8` to continue fixing bob-mac-capture CI.
- **10:54:39:** `sase-1n6.11.1` closes its bead `sase-1n6.11.1` (resolution `done`), then stages a verification monitor and ends its provider turn.
- **10:56:12:** The automatic `sase update` fast-forwards the primary checkout `a1a07efff8 → ced5901dd5`.
- **10:56:40:** The AXE scheduler restarts.
- **10:56:53:** `sase-1n6.11.1` crashes. The host's staged-monitor adoption raises `TypeError: capture_monitor_handoff() got an unexpected keyword argument 'require_capture'`.
- **10:57:03:** `178.w0--plan` crashes. Staged plan adoption raises `TypeError: handle_gate_marker() got an unexpected keyword argument 'persist_chat'`.
- **10:58:51:** `17a--3` crashes with the same `require_capture` TypeError. Its staged monitor `vdgpvm` (`17a--mon-2`) never starts.
- **10:58 to 16:43:** The `auto_restart` healer runs about every 70 seconds and logs `targets=0 … reason=nothing_eligible` every time.
- **16:43:37:** You relaunch `sase-1n6.11.1` from ACE. Launch-time eviction rescues the first run's uncommitted `sase-core` edits from workspace 11 into `~/.sase/rescue/`.
- **16:51:** You re-run `actstat` and launch `17r`. bob-mac-capture CI is still red, because `17a`'s fix never ran its verification or landed.

### The mechanism

1. **The editable install makes the primary checkout the live code for every process.**
   - `~/.local/share/uv/tools/sase/uv-receipt.toml` installs `sase` as `editable = "/home/bryan/projects/github/sase-org/sase"`.
   - The automatic `sase update` keeps that checkout fast-forwarded to `origin/master`. Its journal `~/.sase/update_attempts.json` is at revision 1335; the last success started at 16:16:34.
   - The checkout moved 8 times today and 17 times since Nov 1.
2. **Runner processes import lazily, so they mix code from two revisions.**
   - The staged-handoff adopters in `src/sase/axe/run_agent_exec_staged_adopters.py` import their targets inside function bodies. For example, `_adopt_monitor` does `from sase.axe.run_agent_exec_monitor import capture_monitor_handoff` at the old line 347.
   - These imports run when the provider turn ends, often an hour or more after the runner booted.
   - `17a--3` had `_adopt_monitor` in memory at `a1a07efff8`, which still passed `require_capture=True`. Its first import of `run_agent_exec_monitor` happened after the swap, so it got the `ced5901dd5` version, whose signature no longer accepts that argument.
3. **The traceback itself shows the swap.**
   - `17a--3`'s traceback points at `run_agent_exec_staged_adopters.py, line 349, in _adopt_monitor`, but prints the source line `adopted = handle_staged_gate_marker(`.
   - Python reads source text from disk at print time. The bytecode that ran was the old revision, and the text shown is the new one.
4. **The crash point is the worst possible place.**
   - Each agent had already finished its provider turn and staged a successor, so the crash dropped the handoff: `.sase_handoff_adopted.json` says `"outcome": "handoff_not_adopted"`.
   - For `17a--3`, the commit finalizer had already decided to *carry* the dirty repository to the successor (`finalizer_result.json`: `"kind": "carried_repo"`, status `success`). With no successor, nothing will ever commit those changes.

Only agents that hit a lazy-import boundary after the swap died. `17c--code` was mid-run at 10:56 (10:46 to 11:40) but staged no handoff, and it finished normally. The other fast-forwards today didn't break anyone because their commits didn't change signatures on the adoption path.

### Why it was silent: three gaps in existing defenses

SASE already knows about this hazard. `src/sase/axe/source_skew.py` opens with: _"When that checkout fast-forwards mid-run, every module already in `sys.modules` stays at the old revision while every deferred import reads the new source."_ Each of its three defenses missed today's case:

1. **Preloading doesn't cover the staged-adoption modules.**
   - `preload_post_gate_modules()` imports only the `sase.sdd` and `sase.bead` packages, plus `sase.agents_sync.prompt_archive`, `sase.notifications.senders`, `sase.vcs_provider.plugins._git_commit_dispatch`, and plugin entry points.
   - None of the lazily imported adoption targets are preloaded: `sase.axe.run_agent_exec_monitor`, `_gate`, `_plan`, `_questions`, `_pipe`, `_staged_gate`, `sase.monitor.start_stage`, and `sase.monitor.staged_owner`.
2. **The update-skew prefilter ignores signature skew.**
   - `src/sase/axe/runner_failure_facts.py` defines `_SKEW_TYPE_NAMES = {ImportError, ModuleNotFoundError, AttributeError, SyntaxError, IndentationError}`.
   - Its `_SKEW_MESSAGE_PATTERNS` list (`"cannot import name"`, `"has no attribute"`, `"does not expose binding"`, …) has no TypeError signature patterns such as `"unexpected keyword argument"`, `"missing N required … argument"`, or `"takes N positional arguments but M were given"`.
   - So `17a--3`'s `done.json` records `failure_facts.skew_suspect: false`. The candidate filter in `healer_targets.py` returns False, and the healer, which has W1 boot-identity drift data that would have proven the skew, never looks at the row.
   - The waits log shows `agent_auto_restart: targets=0 resurfaced=0 settled=0 reason=nothing_eligible` for every pass from 10:58 onward.
3. **The swap explainer has the same narrow filter.**
   - `code_swap_explanation()` labels a failure as a code swap only when its exception chain contains an `ImportError` or `AttributeError`.
   - So the notifications said only `TypeError: …` and never "the sase checkout moved under this runner".

Three UX effects then made the failures easy to miss:

- **A monitor that never started shows as Running.** `sase monitor list -a` reports `vdgpvm` (`17a--mon-2`) with `monitor_state=staged`, `pid=None`, `status_bucket=Running`. It has looked that way for more than 6 hours. It's the only monitor in `staged` state across the 400 most recent.
- **The crashed rows drop out of the agent list.** `sase agent list -a` no longer shows `17a--3` or `17a--mon-2`. The `17a` chain's last visible row is `17a--mon-1 TESTED`, which reads like a normal intermediate step.
- **A closed bead hid an uncommitted change.**
  - `sase-1n6.11.1` closed its bead *before* staging its verification monitor, so the bead reads `done` even though nothing was committed.
  - `sase-1n6.11.3` was gated on that agent and sat in WAITING until your 16:43 relaunch, holding back `.4` and `.land` with it.

### Who was hit today, and what is still broken

1. **`17a--3` (bob-mac-capture CI fix): STILL BROKEN.**
   - Thirteen modified files remain uncommitted in `~/.local/state/sase/workspaces/bobs-org/bob-cli/bob-cli_15/sase/repos/linked/bob-mac-capture`. They span `Sources/BobMacCapture/CapturePullInChoice.swift`, seven test files, three fixtures, `Tests/Fixtures/fake-bob`, and `docs/protocol.md`.
   - Monitor `vdgpvm` is stuck in `staged`.
   - CI is still red; `17r` at 17:04 found 23 failing tests across 7 classes.
2. **`sase-1n6.11.1` (`sase-core` `release_steward`): WORK LOST from the pipeline, recoverable from rescue.**
   - The first run's edits never reached `sase-core` `origin/master`; there are no `release_steward` commits today.
   - They sit in `~/.sase/rescue/202611/20261103T214433Z-ws11-linked-sase-core-234c21fc/worktree.patch`: 251 lines touching `checks.rs`, `facts.rs`, `wire.rs`, `tests/fixtures.rs`, and `tests/states.rs`.
   - A verified snapshot of the same tree is at `…/20261103T214432Z-ws11-linked-sase-core-1a56f307291e`.
   - Your 16:43 relaunch is running against the *closed* bead. Its prompt tells it to check whether the earlier work landed; it did not.
3. **`178.w0--plan` (v0.19.0 release epic planner): no lasting damage.** The plan gate (`178.w0--gate`) had been created at 10:57:01, and the epic `sase-1r2` launched at 11:09. Only a FAILED row remains.

## The Nov 1 reboot: same bug, older residue

You rebooted at 07:26:23 on Nov 1, 18 minutes after the automatic update fast-forwarded the primary from `9409312d1e` to `745d7b57b1`. That jump, at 07:07:59, carried every commit from Oct 31 afternoon, including the workspace-retention adapter work (`17f5aa3ca1`, `f2e84801cc`, `745d7b57b1`). The installed `sase_core_rs` wheel was older than the Python code until the reinstall at 17:44 that day.

- **Settlement crashed on skew.**
  - Monitors that received SIGTERM ran workspace-retention settlement through the half-swapped code. They failed in two ways:
    - Python skew: `release_workspace() got an unexpected keyword argument 'artifacts_timestamp'`.
    - Rust binding skew: `sase_core_rs is importable but does not expose binding 'decide_workspace_retention'`.
  - Either way, their follow-ups never launched. This is visible in the prompts of the Nov 1 `.f0` recovery agents; for example `sase-1oe.4.f0` says _"was SIGTERM'd by athena's restart … its follow-up never launched (workspace retention settlement failed: release_workspace() got an unexpected keyword argument 'artifacts_timestamp')"_.
- **The recovery agents died at launch.** Seven of the eight `.f0` agents launched at 13:17 by the `16p` recovery failed immediately with `Failed to claim bead '<id>' … already in_progress and assigned to '<id>'`. The beads were still assigned to the dead originals. Only `sase-1om.8.f0` succeeded.
- **Waiting agents vanished without a trace.** The SIGKILLed scopes include the waiting runners for `sase-1nv.5.1.6` (PID 4018970, scope `sase-agent-3978036-…`) and `sase-1nv.5.1.land` (PID 3934181, scope `sase-agent-3899692-…`). Neither has a `done.json`, and neither appears in `sase agent list` any more. `sase-1nv.5.1.5` and `.5.1.7` were launched on Oct 27 with the same dependency waits; they also have dead PIDs and no `done.json`. I couldn't tie them to a specific scope in the shutdown journal.
- **This explains your two manual bead closes.** `sase-1pt.9.2` (closed Nov 2: "I'm not sure why the bead wasn't closed") and `sase-1n6.10` (closed Nov 3) both belong to monitors SIGTERMed by the reboot whose settlement crashed and whose `.f0` recovery failed to claim the bead.

**Still stranded today:** these beads are `in_progress`, each assigned to an agent with no live process and no current run:

- `sase-1qh.7`: Clear the already-stuck planner and research rows
- `sase-1pi.1`: sase-core master CI passes on macOS …
- `sase-1oe.4`: Prove a green master rehearsal, then raise a handover gate …
- `sase-1q2.9.2`: A complete published sase-core-rs contains master's source …
- `sase-1nv.5.1.4`: Prove one formerly failing Athena timeout request
- `sase-1nv.5.1.5`, `sase-1nv.5.1.6`, `sase-1nv.5.1.7`, and the `sase-1nv.5.1` lander: waiting runners with dead PIDs and no `done.json`. Two of them (`.5.1.6` and the lander) are confirmed SIGKILLed at the reboot.

As a result, `sase-1nv.land` has been WAITING since 2026-11-01 10:19 and cannot finish. The reboot half of this is already tracked by open bead **`sase-1qj`** ("Host restart leaves %w waiters and land agents stranded with no auto-recovery"). These findings add evidence to that bead, plus the bead-claim conflict that defeats `.f0` recovery.

## Recommendations

### Immediate cleanup (yours to decide)

1. **Finish `17a`.**
   - Either relaunch `17a` so it continues from workspace `bob-cli_15` with the carried bob-mac-capture changes, or have `17r`'s plan absorb them.
   - Then cancel or settle the zombie monitor `vdgpvm` so it stops showing as Running.
   - Until then, don't let another agent claim workspace `bob-cli_15` blindly: launch-time eviction would move the changes to `~/.sase/rescue/`.
2. **Point the running `sase-1n6.11.1` relaunch at the rescue patch,** `~/.sase/rescue/202611/20261103T214433Z-ws11-linked-sase-core-234c21fc/worktree.patch`, so it doesn't conclude "already landed" from the closed bead.
3. **Settle the five reboot-stranded beads and `sase-1nv.5.1.5`–`.7`.** For each, reopen and reassign, or close with a note, so `sase-1nv.land` and the other blocked landers can move.

### Fixes, mapped to beads

These are listed in order of value to cost. I filed one new bug and corroborated three existing beads with today's evidence.

1. **Treat signature skew as update skew. New bug: `sase-1r4`.**
   - Add TypeError shapes to `_SKEW_MESSAGE_PATTERNS` and `_has_import_error_cause()`: `unexpected keyword argument`, `missing \d+ required (positional|keyword-only) argument`, and `takes \d+ positional arguments? but \d+ (was|were) given`.
   - Let the existing W1 witness (boot identity ≠ current identity) and W3 file proof (`git log -S <kwarg>`) do the authoritative classification. W3 would name `ced5901dd5` here directly.
   - Epic `sase-1j6` deliberately made *post-provider* skew deaths notify-only, and all three of today's deaths were post-provider (`lifecycle_phase: finalizing`). So this fix alone would not have relaunched them. It would have labeled them honestly as update skew and routed them to the healer's post-provider path, instead of a bare TypeError that nothing acted on.
2. **Preload the staged-adoption surface. Existing bead `sase-1jd`, now +1'd.**
   - Add the `sase.axe.run_agent_exec_*` adoption targets and the `sase.monitor.start_stage*` / `staged_owner` modules to `_PRELOAD_MODULES`, or walk `sase.axe` and `sase.monitor`. The adopters' function-level imports would then resolve against the boot revision.
   - `sase-1jd` proposes the matching CI test that forbids any sase module from being imported for the first time after the provider turn starts.
3. **Make an adoption crash fail loudly and in a recoverable state. Part of `sase-1r4`.**
   - When adoption raises, mark the pre-created staged monitor as failed or orphaned instead of leaving it `staged` with `status_bucket=Running`.
   - Keep the parent row visible in `sase agent list`.
4. **Resume post-provider skew deaths in place. Existing bead `sase-1jf`, now +1'd.** This is the piece that would actually have finished `17a`'s carried commit and `sase-1n6.11.1`'s `sase-core` edits.
5. **Prefer pinning over hot-swapping for long-lived runners. Existing bead `sase-1je`.** Runners should execute from an immutable snapshot of the source tree rather than the live primary checkout, for example a per-revision copy or a wheel. A swap would then only affect new launches. The existing post-wait re-exec in `src/sase/axe/run_agent_runner_refresh.py` already uses this pattern for waiting runners.
6. **Reboot recovery. Existing bead `sase-1qj`, now +1'd.** `.f0` recovery should take over the dead owner's bead claim rather than fail. The stranded detector should also treat a SIGKILLed waiter with no `done.json` as stranded.

## Evidence index

- **Primary checkout fast-forwards:** `git -C ~/projects/github/sase-org/sase reflog --date=iso`. Today: 06:38:02, 09:15:03, 10:39:08, **10:56:12 (`ced5901dd5`)**, 12:34:58, 14:20:26, 15:46:58, 16:16:35. Nov 1: **07:07:59 (`745d7b57b1`)**.
- **Update journal:** `~/.sase/update_attempts.json` (revision 1335, last success started 16:16:34).
- **Editable install:** `~/.local/share/uv/tools/sase/uv-receipt.toml`.
- **Crash records:**
  - `17a--3`: `~/.sase/projects/gh_bobs-org__bob-cli/artifacts/ace-run/202611/03/20261103105310/{done.json,error_report.md,.sase_handoff_adopted.json,finalizer_result.json}`, booted on `a1a07efff8`.
  - `178.w0--plan`: `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202611/03/20261103093607/{error_report.md,.sase_handoff_adopted.json}`, booted on `323a91d69f`.
  - `sase-1n6.11.1` (first run): `~/.sase/workflows/202611/gh_sase-org__sase_ace-run-261103_095305.txt`.
- **Signature removal:** `git show ced5901dd5` (drops `require_capture` from `run_agent_exec_monitor.capture_monitor_handoff` and `persist_chat` from `run_agent_exec_gate.handle_gate_marker`). In `a1a07efff8`, `run_agent_exec_staged_adopters.py:347–358` lazily imports and calls with `require_capture=True`.
- **Healer verdicts:** `~/.sase/axe/logs/lumberjack-waits.log` (`agent_auto_restart … nothing_eligible`), plus `failure_facts.skew_suspect=false` in `17a--3`'s `done.json`.
- **Failure notifications (sent, now dismissed):** `sase notify list -a` at 10:56:53, 10:57:04, and 10:58:51.
- **Zombie monitor:** `sase monitor show vdgpvm`, and `sase monitor list -a -j` (`monitor_state=staged`, `pid=null`, `status_bucket=Running`).
- **Rescue of `sase-1n6.11.1` work:** `~/.sase/rescue/202611/20261103T214433Z-ws11-linked-sase-core-234c21fc/` and the 16:44 `workspace-rescue` notifications.
- **Reboot:**
  - `journalctl --list-boots` (boot `ae1026e8…` at 2026-11-01 08:33).
  - `journalctl --user` scope stops at 07:26:27 to 07:27:57, including seven `Stopping timed out. Killing.`
  - Shell history `reboot` at 07:26:23.
- **Failed recovery agents:** `~/.sase/workflows/202611/gh_sase-org__sase_ace-run-261101_13171[2-9].txt`.
- **Ruled-out events:** shell history (`~/.zsh_history`) for `just install` (07:25, 11:25) and `chez update -v -a` (15:48); `~/.sase/axe/lifecycle.jsonl` for the scheduler restarts.
