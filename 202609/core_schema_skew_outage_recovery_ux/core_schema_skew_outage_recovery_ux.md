# The 2026-09-25 Core Schema-Skew Outage: Audit and TUI Recovery UX (consolidated)

- **Date:** 2026-09-25, written about 17:15–17:45 EDT. All times are EDT unless marked `Z`.
- **Machine:** athena.
- **Inputs:** five independent swarm reports ([cdx](core_schema_skew_outage_recovery_ux__cdx.md),
  [cld](core_schema_skew_outage_recovery_ux__cld.md),
  [grk](core_schema_skew_outage_recovery_ux__grk.md),
  [mus](core_schema_skew_outage_recovery_ux__mus.md),
  [gem](core_schema_skew_outage_recovery_ux__gem.md)).
- **Lead check:** I re-checked every point where the reports disagreed against the raw
  logs (`dev_update.jsonl`, `runs.jsonl`, `tui_toasts.jsonl`, `tui.log`,
  `workspace_claims.jsonl`, `~/.zsh_history`, `journalctl`), the failed runs' artifacts,
  and the current source. §4 lists the corrections.

---

## Bottom line

1. **What broke:** a breaking sase-core commit reached the live dev install before the
   sase-side change that understands it.
   - sase-core `2a0fc2a` (`feat(core)!: canonicalize agent-session contracts`, phase
     `sase-17m.8`) landed on core `master` at 14:55. It bumped several wire schemas,
     including agent scan 9→10 and launch 1→2.
   - The matching Python mirror bump and pin move belonged to the next phase,
     `sase-17m.9`, which `.8` blocks. It was still in progress.
   - At 15:02 a TUI **Update** fast-forwarded the linked core to `2a0fc2a`, rebuilt
     `sase_core_rs` into the shared uv-tool venv, and checked only that it imports.
     ACE then restarted onto it.
   - From then on, every path that parses an agent scan raised
     `ValueError: agent scan wire schema mismatch: got 10, expected 9`.
2. **Blast radius (verified in `runs.jsonl`):**
   - 12 agent runs failed between 15:10 and 15:52:
     - 9 died in bootstrap before any provider turn;
     - 1 failed after its commit landed;
     - 2 were SIGTERMed by your own `sbd work -Y`.
   - The TUI was down from 15:08 to 15:33, and scheduler chops failed from 15:06 to 15:32.
   - Verification monitors in stale workspaces kept failing until about 16:15.
   - End to end, the incident lasted about 63 minutes (15:06 → the 16:09 fix commit).
3. **Your recovery worked, but it was manual and partly risky.**
   - It took about 25 actions across the TUI, zsh, tmux, raw git, `rm`, `sbd work -Y`, and
     an out-of-band Claude Code session. That session made the decisive fix.
   - Two actions deserve review:
     - `rm -rf sase_14`. Workspace #14 had been re-claimed 2.5 minutes earlier by the
       planner you had just launched.
     - `sbd work … -Y`. It killed and relaunched 21 epic agents from their bead prompts,
       with no preview, including agents that were only waiting.
4. **Why recovery was hard:**
   - One root cause surfaced as more than 80 separate signals.
   - The recovery console (ACE) was itself a casualty.
   - There was no rollback.
   - Nothing paused new launches, so waits and monitor continuations kept feeding a
     broken runtime.
   - Every retry primitive is per-agent or per-epic, never per-incident.
   - This is the **second** occurrence of this failure class: on 2026-09-13 it failed as
     `got 9, expected 8`.
5. **Recommendation:** build an **Incident Recovery panel** ("Recover affected"),
   modeled on the existing Provider Drain modal.
   - Backing:
     - core-side failure clustering;
     - recovery classes: replay, resume finalization, re-arm, or leave alone;
     - the existing `plan_agent_restart` / `execute_agent_restart` engine;
     - a durable, sequential recovery proc.
   - It can only fire once a fixed contract probe is green.
   - Two prerequisites come first:
     - an **update safety net**: probe before swapping builds, respect the core pin, and
       roll back to the last known-good build. This alone would have prevented today's
       outage.
     - a **TUI that degrades instead of crashing** on contract skew. Without it the panel
       would have been unreachable today.
   - An **admission circuit breaker** follows.
   - Details are in §7.

---

## 1. What happened

### 1.1 Timeline (verified)

| Time | Event | Evidence |
|---|---|---|
| 14:55:11 | sase-core `2a0fc2a` lands (`sase-17m.8`, core contract flip). Scan wire 9→10, launch 1→2, cleanup 5→6, and more. | core git log; `sase bead read sase-17m.8 sase-17m.9` (`.8` blocks `.9` "Pin bump…") |
| 15:02:44 → 15:07:42 | **TUI Update** (pid 124854). sase `982209d→136a3e9`, core `96e42d9→2a0fc2a`. The prebuilt artifact misses (`commit-mismatch`), so `just rust-dev-install-uv-tool` rebuilds (292 s). The only check is "Verify sase-core-rs imports". Toast: "restarting ACE to load new code". | `dev_update.jsonl` 15:07:42 entry; `tui_toasts.jsonl` |
| 15:06:22 | First scheduler chop failure (`sidecar_auto_sync`). | axe digest `digest_20260925_150818.txt` |
| 15:08:10 | **ACE crashes**: `WorkerFailed: ValueError('…got 10, expected 9')`. The service host restarts 15:07:55→15:08:13. | `tui.log`; `journalctl --user -u sase.service` |
| 15:09:36 | Shell: `sase update -y && sase agent index gc && ace --restart-service`. The update pulls core `7677abd` (still skewed) and restarts the scheduler. `index gc` crashes, so `&&` never relaunches ACE. | `~/.zsh_history`; `dev_update.jsonl` 15:14:48 entry |
| 15:10:00 – 15:15:27 | Seven bootstrap deaths. Wait-released phases and `#fork:` continuations die in `find_named_agent` → `scan_agent_artifacts`. | `runs.jsonl`; `error_report.md` tracebacks |
| 15:16:27 | You open a **raw Claude Code session in the primary checkout** with the traceback and ask it to diagnose, fix, and commit. | `~/.claude/projects/-home-bryan-projects-github-sase-org-sase/07f3c76a….jsonl` |
| 15:23:18 | `sase-19o.1` fails **after its commit landed**: agent publication fails with `no such column: agent_session`, a second core bug in the index migration. | `20260925135218/error_report.md` |
| ~15:32 | The fixer's **uncommitted** mirror edits in the editable primary checkout restore ACE and the chops. | fixer transcript; last chop failure 15:31:57 |
| 15:33:19 | `ace` relaunched. Toast: "Agent artifact index schema rebuild failed; using a bounded scan". | zsh; toasts |
| 15:34:20 / 15:34:28 | Two more bootstrap deaths. Their runners execute code from **stale workspace checkouts** (`sase_25/src/…`, `sase_40/src/…`), which the primary-checkout fix did not reach. | `20260925153407`, `20260925153415` error reports |
| 15:34:43 – 15:35:19 | TUI: "Killed 1 agent and dismissed 3 agents"; "Killed agent (PID 1029166)". Then "Dismiss cleanup failed: dismissed-agent artifact index sync failed". | toasts |
| 15:35:16 → 15:35:23 | You launch the `0sc` resilience plan. The launcher **claims workspace #14** (preclaim, then retry-transfer at 15:35:31). | `workspace_claims.jsonl` |
| 15:35:35 – 15:36:15 | tmux `sase_34`: `gst; gaa; gc -m "feat: Add Grok 4.7 support"; gg; gp`. This hand-salvages the dead `0s8` fork's work. | zsh |
| 15:37:52 | **`rm -rf sase_14`**, while `0sc--plan` held #14. | zsh; claims ledger |
| 15:38:20 | Fixer pushes core `6cb3517` ("keep pre-contract artifact indexes and saved groups readable"). | core reflog |
| 15:40:17 / 15:40:57 | Two plan approvals fail to archive: "operational workspace lease failed" on `index.lock`. | toasts |
| 15:41:20 | `rm -rf …/sase_25/.git/index.lock`. Relaunches `0se--0` / `0sf--0` start 15:41:45 / 15:42:17. | zsh; toasts |
| 15:43:02 | **`sbd work 18j 19i 19o 19p -Y`**. Relaunches 16 agents under the same names from bead prompts. `sase-18j.9` (a waiter running 20.5 h) is SIGTERMed at 15:43:50. | zsh; `runs.jsonl` |
| 15:49:58 | **`sbd work 17x.13.10 17d.12 -Y`**. Relaunches 5 more. `sase-17d.12.land` is SIGTERMed at 15:51:53. | zsh; `runs.jsonl` |
| 15:54:52 | Core `2457913` ("accept pre-contract v2 agent relationship batches"). | core reflog |
| 15:57:02 | `just check` monitors in workspaces #12, #25 and #29 fail `_setup`. Their automatic `#fork:` continuations (`0se--1`, `sase-17m.9--1`, `0sf--1`) queue, and **all later complete**. | artifacts `155740/155748/155757` (`done.json` outcome `completed`) |
| **16:09:18** | **Fix pushed:** sase `d86bcc3ac` "fix(core)!: speak the agent-session core contract". It updates all mirrors and moves the pin to `2457913`. | sase reflog |
| 16:09:43 – 16:09:55 | ACE restarts, and the service host restarts with it. | toasts; journal |
| 16:09:59 – 16:10:43 | "Axe: 38 error(s) in the last hour". You mark 83, then 21 notifications read. A transient "Services unhealthy: host stopped" toast appears. | toasts |
| 16:20:56 | A **different** TUI process (pid 1670985, a screenshot export running from `sase_24`) crashes on the reverse skew, `got 9, expected 10`. Your main ACE (pid 1022431) keeps running. | `tui.log`; toasts |
| 16:30:12 – 16:30:20 | Another clean service-host restart. The host is active now with `NRestarts=0`. | journal |

**Outage windows:**

| Window | Start | End | Length |
|---|---|---|---|
| TUI | 15:08 | 15:33 | 25 min |
| Scheduler chops | 15:06 | 15:32 | 26 min |
| Bootstrap for workspace-sourced runners | 15:10 | about 16:09–16:15 | about 60 min |
| End to end | 15:06 | 16:09 | about 63 min |

### 1.2 Root cause

**The gate that threw.**
- `agent_scan_wire_from_dict()` in `src/sase/core/agent_scan_wire_conversion.py` (around
  line 487) requires exact equality between the Rust payload's `schema_version` and the
  Python mirror `AGENT_SCAN_WIRE_SCHEMA_VERSION`.
- Failing closed is correct for data integrity.
- Callers never turned the error into a recoverable incident, so it escaped as a
  worker or bootstrap exception.

**Why it hit everything.** The agent scan sits under almost all agent-touching code:
- ACE startup and refresh;
- `sase agent list` and `sase agent index gc`;
- the chops `sidecar_auto_sync`, `bead_claim_checks` and `gate_shell_reclaim`;
- **every `#fork:` continuation's bootstrap**, through `fork_wait_dependency` →
  `find_named_agent`.

The fixer's commit message also lists these as broken:
- launches, rejected at launch-wire schema 1;
- session-parent resolution;
- relationship batches;
- hold armers;
- fleet enrollment.

**Two independent skew channels.** No single report stated both. Neither channel reads
`sase-core-revision.txt`; only CI and `tools/ratchet_core_revision` do.

1. **Host uv-tool venv.**
   - `dev_update` runs `git merge --ff-only origin/master` in the linked core checkout,
     then rebuilds and installs that HEAD.
   - Its post-install check is import-only.
   - The app-level update path then restarts ACE whenever `result.code_changed`
     (`src/sase/ace/tui/actions/update_run.py` around line 286).
   - This channel took down ACE, the CLI, the chops, and runners that run from the
     primary checkout.
2. **Per-workspace `.venv`.**
   - The Justfile `_setup` recipe calls `_refresh-sase-core-checkout`, which
     fast-forwards the linked core to `origin/master`, and then rebuilds `sase_core_rs`
     into the workspace venv when the core source changed.
   - It then runs `tools/validate_sase_core_rs` against the **workspace's own** Python
     expectations.
   - This channel is why `just check` monitors in older workspaces kept failing
     (`scan_agent_artifacts probe returned stale schema: got 10, expected 9`) after the
     primary checkout was fixed.
   - It is also the likely cause of the 16:20 reverse skew (`got 9, expected 10`): the
     `sase_24` checkout had the new Python, but its venv still held an older build.

**The epic's ordering made a skew window inevitable.**
- Phase `sase-17m.8` pushes a breaking `feat(core)!` change to core `master`.
- Phase `sase-17m.9` moves the pin and the mirrors, and `.8` blocks it.
- Any update between those two phases lands on the skew.
- That is exactly what happened, and it also happened on 2026-09-13 (`got 9, expected 8`,
  fixed by `654335d55`).

**Secondary core bug.**
- The new core created the index `idx_agent_artifacts_agent_session` before it migrated
  the `agent_session` column.
- That caused:
  - `sase-19o.1`'s post-commit publication failure;
  - the dismiss-cleanup failure;
  - ACE's "bounded scan" fallback.
- The fixer reproduced it on a copy of your index and fixed it in `6cb3517`.

**Unrelated noise in the same window** (you had to separate these by hand):
- the `0sa` transient Claude failure at 14:23 and the plans it spawned;
- a stale `.git/index.lock` in `sase_25`, which predated the incident;
- about ten `…_main_ERROR` transcripts (exit −15/143). These are normal handoff SIGTERMs,
  not failures.

---

## 2. Blast radius (verified)

| Category | Count | Members / notes |
|---|---|---|
| Died in bootstrap (no provider tokens spent) | 9 | `sase-18j.7`, `sase-18j.8`, `sase-19i.2--1` (#42), `sase-19p.2`, `0rv.w0.f0--2` (#14), `0s8--0` (#34), `sase-17x.13.10.6`, `sase-17d.12.2--6` (#25), `sase-19i.1--1` (#40) |
| Failed after its commit (publication) | 1 | `sase-19o.1` (ran 91 min; commit landed, publication failed) |
| SIGTERMed by `sbd work -Y` | 2 | `sase-18j.9` (a waiter, up 20.5 h), `sase-17d.12.land` |
| Relaunched from bead prompts by `sbd work -Y` | 21 | `18j` ×4, `19i` ×7, `19o` ×2, `19p` ×3, `17x.13.10` ×2, `17d.12` ×3 (cld's artifact count) |
| Monitors failing `_setup` in stale workspaces | several, through about 16:15 | #12, #25, #29 at 15:57; continuations then completed normally |
| Scheduler job failures | 59 digest entries (4 + 17 + 38) | mostly `sidecar_auto_sync`; also `bead_claim_checks`, `gate_shell_reclaim`, `artifact_run_prune`, `toobig_split` |
| "Wait dependency can never self-resolve" notices | 14 (cld) | dependents of the dead runs |
| Workspaces held by failed runs | 5 | #14, #25, #34, #40, #42 |
| Notifications cleared by hand | 104 | 83 + 21 |

Long-running provider turns that were already past bootstrap mostly **survived**. For
example, `sase-19o.1` ran through the whole window and failed only at publication. So
"all agents failed" really means that **every new start and every scan consumer**
failed. It does not mean every running agent died. This distinction matters for the
recovery design: a "restart everything non-terminal" button would have killed healthy
work.

---

## 3. Audit of your recovery actions

| # | Time | Action | Assessment |
|---|---|---|---|
| 1 | 15:02 | TUI Update | Reasonable. Nothing warned that core `master` was ahead of the pin with a `feat!` change. **The update triggered the incident, but you are not at fault;** the tooling allowed it. |
| 2 | 15:09 | `sase update -y && sase agent index gc && ace --restart-service` | A sensible "update, clean, restart" reflex. It pulled another skewed core and restarted the scheduler onto it. `&&` short-circuited on the crashing `index gc`, so ACE stayed down. |
| 3 | 15:16 | Out-of-band Claude Code fixer in the primary checkout | **The decisive action.** It correctly bypassed the broken SASE runner. It diagnosed the problem in seconds, checked that `sase-17m.9` owned the same scope, reproduced the index bug on a copy of real data, and landed core fixes first. The cost: with no rollback, forward-fixing took 53 minutes to the committed sase fix. |
| 4 | ~15:32–16:09 | Fleet runs uncommitted code from the dirty primary tree | This restored ACE and the chops 37 minutes early, but it was fragile. The fixer notes that it accidentally ran a stash/pop mid-incident. |
| 5 | 15:33 | Relaunch `ace` | Correct. It worked in bounded-scan mode. |
| 6 | 15:34 | Kill 1 and dismiss 3 failed rows | Correct triage. It released the held workspaces #14, #25 and #34. Side effect: #14 was re-claimed 36 seconds later. |
| 7 | 15:35 | Hand-commit the Grok 4.7 work from `sase_34` | Efficient salvage, since only the continuation had died. It bypassed the host-owned finalizer (no stitch metadata, bead linkage, or publication); the TUI has no "salvage via finalizer" action. |
| 8 | 15:37 | `gcm; gg; rm -rf sase_14` | **The riskiest action.** The claims ledger shows #14 claimed by `0sc--plan` at 15:35:23 and held until its plan gate settled around 15:49. The planner survived only because its output goes to `~/.sase/plans`. A coding agent there would have lost its tree. Nothing in the TUI showed that #14 had changed hands. |
| 9 | 15:41 | `rm -rf …/sase_25/.git/index.lock` | Safe in practice, since #25 was briefly unclaimed. It still took shell spelunking to find. A proper fix is already in flight (`lease_index_lock_recovery.md` / `lease_git_lock_recovery.md` from `0sf` / `0sc`). |
| 10 | 15:43, 15:49 | `sbd work … -Y` ×2 | Effective: six epics were moving again within about 10 minutes. The cost is itemized below. |
| 11 | 16:09–16:10 | Restart ACE; mark 104 notifications read | Necessary busywork. The signals never learned that the incident was over. |

**Cost of action 10:**
- It relaunched phases from their **bead prompts** instead of replaying the dead turns.
  - `sase-17d.12.2` was on its sixth continuation (`--6`). It went back to `--plan` in a
    fresh workspace (#46) on a different model.
  - `sase-19i.2` repeated a full plan → monitor → continuation cycle (about 57 minutes)
    even though its dead fork already carried the monitor result.
- It killed **waiting** members that only needed their waits re-armed. The runner's
  SIGTERM handler then raised `RuntimeError: reentrant call inside <_io.BufferedWriter
  name='<stderr>'>` (`src/sase/axe/runner_signals.py`).
- `-Y`, like the TUI beads-pane `w` path (`yes_to_all=True`), skips the destructive
  preview. You never saw what was killed and wiped.

**What worked and should be kept:**
- The failed-run workspace hold plus `error_report.md` preserved every traceback.
- The wait checker flagged invalidated waiters within seconds.
- `sase bead work` forced same-name reuse gave you a working bulk relaunch without
  writing prompts.
- ACE's bounded-scan fallback kept the TUI usable while the index was broken.

**Still open (checked at 17:24):**
- `0rv.w0.f0.w0` is **still WAITING**, as it has been since 10:30, on a dependency whose
  last attempt died at 15:13 and whose workspace you deleted at 15:37. Kill or relaunch
  it.
- `sase-17m.9` owns the same pin and mirror scope that the hotfix `d86bcc3ac` shipped. Its
  chain is still running (`--mon-1` TESTING at 17:24). Check that it does not redo or
  conflict with the hotfix.
- `sase core health` is **false-red on current master**:
  - Output: `agent_launch_wire_schema_version() raised RuntimeError: unexpected schema
    version 2`.
  - Cause: `src/sase/core/health.py` hard-codes `!= 1` for the launch wire (and for the
    commit footer). The hotfix bumped launch to 2 without updating it.
  - Any health-gated design must fix this first.
- `sase revive-log --since -1d` crashes with `TypeError: can't compare offset-naive and
  offset-aware datetimes` (`src/sase/logs/run_log.py`, `iter_revive_events`).

---

## 4. Where the reports disagreed, and what the evidence says

| Claim | Source | Verdict | Evidence |
|---|---|---|---|
| The trigger was the 15:02 TUI update | cld | **Confirmed.** The 15:07:42 `dev_update` entry shows core `96e42d9→2a0fc2a`, a 292 s rebuild, an import-only check, and an ACE restart. | `dev_update.jsonl` |
| The trigger was the 15:09 shell `sase update -y` | grk (flagged uncertain) | **Partly.** It re-applied a still-skewed core (`7677abd`) and restarted the scheduler. The skew was already live from 15:02. | `dev_update.jsonl` 15:14:48 |
| Workspace `just _setup` fast-forwards core and rebuilds | gem | **Confirmed, as a second channel** (§1.2). It explains the monitor failures, not the ACE or bootstrap failures. | Justfile `_setup` |
| The incident under audit was the 16:20 crash, and "agents did not fail, the TUI did" | mus | **Incorrect.** The 16:20:56 crash was a side screenshot-export TUI from `sase_24`. Your ACE (pid 1022431) ran continuously from 15:33 onward. Twelve agent runs failed between 15:10 and 15:52. | `tui.log`; toasts; `runs.jsonl` |
| At 15:57 you made a "premature relaunch" of `0se--1`, `sase-17m.9--1` and `0sf--1`, which then failed. The 16:12–16:44 "restart waves" were manual. | gem | **Incorrect.** These were automatic `#fork:` monitor continuations queued after `just check` failed, and all completed. Your manual relaunches were `sbd work` plus single TUI launches. | `raw_xprompt.md` (`#fork:0se--0` + "Monitored command finished"); `done.json` |
| "The user authored" the core fixes | gem | **Imprecise.** An out-of-band Claude Code session you started at 15:16 authored and pushed them. | fixer transcript |
| Only 2 failures captured | cdx | **Undercount.** 12 runs failed (§2). | `runs.jsonl` |
| Restart ACE did not restart the service host | grk | **Not supported.** The journal shows the host restarting 16:09:52→16:09:55 in step with ACE. The 16:10:16 "host stopped" toast was a stale read. | journal |
| `R` / `F` ignore marks; there is no "mark all" on the Agents tab | gem, grk | **Confirmed.** `_retry_selected_agent` acts on the focused row, `R` allocates a retry name (`allocate_retry_name`) and does not kill, and the only Agents mark-all is for unread rows. | `_base_workflow.py`, `_entry_relaunch.py`, `default_config.yml` |
| Restart deletes artifacts, versus restart saves a recovery bundle | mus vs. cdx | **Both are true.** `sase agent restart` deletes the old run's artifacts but keeps the chat. `execute_agent_restart` snapshots a recovery bundle under `~/.sase/restarts` before it stops anything, and a failed relaunch returns a recovery command. | `restart --help`; `_restart_execute.py` |
| Recover by restarting "every non-terminal agent" | mus | **Rejected.** Running turns survived; this would have killed healthy work. | §2 |
| Bulk `R` / `F` over marks, with new names, as the main fix | gem | **Rejected as primary.** New names break clan, bead and wait identity. It also still needs a health gate and manual target selection. | — |

Overall, cld's evidence is the most complete. cdx best describes the reusable machinery
and the durable-transaction design. grk found the right UX pattern (Provider Drain) and
the recurrence. mus is right that the TUI must not die. gem's timeline is largely
unreliable, but its cross-clan argument and pre-flight gate idea stand.

---

## 5. Why recovery was hard, and the requirement each friction implies

| # | Friction today | Requirement |
|---|---|---|
| F1 | One cause produced 80+ signals: 10 agent-failure notices, 14 wait notices, 59 digest entries, a crash, and toasts. The 38-entry digest repeats one traceback 36 times. | **R1** Cluster failures into one incident per normalized signature, correlated with the latest update. |
| F2 | The recovery console crashed, as did `sase agent list` and `index gc`. You had to leave SASE to fix SASE. | **R2** The recovery surface must not depend on what broke: degraded mode plus a fixer path outside the runner. |
| F3 | No rollback, so a 53-minute forward fix ran under pressure on a dirty tree. | **R3** Last-known-good rollback of the checkouts plus the core build. |
| F4 | Waits and monitor continuations kept launching into the broken runtime. | **R4** Pause admissions automatically on a storm of same-signature bootstrap failures. |
| F5 | Recovery primitives are per-agent (`R` renames the agent; `,x` needs marks) or per-epic (`sbd work`). None preserves a dead continuation. | **R5** Recover by *class*, preserving identity and continuation state. |
| F6 | `-Y` and the TUI `w` path destroy without a preview. | **R6** Preview, then confirm, for every bulk action. |
| F7 | Held and claimed workspaces are invisible in the TUI, and a claim moved seconds after a dismiss. | **R7** Claim-aware workspace view; refuse destructive actions on claimed workspaces. |
| F8 | 104 manual mark-reads; wait notices say "kill and relaunch" but have no button. | **R8** Resolve an incident's signals together, and put actions on the notices. |
| F9 | Agents worked around the breakage inside feature diffs (`sase-19o.3` stubbed the scan in tests). Monitors in stale workspaces reported infrastructure failure as task failure. | **R9** Tell agents about active incidents; classify monitor setup failures as "blocked (runtime)", not task failures. |

Already in flight, so do not duplicate:
- `monitor_failed_count_leak.md` (`0sh`) fixes settled monitors inflating the "failed"
  count over a running epic.
- `lease_index_lock_recovery.md` / `lease_git_lock_recovery.md` handle stale
  `index.lock` recovery for operational leases.

---

## 6. UX options considered

| Option (from which reports) | What it does | Against today's incident | Verdict |
|---|---|---|---|
| **A. Update safety net**: stage → probe → swap, respect the pin, keep the last-known-good build, **Roll back last update** (cld D, grk D, cdx phase 2) | Probe the staged build against the host's mirrors before install and before any restart. If the probe fails, keep the old build and report `held_back`. | The 15:02 update reports "held back"; **outage 0**. | **Do first.** Cheap, and mostly install tooling. |
| **B. Degraded / safe-mode TUI** (cld C, mus A/B, cdx phase 0) | On a typed contract-mismatch error, keep ACE alive with the last good snapshot, a skew table, and actions (roll back, probe, open fixer, pause). | TUI outage 25 → 0 min. With A's rollback, fleet outage of minutes. | **Do second.** It makes everything else reachable. |
| **C. Incident banner + Recovery panel** with recovery classes and preview/confirm (cld A+B, cdx, grk C, gem 2) | One incident object with an affected set grouped by recovery class. **Recover affected** runs after the probe is green. | About 20 manual steps become about 3 keystrokes. No epics restart from scratch, and no waiters are killed. | **The core TUI answer.** |
| **D. Admission circuit breaker / fleet pause** (cld E, grk H) | After K same-signature bootstrap failures in M minutes, park new launches, and resume them on a green probe. Includes a manual "Pause fleet" toggle. | Tripping at 15:12 prevents 6 of 9 deaths and their wait cascades. | **Do after the probe is trustworthy.** |
| E. Mark-all-visible (`status:FAILED` + mark all + `,x`) (grk A, gem 1) | Bulk-select filtered rows. | Fewer keystrokes, but still identity-changing and ungated. | Cheap convenience only. |
| F. Bulk `R` / `F` over marks (gem 1) | Retry or fork every marked row. | New names break bead and clan waits, and it does not know the runtime is broken. | Reject as the recovery path. |
| G. Claim-aware workspace hygiene (cld F) | Held badge, claim owner, verified-stale lock clearing, reset refused while claimed. | Blocks the `rm -rf sase_14` near-miss. | Fold into C. |
| H. Actionable, auto-resolving notifications (cld G, grk) | One incident notice; digests grouped by signature; buttons on wait notices. | Saves the 104 mark-reads. | Fold into C. |
| I. `:recover` colon command (cld H, grk G, gem 3) | A command-line front end over C. | Only useful once C exists. | Later. |
| J. Accept schema N−1 in Python (grk E) | Tolerate a one-version lag. | Would not have helped today: the same bump renamed keys (`session` → `agent_session`). | Reject for now. |
| K. Pin the binding per workspace (grk F) | Make mixed binaries impossible. | Heavy. Partly subsumed by A applied to `_setup`. | Hardening, later. |
| L. Automatic timed retry of skew errors | — | The error is deterministic until the fix lands, so retries become a storm that hides the signal. | **Reject** (all five reports agree). |

---

## 7. Recommended solution

**Build an Incident Recovery layer whose centerpiece is a TUI Recovery panel with one
primary action, "Recover affected".** Ship it in four layers, in this order:

1. **Prevent** (option A).
2. **Survive** (option B).
3. **Recover** (option C, with G and H folded in).
4. **Contain** (option D).

Why this order, and why not one feature:
- A alone would have prevented today's outage, and its rollback is what makes B useful.
- A Recovery panel without B would have been unreachable today, because ACE was down for
  25 minutes.
- A panel without recovery classes is just a nicer list of failures, and a generic
  "retry all failed" would have repeated the damage of `-Y`.
- D needs a trustworthy probe, and today's probe is false-red.

### 7.1 Layer 0: fix the probe and add the update safety net (prevention)

1. **Fix the probe first.**
   - `src/sase/core/health.py` and `tools/validate_sase_core_rs` must compare against
     the **imported mirror constants** (`AGENT_SCAN_WIRE_SCHEMA_VERSION`,
     `AGENT_LAUNCH_WIRE_SCHEMA_VERSION`, …), not literals.
   - Add a real agent-scan round trip on a temp directory. That is the exact call that
     failed today.
2. **Stage, probe, swap** in `dev_update`.
   - Build the new core, then probe it in a subprocess against the staged artifact
     before installing it and before any ACE or service restart.
   - On failure, keep the old build, record `held_back` with the skew diff, and suppress
     the restart.
   - Never restart ACE when the Rust step failed. Today `dev_update` returns
     `changed=True` even when the reconcile fails.
3. **Respect `sase-core-revision.txt` in both channels.**
   - Let the host uv-tool install and the workspace `_setup` refresh run core ahead of
     the pin **only when the probe passes**; otherwise build at the pin.
   - This keeps the dogfooding benefit of tracking HEAD without this failure mode.
4. **Keep the last-known-good artifact.** The prebuild cache is already keyed by core
   commit. Add **Roll back last update** to the Updates panel and to safe mode.
   `dev_update.jsonl` already records old→new SHAs per checkout. The rollback must
   refuse a dirty tree.
5. **Caveat:** probe before the new core touches durable state. Today's index migration
   shows that rolling back after a migration can create the reverse skew. The artifact
   index can be rebuilt; saved-group archives (v3) cannot.
6. **Process rule** (not UX, but it caused today): a `feat(core)!` change should not
   reach core `master` until the host phase that moves the pin lands with it. Two ways:
   - an epic land step that pushes both repos together;
   - a core compatibility shim that keeps emitting the old schema until the pin moves.

   Worth recording as a decision. Layer 0 makes a violation harmless locally; it does
   not make the violation right.

### 7.2 Layer 1: ACE degrades instead of dying

- **Trigger.** Catch a typed `runtime_contract_mismatch` at the scan-worker and startup
  boundaries. It should be a small allowlist:
  - wire or schema mismatch;
  - `ImportError` of `sase_core_rs`;
  - "format this process does not understand".

  A failed post-restart probe should also enter this mode. Today the path goes to
  `_handle_exception` and exits (`src/sase/ace/tui/app.py`).
- **Screen:**
  - the error, once;
  - a skew table: per wire, the Python mirror, the Rust-reported version, the pin, and
    the installed core commit;
  - the last update receipt;
  - recent failures read **directly from raw JSON/JSONL** (`runs.jsonl`,
    `error_report.md`, `recent_errors.json`) without calling `sase_core_rs`.
- **Actions:**
  - **Roll back last update**;
  - **Run probe**;
  - **Open fixer**: a tmux window in the primary checkout running your default provider
    CLI with a pre-filled incident brief. This is what you did by hand at 15:16, and it
    must not go through the SASE runner;
  - **Pause fleet**;
  - **Retry normal startup**.
- **Boundary note.** Reading raw failure records without the core is a deliberate,
  narrow exception to the "Rust core is required" decision. It is presentation of raw
  records, not domain logic. Record it as a decision so it does not grow.

### 7.3 Layer 2: incident banner and Recovery panel (the TUI centerpiece)

**Incident model.** This goes in **sase-core**: Telegram, mobile and the CLI need the
same answer, so by the core-boundary litmus test it is backend logic.
- `Incident { id, signature, first_seen, last_seen, state, correlated_update, members[] }`.
- The signature is normalized: strip pids, paths, timestamps and hashes; keep the
  exception type, message and top frame.
- Each member records:
  - `failure_stage` (bootstrap / provider / finalize / monitor-setup). Add it to
    `done.json` and `error_report.md`; today only the traceback implies it.
  - `recovery_class`, `held_workspace`, and a `replay_plan`.
- Unrelated failures (the `0sa` transient, the stale lock) cluster separately. The
  panel does the triage you did in your head.

**Banner.**
- A single line under the header while an incident is active. Below the clustering
  threshold nothing changes.
- The header separates `Task failures` from `Infrastructure blocked`, so monitors that
  failed on `_setup` do not read as failed task logic.

**Panel.** It follows the Provider Drain modal's pattern: plan off-thread, show a
preview modal, then submit a durable proc and toast the result.

```text
INCIDENT i-0925-a · ACTIVE 14m · ValueError: agent scan wire schema mismatch (got 10, expected 9)
first 15:06:22 (sidecar_auto_sync) · 3m after update sase 982209d→136a3e9, core 96e42d9→2a0fc2a
probe: ✗ agent_scan 10≠9  launch 2≠1        admissions: ⏸ paused 15:12 (3 same-signature bootstrap failures)

REPLAY · died before provider start · same name / prompt / continuation              9
  sase-18j.7          wait on sase-18j.6 released → bootstrap          —
  sase-19i.2--1       fork: monitor result 1pbgzhry989h                ws #42 held · clean vs baseline
  sase-17d.12.2--6    fork: monitor result ty5tnr2qr22z                ws #25 held · index.lock (no git pid, 21m)
  …
RESUME FINALIZATION · commit landed, publication failed                               1
  sase-19o.1          stitch create --resume                           ws #37 held
RE-ARM WAITERS · dependency will be replayed; no kill                                14
PARKED LAUNCHES · never started; start on resume                                      6
BLOCKED MONITORS · runtime, not task failure                                          3
LEAVE ALONE · running and healthy                                                    —
NEEDS DECISION · dirty or unknown workspace, live agent, pending gate                 0
SCHEDULER JOBS · sidecar_auto_sync ×40 · bead_claim_checks ×13 · … (self-heal on next tick)

[r] roll back update  [p] probe  [f] open fixer  [R] recover affected (preview)  [w] workspaces  [z] resolve
```

**Recovery semantics.** Everything hard here was proven today.
- **Gated on health.**
  - Before `R` fans out, require a green, fixed probe plus a disposable bootstrap
    canary.
  - While the probe is red, the only enabled actions are roll back, open fixer, and
    pause. `R` can be *armed* to fire automatically when the probe goes green.
- **Replay by class, preserving identity.**
  - **Bootstrap deaths** cost zero provider tokens, and the stored `raw_xprompt.md` *is*
    the continuation (for example `#fork:<parent>` plus the monitor result). So
    `execute_agent_restart` already acts as a verbatim, same-name replay, and it saves a
    recovery bundle first.
  - **Post-commit failures** resume finalization (`sase stitch create --resume`); they do
    not relaunch.
  - **Waiters** are re-armed or retargeted, not killed. This is where `-Y` hurt.
  - **Running agents are left alone.**
- **Workspaces.**
  - A held workspace is handed to its replay only if it matches the finalizer baseline
    plus the dead run's delta.
  - Dirty or unknown workspaces go to **NEEDS DECISION**.
  - A workspaces sub-view shows claim owner, dirty count, and lock age with owner pid.
    It offers Salvage (through the host finalizer, not a raw `git commit`), Release,
    Clear verified-stale lock, and Reset. Reset is **refused while claimed**, which
    blocks the `rm -rf sase_14` case.
- **Preview, then confirm.**
  - The per-member plan reuses `plan_agent_restart()` warnings: live, dirty, related
    wipes, pending questions.
  - The default excludes uncertain rows; the operator can add rows explicitly.
- **Sequential, durable, resumable.**
  - Run as one durable proc, `agent.incident_recover:<id>`, through normal admission.
    Provider drain already avoids restart storms the same way.
  - Persist its state machine: planned → quiesced → runtime repaired → reloaded →
    canary green → bundled → restarting → complete/partial.
  - Recovery often crosses the ACE and service restart that loads the fix, so the new
    ACE generation must resume the proc.
- **Audit.**
  - Record `incident → old run → recovery bundle → new run` for every member, together
    with the acting session, confirmation, skipped rows, and canary evidence.
  - Today's proc store only says "kill sase" and "Started 1 agent(s)", which is why no
    report could prove a complete old→new mapping.
- **Resolve.**
  - When the probe is green, the replays have launched, and the signature has not
    recurred for T minutes, all of the incident's notifications resolve in one step.
  - One summary notice remains, linking an incident report file.
  - Wait notices outside incidents gain **Relaunch dependency**, **Re-arm**, and
    **Kill waiter** buttons.

**Keys.**
- `,i` looks free in `leader_mode.keys`; check it when implementing. Also add an Admin
  Center tab entry, and update `src/sase/default_config.yml`.
- Do not overload `R`.
- Add a cheap Agents-tab **mark all visible** as a same-week convenience for unrelated
  bulk work.

### 7.4 Layer 3: admission circuit breaker

- **Automatic trip.** K=3 bootstrap-stage failures with one signature within M=10
  minutes, or any single contract-mismatch failure.
- **Manual trip.** "Pause fleet" from safe mode, the banner, or the bang-mode toggles.
- **Parked:**
  - wait-released starts;
  - monitor continuations;
  - `sbd work` and TUI launches, with an explicit "launch anyway";
  - agent-spawning chops.
- **Not parked:** running agents, and chops the fix depends on.
- **Resume.** Automatic on a green probe. Parked launches start in queue order and need
  no replay, because they never died.
- **Tell running agents.** Add a short "known incident" line to continuation and final
  context, such as: "agent-scan schema skew: do not stub or work around it in your
  diff; report and stop if blocked."
- **Fits existing decisions.** Parking a *launch* never blocks a running agent, so this
  is consistent with the "A Gate Never Blocks An Agent" and "Agents Are Single-Turn"
  decisions. The pause needs a durable store with a reason and an owner.

### 7.5 Counterfactual: today with the layers in place

| Layers present | Outcome |
|---|---|
| Layer 0 only | At 15:07: "core update held back: agent scan v10 vs v9 (pin c31b8cf)". No restart onto the skew and no failures; `sase-17m.9` lands later and the next update passes. **Outage 0.** |
| Layer 1 with rollback, no pre-swap probe | At 15:08 ACE opens in safe mode, and one key rolls back (seconds with a retained artifact). **Outage about 2–6 minutes, with 2–3 deaths.** |
| Layers 2 and 3 without 0 or 1 | The breaker trips at 15:12 and 6 launches park. After the 16:09 fix the probe goes green, parked launches start, and **Recover affected** replays 3, resumes 1 finalization, and re-arms the waiters. One resolve clears everything. **About 3 keystrokes instead of about 25 actions across 6 tools**, and no epic phase restarts from scratch. |

### 7.6 Where the code goes

- **sase-core:**
  - signature normalization and incident clustering;
  - recovery-class and replay-plan computation;
  - the admission pause as a first-class admission blocker;
  - the `Incident` wire type;
  - a contract-inventory handshake reporting every wire version.

  Move sase's `sase-core-revision.txt` pin with each change.
- **sase (Python):**
  - runner `failure_stage` recording;
  - `dev_update` and Justfile stage/probe/swap/rollback and pin respect;
  - the core-independent raw failure reader for safe mode;
  - Textual banner, panel, modals and keybindings.

### 7.7 Build order

| # | Slice | Size | Unblocks |
|---|---|---|---|
| 1 | Fix `sase core health` / `validate_sase_core_rs` to use mirror constants, and add an agent-scan round-trip probe | S | everything |
| 2 | `dev_update` stage→probe→swap, pin respect (host and `_setup`), last-known-good, no restart on failure, **Roll back last update** | M | 3 |
| 3 | ACE degraded mode (typed mismatch boundary, raw-ledger view, rollback, open fixer, pause) | M | 4 |
| 4 | Runner `failure_stage`, core incident clustering, banner, read-only Recovery panel, grouped digests, infra-vs-task split | M | 5 |
| 5 | **Recover affected**: class-aware, previewed, durable sequential proc over `execute_agent_restart`, plus the claim-aware workspaces sub-view and audit linkage | L (epic) | — |
| 6 | Admission breaker plus agent incident advisory | M | — |

**Acceptance test for the whole layer.** Replay today in a sandbox: an editable host, a
linked core with a deliberate mirror bump, and a queued epic with waiters and monitor
continuations. Assert:
- both skew directions are handled;
- ACE never crashes;
- a held-back or safe-mode path is taken;
- exactly one incident is created;
- the recovery plan matches §2;
- no waiting agent is killed, and there is no retry storm while the probe is red;
- an interrupted recovery resumes;
- the audit links every old run to its new run.

---

## 8. Follow-up defects found

Items 1 and 2 are recorded; the rest are candidates for task beads:

1. `sase core health` is false-red on master: the launch-wire and footer versions are
   hard-coded (`src/sase/core/health.py`). **Verified live.** Recorded as a
   `DISCOVERED ISSUE` note on epic `sase-17m`, whose contract flip caused it; phase
   `sase-17m.10` is the cross-repo audit and guardrail phase.
2. `sase revive-log --since` crashes on comparing naive and aware datetimes. The cause:
   `revive_log_cli._resolve_since` strips the tzinfo that `run_log._parse_event_timestamp`
   now adds. **Verified live.** Filed as task bead `sase-19q` (bug, small).
3. The app-level update restarts ACE even when the Rust build step failed:
   `dev_update` returns `changed=True` when the reconcile fails (cld).
4. The runner's SIGTERM handler re-enters stderr (`src/sase/axe/runner_signals.py`) (cld).
5. Normal handoff SIGTERMs are saved as `…_main_ERROR` transcripts, which reads as
   failure (cld).
6. The wait checker's "can never self-resolve" fires on routine monitor failures that
   already have a continuation. It fired at 16:46 for `sase-19p.2` (cld, grk).
7. `tools/validate_sase_core_rs` hard-codes schema literals instead of importing the
   mirrors (cld).
8. Operational: the orphaned waiter `0rv.w0.f0.w0`, and a check that `sase-17m.9` does
   not conflict with the hotfix `d86bcc3ac`.

---

## Appendix: evidence index

| Evidence | Path / command |
|---|---|
| Update runs (SHAs, commands, restart) | `~/.sase/logs/dev_update.jsonl` (15:07:42, 15:14:48) |
| Run outcomes (12 failures) | `~/.sase/logs/runs.jsonl` (`260925_1510`–`1552`) |
| Toast timeline | `~/.sase/logs/tui_toasts.jsonl` (pids 124854, 1022431, 1670985) |
| Crashes | `~/.sase/logs/tui.log` (15:08:10; 16:20:56 from `sase_24` screenshot export); `tui.log.2` (2026-09-13, `got 9, expected 8`) |
| Claims | `~/.sase/logs/workspace_claims.jsonl` (#14: claim 15:35:23, transfer 15:35:31) |
| Shell actions | `~/.zsh_history` 15:09:36–16:09:24 (`sbd`=`sase -p bead`, `ace`=`sase -p tui`) |
| Failed-run reports | `~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202609/25/{20260925151151,…153407,153415,135218}/error_report.md` |
| Monitor continuations | the same dir, `20260925155740/155748/155757` (`raw_xprompt.md`, `done.json`) |
| Scheduler digests | `~/.sase/axe/error_digests/digest_20260925_{150818,151451,160958}.txt` |
| Service host | `journalctl --user -u sase.service` (15:08:13, 16:09:55, 16:30:20) |
| Fixer session | `~/.claude/projects/-home-bryan-projects-github-sase-org-sase/07f3c76a-….jsonl` (from 15:16:27) |
| Commits | core `2a0fc2a` (break), `7677abd`, `6cb3517`, `2457913`; sase `d86bcc3ac` (fix), `654335d55` (the 09-13 recurrence) |
| Beads | `sase-17m.8` (core flip, closed) → blocks `sase-17m.9` (pin bump, in progress) |
| Code | `src/sase/core/agent_scan_wire_conversion.py`; `src/sase/core/health.py`; `src/sase/ace/tui/actions/update_run.py`; `src/sase/ace/tui/actions/_base_workflow.py`; `src/sase/ace/tui/actions/agent_workflow/_entry_relaunch.py`; `src/sase/agent/restart.py`, `_restart_execute.py`; `src/sase/agent/provider_drain.py`; Justfile `_setup` |
| Related in-flight plans | `monitor_failed_count_leak.md` (`0sh`); `lease_index_lock_recovery.md`, `lease_git_lock_recovery.md` |
